#!/usr/bin/env python3
"""Test script to verify JSON logging from main branch."""

import logging
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

from app.core.logging_config import configure_logging

# Configure logging
configure_logging()

# Get logger
logger = logging.getLogger("app.main")

# Test logging
print("Testing JSON logging from main branch:")
print("-" * 60)

logger.info("Testing structured logging from main branch")
logger.warning("This is a warning message", extra={"branch": "main", "test": True})
logger.error("Error with context", extra={"user_id": 456, "action": "test_from_main"})

# Test exception
try:
    1 / 0
except Exception as e:
    logger.error("Exception in main branch test", exc_info=True)

print("-" * 60)
print("JSON logging test completed successfully!")