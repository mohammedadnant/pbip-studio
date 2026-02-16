# Read credentials from config.md and login to Fabric

# Check if Fabric CLI is installed - search in multiple locations
Write-Host "Checking for Fabric CLI..." -ForegroundColor Cyan

# Try to find fab command in PATH first
$fabCommand = Get-Command fab -ErrorAction SilentlyContinue

# If not found in PATH, search common installation locations
if (-not $fabCommand) {
    Write-Host "Not found in PATH, searching common locations..." -ForegroundColor Yellow
    
    $searchPaths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\Scripts\fab.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\Scripts\fab.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\Scripts\fab.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python39\Scripts\fab.exe",
        "$env:APPDATA\Python\Python312\Scripts\fab.exe",
        "$env:APPDATA\Python\Python311\Scripts\fab.exe",
        "$env:APPDATA\Python\Python310\Scripts\fab.exe",
        "C:\Python312\Scripts\fab.exe",
        "C:\Python311\Scripts\fab.exe",
        "C:\Python310\Scripts\fab.exe"
    )
    
    foreach ($path in $searchPaths) {
        if (Test-Path $path) {
            $fabCommand = Get-Command $path -ErrorAction SilentlyContinue
            if ($fabCommand) {
                Write-Host "Found at: $path" -ForegroundColor Green
                # Add this directory to PATH for current session
                $fabDir = Split-Path $path
                $env:PATH = "$fabDir;$env:PATH"
                break
            }
        }
    }
}

if (-not $fabCommand) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "ERROR: Fabric CLI not found!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Microsoft Fabric CLI first:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. Install via Python:" -ForegroundColor White
    Write-Host "   pip install ms-fabric-cli" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Or download from:" -ForegroundColor White
    Write-Host "   https://github.com/microsoft/fabric-cli" -ForegroundColor Gray
    Write-Host ""
    Write-Host "After installation, restart this application and try again." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to close this window"
    exit 1
}

Write-Host "✓ Fabric CLI found at: $($fabCommand.Path)" -ForegroundColor Green
Write-Host ""

$scriptPath = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }

# Check if config.md exists - prioritize AppData location over script directory
$configPath = "$env:LOCALAPPDATA\PowerBI Migration Toolkit\config.md"
if (-not (Test-Path $configPath)) {
    # Fall back to script directory (for dev/testing)
    $configPath = "$scriptPath\config.md"
    if (-not (Test-Path $configPath)) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Red
        Write-Host "ERROR: config.md not found!" -ForegroundColor Red
        Write-Host "========================================" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please configure your credentials first in the Configuration tab." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Expected location: $env:LOCALAPPDATA\PowerBI Migration Toolkit\config.md" -ForegroundColor Gray
        Write-Host ""
        Read-Host "Press Enter to close this window"
        exit 1
    }
}

Write-Host "Reading credentials from: $configPath" -ForegroundColor Cyan
$config = Get-Content $configPath
$tenantId = ($config | Select-String 'tenantId = "(.+)"').Matches.Groups[1].Value
$clientId = ($config | Select-String 'clientId = "(.+)"').Matches.Groups[1].Value
$clientSecret = ($config | Select-String 'clientSecret = "(.+)"').Matches.Groups[1].Value

if (-not $tenantId -or -not $clientId -or -not $clientSecret) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "ERROR: Invalid config.md format!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Could not parse credentials from config.md" -ForegroundColor Yellow
    Write-Host "Make sure the file contains:" -ForegroundColor Yellow
    Write-Host '  tenantId = "your-tenant-id"' -ForegroundColor Gray
    Write-Host '  clientId = "your-client-id"' -ForegroundColor Gray
    Write-Host '  clientSecret = "your-client-secret"' -ForegroundColor Gray
    Write-Host ""
    Read-Host "Press Enter to close this window"
    exit 1
}

Write-Host "Logging in with credentials from config.md..."
Write-Host "Tenant ID: $tenantId"
Write-Host "Client ID: $clientId"

# Login to Fabric
Write-Host ""
Write-Host "Authenticating with Fabric..." -ForegroundColor Cyan

$loginOutput = fab auth login -u $clientId -p $clientSecret --tenant $tenantId 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "ERROR: Authentication failed!" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Output:" -ForegroundColor Yellow
    Write-Host $loginOutput
    Write-Host ""
    Write-Host "Please verify your credentials in the Configuration tab." -ForegroundColor Yellow
    Read-Host "Press Enter to close this window"
    exit 1
}

Write-Host "✓ Authentication successful" -ForegroundColor Green

Write-Host "`nFetching all workspaces..."
# Step 1: List all workspaces
$workspaces = fab ls 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Failed to list workspaces" -ForegroundColor Red
    Write-Host "Output: $workspaces" -ForegroundColor Yellow
    Read-Host "Press Enter to close this window"
    exit 1
}

