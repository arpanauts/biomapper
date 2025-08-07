"""Global pytest configuration."""
import pytest
import os

# Disable Langfuse monitoring for tests to prevent connection errors
# More aggressive - set to empty strings rather than removing
os.environ["LANGFUSE_PUBLIC_KEY"] = ""
os.environ["LANGFUSE_SECRET_KEY"] = ""
os.environ["LANGFUSE_HOST"] = ""
os.environ["LANGFUSE_ENABLED"] = "false"
os.environ["LANGFUSE_RELEASE"] = ""

# Also try to disable via the library if it's imported
try:
    import langfuse

    langfuse.disabled = True

    # Also monkey-patch the Langfuse class to prevent initialization
    class DisabledLangfuse:
        def __init__(self, *args, **kwargs):
            pass

        def __getattr__(self, name):
            return lambda *args, **kwargs: None

    langfuse.Langfuse = DisabledLangfuse
except ImportError:
    pass

# Monkey-patch the decorator to do nothing
try:
    from langfuse import decorators

    decorators.observe = lambda **kwargs: lambda func: func
    decorators.langfuse_context = type(
        "MockContext",
        (),
        {"__getattr__": lambda self, name: lambda *args, **kwargs: None},
    )()
except ImportError:
    pass


def pytest_collection_modifyitems(config, items):
    """Configure test collection and marking."""
    # Check if we're running the full test suite
    running_full_suite = len(config.args) == 0 or any(
        arg.startswith("-") for arg in config.args
    )

    for item in items:
        # Mark slow tests
        if "large_dataset" in str(item.fspath) or "performance" in str(item.name):
            item.add_marker(pytest.mark.slow)

        # Mark integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

    # Skip problematic tests based on environment variable
    if os.environ.get("SKIP_SLOW_TESTS") == "1":
        skip_slow = pytest.mark.skip(reason="Skipping slow tests")
        for item in items:
            if hasattr(item, "get_closest_marker") and item.get_closest_marker("slow"):
                item.add_marker(skip_slow)


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "api: marks tests that require API server")
