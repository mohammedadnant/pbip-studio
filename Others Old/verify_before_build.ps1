# Pre-Build Verification Script
# Run this before building to catch common issues

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Pre-Build Verification" -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$allGood = $true

# Check 1: Python version
Write-Host "[1/7] Checking Python version..." -ForegroundColor Cyan
$pythonVersion = python --version 2>&1
if ($pythonVersion -match "Python 3\.(1[0-9]|[2-9][0-9])") {
    Write-Host "  ✓ $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "  ✗ Python 3.10+ required, found: $pythonVersion" -ForegroundColor Red
    $allGood = $false
}
Write-Host ""

# Check 2: Required files exist
Write-Host "[2/7] Checking required files..." -ForegroundColor Cyan
$requiredFiles = @(
    "src\main.py",
    "src\gui\main_window.py",
    "src\api\server.py",
    "login.ps1",
    "publish_to_fabric.ps1",
    "powerbi-toolkit.spec",
    "setup.py",
    "requirements.txt"
)

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Missing: $file" -ForegroundColor Red
        $allGood = $false
    }
}
Write-Host ""

# Check 3: Test app launch (quick)
Write-Host "[3/7] Testing app launch..." -ForegroundColor Cyan
try {
    $testProcess = Start-Process python -ArgumentList "src\main.py" -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 3
    
    if (-not $testProcess.HasExited) {
        Write-Host "  ✓ App launches successfully" -ForegroundColor Green
        Stop-Process -Id $testProcess.Id -Force -ErrorAction SilentlyContinue
    } else {
        Write-Host "  ✗ App exited immediately (check for errors)" -ForegroundColor Red
        $allGood = $false
    }
} catch {
    Write-Host "  ✗ Failed to launch app: $_" -ForegroundColor Red
    $allGood = $false
}
Write-Host ""

# Check 4: Test API backend
Write-Host "[4/7] Testing API backend..." -ForegroundColor Cyan
try {
    Start-Sleep -Seconds 2
    $apiTest = Invoke-WebRequest -Uri "http://127.0.0.1:8000/" -TimeoutSec 3 -ErrorAction Stop
    Write-Host "  ✓ Backend API responds" -ForegroundColor Green
} catch {
    Write-Host "  ⚠ Backend not responding (might be ok if app already closed)" -ForegroundColor Yellow
}
Write-Host ""

# Check 5: Verify spec file includes PowerShell scripts
Write-Host "[5/7] Checking build configuration..." -ForegroundColor Cyan
$specContent = Get-Content "powerbi-toolkit.spec" -Raw
if ($specContent -match "login\.ps1" -and $specContent -match "publish_to_fabric\.ps1") {
    Write-Host "  ✓ PyInstaller spec includes PowerShell scripts" -ForegroundColor Green
} else {
    Write-Host "  ✗ PowerShell scripts not in spec file" -ForegroundColor Red
    $allGood = $false
}

$setupContent = Get-Content "setup.py" -Raw
if ($setupContent -match "login\.ps1" -and $setupContent -match "publish_to_fabric\.ps1") {
    Write-Host "  ✓ cx_Freeze setup includes PowerShell scripts" -ForegroundColor Green
} else {
    Write-Host "  ✗ PowerShell scripts not in setup.py" -ForegroundColor Red
    $allGood = $false
}
Write-Host ""

# Check 6: Verify config path uses AppData
Write-Host "[6/7] Checking config path logic..." -ForegroundColor Cyan
$mainWindowContent = Get-Content "src\gui\main_window.py" -Raw
if ($mainWindowContent -match "LOCALAPPDATA.*config\.md") {
    Write-Host "  ✓ Config uses AppData (writable location)" -ForegroundColor Green
} else {
    Write-Host "  ✗ Config might use Program Files (not writable)" -ForegroundColor Red
    $allGood = $false
}
Write-Host ""

# Check 7: Check for syntax errors
Write-Host "[7/7] Checking for Python syntax errors..." -ForegroundColor Cyan
$pythonFiles = Get-ChildItem -Path "src" -Filter "*.py" -Recurse
$syntaxErrors = 0
foreach ($file in $pythonFiles) {
    $result = python -m py_compile $file.FullName 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ✗ Syntax error in: $($file.FullName)" -ForegroundColor Red
        $syntaxErrors++
        $allGood = $false
    }
}
if ($syntaxErrors -eq 0) {
    Write-Host "  ✓ No syntax errors found" -ForegroundColor Green
}
Write-Host ""

# Summary
Write-Host "================================================" -ForegroundColor Cyan
if ($allGood) {
    Write-Host "✓ ALL CHECKS PASSED - Ready to build!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Run one of these commands to build:" -ForegroundColor Cyan
    Write-Host "  .\build.ps1 -BuildType exe   # Build .exe with PyInstaller" -ForegroundColor White
    Write-Host "  .\build.ps1 -BuildType msi   # Build .msi with cx_Freeze" -ForegroundColor White
} else {
    Write-Host "✗ SOME CHECKS FAILED - Fix issues before building" -ForegroundColor Red
    Write-Host ""
    Write-Host "Review errors above and fix them first." -ForegroundColor Yellow
}
Write-Host "================================================" -ForegroundColor Cyan
