# Moved Files - Others Old Folder

This folder contains files that were part of the development/testing process but are **NOT required** for running the main Power BI Migration Toolkit application.

## Last Updated
December 18, 2025 - Complete project analysis and cleanup

## Files Moved and Reasons

### 🚫 Unused PowerShell Scripts (Replaced by Python)
- **login.ps1** - Old PowerShell-based authentication (replaced by Python FabricCLIWrapper)
- **publish_to_fabric.ps1** - Old PowerShell upload script (replaced by Python FabricClient in Upload tab)
- Both scripts are legacy from when the project used PowerShell automation

### 🔧 Unused Python Modules
- **powerbi_downloader.py** - XMLA-based downloader for Premium workspaces (not imported anywhere, replaced by FabricClient)

### 📁 Unused Folders
- **scripts/** - Contains download_tmdl.ps1 (PowerShell XMLA script, not referenced in Python code)

### 📝 Development/Historical Documentation
Files that were useful during development but are not needed for end users:
- CHANGES_SUMMARY.md
- download_solution_options.md
- DOWNLOAD_STRATEGY.md
- FABRIC_CLI_IMPLEMENTATION_SUMMARY.md
- FABRIC_CLI_INTEGRATION.md
- FEATURE_COMPARISON.md
- IMPLEMENTATION_GUIDE.md
- IMPLEMENTATION_GUIDE_PBIP.md
- INTEGRATION_GUIDE.md
- POWERSHELL_FIX.md
- PRE_BUILD_CHECKLIST.md
- PROJECT_SUMMARY.txt
- PYTHON_REST_API_MIGRATION.md
- QUICK_START_CHECKLIST.md
- QUICK_SUMMARY_PBIP.md
- SIMPLE_DEPLOYMENT.md

### 🧪 Test Files
All test scripts used during development:
- test_app.py
- test_async_download.py
- test_download_api.py
- test_download_capabilities.py
- test_download_setup.py
- test_fabric_client.py
- test_integration.py
- test_single_download.py
- test_before_build.ps1
- test_fabric_auth.ps1

### 🎨 Alternative/Experimental Apps
- **streamlit_app.py** - Streamlit web app version (not used in final PyQt6 app)
- **tkinter_app.py** - Tkinter desktop app version (not used in final PyQt6 app)
- **quick_start_fabric_cli.py** - Quick start script (not needed in final app)

### 🗑️ Old Build Files
- build_msi.old.ps1
- verify_before_build.ps1

### 📊 Temporary Data Files
- powershell_diagnostics.txt
- import_results.json
- publish_items.json

## ✅ Files That REMAIN in Root (Actively Used by main.py)

### Core Application Files
- **src/main.py** - Main entry point (PyQt6 + FastAPI)
- **src/gui/** - All GUI components
  - main_window.py - Main window
  - fabric_cli_tab_new.py - Download from Fabric tab
  - fabric_upload_tab.py - Upload to Fabric tab
- **src/api/** - FastAPI backend
  - server.py - REST API server
- **src/services/** - Core services
  - indexer.py - File indexing
  - query_service.py - Database queries
  - migration_service.py - Data source migration
  - detail_loader.py - Table details loader
  - fabric_client.py - Fabric API client (Python)
  - fabric_cli_wrapper.py - Fabric CLI wrapper (Python)
- **src/database/** - Database schema
- **src/models/** - Data models
- **src/parsers/** - TMDL parsers
- **src/utils/** - Utilities
  - data_source_migration.py
  - table_rename.py
  - folder_management.py

### Configuration
- **config.md** - User configuration file (loaded by fabric_client.py)
- **requirements.txt** - Python dependencies

### Build Files
- **build.ps1** - Main build script
- **build_msi.ps1** - MSI installer build
- **setup.py** - cx_Freeze setup for MSI
- **powerbi-toolkit.spec** - PyInstaller spec file
- **start.ps1** - Development start script

### Essential Documentation
- **README.md** - Main project documentation
- **GETTING_STARTED.md** - User guide
- **DEPLOYMENT_GUIDE.md** - Deployment instructions
- **AZURE_APP_SETUP.md** - Azure configuration guide
- **FABRIC_CLI_INSTALLATION.md** - Fabric CLI setup
- **BUILD.md** - Build instructions
- **config.template.md** - Configuration template

## 🔍 Analysis Method

Complete dependency analysis performed:
1. ✅ Traced all imports in src/main.py
2. ✅ Traced all imports in src/gui/main_window.py
3. ✅ Verified all src/services/* usage
4. ✅ Confirmed no Python code calls PowerShell scripts
5. ✅ Verified build file requirements

## 📌 Key Findings

**Current Architecture:**
- ✅ **Pure Python** - No PowerShell dependencies
- ✅ **PyQt6** - GUI framework
- ✅ **FastAPI** - Backend REST API
- ✅ **FabricClient** (Python) - All Fabric operations
- ✅ **FabricCLIWrapper** (Python) - CLI integration

**Removed Architecture:**
- ❌ **PowerShell scripts** - login.ps1, publish_to_fabric.ps1
- ❌ **XMLA downloader** - powerbi_downloader.py
- ❌ **Alternative UIs** - Streamlit, Tkinter

## 🔄 Restoration
If you need any of these files for reference or testing, they are preserved here and can be copied back to the root directory.

## 🧹 Impact
Moving these files:
- ✅ Cleaner project structure
- ✅ Faster builds (fewer files to process)
- ✅ Easier navigation for developers
- ✅ No impact on main application functionality
- ✅ All files preserved for historical reference
- ✅ Build files updated (powerbi-toolkit.spec, setup.py)
