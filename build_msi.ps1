# Build Script for MSI Installer
# This script builds a complete MSI package without interactive prompts

Write-Host "PBIP Studio - MSI Builder" -ForegroundColor Cyan
Write-Host "==========================" -ForegroundColor Cyan

# Step 1: Ensure data directory exists
Write-Host "`nStep 1: Preparing data directory..." -ForegroundColor Cyan
$dataFolder = "data"
if (-not (Test-Path $dataFolder)) {
    New-Item -ItemType Directory -Path $dataFolder -Force | Out-Null
    Write-Host "  ✓ Created data folder" -ForegroundColor Green
} else {
    Write-Host "  ✓ Data folder exists" -ForegroundColor Green
}
Write-Host "  Note: Database will be created automatically on first run" -ForegroundColor Yellow

# Step 2: Ensure config.md exists with blank template
Write-Host "`nStep 2: Checking config file..." -ForegroundColor Cyan
if (-not (Test-Path "config.md")) {
    Write-Host "  Creating blank config.md..." -ForegroundColor Yellow
    @"
# Fabric Configuration

tenantId = ""
clientId = ""
clientSecret = ""
"@ | Out-File -FilePath "config.md" -Encoding UTF8
    Write-Host "  ✓ Created blank config.md" -ForegroundColor Green
} else {
    Write-Host "  ✓ config.md exists" -ForegroundColor Green
}

# Step 3: Clean previous builds
Write-Host "`nStep 3: Cleaning previous builds..." -ForegroundColor Cyan
if (Test-Path "build") {
    Remove-Item -Path "build" -Recurse -Force
    Write-Host "  ✓ Removed build folder" -ForegroundColor Green
}
if (Test-Path "dist") {
    Remove-Item -Path "dist" -Recurse -Force
    Write-Host "  ✓ Removed dist folder" -ForegroundColor Green
}

# Step 4: Build MSI
Write-Host "`nStep 4: Building MSI installer..." -ForegroundColor Cyan
Write-Host "  This may take 5-10 minutes..." -ForegroundColor Yellow

if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "`n  ✗ Error: Virtual environment not found." -ForegroundColor Red
    Write-Host "  Run these commands first:" -ForegroundColor Yellow
    Write-Host "    python -m venv venv" -ForegroundColor White
    Write-Host "    .\venv\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host "    pip install -r requirements.txt" -ForegroundColor White
    exit 1
}

# Activate virtual environment
& .\venv\Scripts\Activate.ps1

# Run build in background with timeout protection
Write-Host "  Building (timeout: 15 minutes)..." -ForegroundColor Yellow

$buildScript = {
    param($workDir)
    Set-Location $workDir
    & .\venv\Scripts\Activate.ps1
    python setup.py bdist_msi 2>&1
}

$job = Start-Job -ScriptBlock $buildScript -ArgumentList (Get-Location).Path

# Wait for job with timeout
$timeout = 900 # 15 minutes
$waitResult = Wait-Job $job -Timeout $timeout

if ($waitResult) {
    $output = Receive-Job $job
    $exitCode = $job.State -eq "Completed"
    Remove-Job $job
    
    # Show output if there were errors
    if ($output -match "error|failed") {
        Write-Host "`n  Build output:" -ForegroundColor Yellow
        $output | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
    }
} else {
    Write-Host "`n  ✗ Build timed out after $timeout seconds" -ForegroundColor Red
    Stop-Job $job
    Remove-Job $job
    exit 1
}

# Check if MSI was created
$msiFile = Get-ChildItem -Path "dist" -Filter "*.msi" -ErrorAction SilentlyContinue | Select-Object -First 1

if ($msiFile) {
    Write-Host "`n✓ MSI built successfully!" -ForegroundColor Green
    Write-Host "`n================================================" -ForegroundColor Cyan
    Write-Host "MSI Location: $($msiFile.FullName)" -ForegroundColor White
    Write-Host "Size: $([math]::Round($msiFile.Length / 1MB, 2)) MB" -ForegroundColor White
    Write-Host "================================================" -ForegroundColor Cyan
    
    Write-Host "=== What's Included ===" -ForegroundColor Yellow
    Write-Host "  ✓ PBIP-Studio.exe" -ForegroundColor White
    Write-Host "  ✓ Blank config.md (fill via UI)" -ForegroundColor White
    Write-Host "  ✓ Documentation files" -ForegroundColor White
    Write-Host "  ✓ All Python dependencies" -ForegroundColor White
    
    # Check for code signing
    Write-Host "`n=== Code Signing Status ===" -ForegroundColor Yellow
    Write-Host "  ⚠ MSI is NOT digitally signed" -ForegroundColor Red
    Write-Host "  Users will see 'Unknown publisher' warning" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  To sign the MSI and remove warnings:" -ForegroundColor Cyan
    Write-Host "  1. For production: Get a code signing certificate (~$200-500/year)" -ForegroundColor White
    Write-Host "  2. For internal use: Run .\create_self_signed_cert.ps1" -ForegroundColor White
    Write-Host "  3. Then run: .\sign_installer.ps1 -CertificatePath 'path\to\cert.pfx' -CertificatePassword 'password'" -ForegroundColor White
    Write-Host ""
    Write-Host "  See SMARTSCREEN_SOLUTION_GUIDE.md for detailed options" -ForegroundColor Cyan
    
    Write-Host "`n=== Installation Steps ===" -ForegroundColor Yellow
    Write-Host "  1. Copy MSI to target machine" -ForegroundColor White
    Write-Host "  2. Double-click to install" -ForegroundColor White
    Write-Host "  3. If SmartScreen warning appears:" -ForegroundColor Yellow
    Write-Host "     - Click 'More info'" -ForegroundColor White
    Write-Host "     - Click 'Run anyway'" -ForegroundColor White
    Write-Host "  4. Launch from Start Menu" -ForegroundColor White
    Write-Host "  5. Enter credentials in Settings tab" -ForegroundColor White
    Write-Host "  6. Start using the toolkit!" -ForegroundColor White
    
    # Ask if user wants to create distribution package
    Write-Host "`n=== Distribution Package ===" -ForegroundColor Yellow
    Write-Host "  Create a ZIP file with MSI and installation guide?" -ForegroundColor Cyan
    Write-Host "  (Ready to share with users)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  [Y] Yes  [N] No  (default is Y): " -ForegroundColor White -NoNewline
    
    $response = Read-Host
    if ($response -eq "" -or $response -eq "Y" -or $response -eq "y") {
        Write-Host ""
        & .\package_for_distribution.ps1
    } else {
        Write-Host ""
        Write-Host "  Skipped. You can run .\package_for_distribution.ps1 later" -ForegroundColor Gray
        Write-Host ""
    }
} else {
    Write-Host "`n✗ Build failed - MSI not found in dist folder" -ForegroundColor Red
    Write-Host "Check build output above for errors" -ForegroundColor Yellow
    exit 1
}
