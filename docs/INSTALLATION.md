# PBIP Studio Installation Guide

## Table of Contents
- [System Requirements](#system-requirements)
- [Installation Options](#installation-options)
- [First Launch](#first-launch)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements
- **Operating System**: Windows 10 (64-bit) or Windows 11
- **RAM**: 4GB
- **Storage**: 500MB for application
- **Display**: 1280x720 resolution
- **Internet**: Optional (only needed for Fabric integration)

### Recommended Requirements
- **RAM**: 8GB or more
- **Storage**: 1GB+ for application and data
- **Display**: 1920x1080 or higher
- **Internet**: Broadband connection for Fabric features

### Software Dependencies
- **Python**: Not required for executable version
- **Power BI Desktop**: Optional (for testing modified models)
- **.NET Framework**: Usually pre-installed on Windows

## Installation Options

### Option 1: MSI Installer (Recommended)

The MSI installer provides the easiest installation experience.

1. **Download the MSI**
   - Download `PBIP-Studio-1.0.0-win64.msi` from [GitHub Releases](../../releases)

2. **Run the Installer**
   - Double-click the MSI file
   - Click "Next" through the installation wizard
   - Choose installation location (default: `C:\Program Files\PBIP Studio`)
   - Click "Install"

3. **Handle SmartScreen Warning** (if shown)
   - Windows may show a SmartScreen warning for unsigned apps
   - Click "More info" → "Run anyway"
   - This is normal for open-source applications without code signing certificates

4. **Complete Installation**
   - Click "Finish"
   - A shortcut is added to your Start Menu

### Option 2: Portable ZIP

For users who prefer not to install, use the portable ZIP version.

1. **Download ZIP**
   - Download `PBIP-Studio-1.0.0-portable.zip` from [GitHub Releases](../../releases)

2. **Extract Files**
   - Extract to a folder of your choice (e.g., `C:\Tools\PBIP-Studio`)

3. **Run Application**
   - Navigate to the extracted folder
   - Run `PBIP-Studio.exe`

4. **Create Shortcut** (Optional)
   - Right-click on `PBIP-Studio.exe`
   - Send to → Desktop (create shortcut)

### Option 3: Run from Source

For developers or users who want to run from source code.

#### Prerequisites
- Python 3.10 or higher
- Git (for cloning repository)

#### Steps

```powershell
# 1. Clone the repository
git clone https://github.com/mohammedadnant/pbip-studio.git
cd pbip-studio

# 2. Run the quick start script (creates venv and installs dependencies)
.\start.ps1
```

**Manual Installation:**

```powershell
# 1. Create virtual environment
python -m venv venv

# 2. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python src/main.py
```

## First Launch

When you first launch PBIP Studio:

1. **Application Startup**
   - The application creates necessary folders in `%LOCALAPPDATA%\PBIP Studio\`
   - Initializes the SQLite database
   - Starts the backend API server (localhost:8000)

2. **Main Window**
   - The main window opens maximized
   - You'll see the Assessment tab by default
   - No configuration required to start using local features

3. **Folder Structure Created**
   ```
   %LOCALAPPDATA%\PBIP Studio\
   ├── data\           # SQLite database files
   ├── logs\           # Application logs
   └── backups\        # Backup files (if enabled)
   ```

## Configuration

### Azure/Fabric Integration (Optional)

To use Fabric download/upload features:

1. **Navigate to Configuration Tab**
   - Click the "Configuration" tab in the main window

2. **Enter Azure Service Principal Details**
   - **Tenant ID**: Your Azure AD tenant ID
   - **Client ID**: Service principal application ID
   - **Client Secret**: Service principal secret

3. **Save Configuration**
   - Click "Save Configuration"
   - Credentials are stored locally in `config.json`

4. **Test Connection**
   - Use the "Test Connection" button to verify credentials

### Theme Settings

1. **Change Theme**
   - Go to Settings (gear icon)
   - Select "Light" or "Dark" theme
   - Theme is applied immediately

## Troubleshooting

### Windows SmartScreen Warning

**Problem**: Windows shows "Windows protected your PC" message

**Solution**:
1. Click "More info"
2. Click "Run anyway"
3. This happens because the app isn't code-signed (costs money)

### Application Won't Start

**Problem**: Application crashes on startup

**Solutions**:
1. Check log files at `%LOCALAPPDATA%\PBIP Studio\logs\app.log`
2. Ensure Windows is up to date
3. Install Visual C++ Redistributable (usually not needed)
4. Run as administrator (try once to rule out permissions)

### Missing Dependencies (when running from source)

**Problem**: Import errors or missing modules

**Solution**:
```powershell
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt
```

### Port Already in Use

**Problem**: "Port 8000 is already in use" error

**Solutions**:
1. Close other applications using port 8000
2. Or modify the port in `src/main.py` (line ~60)

### Database Locked

**Problem**: "Database is locked" error

**Solutions**:
1. Close all other instances of PBIP Studio
2. Delete `%LOCALAPPDATA%\PBIP Studio\data\powerbi_migration.db-journal`
3. Restart the application

### Azure Authentication Fails

**Problem**: Cannot connect to Fabric

**Solutions**:
1. Verify service principal has correct permissions:
   - Fabric Admin or Workspace Admin role
   - Proper API permissions in Azure AD
2. Check firewall/proxy settings
3. Verify tenant ID, client ID, and secret are correct

## Uninstallation

### MSI Installation
1. Go to Windows Settings → Apps → Apps & Features
2. Find "PBIP Studio"
3. Click "Uninstall"

### Portable Version
1. Delete the folder where you extracted the files

### Clean User Data
```powershell
# Remove all user data (optional)
Remove-Item -Path "$env:LOCALAPPDATA\PBIP Studio" -Recurse -Force
```

## Updating

### MSI Users
1. Download the latest MSI
2. Run the installer
3. It will automatically upgrade your existing installation

### Portable Users
1. Download the latest ZIP
2. Extract to a new folder (or overwrite existing)
3. User data in `%LOCALAPPDATA%` is preserved

### Source Users
```powershell
git pull origin main
pip install -r requirements.txt --upgrade
```

## Getting Help

- **Documentation**: [docs/](../docs/)
- **GitHub Issues**: [Report a bug](../../issues/new?template=bug_report.yml)
- **Discussions**: [Ask questions](../../discussions)

## Next Steps

After installation, check out:
- [User Guide](USER_GUIDE.md) - Learn how to use all features
- [Quick Start](../README.md#quick-start) - Get started quickly
- [Examples](EXAMPLES.md) - Common workflows and use cases
