# PBIP Studio - Developer Guide

## Table of Contents
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Development Setup](#development-setup)
- [Architecture](#architecture)
- [Contributing](#contributing)
- [Testing](#testing)
- [Building](#building)

## Getting Started

### Prerequisites
- Python 3.10 or higher
- Git
- Windows 10/11 (for full testing)
- Visual Studio Code (recommended)

### Clone and Setup

```powershell
# Clone the repository
git clone https://github.com/mohammedadnant/pbip-studio.git
cd pbip-studio

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-qt black flake8 mypy
```

### Run the Application

```powershell
# From project root
python src/main.py
```

## Project Structure

```
pbip-studio/
├── .github/                    # GitHub workflows and templates
│   ├── ISSUE_TEMPLATE/        # Issue templates
│   └── pull_request_template.md
├── src/                       # Source code
│   ├── main.py               # Application entry point
│   ├── api/                  # FastAPI backend
│   │   ├── __init__.py
│   │   ├── server.py         # FastAPI app
│   │   ├── routes/           # API routes
│   │   └── schemas/          # Pydantic schemas
│   ├── database/             # Database layer
│   │   ├── __init__.py
│   │   ├── connection.py     # SQLite connection
│   │   └── models.py         # Database models
│   ├── gui/                  # PyQt6 GUI
│   │   ├── __init__.py
│   │   ├── main_window.py    # Main application window
│   │   ├── widgets/          # Custom widgets
│   │   └── dialogs/          # Dialog windows
│   ├── models/               # Data models
│   │   ├── __init__.py
│   │   └── powerbi.py        # Power BI model classes
│   ├── parsers/              # File parsers
│   │   ├── __init__.py
│   │   ├── tmdl_parser.py    # TMDL parser
│   │   ├── pbir_parser.py    # PBIR parser
│   │   └── json_parser.py    # JSON parser
│   ├── services/             # Business logic
│   │   ├── __init__.py
│   │   ├── indexer.py        # Model indexing
│   │   ├── downloader.py     # Fabric download
│   │   └── uploader.py       # Fabric upload
│   └── utils/                # Utility functions
│       ├── __init__.py
│       ├── theme_manager.py  # Theme handling
│       └── helpers.py        # Helper functions
├── tests/                    # Test suite
│   ├── __init__.py
│   ├── test_parser.py
│   ├── test_api.py
│   └── fixtures/             # Test data
├── docs/                     # Documentation
│   ├── INSTALLATION.md
│   ├── USER_GUIDE.md
│   ├── DEVELOPER.md
│   └── ARCHITECTURE.md
├── data/                     # Database files (gitignored)
├── logos/                    # Application icons
├── build/                    # Build outputs (gitignored)
├── requirements.txt          # Python dependencies
├── setup.py                  # Build configuration
├── build.ps1                 # Build script
├── README.md                 # Project readme
├── LICENSE                   # MIT License
└── CONTRIBUTING.md           # Contribution guidelines
```

## Development Setup

### Recommended VS Code Extensions

Install these for the best development experience:

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.black-formatter",
    "ms-python.flake8",
    "github.copilot"
  ]
}
```

### VS Code Settings

Create `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/Scripts/python.exe",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.flake8Args": [
    "--max-line-length=100",
    "--ignore=E203,W503"
  ],
  "editor.formatOnSave": true,
  "editor.rulers": [100],
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "build/": true,
    "dist/": true
  }
}
```

### Environment Variables

Create a `.env` file in the project root (for development):

```bash
# Azure/Fabric (optional)
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-secret

# Development
DEBUG=True
LOG_LEVEL=DEBUG
```

## Architecture

### Overview

PBIP Studio uses a **client-server architecture** with:
- **Frontend**: PyQt6 (native desktop GUI)
- **Backend**: FastAPI REST API (localhost:8000)
- **Database**: SQLite (local file storage)

### Communication Flow

```
┌──────────────┐         HTTP/REST        ┌─────────────┐
│   PyQt6 GUI  │ ───────────────────────> │  FastAPI    │
│   (Frontend) │                           │  (Backend)  │
│              │ <─────────────────────── │             │
└──────────────┘         JSON              └─────────────┘
                                                  │
                                                  │ SQLAlchemy
                                                  ▼
                                            ┌─────────────┐
                                            │   SQLite    │
                                            │  Database   │
                                            └─────────────┘
```

### Key Components

#### 1. GUI Layer (PyQt6)
- Main window with tab-based interface
- Custom widgets for data display
- Theme support (light/dark)
- Responsive design

#### 2. API Layer (FastAPI)
- RESTful endpoints
- Async request handling
- Pydantic validation
- Auto-generated OpenAPI docs

#### 3. Service Layer
- Business logic implementation
- File parsing and processing
- Fabric API integration
- Data transformations

#### 4. Data Layer
- SQLite database
- SQLAlchemy ORM
- Model definitions
- Query optimization

### Threading Model

- **Main Thread**: PyQt6 GUI (UI updates)
- **Backend Thread**: FastAPI server (daemon thread)
- **Worker Threads**: Long-running tasks (indexing, downloads)

### File Parsing

```python
# TMDL Parser example
from src.parsers.tmdl_parser import TmdlParser

parser = TmdlParser()
table_data = parser.parse_table(tmdl_content)
```

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for detailed contribution guidelines.

### Quick Contribution Workflow

```powershell
# 1. Fork and clone
git clone https://github.com/mohammedadnant/pbip-studio.git

# 2. Create feature branch
git checkout -b feature/my-feature

# 3. Make changes and test
python -m pytest

# 4. Format code
black src/

# 5. Commit and push
git add .
git commit -m "Add my feature"
git push origin feature/my-feature

# 6. Create pull request on GitHub
```

## Testing

### Running Tests

```powershell
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test
pytest tests/test_parser.py

# Run with verbose output
pytest -v
```

### Writing Tests

Example test structure:

```python
import pytest
from src.parsers.tmdl_parser import TmdlParser


class TestTmdlParser:
    """Test TMDL parser functionality."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return TmdlParser()
    
    def test_parse_table(self, parser):
        """Test table parsing."""
        tmdl = """
        table Sales {
            column Amount = CURRENCY
        }
        """
        result = parser.parse_table(tmdl)
        assert result["name"] == "Sales"
        assert len(result["columns"]) == 1
```

### GUI Testing

Using `pytest-qt`:

```python
import pytest
from PyQt6.QtWidgets import QApplication
from src.gui.main_window import MainWindow


@pytest.fixture
def app(qtbot):
    """Create application."""
    window = MainWindow()
    qtbot.addWidget(window)
    return window


def test_main_window(app):
    """Test main window creation."""
    assert app.windowTitle() == "PBIP Studio"
```

## Building

### Build Executable

```powershell
# Using PyInstaller
.\build.ps1
```

This creates a standalone executable in `dist/`.

### Build MSI Installer

```powershell
# Using cx_Freeze
python setup.py bdist_msi
```

Output: `dist/PBIP Studio-1.0.0-win64.msi`

### Build Configuration

Edit `setup.py` to customize:
- Application version
- Icon
- Dependencies
- Install location

### Distribution Checklist

Before releasing:
- [ ] Update version in `setup.py`
- [ ] Update `CHANGELOG.md`
- [ ] Run all tests
- [ ] Build and test MSI
- [ ] Test on clean Windows install
- [ ] Update documentation
- [ ] Create GitHub release
- [ ] Tag version in git

## Debugging

### VS Code Launch Configuration

`.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: PBIP Studio",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/src/main.py",
      "console": "integratedTerminal",
      "justMyCode": false,
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src"
      }
    }
  ]
}
```

### Common Debug Points

1. **Application Startup**: `src/main.py:main()`
2. **API Endpoints**: `src/api/routes/`
3. **File Parsing**: `src/parsers/`
4. **GUI Events**: `src/gui/main_window.py`

### Logging

```python
import logging

logger = logging.getLogger(__name__)
logger.debug("Debug message")
logger.info("Info message")
logger.error("Error message")
```

Logs are written to: `%LOCALAPPDATA%\PBIP Studio\logs\app.log`

## Performance

### Profiling

```python
import cProfile
import pstats

# Profile a function
profiler = cProfile.Profile()
profiler.enable()
# ... your code ...
profiler.disable()

stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

### Database Optimization

```python
# Use bulk operations
session.bulk_insert_mappings(Model, data_list)

# Add indexes
Index('idx_table_name', Table.name)

# Use eager loading
query.options(joinedload(Table.columns))
```

## Troubleshooting Development Issues

### Import Errors

Make sure `src/` is in Python path:

```powershell
$env:PYTHONPATH = "$PWD\src"
```

### Qt Designer

For editing UI files:

```powershell
pip install pyqt6-tools
pyqt6-tools designer
```

### Database Schema Changes

```python
# After modifying models
from src.database import Base, engine
Base.metadata.create_all(engine)
```

## Resources

- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Python Style Guide (PEP 8)](https://pep8.org/)

## Getting Help

- **GitHub Issues**: [Report bugs](../../issues)
- **Discussions**: [Ask questions](../../discussions)
- **Contributing**: [Contribution guide](../CONTRIBUTING.md)
