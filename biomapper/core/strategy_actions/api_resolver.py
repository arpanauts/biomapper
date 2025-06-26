"""
API Resolver Strategy Action

This action resolves historical or deprecated identifiers by querying external APIs.
It supports batching, rate limiting, and retry logic for resilient API interactions.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.core.strategy_actions.base import BaseStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.models import Endpoint


@register_action("API_RESOLVER")
class ApiResolver(BaseStrategyAction):
    """
    Resolves identifiers by querying an external API.
    
    This action is designed to handle historical or deprecated identifiers
    by making requests to external APIs (e.g., UniProt) to retrieve current
    mappings. It includes support for batching requests, rate limiting,
    and automatic retries on failure.
    
    Parameters:
        input_context_key: Key in context containing identifiers to resolve
        output_context_key: Key to store resolved identifiers in context
        api_base_url: Base URL of the API to query
        endpoint_path: API endpoint path (appended to base URL)
        batch_size: Number of identifiers to query per request (default: 50)
        rate_limit_delay: Delay in seconds between batches (default: 0.1)
        max_retries: Maximum number of retry attempts (default: 3)
        timeout: Request timeout in seconds (default: 30)
        request_params: Additional parameters to include in requests
        response_id_field: Field in response containing the resolved ID
        response_mapping_field: Field containing mapping information
    
    Example YAML configuration:
        - action: API_RESOLVER
          params:
            input_context_key: "unresolved_identifiers"
            output_context_key: "resolved_identifiers"
            api_base_url: "https://www.uniprot.org"
            endpoint_path: "/uniprot/{id}/history"
            batch_size: 100
            rate_limit_delay: 0.5
            response_id_field: "current_accession"
    """
    
    def __init__(self, session: AsyncSession):
        """Initialize the API resolver with database session."""
        self.session = session
        self.logger = logging.getLogger(__name__)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the HTTP session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def _close_session(self):
        """Close the HTTP session if it exists."""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def execute(
        self,
        current_identifiers: List[str],
        current_ontology_type: str,
        action_params: Dict[str, Any],
        source_endpoint: Endpoint,
        target_endpoint: Endpoint,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute the API resolution process.
        
        Args:
            current_identifiers: Current list of identifiers
            current_ontology_type: Current ontology type
            action_params: Action configuration parameters
            source_endpoint: Source endpoint
            target_endpoint: Target endpoint
            context: Execution context
            
        Returns:
            Dict containing resolved identifiers and provenance data
        """
        try:
            # Validate required parameters
            input_key = action_params.get('input_context_key')
            output_key = action_params.get('output_context_key')
            api_base_url = action_params.get('api_base_url')
            endpoint_path = action_params.get('endpoint_path', '')
            
            if not input_key:
                raise ValueError("input_context_key is required")
            if not output_key:
                raise ValueError("output_context_key is required")
            if not api_base_url:
                raise ValueError("api_base_url is required")
            
            # Get configuration parameters
            batch_size = action_params.get('batch_size', 50)
            rate_limit_delay = action_params.get('rate_limit_delay', 0.1)
            max_retries = action_params.get('max_retries', 3)
            timeout = action_params.get('timeout', 30)
            request_params = action_params.get('request_params', {})
            response_id_field = action_params.get('response_id_field', 'id')
            response_mapping_field = action_params.get('response_mapping_field')
            
            # Get identifiers from context
            identifiers_to_resolve = context.get(input_key, [])
            if not identifiers_to_resolve:
                self.logger.info(f"No identifiers found in context key '{input_key}'")
                return self._empty_result(current_identifiers, current_ontology_type)
            
            self.logger.info(f"Resolving {len(identifiers_to_resolve)} identifiers via API")
            
            # Process identifiers in batches
            resolved_mappings = {}
            provenance = []
            session = await self._get_session()
            
            for i in range(0, len(identifiers_to_resolve), batch_size):
                batch = identifiers_to_resolve[i:i + batch_size]
                
                # Rate limiting delay (except for first batch)
                if i > 0:
                    await asyncio.sleep(rate_limit_delay)
                
                # Process batch with retries
                batch_results = await self._process_batch_with_retries(
                    session=session,
                    batch=batch,
                    api_base_url=api_base_url,
                    endpoint_path=endpoint_path,
                    request_params=request_params,
                    response_id_field=response_id_field,
                    response_mapping_field=response_mapping_field,
                    max_retries=max_retries,
                    timeout=timeout
                )
                
                # Update results
                resolved_mappings.update(batch_results['mappings'])
                provenance.extend(batch_results['provenance'])
            
            # Extract resolved identifiers
            resolved_identifiers = list(resolved_mappings.values())
            
            # Store in context
            context[output_key] = resolved_identifiers
            
            self.logger.info(
                f"Resolved {len(resolved_identifiers)} of {len(identifiers_to_resolve)} identifiers"
            )
            
            return {
                'input_identifiers': identifiers_to_resolve,
                'output_identifiers': resolved_identifiers,
                'output_ontology_type': current_ontology_type,
                'provenance': provenance,
                'details': {
                    'api_base_url': api_base_url,
                    'total_queried': len(identifiers_to_resolve),
                    'total_resolved': len(resolved_identifiers),
                    'resolution_rate': len(resolved_identifiers) / len(identifiers_to_resolve)
                    if identifiers_to_resolve else 0
                }
            }
            
        finally:
            # Clean up session
            await self._close_session()
    
    async def _process_batch_with_retries(
        self,
        session: aiohttp.ClientSession,
        batch: List[str],
        api_base_url: str,
        endpoint_path: str,
        request_params: Dict[str, Any],
        response_id_field: str,
        response_mapping_field: Optional[str],
        max_retries: int,
        timeout: int
    ) -> Dict[str, Any]:
        """
        Process a batch of identifiers with retry logic.
        
        Args:
            session: HTTP session
            batch: Batch of identifiers to process
            api_base_url: Base URL of the API
            endpoint_path: API endpoint path
            request_params: Additional request parameters
            response_id_field: Field containing resolved ID
            response_mapping_field: Field containing mapping info
            max_retries: Maximum retry attempts
            timeout: Request timeout
            
        Returns:
            Dict with mappings and provenance data
        """
        mappings = {}
        provenance = []
        
        for identifier in batch:
            for attempt in range(max_retries):
                try:
                    # Build URL (handle placeholder in endpoint_path)
                    url = urljoin(api_base_url, endpoint_path.replace('{id}', identifier))
                    
                    # Make request
                    async with session.get(
                        url,
                        params=request_params,
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as response:
                    
                        if response.status == 200:
                            data = await response.json()
                            
                            # Extract resolved identifier
                            resolved_id = self._extract_field(data, response_id_field)
                            if resolved_id:
                                mappings[identifier] = resolved_id
                                
                                # Create provenance entry
                                prov_entry = {
                                    'action': 'api_resolution',
                                    'api_endpoint': url,
                                    'original_id': identifier,
                                    'resolved_id': resolved_id,
                                    'status': 'resolved'
                                }
                                
                                # Add mapping info if available
                                if response_mapping_field:
                                    mapping_info = self._extract_field(data, response_mapping_field)
                                    if mapping_info:
                                        prov_entry['mapping_info'] = mapping_info
                                
                                provenance.append(prov_entry)
                                break  # Success, exit retry loop
                            else:
                                self.logger.warning(
                                    f"No resolved ID found for {identifier} in field '{response_id_field}'"
                                )
                                provenance.append({
                                    'action': 'api_resolution',
                                    'api_endpoint': url,
                                    'original_id': identifier,
                                    'status': 'no_mapping_found'
                                })
                                break
                        
                        elif response.status == 404:
                            # Not found, no need to retry
                            provenance.append({
                                'action': 'api_resolution',
                                'api_endpoint': url,
                                'original_id': identifier,
                                'status': 'not_found'
                            })
                            break
                        
                        else:
                            # Other error, might be worth retrying
                            if attempt == max_retries - 1:
                                self.logger.error(
                                    f"Failed to resolve {identifier} after {max_retries} attempts. "
                                    f"Status: {response.status}"
                                )
                                provenance.append({
                                    'action': 'api_resolution',
                                    'api_endpoint': url,
                                    'original_id': identifier,
                                    'status': 'error',
                                    'error': f'HTTP {response.status}'
                                })
                            else:
                                # Wait before retry
                                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
                except Exception as e:
                    if attempt == max_retries - 1:
                        self.logger.error(
                            f"Exception resolving {identifier}: {str(e)}"
                        )
                        provenance.append({
                            'action': 'api_resolution',
                            'api_endpoint': url if 'url' in locals() else api_base_url,
                            'original_id': identifier,
                            'status': 'error',
                            'error': str(e)
                        })
                    else:
                        # Wait before retry
                        await asyncio.sleep(2 ** attempt)
        
        return {
            'mappings': mappings,
            'provenance': provenance
        }
    
    def _extract_field(self, data: Any, field_path: str) -> Any:
        """
        Extract a field from nested data using dot notation.
        
        Args:
            data: Data to extract from
            field_path: Dot-separated path to field (e.g., "result.current.id")
            
        Returns:
            Extracted value or None if not found
        """
        if not field_path:
            return data
        
        parts = field_path.split('.')
        current = data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list) and part.isdigit():
                index = int(part)
                if 0 <= index < len(current):
                    current = current[index]
                else:
                    return None
            else:
                return None
        
        return current
    
    def _empty_result(
        self,
        current_identifiers: List[str],
        current_ontology_type: str
    ) -> Dict[str, Any]:
        """Return empty result when no identifiers to resolve."""
        return {
            'input_identifiers': current_identifiers,
            'output_identifiers': current_identifiers,
            'output_ontology_type': current_ontology_type,
            'provenance': [],
            'details': {
                'total_queried': 0,
                'total_resolved': 0,
                'resolution_rate': 0
            }
        }