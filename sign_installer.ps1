# Sign MSI Installer with Code Signing Certificate
# Run this after building the MSI

param(
    [Parameter(Mandatory=$false)]
    [string]$CertificateThumbprint = "",
    
    [Parameter(Mandatory=$false)]
    [string]$CertificatePath = "",
    
    [Parameter(Mandatory=$false)]
    [string]$CertificatePassword = "",
    
    [Parameter(Mandatory=$false)]
    [string]$TimestampServer = "http://timestamp.digicert.com"
)

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "MSI Code Signing Tool" -ForegroundColor Yellow
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Find MSI file
$msiFile = Get-ChildItem -Path "dist" -Filter "*.msi" -File | Select-Object -First 1

if (-not $msiFile) {
    Write-Host "ERROR: No MSI file found in dist folder" -ForegroundColor Red
    exit 1
}

Write-Host "Found MSI: $($msiFile.Name)" -ForegroundColor Green
Write-Host ""

# Check if signtool is available
$signtool = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe"
if (-not (Test-Path $signtool)) {
    # Try to find signtool in PATH or common locations
    $signtool = Get-Command signtool.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
    if (-not $signtool) {
        Write-Host "ERROR: signtool.exe not found" -ForegroundColor Red
        Write-Host "Install Windows SDK from: https://developer.microsoft.com/windows/downloads/windows-sdk/" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "Using signtool: $signtool" -ForegroundColor Cyan
Write-Host ""

# Build signtool command
if ($CertificateThumbprint) {
    # Sign using certificate from Windows Certificate Store
    Write-Host "Signing with certificate from store (thumbprint: $CertificateThumbprint)..." -ForegroundColor Cyan
    
    & $signtool sign /sha1 $CertificateThumbprint /fd SHA256 /tr $TimestampServer /td SHA256 /d "PBIP Studio" /du "https://github.com/yourusername/yourrepo" $msiFile.FullName
    
} elseif ($CertificatePath) {
    # Sign using PFX certificate file
    Write-Host "Signing with certificate file: $CertificatePath..." -ForegroundColor Cyan
    
    if ($CertificatePassword) {
        & $signtool sign /f $CertificatePath /p $CertificatePassword /fd SHA256 /tr $TimestampServer /td SHA256 /d "PBIP Studio" /du "https://github.com/yourusername/yourrepo" $msiFile.FullName
    } else {
        & $signtool sign /f $CertificatePath /fd SHA256 /tr $TimestampServer /td SHA256 /d "PBIP Studio" /du "https://github.com/yourusername/yourrepo" $msiFile.FullName
    }
    
} else {
    Write-Host "ERROR: No certificate specified" -ForegroundColor Red
    Write-Host ""
    Write-Host "Usage examples:" -ForegroundColor Yellow
    Write-Host "  1. Using certificate from store:" -ForegroundColor Cyan
    Write-Host "     .\sign_installer.ps1 -CertificateThumbprint 'YOUR_CERT_THUMBPRINT'" -ForegroundColor White
    Write-Host ""
    Write-Host "  2. Using PFX file:" -ForegroundColor Cyan
    Write-Host "     .\sign_installer.ps1 -CertificatePath 'C:\path\to\cert.pfx' -CertificatePassword 'password'" -ForegroundColor White
    Write-Host ""
    Write-Host "To find certificate thumbprint:" -ForegroundColor Yellow
    Write-Host "  Get-ChildItem -Path Cert:\CurrentUser\My | Where-Object {`$_.Subject -like '*YourName*'}" -ForegroundColor White
    exit 1
}

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✓ MSI signed successfully!" -ForegroundColor Green
    Write-Host ""
    
    # Verify signature
    Write-Host "Verifying signature..." -ForegroundColor Cyan
    & $signtool verify /pa /v $msiFile.FullName
    
} else {
    Write-Host ""
    Write-Host "✗ Signing failed!" -ForegroundColor Red
    exit 1
}
