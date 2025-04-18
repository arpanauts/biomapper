"""
Health-aware endpoint manager integration for endpoint configurations.

This module provides an extension to the EndpointManager class that is aware
of health metrics and can filter preferences based on configuration health.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Set, Tuple

from sqlalchemy.orm import Session

from biomapper.mapping.health.analyzer import PerformanceClassifier

logger = logging.getLogger(__name__)


class HealthAwareEndpointManager:
    """
    Extension to the EndpointManager that is aware of health metrics.
    
    This class adds health awareness to the EndpointManager, filtering
    preferences based on configuration health and providing health metrics
    alongside endpoint information.
    """
    
    def __init__(self, base_manager: Any, db_session: Optional[Session] = None):
        """
        Initialize the health-aware endpoint manager.
        
        Args:
            base_manager: The base EndpointManager instance
            db_session: Database session (optional)
        """
        self.base_manager = base_manager
        self.db_session = db_session or base_manager.db_session
        
    def get_endpoints(self, parent_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get endpoints with health information.
        
        Args:
            parent_id: Optional parent endpoint ID
            
        Returns:
            List of endpoint dictionaries with health info
        """
        # Get endpoints from base manager
        endpoints = self.base_manager.get_endpoints(parent_id)
        
        # Enrich with health info
        for endpoint in endpoints:
            endpoint_id = endpoint.get("endpoint_id")
            health_info = self._get_endpoint_health(endpoint_id)
            endpoint["health"] = health_info
            
        return endpoints
    
    def get_healthy_ontology_preferences(
        self,
        endpoint_id: int,
        min_success_rate: float = 0.8
    ) -> List[Dict[str, Any]]:
        """
        Get ontology preferences that have healthy configurations.
        
        Args:
            endpoint_id: Endpoint ID
            min_success_rate: Minimum success rate for a config to be considered healthy
            
        Returns:
            List of healthy ontology preferences
        """
        # Get all preferences from base manager
        all_preferences = self.base_manager.get_ontology_preferences(endpoint_id)
        
        # Get health records for this endpoint
        health_records = self._get_health_records_by_endpoint(endpoint_id)
        
        # Filter preferences that have healthy configs
        healthy_preferences = []
        for pref in all_preferences:
            ontology_type = pref.get("ontology_type")
            
            # Check if we have health data for this ontology type
            healthy = False
            for record in health_records:
                if record.ontology_type == ontology_type:
                    success_rate = record.success_rate
                    if success_rate >= min_success_rate:
                        healthy = True
                        break
            
            # Only include healthy preferences
            if healthy:
                healthy_preferences.append(pref)
                
        return healthy_preferences
    
    def get_property_configs_with_health(
        self,
        endpoint_id: int,
        ontology_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get property configurations with health information.
        
        Args:
            endpoint_id: Endpoint ID
            ontology_type: Optional ontology type to filter by
            
        Returns:
            List of property configs with health info
        """
        # Get configs from base manager
        configs = self.base_manager.get_property_configs(endpoint_id, ontology_type)
        
        # Get health records for this endpoint
        health_records = self._get_health_records_by_endpoint(endpoint_id)
        
        # Create a mapping of config to health record
        health_by_config = {}
        for record in health_records:
            key = (record.ontology_type, record.property_name)
            health_by_config[key] = record
            
        # Enrich configs with health info
        for config in configs:
            ontology = config.get("ontology_type")
            property_name = config.get("property_name")
            key = (ontology, property_name)
            
            if key in health_by_config:
                record = health_by_config[key]
                
                # Add health info
                config["health"] = {
                    "success_rate": record.success_rate,
                    "status": PerformanceClassifier.classify_config(record),
                    "sample_size": record.sample_size,
                    "avg_extraction_time_ms": record.avg_extraction_time_ms,
                    "error_types": record.error_types_list if hasattr(record, "error_types_list") else []
                }
            else:
                config["health"] = {
                    "status": "unknown",
                    "success_rate": None,
                    "sample_size": 0
                }
                
        return configs
    
    def get_property_extraction_patterns(
        self,
        endpoint_id: int,
        ontology_type: Optional[str] = None,
        min_success_rate: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Get property extraction patterns, optionally filtered by health.
        
        Args:
            endpoint_id: Endpoint ID
            ontology_type: Optional ontology type to filter by
            min_success_rate: Optional minimum success rate to filter by
            
        Returns:
            List of property extraction patterns
        """
        # Get configs with health info
        configs = self.get_property_configs_with_health(endpoint_id, ontology_type)
        
        # Filter by success rate if specified
        if min_success_rate is not None:
            configs = [
                config for config in configs
                if config.get("health", {}).get("success_rate", 0) >= min_success_rate
            ]
            
        return configs
    
    def _get_endpoint_health(self, endpoint_id: int) -> Dict[str, Any]:
        """Get health information for an endpoint."""
        # Get health records for this endpoint
        health_records = self._get_health_records_by_endpoint(endpoint_id)
        
        if not health_records:
            return {
                "status": "unknown",
                "configs_count": 0,
                "success_rate": None,
                "sample_size": 0
            }
            
        # Calculate overall health
        total_success = sum(r.extraction_success_count for r in health_records)
        total_failure = sum(r.extraction_failure_count for r in health_records)
        total = total_success + total_failure
        
        if total == 0:
            success_rate = None
        else:
            success_rate = total_success / total
        
        # Classify overall status
        if success_rate is None:
            status = "unknown"
        elif success_rate >= 0.9:
            status = "healthy"
        elif success_rate >= 0.5:
            status = "at_risk"
        else:
            status = "failed"
            
        # Count configs by status
        status_counts = {"healthy": 0, "at_risk": 0, "failed": 0, "unknown": 0}
        for record in health_records:
            config_status = PerformanceClassifier.classify_config(record)
            status_counts[config_status] += 1
            
        return {
            "status": status,
            "configs_count": len(health_records),
            "success_rate": success_rate,
            "sample_size": total,
            "status_counts": status_counts
        }
    
    def _get_health_records_by_endpoint(self, endpoint_id: int) -> List[Any]:
        """Get health records for an endpoint."""
        return self.db_session.execute(
            "SELECT * FROM endpoint_property_health WHERE endpoint_id = :id",
            {"id": endpoint_id}
        ).fetchall()
        

class ValidPreferenceSelector:
    """
    Utility for selecting valid preferences based on health.
    
    This class helps select ontology preferences that have healthy configurations,
    ensuring that mapping paths only use configurations that are likely to work.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize the preference selector.
        
        Args:
            db_session: Database session
        """
        self.db_session = db_session
        
    def get_valid_preferences(
        self,
        endpoint_id: int,
        min_success_rate: float = 0.8,
        min_sample_size: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get valid ontology preferences based on health metrics.
        
        Args:
            endpoint_id: Endpoint ID
            min_success_rate: Minimum success rate for a preference to be valid
            min_sample_size: Minimum sample size for health metrics to be considered
            
        Returns:
            List of valid preferences
        """
        try:
            # Get all preferences
            preferences = self.db_session.execute(
                """SELECT op.*, e.name as endpoint_name 
                   FROM endpoint_ontology_preferences op
                   JOIN endpoints e ON op.endpoint_id = e.endpoint_id
                   WHERE op.endpoint_id = :id
                   ORDER BY op.preference_level DESC""",
                {"id": endpoint_id}
            ).fetchall()
            
            if not preferences:
                logger.info(f"No preferences found for endpoint {endpoint_id}")
                return []
                
            # Get health records
            health_records = self.db_session.execute(
                """SELECT * FROM endpoint_property_health
                   WHERE endpoint_id = :id""",
                {"id": endpoint_id}
            ).fetchall()
            
            # Create a map of ontology type to health record
            health_by_ontology = {}
            for record in health_records:
                if record.ontology_type not in health_by_ontology:
                    health_by_ontology[record.ontology_type] = []
                health_by_ontology[record.ontology_type].append(record)
                
            # Filter preferences based on health
            valid_preferences = []
            for pref in preferences:
                ontology_type = pref.ontology_type
                
                # If we have no health data, include the preference
                if ontology_type not in health_by_ontology:
                    valid_preferences.append({
                        "endpoint_id": pref.endpoint_id,
                        "endpoint_name": pref.endpoint_name,
                        "ontology_type": pref.ontology_type,
                        "preference_level": pref.preference_level,
                        "health": {
                            "status": "unknown",
                            "success_rate": None,
                            "sample_size": 0
                        }
                    })
                    continue
                    
                # Calculate overall success rate for this ontology type
                records = health_by_ontology[ontology_type]
                total_success = sum(r.extraction_success_count for r in records)
                total_failure = sum(r.extraction_failure_count for r in records)
                total = total_success + total_failure
                
                # Skip if we don't have enough samples
                if total < min_sample_size:
                    valid_preferences.append({
                        "endpoint_id": pref.endpoint_id,
                        "endpoint_name": pref.endpoint_name,
                        "ontology_type": pref.ontology_type,
                        "preference_level": pref.preference_level,
                        "health": {
                            "status": "unknown",
                            "success_rate": total_success / total if total > 0 else None,
                            "sample_size": total
                        }
                    })
                    continue
                    
                # Check success rate
                success_rate = total_success / total if total > 0 else 0
                if success_rate >= min_success_rate:
                    valid_preferences.append({
                        "endpoint_id": pref.endpoint_id,
                        "endpoint_name": pref.endpoint_name,
                        "ontology_type": pref.ontology_type,
                        "preference_level": pref.preference_level,
                        "health": {
                            "status": "healthy",
                            "success_rate": success_rate,
                            "sample_size": total
                        }
                    })
                    
            return valid_preferences
            
        except Exception as e:
            logger.error(f"Error getting valid preferences: {e}")
            return []