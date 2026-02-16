# Build Script for MSI Installer with Database
# This script prepares and builds a complete MSI package

# Step 1: Ensure database exists
Write-Host "Step 1: Preparing database..." -ForegroundColor Cyan

$dataFolder = "data"
$dbPath = "$dataFolder/fabric_migration.db"

if (-not (Test-Path $dataFolder)) {
    New-Item -ItemType Directory -Path $dataFolder -Force | Out-Null
    Write-Host "  Created data folder" -ForegroundColor Green
}

if (-not (Test-Path $dbPath)) {
    Write-Host "  Creating empty database..." -ForegroundColor Yellow
    
    # Activate virtual environment and create database
    if (Test-Path "venv\Scripts\Activate.ps1") {
        & .\venv\Scripts\Activate.ps1
        python -c @"
import sqlite3
from pathlib import Path

# Create database with schema
conn = sqlite3.connect('data/fabric_migration.db')
cursor = conn.cursor()

# Create tables (from src/database/schema.py)
cursor.execute('''
CREATE TABLE IF NOT EXISTS workspaces (
    workspace_id TEXT PRIMARY KEY,
    workspace_name TEXT NOT NULL,
    tool_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS datasets (
    dataset_id TEXT PRIMARY KEY,
    dataset_name TEXT NOT NULL,
    workspace_id TEXT,
    model_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS data_objects (
    object_id TEXT PRIMARY KEY,
    dataset_id TEXT,
    object_name TEXT NOT NULL,
    object_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS data_sources (
    source_id TEXT PRIMARY KEY,
    dataset_id TEXT,
    source_type TEXT,
    connection_details TEXT,
    tables TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS migration_history (
    migration_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT,
    migration_type TEXT,
    old_value TEXT,
    new_value TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES data_sources(source_id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS bi_tools (
    tool_id TEXT PRIMARY KEY,
    tool_name TEXT NOT NULL,
    tool_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

conn.commit()
conn.close()
print('Database created successfully!')
"@
        Write-Host "  Database created with schema" -ForegroundColor Green
    } else {
        Write-Host "  Warning: Virtual environment not found. Database will be created at runtime." -ForegroundColor Yellow
    }
} else {
    Write-Host "  Database already exists: $dbPath" -ForegroundColor Green
}

# Step 2: Ensure config template exists
Write-Host "`nStep 2: Checking config template..." -ForegroundColor Cyan
if (Test-Path "config.template.md") {
    Write-Host "  Config template exists" -ForegroundColor Green
} else {
    Write-Host "  Creating config template..." -ForegroundColor Yellow
    @"
# Fabric Configuration Template

## Azure Service Principal Credentials
# Copy this file to 'config.md' and fill in your credentials

tenantId = "your-tenant-id-here"
clientId = "your-client-id-here"
clientSecret = "your-client-secret-here"

## How to Get These Values:
# 1. Go to Azure Portal (portal.azure.com)
# 2. Navigate to Azure Active Directory > App registrations
# 3. Create a new registration or use existing one
# 4. Copy Application (client) ID -> clientId
# 5. Copy Directory (tenant) ID -> tenantId
# 6. Go to Certificates & secrets > New client secret
# 7. Copy the secret value -> clientSecret
# 8. Grant API permissions: Power BI Service

## Optional: Leave blank if not using Fabric deployment features
"@ | Out-File -FilePath "config.template.md" -Encoding UTF8
    Write-Host "  Config template created" -ForegroundColor Green
}

# Step 3: Clean previous builds
Write-Host "`nStep 3: Cleaning previous builds..." -ForegroundColor Cyan
if (Test-Path "build") {
    Remove-Item -Path "build" -Recurse -Force
    Write-Host "  Removed build folder" -ForegroundColor Green
}
if (Test-Path "dist") {
    Remove-Item -Path "dist" -Recurse -Force
    Write-Host "  Removed dist folder" -ForegroundColor Green
}

# Step 4: Build MSI
Write-Host "`nStep 4: Building MSI installer..." -ForegroundColor Cyan
Write-Host "  This may take several minutes..." -ForegroundColor Yellow

if (Test-Path "venv\Scripts\Activate.ps1") {
    & .\venv\Scripts\Activate.ps1
    
    # Run build with timeout protection (15 minutes max)
    $buildJob = Start-Job -ScriptBlock {
        Set-Location $using:PWD
        & .\venv\Scripts\Activate.ps1
        python setup.py bdist_msi --quiet
    }
    
    $completed = Wait-Job $buildJob -Timeout 900
    if ($completed) {
        Receive-Job $buildJob
        Remove-Job $buildJob
    } else {
        Stop-Job $buildJob
        Remove-Job $buildJob
        Write-Host "`n✗ Build timed out after 15 minutes. Try cleaning build folders and retry." -ForegroundColor Red
        exit 1
    }
    
    if ($LASTEXITCODE -eq 0 -or (Test-Path "dist\*.msi")) {
        Write-Host "`n✓ MSI built successfully!" -ForegroundColor Green
        
        # Find the MSI file
        $msiFile = Get-ChildItem -Path "dist" -Filter "*.msi" | Select-Object -First 1
        if ($msiFile) {
            Write-Host "`nMSI Location: $($msiFile.FullName)" -ForegroundColor Cyan
            Write-Host "Size: $([math]::Round($msiFile.Length / 1MB, 2)) MB" -ForegroundColor Cyan
            
            Write-Host "`n=== Installation Includes ===" -ForegroundColor Yellow
            Write-Host "  ✓ PowerBI-Migration-Toolkit.exe" -ForegroundColor White
            Write-Host "  ✓ Blank config file (config.md)" -ForegroundColor White
            Write-Host "  ✓ Documentation (README.md, GETTING_STARTED.md, DEPLOYMENT_GUIDE.md)" -ForegroundColor White
            Write-Host "  ✓ All required Python libraries" -ForegroundColor White
            
            Write-Host "`n=== Next Steps ===" -ForegroundColor Yellow
            Write-Host "  1. Copy the MSI file to target laptop" -ForegroundColor White
            Write-Host "  2. Run MSI to install" -ForegroundColor White
            Write-Host "  3. Launch application from Start Menu" -ForegroundColor White
            Write-Host "  4. Use Settings tab in UI to enter credentials" -ForegroundColor White
            Write-Host "  5. Credentials saved to config.md automatically" -ForegroundColor White
            Write-Host "  6. Database created automatically on first use!" -ForegroundColor White
        }
    } else {
        Write-Host "`n✗ Build failed. Check errors above." -ForegroundColor Red
    }
} else {
    Write-Host "  Error: Virtual environment not found." -ForegroundColor Red
    Write-Host "  Run: python -m venv venv" -ForegroundColor Yellow
    Write-Host "  Then: .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "  Then: pip install -r requirements.txt" -ForegroundColor Yellow
}
