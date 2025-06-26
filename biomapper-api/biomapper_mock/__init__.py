"""
Minimal mock for biomapper to enable API startup during environment debugging
"""
import pandas as pd


def load_tabular_file(filepath: str, **kwargs) -> pd.DataFrame:
    """Mock implementation of load_tabular_file"""
    return pd.read_csv(filepath, **kwargs)