"""
Health analysis system for endpoint configurations.

This module provides components for analyzing health data and suggesting
improvements to endpoint property extraction configurations.
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Union, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from biomapper.db.models_health import EndpointPropertyHealth
from biomapper.db.session import get_session

logger = logging.getLogger(__name__)


class PerformanceClassifier:
    """Classifies property configurations by performance."""
    
    @staticmethod
    def classify_config(health_record: EndpointPropertyHealth) -> str:
        """
        Classify a config's health status.
        
        Args:
            health_record: Health record for the config
            
        Returns:
            Status string: "healthy", "at_risk", or "failed"
        """
        # Calculate success rate
        total = health_record.extraction_success_count + health_record.extraction_failure_count
        if total == 0:
            return "unknown"  # No data
            
        success_rate = health_record.extraction_success_count / total
        
        if success_rate >= 0.9:
            return "healthy"
        elif success_rate >= 0.5:
            return "at_risk"
        else:
            return "failed"
    
    @staticmethod
    def get_health_summary(db_session: Session) -> Dict[str, Any]:
        """
        Get a summary of health statuses across all configurations.
        
        Args:
            db_session: Database session
            
        Returns:
            Summary statistics
        """
        try:
            # Get all health records
            records = db_session.query(EndpointPropertyHealth).all()
            
            stats = {
                "total": len(records),
                "healthy": 0,
                "at_risk": 0,
                "failed": 0,
                "unknown": 0
            }
            
            # Classify each record
            for record in records:
                status = PerformanceClassifier.classify_config(record)
                stats[status] += 1
                
            # Calculate percentages
            if stats["total"] > 0:
                for key in ["healthy", "at_risk", "failed", "unknown"]:
                    stats[f"{key}_percent"] = round(stats[key] / stats["total"] * 100, 1)
                    
            return stats
                
        except Exception as e:
            logger.error(f"Error getting health summary: {e}")
            return {
                "error": str(e),
                "total": 0,
                "healthy": 0,
                "at_risk": 0,
                "failed": 0,
                "unknown": 0
            }


class PatternAnalyzer:
    """Analyzes extraction patterns to identify weaknesses."""
    
    @staticmethod
    def analyze_pattern(
        pattern_json: str,
        extraction_method: str,
        common_errors: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze an extraction pattern for potential issues.
        
        Args:
            pattern_json: JSON string containing the pattern
            extraction_method: Extraction method (column, pattern, etc.)
            common_errors: List of common error types
            
        Returns:
            Dictionary with analysis results
        """
        try:
            pattern = json.loads(pattern_json)
            issues = []
            
            # Analyze based on extraction method
            if extraction_method == "column":
                issues.extend(PatternAnalyzer._analyze_column_pattern(pattern, common_errors))
            elif extraction_method == "pattern":
                issues.extend(PatternAnalyzer._analyze_regex_pattern(pattern, common_errors))
            elif extraction_method == "query":
                issues.extend(PatternAnalyzer._analyze_query_pattern(pattern, common_errors))
                
            return {
                "extraction_method": extraction_method,
                "pattern": pattern,
                "issues": issues,
                "issue_count": len(issues),
                "has_issues": len(issues) > 0
            }
                
        except json.JSONDecodeError:
            return {
                "extraction_method": extraction_method,
                "pattern": pattern_json,
                "issues": ["Invalid JSON format in pattern"],
                "issue_count": 1,
                "has_issues": True
            }
            
        except Exception as e:
            logger.error(f"Error analyzing pattern: {e}")
            return {
                "extraction_method": extraction_method,
                "pattern": pattern_json,
                "issues": [f"Error analyzing pattern: {str(e)}"],
                "issue_count": 1,
                "has_issues": True
            }
    
    @staticmethod
    def _analyze_column_pattern(pattern: Dict[str, Any], common_errors: List[str]) -> List[str]:
        """Analyze a column-based extraction pattern."""
        issues = []
        
        # Check if column_name is specified
        if "column_name" not in pattern:
            issues.append("No column_name specified in pattern")
            return issues
            
        column_name = pattern["column_name"]
        
        # Check if column_name is empty
        if not column_name:
            issues.append("Empty column_name in pattern")
            
        # Check for common errors
        if "missing_column" in common_errors:
            issues.append(f"Column '{column_name}' not found in data")
            
        return issues
    
    @staticmethod
    def _analyze_regex_pattern(pattern: Dict[str, Any], common_errors: List[str]) -> List[str]:
        """Analyze a regex-based extraction pattern."""
        issues = []
        
        # Check if pattern is specified
        if "pattern" not in pattern:
            issues.append("No regex pattern specified")
            return issues
            
        regex = pattern["pattern"]
        
        # Check if pattern is empty
        if not regex:
            issues.append("Empty regex pattern")
            return issues
            
        # Check regex syntax
        try:
            re.compile(regex)
        except re.error as e:
            issues.append(f"Invalid regex syntax: {str(e)}")
            return issues
            
        # Check for common regex issues
        if regex.startswith("^") and regex.endswith("$") and "*" not in regex and "+" not in regex:
            issues.append("Strict pattern (^...$) without wildcards may be too restrictive")
            
        if "group" in pattern and not any(c in regex for c in "()"):
            issues.append("Group specified but no capture groups in pattern")
            
        # Check for common errors
        if "pattern_syntax" in common_errors:
            issues.append("Pattern syntax errors reported during extraction")
            
        if "no_match" in common_errors:
            issues.append("Pattern doesn't match data")
            
        return issues
    
    @staticmethod
    def _analyze_query_pattern(pattern: Dict[str, Any], common_errors: List[str]) -> List[str]:
        """Analyze a query-based extraction pattern."""
        issues = []
        
        # Check if query is specified
        has_query = False
        query_key = None
        query = None
        
        for key in ["aql", "cypher", "sql", "query"]:
            if key in pattern:
                has_query = True
                query_key = key
                query = pattern[key]
                break
                
        if not has_query:
            issues.append("No query specified in pattern")
            return issues
            
        # Check if query is empty
        if not query:
            issues.append(f"Empty {query_key} query")
            return issues
            
        # Basic query analysis based on type
        if query_key == "aql":
            if not any(keyword in query for keyword in ["FOR", "IN", "FILTER"]):
                issues.append("AQL query missing required keywords (FOR, IN, FILTER)")
                
            # Check parameter syntax
            if "@" not in query and "FILTER" in query:
                issues.append("AQL query uses FILTER but no bind parameters (@...)")
                
        elif query_key == "cypher":
            if not any(keyword in query for keyword in ["MATCH", "WHERE"]):
                issues.append("Cypher query missing required keywords (MATCH, WHERE)")
                
            # Check parameter syntax
            if "$" not in query and "WHERE" in query:
                issues.append("Cypher query uses WHERE but no bind parameters ($...)")
                
        # Check for common errors
        if "connection_error" in common_errors:
            issues.append("Connection errors reported during query execution")
            
        return issues


