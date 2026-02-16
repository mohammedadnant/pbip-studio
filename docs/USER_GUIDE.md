# PBIP Studio - User Guide

**Version:** 1.0.0  
**Last Updated:** December 22, 2025  
**Application Type:** Windows Desktop Application

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [License Activation](#license-activation)
4. [Getting Started](#getting-started)
5. [Azure Configuration](#azure-configuration)
6. [Core Features](#core-features)
7. [Common Workflows](#common-workflows)
8. [Troubleshooting](#troubleshooting)
9. [Support & Help](#support--help)

---

## Overview

### What is PBIP Studio?

PBIP Studio is a developer utility for Power BI professionals working with Microsoft Fabric and Power BI semantic models. It's designed to help you work more efficiently with PBIP/TMDL files, automate repetitive tasks, and streamline your Power BI development workflow.

### Who is this for?

- 🎯 **Power BI Developers**: Working with semantic models and PBIP format
- 🔧 **Data Engineers**: Managing data source migrations and transformations
- 📊 **BI Consultants**: Handling multiple client projects and standardization
- 🚀 **DevOps Teams**: Automating Power BI deployment pipelines

### What Can You Do?

- 📊 **Analyze Your Models**: Index and explore semantic models, tables, measures, and relationships
- 📥 **Download from Fabric**: Pull down workspaces in PBIP/TMDL format for local development
- 🔄 **Migrate Data Sources**: Quickly switch between SQL Server, Azure SQL, Snowflake, or Fabric Lakehouse
- 🏷️ **Bulk Table Rename**: Add prefixes/suffixes (like `dim_`, `fact_`) with automatic DAX updates
- 📏 **Column Transformations**: Convert naming conventions (snake_case ↔ PascalCase) across models
- 📤 **Deploy to Fabric**: Push your changes back to Microsoft Fabric workspaces
- 💾 **Local Metadata DB**: SQLite database for fast searching and reporting
- 🔒 **Offline-First**: All processing happens locally on your machine

### Why Use PBIP Studio?

**Save Time**: Instead of manually updating hundreds of DAX measures when renaming tables, let PBIP Studio do it in seconds.

**Standardize Naming**: Apply consistent naming conventions across multiple models (e.g., add `dim_` prefix to all dimension tables).

**Analyze Faster**: Index your semantic models once, then search and filter through tables, columns, measures, and relationships instantly.

**Version Control Friendly**: Work with PBIP/TMDL text files that integrate seamlessly with Git.

**No Lock-In**: Everything runs locally. No subscriptions, no cloud dependencies (except when you want to sync with Fabric).

### How It Works

- **Desktop App**: Native Windows application built with PyQt6 - fast and responsive
- **Local Database**: SQLite stores all metadata on your machine (`%LOCALAPPDATA%\PBIP Studio\data\`)
- **File-Based**: Works directly with PBIP/TMDL files (the modern Power BI project format)
- **REST API**: Internal FastAPI backend (localhost:8000) handles parsing and transformations
- **Privacy**: All processing is local - nothing sent to external servers unless you explicitly use Fabric sync features

---

## Installation

### System Requirements

- **Operating System**: Windows 10 or Windows 11 (64-bit)
- **RAM**: 4GB minimum, 8GB recommended for large models
- **Storage**: 500MB for application + space for your semantic models and downloads
- **Internet**: Only needed for Fabric download/upload features (offline work fully supported)
- **Power BI Desktop**: Optional but recommended for testing modified models locally

### Installing the Application

1. **Download the MSI Installer**
   - File name: `PBIP Studio-1.0.0-win64.msi`
   - Size: ~200-250MB

2. **Run the Installer**
   - Double-click the MSI file
   - If prompted by Windows security, click "Run" or "Install"
   - Follow the installation wizard
   - Default installation path: `C:\Program Files\PBIP Studio`

3. **Complete Installation**
   - Installation takes 1-2 minutes
   - A shortcut is added to your Start Menu
   - Application is ready to use immediately

4. **First Launch**
   - Click the Start Menu shortcut or desktop icon
   - Application creates necessary folders automatically
   - Database is initialized and ready

### Updating the Application

When a new version is released:

1. Download the new MSI installer
2. Run the installer (it will automatically detect and upgrade the existing installation)
3. Your database and configuration are preserved
4. Launch the updated application

### Uninstalling

1. Open Windows Settings → Apps → Installed apps
2. Find "PBIP Studio"
3. Click "Uninstall"
4. Your database and configuration files remain in your user folder (can be manually deleted if desired)

---

## License Activation

### Overview

PowerBI Desktop App requires a valid license to run. Each license is locked to a specific computer for security and is valid for one year from activation.

### First Launch - Activation Required

When you launch the application for the first time (or after license expiry), you'll see the **License Activation Dialog**:

![License Dialog shows logo, Machine ID with Copy button, and license key input field]

### Step 1: Get Your Machine ID

1. **Locate Machine Information Section**
   - Your unique Machine ID is displayed in white, bold text
   - Format: `3fd26d46a6cf64ae` (16 characters)

2. **Copy Your Machine ID**
   - Click the blue **"📋 Copy"** button
   - Your Machine ID is now copied to clipboard

3. **Send Machine ID to Support**
   - Email your Machine ID to: **support@taik18.com**
   - Subject: "License Request - [Your Name]"
   - Body: Paste your Machine ID

### Step 2: Receive License Key

- **Delivery Time**: Within 1-2 hours (max 24 hours)
- You'll receive an email with your license key
- License key format: `PBMT-xxxxx-xxxxx-xxxxx`

### Step 3: Activate License

1. **Enter License Key**
   - Paste the entire license key into the input field
   - Make sure there are no extra spaces or line breaks

2. **Click "Activate License"**
   - The app validates your key offline
   - If successful, you'll see a confirmation message

3. **Start Using the App**
   - App opens normally after activation
   - License is stored securely on your computer
   - No internet required for subsequent launches

### License Information

**What You Get:**
- ✅ Valid for 1 year from activation date
- ✅ Works completely offline (no internet needed)
- ✅ Locked to your specific computer (secure)
- ✅ Free updates during license period

**Important Notes:**
- 🔒 **Machine-Locked**: License only works on the computer where you activated it
- 📧 **Keep Your Key Safe**: You'll need it if you reinstall Windows or the app
- 🔄 **Moving to New PC**: Contact support to revoke and reactivate on new machine
- ⏰ **Renewal**: Contact support before expiry for renewal license

### Checking License Status

**View License Information:**
1. Click the **🔑 (key icon)** in the top-right corner of the app
2. See your license details:
   - Email address
   - Expiration date
   - Days remaining
   - Machine ID

**Expiry Warning:**
- If less than 30 days remaining, you'll see a warning
- Contact support@taik18.com for renewal
- App continues to work until expiration date

### Moving to a New Computer

**If you need to move your license to a different computer:**

1. **On Old Computer** (if accessible):
   - Click the 🔑 icon → "Revoke License"
   - Confirm revocation
   - App will close

2. **On New Computer**:
   - Install the application
   - Launch and copy your new Machine ID
   - Email new Machine ID to support@taik18.com
   - Support will send you a new license key for the new machine

3. **If Old Computer Not Accessible**:
   - Just send your new Machine ID to support
   - They'll issue a new license for your new machine

### Troubleshooting Activation

**"Invalid signature - key may be tampered"**
- Make sure you copied the entire license key
- Check for extra spaces at beginning or end
- Key is case-sensitive - don't modify it
- Contact support if problem persists

**"License is locked to a different machine"**
- This means the license was generated for a different computer
- Send your correct Machine ID to support
- They'll generate a new license for your machine

**"License expired"**
- Your 1-year license period has ended
- Contact support@taik18.com for renewal
- They'll send you a new license key

**Can't Find Machine ID**
- Machine ID is in the License Activation dialog
- It's shown in white/bold text under "Machine Information"
- Use the "📋 Copy" button to copy it easily

**License Keys Are Sent Via Email Within 1-2 Hours (Max 24 Hours) After Purchase**
- Check your spam/junk folder if you don't receive it
- Contact support@taik18.com if delayed

### Support Contact

**For License Issues:**
- Email: support@taik18.com
- Include: Your Machine ID (copy from dialog)
- Response time: 1-2 business days

---

## Getting Started

### First Launch (After Activation)

Once your license is activated, the application will start normally:

1. **Automatic Setup**
   - Creates data folder: `%LOCALAPPDATA%\PBIP Studio\`
   - Initializes SQLite database with schema
   - Generates config template for Azure credentials
   - Starts internal REST API on localhost:8000

2. **Main Window**
   - Clean tab-based interface (7 main tabs)
   - Status bar shows connection status and operation progress
   - Responsive UI - operations run in background threads

### Understanding the Interface

**Main Tabs** (left to right):

1. **Configuration** ⚙️: Set up Azure credentials for Fabric integration
2. **Download from Fabric** 📥: Browse and download workspaces from Microsoft Fabric
3. **Assessment** 📊: Index and analyze Power BI exports
4. **Migration** 🔄: Transform data sources between platforms
5. **Rename Tables** 🏷️: Bulk rename tables with automatic updates
6. **Rename Columns** 📏: Bulk rename columns with automatic updates
7. **Upload to Fabric** 📤: Publish modified items back to Fabric

### Quick Start Workflow

**Option 1: Index Local PBIP Files** (No Azure needed)

If you already have Power BI models in PBIP/TMDL format:

1. Go to **Assessment** tab
2. Click "Select Export Folder"
3. Browse to your `.SemanticModel` folder
4. Click "Start Indexing"
5. Wait for completion (~1000 files per minute)
6. Browse tables, measures, relationships in the dashboard

**Option 2: Download from Fabric** (Requires Azure setup)

Pull down workspaces from Microsoft Fabric:

1. **Setup**: Configure Azure credentials in Configuration tab (see next section)
2. Go to **Download from Fabric** tab
3. Click "Browse Workspaces" (lists all accessible workspaces)
4. Check items you want (semantic models, reports)
5. Click "Download Selected"
6. Files saved to: `%USERPROFILE%\Documents\PBIP-Studio-Downloads\[WorkspaceName]\`

**Tip for Developers**: Downloaded files are organized by workspace and ready to open in Power BI Desktop or commit to Git.

---

## Azure Configuration

### Why Configure Azure?

Azure configuration is **optional** and only needed if you want to:
- ✅ Download semantic models/reports from Fabric to your local machine
- ✅ Upload/deploy your modified models back to Fabric workspaces

**You don't need Azure if:**
- ❌ You're only working with local PBIP files
- ❌ You're just analyzing, migrating, or renaming (local operations)
- ❌ You export/import models manually through Power BI Desktop

**Developer Note**: Service Principal authentication is non-interactive and perfect for automation scripts.

### What You Need

You need three pieces of information from Azure:

1. **Tenant ID**: Your organization's Azure directory ID
2. **Client ID**: Application (client) ID from Azure App Registration
3. **Client Secret**: Secret value from Azure App Registration

**Note**: Your IT administrator or Azure administrator must create an Azure App Registration and provide these credentials. See the section below for what they need to configure.

### Configuring in the Application

1. **Open Configuration Tab**
   - Click the "Configuration" tab

2. **Enter Credentials**
   - **Tenant ID**: Your Azure AD tenant GUID (format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
   - **Client ID**: Application (client) ID from App Registration
   - **Client Secret**: Secret value (shown once when created)
   - Toggle eye icon to show/hide secret

3. **Save Configuration**
   - Click "Save Configuration"
   - Saved to: `%LOCALAPPDATA%\PBIP Studio\config.md`
   - Format:
     ```markdown
     # Fabric Configuration
     tenantId = "your-tenant-id-guid"
     clientId = "your-client-id-guid"
     clientSecret = "your-client-secret"
     ```

4. **Test Connection** (Optional)
   - Click "Test Connection" to verify
   - Checks if credentials can authenticate to Fabric API
   - Status bar shows success/failure

**Developer Tip**: Configuration file is plain text markdown. You can edit it directly or store credentials in environment variables for CI/CD.

### Information for Your IT Administrator

Your IT/Azure administrator needs to:

1. **Create Azure App Registration**
   - Portal: [Azure Portal](https://portal.azure.com) → Azure Active Directory → App registrations
   - Name: `PBIP-Studio`

2. **Configure API Permissions**
   - Add Power BI Service permissions
   - Grant admin consent
   
   Required permissions:
   - `Workspace.Read.All`
   - `Workspace.ReadWrite.All`
   - `Dataset.Read.All`
   - `Dataset.ReadWrite.All`
   - `Report.Read.All`
   - `Report.ReadWrite.All`

3. **Enable Service Principal**
   - Power BI Admin Portal → Tenant settings → Developer settings
   - Enable "Service principals can access Power BI APIs"

4. **Add to Workspaces**
   - Add the app to each workspace you need to access
   - Grant "Admin" or "Member" role

5. **Create Client Secret**
   - Generate a client secret
   - Provide the Tenant ID, Client ID, and Client Secret to you

---

## Core Features

### 1. Configuration Management ⚙️

**Purpose**: Set up Azure AD credentials for Fabric API access

**How to Use**:
1. Open Configuration tab
2. Enter Tenant ID, Client ID, and Client Secret (provided by your IT admin)
3. Click "Save Configuration"
4. Optionally test the connection

**Features**:
- Secure storage in your user profile
- Password visibility toggle
- Auto-load saved configuration on startup
- Integrated Azure setup guide

---

### 2. Download from Fabric 📥

**Purpose**: Pull semantic models and reports from Microsoft Fabric to your local machine for development

**Prerequisites**: Azure credentials configured (Configuration tab)

**Authentication**: Service Principal (non-interactive, perfect for automation)

**How to Use**:

1. **Browse Workspaces**
   - Click "Browse Workspaces" button
   - Application scans all Fabric workspaces you have access to
   - Tree view shows workspaces → items hierarchy

2. **Select Items to Download**
   - Expand workspaces to see contents
   - Check boxes for semantic models (.SemanticModel) or reports (.Report)
   - Multi-select supported

3. **Download**
   - Click "Download Selected"
   - Individual progress bar per item
   - Multi-threaded parallel downloads
   - Real-time status updates

**What Gets Downloaded**:
- **Semantic Models**: Complete `.SemanticModel` folder with TMDL files
  - `definition/model.tmdl` - Model metadata
  - `definition/tables/` - Table definitions
  - `definition/relationships/` - Relationship definitions
  - `definition/measures/` - DAX measures
- **Reports**: `.Report` folders with PBIR files

**Download Location**:
```
%USERPROFILE%\Documents\PBIP-Studio-Downloads\
  └── [WorkspaceName]\        ← Organized by workspace
      ├── [Model1.SemanticModel]\  ← Ready to open in Power BI Desktop
      │   └── definition\
      │       ├── model.tmdl
      │       ├── tables\*.tmdl
      │       ├── relationships\*.tmdl
      │       └── measures\*.tmdl
      └── [Report1.Report]\         ← Report definition
          └── definition.pbir
```

**Developer Tips**:
- Downloaded files are in PBIP format (Power BI Project) - Git-friendly text files
- Open `.SemanticModel` folder directly in Power BI Desktop
- Parallel downloads: ~5-10 items simultaneously depending on size
- Performance: ~1000 TMDL files per minute indexing speed
```

---

### 3. Assessment & Indexing 📊

**Purpose**: Parse PBIP/TMDL files and build a searchable local database of all metadata

**How to Use**:

1. **Select Source Folder**
   - Click "Select Export Folder"
   - Browse to folder containing `.SemanticModel` folders
   - Can be downloaded files or exported from Power BI Desktop

2. **Start Indexing**
   - Click "Start Indexing"
   - Parser scans all TMDL/PBIR files recursively
   - Progress bar shows files processed
   - Typical speed: ~1000 files/minute

3. **Explore Indexed Data**
   - Multiple dashboard views with filters
   - Real-time search across all metadata
   - Export to Excel for offline analysis

**What Gets Indexed** (11 database tables):

- ✅ **Workspaces**: Names, IDs, item counts
- ✅ **Datasets/Semantic Models**: Paths, sizes, table counts
- ✅ **Tables**: Names, types, source types, column counts, partitions
- ✅ **Columns**: Names, data types, format strings, calculated vs regular
- ✅ **Data Sources**: Connection types, servers, databases, auth methods
- ✅ **Relationships**: From/To tables+columns, cardinality, cross-filter direction, active status
- ✅ **Measures**: Names, DAX expressions, format strings, display folders
- ✅ **Power Query (M)**: Complete M code for each table transformation
- ✅ **Partitions**: Modes (import/DirectQuery), source types, query expressions

**Database Details**:
- **Location**: `%LOCALAPPDATA%\PBIP Studio\data\fabric_migration.db`
- **Type**: SQLite (single file, portable)
- **Schema**: 11 tables with foreign key relationships
- **Features**: ACID compliance, full-text search, export to Excel

**Dashboard Views**:

1. **Tables View**: Complete table catalog with source type, column count, relationships
2. **Relationships View**: All table relationships with cardinality (1:*, *:1, 1:1)
3. **Measures View**: DAX measure library with full expressions
4. **Columns View**: Column catalog with data types and calculated column flag
5. **Power Query View**: M query expressions with syntax highlighting
6. **Data Sources View**: Connection strings, server names, authentication types

**Filtering System**:
- 🔍 **Workspace Filter**: Dropdown shows all indexed workspaces
- 🔍 **Dataset Filter**: Cascading filter based on workspace selection
- 🔍 **Type Filter**: By source type (SQL, Snowflake, Lakehouse, etc.)
- 🔍 **Search Box**: Real-time text search across names
- 🔍 **Relationship Filter**: By cardinality type
- 🧹 **Clear All**: Reset filters with one click
- 📊 **Live Counts**: Shows filtered vs total counts

**Export to Excel**:
- Click "Export to Excel" in any view
- Generates multi-worksheet workbook
- Separate sheets for: Tables, Columns, Relationships, Measures, Queries, Data Sources
- Perfect for documentation or sharing with team

**Developer Use Cases**:
- 📝 **Documentation**: Generate data dictionary from semantic models
- 🔍 **Impact Analysis**: Find all measures using a specific table/column
- 🔄 **Migration Planning**: Identify data sources that need migration
- 📊 **Metadata Reports**: Export to Excel for stakeholder review

---

### 4. Data Source Migration 🔄

**Purpose**: Automatically transform data source connections across multiple semantic models

**Common Developer Scenarios**:
- Moving from on-prem SQL Server to Azure SQL Database
- Migrating to Fabric Lakehouse (SQL endpoint)
- Switching to Snowflake data warehouse
- Testing with different environments (dev/staging/prod)

**Prerequisites**: Models must be indexed first (Assessment tab)

**Supported Platforms**:

| Source | Target |
|--------|--------|
| SQL Server | Azure SQL, Snowflake, Fabric Lakehouse |
| Azure SQL | Snowflake, Fabric Lakehouse |
| Excel | SQL Server, Azure SQL |
| Any | Any (with custom config) |

**How It Works**:

1. **Source Detection**
   - Scans indexed models for data source types
   - Groups tables by source (SQL Server, Excel, Snowflake, etc.)
   - Shows count of models per source

2. **Model Selection**
   - Filter: Show only models using specific source type
   - Multi-select models to migrate
   - Preview affected tables

3. **Target Configuration**
   
   **For SQL Server / Azure SQL / Fabric Lakehouse (SQL Endpoint)**:
   ```
   Server: yourserver.database.windows.net
   Database: YourDatabase
   Schema: dbo (optional)
   ```
   
   **For Snowflake**:
   ```
   Account: xy12345.us-east-1
   Warehouse: COMPUTE_WH
   Database: ANALYTICS
   Schema: PUBLIC
   ```
   
4. **Migration Execution**
   - **Smart M Query Generation**: Rewrites Power Query with new source
   - **Preserves Transformations**: All query steps maintained
   - **Updates Connection Strings**: Changes server/database references
   - **Maintains Relationships**: All table joins preserved
   - **Keeps DAX Logic**: Measures and calculations unchanged
   - **Automatic Backup**: Creates timestamped backup before changes

5. **Validation & Testing**
   - Console shows real-time progress
   - Success/failure count per model
   - Detailed error logs
   - Test locally in Power BI Desktop before uploading

**What Gets Updated**:
- ✅ Data source definitions in model.tmdl
- ✅ M queries (Power Query expressions)
- ✅ Connection strings and credentials
- ✅ Table partition source queries

**What Stays the Same**:
- ✅ All DAX measures and calculations
- ✅ All relationships and cardinality
- ✅ All column mappings
- ✅ Visual/report definitions

**Performance**:
- Bulk processing: ~50 tables per minute
- Atomic operations: All-or-nothing per model
- Progress tracking: Real-time console output

**Safety Features**:
- 📦 **Automatic Backups**: `BACKUP/` folder with timestamp
- 📋 **Detailed Logs**: Every change logged to console
- 💾 **Local-Only**: Changes to local files, not production
- ✅ **Testable**: Open in Power BI Desktop before deploying

**Developer Workflow**:
```
1. Index models → 2. Select & Configure → 3. Migrate → 4. Test in Desktop → 5. Deploy to Fabric
```

---

### 5. Table Rename 🏷️

**Purpose**: Bulk rename tables with automatic updates to all DAX and M query references

**Common Use Cases**:
- 📊 Add `dim_` / `fact_` prefixes for star schema standards
- 🔢 Version control: Add `_v2` suffix for schema updates
- 🧹 Clean up inconsistent naming across models
- 🔄 Standardize naming conventions across projects

**Prerequisites**: Models must be indexed (Assessment tab)

**Renaming Strategies**:

1. **Add Prefix**: `Customer` → `dim_Customer`
2. **Add Suffix**: `Sales` → `Sales_v2`
3. **Prefix + Suffix**: `Product` → `dim_Product_current`
4. **Custom Mapping**: Manual rename table by table

**How to Use**:

1. **Select Models**
   - Filter by workspace/dataset if needed
   - Check models containing tables to rename
   - Click "Load Tables" button

2. **Choose Strategy**
   - Select: Prefix, Suffix, or Both
   - Enter text (e.g., `dim_`, `_v2`)
   - Preview updates in real-time

3. **Preview & Edit**
   - Table shows: `Current Name → New Name`
   - Double-click "New Name" column to manually edit
   - Fix any naming conflicts

4. **Execute Rename**
   - Click "Execute Bulk Rename"
   - Watch console for progress
   - Automatic backup created before changes

**What Gets Updated Automatically**:

✅ **TMDL Files**: Table definitions
```tmdl
table Customer          →  table dim_Customer
```

✅ **DAX Measures**: All table references
```dax
SUM(Customer[Sales])    →  SUM(dim_Customer[Sales])
CALCULATE([Total], Customer[Active] = TRUE)
                        →  CALCULATE([Total], dim_Customer[Active] = TRUE)
```

✅ **Calculated Columns**: Table references in expressions
```dax
RELATED(Customer[Name]) →  RELATED(dim_Customer[Name])
```

✅ **Relationships**: From/To table names
```tmdl
fromTable: Customer     →  fromTable: dim_Customer
toTable: Sales          →  toTable: fact_Sales
```

✅ **M Queries**: Power Query table references
```m
= #"Customer"           →  = #"dim_Customer"
```

✅ **Row-Level Security**: RLS role definitions
```dax
[Region] = USERPRINCIPALNAME()
```

**Example Scenario**:

**Before**:
- `Customer`, `Product`, `Date`, `Sales`, `Orders`

**Apply**: Add `dim_` to dimensions, `fact_` to facts

**After**:
- `dim_Customer`, `dim_Product`, `dim_Date`, `fact_Sales`, `fact_Orders`
- All 47 measures automatically updated
- All 12 relationships automatically updated
- All M queries automatically updated

**Safety & Validation**:
- 📦 Automatic backup: `BACKUP/[Model]_table_rename_[timestamp]/`
- ⚠️ Naming conflict detection
- 📋 Detailed change log in console
- 💾 Test locally before uploading to Fabric

**Developer Tips**:
- Works on TMDL text files - perfect for Git diffs
- Backup folder preserves original for easy rollback
- Test in Power BI Desktop before deploying
- Can batch rename across 100+ tables in seconds

---

### 6. Column Rename 📏

**Purpose**: Bulk rename columns with intelligent updates to all DAX measures, M queries, and relationships

**Developer Use Cases**:
- 🔤 Convert legacy snake_case to PascalCase
- 🧹 Clean up source system naming (remove prefixes like `col_`, `fld_`)
- 📊 Standardize naming conventions across team
- 🔄 Apply corporate naming standards to imported models

**Prerequisites**: Models must be indexed (Assessment tab)

**Transformation Options**:

**Case Conversions** (most popular):
```
snake_to_pascal:  customer_id      →  CustomerId
                  first_name       →  FirstName
                  order_date       →  OrderDate

pascal_to_snake:  CustomerId       →  customer_id
                  FirstName        →  first_name

camel_to_pascal:  customerId       →  CustomerId
                  firstName        →  FirstName

pascal_to_camel:  CustomerId       →  customerId
                  FirstName        →  firstName

kebab_to_pascal:  customer-id      →  CustomerId
                  first-name       →  FirstName

snake_to_camel:   customer_id      →  customerId
                  first_name       →  firstName
```

**Other Transformations**:
```
uppercase:         CustomerId      →  CUSTOMERID
lowercase:         CustomerId      →  customerid
title_case:        customer name   →  Customer Name
remove_spaces:     Customer Name   →  CustomerName
spaces_to_underscores: Customer Name → Customer_Name
remove_prefix:     col_CustomerID  →  CustomerID
remove_suffix:     CustomerID_key  →  CustomerID
```

**Custom Prefix/Suffix**:
- Add prefix: `ID` → `pk_ID`
- Add suffix: `Date` → `Date_UTC`
- Combine with transformations: `customer_id` → `pk_CustomerId`

**How to Use**:

1. **Filter to Table**
   - Workspace dropdown → Dataset dropdown → Table dropdown
   - Cascading filters narrow down selection
   - Click "Load Columns"

2. **Choose Transformation**
   - Select from dropdown (e.g., `snake_to_pascal`)
   - OR add custom prefix/suffix
   - Preview updates instantly

3. **Preview Changes**
   - Table shows:
     - Workspace, Model, Table (read-only)
     - Current Column Name (read-only)
     - **New Column Name (EDITABLE)**
     - Column Type (string, int64, datetime, etc.)
     - Calculated Column? (Yes/No)
   - Click in "New Column Name" to manually adjust

4. **Execute Rename**
   - Click "Execute Bulk Rename"
   - Console shows progress per file
   - Automatic backup created

**What Gets Updated Automatically**:

✅ **Column Definitions** (TMDL):
```tmdl
column customer_id      →  column CustomerId
    dataType: int64
```

✅ **DAX Measures**:
```dax
SUM(Customers[customer_id])  →  SUM(Customers[CustomerId])
CALCULATE([Total], Customers[first_name] = "John")
                             →  CALCULATE([Total], Customers[FirstName] = "John")
```

✅ **Calculated Columns**:
```dax
[full_name] = [first_name] & " " & [last_name]
           →  [FullName] = [FirstName] & " " & [LastName]
```

✅ **M Queries** (Power Query):
```m
= Table.SelectColumns(Source, {"customer_id", "first_name"})
→ = Table.SelectColumns(Source, {"CustomerId", "FirstName"})
```

✅ **Relationships**:
```tmdl
fromColumn: customer_id  →  fromColumn: CustomerId
toColumn: customer_id    →  toColumn: CustomerId
```

**Example Workflow**:

**Scenario**: Legacy SQL database uses `snake_case`, team standard is `PascalCase`

**Before**:
- `customer_id`, `first_name`, `last_name`, `email_address`, `created_date`
- 15 measures referencing these columns
- 3 calculated columns using these in expressions
- 2 relationships on `customer_id`

**Apply**: `snake_to_pascal` transformation

**After**:
- `CustomerId`, `FirstName`, `LastName`, `EmailAddress`, `CreatedDate`
- All 15 measures automatically updated
- All 3 calculated columns automatically updated
- All 2 relationships automatically updated
- All M query steps automatically updated

**Performance**:
- Process: ~50 columns per minute (depends on reference count)
- Smart parsing: Only updates actual references, not string literals

**Safety Features**:
- 📦 Automatic backup: `BACKUP/[Model]_column_rename_[timestamp]/`
- 📋 Detailed logs: Every file change logged
- 🔍 Smart detection: Distinguishes column refs from string values
- 💾 Test before deploy: Open in Power BI Desktop

**Developer Tips**:
- Process one table at a time for large models
- Use preview to verify transformations before executing
- Check calculated columns carefully - some may need manual review
- Git diff shows exact text changes in TMDL files

---

### 7. Upload to Fabric 📤

**Purpose**: Deploy your modified semantic models and reports back to Microsoft Fabric

**Prerequisites**: 
- Azure credentials configured (Configuration tab)
- Modified `.SemanticModel` or `.Report` folders ready
- Target workspace access (Contributor or Admin role)

**How to Use**:

1. **Select Source Folder**
   - Click "Select Source Folder"
   - Browse to folder containing modified items
   - Typical path: `%USERPROFILE%\Documents\PBIP-Studio-Downloads\[WorkspaceName]\`

2. **Browse Target Workspace**
   - Click "Browse Workspaces"
   - Dropdown shows all accessible workspaces
   - Select destination workspace

3. **Select Items to Upload**
   - Check boxes for items to upload
   - Can select multiple semantic models and reports
   - Shows item type and size

4. **Configure Upload Options**
   - **Conflict Resolution**:
     - **Overwrite**: Replace existing item with same name
     - **Skip**: Don't upload if exists
     - **Rename**: Create new item with suffix (e.g., `_copy`)

5. **Execute Upload**
   - Click "Upload Selected"
   - Individual progress bar per item
   - Real-time upload speed and ETA
   - Console shows detailed API responses

**What Can Be Uploaded**:
- ✅ **Semantic Models**: `.SemanticModel` folders → Fabric semantic model
- ✅ **Reports**: `.Report` folders → Fabric report

**Upload Features**:
- 🔄 **Parallel Upload**: Multiple items simultaneously
- 📊 **Progress Tracking**: Per-item progress bars
- ⚡ **Conflict Handling**: Automatic resolution based on settings
- ✅ **Post-Upload Validation**: Verifies items accessible after upload
- 📝 **Detailed Logging**: API responses, error messages, timing info

**Developer Workflow**:
```
Local Changes → Test in Power BI Desktop → Upload to Dev Workspace → Test in Service → Promote to Prod
```

**Upload Location Structure**:
```
Documents\PBIP-Studio-Downloads\
└── [WorkspaceName]\
    ├── SalesModel.SemanticModel\     ← Upload this
    │   └── definition\
    │       ├── model.tmdl
    │       ├── tables\
    │       └── relationships\
    └── SalesReport.Report\           ← Upload this
        └── definition.pbir
```

**Developer Tips**:
- 🧪 **Test First**: Always test in dev workspace before production
- 📦 **Version Control**: Commit TMDL changes to Git before uploading
- 🔄 **Incremental Uploads**: Upload changed models individually
- 🛡️ **Safety**: Use "Skip" conflict mode to avoid accidental overwrites
- 📊 **Monitor**: Watch console for API responses and errors

**Common Upload Scenarios**:

**Scenario 1: Deploy After Migration**
```
1. Migrated SQL → Azure SQL locally
2. Tested in Power BI Desktop ✓
3. Upload to Dev workspace
4. Refresh in Fabric to test connections
5. If good → Upload to Prod
```

**Scenario 2: Deploy After Rename**
```
1. Renamed tables with dim_/fact_ prefixes
2. Verified all measures updated ✓
3. Opened in Desktop - no errors ✓
4. Upload to workspace
5. Reports automatically use new names
```

**Troubleshooting Uploads**:
- ❌ "Access Denied" → Check workspace role (need Contributor+)
- ❌ "Item Exists" → Use Overwrite mode or rename item
- ❌ "Invalid Format" → Ensure .SemanticModel folder structure intact
- ❌ "Connection Failed" → Verify Azure credentials in Configuration tab

---

## Common Workflows

### Workflow 1: Analyze a Power BI Export

**Goal**: Understand what's in a Power BI export

**Steps**:
1. Get PBIP/TMDL export files (downloaded from Fabric or exported elsewhere)
2. Open PBIP Studio
3. Go to **Assessment** tab
4. Click "Select Export Folder" → choose export folder
5. Click "Start Indexing" → wait for completion
6. Explore data in various views (Tables, Relationships, Measures, etc.)
7. Use filters to focus on specific workspaces/datasets
8. Click "Export to Excel" to save analysis

**Result**: Complete catalog of all metadata, exportable to Excel

---

### Workflow 2: Migrate SQL Server to Azure SQL

**Goal**: Change all SQL Server connections to Azure SQL Database

**Steps**:
1. Index the export (Assessment tab)
2. Go to **Migration** tab
3. Filter source type: "SQL Server"
4. Select models to migrate
5. Configure Azure SQL target:
   - Server: `yourserver.database.windows.net`
   - Database: `YourDatabase`
   - Schema: `dbo`
6. Click "Execute Migration"
7. Wait for completion
8. Review console logs for success
9. Test locally with Power BI Desktop
10. Upload back to Fabric (Upload tab)

**Result**: All selected models now connect to Azure SQL

---

### Workflow 3: Standardize Table Naming

**Goal**: Add `dim_` prefix to dimension tables

**Steps**:
1. Index the export (Assessment tab)
2. Go to **Rename Tables** tab
3. Select models containing dimension tables
4. Click "Load Tables"
5. Select dimension tables from list
6. Choose "Add Prefix"
7. Enter prefix: `dim_`
8. Preview changes
9. Click "Execute Bulk Rename"
10. Test locally
11. Upload to Fabric

**Result**: All dimension tables renamed with `dim_` prefix, all references updated

---

### Workflow 4: Convert Column Names to PascalCase

**Goal**: Change column naming convention from snake_case to PascalCase

**Steps**:
1. Index the export (Assessment tab)
2. Go to **Rename Columns** tab
3. Filter to specific workspace/dataset/table
4. Click "Load Columns"
5. Select transformation: `snake_to_pascal`
6. Preview changes in table
7. Manually adjust any columns if needed
8. Click "Execute Bulk Rename"
9. Repeat for other tables
10. Test locally
11. Upload to Fabric

**Result**: All columns in PascalCase, all formulas and queries updated

---

### Workflow 5: Download → Modify → Upload

**Goal**: Complete round-trip modification workflow

**Steps**:
1. **Configure** (Configuration tab)
   - Enter Azure credentials
   - Save configuration

2. **Download** (Download tab)
   - Browse workspaces
   - Select items to download
   - Download to local folder

3. **Index** (Assessment tab)
   - Select downloaded folder
   - Start indexing

4. **Modify** (Migration/Rename tabs)
   - Make desired changes (migration, rename, etc.)
   - Test locally with Power BI Desktop

5. **Upload** (Upload tab)
   - Select modified folder
   - Choose target workspace
   - Upload items back to Fabric

**Result**: Complete migration cycle from Fabric and back

---

## Troubleshooting

### Application Won't Start

**Problem**: Double-clicking application does nothing

**Solutions**:

1. **Check Windows Security**
   - Right-click application
   - Select "Properties"
   - If you see "Unblock" checkbox, check it and click OK
   - Try launching again

2. **Run as Administrator**
   - Right-click application
   - Select "Run as administrator"

3. **Check Antivirus**
   - Temporarily disable antivirus
   - Try launching application
   - If it works, add exception to antivirus

4. **Reinstall**
   - Uninstall application
   - Download fresh MSI
   - Install again

---

### "Found 0 Workspaces" in Download Tab

**Problem**: No workspaces appear when browsing

**Solutions**:

1. **Verify Credentials**
   - Go to Configuration tab
   - Check Tenant ID, Client ID, Client Secret are correct
   - No extra spaces or quotes
   - Try "Test Connection"

2. **Check with IT Admin**
   - Confirm Azure App Registration exists
   - Confirm admin consent was granted
   - Confirm service principal is enabled in Power BI tenant settings
   - Wait 15-30 minutes after enabling

3. **Add to Workspaces**
   - Ask Power BI workspace owners to add the app to their workspaces
   - App needs "Admin" or "Member" role

---

### Indexing Fails or Takes Too Long

**Problem**: Indexing stops or runs for hours

**Solutions**:

1. **Check Folder Structure**
   - Ensure folder contains PBIP/TMDL files
   - Look for `.SemanticModel` folders with `definition` subfolders

2. **Reduce Scope**
   - Index smaller folders first
   - Index workspace by workspace

3. **Check Disk Space**
   - Ensure enough disk space available
   - Database grows as it indexes

4. **Close Other Applications**
   - Free up memory
   - Close Power BI Desktop if open

---

### Migration Doesn't Update All References

**Problem**: Some DAX/M queries not updated after migration

**Solutions**:

1. **Ensure Indexed First**
   - Always index before migration
   - Migration relies on indexed metadata

2. **Check Backups**
   - Backups created? Migration started successfully
   - No backup? Migration didn't run

3. **Review Console Logs**
   - Read detailed error messages
   - Look for specific files that failed

4. **Test Locally**
   - Open modified .pbip file in Power BI Desktop
   - Check for errors
   - Manually fix if needed

---

### Upload Fails

**Problem**: Upload to Fabric returns errors

**Solutions**:

1. **Verify Workspace Access**
   - Confirm you have access to target workspace
   - Need "Contributor" or higher role

2. **Check File Structure**
   - Ensure folder structure intact
   - `.SemanticModel` folders must have `definition` subfolder

3. **Check Item Names**
   - No special characters in item names
   - No duplicate names in workspace

4. **Review Console Logs**
   - Check API error messages
   - Common errors: permissions, naming conflicts

---

### Database Lock Error

**Problem**: "Database is locked" error message

**Solutions**:

1. **Close All Instances**
   - Close all copies of the application
   - Check Task Manager for any remaining processes

2. **Delete Journal File**
   - Navigate to: `%LOCALAPPDATA%\PBIP Studio\data\`
   - Delete file: `fabric_migration.db-journal` (if exists)
   - Restart application

---

### Port 8000 Already in Use

**Problem**: Backend API won't start

**Solutions**:

1. **Check for Conflicts**
   - Open PowerShell
   - Run: `netstat -ano | findstr :8000`
   - See if another program is using port 8000

2. **Close Conflicting Program**
   - Identify process ID (PID) from netstat output
   - Open Task Manager
   - Find process by PID
   - End process

3. **Restart Computer**
   - If unsure which program is using port
   - Restart computer
   - Launch application

---

## Support & Help

### Getting Help

**Check Log Files**:
- Location: `%LOCALAPPAT A%\PBIP Studio\logs\app.log`
- Contains detailed error messages and operation logs
- Include relevant portions when reporting issues

**Information to Provide**:
- Windows version (Windows 10 or 11?)
- Application version (see Help → About)
- Steps to reproduce the issue
- Error messages from logs
- Screenshots if relevant

### File Locations Reference

**Application Installation**:
```
C:\Program Files\PBIP Studio\
```

**User Data**:
```
%LOCALAPPDATA%\PBIP Studio\
├── config.md                    (Azure credentials)
├── data\
│   └── fabric_migration.db      (Local database)
└── logs\
    └── app.log                  (Application logs)
```

**Downloads**:
```
%USERPROFILE%\Documents\PBIP-Studio-Downloads\
```

To open these locations:
- Press `Windows + R`
- Type the path (e.g., `%LOCALAPPDATA%\PBIP Studio`)
- Press Enter

---

## Quick Reference

### Common Keyboard Shortcuts

- `Ctrl + Tab`: Switch between tabs
- `Ctrl + F`: Focus search box (in views with search)
- `F5`: Refresh current view
- `Ctrl + Q`: Quit application

### File Types You'll See

- `.SemanticModel`: Folder containing semantic model definition
- `.Report`: Folder containing report definition
- `.tmdl`: Tabular Model Definition Language file (metadata)
- `.pbir`: Power BI Report file (JSON configuration)
- `.m`: Power Query M formula file
- `.db`: SQLite database file

### Status Bar Indicators

Bottom of window shows:
- **Ready**: Application ready for operations
- **Indexing...**: Currently indexing files
- **Migrating...**: Migration in progress
- **Connected**: Azure credentials configured and valid
- **Not Connected**: Azure credentials not configured or invalid

---

## Best Practices

### Before Making Changes

1. ✅ **Always index first** (Assessment tab)
2. ✅ **Test locally** with Power BI Desktop before uploading
3. ✅ **Verify backups** were created (check BACKUP folder)
4. ✅ **Start with small scope** (one workspace, one model)
5. ✅ **Review console logs** after operations

### During Migration

1. ✅ **Don't close application** during operations
2. ✅ **Watch progress bars** and console
3. ✅ **Wait for completion** messages
4. ✅ **Read error messages** carefully
5. ✅ **Check backups** after any changes

### After Changes

1. ✅ **Open in Power BI Desktop** to validate
2. ✅ **Check all relationships** still work
3. ✅ **Test DAX measures** return expected results
4. ✅ **Verify data source connections** work
5. ✅ **Upload to test workspace** first before production

---

## Frequently Asked Questions

**Q: Do I need Python installed?**  
A: No, the MSI installer includes everything needed.

**Q: Is my data sent anywhere?**  
A: No, all processing is local. Only Fabric API calls (when you upload/download) go to Microsoft.

**Q: Can I use this on Mac or Linux?**  
A: Not currently, Windows only.

**Q: What if I don't have Azure credentials?**  
A: You can still use Assessment, Migration, and Rename features on local files. Only Download and Upload require Azure.

**Q: Will this modify my production workspaces?**  
A: Only when you explicitly upload. All local operations work on copies of files.

**Q: Can multiple people use this?**  
A: Yes, each user installs on their own computer with their own database and configuration.

**Q: Is there a cost?**  
A: The application is free. You need Power BI/Fabric licenses for accessing workspaces.

**Q: Can I automate this?**  
A: Not currently, it's designed for interactive use.

**Q: What's the difference between this and Power BI Desktop?**  
A: This is for bulk operations and migrations. Power BI Desktop is for creating/editing individual reports.

**Q: Can I undo a migration?**  
A: Yes, automatic backups are created. Restore from the BACKUP folder.

---

## About

**Version**: 1.0.0  
**Release Date**: December 2025  
**Platform**: Windows 10/11

**Built with**:
- PyQt6 (User Interface)
- FastAPI (Backend Processing)
- SQLite (Local Database)
- Microsoft Azure Identity (Authentication)

---

**End of User Guide**

*For technical details or development information, refer to the Complete Documentation (COMPLETE_DOCUMENTATION.md).*