Write-Host ""
Write-Host "Raw output from 'fab ls':" -ForegroundColor Cyan
Write-Host "------------------------" -ForegroundColor Cyan
Write-Host $workspaces
Write-Host "------------------------" -ForegroundColor Cyan
Write-Host ""

# Parse the output to extract workspace names
$workspaceLines = $workspaces | Where-Object { $_ -match '\.Workspace' }

Write-Host "Parsed workspace lines: $($workspaceLines.Count)" -ForegroundColor Cyan
if ($workspaceLines.Count -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "WARNING: No workspaces found!" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "This usually means:" -ForegroundColor Yellow
    Write-Host "  1. Your service principal doesn't have permissions" -ForegroundColor White
    Write-Host "  2. Service principals aren't enabled in Power BI Admin Portal" -ForegroundColor White
    Write-Host "  3. The app isn't added to any workspaces" -ForegroundColor White
    Write-Host ""
    Write-Host "Please check:" -ForegroundColor Cyan
    Write-Host "  • Power BI Admin Portal → Tenant Settings → Developer Settings" -ForegroundColor Gray
    Write-Host "    → Enable 'Service principals can access Power BI APIs'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  • Azure Portal → App Registrations → Your App → API Permissions" -ForegroundColor Gray
    Write-Host "    → Verify permissions and grant admin consent" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  • Add the service principal to your workspaces as Admin or Member" -ForegroundColor Gray
    Write-Host ""
    Write-Host "See AZURE_APP_SETUP.md for detailed instructions" -ForegroundColor Cyan
    Write-Host ""
    Read-Host "Press Enter to close this window"
    exit 0
}

# Determine output location - use Documents folder instead of Program Files
$documentsFolder = [Environment]::GetFolderPath("MyDocuments")
$downloadsFolder = "$documentsFolder\PowerBI-Toolkit-Downloads"
# Determine output location - use Documents folder instead of Program Files
$documentsFolder = [Environment]::GetFolderPath("MyDocuments")
$downloadsFolder = "$documentsFolder\PowerBI-Toolkit-Downloads"
$timestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
$exportFolder = "$downloadsFolder\FabricExport_$timestamp"
$jsonFile = "$exportFolder\workspaces_hierarchy.json"

Write-Host ""
Write-Host "Downloads will be saved to:" -ForegroundColor Cyan
Write-Host "  $downloadsFolder" -ForegroundColor Gray
Write-Host ""

# Create downloads and export folders
try {
    New-Item -ItemType Directory -Force -Path $downloadsFolder -ErrorAction Stop | Out-Null
    New-Item -ItemType Directory -Force -Path $exportFolder -ErrorAction Stop | Out-Null
    Write-Host "✓ Created export folder: $exportFolder" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "ERROR: Failed to create folders" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Yellow
    Read-Host "Press Enter to close this window"
    exit 1
}

# Initialize JSON structure
$jsonStructure = @{
    exportDate = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    tenantId = $tenantId
    workspaceCount = 0
    workspaces = @()
}

