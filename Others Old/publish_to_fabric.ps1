<#
.SYNOPSIS
    Publish items to a Microsoft Fabric workspace using Fabric CLI.

.DESCRIPTION
    Usage:
        .\publish_to_fabric.ps1 -WorkspaceName "MyWorkspace" -ItemsJsonPath "items.json"

    items.json should be an array of objects like:
    [
      {
        "name": "MyReport",
        "path": "C:\\path\\to\\MyReport.pbip"
      },
      {
        "name": "MyDataset",
        "path": "C:\\path\\to\\MyDataset.pbip"
      }
    ]
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$WorkspaceName,
    
    [Parameter(Mandatory = $true)]
    [string]$ItemsJsonPath
)

# ---------------------------------------------
# Check if Fabric CLI is installed
# ---------------------------------------------
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
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✓ Fabric CLI found at: $($fabCommand.Path)" -ForegroundColor Green
Write-Host ""

# ---------------------------------------------
# Resolve script path
# ---------------------------------------------
$scriptPath = if ($PSScriptRoot) { 
    $PSScriptRoot 
} else { 
    Split-Path -Parent $MyInvocation.MyCommand.Path 
}

Write-Host "Script path: $scriptPath" -ForegroundColor DarkGray

# ---------------------------------------------
# Validate items JSON path
# ---------------------------------------------
if (-not (Test-Path -Path $ItemsJsonPath)) {
    Write-Host "ERROR: Items file not found: $ItemsJsonPath" -ForegroundColor Red
    exit 1
}

try {
    $itemsContent = Get-Content -Path $ItemsJsonPath -Encoding UTF8 -ErrorAction Stop
    $items = $itemsContent | ConvertFrom-Json -ErrorAction Stop
}
catch {
    Write-Host "ERROR: Failed to read or parse items JSON file: $ItemsJsonPath" -ForegroundColor Red
    Write-Host "       $_" -ForegroundColor Red
    exit 1
}

if (-not $items) {
    Write-Host "ERROR: Items JSON is empty or invalid: $ItemsJsonPath" -ForegroundColor Red
    exit 1
}

# Handle case where JSON is a single object instead of an array
if ($items -isnot [System.Collections.IEnumerable] -or $items -is [string]) {
    $items = @($items)
}

# ---------------------------------------------
# Determine directory for logs (same as items.json)
# ---------------------------------------------
$itemsDir = Split-Path -Parent $ItemsJsonPath
if (-not $itemsDir) {
    # Fallback to script path if something odd happens
    $itemsDir = $scriptPath
}

# ---------------------------------------------
# Read credentials from config.md and login
# ---------------------------------------------
Write-Host "Authenticating with Fabric..." -ForegroundColor Cyan

$configPath = Join-Path $scriptPath "config.md"
if (-not (Test-Path -Path $configPath)) {
    # Try AppData location
    $configPath = "$env:LOCALAPPDATA\PowerBI Migration Toolkit\config.md"
    if (-not (Test-Path -Path $configPath)) {
        Write-Host "ERROR: config.md not found" -ForegroundColor Red
        Write-Host "Expected location: $configPath" -ForegroundColor Gray
        exit 1
    }
}

Write-Host "Using config from: $configPath" -ForegroundColor DarkGray
$config = Get-Content $configPath

# Extract credentials using the same proven method as login.ps1
$tenantId     = ($config | Select-String 'tenantId = "(.+)"').Matches.Groups[1].Value
$clientId     = ($config | Select-String 'clientId = "(.+)"').Matches.Groups[1].Value
$clientSecret = ($config | Select-String 'clientSecret = "(.+)"').Matches.Groups[1].Value

if (-not $tenantId -or -not $clientId -or -not $clientSecret) {
    Write-Host "ERROR: Missing tenantId, clientId, or clientSecret in config.md" -ForegroundColor Red
    exit 1
}

fab auth login -u $clientId -p $clientSecret --tenant $tenantId | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Authentication failed. Please check credentials in config.md" -ForegroundColor Red
    exit 1
}

Write-Host "Authenticated successfully." -ForegroundColor Green
Write-Host ""

# ---------------------------------------------
# Initialize counters and diagnostics log
# ---------------------------------------------
$successCount = 0
$errorCount   = 0
$results      = @()

$diagFile = Join-Path $itemsDir "powershell_diagnostics.txt"

"=== PowerShell Script Execution ==="      | Out-File $diagFile
"Timestamp : $(Get-Date)"                  | Out-File $diagFile -Append
"Workspace: $WorkspaceName"                | Out-File $diagFile -Append
"Items JSON: $ItemsJsonPath"               | Out-File $diagFile -Append
"Items count: $($items.Count)"             | Out-File $diagFile -Append
"Script path: $scriptPath"                 | Out-File $diagFile -Append
"Config path: $configPath"                 | Out-File $diagFile -Append
""                                         | Out-File $diagFile -Append

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Publishing to Workspace: $WorkspaceName" -ForegroundColor Yellow
Write-Host "Total items: $($items.Count)" -ForegroundColor Yellow
Write-Host "Diagnostics log: $diagFile" -ForegroundColor DarkGray
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------
# Process each item
# ---------------------------------------------
$itemIndex = 0

