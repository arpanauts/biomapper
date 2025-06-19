"""
IdentifierLoader module for loading identifiers from data endpoints.

This module provides the IdentifierLoader class which handles loading identifiers
from endpoints configured in the metamapper database.
"""

import json
import logging
import os
from typing import List, Union, TYPE_CHECKING
from sqlalchemy.future import select

from biomapper.db.models import Endpoint, EndpointPropertyConfig, PropertyExtractionConfig
from biomapper.core.exceptions import ConfigurationError, DatabaseQueryError
from biomapper.core.utils.placeholder_resolver import resolve_placeholders

if TYPE_CHECKING:
    import pandas as pd


class IdentifierLoader:
    """
    Handles loading identifiers from data endpoints using metamapper.db configurations.
    
    This class is responsible for:
    - Retrieving endpoint configurations from the database
    - Loading data files based on endpoint configuration
    - Extracting identifiers from the appropriate columns
    - Handling different file formats (CSV, TSV)
    """
    
    def __init__(self, metamapper_session_factory):
        """
        Initialize the IdentifierLoader.
        
        Args:
            metamapper_session_factory: Async session factory for metamapper database
        """
        self.metamapper_session_factory = metamapper_session_factory
        self.logger = logging.getLogger(__name__)
    
    async def get_ontology_column(self, endpoint_name: str, ontology_type: str) -> str:
        """
        Get the column name for a given ontology type from an endpoint's property configuration.
        
        Args:
            endpoint_name: Name of the endpoint
            ontology_type: Ontology type to look up (e.g., 'UniProt', 'Gene')
            
        Returns:
            Column name for the ontology type
            
        Raises:
            ConfigurationError: If endpoint, property config, or extraction config not found
            DatabaseQueryError: If there's an error querying the database
        """
        try:
            async with self.metamapper_session_factory() as session:
                # Get the endpoint
                stmt = select(Endpoint).where(Endpoint.name == endpoint_name)
                result = await session.execute(stmt)
                endpoint = result.scalar_one_or_none()
                
                if not endpoint:
                    raise ConfigurationError(f"Endpoint '{endpoint_name}' not found in database")
                
                # Get the property config for the ontology type
                stmt = select(EndpointPropertyConfig).where(
                    EndpointPropertyConfig.endpoint_id == endpoint.id,
                    EndpointPropertyConfig.ontology_type == ontology_type
                )
                result = await session.execute(stmt)
                property_config = result.scalar_one_or_none()
                
                if not property_config:
                    raise ConfigurationError(
                        f"No property configuration found for ontology type '{ontology_type}' "
                        f"in endpoint '{endpoint_name}'"
                    )
                
                # Get the extraction config to find the column name
                stmt = select(PropertyExtractionConfig).where(
                    PropertyExtractionConfig.id == property_config.property_extraction_config_id
                )
                result = await session.execute(stmt)
                extraction_config = result.scalar_one_or_none()
                
                if not extraction_config:
                    raise ConfigurationError(
                        f"No extraction configuration found for property config ID "
                        f"{property_config.property_extraction_config_id}"
                    )
                
                # Parse the extraction pattern to get the column name
                pattern_data = json.loads(extraction_config.extraction_pattern)
                column_name = pattern_data.get('column')
                if not column_name:
                    raise ConfigurationError(
                        f"No 'column' field found in extraction pattern: "
                        f"{extraction_config.extraction_pattern}"
                    )
                return column_name
                
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in extraction pattern: {e}")
        except ConfigurationError:
            raise  # Re-raise configuration errors as-is
        except Exception as e:
            self.logger.error(f"Error getting ontology column: {e}")
            raise DatabaseQueryError(f"Failed to get ontology column: {e}")
    
    async def load_endpoint_identifiers(
        self, 
        endpoint_name: str, 
        ontology_type: str,
        return_dataframe: bool = False
    ) -> Union[List[str], 'pd.DataFrame']:
        """
        Load identifiers from an endpoint using its configuration in metamapper.db.
        
        Args:
            endpoint_name: Name of the endpoint to load from
            ontology_type: Ontology type of the identifiers to load
            return_dataframe: If True, return the full dataframe instead of just identifiers
            
        Returns:
            List of unique identifiers (default) or full DataFrame if return_dataframe=True
            
        Raises:
            ConfigurationError: If endpoint not found or file path issues
            FileNotFoundError: If the data file doesn't exist
            KeyError: If the specified column doesn't exist in the data
            DatabaseQueryError: If there's an error querying the database
        """
        try:
            # First get the column name for the ontology type
            column_name = await self.get_ontology_column(endpoint_name, ontology_type)
            self.logger.info(f"Ontology type '{ontology_type}' maps to column '{column_name}'")
            
            # Get endpoint configuration from metamapper.db
            async with self.metamapper_session_factory() as session:
                stmt = select(Endpoint).where(Endpoint.name == endpoint_name)
                result = await session.execute(stmt)
                endpoint = result.scalar_one_or_none()
                
                if not endpoint:
                    raise ConfigurationError(f"Endpoint '{endpoint_name}' not found in database")
                
                # Parse connection details (it's a JSON string)
                connection_details = json.loads(endpoint.connection_details)
                file_path = connection_details.get('file_path', '')
                delimiter = connection_details.get('delimiter', ',')
                
                # Handle environment variable substitution
                file_path = resolve_placeholders(file_path, {})
                
                self.logger.info(f"Loading identifiers from endpoint '{endpoint_name}'")
                self.logger.info(f"File path: {file_path}")
                
                # Check if file exists
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"Data file not found: {file_path}")
                
                # Lazy import pandas to avoid circular imports
                import pandas as pd
                
                # Load the file
                if endpoint.type == 'file_tsv':
                    df = pd.read_csv(file_path, sep=delimiter)
                elif endpoint.type == 'file_csv':
                    df = pd.read_csv(file_path, sep=delimiter)
                else:
                    raise ConfigurationError(f"Unsupported endpoint type: {endpoint.type}")
                
                self.logger.info(f"Loaded dataframe with shape: {df.shape}")
                
                # Check if column exists
                if column_name not in df.columns:
                    raise KeyError(
                        f"Column '{column_name}' not found in {endpoint_name} data. "
                        f"Available columns: {list(df.columns)}"
                    )
                
                if return_dataframe:
                    return df
                
                # Extract unique identifiers
                identifiers = df[column_name].dropna().unique().tolist()
                self.logger.info(f"Found {len(identifiers)} unique identifiers in column '{column_name}'")
                
                # Log sample of identifiers including any composites
                sample_ids = identifiers[:10]
                composite_count = sum(1 for id in identifiers if '_' in str(id))
                self.logger.info(f"Sample identifiers: {sample_ids}")
                self.logger.info(f"Composite identifiers found: {composite_count} (with '_' delimiter)")
                
                return identifiers
                
        except (ConfigurationError, FileNotFoundError, KeyError):
            raise  # Re-raise these specific errors as-is
        except Exception as e:
            self.logger.error(f"Error loading identifiers from endpoint {endpoint_name}: {e}")
            raise DatabaseQueryError(f"Failed to load endpoint identifiers: {e}")