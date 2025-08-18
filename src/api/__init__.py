"""
Biomapper REST API Server.

This module provides the FastAPI-based REST API for biomapper,
enabling HTTP access to strategies, actions, and data processing services.
"""

from .main import app

__all__ = ['app']