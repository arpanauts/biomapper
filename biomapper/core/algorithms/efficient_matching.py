"""Efficient matching algorithms to replace O(n*m) nested loops."""

from typing import List, Dict, Tuple, Callable, Any, Optional, Set
from collections import defaultdict
import pandas as pd
import numpy as np
from dataclasses import dataclass
import hashlib


@dataclass
class MatchResult:
    """Result of a matching operation."""
    
    source_item: Any
    target_item: Any
    match_score: float = 1.0
    match_type: str = "exact"


class EfficientMatcher:
    """Provides efficient O(n) and O(n log n) matching algorithms."""
    
    @staticmethod
    def build_index(items: List[Any], key_func: Callable[[Any], str]) -> Dict[str, List[Any]]:
        """
        Build an index for O(1) lookups.
        
        Args:
            items: List of items to index
            key_func: Function to extract key from each item
            
        Returns:
            Dictionary mapping keys to lists of items
            
        Time Complexity: O(n) where n = len(items)
        Space Complexity: O(n)
        """
        index = defaultdict(list)
        for item in items:
            key = key_func(item)
            if key is not None and key != '':
                index[key].append(item)
        return dict(index)
    
    @staticmethod
    def match_with_index(
        source: List[Any], 
        target_index: Dict[str, List[Any]],
        source_key_func: Callable[[Any], str]
    ) -> List[MatchResult]:
        """
        Match source items against pre-built target index.
        
        Args:
            source: List of source items
            target_index: Pre-built index of target items
            source_key_func: Function to extract key from source items
            
        Returns:
            List of match results
            
        Time Complexity: O(n) where n = len(source)
        """
        matches = []
        for source_item in source:
            key = source_key_func(source_item)
            if key in target_index:
                for target_item in target_index[key]:
                    matches.append(MatchResult(
                        source_item=source_item,
                        target_item=target_item,
                        match_score=1.0,
                        match_type="exact"
                    ))
        return matches
    
    @staticmethod
    def multi_key_index(
        items: List[Any], 
        key_funcs: List[Callable[[Any], Optional[str]]]
    ) -> Dict[str, List[Tuple[int, Any]]]:
        """
        Build index with multiple keys per item.
        
        Args:
            items: List of items to index
            key_funcs: List of functions to extract different keys
            
        Returns:
            Dictionary mapping all keys to (priority, item) tuples
            
        Time Complexity: O(n*k) where n = len(items), k = len(key_funcs)
        """
        index = defaultdict(list)
        for item in items:
            for priority, key_func in enumerate(key_funcs):
                try:
                    key = key_func(item)
                    if key is not None and key != '':
                        index[key].append((priority, item))
                except (KeyError, AttributeError, TypeError):
                    continue
        return dict(index)
    
    @staticmethod
    def dataframe_index_merge(
        df1: pd.DataFrame,
        df2: pd.DataFrame,
        key_col1: str,
        key_col2: str,
        how: str = 'inner'
    ) -> pd.DataFrame:
        """
        Efficient DataFrame merge using pandas indexing.
        
        Args:
            df1: First DataFrame
            df2: Second DataFrame
            key_col1: Key column in df1
            key_col2: Key column in df2
            how: Merge type ('inner', 'left', 'right', 'outer')
            
        Returns:
            Merged DataFrame
            
        Time Complexity: O(n + m) average case with hash join
        """
        # Use pandas merge which implements efficient hash join
        return pd.merge(
            df1, df2,
            left_on=key_col1,
            right_on=key_col2,
            how=how,
            suffixes=('_source', '_target')
        )
    
    @staticmethod
    def batch_lookup(
        keys: List[str],
        lookup_dict: Dict[str, Any],
        default: Any = None
    ) -> List[Any]:
        """
        Efficient batch lookup with default values.
        
        Args:
            keys: List of keys to look up
            lookup_dict: Dictionary to search in
            default: Default value for missing keys
            
        Returns:
            List of values
            
        Time Complexity: O(n) where n = len(keys)
        """
        return [lookup_dict.get(key, default) for key in keys]
    
    @staticmethod
    def set_intersection_match(
        source_items: List[str],
        target_items: List[str]
    ) -> Tuple[List[str], List[str], List[str]]:
        """
        Fast set-based matching for unique items.
        
        Args:
            source_items: List of source identifiers
            target_items: List of target identifiers
            
        Returns:
            Tuple of (matched, source_only, target_only)
            
        Time Complexity: O(n + m) where n, m are list lengths
        """
        source_set = set(source_items)
        target_set = set(target_items)
        
        matched = list(source_set & target_set)
        source_only = list(source_set - target_set)
        target_only = list(target_set - source_set)
        
        return matched, source_only, target_only
    
    @staticmethod
    def sorted_merge_join(
        source: List[Tuple[str, Any]],
        target: List[Tuple[str, Any]]
    ) -> List[Tuple[Any, Any]]:
        """
        Efficient merge join for sorted data.
        
        Args:
            source: List of (key, value) tuples, must be sorted by key
            target: List of (key, value) tuples, must be sorted by key
            
        Returns:
            List of matched (source_value, target_value) pairs
            
        Time Complexity: O(n + m) where n, m are list lengths
        Prerequisite: Both lists must be sorted
        """
        matches = []
        i, j = 0, 0
        
        while i < len(source) and j < len(target):
            source_key, source_val = source[i]
            target_key, target_val = target[j]
            
            if source_key == target_key:
                # Found match - handle potential duplicates
                source_group = [(source_key, source_val)]
                target_group = [(target_key, target_val)]
                
                # Collect all items with same key from source
                i_next = i + 1
                while i_next < len(source) and source[i_next][0] == source_key:
                    source_group.append(source[i_next])
                    i_next += 1
                
                # Collect all items with same key from target
                j_next = j + 1
                while j_next < len(target) and target[j_next][0] == target_key:
                    target_group.append(target[j_next])
                    j_next += 1
                
                # Create cartesian product of groups
                for _, s_val in source_group:
                    for _, t_val in target_group:
                        matches.append((s_val, t_val))
                
                i = i_next
                j = j_next
            elif source_key < target_key:
                i += 1
            else:
                j += 1
        
        return matches
    
    @staticmethod
    def hash_partition_match(
        source: List[Any],
        target: List[Any],
        key_func: Callable[[Any], str],
        num_partitions: int = 10
    ) -> List[MatchResult]:
        """
        Partition data by hash for parallel processing.
        
        Args:
            source: Source items
            target: Target items
            key_func: Function to extract key
            num_partitions: Number of partitions
            
        Returns:
            List of matches
            
        Time Complexity: O(n + m) with better cache locality
        """
        # Partition source and target by hash
        source_partitions = defaultdict(list)
        target_partitions = defaultdict(list)
        
        for item in source:
            key = key_func(item)
            if key:
                partition = int(hashlib.md5(key.encode()).hexdigest(), 16) % num_partitions
                source_partitions[partition].append(item)
        
        for item in target:
            key = key_func(item)
            if key:
                partition = int(hashlib.md5(key.encode()).hexdigest(), 16) % num_partitions
                target_partitions[partition].append(item)
        
        # Match within each partition
        all_matches = []
        for partition in range(num_partitions):
            if partition in source_partitions and partition in target_partitions:
                # Build index for this partition
                partition_index = EfficientMatcher.build_index(
                    target_partitions[partition],
                    key_func
                )
                # Match within partition
                partition_matches = EfficientMatcher.match_with_index(
                    source_partitions[partition],
                    partition_index,
                    key_func
                )
                all_matches.extend(partition_matches)
        
        return all_matches
    
    @staticmethod
    def dataframe_vectorized_match(
        df1: pd.DataFrame,
        df2: pd.DataFrame,
        match_columns: List[str]
    ) -> pd.DataFrame:
        """
        Vectorized matching for DataFrames without loops.
        
        Args:
            df1: First DataFrame
            df2: Second DataFrame
            match_columns: Columns to match on
            
        Returns:
            DataFrame with matches
            
        Time Complexity: O(n + m) with pandas optimizations
        """
        # Create composite key for matching
        df1_key = df1[match_columns].astype(str).agg('|'.join, axis=1)
        df2_key = df2[match_columns].astype(str).agg('|'.join, axis=1)
        
        # Add temporary key columns
        df1_temp = df1.copy()
        df2_temp = df2.copy()
        df1_temp['_match_key'] = df1_key
        df2_temp['_match_key'] = df2_key
        
        # Perform efficient merge
        result = pd.merge(
            df1_temp, df2_temp,
            on='_match_key',
            how='inner',
            suffixes=('_source', '_target')
        )
        
        # Drop temporary key column
        result = result.drop('_match_key', axis=1)
        
        return result
    
    @staticmethod
    def chunked_processing(
        items: List[Any],
        process_func: Callable[[List[Any]], Any],
        chunk_size: int = 10000
    ) -> List[Any]:
        """
        Process large datasets in chunks for memory efficiency.
        
        Args:
            items: Items to process
            process_func: Function to process each chunk
            chunk_size: Size of each chunk
            
        Returns:
            Combined results from all chunks
            
        Benefits: Better memory usage, cache locality
        """
        results = []
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            chunk_result = process_func(chunk)
            results.extend(chunk_result if isinstance(chunk_result, list) else [chunk_result])
        return results
    
    @staticmethod
    def estimate_performance(
        n_source: int,
        n_target: int,
        algorithm: str = "nested_loop"
    ) -> Dict[str, Any]:
        """
        Estimate performance for different algorithms.
        
        Args:
            n_source: Number of source items
            n_target: Number of target items
            algorithm: Algorithm type
            
        Returns:
            Performance estimates
        """
        algorithms = {
            "nested_loop": {
                "operations": n_source * n_target,
                "complexity": "O(n*m)",
                "memory": "O(1)",
                "recommended": n_source * n_target < 10000
            },
            "hash_index": {
                "operations": n_source + n_target,
                "complexity": "O(n+m)",
                "memory": "O(m)",
                "recommended": True
            },
            "sorted_merge": {
                "operations": n_source * np.log2(n_source) + n_target * np.log2(n_target),
                "complexity": "O(n log n + m log m)",
                "memory": "O(1)",
                "recommended": n_source > 100000 and n_target > 100000
            },
            "set_intersection": {
                "operations": n_source + n_target,
                "complexity": "O(n+m)",
                "memory": "O(n+m)",
                "recommended": True
            }
        }
        
        if algorithm not in algorithms:
            return {"error": f"Unknown algorithm: {algorithm}"}
        
        algo_info = algorithms[algorithm]
        
        # Estimate time (assuming 1M operations per second)
        estimated_seconds = algo_info["operations"] / 1_000_000
        
        return {
            "algorithm": algorithm,
            "complexity": algo_info["complexity"],
            "memory": algo_info["memory"],
            "operations": algo_info["operations"],
            "estimated_seconds": estimated_seconds,
            "estimated_time": f"{estimated_seconds:.2f}s" if estimated_seconds < 60 else f"{estimated_seconds/60:.2f}m",
            "recommended": algo_info["recommended"],
            "warning": "Performance may vary based on data characteristics"
        }