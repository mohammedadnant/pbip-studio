# PBIP Studio

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-blue)](https://www.microsoft.com/windows)
[![Latest Release](https://img.shields.io/github/v/release/mohammedadnant/pbip-studio)](https://github.com/mohammedadnant/pbip-studio/releases/latest)

> A free, open-source Power BI development toolkit for working with PBIP/TMDL files, similar to Tabular Editor 2 and DAX Studio.

**PBIP Studio** is a comprehensive Windows desktop application designed for Power BI professionals working with Microsoft Fabric and Power BI semantic models. It helps you work more efficiently with PBIP/TMDL files, automate repetitive tasks, and streamline your Power BI development workflow.

## ✨ Features

- 📊 **Semantic Model Analysis** - Index and explore models, tables, measures, and relationships
- 📥 **Download from Fabric** - Pull down workspaces in PBIP/TMDL format for local development
- 🔄 **Data Source Migration** - Switch between SQL Server, Azure SQL, Snowflake, or Fabric Lakehouse
- 🏷️ **Bulk Table Rename** - Add prefixes/suffixes (like `dim_`, `fact_`) with automatic DAX updates
- 📏 **Column Transformations** - Convert naming conventions (snake_case ↔ PascalCase) across models
- 📤 **Deploy to Fabric** - Push your changes back to Microsoft Fabric workspaces
- 💾 **Local Metadata Database** - SQLite database for fast searching and reporting
- 🔒 **Privacy-First** - All processing happens locally on your machine

## 🎯 Who Is This For?

- **Power BI Developers** - Working with semantic models and PBIP format
- **Data Engineers** - Managing data source migrations and transformations
- **BI Consultants** - Handling multiple client projects and standardization
- **DevOps Teams** - Automating Power BI deployment pipelines

## 🚀 Quick Start

### Option 1: Download Executable (Recommended for Users)

1. **[Download Latest Release (v1.0.0+)](https://github.com/mohammedadnant/pbip-studio/releases/latest)** from GitHub
2. Run the MSI installer or extract the ZIP file
3. Launch PBIP Studio from the Start Menu

> **Note**: You may see a Windows SmartScreen warning for unsigned applications. Click "More info" → "Run anyway"

### Option 2: Run from Source (For Developers)

```powershell
# Clone the repository
git clone https://github.com/mohammedadnant/pbip-studio.git
cd pbip-studio

# Run the quick start script
.\start.ps1
```

The script automatically creates a virtual environment, installs dependencies, and launches the application.

## 📋 Prerequisites

- **OS**: Windows 10 or Windows 11 (64-bit)
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 500MB for application
- **Internet**: Only needed for Fabric download/upload features
- **Python**: 3.10+ (only for running from source)

## 🏗️ Architecture

PBIP Studio uses a modern desktop application architecture:

- **Frontend**: PyQt6 (native Windows GUI)
- **Backend**: FastAPI REST API (localhost:8000)
- **Database**: SQLite (local, portable)
- **Parser**: Custom TMDL/PBIR/JSON parsers
- **Auth**: Azure AD Service Principal for Fabric integration

## 📖 Documentation

- [User Guide](docs/USER_GUIDE.md) - Comprehensive guide for end users
- [Installation Guide](docs/INSTALLATION.md) - Detailed installation instructions
- [Developer Guide](docs/DEVELOPER.md) - Contributing and development setup

## 🤝 Contributing

We welcome contributions from the community! Whether it's bug reports, feature requests, or code contributions, please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```powershell
# Clone the repo
git clone https://github.com/mohammedadnant/pbip-studio.git
cd pbip-studio

# Create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run the application
python src/main.py
```

### 🚫 Important: .gitignore Rules for Contributors

**NEVER commit these files to the repository:**

- **Sensitive Data**: 
  - Certificate files (`*.pfx`, `*.cer`, `*.p12`, `*.pem`)
  - Configuration with secrets (`config.json`, `.env`)
  - Local databases (`*.db`, `*.sqlite`)
  - Downloaded PBIP/TMDL files (`Downloads/` folder)

- **Build Artifacts**: 
  - Build outputs (`build/`, `dist/`, `*.exe`, `*.msi`)
  - Python cache (`__pycache__/`, `*.pyc`)
  - Virtual environments (`venv/`, `env/`)
  - Log files (`*.log`, `logs/`)

- **Personal Files**: 
  - IDE settings (`.vscode/`, `.idea/`)
  - OS files (`Thumbs.db`, `.DS_Store`)
  - Temporary files (`*.tmp`, `*.bak`)

**What TO commit:**
- Source code in `src/`
- Documentation in `docs/`
- Build scripts (`build.ps1`, `build_msi.ps1`, `setup.py`)
- Dependencies (`requirements.txt`)
- Configuration templates (without secrets)

> 💡 **Tip**: Run `git status` before committing to verify only intended files are staged. The `.gitignore` file handles most exclusions automatically.

See the complete `.gitignore` file in the repository root for all exclusion rules.

## 🛠️ Building from Source

### Build Standalone Executable

```powershell
# Install build dependencies
pip install pyinstaller

# Build executable
.\build.ps1
```

### Build MSI Installer

```powershell
# Install cx_Freeze
pip install cx-Freeze

# Build MSI
python setup.py bdist_msi
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

PBIP Studio is inspired by amazing open-source Power BI community tools:
- [Tabular Editor 2](https://github.com/TabularEditor/TabularEditor) by Daniel Otykier
- [DAX Studio](https://daxstudio.org/) by Darren Gosbell and the DAX Studio team
- [pbi-tools](https://pbi.tools/) by Mathias Thierbach

## 🌟 Comparison to Similar Tools

| Feature | PBIP Studio | Tabular Editor 2 | DAX Studio |
|---------|-------------|------------------|------------|
| PBIP/TMDL Support | ✅ | ✅ | ❌ |
| Fabric Integration | ✅ | ❌ | ❌ |
| Data Source Migration | ✅ | ⚠️ Manual | ❌ |
| Bulk Renaming | ✅ | ⚠️ Limited | ❌ |
| DAX Query Editor | ❌ | ⚠️ Basic | ✅ |
| Model Analysis | ✅ | ✅ | ✅ |
| Free & Open Source | ✅ | ✅ | ✅ |

## 💬 Support

- **Issues**: [GitHub Issues](../../issues)
- **Discussions**: [GitHub Discussions](../../discussions)
- **Documentation**: [PBIP Studio Docs](docs/)

## 🗺️ Community Roadmap

> **Ideas for future development – not commitments, no deadlines**

### 🚨 Current Focus: Stability & Quality
- Fix known bugs (large models, migrations, auth tokens)
- Add unit tests (parsers, services, workflows)
- Setup CI/CD pipeline (automated testing & builds)
- Refactor large GUI components

### 🚧 Community Ideas (Open for Contribution)

**Intelligence & Analysis**
- Azure AI integration (explain/optimize DAX, generate measures)
- Best Practice Analyzer (performance, naming, security rules)
- Measure dependency explorer (visualize relationships)
- Semantic model diff viewer
- Data lineage visualization

**Data Sources & Integration**
- PostgreSQL, MySQL, Oracle support
- Azure Data Lake Gen2, Databricks SQL
- Dataverse (full support), SAP HANA
- More connector templates

**Enterprise Features**
- Multi-language support (Spanish, French, German, Chinese, Arabic)
- Audit trail (compliance logging, change history)
- CI/CD with Fabric (auto-deploy, Git integration)
- Approval workflows for sensitive operations
- Plugin/extension system

**UI/UX Improvements**
- Command palette (Ctrl+Shift+P like VS Code)
- Keyboard shortcuts for all actions
- Recent files/workspaces quick access
- Customizable toolbar and layouts
- Progress indicators with cancel support
- Drag-and-drop PBIP file import
- Search/filter in all tables
- Export results to Excel/CSV from any view
- Themes and color schemes
- Multi-tab workspace (work on multiple models)

**Developer Experience**
- Replace regex parser with AST (performance & reliability)
- OpenAPI/Swagger documentation
- CLI interface for automation
- Cross-platform support (macOS, Linux)
- Model documentation generator
- Better error messages and logging

### 🗳️ Influence the Roadmap

Vote with 👍 on [GitHub Issues](../../issues). We prioritize based on community interest and contributions.

**This is a community wishlist** – features happen when contributors build them. Want to help? Check issues labeled `good first issue`!

## ⚠️ Disclaimer

This is an independent community project and is not affiliated with, endorsed by, or supported by Microsoft Corporation. Power BI and Microsoft Fabric are trademarks of Microsoft Corporation.

## 📊 Project Status

PBIP Studio is actively maintained and under continuous development. We release updates regularly based on community feedback.

---

**Made with ❤️ by the Power BI Community**
