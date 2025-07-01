#!/usr/bin/env python3
"""
Build validation script for CI/CD pipeline.
Tests that the package can be imported and basic functionality works.
"""

import importlib
import sys
from pathlib import Path


def validate_imports():
    """Test that all main modules can be imported."""
    modules_to_test = [
        "src.agents",
        "src.core",
        "src.diagram",
        "src.api",
        "src.validation",
        "src.templates",
    ]

    print("🔍 Testing module imports...")
    for module in modules_to_test:
        try:
            importlib.import_module(module)
            print(f"✅ {module}")
        except ImportError as e:
            print(f"❌ {module}: {e}")
            return False

    return True


def validate_core_functionality():
    """Test that core functionality works."""
    print("\n🔍 Testing core functionality...")

    try:
        # Test settings
        from src.core.settings import Settings

        Settings()  # Test instantiation without storing unused variable
        print("✅ Settings initialization")

        # Test models
        from src.core.models import DiagramSpec

        DiagramSpec(pattern_name="test", parameters={})  # Test instantiation
        print("✅ Model creation")

        # Test tool registry (skip full initialization to avoid complex dependencies)
        from src.diagram.engine import DiagramEngine
        from src.diagram.tool_registry import ToolRegistry

        # Create a minimal engine for testing
        engine = DiagramEngine()
        ToolRegistry(engine)  # Test instantiation
        print("✅ Tool registry")

        return True

    except Exception as e:
        print(f"❌ Core functionality test failed: {e}")
        return False


def validate_package_metadata():
    """Test that package metadata is correct."""
    print("\n🔍 Testing package metadata...")

    try:
        # Check if pyproject.toml exists and has required fields
        pyproject_path = Path("pyproject.toml")
        if not pyproject_path.exists():
            print("❌ pyproject.toml not found")
            return False

        print("✅ pyproject.toml exists")

        # Check build artifacts
        dist_path = Path("dist")
        if not dist_path.exists():
            print("❌ dist directory not found")
            return False

        wheel_files = list(dist_path.glob("*.whl"))
        tar_files = list(dist_path.glob("*.tar.gz"))

        if not wheel_files:
            print("❌ No wheel file found in dist/")
            return False

        if not tar_files:
            print("❌ No source distribution found in dist/")
            return False

        print(f"✅ Found wheel: {wheel_files[0].name}")
        print(f"✅ Found source dist: {tar_files[0].name}")

        return True

    except Exception as e:
        print(f"❌ Package metadata validation failed: {e}")
        return False


def main():
    """Run all validation tests."""
    print("🚀 Starting build validation...\n")

    tests = [
        ("Module Imports", validate_imports),
        ("Core Functionality", validate_core_functionality),
        ("Package Metadata", validate_package_metadata),
    ]

    all_passed = True

    for test_name, test_func in tests:
        print(f"\n{'=' * 50}")
        print(f"Running: {test_name}")
        print(f"{'=' * 50}")

        if not test_func():
            all_passed = False

    print(f"\n{'=' * 50}")
    if all_passed:
        print("🎉 All validation tests passed!")
        print("✅ Build is ready for deployment")
        sys.exit(0)
    else:
        print("💥 Some validation tests failed!")
        print("❌ Build needs attention")
        sys.exit(1)


if __name__ == "__main__":
    main()
