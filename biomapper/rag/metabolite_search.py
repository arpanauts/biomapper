"""Stub for metabolite search module."""

class QdrantClient:
    """Stub for QdrantClient."""
    def __init__(self, *args, **kwargs):
        pass
    
    def search(self, *args, **kwargs):
        """Mock search method."""
        return []

class TextEmbedding:
    """Stub for TextEmbedding."""
    def __init__(self, *args, **kwargs):
        pass
    
    def embed(self, texts):
        """Mock embed method."""
        return [[0.1] * 384 for _ in texts]

class MetaboliteSearcher:
    """Stub for metabolite searcher."""
    def __init__(self, *args, **kwargs):
        pass
    
    def search(self, query, **kwargs):
        return []