if ($workspaceLines) {
    Write-Host "Found $($workspaceLines.Count) workspace(s)`n" -ForegroundColor Green
    $jsonStructure.workspaceCount = $workspaceLines.Count
    
    $workspaceCounter = 0
    foreach ($line in $workspaceLines) {
        # Extract workspace name (format: "name.Workspace")
        if ($line -match '(.+)\.Workspace') {
            $workspaceCounter++
            $workspaceName = $matches[1].Trim()
            
            Write-Host "================================================" -ForegroundColor Cyan
            Write-Host "Processing Workspace $workspaceCounter of $($workspaceLines.Count): $workspaceName" -ForegroundColor Yellow
            
            try {
                # Skip re-authentication - it causes issues and isn't necessary
                # The initial login is sufficient for all workspace operations
                
                # Step 2 & 3: List items in workspace using direct path (cd doesn't work as expected)
                Write-Host "Items in workspace:" -ForegroundColor Cyan
                $itemsOutput = fab ls "$workspaceName.Workspace"
            
                # Parse items (exclude .Workspace, .Folder, and hidden items)
                $itemsList = @()
                $exportedItems = @()
                $failedItems = @()
            
                foreach ($itemLine in $itemsOutput) {
                # Match items but exclude Workspace, Folder, and lines starting with .
                if ($itemLine -match '^\s*(.+)\.([\w]+)\s*$' -and $itemLine -notmatch '\.Workspace' -and $itemLine -notmatch '\.Folder' -and $itemLine -notmatch '^\s*\.') {
                    $itemName = $matches[1].Trim()
                    $itemType = $matches[2]
                    $fullItemName = "$itemName.$itemType"
                    
                    $itemsList += @{
                        name = $itemName
                        type = $itemType
                        fullName = $fullItemName
                    }
                    
                    Write-Host "  - $fullItemName" -ForegroundColor Gray
                    
                    # Only process Power BI items: Report, SemanticModel, Dashboard
                    $powerBITypes = @("Report", "SemanticModel", "Dashboard")
                    if ($powerBITypes -notcontains $itemType) {
                        Write-Host "    Skipped (not a Power BI item)" -ForegroundColor DarkGray
                        continue
                    }
                    
                    # Step 4: Export each item individually using full path
                    Write-Host "    Exporting $fullItemName..." -ForegroundColor Yellow
                    
                    try {
                        $ErrorActionPreference = 'Continue'
                        
                        # Create Raw Files subfolder inside FabricExport_xxx
                        $rawFilesFolder = "$exportFolder/Raw Files"
                        New-Item -ItemType Directory -Force -Path $rawFilesFolder | Out-Null
                        
                        # Create workspace export directory inside Raw Files
                        $exportPath = "$rawFilesFolder/$workspaceName"
                        New-Item -ItemType Directory -Force -Path $exportPath | Out-Null
                        
                        # Capture output to see actual errors
                        $exportOutput = fab export "$workspaceName.Workspace/$fullItemName" -o $exportPath -f 2>&1
                        
                        if ($LASTEXITCODE -eq 0) {
                            Write-Host "    Exported successfully" -ForegroundColor Green
                            $exportedItems += $fullItemName
                        } else {
                            # Extract error message if available - with null checks
                            $errorMsg = $null
                            if ($null -ne $exportOutput -and $exportOutput.Count -gt 0) {
                                $errorMatch = $exportOutput | Select-String -Pattern "x export: (.+)" | Select-Object -First 1
                                if ($null -ne $errorMatch -and $null -ne $errorMatch.Matches -and $errorMatch.Matches.Count -gt 0) {
                                    $errorMsg = $errorMatch.Matches.Groups[1].Value
                                }
                            }
                            
                            if ($errorMsg) {
                                Write-Host "    Export failed: $errorMsg" -ForegroundColor Red
                            } else {
                                Write-Host "    Export failed (exit code: $LASTEXITCODE)" -ForegroundColor Red
                                if ($null -ne $exportOutput -and $exportOutput.Count -gt 0) {
                                    Write-Host "    Raw output: $($exportOutput -join '; ')" -ForegroundColor DarkRed
                                }
                            }
                            $failedItems += $fullItemName
                        }
                    } catch {
                        Write-Host "    Export failed: $_" -ForegroundColor Red
                        $failedItems += $fullItemName
                    } finally {
                        $ErrorActionPreference = 'Stop'
                    }
                }
            }
            
            # Add workspace to JSON structure
            $workspaceObj = @{
                    name = $workspaceName
                    itemCount = $itemsList.Count
                    items = $itemsList
                    exportedCount = $exportedItems.Count
                    failedCount = $failedItems.Count
                    exportedItems = $exportedItems
                    failedItems = $failedItems
                }
                
                $jsonStructure.workspaces += $workspaceObj
                
                Write-Host "  Summary: $($exportedItems.Count) exported, $($failedItems.Count) failed" -ForegroundColor Cyan
                Write-Host ""
                
            } catch {
                Write-Host "  ERROR processing workspace: $_" -ForegroundColor Red
                Write-Host "  Continuing to next workspace..." -ForegroundColor Yellow
                Write-Host ""
            }
        }
    }
    Write-Host "================================================" -ForegroundColor Cyan
    
    # Save JSON hierarchy (UTF8 without BOM)
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    $jsonContent = $jsonStructure | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText($jsonFile, $jsonContent, $utf8NoBom)
    
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "✓ DOWNLOAD COMPLETE!" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Summary:" -ForegroundColor Cyan
    Write-Host "  Workspaces processed: $($jsonStructure.workspaceCount)" -ForegroundColor White
    $totalItems = $jsonStructure.workspaces | ForEach-Object { $_.itemCount } | Measure-Object -Sum | Select-Object -ExpandProperty Sum
    Write-Host "  Total items found: $totalItems" -ForegroundColor White
    Write-Host ""
    Write-Host "Files saved to:" -ForegroundColor Cyan
    Write-Host "  $exportFolder" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Go to the Assessment tab in the application" -ForegroundColor White
    Write-Host "  2. Select the export from the dropdown" -ForegroundColor White
    Write-Host "  3. Click 'Index Export' to import into database" -ForegroundColor White
    Write-Host ""
    Write-Host "You can now close this window" -ForegroundColor Cyan
    Read-Host "Press Enter to close"
}

# Exit with success code
exit 0
