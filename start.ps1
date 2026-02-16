# Quick Start Script for PBIP Studio
# Run this to set up and start the application

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "PBIP Studio - Quick Start" -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check Python installation
Write-Host "Checking Python installation..." -ForegroundColor Cyan
$pythonVersion = python --version 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found. Please install Python 3.10 or later." -ForegroundColor Red
    Write-Host "Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

Write-Host "Found: $pythonVersion" -ForegroundColor Green
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv venv
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Virtual environment created successfully" -ForegroundColor Green
    Write-Host ""
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& ".\venv\Scripts\Activate.ps1"

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to activate virtual environment" -ForegroundColor Red
    Write-Host "You may need to run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Yellow
    exit 1
}

Write-Host "Virtual environment activated" -ForegroundColor Green
Write-Host ""

# Check if requirements are installed
$pipList = pip list
$needsInstall = $false

if ($pipList -notmatch "PyQt6") {
    $needsInstall = $true
}

if ($needsInstall) {
    Write-Host "Installing dependencies..." -ForegroundColor Cyan
    pip install -r requirements.txt
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install dependencies" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Dependencies installed successfully" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "Dependencies already installed" -ForegroundColor Green
    Write-Host ""
}

# Create data directory if it doesn't exist
if (-not (Test-Path "data")) {
    Write-Host "Creating data directory..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Path "data" | Out-Null
    Write-Host "Data directory created" -ForegroundColor Green
    Write-Host ""
}

# Start application
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Starting PBIP Studio..." -ForegroundColor Yellow
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "The application will open in a new window." -ForegroundColor Cyan
Write-Host "To stop the application, close the window or press Ctrl+C here." -ForegroundColor Cyan
Write-Host ""

python src/main.py

Write-Host ""
Write-Host "Application closed." -ForegroundColor Yellow
