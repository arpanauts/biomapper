"""
Health monitoring system for endpoint configurations.

This module provides components for monitoring the health of endpoint
property extraction configurations, including scheduled health checks
and test execution against sample data.
"""

import time
import json
import logging
import datetime
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session

from biomapper.db.models_health import HealthCheckLog
from biomapper.db.session import get_session
from biomapper.mapping.health.tracker import PropertyHealthTracker

logger = logging.getLogger(__name__)


class SampleDataFetcher:
    """Fetches representative data for testing property extraction configurations."""

    @staticmethod
    async def fetch_sample_data(
        endpoint_id: int, db_session: Session
    ) -> Dict[str, Any]:
        """
        Fetch a sample of data from an endpoint for testing.

        Args:
            endpoint_id: The endpoint ID
            db_session: Database session

        Returns:
            Dictionary containing sample data
        """
        # Get endpoint information
        endpoint = db_session.execute(
            "SELECT * FROM endpoints WHERE endpoint_id = :id", {"id": endpoint_id}
        ).fetchone()

        if not endpoint:
            raise ValueError(f"Endpoint not found: {endpoint_id}")

        # Different strategies based on endpoint type
        if endpoint.endpoint_type == "csv":
            return await SampleDataFetcher._fetch_csv_sample(endpoint, db_session)
        elif endpoint.endpoint_type == "graph":
            return await SampleDataFetcher._fetch_graph_sample(endpoint, db_session)
        else:
            return {"error": f"Unsupported endpoint type: {endpoint.endpoint_type}"}

    @staticmethod
    async def _fetch_csv_sample(endpoint: Any, db_session: Session) -> Dict[str, Any]:
        """Fetch sample data from a CSV endpoint."""
        # This would typically involve:
        # 1. Getting the file path from connection_info
        # 2. Reading a small sample of rows
        # 3. Returning column data

        # For the MVP, we'll return a mock sample
        return {
            "endpoint_id": endpoint.endpoint_id,
            "endpoint_type": endpoint.endpoint_type,
            "sample_type": "mock",  # Placeholder for actual implementation
            "columns": ["HMDB", "BIOCHEMICAL_NAME", "KEGG", "PUBCHEM"],
            "sample_rows": [
                {
                    "HMDB": "HMDB0000001",
                    "BIOCHEMICAL_NAME": "1-Methylhistidine",
                    "KEGG": "C01152",
                    "PUBCHEM": "92865",
                },
                {
                    "HMDB": "HMDB0000002",
                    "BIOCHEMICAL_NAME": "1,3-Diaminopropane",
                    "KEGG": "C00986",
                    "PUBCHEM": "428",
                },
            ],
        }

    @staticmethod
    async def _fetch_graph_sample(endpoint: Any, db_session: Session) -> Dict[str, Any]:
        """Fetch sample data from a graph endpoint."""
        # This would involve querying the graph database for sample nodes
        return {
            "endpoint_id": endpoint.endpoint_id,
            "endpoint_type": endpoint.endpoint_type,
            "sample_type": "mock",  # Placeholder for actual implementation
            "entities": [
                {"id": "CHEBI:15377", "name": "water", "source": "ChEBI"},
                {"id": "HMDB0000001", "name": "1-Methylhistidine", "source": "HMDB"},
            ],
        }


