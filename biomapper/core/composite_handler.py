"""Middleware module for handling composite identifiers in Biomapper.

This module provides middleware components that work with the MappingExecutor
to handle composite identifiers (e.g., comma-separated UniProt IDs or 
underscore-separated gene names).

It implements the configurable pre-processing approach outlined in
docs/technical_notes/composite_identifier_handling.md, supporting the 
generalization of composite identifier handling.
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from sqlalchemy.orm import Session

from biomapper.db.models import CompositePatternConfig, CompositeProcessingStep
from biomapper.core.exceptions import BiomapperError, ConfigurationError

logger = logging.getLogger(__name__)


class CompositeIdentifierHandler:
    """Middleware for handling composite identifiers in mapping operations.
    
    This handler detects composite identifiers based on patterns defined in the
    database, splits them into individual components, and provides utilities
    for executing mapping operations on the components and aggregating results.
    """
    
    def __init__(self):
        """Initialize the composite identifier handler."""
        self._patterns: Dict[str, List[CompositePatternConfig]] = {}
        self._initialized = False
    
    async def initialize(self, session: Session) -> None:
        """Load composite identifier patterns from the database.
        
        Args:
            session: SQLAlchemy database session for metamapper.db
        """
        try:
            # Load all patterns and group by ontology type
            patterns = session.query(CompositePatternConfig).order_by(
                CompositePatternConfig.ontology_type,
                CompositePatternConfig.priority
            ).all()
            
            # Group patterns by ontology type
            for pattern in patterns:
                ontology_type = pattern.ontology_type.upper()  # Ensure uppercase for consistency
                if ontology_type not in self._patterns:
                    self._patterns[ontology_type] = []
                
                # Add the pattern to the list for this ontology type
                self._patterns[ontology_type].append(pattern)
                
                # Load the processing steps for this pattern
                steps = session.query(CompositeProcessingStep).filter(
                    CompositeProcessingStep.pattern_id == pattern.id
                ).order_by(CompositeProcessingStep.order).all()
                
                logger.debug(
                    f"Loaded pattern '{pattern.name}' for ontology type '{ontology_type}' "
                    f"with {len(steps)} processing steps"
                )
            
            logger.info(
                f"Initialized composite identifier handler with patterns for "
                f"{len(self._patterns)} ontology types"
            )
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize composite identifier handler: {e}")
            raise ConfigurationError(
                f"Failed to initialize composite identifier handler: {str(e)}",
                details={"error": str(e)}
            )
    
    def has_patterns_for_ontology(self, ontology_type: str) -> bool:
        """Check if patterns exist for the specified ontology type.
        
        Args:
            ontology_type: The ontology type to check
            
        Returns:
            True if patterns exist for the ontology type, False otherwise
        """
        if not self._initialized:
            logger.warning("Composite identifier handler not initialized")
            return False
        
        return ontology_type.upper() in self._patterns
    
    def is_composite(self, identifier: str, ontology_type: str) -> bool:
        """Check if an identifier is composite based on patterns for its ontology type.
        
        Args:
            identifier: The identifier to check
            ontology_type: The ontology type of the identifier
            
        Returns:
            True if the identifier matches any composite pattern for its ontology type
        """
        if not self._initialized:
            logger.warning("Composite identifier handler not initialized")
            return False
        
        ontology_type = ontology_type.upper()  # Ensure uppercase for consistency
        if ontology_type not in self._patterns:
            return False
        
        # Check against each pattern for this ontology type
        for pattern_config in self._patterns[ontology_type]:
            if re.search(pattern_config.pattern, identifier):
                return True
        
        return False
    
    def split_composite(self, identifier: str, ontology_type: str) -> Tuple[bool, List[str], Optional[CompositePatternConfig]]:
        """Split a composite identifier into its individual components.
        
        Args:
            identifier: The composite identifier to split
            ontology_type: The ontology type of the identifier
            
        Returns:
            Tuple containing:
            - is_composite: True if the identifier is composite
            - components: List of individual components (or [identifier] if not composite)
            - pattern: The pattern config that matched, or None if no match
        """
        if not self._initialized:
            logger.warning("Composite identifier handler not initialized")
            return False, [identifier], None
        
        ontology_type = ontology_type.upper()  # Ensure uppercase for consistency
        if ontology_type not in self._patterns:
            return False, [identifier], None
        
        # Check against each pattern for this ontology type
        for pattern_config in self._patterns[ontology_type]:
            if re.search(pattern_config.pattern, identifier):
                # Split the identifier using the delimiters from the pattern
                delimiters = pattern_config.delimiters.split(',')
                components = [identifier]
                
                # Apply each delimiter in sequence
                for delimiter in delimiters:
                    new_components = []
                    for component in components:
                        new_components.extend([c.strip() for c in component.split(delimiter) if c.strip()])
                    components = new_components
                
                return True, components, pattern_config
        
        return False, [identifier], None
    
    def get_component_ontology_type(self, pattern_config: CompositePatternConfig) -> str:
        """Get the ontology type to use for components of a composite identifier.
        
        Args:
            pattern_config: The composite pattern configuration
            
        Returns:
            The ontology type to use for components
        """
        if pattern_config.keep_component_type:
            return pattern_config.ontology_type
        else:
            return pattern_config.component_ontology_type or pattern_config.ontology_type


class CompositeMiddleware:
    """Middleware that integrates the composite identifier handler with the MappingExecutor.
    
    This middleware intercepts mapping operations to identify and handle composite
    identifiers, providing transparent support for complex identifier formats
    without requiring client-specific implementations.
    """
    
    def __init__(self, handler: CompositeIdentifierHandler):
        """Initialize the composite middleware.
        
        Args:
            handler: The composite identifier handler to use
        """
        self.handler = handler
    
    async def preprocess_identifiers(
        self, 
        identifiers: List[str], 
        ontology_type: str
    ) -> Dict[str, List[Tuple[str, str]]]:
        """Preprocess identifiers to identify and split composite identifiers.
        
        Args:
            identifiers: List of identifiers to process
            ontology_type: The ontology type of the identifiers
            
        Returns:
            Dictionary mapping original identifiers to a list of (component, component_ontology_type) tuples
        """
        result = {}
        
        for identifier in identifiers:
            is_composite, components, pattern_config = self.handler.split_composite(
                identifier, ontology_type
            )
            
            if is_composite and pattern_config:
                component_type = self.handler.get_component_ontology_type(pattern_config)
                result[identifier] = [(comp, component_type) for comp in components]
            else:
                # Not composite, or no matching pattern
                result[identifier] = [(identifier, ontology_type)]
        
        return result
    
    async def aggregate_results(
        self,
        original_identifiers: List[str],
        component_results: Dict[str, Any],
        preprocessed_map: Dict[str, List[Tuple[str, str]]],
        ontology_type: str
    ) -> Dict[str, Any]:
        """Aggregate mapping results from individual components back to original identifiers.
        
        Args:
            original_identifiers: The original identifiers (before preprocessing)
            component_results: The mapping results for each component
            preprocessed_map: The map of original identifiers to components from preprocess_identifiers
            ontology_type: The original ontology type
            
        Returns:
            Dictionary mapping original identifiers to aggregated mapping results
        """
        aggregated_results = {}
        
        for original_id in original_identifiers:
            # Get the components for this original identifier
            components = preprocessed_map.get(original_id, [(original_id, ontology_type)])
            
            if len(components) == 1 and components[0][0] == original_id:
                # Not a composite identifier, use the result directly
                aggregated_results[original_id] = component_results.get(original_id)
            else:
                # Composite identifier, aggregate results from components
                component_ids = [comp[0] for comp in components]
                
                # Find the pattern that matched this identifier
                _, _, pattern_config = self.handler.split_composite(original_id, ontology_type)
                
                if pattern_config:
                    # Aggregate based on the mapping strategy in the pattern
                    strategy = pattern_config.mapping_strategy
                    
                    if strategy == 'first_match':
                        # Use the first component that has a mapping result
                        for comp_id in component_ids:
                            result = component_results.get(comp_id)
                            if result and result[0]:  # Not None and not empty list
                                aggregated_results[original_id] = result
                                break
                        else:
                            # No component had a mapping result
                            aggregated_results[original_id] = None
                    
                    elif strategy == 'all_matches':
                        # Combine all mapping results from all components
                        all_mapped_ids = []
                        successful_component = None
                        
                        for comp_id in component_ids:
                            result = component_results.get(comp_id)
                            if result and result[0]:  # Not None and not empty list
                                all_mapped_ids.extend(result[0])
                                if not successful_component:
                                    successful_component = result[1]
                        
                        if all_mapped_ids:
                            aggregated_results[original_id] = (all_mapped_ids, successful_component)
                        else:
                            aggregated_results[original_id] = None
                    
                    elif strategy == 'combined':
                        # Create a combined result with special handling
                        # This is for custom aggregation logic
                        # For now, default to 'all_matches' behavior
                        all_mapped_ids = []
                        successful_component = None
                        
                        for comp_id in component_ids:
                            result = component_results.get(comp_id)
                            if result and result[0]:  # Not None and not empty list
                                all_mapped_ids.extend(result[0])
                                if not successful_component:
                                    successful_component = result[1]
                        
                        if all_mapped_ids:
                            aggregated_results[original_id] = (all_mapped_ids, successful_component)
                        else:
                            aggregated_results[original_id] = None
                    
                    else:
                        # Unknown strategy, use first_match as default
                        for comp_id in component_ids:
                            result = component_results.get(comp_id)
                            if result and result[0]:  # Not None and not empty list
                                aggregated_results[original_id] = result
                                break
                        else:
                            # No component had a mapping result
                            aggregated_results[original_id] = None
                else:
                    # No pattern config, use first_match as default
                    for comp_id in component_ids:
                        result = component_results.get(comp_id)
                        if result and result[0]:  # Not None and not empty list
                            aggregated_results[original_id] = result
                            break
                    else:
                        # No component had a mapping result
                        aggregated_results[original_id] = None
        
        return aggregated_results
