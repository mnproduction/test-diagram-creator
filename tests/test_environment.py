# tests/test_environment.py
import importlib

import pytest

# This list maps package names from pyproject.toml to their importable module names.
# This is not an exhaustive list but covers the main libraries. It's intended
# as a quick sanity check to catch broken virtual environments early.
# If dependencies change in pyproject.toml, this list may need to be updated.
DEPENDENCY_MAPPING = [
    # Main dependencies
    ("diagrams", "diagrams"),
    ("fastapi", "fastapi"),
    ("google-generativeai", "google.generativeai"),
    ("pillow", "PIL"),
    ("pydantic", "pydantic"),
    ("pydantic-ai", "pydantic_ai"),
    ("python-dotenv", "dotenv"),
    ("uvicorn", "uvicorn"),
    ("logfire", "logfire"),
    ("opentelemetry-instrumentation-fastapi", "opentelemetry.instrumentation.fastapi"),
    ("structlog", "structlog"),
    ("slowapi", "slowapi"),
    ("pydantic-settings", "pydantic_settings"),
    # Dev dependencies
    ("ruff", "ruff"),
    ("httpx", "httpx"),
    ("pytest", "pytest"),
    ("pytest-asyncio", "pytest_asyncio"),
    ("pytest-cov", "pytest_cov"),
]


@pytest.mark.parametrize("package_name, import_name", DEPENDENCY_MAPPING)
def test_dependency_is_importable(package_name, import_name):
    """
    Tests that a dependency is installed and importable.
    This helps catch environment issues early.
    """
    try:
        importlib.import_module(import_name)
    except ImportError as e:
        pytest.fail(
            f"Could not import '{import_name}' from package '{package_name}'. "
            f"Please ensure all dependencies in pyproject.toml are installed correctly. "
            f"Original error: {e}"
        )
