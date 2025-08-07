"""
Fuzzy matching algorithms for biomapper.

This module provides string similarity and fuzzy matching algorithms
that can be used across different entity types and actions.

Available Functions (when implemented):
    calculate_similarity: Compute similarity between two strings
    batch_fuzzy_match: Fuzzy match lists of strings efficiently
    semantic_similarity: AI-powered semantic similarity

Supported Methods:
    - Levenshtein distance
    - Jaro-Winkler similarity
    - Cosine similarity
    - Semantic embeddings

Example Usage:
    from biomapper.core.strategy_actions.algorithms.fuzzy_matching import calculate_similarity
    
    score = calculate_similarity("HbA1c", "Hemoglobin A1c", method="jaro_winkler")
    matches = batch_fuzzy_match(source_list, target_list, threshold=0.8)

Development:
    Implement performance-optimized algorithms with configurable methods.
    Support batch processing for large datasets.
"""

# Import fuzzy matching functions
# from .string_similarity import calculate_similarity, batch_fuzzy_match  # To be implemented
# from .semantic_similarity import semantic_similarity                    # To be implemented

__all__ = []  # Functions will be exported when implemented
