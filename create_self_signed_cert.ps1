# Create Self-Signed Certificate for Code Signing
# Use this for testing or internal distribution only
# Users will need to trust this certificate manually

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Self-Signed Certificate Creator" -ForegroundColor Yellow
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Certificate details
$certName = "PBIP Studio Publisher"
$certSubject = "CN=PBIP Studio Publisher,O=Your Organization,C=US"
$certPassword = ConvertTo-SecureString -String "YourStrongPassword123!" -Force -AsPlainText

# Create certificate
Write-Host "Creating self-signed certificate..." -ForegroundColor Cyan
$cert = New-SelfSignedCertificate `
    -Type CodeSigningCert `
    -Subject $certSubject `
    -KeyUsage DigitalSignature `
    -FriendlyName $certName `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}") `
    -NotAfter (Get-Date).AddYears(5)

Write-Host "✓ Certificate created!" -ForegroundColor Green
Write-Host "  Thumbprint: $($cert.Thumbprint)" -ForegroundColor Cyan
Write-Host ""

# Export certificate for distribution
$exportPath = ".\PBIP-Studio-Certificate.cer"
Export-Certificate -Cert $cert -FilePath $exportPath | Out-Null
Write-Host "✓ Certificate exported to: $exportPath" -ForegroundColor Green
Write-Host ""

# Export PFX with private key for signing
$pfxPath = ".\PBIP-Studio-Certificate.pfx"
Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $certPassword | Out-Null
Write-Host "✓ PFX exported to: $pfxPath" -ForegroundColor Green
Write-Host "  Password: YourStrongPassword123!" -ForegroundColor Yellow
Write-Host ""

Write-Host "IMPORTANT NOTES:" -ForegroundColor Yellow
Write-Host "================" -ForegroundColor Yellow
Write-Host "1. Use this PFX to sign your MSI:" -ForegroundColor Cyan
Write-Host "   .\sign_installer.ps1 -CertificatePath '$pfxPath' -CertificatePassword 'YourStrongPassword123!'" -ForegroundColor White
Write-Host ""
Write-Host "2. Users must install the certificate ($exportPath) to 'Trusted Root Certification Authorities' to avoid warnings:" -ForegroundColor Cyan
Write-Host "   - Right-click the .cer file > Install Certificate" -ForegroundColor White
Write-Host "   - Select 'Local Machine'" -ForegroundColor White
Write-Host "   - Choose 'Place all certificates in the following store'" -ForegroundColor White
Write-Host "   - Browse > Select 'Trusted Root Certification Authorities'" -ForegroundColor White
Write-Host ""
Write-Host "3. This is ONLY suitable for internal/testing use" -ForegroundColor Red
Write-Host "   For public distribution, get a real code signing certificate" -ForegroundColor Red
Write-Host ""

# Save instructions
$instructions = @"
# Installing PBIP Studio Certificate

To avoid Windows SmartScreen warnings, you need to trust the PBIP Studio certificate.

## Steps:
1. Right-click on 'PBIP-Studio-Certificate.cer'
2. Select 'Install Certificate'
3. Choose 'Local Machine' (requires administrator)
4. Select 'Place all certificates in the following store'
5. Click 'Browse' and select 'Trusted Root Certification Authorities'
6. Click 'OK' and complete the wizard

## Command Line (Run as Administrator):
``````powershell
certutil -addstore -f "Root" "PBIP-Studio-Certificate.cer"
``````

## Security Note:
This is a self-signed certificate created specifically for PBIP Studio.
Only install if you trust the source of this application.
"@

$instructions | Out-File -FilePath "CERTIFICATE_INSTALL_INSTRUCTIONS.md" -Encoding UTF8
Write-Host "✓ Installation instructions saved to: CERTIFICATE_INSTALL_INSTRUCTIONS.md" -ForegroundColor Green
