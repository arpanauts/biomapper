# Endpoint Configuration Health Monitoring System

## Overview

The Endpoint Configuration Health Monitoring System is a comprehensive solution for tracking, analyzing, and improving the health of endpoint property extraction configurations in Biomapper. It provides insights into which extraction patterns are working well and which need improvement, helping to maintain high-quality mapping results.

## Key Components

### 1. Health Tracking

The system automatically tracks property extraction attempts, recording success rates, timing information, and error patterns. This data is stored in a SQLite database and used to assess the health of configurations.

```python
from biomapper.mapping.health.tracker import PropertyHealthTracker

# Record an extraction attempt
with PropertyHealthTracker() as tracker:
    tracker.record_extraction_attempt(
        endpoint_id=1,
        ontology_type="hmdb",
        property_name="HMDB ID",
        success=True,
        execution_time_ms=42,
        error_message=None
    )
```

### 2. Health Monitoring

Regular health checks can be scheduled to proactively identify issues with property extraction configurations. The `EndpointHealthMonitor` runs tests against sample data and updates health metrics.

```python
from biomapper.mapping.health.monitor import EndpointHealthMonitor

# Run a health check
monitor = EndpointHealthMonitor()
results = await monitor.run_health_check(endpoint_id=1)
```

### 3. Health Reporting

The system can generate comprehensive reports on the health of endpoint configurations, highlighting potential issues and areas for improvement.

```python
from biomapper.mapping.health.reporter import HealthReportGenerator, ReportFormatter

# Generate a report
generator = HealthReportGenerator()
report = generator.generate_endpoint_health_report()

# Format as HTML
html_report = ReportFormatter.to_html(report)
```

### 4. Configuration Analysis and Improvement

The system analyzes health data to suggest improvements to problematic configurations.

```python
from biomapper.mapping.health.analyzer import ConfigImprover

# Get improvement suggestions
improver = ConfigImprover()
suggestions = improver.suggest_improvements(endpoint_id=1)
```

### 5. Integration with Existing Systems

The health monitoring system integrates with other Biomapper components, allowing for health-aware mapping operations.

```python
from biomapper.mapping.health.integrations.endpoint_manager import HealthAwareEndpointManager

# Get only healthy ontology preferences
manager = HealthAwareEndpointManager(base_manager)
preferences = manager.get_healthy_ontology_preferences(endpoint_id=1)
```

## Command-Line Interface

The system includes a CLI for running health checks, generating reports, and analyzing configurations:

```bash
# Run a health check
biomapper health check --endpoint 1

# Generate a report
biomapper health report --format html --output report.html

# Analyze configurations and suggest improvements
biomapper health analyze --endpoint 1

# Test a specific configuration
biomapper health test --endpoint 1 --ontology hmdb --property "HMDB ID"
```

## Database Schema

The system uses two main tables:

1. `endpoint_property_health`: Stores health metrics for each property configuration
2. `health_check_logs`: Records the history of health check runs

## Health Metrics

The system tracks the following metrics:

- **Success Rate**: Percentage of successful extraction attempts
- **Avg Extraction Time**: Average time taken for extractions in milliseconds
- **Error Types**: Categorized error patterns that occur during extraction
- **Sample Size**: Number of extraction attempts recorded

## Health Status Classification

Configurations are classified into one of four statuses:

- **Healthy**: Success rate >= 90%
- **At Risk**: Success rate between 50% and 90%
- **Failed**: Success rate < 50%
- **Unknown**: No health data available

## Best Practices

1. **Regular Health Checks**: Run health checks regularly to catch issues early
2. **Review Health Reports**: Review reports to identify patterns of failure
3. **Apply Suggested Improvements**: Implement suggested pattern improvements
4. **Test After Changes**: Always test configurations after making changes

## Future Enhancements

- A/B testing for pattern improvements
- Usage-weighted health scores
- Trend analysis for detecting degrading performance
- Web dashboard for monitoring health metrics