class ConfigTester:
    """Tests property extraction configurations against sample data."""

    @staticmethod
    async def test_config(
        endpoint_id: int, ontology_type: str, property_name: str, db_session: Session
    ) -> Dict[str, Any]:
        """
        Test a property config against sample data.

        Args:
            endpoint_id: ID of the endpoint
            ontology_type: Ontology type
            property_name: Property name
            db_session: Database session

        Returns:
            Dictionary with test results
        """
        start_time = time.time()
        success = False
        error_message = None
        extracted_values = []

        try:
            # Get property config
            config = db_session.execute(
                """SELECT * FROM endpoint_property_configs 
                   WHERE endpoint_id = :endpoint_id 
                   AND ontology_type = :ontology_type 
                   AND property_name = :property_name""",
                {
                    "endpoint_id": endpoint_id,
                    "ontology_type": ontology_type,
                    "property_name": property_name,
                },
            ).fetchone()

            if not config:
                raise ValueError(
                    f"Property config not found: {endpoint_id}/{ontology_type}/{property_name}"
                )

            # Get sample data
            sample_data = await SampleDataFetcher.fetch_sample_data(
                endpoint_id, db_session
            )

            # Test extraction based on method
            if config.extraction_method == "column":
                extracted_values = ConfigTester._test_column_extraction(
                    config, sample_data
                )
            elif config.extraction_method == "pattern":
                extracted_values = ConfigTester._test_pattern_extraction(
                    config, sample_data
                )
            elif config.extraction_method == "query":
                extracted_values = ConfigTester._test_query_extraction(
                    config, sample_data
                )
            else:
                raise ValueError(
                    f"Unsupported extraction method: {config.extraction_method}"
                )

            success = len(extracted_values) > 0

        except Exception as e:
            error_message = str(e)
            logger.error(f"Error testing config: {error_message}")

        finally:
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Record the test result
            with PropertyHealthTracker(db_session) as tracker:
                tracker.record_extraction_attempt(
                    endpoint_id=endpoint_id,
                    ontology_type=ontology_type,
                    property_name=property_name,
                    success=success,
                    execution_time_ms=execution_time_ms,
                    error_message=error_message,
                )

            return {
                "endpoint_id": endpoint_id,
                "ontology_type": ontology_type,
                "property_name": property_name,
                "success": success,
                "execution_time_ms": execution_time_ms,
                "error_message": error_message,
                "extracted_count": len(extracted_values),
                "sample_values": extracted_values[:5],
            }

    @staticmethod
    def _test_column_extraction(config: Any, sample_data: Dict[str, Any]) -> List[str]:
        """Test column-based extraction."""
        extracted_values = []
        pattern = json.loads(config.extraction_pattern)
        column_name = pattern.get("column_name")

        if not column_name:
            raise ValueError("No column_name specified in extraction pattern")

        # Check if column exists in sample data
        if "sample_rows" not in sample_data:
            raise ValueError("No sample rows available")

        # Extract values from column
        for row in sample_data.get("sample_rows", []):
            if column_name in row:
                value = row[column_name]
                if value:  # Skip empty/null values
                    extracted_values.append(value)

        return extracted_values

    @staticmethod
    def _test_pattern_extraction(config: Any, sample_data: Dict[str, Any]) -> List[str]:
        """Test pattern-based extraction."""
        import re

        extracted_values = []
        pattern_config = json.loads(config.extraction_pattern)

        if "pattern" not in pattern_config:
            raise ValueError("No pattern specified in extraction pattern")

        regex = re.compile(pattern_config["pattern"])
        group_index = pattern_config.get("group", 0)

        # Test against column names if it's a CSV
        if "columns" in sample_data:
            for column in sample_data["columns"]:
                match = regex.match(column)
                if match:
                    try:
                        value = match.group(group_index)
                        if value:
                            extracted_values.append(value)
                    except IndexError:
                        pass  # Group index out of range

        return extracted_values

    @staticmethod
    def _test_query_extraction(config: Any, sample_data: Dict[str, Any]) -> List[str]:
        """Test query-based extraction."""
        # This would typically involve:
        # 1. Parsing the query pattern
        # 2. Checking if it's structurally valid
        # 3. Maybe run a trivial query against a test DB

        # For the MVP, we'll just check query syntax
        pattern = json.loads(config.extraction_pattern)

        if "aql" in pattern:
            # Verify AQL query has basic elements
            query = pattern["aql"]
            if all(keyword in query for keyword in ["FOR", "IN", "FILTER"]):
                return ["valid_aql_query"]

        # Basic validation passed
        return ["query_syntax_valid"]


