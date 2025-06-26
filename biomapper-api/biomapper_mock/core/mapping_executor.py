"""Mock MappingExecutor"""
from typing import Dict, Any
import pandas as pd


class MappingExecutor:
    """Mock MappingExecutor class"""
    def __init__(self, strategy):
        self.strategy = strategy
    
    def execute(self, data: pd.DataFrame) -> Dict[str, Any]:
        return {"status": "mock", "data": data.to_dict()}