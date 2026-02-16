# PBIP Studio - Complete Documentation

**Version:** 1.0.0  
**Last Updated:** December 22, 2025  
**Application Type:** Windows Desktop Application (PyQt6 + FastAPI)

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Quick Start Guide](#quick-start-guide)
3. [Architecture Overview](#architecture-overview)
4. [Core Features](#core-features)
5. [Installation & Setup](#installation--setup)
6. [Azure Configuration](#azure-configuration)
7. [Building & Deployment](#building--deployment)
8. [User Guide](#user-guide)
9. [Technical Documentation](#technical-documentation)
10. [Security & Compliance](#security--compliance)
11. [Troubleshooting](#troubleshooting)
12. [Project Structure](#project-structure)

---

## Executive Summary

### What is PBIP Studio?

PBIP Studio is a comprehensive Windows desktop application designed for enterprise-grade Power BI and Microsoft Fabric migration, management, and transformation. It provides a professional native desktop experience with powerful backend processing capabilities for handling complex Power BI migration scenarios.

### Key Capabilities

- 📊 **Assessment & Indexing**: Analyze and catalog Power BI/Fabric artifacts
- 📥 **Download from Fabric**: Native Python API to download workspaces in PBIP/TMDL format
- 🔄 **Data Source Migration**: Transform connections between different data platforms
- 🏷️ **Table Renaming**: Bulk rename tables with automatic DAX/M query updates
- 📏 **Column Renaming**: Rename columns with intelligent reference updates
- 📤 **Upload to Fabric**: Publish modified items back to Microsoft Fabric
- 💾 **Local Database**: SQLite-based metadata storage and management
- 🔒 **Secure**: Local-only processing, no cloud dependencies

### Technology Stack

- **Frontend**: PyQt6 (Native Windows GUI)
- **Backend**: FastAPI (REST API on localhost:8000)
- **Database**: SQLite (File-based, portable)
- **Language**: Python 3.10+
- **Parser**: Custom TMDL/PBIR/JSON parsers
- **Authentication**: Azure AD Service Principal 

---

## Quick Start Guide

### Prerequisites

- Windows 10/11 (64-bit)
- Python 3.10 or higher (for development)
- 4GB RAM minimum, 8GB recommended
- Internet connection for Fabric API access
- **Valid License Key** (required for production use)

### Option 1: Run from Source (Development)

```powershell
# 1. Navigate to project directory
cd "c:\Users\moham\Documents\Adnan Github Community\PBIP-Studio-App"

# 2. Run quick start script
.\start.ps1
```

The script automatically:
- Creates virtual environment
- Installs dependencies
- Launches the application

**Note**: License activation required on first launch. See [License Activation](#license-activation) section.

### Option 2: Run Standalone Executable

1. Download the `.exe` or install the `.msi` from releases
2. Run the application
3. **License Activation**: On first launch, you'll be prompted to activate your license (see below)

---

## License Activation

### Overview

PowerBI Desktop App uses an offline, machine-locked licensing system:
- ✅ Valid for 1 year from activation
- ✅ Completely offline (no internet required after activation)
- ✅ Machine-locked for security (1 license per computer)
- ✅ Easy activation with copy-paste workflow

### Activation Process

**Step 1: Get Your Machine ID**
- Launch the application
- License dialog appears automatically
- Click the "📋 Copy" button to copy your unique Machine ID
- Email Machine ID to: support@taik18.com

**Step 2: Receive License Key**
- Support will email you a license key within 1-2 hours
- License key format: `PBMT-xxxxx-xxxxx-xxxxx`

**Step 3: Activate**
- Paste license key in the activation dialog
- Click "Activate License"
- App starts normally

### License Features

- **Machine-Locked**: License only works on the specific computer where it's activated
- **Offline Operation**: No internet required after initial activation
- **Revocation Support**: Move license to new computer by revoking on old machine
- **Annual Renewal**: Contact support before expiry for renewal

For detailed license information, see the User Guide section on License Activation.
2. Double-click to run (no Python required)
3. Application launches with all features ready

### First Time Setup

1. **Configure Azure Credentials** (Optional - for Fabric integration):
   - Open Configuration tab
   - Enter Tenant ID, Client ID, and Client Secret
   - Click "Save Configuration"

2. **Index Your First Export**:
   - Go to Assessment tab
   - Select a Power BI export folder
   - Click "Start Indexing"
   - Wait for completion

3. **Ready to Use**: All features are now available!

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PyQt6 Desktop GUI                        │
│  ┌────────┬──────────┬──────────┬──────────┬──────────┐    │
│  │ Config │Assessment│Migration │  Rename  │  Upload  │    │
│  │  Tab   │   Tab    │   Tab    │   Tabs   │   Tab    │    │
│  └────────┴──────────┴──────────┴──────────┴──────────┘    │
│                          ↓↑                                  │
│                    REST API Calls                            │
│                          ↓↑                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         FastAPI Backend (localhost:8000)             │   │
│  │  ┌──────────┬──────────┬──────────┬──────────────┐  │   │
│  │  │ Indexing │  Query   │Migration │ Fabric Client│  │   │
│  │  │ Service  │ Service  │ Service  │   Service    │  │   │
│  │  └──────────┴──────────┴──────────┴──────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                          ↓↑                                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         SQLite Database (fabric_migration.db)        │   │
│  │  Stores: Workspaces, Datasets, Tables, Columns,     │   │
│  │  Relationships, Measures, Data Sources, Queries      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                          ↓↑
         ┌────────────────────────────────┐
         │   Microsoft Fabric REST API    │
         │  (Download/Upload Workspaces)  │
         └────────────────────────────────┘
```

### Component Description

#### Frontend Layer (PyQt6)
- **Main Window**: Tab-based interface with native Windows controls
- **Widgets**: Custom components (progress bars, tables, dialogs)
- **Threading**: Background workers for non-blocking operations
- **Icons**: QtAwesome font icons for modern UI

#### Backend Layer (FastAPI)
- **Server**: Runs in separate daemon thread on port 8000
- **Endpoints**: RESTful API for all operations
- **Services**: Business logic layer (indexing, querying, migration)
- **Parsers**: TMDL/PBIR file parsers for metadata extraction

#### Data Layer (SQLite)
- **Location**: `%LOCALAPPDATA%\PBIP Studio\data\fabric_migration.db`
- **Schema**: 11 tables with foreign key relationships
- **Features**: ACID compliance, full-text search, export to Excel

---

## Core Features

### 1. Configuration Management ⚙️

**Purpose**: Set up Azure AD credentials for Fabric API access

**Features**:
- Configure Service Principal authentication (Tenant ID, Client ID, Client Secret)
- Secure storage in user's AppData directory
- Password visibility toggle with eye icon
- GUID format validation
- Auto-load saved configuration on startup
- Integrated Azure App Registration setup guide

**Configuration File Location**:
```
%LOCALAPPDATA%\PBIP Studio\config.md
```

**Configuration Format**:
```markdown
# Fabric Configuration
tenantId = "your-tenant-id-guid"
clientId = "your-client-id-guid"
clientSecret = "your-client-secret"
```

---

### 2. Download from Fabric 📥

**Purpose**: Download workspaces, semantic models, and reports from Microsoft Fabric

**Authentication Methods**:
- **Service Principal**: Non-interactive, production-ready

**Download Capabilities**:
- **Workspace Discovery**: Auto-scan all available Fabric workspaces
- **Item Selection**: Browse and select semantic models, reports, dashboards
- **Bulk Download**: Process multiple items simultaneously
- **Format Support**: Native PBIP/TMDL format (Power BI Project files)
- **Auto-organized**: Downloads saved to organized folder structure

**Download Location**:
```
%USERPROFILE%\Documents\PBIP-Studio-Downloads\
  └── [WorkspaceName]\
      ├── [Model1.SemanticModel]\
      │   └── definition\
      │       ├── model.tmdl
      │       ├── tables\
      │       ├── relationships\
      │       └── measures\
      ├── [Model2.SemanticModel]\
      └── [Report1.Report]\
```

**Features**:
- Real-time progress tracking per item
- Parallel multi-threaded downloads
- Error recovery and detailed logging
- Automatic folder structure creation

---

### 3. Assessment & Indexing 📊

**Purpose**: Analyze Power BI exports and catalog metadata in local database

**Indexing Process**:
1. Select export folder containing PBIP/TMDL files
2. Click "Start Indexing"
3. Application scans and parses all files
4. Metadata extracted and stored in SQLite database
5. Data available for filtering, searching, and reporting

**What Gets Indexed**:

- ✅ **Workspaces**: Names, IDs, counts
- ✅ **Datasets/Semantic Models**: Paths, sizes, table counts
- ✅ **Tables**: Names, types, column counts, partitions
- ✅ **Columns**: Names, data types, format strings, calculated/regular
- ✅ **Data Sources**: Connection types, servers, databases, authentication
- ✅ **Relationships**: From/To tables and columns, cardinality, active status
- ✅ **Measures**: Names, DAX expressions, format strings, display folders
- ✅ **Power Query (M)**: Complete M code for each table
- ✅ **Partitions**: Modes, source types, query expressions

**Dashboard Views**:

1. **Tables View**: Complete table listing with metadata
2. **Relationships View**: All relationships with cardinality
3. **Measures View**: DAX measure catalog with expressions
4. **Columns View**: Detailed column metadata
5. **Power Query View**: M query expressions with syntax highlighting
6. **Data Sources View**: Connection details and types

**Filtering System**:
- Filter by Workspace
- Filter by Dataset
- Filter by Source Type
- Search tables by name
- Filter relationships by type
- Clear all filters with one click
- Live filter counts

**Export Capabilities**:
- Export entire database to Excel workbook
- Separate worksheets for each entity type
- Perfect for offline analysis and documentation

---

### 4. Data Source Migration 🔄

**Purpose**: Migrate data sources from one platform to another across multiple models

**Supported Source Types**:
- SQL Server (on-premises)
- Azure SQL Database
- Microsoft Fabric Lakehouse
- Snowflake
- Excel Files

**Migration Process**:

1. **Source Detection**:
   - Automatically scans indexed models
   - Detects current data source types
   - Groups tables by data source

2. **Model Selection**:
   - Filter models by source type
   - See count of models using each source
   - Select models to migrate

3. **Target Configuration**:
   - Choose target platform
   - Configure connection parameters
   - Validate configuration

4. **Migration Execution**:
   - Generates new Power Query (M) expressions
   - Updates connection strings and parameters
   - Maintains column mappings and transformations
   - Preserves relationships and measures
   - Creates automatic backups

5. **Validation**:
   - Verifies all references updated
   - Reports success/failure counts
   - Detailed error logging

**Target Platform Options**:

**SQL Server / Azure SQL / Fabric Lakehouse (SQL Endpoint)**:
- Server name
- Database name
- Schema (optional)
- Authentication method

**Snowflake**:
- Account identifier
- Warehouse name
- Database and schema

**Excel**:
- File path or URL
- Worksheet specifications

**Features**:
- **Bulk Migration**: Process hundreds of tables in minutes
- **Atomic Operations**: All or nothing (transaction-safe)
- **Smart Query Generation**: Preserves existing query logic
- **Progress Tracking**: Real-time status for each model
- **Detailed Logging**: Console-style output with timestamps
- **Automatic Backups**: Creates backup before migration

---

### 5. Table Rename 🏷️

**Purpose**: Bulk rename tables across multiple models with automatic reference updates

**Renaming Strategies**:

1. **Add Prefix**: Add text to beginning (e.g., `dim_`, `fact_`)
2. **Add Suffix**: Add text to end (e.g., `_v2`, `_new`)
3. **Prefix + Suffix**: Combine both strategies
4. **Custom Mapping**: Manual table-by-table renaming

**What Gets Updated Automatically**:

- ✅ Table definitions in TMDL files
- ✅ DAX measures (CALCULATE, FILTER, etc.)
- ✅ Calculated columns
- ✅ Relationships (From/To table names)
- ✅ M queries (Power Query references)
- ✅ Row-Level Security (RLS) definitions
- ✅ Calculation groups

**Process**:

1. Select models from indexed database
2. Load all tables from selected models
3. Choose renaming strategy
4. Preview all changes (old name → new name)
5. Manually edit individual names if needed
6. Execute bulk rename
7. All references automatically updated

**Safety Features**:
- Preview before applying changes
- Works on local TMDL files (not production)
- Validation checks for naming conflicts
- Detailed change logs
- Automatic backups created
- Can be tested locally before re-importing to Fabric

---

### 6. Column Rename 📏

**Purpose**: Bulk rename columns across multiple tables with intelligent reference updates

**Transformation Options**:

**Case Conversions**:
- `snake_to_pascal`: `customer_id` → `CustomerId`
- `pascal_to_snake`: `CustomerId` → `customer_id`
- `camel_to_pascal`: `customerId` → `CustomerId`
- `pascal_to_camel`: `CustomerId` → `customerId`
- `kebab_to_pascal`: `customer-id` → `CustomerId`
- `snake_to_camel`: `customer_id` → `customerId`

**Other Transformations**:
- **uppercase**: Convert to UPPERCASE
- **lowercase**: Convert to lowercase
- **title_case**: Convert To Title Case
- **remove_spaces**: RemoveAllSpaces
- **spaces_to_underscores**: Spaces → Underscores
- **remove_prefix**: Remove common prefixes (col_, fld_, dim_, fact_)
- **remove_suffix**: Remove common suffixes (_id, _key, _name, _date)

**Prefix/Suffix Operations**:
- Add prefix to column names
- Add suffix to column names
- Combine with case transformations

**What Gets Updated Automatically**:

- ✅ Column definitions in table TMDL files
- ✅ DAX expressions in measures
- ✅ DAX expressions in calculated columns
- ✅ DAX expressions in calculated tables
- ✅ M queries in Power Query
- ✅ Relationships (fromColumn/toColumn)
- ✅ Source column references

**Process**:

1. **Filter**: Select Workspace → Dataset → Table
2. **Load Columns**: Load columns from selected table
3. **Transform**: Choose transformation strategy
4. **Preview**: Review changes in preview table
5. **Edit**: Manually adjust individual column names
6. **Execute**: Bulk rename with automatic reference updates

**Preview Table Columns**:
- Workspace Name
- Model Name
- Table Name
- Current Column Name (read-only)
- New Column Name (editable)
- Column Type (string, int64, etc.)
- Calculated Column? (Yes/No)

---

### 7. Upload to Fabric 📤

**Purpose**: Publish modified semantic models and reports back to Microsoft Fabric

**Upload Capabilities**:

**Workspace Management**:
- Browse all available Fabric workspaces
- Filter workspaces by name
- Select target workspace for upload

**Upload Modes**:
1. **Create New Items**: Upload as new semantic models/reports
2. **Update Existing Items**: Update by name matching or ID mapping

**Item Types Supported**:
- Semantic Models (.SemanticModel folders)
- Reports (.Report folders)
- Dashboards (JSON definitions)

**Upload Process**:

1. Select source folder containing modified items
2. Browse and select target workspace
3. Choose items to upload
4. Configure conflict resolution
5. Execute batch upload
6. Monitor progress per item

**Features**:
- **Batch Upload**: Upload multiple items simultaneously
- **Parallel Processing**: Individual progress per item
- **Conflict Resolution**: Overwrite, skip, or rename on conflict
- **Progress Tracking**: Real-time upload speed and ETA
- **Post-Upload Validation**: Verify items exist and are accessible
- **Detailed Logging**: API responses and error messages

**Upload Source Location**:
```
Documents\PBIP-Studio-Downloads\
[WorkspaceName]\
  ├── [Model.SemanticModel]\  → Upload to Fabric
  └── [Report.Report]\         → Upload to Fabric
```

---

### 8. Backup & Connection Management 🔄

**Purpose**: Ensure safe modifications and proper local development workflow

**Backup Manager**:

**Automatic Backups**:
- Created before any model operation (migration, rename, etc.)
- Timestamped for easy identification
- Organized by workspace and operation type

**Backup Structure**:
```
Export_Root/
├── Raw Files/
│   └── WorkspaceName/
│       └── ModelName.SemanticModel/
└── BACKUP/
    └── WorkspaceName/
        ├── ModelName_migration_20251220_143022/
        ├── ModelName_table_rename_20251220_150000/
        └── ModelName_column_rename_20251220_153000/
```

**Connection Manager (PBIR)**:

**Connection Types**:

1. **Local Connection** (for development):
```json
{
  "datasetReference": {
    "byPath": {
      "path": "ModelName.SemanticModel"
    }
  }
}
```

2. **Fabric Connection** (for publishing):
```json
{
  "datasetReference": {
    "byConnection": {
      "connectionString": "Data Source=powerbi://api.powerbi.com/v1.0/myorg/{workspace_id};Initial Catalog={model_name};..."
    }
  }
}
```

**Workflow**:
1. Before modification: Create backup, set reports to local connections
2. Perform modifications on Raw Files
3. Test locally with Power BI Desktop
4. Restore Fabric connections from backup
5. Upload to Fabric with correct connections

---

## Installation & Setup

### Option 1: Development Installation

**Step 1: Install Python**
1. Download Python 3.10+ from [python.org](https://www.python.org/downloads/)
2. During installation, check "Add Python to PATH"
3. Verify: `python --version`

**Step 2: Clone/Copy Project**
```powershell
cd "C:\Your\Project\Location"
# Or copy the PBIP-Studio-App folder
```

**Step 3: Create Virtual Environment**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If execution policy error:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Step 4: Install Dependencies**
```powershell
pip install -r requirements.txt
```

**Step 5: Run Application**
```powershell
python src/main.py
```

Or use quick start script:
```powershell
.\start.ps1
```

---

### Option 2: Standalone Executable

**Build EXE (Single File)**:
```powershell
.\build.ps1 -BuildType exe
```

Output: `dist\PBIP-Studio.exe` (~150-200MB)

**Features**:
- Single executable file
- No Python installation required
- Portable - run from any location
- All dependencies bundled

---

### Option 3: MSI Installer (IT Distribution)

**Build MSI Installer**:
```powershell
.\build_msi.ps1
```

Or manually:
```powershell
python setup.py bdist_msi
```

Output: `dist\PBIP Studio-1.0.0-win64.msi`

**MSI Includes**:
- ✅ Application executable
- ✅ SQLite database with schema (ready to use)
- ✅ Configuration template
- ✅ All documentation
- ✅ All required libraries

**Installation**:
1. Double-click MSI file
2. Follow installation wizard
3. Installs to `C:\Program Files\PBIP Studio`
4. Creates Start Menu shortcut
5. Database is pre-initialized and ready

**Update Existing Installation**:
- Run new MSI installer
- Automatically upgrades existing installation
- Preserves existing database and configuration

---

## Azure Configuration

### Required: Azure AD App Registration

PBIP Studio requires an Azure AD App Registration with specific permissions to access Microsoft Fabric workspaces.

### Step 1: Create App Registration

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click **New registration**
4. **Name**: `PBIP-Studio`
5. **Supported account types**: Accounts in this organizational directory only
6. Click **Register**

### Step 2: Configure API Permissions

**Required Delegated Permissions**:
- ✅ `Workspace.Read.All`
- ✅ `Workspace.ReadWrite.All`
- ✅ `Dataset.Read.All`
- ✅ `Dataset.ReadWrite.All`
- ✅ `Report.Read.All`
- ✅ `Report.ReadWrite.All`

**Required Application Permissions**:
- ✅ `Tenant.Read.All`
- ✅ `Workspace.Read.All`
- ✅ `Dataset.Read.All`
- ✅ `Report.Read.All`

**Steps**:
1. Click **API permissions**
2. Click **Add a permission**
3. Select **Power BI Service**
4. Add delegated and application permissions listed above
5. **IMPORTANT**: Click **Grant admin consent for [Your Organization]**

### Step 3: Create Client Secret

1. Click **Certificates & secrets**
2. Click **New client secret**
3. Description: `PowerBI Toolkit Secret`
4. Expires: Choose duration (24 months recommended)
5. Click **Add**
6. **COPY THE SECRET VALUE IMMEDIATELY** (can't view again)

### Step 4: Get Credentials

You need three values:

1. **Tenant ID**: Overview tab → Directory (tenant) ID
2. **Client ID**: Overview tab → Application (client) ID
3. **Client Secret**: The value you copied in Step 3

### Step 5: Enable Service Principal in Power BI

**CRITICAL**: Must be enabled by Power BI Admin

1. Go to [Power BI Admin Portal](https://app.powerbi.com/admin-portal)
2. Navigate to **Tenant settings**
3. Scroll to **Developer settings**
4. Enable: **Service principals can access Power BI APIs**
5. Select **Specific security groups** or **The entire organization**
6. Click **Apply**
7. **Wait 15-30 minutes** for propagation

### Step 6: Add Service Principal to Workspaces

For each workspace you want to access:

1. Open workspace in Power BI Service
2. Click **Workspace settings** (gear icon)
3. Click **Access**
4. Add your app by name (`PBIP-Studio`)
5. Grant role: **Admin** or **Member**
6. Click **Add**

### Step 7: Configure in Application

1. Launch PBIP Studio
2. Go to **Configuration** tab
3. Enter:
   - Tenant ID
   - Client ID
   - Client Secret
4. Click **Save Configuration**
5. Test connection by clicking **Test Connection**

---

## Building & Deployment

### Development Build Tools

**Required**:
```powershell
pip install pyinstaller cx-Freeze
```

### Building EXE (PyInstaller)

**Using Build Script** (Recommended):
```powershell
.\build.ps1 -BuildType exe
```

**Manual Build**:
```powershell
pyinstaller PBIP-Studio.spec
```

**Output**: `dist\PBIP-Studio.exe`

**Spec File Configuration**:
- Located at: `PBIP-Studio.spec`
- Customizable: Hidden imports, data files, exclusions
- Icon: `pbip-studio.ico`

### Building MSI (cx_Freeze)

**Using Build Script** (Recommended):
```powershell
.\build_msi.ps1
```

**Manual Build**:
```powershell
python setup.py bdist_msi
```

**Output**: `dist\PBIP Studio-1.0.0-win64.msi`

**Setup.py Configuration**:
- Application name and version
- Include files (docs, database, logos)
- Package dependencies
- MSI options (install path, icon, upgrade code)

### Build Options Comparison

| Aspect | EXE (PyInstaller) | MSI (cx_Freeze) |
|--------|-------------------|-----------------|
| **File Size** | ~150-200MB | ~200-250MB |
| **Installation** | No installation needed | Installs to Program Files |
| **Portability** | Fully portable | Installed system-wide |
| **Uninstall** | Just delete file | Use Windows uninstaller |
| **Updates** | Replace file | Install new MSI (auto-upgrade) |
| **IT Acceptance** | Good | Excellent |
| **Admin Rights** | No | Yes (for installation) |

### Code Signing (Recommended)

To avoid "Unknown Publisher" warnings:

```powershell
signtool sign /f your-certificate.pfx /p password /t http://timestamp.digicert.com dist\PBIP-Studio.exe
```

**Benefits**:
- Removes security warnings
- Increases user trust
- Required for enterprise distribution
- Prevents antivirus false positives

---

## User Guide

### Getting Started

**1. First Launch**:
- Application creates necessary directories automatically
- Database is initialized in `%LOCALAPPDATA%\PBIP Studio\data\`
- Configuration file template created

**2. Configuration Tab**:
- **Optional**: Configure Azure AD credentials for Fabric integration
- **Required for**: Download from Fabric, Upload to Fabric
- **Not required for**: Assessment, Migration, Rename (local operations)

**3. Assessment Tab**:
- Select a Power BI export folder
- Click "Start Indexing"
- Wait for completion
- Browse indexed metadata in dashboard

### Typical Workflows

#### Workflow 1: Analyze Power BI Export

```
1. Export workspace from Fabric → PBIP/TMDL format
2. Launch PBIP Studio
3. Go to Assessment tab
4. Select export folder
5. Click "Start Indexing"
6. Explore metadata in dashboard views
7. Export to Excel for reporting
```

#### Workflow 2: Migrate Data Sources

```
1. Index Power BI export (Assessment tab)
2. Go to Migration tab
3. Filter models by source type
4. Select models to migrate
5. Configure target platform
6. Preview affected tables
7. Execute migration
8. Review migration logs
9. Test locally with Power BI Desktop
10. Upload to Fabric (Upload tab)
```

#### Workflow 3: Bulk Table Rename

```
1. Index Power BI export
2. Go to Rename Tables tab
3. Select models
4. Load tables
5. Choose renaming strategy (prefix/suffix)
6. Preview changes
7. Execute bulk rename
8. Test locally
9. Upload to Fabric
```

#### Workflow 4: Download → Modify → Upload

```
1. Configure Azure credentials (Configuration tab)
2. Download workspace (Download tab)
3. Index downloaded files (Assessment tab)
4. Make modifications (Migration/Rename tabs)
5. Test locally with Power BI Desktop
6. Upload back to Fabric (Upload tab)
```

### UI Navigation

**Tab Organization**:
- **Configuration**: Azure AD setup and testing
- **Download from Fabric**: Browse and download workspaces
- **Assessment**: Index and analyze exports
- **Migration**: Data source transformation
- **Rename Tables**: Bulk table renaming
- **Rename Columns**: Bulk column renaming
- **Upload to Fabric**: Publish back to Fabric

**Common UI Elements**:
- **Progress Bars**: Show operation status
- **Status Bar**: Bottom of window, shows connection and operation status
- **Tables**: Sortable columns (click header), resizable columns (drag border)
- **Filters**: Dropdown menus with counts
- **Buttons**: Color-coded (Green=execute, Blue=info, Red=clear)

---

## Technical Documentation

### Project Structure

```
PBIP-Studio-App/
├── src/
│   ├── main.py                      # Application entry point
│   ├── gui/                         # PyQt6 UI components
│   │   ├── main_window.py           # Main window (all tabs)
│   │   ├── fabric_cli_tab_new.py    # Download from Fabric
│   │   ├── fabric_upload_tab.py     # Upload to Fabric
│   │   └── widgets/                 # Custom widgets
│   │       ├── preview_dialog.py
│   │       └── side_by_side_diff.py
│   ├── api/                         # FastAPI backend
│   │   ├── server.py                # REST API server
│   │   └── routes/                  # API endpoints
│   ├── database/                    # Database layer
│   │   └── schema.py                # SQLite schema and manager
│   ├── models/                      # Data models
│   │   ├── __init__.py
│   │   ├── workspace.py
│   │   ├── dataset.py
│   │   ├── data_object.py
│   │   └── data_source.py
│   ├── parsers/                     # File parsers
│   │   ├── __init__.py
│   │   ├── base_parser.py
│   │   └── powerbi_parser.py        # TMDL/PBIR parser
│   ├── services/                    # Business logic
│   │   ├── __init__.py
│   │   ├── indexer.py               # Indexing service
│   │   ├── query_service.py         # Database queries
│   │   ├── migration_service.py     # Migration logic
│   │   ├── fabric_client.py         # Fabric REST API client
│   │   ├── fabric_cli_wrapper.py    # Fabric CLI Python wrapper
│   │   └── detail_loader.py         # Detail loader
│   └── utils/                       # Utilities
│       ├── data_source_migration.py # Migration utilities
│       ├── table_rename.py          # Table rename utilities
│       ├── column_rename.py         # Column rename utilities
│       ├── backup_manager.py        # Backup management
│       └── pbir_connection_manager.py # PBIR connection manager
├── data/                            # Data directory (auto-created)
│   └── fabric_migration.db          # SQLite database
├── logos/                           # Application logos
├── requirements.txt                 # Python dependencies
├── setup.py                         # MSI installer config
├── PBIP-Studio.spec             # PyInstaller config
├── pbip-studio.spec                 # Alternative spec file
├── build.ps1                        # Build script
├── build_msi.ps1                    # MSI build script
├── start.ps1                        # Quick start script
└── COMPLETE_DOCUMENTATION.md        # This file
```

### Database Schema

**Tables**:

1. **bi_tools**: BI tool registry (Power BI, Tableau, etc.)
2. **workspaces**: Fabric workspaces
3. **datasets**: Semantic models/datasets
4. **data_objects**: Tables, sheets, queries
5. **columns**: Column definitions
6. **data_sources**: Connection details
7. **relationships**: Table relationships
8. **measures**: DAX measures
9. **power_query**: M query expressions
10. **migration_history**: Migration audit trail
11. **assessment_findings**: Assessment results

**Key Relationships**:
- `workspaces` → `datasets` (one-to-many)
- `datasets` → `data_objects` (one-to-many)
- `data_objects` → `columns` (one-to-many)
- `data_objects` → `data_sources` (one-to-many)
- `data_objects` → `measures` (one-to-many)
- `data_objects` → `power_query` (one-to-one)

**Database Location**:
```
%LOCALAPPDATA%\PBIP Studio\data\fabric_migration.db
```

### API Endpoints (FastAPI)

**Base URL**: `http://127.0.0.1:8000`

**Endpoints**:

- `GET /` - Health check
- `GET /api/workspaces` - List workspaces
- `GET /api/datasets` - List datasets
- `GET /api/data-objects` - List tables/objects
- `GET /api/data-sources` - List data sources
- `GET /api/relationships` - List relationships
- `GET /api/measures` - List measures
- `GET /api/columns` - List columns
- `POST /api/index` - Index export folder
- `POST /api/migrate` - Execute migration
- `GET /api/statistics` - Database statistics

**CORS Configuration**:
- Restricted to localhost only
- Allowed origins: `http://127.0.0.1:8000`, `http://localhost:8000`
- Allowed methods: GET, POST, DELETE
- Credentials: Enabled

### Dependencies

**Core Requirements** (from `requirements.txt`):

```
# GUI Framework
PyQt6>=6.6.0
PyQt6-WebEngine>=6.6.0
qtawesome>=1.3.0

# Backend API
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.6

# Data Processing
pandas>=2.0.0
openpyxl>=3.1.0
plotly>=5.18.0

# Azure Authentication
azure-identity>=1.15.0
msal>=1.26.0

# Microsoft Fabric CLI
ms-fabric-cli>=0.1.0

# Utilities
python-dotenv>=1.0.0
pydantic>=2.5.0
requests>=2.31.0

# Packaging
pyinstaller>=6.3.0
cx-Freeze>=6.15.0
```

### Threading Model

**Main Thread** (Qt Application):
- UI rendering and user interaction
- Event handling
- Signal/slot connections

**Backend Thread** (FastAPI):
- Daemon thread
- Runs uvicorn server
- Handles API requests
- Non-blocking for UI

**Worker Threads** (QThread):
- Indexing operations
- Migration execution
- Download/upload operations
- Progress updates via signals

**Thread Safety**:
- SQLite connection with `check_same_thread=False`
- Qt signals for cross-thread communication
- Thread-safe data sharing via Queue/locks where needed

---

## Security & Compliance

### Security Audit Summary

**Overall Security Rating**: ⭐⭐⭐⭐⭐⭐⭐⭐☆☆ (8/10)

| Category | Status |
|----------|--------|
| **PHI/PII Data Handling** | ✅ SAFE - No PHI/PII collected |
| **Malicious Libraries** | ✅ SAFE - All dependencies verified |
| **Code Injection Risks** | ✅ SAFE - No eval/exec usage |
| **Credential Security** | ⚠️ MEDIUM - Plaintext storage |
| **API Security** | ✅ FIXED - CORS restricted |
| **Subprocess Execution** | ✅ SAFE - Minimal usage |
| **Network Security** | ✅ SAFE - HTTPS only |

### Data Handling

**What is Processed**:
- ✅ Power BI metadata (workspace names, dataset names, table names)
- ✅ Data model structure (columns, relationships, measures)
- ✅ Power Query M expressions (connection logic)
- ✅ DAX formulas and calculations

**What is NOT Processed**:
- ❌ Actual data values from reports or datasets
- ❌ Personal information of any kind
- ❌ Protected Health Information (PHI)
- ❌ Payment card information

**Data Storage**:
1. **SQLite Database**: Metadata only (names, IDs, structure)
2. **Configuration File**: Azure credentials (plaintext - see recommendations)
3. **Log Files**: Application events (no sensitive data logged)

**HIPAA Compliance**: ✅ N/A - Application does not handle PHI

**GDPR Compliance**: ✅ Minimal Risk - Only technical metadata, no personal data

### Credential Security

**Current Implementation**:
- Credentials stored in plaintext in `config.md`
- File location: `%LOCALAPPDATA%\PBIP Studio\config.md`
- File system permissions protect access

**Risk Assessment**:
- **Severity**: Medium
- **Likelihood**: Low (requires local file system access)
- **Impact**: High (Azure credentials could be compromised)

**Mitigations in Place**:
- ✅ File stored in user-specific AppData (not shared)
- ✅ Configuration tab validates GUID format
- ✅ `.gitignore` excludes config.md
- ✅ Uses official Azure SDK

**Recommended Improvements**:

1. **Windows Credential Manager (DPAPI)**:
   - Encrypt credentials using Windows Data Protection API
   - Stored in Windows Credential Manager
   - Only accessible to current user

2. **Azure Key Vault**:
   - Store client secret in Azure Key Vault
   - Application retrieves at runtime
   - Requires additional Azure setup

3. **Certificate-based Authentication**:
   - Use certificate instead of client secret
   - More secure for production
   - Requires certificate management

### Network Security

**HTTPS Enforcement**:
- All Fabric API calls use HTTPS
- TLS certificate validation enabled
- No insecure HTTP connections

**Local API Server**:
- Binds to localhost (127.0.0.1) only
- Not accessible from network
- CORS restricted to localhost

**No Telemetry**:
- No data sent to external servers
- No tracking or analytics
- All processing local

---

## Troubleshooting

### Common Issues

#### Issue: "Python not found"

**Symptoms**: Error when running scripts

**Solution**:
1. Reinstall Python from [python.org](https://www.python.org/downloads/)
2. During installation, check "Add Python to PATH"
3. Verify: `python --version` in PowerShell
4. Restart PowerShell after installation

---

#### Issue: "Cannot run scripts" (Execution Policy)

**Symptoms**: PowerShell scripts won't execute

**Solution**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

#### Issue: "Module not found" errors

**Symptoms**: Import errors when running application

**Solution**:
```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Reinstall all dependencies
pip install -r requirements.txt --force-reinstall
```

---

#### Issue: Backend API not starting

**Symptoms**: Application opens but features don't work

**Solution 1: Port Conflict**:
```powershell
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Kill process using port (replace PID)
taskkill /F /PID <PID>
```

**Solution 2: Change Port**:
Edit `src/main.py` line ~115:
```python
backend = BackendThread(port=8001)  # Use different port
```

---

#### Issue: Database lock error

**Symptoms**: "Database is locked" error

**Solution**:
```powershell
# Close all instances of application

# Delete journal file if exists
cd "%LOCALAPPDATA%\PBIP Studio\data"
del fabric_migration.db-journal

# Restart application
```

---

#### Issue: "Found 0 workspaces" when downloading from Fabric

**Symptoms**: No workspaces appear in download list

**Solutions**:

1. **Check Service Principal Permissions**:
   - Verify admin consent granted in Azure Portal
   - Confirm Service Principal enabled in Power BI tenant settings
   - Wait 15-30 minutes after enabling

2. **Add Service Principal to Workspaces**:
   - Open each workspace in Power BI Service
   - Add your app as Admin or Member

3. **Verify Credentials**:
   - Check Tenant ID, Client ID, Client Secret are correct
   - GUIDs should not have extra quotes or spaces

4. **Test Connection**:
   - Use "Test Connection" button in Configuration tab
   - Check application logs for detailed error messages

---

#### Issue: Migration not updating all references

**Symptoms**: Some table/column references not updated

**Solution**:
1. Ensure you've indexed the export first (Assessment tab)
2. Check backup was created (indicates successful start)
3. Review migration logs for errors
4. Test locally with Power BI Desktop
5. Report issues with example files

---

#### Issue: Application won't start (EXE/MSI)

**Symptoms**: Double-click does nothing or crashes immediately

**Solution 1: Check Logs**:
```
%LOCALAPPDATA%\PBIP Studio\logs\app.log
```

**Solution 2: Missing Dependencies**:
- Install Visual C++ Redistributable from Microsoft
- Ensure .NET Framework 4.8+ installed

**Solution 3: Antivirus Blocking**:
- Add exception for application in antivirus
- Submit to antivirus vendor for whitelist

---

#### Issue: Qt Platform Plugin error

**Symptoms**: "Could not find the Qt platform plugin..."

**Solution** (development only):
```powershell
# Reinstall PyQt6
pip uninstall PyQt6 PyQt6-Qt6
pip install PyQt6 --force-reinstall
```

For built EXE, this shouldn't occur. If it does, rebuild with:
```powershell
.\build.ps1 -BuildType exe
```

---

### Debug Mode

Enable detailed logging:

1. **Check Log Files**:
```
%LOCALAPPDATA%\PBIP Studio\logs\app.log
```

2. **Increase Log Level**:
Edit `src/main.py`, change:
```python
logging.basicConfig(level=logging.DEBUG)  # Was INFO
```

3. **Check API Server**:
Open browser to: `http://127.0.0.1:8000/docs`
(FastAPI Swagger documentation)

---

### Getting Help

**Log Files to Include**:
1. Application log: `%LOCALAPPDATA%\PBIP Studio\logs\app.log`
2. Database location: `%LOCALAPPDATA%\PBIP Studio\data\fabric_migration.db`
3. Configuration (redact secrets): `%LOCALAPPDATA%\PBIP Studio\config.md`

**Information to Provide**:
- Windows version
- Python version (if running from source)
- Application version (see Help → About)
- Steps to reproduce issue
- Error messages from logs
- Screenshots if relevant

---

## Additional Information

### Performance Considerations

**System Requirements**:
- **Minimum**: 4GB RAM, dual-core CPU
- **Recommended**: 8GB+ RAM, quad-core CPU
- **Storage**: 500MB for application, additional for downloads and database

**Performance Metrics**:
- **Indexing**: ~1000 TMDL files per minute
- **Migration**: ~50 tables per minute
- **Download**: Limited by network bandwidth
- **Database**: Handles millions of records efficiently

**Optimization Tips**:
- Use filters to reduce data displayed in tables
- Export large datasets to Excel for external analysis
- Close other applications during large migrations
- Use SSD for better database performance

---

### Known Limitations

1. **Windows Only**: Currently supports Windows 10/11 only (PyQt6 is cross-platform, but testing done on Windows)
2. **Fabric Workspaces**: Download feature requires Microsoft Fabric workspaces (not classic Power BI Service)
3. **TMDL Format**: Works with PBIP/TMDL format files (modern format)
4. **Single Database**: One SQLite database per installation (can export/import for sharing)
5. **No Real-time Sync**: Changes not synced to Fabric automatically (manual upload required)

---

### Roadmap & Future Features

**Planned Enhancements**:
- [ ] Git integration for version control
- [ ] Dataflow upload/download support
- [ ] Automated testing and validation
- [ ] Schedule migrations
- [ ] Email notifications
- [ ] Custom plugin system
- [ ] PowerShell module
- [ ] REST API for automation
- [ ] Multi-tenant support
- [ ] Collaboration features
- [ ] Linux/Mac support
- [ ] Dark mode theme
- [ ] Advanced DAX analysis
- [ ] Impact analysis before migration
- [ ] Rollback capability

---

### Contributing

This project is currently maintained as an internal tool. For suggestions or bug reports, please use the internal communication channels.

---

### Credits & Acknowledgments

**Built with**:
- **PyQt6**: Cross-platform GUI framework
- **FastAPI**: Modern web framework for APIs
- **SQLite**: Lightweight database engine
- **Azure Identity**: Microsoft authentication library
- **Pandas**: Data manipulation library

**Special Thanks**:
- Microsoft Power BI team for TMDL/PBIP format
- Microsoft Fabric team for REST API
- Python community for excellent libraries

---

### License

MIT License

Copyright (c) 2025 PBIP Studio

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## Document Version

**Version**: 1.0.0  
**Last Updated**: December 22, 2025  
**Covers Application Version**: 1.0.0

---

## Quick Reference

### File Locations

```
Application Directory:
C:\Program Files\PBIP Studio\

User Data Directory:
%LOCALAPPDATA%\PBIP Studio\
├── config.md
├── data\
│   └── fabric_migration.db
└── logs\
    └── app.log

Downloads Directory:
%USERPROFILE%\Documents\PBIP-Studio-Downloads\
```

### Important Commands

```powershell
# Run from source
python src/main.py

# Build EXE
.\build.ps1 -BuildType exe

# Build MSI
.\build_msi.ps1

# Install dependencies
pip install -r requirements.txt

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Check Python version
python --version

# Check port usage
netstat -ano | findstr :8000
```

### Support Contacts

- **Technical Issues**: Check `%LOCALAPPDATA%\PBIP Studio\logs\app.log`
- **Documentation**: This file (COMPLETE_DOCUMENTATION.md)
- **Azure Setup**: See [Azure Portal](https://portal.azure.com)

---

**End of Documentation**

*This document consolidates all information from the PBIP Studio project. For specific technical details, refer to the source code comments and inline documentation.*