foreach ($item in $items) {
    $itemIndex++
    $itemName = $item.name
    $itemPath = $item.path

    if (-not $itemName -or -not $itemPath) {
        Write-Host "[$itemIndex/$($items.Count)] Skipping item with missing name or path." -ForegroundColor Yellow
        "Item #${itemIndex}: INVALID (missing name or path)" | Out-File $diagFile -Append
        "" | Out-File $diagFile -Append

        $errorCount++
        $results += @{
            item    = $itemName
            status  = "error"
            message = "Missing name or path in items.json entry."
        }
        continue
    }

    Write-Host "[$itemIndex/$($items.Count)] Importing $itemName..." -ForegroundColor Cyan

    # Ensure file exists
    if (-not (Test-Path -Path $itemPath)) {
        Write-Host "  [FAIL] File not found: $itemPath" -ForegroundColor Red
        "Item: $itemName"        | Out-File $diagFile -Append
        "Path: $itemPath"        | Out-File $diagFile -Append
        "ERROR: File not found." | Out-File $diagFile -Append
        ""                       | Out-File $diagFile -Append

        $errorCount++
        $results += @{
            item    = $itemName
            status  = "error"
            message = "File not found: $itemPath"
        }
        Write-Host ""
        continue
    }

    try {
        $ErrorActionPreference = 'Continue'

        # Log command info
        "Item: $itemName" | Out-File $diagFile -Append
        "Path: $itemPath" | Out-File $diagFile -Append

        $fabCommand = "fab import `"$WorkspaceName.Workspace/$itemName`" -i `"$itemPath`" -f"
        "Command: $fabCommand" | Out-File $diagFile -Append

        # Execute Fabric import with proper output handling
        # Redirect both stdout and stderr to capture all output safely
        $tempOutputFile = Join-Path $env:TEMP "fab_output_$(Get-Random).txt"
        $tempErrorFile = Join-Path $env:TEMP "fab_error_$(Get-Random).txt"
        
        try {
            # Run fab command and capture output to files to avoid encoding issues
            $process = Start-Process -FilePath "fab" `
                -ArgumentList "import", "$WorkspaceName.Workspace/$itemName", "-i", "$itemPath", "-f" `
                -NoNewWindow `
                -Wait `
                -PassThru `
                -RedirectStandardOutput $tempOutputFile `
                -RedirectStandardError $tempErrorFile
            
            $exitCode = $process.ExitCode
            
            # Read output files safely
            $importOutput = ""
            $importError = ""
            
            if (Test-Path $tempOutputFile) {
                $importOutput = Get-Content $tempOutputFile -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
            }
            if (Test-Path $tempErrorFile) {
                $importError = Get-Content $tempErrorFile -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
            }
            
            # Clean up temp files
            Remove-Item $tempOutputFile -ErrorAction SilentlyContinue
            Remove-Item $tempErrorFile -ErrorAction SilentlyContinue
            
            "Exit Code: $exitCode" | Out-File $diagFile -Append
            if ($importOutput) {
                "Output:" | Out-File $diagFile -Append
                $importOutput | Out-File $diagFile -Append
            }
            if ($importError) {
                "Error Output:" | Out-File $diagFile -Append
                $importError | Out-File $diagFile -Append
            }
            "" | Out-File $diagFile -Append

            if ($exitCode -eq 0) {
                Write-Host "  [OK] Import succeeded." -ForegroundColor Green
                $successCount++
                $results += @{
                    item    = $itemName
                    status  = "success"
                    message = "Imported successfully"
                }
            }
            else {
                Write-Host "  [FAIL] Import failed." -ForegroundColor Red
                $errorCount++

                $errorMsg = if ($importError) { 
                    $importError.Trim() 
                } elseif ($importOutput) {
                    $importOutput.Trim()
                } else { 
                    "Import failed with exit code $exitCode" 
                }

                $results += @{
                    item    = $itemName
                    status  = "error"
                    message = $errorMsg
                }
            }
        }
        catch {
            # Cleanup on exception
            Remove-Item $tempOutputFile -ErrorAction SilentlyContinue
            Remove-Item $tempErrorFile -ErrorAction SilentlyContinue
            throw
        }

        $ErrorActionPreference = 'Stop'
    }
    catch {
        Write-Host "  [ERROR] Exception during import." -ForegroundColor Red
        $errorCount++

        $results += @{
            item    = $itemName
            status  = "error"
            message = $_.Exception.Message
        }

        "ERROR (exception): $($_.Exception.Message)" | Out-File $diagFile -Append
        "" | Out-File $diagFile -Append
    }

    Write-Host ""
}