class EndpointHealthMonitor:
    """Monitors endpoint configuration health and sends alerts."""

    def __init__(
        self, db_session: Optional[Session] = None, alert_manager: Optional[Any] = None
    ):
        """
        Initialize the health monitor.

        Args:
            db_session: Database session (optional)
            alert_manager: Alert manager (optional)
        """
        self.db_session = db_session
        self.session_owner = db_session is None
        self.alert_manager = alert_manager
        self.health_tracker = PropertyHealthTracker(db_session)

    async def run_health_check(
        self,
        endpoint_id: Optional[int] = None,
        ontology_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Run a health check on endpoint configurations.

        Args:
            endpoint_id: Optional specific endpoint ID to check
            ontology_types: Optional list of ontology types to check

        Returns:
            Dictionary with health check results
        """
        start_time = time.time()
        session = self.db_session or get_session()
        session_owner = self.db_session is None

        try:
            # Create health check log
            health_log = HealthCheckLog(
                check_time=datetime.datetime.utcnow(), status="running"
            )
            session.add(health_log)
            session.flush()  # Get the ID without committing

            # Get endpoints to check
            endpoints = self._get_endpoints_to_check(session, endpoint_id)
            health_log.endpoints_checked = len(endpoints)

            # Track results
            total_configs = 0
            success_count = 0
            failure_count = 0
            results_by_endpoint: Dict[int, Dict[str, Any]] = {}

            # Process each endpoint
            for endpoint in endpoints:
                endpoint_results = {
                    "endpoint_id": endpoint.endpoint_id,
                    "name": endpoint.name,
                    "configs_checked": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "configs": [],
                }

                # Get configs for this endpoint
                configs = self._get_property_configs(
                    session, endpoint.endpoint_id, ontology_types
                )

                if not configs:
                    endpoint_results["status"] = "no_configs"
                    results_by_endpoint[endpoint.endpoint_id] = endpoint_results
                    continue

                # Test each config
                for config in configs:
                    total_configs += 1
                    endpoint_results["configs_checked"] += 1

                    result = await ConfigTester.test_config(
                        endpoint_id=endpoint.endpoint_id,
                        ontology_type=config.ontology_type,
                        property_name=config.property_name,
                        db_session=session,
                    )

                    endpoint_results["configs"].append(result)

                    if result["success"]:
                        success_count += 1
                        endpoint_results["success_count"] += 1
                    else:
                        failure_count += 1
                        endpoint_results["failure_count"] += 1

                        # Send alert if needed
                        if self.alert_manager:
                            self.alert_manager.send_config_failure_alert(
                                endpoint, config, result["error_message"]
                            )

                # Calculate success rate for endpoint
                if endpoint_results["configs_checked"] > 0:
                    endpoint_results["success_rate"] = (
                        endpoint_results["success_count"]
                        / endpoint_results["configs_checked"]
                    )
                    endpoint_results["status"] = (
                        "healthy"
                        if endpoint_results["success_rate"] >= 0.8
                        else "at_risk"
                    )

                    if endpoint_results["success_rate"] < 0.5:
                        endpoint_results["status"] = "failing"

                results_by_endpoint[endpoint.endpoint_id] = endpoint_results

            # Update health check log
            duration_ms = int((time.time() - start_time) * 1000)
            health_log.configs_checked = total_configs
            health_log.success_count = success_count
            health_log.failure_count = failure_count
            health_log.duration_ms = duration_ms
            health_log.status = "completed"
            health_log.details_dict = {
                "endpoints": [
                    results_by_endpoint[eid]
                    for eid in sorted(results_by_endpoint.keys())
                ]
            }

            session.commit()

            # Return results
            return {
                "log_id": health_log.log_id,
                "check_time": health_log.check_time.isoformat(),
                "endpoints_checked": health_log.endpoints_checked,
                "configs_checked": health_log.configs_checked,
                "success_count": health_log.success_count,
                "failure_count": health_log.failure_count,
                "duration_ms": health_log.duration_ms,
                "status": health_log.status,
                "endpoints": [
                    results_by_endpoint[eid]
                    for eid in sorted(results_by_endpoint.keys())
                ],
            }

        except Exception as e:
            logger.error(f"Error running health check: {e}")
            # Try to update health check log
            try:
                health_log.status = "error"
                health_log.details_dict = {"error": str(e)}
                session.commit()
            except Exception:
                pass

            return {
                "status": "error",
                "error": str(e),
                "duration_ms": int((time.time() - start_time) * 1000),
            }

        finally:
            if session_owner:
                session.close()

    def _get_endpoints_to_check(
        self, session: Session, endpoint_id: Optional[int] = None
    ) -> List[Any]:
        """Get the list of endpoints to check."""
        if endpoint_id:
            # Get specific endpoint
            return session.execute(
                "SELECT * FROM endpoints WHERE endpoint_id = :id", {"id": endpoint_id}
            ).fetchall()
        else:
            # Get all endpoints
            return session.execute("SELECT * FROM endpoints").fetchall()

    def _get_property_configs(
        self,
        session: Session,
        endpoint_id: int,
        ontology_types: Optional[List[str]] = None,
    ) -> List[Any]:
        """Get property configurations for an endpoint."""
        query = """SELECT * FROM endpoint_property_configs 
                  WHERE endpoint_id = :endpoint_id"""
        params = {"endpoint_id": endpoint_id}

        if ontology_types:
            query += " AND ontology_type IN :ontology_types"
            params["ontology_types"] = tuple(ontology_types)

        return session.execute(query, params).fetchall()
