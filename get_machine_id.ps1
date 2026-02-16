# PowerBI Desktop App - Machine ID Generator
# This script generates your unique Machine ID for license activation
# Send the Machine ID to support@taik18.com to receive your license key

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "PowerBI Desktop App - Machine ID Generator" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Generating your unique Machine ID..." -ForegroundColor Yellow
Write-Host ""

# Collect system identifiers
$identifiers = @()

try {
    # Get System UUID
    $uuid = (Get-CimInstance -ClassName Win32_ComputerSystemProduct).UUID
    if ($uuid -and $uuid -ne "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF") {
        $identifiers += $uuid
    }

    # Get CPU ID
    $cpuId = (Get-CimInstance -ClassName Win32_Processor | Select-Object -First 1).ProcessorId
    if ($cpuId) {
        $identifiers += $cpuId
    }

    # Get Motherboard Serial
    $boardSerial = (Get-CimInstance -ClassName Win32_BaseBoard | Select-Object -First 1).SerialNumber
    if ($boardSerial) {
        $identifiers += $boardSerial
    }

    # If no identifiers, use MAC address
    if ($identifiers.Count -eq 0) {
        $mac = (Get-NetAdapter | Where-Object {$_.Status -eq "Up"} | Select-Object -First 1).MacAddress
        if ($mac) {
            $identifiers += $mac
        }
    }

    # Combine identifiers
    $combined = $identifiers -join "|"

    # Generate SHA256 hash and take first 16 characters
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    $hashBytes = $sha256.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($combined))
    $hashString = [System.BitConverter]::ToString($hashBytes).Replace("-", "").ToLower()
    $machineId = $hashString.Substring(0, 16)

    # Display Machine ID
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "YOUR MACHINE ID:" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "    $machineId" -ForegroundColor White -BackgroundColor DarkBlue
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""

    # Copy to clipboard
    try {
        Set-Clipboard -Value $machineId
        Write-Host "✓ Machine ID has been copied to your clipboard!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next Steps:" -ForegroundColor Yellow
        Write-Host "1. Email this Machine ID to: support@taik18.com" -ForegroundColor White
        Write-Host "2. Subject: 'License Request - [Your Name]'" -ForegroundColor White
        Write-Host "3. You'll receive your license key within 1-2 hours" -ForegroundColor White
    }
    catch {
        Write-Host "Note: Could not auto-copy to clipboard." -ForegroundColor Yellow
        Write-Host "Please manually copy the Machine ID above." -ForegroundColor White
        Write-Host ""
        Write-Host "Next Steps:" -ForegroundColor Yellow
        Write-Host "1. Copy the Machine ID above" -ForegroundColor White
        Write-Host "2. Email it to: support@taik18.com" -ForegroundColor White
        Write-Host "3. Subject: 'License Request - [Your Name]'" -ForegroundColor White
        Write-Host "4. You'll receive your license key within 1-2 hours" -ForegroundColor White
    }

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""

}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please contact support@taik18.com for assistance." -ForegroundColor Yellow
    Write-Host ""
}

# Wait for user to press Enter
Write-Host "Press Enter to exit..." -ForegroundColor Gray
$null = Read-Host
