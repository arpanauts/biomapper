"""
Performance and end-to-end integration tests.

This module contains tests that evaluate system performance, scalability,
and end-to-end functionality across the entire biomapper pipeline.

These tests typically:
- Require external services (API server, databases)
- Run for extended periods (>30 seconds)
- Test with large datasets
- Measure performance metrics

Run with: poetry run pytest tests/performance/
"""