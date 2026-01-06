# Contributing to RAG Document Assistant

Thank you for your interest in contributing to the RAG Document Assistant! This document provides guidelines and information to help you contribute effectively.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Create a new branch for your feature or bug fix
4. Make your changes
5. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.8 or higher
- pip (package installer for Python)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/RAG-document-assistant.git
cd RAG-document-assistant

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt  # If available
# Or install manually:
pip install pytest black flake8 mypy
```

## Code Style

We follow these coding standards:

### Python Style Guide

- Follow [PEP 8](https://pep8.org/) style guide
- Use 4 spaces for indentation (no tabs)
- Line length should not exceed 88 characters
- Use meaningful variable and function names
- Write docstrings for all public functions and classes

### Formatting

We use Black for code formatting:

```bash
# Format code
black src/ tests/

# Check formatting
black --check src/ tests/
```

### Linting

We use Flake8 for linting:

```bash
flake8 src/ tests/
```

### Type Checking

We use MyPy for static type checking:

```bash
mypy src/
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_retrieval.py
```

### Writing Tests

- Place test files in the `tests/` directory
- Follow the naming convention: `test_*.py`
- Use descriptive test function names
- Include both positive and negative test cases
- Test edge cases and error conditions

## Submitting Changes

1. Ensure your code follows the style guidelines
2. Run all tests and ensure they pass
3. Add tests for new functionality
4. Update documentation as needed
5. Commit your changes with a clear, descriptive commit message
6. Push to your fork
7. Submit a pull request to the main repository

### Pull Request Guidelines

- Include a clear title and description
- Reference any related issues
- Keep changes focused and atomic
- Ensure all CI checks pass
- Be responsive to feedback during review

## Reporting Issues

If you find a bug or have a feature request, please open an issue on GitHub with:

- A clear, descriptive title
- Detailed steps to reproduce the issue
- Expected vs. actual behavior
- Screenshots or code examples if applicable
- Information about your environment (Python version, OS, etc.)

## Code of Conduct

Please note that this project is released with a Contributor Code of Conduct. By participating in this project you agree to abide by its terms.

## Questions?

If you have any questions about contributing, feel free to open an issue or contact the maintainers.