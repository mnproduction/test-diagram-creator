# CI/CD Pipeline Documentation

## Overview

The AI Diagram Creator project uses a comprehensive GitHub Actions CI/CD pipeline that ensures code quality, runs tests, builds packages, and validates deployments without automatic deployment.

## Pipeline Stages

### 1. **Linting Stage** 🔍
**Job Name:** `lint`
**Purpose:** Ensure code quality and formatting standards

**Steps:**
- **Code Formatting Check**: `ruff format --check .`
- **Linting**: `ruff check .` 
- **Type Checking**: Placeholder for future mypy integration
- **Caching**: UV dependency caching for faster builds

**Triggers:** All pushes and pull requests to master branch

### 2. **Testing Stage** 🧪
**Job Name:** `test`
**Purpose:** Run comprehensive test suite across multiple Python versions
**Dependencies:** Requires `lint` stage to pass

**Matrix Strategy:**
- Python 3.11
- Python 3.12

**Steps:**
- **System Dependencies**: Install Graphviz for diagram rendering
- **Test Execution**: `pytest --cov=src --cov-report=xml --cov-report=term-missing`
- **Coverage Reporting**: Upload to Codecov
- **Environment Validation**: Test dependency imports

**Current Results:**
- ✅ **117 tests passing**
- ✅ **82% code coverage**
- ✅ **Full async test support**

### 3. **Build Stage** 🏗️
**Job Name:** `build`
**Purpose:** Build and validate packages and Docker images
**Dependencies:** Requires both `lint` and `test` stages to pass

**Package Building:**
- **Python Package**: `uv build` (creates wheel and source distribution)
- **Package Validation**: Custom validation script tests imports and functionality
- **Docker Image**: Build production Docker image with caching

**Validation Process:**
- Module import verification
- Core functionality testing
- Package metadata validation
- Docker image functionality test

### 4. **Security Stage** 🔒
**Job Name:** `security`
**Purpose:** Scan for security vulnerabilities
**Dependencies:** Requires `lint` stage to pass

**Security Tools:**
- **Safety**: Dependency vulnerability scanning
- **Bandit**: Static security analysis for Python code

## Pipeline Features

### **Caching Strategy**
- **UV Dependencies**: Cached by `uv.lock` hash for faster dependency installation
- **Docker Layers**: GitHub Actions cache for Docker build optimization
- **Per-Python Version**: Separate caches for each Python version in matrix

### **Environment Variables**
```yaml
env:
  GEMINI_API_KEY: "dummy_key_for_testing"
```

### **Build Artifacts**
- **Python Wheel**: `test_diagram_creator-0.1.0-py3-none-any.whl`
- **Source Distribution**: `test_diagram_creator-0.1.0.tar.gz`
- **Docker Image**: `ai-diagram-creator:${{ github.sha }}`

### **Quality Gates**
1. **Code Formatting**: Must pass ruff formatting checks
2. **Linting**: Must pass all ruff lint rules
3. **Test Coverage**: Maintains 82% coverage threshold
4. **Security**: Scans for known vulnerabilities
5. **Build Validation**: Package must import and function correctly
6. **Docker Validation**: Container must run successfully

## Workflow Configuration

**File:** `.github/workflows/ci.yml`

**Triggers:**
```yaml
on:
  push:
    branches: [ master ]
  pull_request:
    branches: [ master ]
```

**Job Dependencies:**
```
lint → test (matrix)
lint → security
[lint, test] → build
```

## Local Testing

### **Run Individual Stages Locally:**

```bash
# Linting
uv run ruff format --check .
uv run ruff check .

# Testing
uv run pytest --cov=src --cov-report=term-missing

# Building
uv build
uv run python scripts/validate_build.py

# Security (install tools first)
uv run pip install safety bandit
uv run safety check
uv run bandit -r src/
```

### **Docker Testing:**
```bash
docker build -t ai-diagram-creator:local .
docker run --rm ai-diagram-creator:local python -c "import src; print('Success')"
```

**Note:** The Dockerfile includes `README.md` in the build context to satisfy the hatchling build backend requirements.

## Deployment Readiness

The pipeline builds and validates everything needed for deployment but **does not automatically deploy**. This allows for:

- **Manual Review**: Human oversight before production deployment
- **Staging Deployment**: Manual promotion to staging environments
- **Release Control**: Controlled release timing and rollback capability

## Future Enhancements

### **Planned Additions:**
- **Type Checking**: MyPy integration for static type analysis
- **Performance Testing**: Benchmark tests for diagram generation speed
- **Integration Tests**: External API integration testing
- **Deployment Stages**: Automated staging and production deployment workflows

### **Monitoring Integration:**
- **Codecov**: Coverage tracking and reporting
- **GitHub Actions**: Build status and artifact management
- **Security Alerts**: Automated vulnerability notifications

## Configuration Files

### **Key Configuration Files:**
- **Pipeline**: `.github/workflows/ci.yml`
- **Build**: `pyproject.toml` (build-system configuration)
- **Testing**: `pyproject.toml` (pytest configuration)
- **Linting**: `pyproject.toml` (ruff configuration)
- **Validation**: `scripts/validate_build.py`

### **Repository:**
- **GitHub**: `https://github.com/mnproduction/test-diagram-creator`

### **Dependencies:**
- **Build**: `hatchling` (modern Python build backend)
- **Testing**: `pytest`, `pytest-asyncio`, `pytest-cov`
- **Linting**: `ruff` (fast Python linter and formatter)
- **Security**: `safety`, `bandit`

## Success Metrics

- ✅ **100% Pipeline Success Rate** on master branch
- ✅ **82% Test Coverage** maintained
- ✅ **Multi-Version Support** (Python 3.11, 3.12)
- ✅ **Fast Builds** with comprehensive caching
- ✅ **Security Scanning** integrated
- ✅ **Production-Ready Artifacts** generated

The CI/CD pipeline ensures that every change is thoroughly tested, validated, and ready for deployment while maintaining high code quality standards. 