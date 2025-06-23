"""Cache management functionality for the mapping executor."""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from biomapper.db.cache_models import (
    EntityMapping,
    PathExecutionLog as MappingPathExecutionLog,
    PathExecutionStatus,
)
from biomapper.db.models import MappingPath
from biomapper.core.exceptions import (
    CacheError,
    CacheTransactionError,
    CacheRetrievalError,
    CacheStorageError,
    ErrorCode,
)
from biomapper.utils.formatters import PydanticEncoder


def get_current_utc_time() -> datetime:
    """Return the current time in UTC timezone."""
    return datetime.now(timezone.utc)


class CacheManager:
    """Manages cache operations for mapping results."""
    
    def __init__(self, cache_sessionmaker: sessionmaker, logger: logging.Logger):
        """Initialize the cache manager.
        
        Args:
            cache_sessionmaker: SQLAlchemy async sessionmaker for cache database
            logger: Logger instance for logging operations
        """
        self._cache_sessionmaker = cache_sessionmaker
        self.logger = logger
    
    async def check_cache(
        self,
        input_identifiers: List[str],
        source_ontology: str,
        target_ontology: str,
        mapping_path_id: Optional[int] = None,
        expiry_time: Optional[datetime] = None
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], List[str]]:
        """Check cache for existing mapping results.
        
        Args:
            input_identifiers: List of source identifiers to check
            source_ontology: Source ontology type
            target_ontology: Target ontology type
            mapping_path_id: Optional specific mapping path ID to filter by
            expiry_time: Optional expiry time to filter results
            
        Returns:
            Tuple of (cached_results, uncached_identifiers) where:
                - cached_results: Dict mapping source IDs to list of cached results
                - uncached_identifiers: List of identifiers not found in cache
        """
        if not input_identifiers:
            return {}, []
        
        cached_results = {}
        
        try:
            async with self._cache_sessionmaker() as cache_session:
                # Build base query
                query = select(EntityMapping).where(
                    EntityMapping.source_type == source_ontology,
                    EntityMapping.target_type == target_ontology
                )
                
                # Add filter for source_id based on the number of identifiers
                if len(input_identifiers) == 1:
                    query = query.where(EntityMapping.source_id == input_identifiers[0])
                else:
                    query = query.where(EntityMapping.source_id.in_(input_identifiers))
                
                # Add timestamp filtering if expiry_time is provided
                if expiry_time:
                    query = query.where(EntityMapping.last_updated >= expiry_time)
                
                # Note: mapping_path_id filtering is done post-query since path_id
                # is stored in the JSON mapping_path_details field
                
                # Execute query
                result = await cache_session.execute(query)
                entity_mappings = result.scalars().all()
                
                # Process results
                for mapping in entity_mappings:
                    # Filter by mapping_path_id if specified
                    should_include = True
                    if mapping_path_id is not None and mapping.mapping_path_details:
                        try:
                            path_details = mapping.mapping_path_details
                            if isinstance(path_details, str):
                                path_details = json.loads(path_details)
                            stored_path_id = path_details.get('path_id')
                            if stored_path_id != mapping_path_id:
                                should_include = False
                        except (json.JSONDecodeError, AttributeError, TypeError):
                            should_include = False
                    
                    if should_include:
                        source_id = mapping.source_id
                        
                        # Parse target_id which might be JSON array
                        target_identifiers = None
                        if mapping.target_id:
                            try:
                                if mapping.target_id.startswith('[') and mapping.target_id.endswith(']'):
                                    target_identifiers = json.loads(mapping.target_id)
                                else:
                                    target_identifiers = [mapping.target_id]
                            except (json.JSONDecodeError, AttributeError):
                                target_identifiers = [mapping.target_id]
                        
                        # Get mapping path details
                        path_details = None
                        if mapping.mapping_path_details:
                            try:
                                if isinstance(mapping.mapping_path_details, str):
                                    path_details = json.loads(mapping.mapping_path_details)
                                else:
                                    path_details = mapping.mapping_path_details
                            except (json.JSONDecodeError, TypeError):
                                pass
                        
                        # Create result structure matching _execute_path format
                        cached_results[source_id] = {
                            "source_identifier": source_id,
                            "target_identifiers": target_identifiers,
                            "mapped_value": target_identifiers[0] if target_identifiers else None,
                            "status": PathExecutionStatus.SUCCESS.value,
                            "message": "Found in cache.",
                            "confidence_score": mapping.confidence_score or 0.8,
                            "mapping_path_details": path_details,
                            "hop_count": mapping.hop_count,
                            "mapping_direction": mapping.mapping_direction,
                            "cached": True,
                        }
                
                # Determine uncached identifiers
                cached_source_ids = set(cached_results.keys())
                uncached_identifiers = [
                    id for id in input_identifiers 
                    if id not in cached_source_ids
                ]
                
                self.logger.debug(
                    f"Cache check complete. Found {len(cached_results)} cached results "
                    f"out of {len(input_identifiers)} requested identifiers"
                )
                
                return cached_results, uncached_identifiers
                
        except SQLAlchemyError as e:
            self.logger.error(f"Database error during cache check: {str(e)}")
            raise CacheRetrievalError(
                message=f"Failed to check cache: {str(e)}",
                details={'source_identifiers': input_identifiers, 'error': str(e)}
            )
        except Exception as e:
            self.logger.error(f"Unexpected error during cache check: {str(e)}")
            raise CacheError(
                message=f"Unexpected cache check error: {str(e)}",
                error_code=ErrorCode.CACHE_RETRIEVAL_ERROR
            )
    
    async def store_mapping_results(
        self,
        results_to_cache: Dict[str, Dict[str, Any]],
        path: Union[MappingPath, "ReversiblePath"],
        source_ontology: str,
        target_ontology: str,
        mapping_session_id: Optional[int] = None
    ) -> Optional[int]:
        """Store mapping results in cache.
        
        Args:
            results_to_cache: Dict mapping source IDs to mapping results
            path: MappingPath or ReversiblePath object
            source_ontology: Source ontology type
            target_ontology: Target ontology type  
            mapping_session_id: Optional mapping session ID
        """
        if not results_to_cache:
            self.logger.debug("No results to cache")
            return None
        
        path_id = path.id
        path_name = path.name
        self.logger.debug(f"Caching results for path ID: {path_id}, Name: {path_name}")
        
        # Note: _get_path_details would need to be passed from MappingExecutor
        # For now, use empty details
        path_step_details = {}
        
        # Determine if this is a reverse path
        is_reversed = getattr(path, "is_reverse", False)
        mapping_direction = "reverse" if is_reversed else "forward"
        
        # Calculate hop count from path steps if available
        hop_count = len(path.steps) if hasattr(path, "steps") and path.steps else None
        self.logger.debug(f"Path {path_id} - Reversed: {is_reversed}, Hop Count: {hop_count}")
        
        # Prepare the rich path details JSON structure
        mapping_path_info = {
            "path_id": path_id,
            "path_name": path_name,
            "is_reversed": is_reversed,
            "hop_count": hop_count,
            "steps": path_step_details
        }
        try:
            path_details_json = json.dumps(mapping_path_info, cls=PydanticEncoder)
        except Exception as e:
            self.logger.error(f"Failed to serialize path details for {path_id} to JSON: {e}", exc_info=True)
            path_details_json = json.dumps({"error": "Failed to serialize path details"}, cls=PydanticEncoder)
        
        async with self._cache_sessionmaker() as cache_session:
            try:
                # Get a representative source ID for logging
                representative_source_id = next(iter(results_to_cache.keys()))
                
                # Create path execution log
                path_log = await self.create_path_execution_log(
                    path_id=path_id,
                    status=PathExecutionStatus.SUCCESS,
                    representative_source_id=representative_source_id,
                    source_entity_type=source_ontology
                )
                
                # Calculate match count accurately
                input_count = len(results_to_cache)
                match_count = sum(
                    1 for res in results_to_cache.values()
                    if res.get("target_identifiers") and any(res["target_identifiers"])
                )
                self.logger.debug(f"Input Count: {input_count}, Match Count: {match_count}")
                
                # Create a mapping execution log entry (using actual model fields)
                # Note: The PathExecutionLog model doesn't have all the fields the code expects
                # We'll store what we can in the available fields
                
                entity_mappings = []
                current_time = get_current_utc_time()
                
                for source_id, result in results_to_cache.items():
                    target_identifiers = result.get("target_identifiers", [])
                    # Ensure target_identifiers is always a list
                    if not isinstance(target_identifiers, list):
                        target_identifiers = [target_identifiers] if target_identifiers is not None else []
                    
                    # Filter out None values from target identifiers
                    valid_target_ids = [tid for tid in target_identifiers if tid is not None]
                    
                    if not valid_target_ids:
                        self.logger.debug(f"No valid target identifiers found for source {source_id}")
                        continue
                    
                    # Calculate confidence score
                    confidence_score = self.calculate_confidence_score(result, hop_count, is_reversed, path_step_details)
                    
                    self.logger.debug(f"Source: {source_id}, Hops: {hop_count}, Reversed: {is_reversed}, Confidence: {confidence_score}")
                    
                    # Create mapping_path_details JSON with complete path information
                    mapping_path_details_dict = self.create_mapping_path_details(
                        path_id=path_id,
                        path_name=path_name,
                        hop_count=hop_count,
                        mapping_direction=mapping_direction,
                        path_step_details=path_step_details,
                        log_id=None,  # Will be set after we have the log entry ID
                        additional_metadata=result.get("additional_metadata")
                    )
                    try:
                        mapping_path_details = json.dumps(mapping_path_details_dict, cls=PydanticEncoder)
                    except Exception as e:
                        self.logger.error(f"Failed to serialize mapping_path_details for {source_id} to JSON: {e}", exc_info=True)
                        mapping_path_details = json.dumps({"error": "Failed to serialize details"}, cls=PydanticEncoder)
                    
                    # Create entity mapping for each valid target identifier
                    for target_id in valid_target_ids:
                        # Determine mapping source based on path details
                        source_type = self.determine_mapping_source(path_step_details)
                        
                        entity_mapping = EntityMapping(
                            source_id=str(source_id),  # Correct field name
                            source_type=source_ontology,  # Correct field name
                            target_id=str(target_id),  # Correct field name
                            target_type=target_ontology,  # Correct field name
                            mapping_source=source_type,
                            last_updated=current_time,
                            
                            # Enhanced metadata fields:
                            confidence_score=confidence_score,
                            hop_count=hop_count,
                            mapping_direction=mapping_direction,
                            mapping_path_details=mapping_path_details
                        )
                        entity_mappings.append(entity_mapping)
                
                if not entity_mappings:
                    self.logger.warning(f"No valid entity mappings generated for path {path_id}, despite having results to cache.")
                    # Still log the execution attempt
                    path_log.status = PathExecutionStatus.NO_MAPPING_FOUND
                    path_log.end_time = get_current_utc_time()
                    await cache_session.commit()
                    self.logger.info(f"Logged execution for path {path_id} with no resulting mappings.")
                    return path_log.id
                
                # Add all entity mappings
                cache_session.add_all(entity_mappings)
                
                # Update path log status
                path_log.status = PathExecutionStatus.SUCCESS
                path_log.end_time = get_current_utc_time()
                
                await cache_session.commit()
                
                self.logger.info(f"Successfully cached {len(entity_mappings)} mappings and execution log (ID: {path_log.id}) for path {path_id}.")
                return path_log.id  # Return the ID of the log entry
                
            except IntegrityError as e:
                await cache_session.rollback()
                self.logger.warning(f"Integrity error during cache storage: {str(e)}")
                # Don't raise - caching failures shouldn't break execution
            except SQLAlchemyError as e:
                await cache_session.rollback()
                self.logger.error(f"Database error during cache storage: {str(e)}")
                raise CacheStorageError(
                    message=f"Failed to store cache results: {str(e)}",
                    details={'cache_data': results_to_cache, 'error': str(e)}
                )
            except Exception as e:
                await cache_session.rollback()
                self.logger.error(f"Unexpected error during cache storage: {str(e)}")
                raise CacheError(
                    message=f"Unexpected cache storage error: {str(e)}",
                    error_code=ErrorCode.CACHE_STORAGE_ERROR
                )
    
    async def create_path_execution_log(
        self,
        path_id: int,
        status: PathExecutionStatus,
        representative_source_id: str,
        source_entity_type: str
    ) -> MappingPathExecutionLog:
        """Create a new path execution log entry.
        
        Args:
            path_id: ID of the mapping path
            status: Execution status
            representative_source_id: Representative source identifier
            source_entity_type: Type of source entity
            
        Returns:
            Created MappingPathExecutionLog instance
        """
        async with self._cache_sessionmaker() as cache_session:
            try:
                log_entry = MappingPathExecutionLog(
                    relationship_mapping_path_id=path_id,  # Correct field name
                    status=status,
                    start_time=get_current_utc_time(),  # Correct field name
                    source_entity_id=representative_source_id,  # Using representative ID
                    source_entity_type=source_entity_type
                )
                
                cache_session.add(log_entry)
                await cache_session.commit()
                await cache_session.refresh(log_entry)
                
                self.logger.debug(
                    f"Created path execution log {log_entry.id} "
                    f"for path {path_id} with status {status}"
                )
                
                return log_entry
                
            except SQLAlchemyError as e:
                await cache_session.rollback()
                self.logger.error(f"Failed to create path execution log: {str(e)}")
                raise CacheTransactionError(
                    message=f"Failed to create path execution log: {str(e)}",
                    details={'path_id': path_id, 'operation': 'create_path_execution_log', 'error': str(e)}
                )
    
    async def get_path_details_from_log(
        self,
        path_log_id: int,
        metamapper_session: AsyncSession
    ) -> Dict[str, Any]:
        """Get path details from a path execution log.
        
        Args:
            path_log_id: ID of the path execution log
            metamapper_session: Async session for metamapper database
            
        Returns:
            Dictionary containing path details
        """
        try:
            async with self._cache_sessionmaker() as cache_session:
                # Get the path log entry
                result = await cache_session.execute(
                    select(MappingPathExecutionLog).where(
                        MappingPathExecutionLog.id == path_log_id
                    )
                )
                path_log = result.scalar_one_or_none()
                
                if not path_log:
                    raise CacheRetrievalError(
                        message=f"Path execution log {path_log_id} not found",
                        details={'path_log_id': path_log_id}
                    )
                
                # Get path details from metamapper DB
                # Note: This requires access to _get_path_details method from MappingExecutor
                # For now, return basic info from the log
                return {
                    'path_id': path_log.relationship_mapping_path_id,  # Correct field name
                    'status': path_log.status.value,
                    'started_at': path_log.start_time.isoformat() if path_log.start_time else None,
                    'completed_at': path_log.end_time.isoformat() if path_log.end_time else None,
                    'representative_source_id': path_log.source_entity_id,  # Correct field name
                    'source_entity_type': path_log.source_entity_type,
                }
                
        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get path details from log: {str(e)}")
            raise CacheRetrievalError(
                message=f"Failed to retrieve path details: {str(e)}",
                details={'path_log_id': path_log_id, 'error': str(e)}
            )
    
    def calculate_confidence_score(
        self,
        result: Dict[str, Any],
        hop_count: Optional[int],
        is_reversed: bool,
        path_step_details: Dict[str, Any]
    ) -> float:
        """Calculate confidence score for a mapping result.
        
        Args:
            result: The mapping result
            hop_count: Number of hops in the path
            is_reversed: Whether the path was reversed
            path_step_details: Details about path steps
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # If result already has a confidence score, use it
        if 'confidence_score' in result:
            return result['confidence_score']
        
        # Base confidence by hop count
        if hop_count is None:
            base_confidence = 0.7
        elif hop_count == 1:
            base_confidence = 0.95
        elif hop_count == 2:
            base_confidence = 0.85
        elif hop_count == 3:
            base_confidence = 0.75
        else:
            # For 4+ hops, decrease by 0.1 per hop
            base_confidence = max(0.15, 0.75 - (hop_count - 3) * 0.1)
        
        # Apply reverse penalty
        if is_reversed:
            base_confidence -= 0.1
        
        # Apply resource type penalties
        resource_types = set()
        if isinstance(path_step_details, dict) and 'steps' in path_step_details:
            for step in path_step_details['steps']:
                if 'resource_name' in step:
                    resource_types.add(step['resource_name'].lower())
                if 'resource_client' in step:
                    resource_types.add(step['resource_client'].lower())
        
        # Apply penalties for certain resource types
        if any('rag' in rt for rt in resource_types):
            base_confidence -= 0.05
        if any('llm' in rt for rt in resource_types):
            base_confidence -= 0.1
        
        # Ensure confidence is between 0 and 1
        final_confidence = max(0.0, min(1.0, base_confidence))
        
        # Round to 2 decimal places
        return round(final_confidence, 2)
    
    def determine_mapping_source(self, path_step_details: Dict[str, Any]) -> str:
        """Determine the mapping source type from path details.
        
        Args:
            path_step_details: Details about the path steps
            
        Returns:
            Mapping source type (e.g., 'api', 'spoke', 'rag', 'llm', 'ramp')
        """
        if not path_step_details or 'steps' not in path_step_details:
            return 'api'
        
        # Check each step for resource type indicators
        for step in path_step_details.get('steps', []):
            resource_name = str(step.get('resource_name', '')).lower()
            resource_client = str(step.get('resource_client', '')).lower()
            
            # Check for specific resource types
            if 'spoke' in resource_name or 'spoke' in resource_client:
                return 'spoke'
            elif 'rag' in resource_name or 'rag' in resource_client:
                return 'rag'
            elif 'llm' in resource_name or 'llm' in resource_client:
                return 'llm'
            elif 'ramp' in resource_name or 'ramp' in resource_client:
                return 'ramp'
        
        return 'api'
    
    def create_mapping_path_details(
        self,
        path_id: int,
        path_name: str,
        hop_count: Optional[int],
        mapping_direction: str,
        path_step_details: Dict[str, Any],
        log_id: Optional[int] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a structured dictionary with path details.
        
        Args:
            path_id: ID of the mapping path
            path_name: Name of the mapping path
            hop_count: Number of hops
            mapping_direction: Direction of mapping
            path_step_details: Details about path steps
            log_id: Optional execution log ID
            additional_metadata: Optional additional metadata
            
        Returns:
            Dictionary with structured path details
        """
        details = {
            'path_id': path_id,
            'path_name': path_name,
            'hop_count': hop_count,
            'direction': mapping_direction,
            'execution_timestamp': get_current_utc_time().isoformat()
        }
        
        if log_id is not None:
            details['log_id'] = log_id
        
        # Add step details if available
        if path_step_details and 'steps' in path_step_details:
            details['steps'] = path_step_details['steps']
        
        # Add additional metadata if provided
        if additional_metadata:
            details['additional_metadata'] = additional_metadata
        
        return details