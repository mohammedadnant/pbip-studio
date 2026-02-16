# Simple diagnostic test for Fabric CLI authentication
# This tests authentication without complex logic

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fabric CLI Authentication Test" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Fabric CLI is installed
Write-Host "Checking for Fabric CLI..." -ForegroundColor Cyan
$fabCommand = Get-Command fab -ErrorAction SilentlyContinue

if (-not $fabCommand) {
    Write-Host "ERROR: Fabric CLI not found!" -ForegroundColor Red
    Write-Host "Install: pip install ms-fabric-cli" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✓ Fabric CLI found at: $($fabCommand.Path)" -ForegroundColor Green
Write-Host ""

# Read config
$configPath = "$env:LOCALAPPDATA\PowerBI Migration Toolkit\config.md"
if (-not (Test-Path $configPath)) {
    Write-Host "ERROR: config.md not found at $configPath" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Reading credentials from: $configPath" -ForegroundColor Cyan
$config = Get-Content $configPath
$tenantId = ($config | Select-String 'tenantId = "(.+)"').Matches.Groups[1].Value
$clientId = ($config | Select-String 'clientId = "(.+)"').Matches.Groups[1].Value
$clientSecret = ($config | Select-String 'clientSecret = "(.+)"').Matches.Groups[1].Value

if (-not $tenantId -or -not $clientId -or -not $clientSecret) {
    Write-Host "ERROR: Could not parse credentials from config.md" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✓ Credentials loaded" -ForegroundColor Green
Write-Host "  Tenant ID: $tenantId" -ForegroundColor Gray
Write-Host "  Client ID: $clientId" -ForegroundColor Gray
Write-Host ""

# Attempt authentication
Write-Host "Authenticating with Fabric..." -ForegroundColor Cyan
$loginOutput = fab auth login -u $clientId -p $clientSecret --tenant $tenantId 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Authentication failed!" -ForegroundColor Red
    Write-Host "Exit code: $LASTEXITCODE" -ForegroundColor Yellow
    Write-Host "Output:" -ForegroundColor Yellow
    Write-Host $loginOutput
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✓ Authentication successful!" -ForegroundColor Green
Write-Host ""
Write-Host "Testing workspace listing..." -ForegroundColor Cyan
$workspaces = fab ls 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Workspace listing successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Workspaces:" -ForegroundColor Cyan
    Write-Host $workspaces
} else {
    Write-Host "ERROR: Failed to list workspaces" -ForegroundColor Red
    Write-Host $workspaces
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Test Complete" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Read-Host "Press Enter to exit"
exit 0
