"""Mock Strategy model"""


class Strategy:
    """Mock Strategy class"""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)