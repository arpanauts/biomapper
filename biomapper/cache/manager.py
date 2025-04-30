"""Cache manager for entity mapping resolution with bidirectional transitivity."""

import datetime
import logging
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

# Import metamapper configuration models needed by cache manager
from ..db.models import EntityTypeConfig, CacheStats
# Import cache-specific models
from ..db.cache_models import EntityMapping, MappingMetadata
from ..db.session import get_session

# Configure logging
logger = logging.getLogger(__name__)


class CacheManager:
    """Manager for entity mapping cache with bidirectional transitivity support."""

    def __init__(
        self,
        default_ttl_days: int = 365,
        confidence_threshold: float = 0.7,
        enable_stats: bool = True,
    ) -> None:
        """Initialize the cache manager.
        
        Args:
            default_ttl_days: Default time-to-live in days for cached mappings
            confidence_threshold: Minimum confidence for valid mappings
            enable_stats: Whether to track cache usage statistics
        """
        self.default_ttl_days = default_ttl_days
        self.confidence_threshold = confidence_threshold
        self.enable_stats = enable_stats
        logger.info(
            f"Initialized CacheManager (TTL: {default_ttl_days} days, "
            f"confidence threshold: {confidence_threshold})"
        )

    @contextmanager
    def _session_scope(self) -> Session:
        """Provide a transactional scope around a series of operations.
        
        Yields:
            Active database session
        """
        session = get_session()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            logger.error(f"Database error: {e}")
            session.rollback()
            raise
        finally:
            session.close()

    def _update_stats(
        self, 
        session: Session, 
        hit: bool = False, 
        miss: bool = False,
        direct: bool = False,
        derived: bool = False,
        api_call: bool = False,
        transitive_derivation: bool = False
    ) -> None:
        """Update cache usage statistics.
        
        Args:
            session: Database session
            hit: Whether this was a cache hit
            miss: Whether this was a cache miss
            direct: Whether this was a direct lookup
            derived: Whether this was a derived mapping lookup
            api_call: Whether an API call was made
            transitive_derivation: Whether a new transitive relationship was derived
        """
        if not self.enable_stats:
            return
        
        today = datetime.date.today()
        stats = session.query(CacheStats).filter(CacheStats.stats_date == today).first()
        
        if not stats:
            stats = CacheStats(stats_date=today)
            session.add(stats)
        
        if hit:
            stats.hits += 1
        if miss:
            stats.misses += 1
        if direct:
            stats.direct_lookups += 1
        if derived:
            stats.derived_lookups += 1
        if api_call:
            stats.api_calls += 1
        if transitive_derivation:
            stats.transitive_derivations += 1

    def _get_ttl(
        self, 
        session: Session, 
        source_type: str, 
        target_type: str
    ) -> int:
        """Get TTL days for a specific entity type pair.
        
        Args:
            session: Database session
            source_type: Source entity type
            target_type: Target entity type
            
        Returns:
            TTL in days
        """
        config = (
            session.query(EntityTypeConfig)
            .filter(
                EntityTypeConfig.source_type == source_type,
                EntityTypeConfig.target_type == target_type
            )
            .first()
        )
        
        if not config:
            return self.default_ttl_days
        
        return config.ttl_days

    def _increment_usage(self, session: Session, mapping: EntityMapping) -> None:
        """Increment usage count for a mapping.
        
        Args:
            session: Database session
            mapping: Entity mapping
        """
        mapping.usage_count += 1
        mapping.last_updated = datetime.datetime.utcnow()

    def lookup(
        self, 
        source_id: str, 
        source_type: str, 
        target_type: Optional[str] = None,
        include_derived: bool = True,
        min_confidence: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Look up target entities for a source entity.
        
        Args:
            source_id: Source entity ID
            source_type: Source entity type
            target_type: Optional target entity type filter
            include_derived: Whether to include derived mappings
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of mappings as dictionaries
        """
        if min_confidence is None:
            min_confidence = self.confidence_threshold
        
        with self._session_scope() as session:
            query = (
                session.query(EntityMapping)
                .filter(
                    EntityMapping.source_id == source_id,
                    EntityMapping.source_type == source_type,
                    EntityMapping.confidence >= min_confidence
                )
            )
            
            if target_type:
                query = query.filter(EntityMapping.target_type == target_type)
            
            if not include_derived:
                query = query.filter(EntityMapping.is_derived == False)
            
            # Get all matching mappings
            mappings = query.all()
            result = []
            
            # Update stats
            direct_count = sum(1 for m in mappings if not m.is_derived)
            derived_count = sum(1 for m in mappings if m.is_derived)
            
            self._update_stats(
                session, 
                hit=bool(mappings),
                miss=not bool(mappings),
                direct=bool(direct_count),
                derived=bool(derived_count)
            )
            
            # Increment usage count for all returned mappings
            for mapping in mappings:
                self._increment_usage(session, mapping)
                result.append(mapping.to_dict())
            
            return result

    def bidirectional_lookup(
        self, 
        entity_id: str, 
        entity_type: str,
        target_type: Optional[str] = None,
        include_derived: bool = True,
        min_confidence: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Look up mappings for an entity in both directions.
        
        Args:
            entity_id: Entity ID
            entity_type: Entity type
            target_type: Optional target entity type filter
            include_derived: Whether to include derived mappings
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of mappings as dictionaries
        """
        if min_confidence is None:
            min_confidence = self.confidence_threshold
        
        with self._session_scope() as session:
            # Query as source
            source_query = (
                session.query(EntityMapping)
                .filter(
                    EntityMapping.source_id == entity_id,
                    EntityMapping.source_type == entity_type,
                    EntityMapping.confidence >= min_confidence
                )
            )
            
            # Query as target
            target_query = (
                session.query(EntityMapping)
                .filter(
                    EntityMapping.target_id == entity_id,
                    EntityMapping.target_type == entity_type,
                    EntityMapping.confidence >= min_confidence
                )
            )
            
            if target_type:
                source_query = source_query.filter(EntityMapping.target_type == target_type)
                target_query = target_query.filter(EntityMapping.source_type == target_type)
            
            if not include_derived:
                source_query = source_query.filter(EntityMapping.is_derived == False)
                target_query = target_query.filter(EntityMapping.is_derived == False)
            
            # Get all mappings
            source_mappings = source_query.all()
            target_mappings = target_query.all()
            all_mappings = source_mappings + target_mappings
            
            # Update stats
            direct_count = sum(1 for m in all_mappings if not m.is_derived)
            derived_count = sum(1 for m in all_mappings if m.is_derived)
            
            self._update_stats(
                session, 
                hit=bool(all_mappings),
                miss=not bool(all_mappings),
                direct=bool(direct_count),
                derived=bool(derived_count)
            )
            
            # Increment usage count for all returned mappings
            result = []
            seen_ids = set()  # Prevent duplicates
            
            for mapping in all_mappings:
                if mapping.id in seen_ids:
                    continue
                
                seen_ids.add(mapping.id)
                self._increment_usage(session, mapping)
                result.append(mapping.to_dict())
            
            return result

    def add_mapping(
        self,
        source_id: str,
        source_type: str,
        target_id: str,
        target_type: str,
        confidence: float = 1.0,
        mapping_source: str = "api",
        is_derived: bool = False,
        derivation_path: Optional[List[int]] = None,
        metadata: Optional[Dict[str, str]] = None,
        ttl_days: Optional[int] = None,
        bidirectional: bool = True,
    ) -> Dict[str, Any]:
        """Add a new mapping to the cache.
        
        Args:
            source_id: Source entity ID
            source_type: Source entity type
            target_id: Target entity ID
            target_type: Target entity type
            confidence: Mapping confidence (0-1)
            mapping_source: Source of the mapping
            is_derived: Whether this is a derived mapping
            derivation_path: List of mapping IDs in the derivation chain
            metadata: Additional metadata for the mapping
            ttl_days: Days until expiration
            bidirectional: Whether to create a reverse mapping as well
            
        Returns:
            Dictionary representation of the created mapping
        """
        with self._session_scope() as session:
            # Check if mapping already exists
            existing = (
                session.query(EntityMapping)
                .filter(
                    EntityMapping.source_id == source_id,
                    EntityMapping.source_type == source_type,
                    EntityMapping.target_id == target_id,
                    EntityMapping.target_type == target_type
                )
                .first()
            )
            
            if existing:
                # Update existing mapping
                existing.confidence = confidence
                existing.mapping_source = mapping_source
                existing.is_derived = is_derived
                
                if derivation_path:
                    existing.derivation_path_list = derivation_path
                
                existing.last_updated = datetime.datetime.utcnow()
                
                # Set expiration
                if ttl_days is None:
                    ttl_days = self._get_ttl(session, source_type, target_type)
                
                existing.expires_at = (
                    datetime.datetime.utcnow() + datetime.timedelta(days=ttl_days)
                )
                
                # Update metadata
                if metadata:
                    # Remove existing metadata
                    session.query(MappingMetadata).filter(
                        MappingMetadata.mapping_id == existing.id
                    ).delete()
                    
                    # Add new metadata
                    for key, value in metadata.items():
                        meta = MappingMetadata(
                            mapping_id=existing.id,
                            key=key,
                            value=str(value)
                        )
                        session.add(meta)
                
                result = existing.to_dict()
            else:
                # Create new mapping
                if ttl_days is None:
                    ttl_days = self._get_ttl(session, source_type, target_type)
                
                expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=ttl_days)
                
                new_mapping = EntityMapping(
                    source_id=source_id,
                    source_type=source_type,
                    target_id=target_id,
                    target_type=target_type,
                    confidence=confidence,
                    mapping_source=mapping_source,
                    is_derived=is_derived,
                    last_updated=datetime.datetime.utcnow(),
                    usage_count=1,
                    expires_at=expires_at
                )
                
                if derivation_path:
                    new_mapping.derivation_path_list = derivation_path
                
                session.add(new_mapping)
                session.flush()  # Ensure ID is assigned
                
                # Add metadata
                if metadata:
                    for key, value in metadata.items():
                        meta = MappingMetadata(
                            mapping_id=new_mapping.id,
                            key=key,
                            value=str(value)
                        )
                        session.add(meta)
                
                result = new_mapping.to_dict()
                
                # Update statistics
                self._update_stats(
                    session,
                    transitive_derivation=is_derived
                )
            
            # Create bidirectional mapping if requested
            if bidirectional and source_id != target_id:
                # Swap source and target
                reverse_source_id = target_id
                reverse_source_type = target_type
                reverse_target_id = source_id
                reverse_target_type = source_type
                
                # Check if reverse mapping exists
                reverse_existing = (
                    session.query(EntityMapping)
                    .filter(
                        EntityMapping.source_id == reverse_source_id,
                        EntityMapping.source_type == reverse_source_type,
                        EntityMapping.target_id == reverse_target_id,
                        EntityMapping.target_type == reverse_target_type
                    )
                    .first()
                )
                
                if reverse_existing:
                    # Update existing reverse mapping
                    reverse_existing.confidence = confidence
                    reverse_existing.mapping_source = mapping_source
                    reverse_existing.is_derived = is_derived
                    
                    if derivation_path:
                        reverse_existing.derivation_path_list = derivation_path
                    
                    reverse_existing.last_updated = datetime.datetime.utcnow()
                    reverse_existing.expires_at = (
                        datetime.datetime.utcnow() + datetime.timedelta(days=ttl_days)
                    )
                else:
                    # Create new reverse mapping
                    reverse_ttl = self._get_ttl(session, reverse_source_type, reverse_target_type)
                    reverse_expires = datetime.datetime.utcnow() + datetime.timedelta(days=reverse_ttl)
                    
                    reverse_mapping = EntityMapping(
                        source_id=reverse_source_id,
                        source_type=reverse_source_type,
                        target_id=reverse_target_id,
                        target_type=reverse_target_type,
                        confidence=confidence,
                        mapping_source=mapping_source,
                        is_derived=is_derived,
                        last_updated=datetime.datetime.utcnow(),
                        usage_count=1,
                        expires_at=reverse_expires
                    )
                    
                    if derivation_path:
                        reverse_mapping.derivation_path_list = derivation_path
                    
                    session.add(reverse_mapping)
                    
                    # Add metadata to reverse mapping if provided
                    if metadata and reverse_mapping.id:
                        for key, value in metadata.items():
                            meta = MappingMetadata(
                                mapping_id=reverse_mapping.id,
                                key=key,
                                value=str(value)
                            )
                            session.add(meta)
            
            return result

    def set_entity_type_config(
        self,
        source_type: str,
        target_type: str,
        ttl_days: int,
        confidence_threshold: Optional[float] = None,
    ) -> None:
        """Set configuration for an entity type pair.
        
        Args:
            source_type: Source entity type
            target_type: Target entity type
            ttl_days: Days until expiration
            confidence_threshold: Minimum confidence threshold
        """
        with self._session_scope() as session:
            config = (
                session.query(EntityTypeConfig)
                .filter(
                    EntityTypeConfig.source_type == source_type,
                    EntityTypeConfig.target_type == target_type
                )
                .first()
            )
            
            if config:
                config.ttl_days = ttl_days
                if confidence_threshold is not None:
                    config.confidence_threshold = confidence_threshold
            else:
                config = EntityTypeConfig(
                    source_type=source_type,
                    target_type=target_type,
                    ttl_days=ttl_days
                )
                
                if confidence_threshold is not None:
                    config.confidence_threshold = confidence_threshold
                
                session.add(config)

    def bulk_add_mappings(
        self,
        mappings: List[Dict[str, Any]],
        bidirectional: bool = True
    ) -> int:
        """Add multiple mappings to the cache.
        
        Args:
            mappings: List of mapping dictionaries
            bidirectional: Whether to create reverse mappings
            
        Returns:
            Number of mappings added
        """
        added_count = 0
        
        for mapping_data in mappings:
            try:
                self.add_mapping(
                    source_id=mapping_data["source_id"],
                    source_type=mapping_data["source_type"],
                    target_id=mapping_data["target_id"],
                    target_type=mapping_data["target_type"],
                    confidence=mapping_data.get("confidence", 1.0),
                    mapping_source=mapping_data.get("mapping_source", "api"),
                    is_derived=mapping_data.get("is_derived", False),
                    derivation_path=mapping_data.get("derivation_path"),
                    metadata=mapping_data.get("metadata"),
                    ttl_days=mapping_data.get("ttl_days"),
                    bidirectional=bidirectional
                )
                added_count += 1
            except Exception as e:
                logger.error(f"Error adding mapping {mapping_data}: {e}")
                continue
        
        return added_count

    def delete_expired_mappings(self) -> int:
        """Delete expired mappings from the cache.
        
        Returns:
            Number of mappings deleted
        """
        with self._session_scope() as session:
            now = datetime.datetime.utcnow()
            query = session.query(EntityMapping).filter(
                EntityMapping.expires_at < now
            )
            count = query.count()
            query.delete()
            
            return count

    def get_cache_stats(
        self, 
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None
    ) -> List[Dict[str, Any]]:
        """Get cache usage statistics.
        
        Args:
            start_date: Optional start date for stats period
            end_date: Optional end date for stats period
            
        Returns:
            List of daily statistics
        """
        with self._session_scope() as session:
            query = session.query(CacheStats)
            
            if start_date:
                query = query.filter(CacheStats.stats_date >= start_date)
            
            if end_date:
                query = query.filter(CacheStats.stats_date <= end_date)
            
            query = query.order_by(CacheStats.stats_date)
            
            return [
                {
                    "date": stats.stats_date.isoformat(),
                    "hits": stats.hits,
                    "misses": stats.misses,
                    "hit_ratio": stats.hits / (stats.hits + stats.misses) if (stats.hits + stats.misses) > 0 else 0,
                    "direct_lookups": stats.direct_lookups,
                    "derived_lookups": stats.derived_lookups,
                    "api_calls": stats.api_calls,
                    "transitive_derivations": stats.transitive_derivations
                }
                for stats in query.all()
            ]

    def get_all_entity_types(self) -> Dict[str, Set[str]]:
        """Get all entity types in the cache.
        
        Returns:
            Dictionary mapping entity types to sets of IDs
        """
        with self._session_scope() as session:
            # Get unique source types and IDs
            source_types = (
                session.query(EntityMapping.source_type, EntityMapping.source_id)
                .distinct()
                .all()
            )
            
            # Get unique target types and IDs
            target_types = (
                session.query(EntityMapping.target_type, EntityMapping.target_id)
                .distinct()
                .all()
            )
            
            # Combine results
            result: Dict[str, Set[str]] = {}
            
            for type_name, entity_id in source_types + target_types:
                if type_name not in result:
                    result[type_name] = set()
                result[type_name].add(entity_id)
            
            return result
