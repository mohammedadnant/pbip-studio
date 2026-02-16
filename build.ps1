# Build Script for PBIP Studio
# Run this to build executable and installer

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('exe', 'msi', 'both')]
    [string]$BuildType = 'exe'
)

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "PBIP Studio - Build Script" -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    & ".\venv\Scripts\Activate.ps1"
} else {
    Write-Host "ERROR: Virtual environment not found. Run start.ps1 first." -ForegroundColor Red
    exit 1
}

# Clean previous builds
if (Test-Path "build") {
    Write-Host "Cleaning previous build..." -ForegroundColor Cyan
    Remove-Item -Recurse -Force "build"
}

if (Test-Path "dist") {
    Write-Host "Cleaning previous dist..." -ForegroundColor Cyan
    Remove-Item -Recurse -Force "dist"
}

Write-Host ""

# Build EXE
if ($BuildType -eq 'exe' -or $BuildType -eq 'both') {
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host "Building EXE with PyInstaller..." -ForegroundColor Yellow
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host ""
    
    pyinstaller pbip-studio.spec
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "EXE built successfully!" -ForegroundColor Green
        Write-Host "Location: dist\PBIP-Studio.exe" -ForegroundColor Cyan
        
        if (Test-Path "dist\PBIP-Studio.exe") {
            $exeSize = (Get-Item "dist\PBIP-Studio.exe").Length / 1MB
            Write-Host "Size: $([math]::Round($exeSize, 2)) MB" -ForegroundColor Cyan
        }
    } else {
        Write-Host "ERROR: EXE build failed" -ForegroundColor Red
        exit 1
    }
    
    Write-Host ""
}

# Build MSI
if ($BuildType -eq 'msi' -or $BuildType -eq 'both') {
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host "Building MSI with cx_Freeze..." -ForegroundColor Yellow
    Write-Host "================================================" -ForegroundColor Cyan
    Write-Host ""
    
    python setup.py bdist_msi
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "MSI built successfully!" -ForegroundColor Green
        
        $msiFile = Get-ChildItem -Path "dist" -Filter "*.msi" | Select-Object -First 1
        if ($msiFile) {
            Write-Host "Location: dist\$($msiFile.Name)" -ForegroundColor Cyan
            $msiSize = $msiFile.Length / 1MB
            Write-Host "Size: $([math]::Round($msiSize, 2)) MB" -ForegroundColor Cyan
        }
    } else {
        Write-Host "ERROR: MSI build failed" -ForegroundColor Red
        exit 1
    }
    
    Write-Host ""
}

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Build Complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Test the executable on your machine" -ForegroundColor Cyan
Write-Host "2. Test on a clean Windows machine (no Python installed)" -ForegroundColor Cyan
Write-Host "3. Consider code signing for IT acceptance" -ForegroundColor Cyan
Write-Host "4. Distribute to users" -ForegroundColor Cyan
Write-Host ""