class ConfigImprover:
    """Suggests improvements to property configurations based on health data."""
    
    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize the config improver.
        
        Args:
            db_session: Database session (optional)
        """
        self.db_session = db_session
        self.session_owner = db_session is None
    
    def suggest_improvements(self, endpoint_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Generate suggestions to improve extraction configurations.
        
        Args:
            endpoint_id: Optional specific endpoint ID to analyze
            
        Returns:
            List of suggested improvements
        """
        session = self.db_session or get_session()
        session_owner = self.db_session is None
        
        try:
            # Get health data
            health_data = self._get_health_data(session, endpoint_id)
            
            suggestions = []
            for health_record in health_data:
                # Skip healthy configs
                success_rate = health_record.success_rate
                if success_rate >= 0.9:
                    continue
                    
                # Get property config
                config = self._get_property_config(
                    session,
                    health_record.endpoint_id,
                    health_record.ontology_type,
                    health_record.property_name
                )
                
                if not config:
                    continue
                    
                # Parse error types
                error_types = []
                if health_record.extraction_error_types:
                    try:
                        error_types = json.loads(health_record.extraction_error_types)
                    except json.JSONDecodeError:
                        error_types = []
                        
                # Analyze pattern
                analysis = PatternAnalyzer.analyze_pattern(
                    config.extraction_pattern,
                    config.extraction_method,
                    error_types
                )
                
                # No issues detected
                if not analysis["has_issues"]:
                    continue
                    
                # Generate improvement suggestion
                suggestion = self._generate_suggestion(
                    config,
                    health_record,
                    analysis
                )
                
                if suggestion:
                    suggestions.append(suggestion)
                    
            return suggestions
            
        except SQLAlchemyError as e:
            logger.error(f"Database error suggesting improvements: {e}")
            return [{"error": f"Database error: {str(e)}"}]
            
        except Exception as e:
            logger.error(f"Error suggesting improvements: {e}")
            return [{"error": str(e)}]
            
        finally:
            if session_owner:
                session.close()
    
    def _get_health_data(
        self,
        session: Session,
        endpoint_id: Optional[int] = None
    ) -> List[EndpointPropertyHealth]:
        """Get health records for analysis."""
        query = session.query(EndpointPropertyHealth)
        
        if endpoint_id:
            query = query.filter(EndpointPropertyHealth.endpoint_id == endpoint_id)
            
        return query.all()
    
    def _get_property_config(
        self,
        session: Session,
        endpoint_id: int,
        ontology_type: str,
        property_name: str
    ) -> Optional[Any]:
        """Get property configuration."""
        config = session.execute(
            """SELECT * FROM endpoint_property_configs 
               WHERE endpoint_id = :endpoint_id 
               AND ontology_type = :ontology_type 
               AND property_name = :property_name""",
            {
                "endpoint_id": endpoint_id,
                "ontology_type": ontology_type,
                "property_name": property_name
            }
        ).fetchone()
        
        return config
    
    def _generate_suggestion(
        self,
        config: Any,
        health_record: EndpointPropertyHealth,
        analysis: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Generate improvement suggestion based on analysis."""
        pattern = json.loads(config.extraction_pattern)
        
        # Base suggestion
        suggestion = {
            "endpoint_id": config.endpoint_id,
            "ontology_type": config.ontology_type,
            "property_name": config.property_name,
            "extraction_method": config.extraction_method,
            "current_pattern": pattern,
            "issues": analysis["issues"],
            "suggested_pattern": None,
            "reason": ", ".join(analysis["issues"]),
            "confidence": 0.5  # Default confidence
        }
        
        # Generate suggestion based on extraction method
        if config.extraction_method == "column":
            suggested_pattern = self._suggest_column_pattern(pattern, analysis["issues"])
            if suggested_pattern:
                suggestion["suggested_pattern"] = suggested_pattern
                suggestion["confidence"] = 0.7
                
        elif config.extraction_method == "pattern":
            suggested_pattern = self._suggest_regex_pattern(pattern, analysis["issues"])
            if suggested_pattern:
                suggestion["suggested_pattern"] = suggested_pattern
                suggestion["confidence"] = 0.6
                
        elif config.extraction_method == "query":
            suggested_pattern = self._suggest_query_pattern(pattern, analysis["issues"])
            if suggested_pattern:
                suggestion["suggested_pattern"] = suggested_pattern
                suggestion["confidence"] = 0.6
        
        # Return only if there's a suggested pattern
        if suggestion["suggested_pattern"]:
            return suggestion
        return None
    
    def _suggest_column_pattern(
        self,
        pattern: Dict[str, Any],
        issues: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Suggest improvement for column pattern."""
        # Copy the pattern to avoid modifying the original
        suggested = pattern.copy()
        
        # Attempt to fix common issues
        for issue in issues:
            if "Column not found" in issue:
                # Suggest checking similar column names
                original = pattern.get("column_name", "")
                if original:
                    suggested["column_name"] = original
                    suggested["comment"] = "Check if this column name is correct. Consider similar names like: " + \
                                          f"'{original.upper()}', '{original.lower()}', '{original.replace('_', '')}'."
                return suggested
        
        return None
    
    def _suggest_regex_pattern(
        self,
        pattern: Dict[str, Any],
        issues: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Suggest improvement for regex pattern."""
        # Copy the pattern to avoid modifying the original
        suggested = pattern.copy()
        original = pattern.get("pattern", "")
        
        # Attempt to fix common issues
        for issue in issues:
            if "too restrictive" in issue:
                # Make pattern less restrictive
                if original.startswith("^") and original.endswith("$"):
                    suggested["pattern"] = original[1:-1]  # Remove ^ and $
                    suggested["comment"] = "Removed strict anchors (^ and $) to make the pattern more flexible."
                    return suggested
                    
            elif "no capture groups" in issue:
                # Add a capture group if there's no grouping
                if "(" not in original and ")" not in original:
                    suggested["pattern"] = f"({original})"
                    suggested["comment"] = "Added capture group around the entire pattern."
                    return suggested
                    
            elif "doesn't match" in issue:
                # Make pattern more general
                if original.startswith("^") and original.endswith("$"):
                    suggested["pattern"] = original[1:-1]
                    suggested["comment"] = "Removed strict anchors to improve matching."
                    return suggested
                elif not original.startswith(".*") and not original.endswith(".*"):
                    suggested["pattern"] = f".*{original}.*"
                    suggested["comment"] = "Added wildcards before and after to improve matching."
                    return suggested
        
        return None
    
    def _suggest_query_pattern(
        self,
        pattern: Dict[str, Any],
        issues: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Suggest improvement for query pattern."""
        # Copy the pattern to avoid modifying the original
        suggested = pattern.copy()
        
        # Determine query type
        query_key = None
        for key in ["aql", "cypher", "sql", "query"]:
            if key in pattern:
                query_key = key
                break
                
        if not query_key:
            return None
            
        original = pattern.get(query_key, "")
        
        # Attempt to fix common issues
        for issue in issues:
            if "no bind parameters" in issue and query_key == "aql":
                # Fix parameter syntax for AQL
                if "==" in original and "@" not in original:
                    suggested[query_key] = original.replace("==", "== @")
                    suggested["comment"] = "Fixed parameter binding syntax for AQL."
                    return suggested
                    
            elif "no bind parameters" in issue and query_key == "cypher":
                # Fix parameter syntax for Cypher
                if "=" in original and "$" not in original:
                    suggested[query_key] = original.replace("=", "= $")
                    suggested["comment"] = "Fixed parameter binding syntax for Cypher."
                    return suggested
        
        return None