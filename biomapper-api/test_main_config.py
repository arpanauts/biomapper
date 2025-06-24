#!/usr/bin/env python3
"""Test configuration from main branch"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.core.config import settings
    print("✓ Settings loaded successfully from main branch!")
    print(f"  - Project Name: {settings.PROJECT_NAME}")
    print(f"  - Debug Mode: {settings.DEBUG}")
    print(f"  - API Prefix: {settings.API_V1_PREFIX}")
    print(f"  - Upload Dir: {settings.UPLOAD_DIR}")
    print(f"  - Strategies Dir: {settings.STRATEGIES_DIR}")
    print(f"  - Max Upload Size: {settings.MAX_UPLOAD_SIZE / (1024*1024*1024):.2f} GB")
    print("\nAll configuration working correctly on main branch!")
except Exception as e:
    print(f"✗ Error loading settings: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)