# ---------------------------------------------
# Summary
# ---------------------------------------------
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Import Summary:" -ForegroundColor Yellow
Write-Host "  Success: $successCount" -ForegroundColor Green
Write-Host "  Failed : $errorCount" -ForegroundColor $(if ($errorCount -gt 0) { "Red" } else { "Gray" })
Write-Host "================================================" -ForegroundColor Cyan

# ---------------------------------------------
# Rebind Reports to SemanticModels using Power BI REST API
# ---------------------------------------------
if ($successCount -gt 0) {
    Write-Host ""
    Write-Host "Rebinding Reports to SemanticModels..." -ForegroundColor Cyan
    
    # Get access token for Power BI API
    $tokenResponse = Invoke-RestMethod -Method Post -Uri "https://login.microsoftonline.com/$tenantId/oauth2/v2.0/token" -Body @{
        grant_type    = "client_credentials"
        client_id     = $clientId
        client_secret = $clientSecret
        scope         = "https://analysis.windows.net/powerbi/api/.default"
    }
    
    $accessToken = $tokenResponse.access_token
    $headers = @{
        "Authorization" = "Bearer $accessToken"
        "Content-Type"  = "application/json"
    }
    
    # Get workspace ID
    try {
        $workspacesResponse = Invoke-RestMethod -Method Get -Uri "https://api.powerbi.com/v1.0/myorg/groups?`$filter=name eq '$WorkspaceName'" -Headers $headers
        $workspace = $workspacesResponse.value | Select-Object -First 1
        
        if (-not $workspace) {
            Write-Host "  Warning: Could not find workspace '$WorkspaceName' for rebinding" -ForegroundColor Yellow
        }
        else {
            $workspaceId = $workspace.id
            Write-Host "  Workspace ID: $workspaceId" -ForegroundColor DarkGray
            
            # Get all reports and datasets in workspace
            $reportsResponse = Invoke-RestMethod -Method Get -Uri "https://api.powerbi.com/v1.0/myorg/groups/$workspaceId/reports" -Headers $headers
            $datasetsResponse = Invoke-RestMethod -Method Get -Uri "https://api.powerbi.com/v1.0/myorg/groups/$workspaceId/datasets" -Headers $headers
            
            # Create lookup for datasets by name
            $datasetLookup = @{}
            foreach ($dataset in $datasetsResponse.value) {
                $datasetLookup[$dataset.name] = $dataset.id
            }
            
            # Rebind each report to its corresponding dataset
            foreach ($report in $reportsResponse.value) {
                $reportName = $report.name
                $reportId = $report.id
                
                # Try to find matching dataset (same name as report or without .Report suffix)
                $datasetName = $reportName -replace '\.Report$', ''
                
                if ($datasetLookup.ContainsKey($datasetName)) {
                    $datasetId = $datasetLookup[$datasetName]
                    
                    try {
                        # Rebind report to dataset
                        $rebindBody = @{
                            datasetId = $datasetId
                        } | ConvertTo-Json
                        
                        Invoke-RestMethod -Method Post -Uri "https://api.powerbi.com/v1.0/myorg/groups/$workspaceId/reports/$reportId/Rebind" -Headers $headers -Body $rebindBody
                        
                        Write-Host "  [OK] Rebound '$reportName' to dataset '$datasetName'" -ForegroundColor Green
                    }
                    catch {
                        Write-Host "  [WARN] Could not rebind '$reportName': $($_.Exception.Message)" -ForegroundColor Yellow
                    }
                }
                else {
                    Write-Host "  [SKIP] No matching dataset found for report '$reportName'" -ForegroundColor DarkGray
                }
            }
        }
    }
    catch {
        Write-Host "  Warning: Failed to rebind reports: $($_.Exception.Message)" -ForegroundColor Yellow
    }
    
    Write-Host ""
}

# ---------------------------------------------
# Save results to JSON
# ---------------------------------------------
$resultPath = [System.IO.Path]::GetDirectoryName($ItemsJsonPath)
if (-not $resultPath) { $resultPath = $scriptPath }

$resultFile = Join-Path $resultPath "import_results.json"

$resultJson = @{
    workspace    = $WorkspaceName
    timestamp    = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    totalItems   = $items.Count
    successCount = $successCount
    errorCount   = $errorCount
    results      = $results
}

$resultJson | ConvertTo-Json -Depth 10 | Out-File -FilePath $resultFile -Encoding UTF8
Write-Host "Results saved to: $resultFile" -ForegroundColor Cyan
Write-Host "Diagnostics log saved to: $diagFile" -ForegroundColor Cyan

# ---------------------------------------------
# Exit with appropriate code
# ---------------------------------------------
if ($errorCount -eq 0) {
    exit 0
}
else {
    exit 1
}

