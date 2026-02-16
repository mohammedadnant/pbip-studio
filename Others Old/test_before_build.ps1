# Pre-Build Test Script
# Run this BEFORE building to catch issues early

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Power BI Migration Toolkit - Pre-Build Tests" -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$ErrorCount = 0

# Test 1: Python version
Write-Host "[TEST 1] Checking Python version..." -ForegroundColor Cyan
$pythonVersion = python --version 2>&1
if ($pythonVersion -match "Python 3\.1[0-2]") {
    Write-Host "✓ Python version OK: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "✗ Python version issue: $pythonVersion" -ForegroundColor Red
    $ErrorCount++
}
Write-Host ""

# Test 2: Virtual environment
Write-Host "[TEST 2] Checking virtual environment..." -ForegroundColor Cyan
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "✓ Virtual environment exists" -ForegroundColor Green
    & ".\venv\Scripts\Activate.ps1"
} else {
    Write-Host "✗ Virtual environment not found" -ForegroundColor Red
    $ErrorCount++
}
Write-Host ""

# Test 3: Required packages
Write-Host "[TEST 3] Checking required packages..." -ForegroundColor Cyan
$requiredPackages = @('PyQt6', 'fastapi', 'uvicorn', 'pandas', 'pyinstaller', 'cx-Freeze')
foreach ($pkg in $requiredPackages) {
    $check = python -c "import importlib.util; print('OK' if importlib.util.find_spec('$($pkg.ToLower().Replace('-', '_'))') else 'MISSING')" 2>&1
    if ($check -match "OK") {
        Write-Host "✓ $pkg installed" -ForegroundColor Green
    } else {
        Write-Host "✗ $pkg missing or broken" -ForegroundColor Red
        $ErrorCount++
    }
}
Write-Host ""

# Test 4: Source code syntax
Write-Host "[TEST 4] Checking Python syntax..." -ForegroundColor Cyan
$pythonFiles = Get-ChildItem -Path "src" -Filter "*.py" -Recurse
$syntaxErrors = 0
foreach ($file in $pythonFiles) {
    $result = python -m py_compile $file.FullName 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Syntax error in $($file.Name)" -ForegroundColor Red
        $syntaxErrors++
    }
}
if ($syntaxErrors -eq 0) {
    Write-Host "✓ All Python files have valid syntax" -ForegroundColor Green
} else {
    Write-Host "✗ Found $syntaxErrors files with syntax errors" -ForegroundColor Red
    $ErrorCount += $syntaxErrors
}
Write-Host ""

# Test 5: Import test
Write-Host "[TEST 5] Testing critical imports..." -ForegroundColor Cyan
$importTest = @"
import sys
sys.path.insert(0, 'src')
try:
    from PyQt6.QtWidgets import QApplication
    from fastapi import FastAPI
    import uvicorn
    from gui.main_window import MainWindow
    from api.server import app
    print('OK')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
"@

$importResult = python -c $importTest 2>&1
if ($importResult -match "OK") {
    Write-Host "✓ All critical imports successful" -ForegroundColor Green
} else {
    Write-Host "✗ Import error: $importResult" -ForegroundColor Red
    $ErrorCount++
}
Write-Host ""

# Test 6: Run application briefly
Write-Host "[TEST 6] Testing application startup (5 seconds)..." -ForegroundColor Cyan
$appTest = Start-Process python -ArgumentList "src/main.py" -PassThru -NoNewWindow
Start-Sleep -Seconds 5
if ($appTest.HasExited) {
    Write-Host "✗ Application crashed on startup" -ForegroundColor Red
    $ErrorCount++
} else {
    Write-Host "✓ Application started successfully" -ForegroundColor Green
    Stop-Process -Id $appTest.Id -Force -ErrorAction SilentlyContinue
}
Write-Host ""

# Test 7: Check spec files
Write-Host "[TEST 7] Checking build configuration..." -ForegroundColor Cyan
if (Test-Path "powerbi-toolkit.spec") {
    Write-Host "✓ PyInstaller spec found" -ForegroundColor Green
} else {
    Write-Host "✗ PyInstaller spec missing" -ForegroundColor Red
    $ErrorCount++
}
if (Test-Path "setup.py") {
    Write-Host "✓ cx_Freeze setup.py found" -ForegroundColor Green
} else {
    Write-Host "✗ setup.py missing" -ForegroundColor Red
    $ErrorCount++
}
Write-Host ""

# Test 8: Database initialization
Write-Host "[TEST 8] Testing database initialization..." -ForegroundColor Cyan
$dbTest = @"
import sys
sys.path.insert(0, 'src')
from database.schema import init_db
try:
    db_path = init_db(test_mode=True)
    print('OK')
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
"@

$dbResult = python -c $dbTest 2>&1
if ($dbResult -match "OK") {
    Write-Host "✓ Database initialization works" -ForegroundColor Green
} else {
    Write-Host "✗ Database error: $dbResult" -ForegroundColor Red
    $ErrorCount++
}
Write-Host ""

# Summary
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

if ($ErrorCount -eq 0) {
    Write-Host "✓ ALL TESTS PASSED" -ForegroundColor Green
    Write-Host ""
    Write-Host "Ready to build!" -ForegroundColor Green
    Write-Host "Run: .\build.ps1 -BuildType msi" -ForegroundColor Cyan
    Write-Host ""
    exit 0
} else {
    Write-Host "✗ $ErrorCount TESTS FAILED" -ForegroundColor Red
    Write-Host ""
    Write-Host "DO NOT BUILD until all tests pass!" -ForegroundColor Red
    Write-Host "Fix the errors above and run this test again." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}
