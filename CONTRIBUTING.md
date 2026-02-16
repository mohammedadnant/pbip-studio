# Contributing to PBIP Studio

Thank you for your interest in contributing to PBIP Studio! We welcome contributions from the community.

## 🌟 Ways to Contribute

- **Report Bugs**: Submit detailed bug reports with reproduction steps
- **Suggest Features**: Share ideas for new features or improvements
- **Improve Documentation**: Fix typos, clarify instructions, or add examples
- **Submit Code**: Fix bugs or implement new features
- **Share Feedback**: Let us know how you're using PBIP Studio

## 🐛 Reporting Bugs

When reporting bugs, please include:

1. **Description**: Clear description of the issue
2. **Steps to Reproduce**: Detailed steps to reproduce the behavior
3. **Expected Behavior**: What you expected to happen
4. **Actual Behavior**: What actually happened
5. **Environment**: 
   - Windows version
   - Python version (if running from source)
   - PBIP Studio version
6. **Screenshots**: If applicable
7. **Log Files**: Located at `%LOCALAPPDATA%\PBIP Studio\logs\app.log`

## 💡 Suggesting Features

Feature requests are welcome! Please:

1. Check if the feature already exists or has been requested
2. Describe the problem you're trying to solve
3. Explain your proposed solution
4. Include any relevant examples or mockups

## 🔧 Development Setup

### Prerequisites

- Windows 10/11 (64-bit)
- Python 3.10 or higher
- Git
- Visual Studio Code (recommended)

### Setup Instructions

```powershell
# 1. Fork and clone the repository
git clone https://github.com/yourusername/pbip-studio.git
cd pbip-studio

# 2. Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install development dependencies
pip install pytest pytest-qt black flake8 mypy

# 5. Run the application
python src/main.py
```

## 📝 Code Guidelines

### Python Style Guide

- Follow [PEP 8](https://pep8.org/) style guide
- Use type hints where possible
- Write docstrings for classes and functions
- Keep functions focused and small

### Code Formatting

We use `black` for code formatting:

```powershell
# Format all Python files
black src/

# Check formatting without changes
black --check src/
```

### Linting

We use `flake8` for linting:

```powershell
flake8 src/ --max-line-length=100 --ignore=E203,W503
```

### Example Code Style

```python
"""Module description."""

from typing import Optional, List
import logging


class MyClass:
    """Class description.
    
    Attributes:
        attr1: Description of attribute
    """
    
    def __init__(self, name: str):
        """Initialize MyClass.
        
        Args:
            name: The name parameter
        """
        self.name = name
        self.logger = logging.getLogger(__name__)
    
    def process_data(self, items: List[str]) -> Optional[dict]:
        """Process a list of items.
        
        Args:
            items: List of items to process
            
        Returns:
            Processed data dictionary or None
        """
        if not items:
            return None
        
        return {"count": len(items)}
```

## 🧪 Testing

### Running Tests

```powershell
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_parser.py
```

### Writing Tests

- Write tests for new features and bug fixes
- Aim for high test coverage
- Use descriptive test names
- Include both positive and negative test cases

Example:

```python
import pytest
from src.parsers.tmdl_parser import TmdlParser


def test_parse_table_definition():
    """Test parsing a table definition from TMDL."""
    parser = TmdlParser()
    tmdl_content = """
    table Sales {
        column Amount = CURRENCY
    }
    """
    result = parser.parse_table(tmdl_content)
    assert result["name"] == "Sales"
    assert len(result["columns"]) == 1
```

## 📦 Pull Request Process

1. **Create a Branch**: Use a descriptive branch name
   ```powershell
   git checkout -b feature/add-dark-mode
   # or
   git checkout -b fix/column-rename-bug
   ```

2. **Make Changes**: Follow code guidelines and write tests

3. **Commit Changes**: Use clear, descriptive commit messages
   ```powershell
   git commit -m "Add dark mode theme support"
   ```

4. **Push to Fork**: Push your branch to your fork
   ```powershell
   git push origin feature/add-dark-mode
   ```

5. **Open Pull Request**: 
   - Provide a clear description of changes
   - Reference any related issues
   - Include screenshots if UI changes
   - Ensure all tests pass

6. **Code Review**: 
   - Address feedback from maintainers
   - Make requested changes
   - Keep discussion constructive

7. **Merge**: Once approved, maintainers will merge your PR

## 📋 Commit Message Guidelines

Use clear, descriptive commit messages:

- **feat**: New feature (`feat: Add data source migration wizard`)
- **fix**: Bug fix (`fix: Handle null values in column rename`)
- **docs**: Documentation (`docs: Update installation guide`)
- **style**: Code style/formatting (`style: Format with black`)
- **refactor**: Code refactoring (`refactor: Simplify parser logic`)
- **test**: Add/update tests (`test: Add tests for TMDL parser`)
- **chore**: Maintenance (`chore: Update dependencies`)

## 🏗️ Project Structure

```
pbip-studio/
├── src/                    # Source code
│   ├── main.py            # Application entry point
│   ├── api/               # FastAPI backend
│   ├── database/          # SQLite database layer
│   ├── gui/               # PyQt6 GUI components
│   ├── models/            # Data models
│   ├── parsers/           # TMDL/PBIR parsers
│   ├── services/          # Business logic
│   └── utils/             # Utility functions
├── tests/                 # Test suite
├── docs/                  # Documentation
├── data/                  # Database files (local)
├── logos/                 # Application icons
├── requirements.txt       # Python dependencies
├── setup.py              # Build configuration
└── README.md             # Project readme
```

## 🔍 Code Review Checklist

Before submitting a PR, ensure:

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New features have tests
- [ ] Documentation is updated
- [ ] No commented-out code
- [ ] No debug print statements
- [ ] Type hints are used
- [ ] Error handling is proper
- [ ] Commit messages are clear

## 📬 Communication

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and general discussion
- **Pull Requests**: Code contributions

## 🙏 Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project README

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## ❓ Questions?

If you have questions about contributing, feel free to:
- Open a GitHub Discussion
- Comment on an existing issue
- Reach out to maintainers

Thank you for contributing to PBIP Studio! 🎉
