# Download Power BI Dataset as TMDL using XMLA Endpoint
# Requires Premium or Fabric capacity with XMLA endpoint enabled

param(
    [Parameter(Mandatory=$true)]
    [string]$WorkspaceId,
    
    [Parameter(Mandatory=$true)]
    [string]$DatasetId,
    
    [Parameter(Mandatory=$true)]
    [string]$OutputPath,
    
    [Parameter(Mandatory=$true)]
    [string]$TenantId,
    
    [Parameter(Mandatory=$true)]
    [string]$ClientId,
    
    [Parameter(Mandatory=$true)]
    [string]$ClientSecret
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Power BI TMDL Downloader via XMLA" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if SqlServer module is installed
Write-Host "[1/5] Checking SqlServer PowerShell module..." -ForegroundColor Yellow

if (-not (Get-Module -ListAvailable -Name SqlServer)) {
    Write-Host "  Installing SqlServer module..." -ForegroundColor Gray
    try {
        Install-Module -Name SqlServer -Force -AllowClobber -Scope CurrentUser -ErrorAction Stop
        Write-Host "  ✓ SqlServer module installed" -ForegroundColor Green
    }
    catch {
        Write-Error "Failed to install SqlServer module: $_"
        exit 1
    }
}
else {
    Write-Host "  ✓ SqlServer module already installed" -ForegroundColor Green
}

# Import the module
try {
    Import-Module SqlServer -ErrorAction Stop
    Write-Host "  ✓ SqlServer module loaded" -ForegroundColor Green
}
catch {
    Write-Error "Failed to import SqlServer module: $_"
    exit 1
}

Write-Host ""

# Authenticate using Service Principal
Write-Host "[2/5] Authenticating to Power BI..." -ForegroundColor Yellow

$connectionString = "Provider=MSOLAP;Data Source=powerbi://api.powerbi.com/v1.0/myorg/$WorkspaceId;User ID=app:$ClientId@$TenantId;Password=$ClientSecret;"

Write-Host "  Workspace ID: $WorkspaceId" -ForegroundColor Gray
Write-Host "  Dataset ID: $DatasetId" -ForegroundColor Gray

try {
    # Load Analysis Services assemblies
    Add-Type -AssemblyName "Microsoft.AnalysisServices.Tabular"
    
    # Create server connection
    $server = New-Object Microsoft.AnalysisServices.Tabular.Server
    $server.Connect($connectionString)
    
    Write-Host "  ✓ Connected to Power BI XMLA endpoint" -ForegroundColor Green
}
catch {
    Write-Error "Authentication failed: $_"
    Write-Host ""
    Write-Host "Common issues:" -ForegroundColor Yellow
    Write-Host "  1. XMLA endpoint not enabled (Premium/Fabric required)" -ForegroundColor Gray
    Write-Host "  2. Service Principal doesn't have access to workspace" -ForegroundColor Gray
    Write-Host "  3. Incorrect credentials" -ForegroundColor Gray
    exit 1
}

Write-Host ""

# Get the database (dataset)
Write-Host "[3/5] Retrieving dataset..." -ForegroundColor Yellow

try {
    $database = $null
    
    # Try to find by ID or name
    foreach ($db in $server.Databases) {
        if ($db.ID -eq $DatasetId -or $db.Name -eq $DatasetId) {
            $database = $db
            break
        }
    }
    
    if ($null -eq $database) {
        Write-Error "Dataset not found: $DatasetId"
        Write-Host ""
        Write-Host "Available datasets in workspace:" -ForegroundColor Yellow
        foreach ($db in $server.Databases) {
            Write-Host "  - $($db.Name) (ID: $($db.ID))" -ForegroundColor Gray
        }
        exit 1
    }
    
    Write-Host "  ✓ Found dataset: $($database.Name)" -ForegroundColor Green
}
catch {
    Write-Error "Failed to retrieve dataset: $_"
    exit 1
}

Write-Host ""

# Create output directory structure
Write-Host "[4/5] Creating output directory structure..." -ForegroundColor Yellow

try {
    $datasetName = $database.Name
    $safeDatasetName = $datasetName -replace '[\\/:*?"<>|]', '_'
    
    $datasetPath = Join-Path $OutputPath "$safeDatasetName.Dataset"
    $definitionPath = Join-Path $datasetPath "definition"
    
    # Create directories
    New-Item -ItemType Directory -Path $definitionPath -Force | Out-Null
    
    Write-Host "  Output: $datasetPath" -ForegroundColor Gray
    Write-Host "  ✓ Directory created" -ForegroundColor Green
}
catch {
    Write-Error "Failed to create output directories: $_"
    exit 1
}

Write-Host ""

# Export TMDL
Write-Host "[5/5] Exporting TMDL definition..." -ForegroundColor Yellow

try {
    $model = $database.Model
    
    # Get all tables
    $tableCount = $model.Tables.Count
    Write-Host "  Tables: $tableCount" -ForegroundColor Gray
    
    # Serialize model to TMDL format
    $tmdlOptions = New-Object Microsoft.AnalysisServices.Tabular.SerializeOptions
    $tmdlOptions.IgnoreInferredObjects = $true
    $tmdlOptions.IgnoreInferredProperties = $true
    $tmdlOptions.IgnoreTimestamps = $true
    
    # Use TmdlSerializer to export
    [Microsoft.AnalysisServices.Tabular.TmdlSerializer]::SerializeModelToFolder(
        $model,
        $definitionPath,
        $tmdlOptions
    )
    
    # Count exported files
    $files = Get-ChildItem -Path $definitionPath -Recurse -File
    Write-Host "  Files exported: $($files.Count)" -ForegroundColor Gray
    
    Write-Host "  ✓ TMDL export complete" -ForegroundColor Green
}
catch {
    Write-Error "Failed to export TMDL: $_"
    exit 1
}

# Create .pbip project file
Write-Host ""
Write-Host "Creating .pbip project file..." -ForegroundColor Yellow

try {
    $pbipContent = @"
{
  "version": "1.0",
  "artifacts": [
    {
      "dataset": {
        "path": "$safeDatasetName.Dataset",
        "type": "SemanticModel"
      }
    }
  ]
}
"@
    
    $pbipFile = Join-Path $OutputPath "$safeDatasetName.pbip"
    Set-Content -Path $pbipFile -Value $pbipContent -Encoding UTF8
    
    Write-Host "  ✓ Created $safeDatasetName.pbip" -ForegroundColor Green
}
catch {
    Write-Warning "Failed to create .pbip file: $_"
}

# Create .dataset.tmd file
try {
    $tmdContent = @"
{
  "name": "$datasetName",
  "compatibilityLevel": 1550
}
"@
    
    $tmdFile = Join-Path $datasetPath ".dataset.tmd"
    Set-Content -Path $tmdFile -Value $tmdContent -Encoding UTF8
}
catch {
    Write-Warning "Failed to create .dataset.tmd file: $_"
}

# Disconnect
$server.Disconnect()

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✓ Download Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Output location:" -ForegroundColor Cyan
Write-Host "  $datasetPath" -ForegroundColor White
Write-Host ""
Write-Host "You can now:" -ForegroundColor Yellow
Write-Host "  1. Open $safeDatasetName.pbip in Power BI Desktop" -ForegroundColor Gray
Write-Host "  2. Edit TMDL files in $definitionPath" -ForegroundColor Gray
Write-Host "  3. Commit to source control" -ForegroundColor Gray
Write-Host ""

exit 0
