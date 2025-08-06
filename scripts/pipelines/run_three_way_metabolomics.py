#!/usr/bin/env python3
"""
Run three-way metabolomics analysis via Biomapper API.

This simplified client replaces the 97-line strategy service script.
"""
from biomapper_client import run_strategy


if __name__ == "__main__":
    # Execute the three-way metabolomics strategy
    result = run_strategy("THREE_WAY_METABOLOMICS_COMPLETE")
    
    # Exit with appropriate code
    exit(0 if result.get('success') else 1)