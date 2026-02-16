# Package MSI with User Guide for Distribution
# Creates a ZIP file ready to share with users

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PBIP Studio - Distribution Packager" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if MSI exists
$msiFile = Get-ChildItem -Path "dist" -Filter "*.msi" -File | Select-Object -First 1

if (-not $msiFile) {
    Write-Host "ERROR: No MSI file found in dist folder" -ForegroundColor Red
    Write-Host "Please run .\build_msi.ps1 first" -ForegroundColor Yellow
    exit 1
}

Write-Host "Found MSI: $($msiFile.Name)" -ForegroundColor Green
Write-Host "Size: $([math]::Round($msiFile.Length / 1MB, 2)) MB" -ForegroundColor Cyan
Write-Host ""

# Extract version from MSI name (e.g., PBIP-Studio-1.0.0-win64.msi)
$version = "1.0.0"
if ($msiFile.Name -match '(\d+\.\d+\.\d+)') {
    $version = $matches[1]
}

# Create temp directory for packaging
$tempDir = "dist\package_temp"
if (Test-Path $tempDir) {
    Remove-Item -Path $tempDir -Recurse -Force
}
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

Write-Host "Preparing package contents..." -ForegroundColor Cyan

# Copy MSI
Copy-Item -Path $msiFile.FullName -Destination $tempDir
Write-Host "  ✓ Added: $($msiFile.Name)" -ForegroundColor Green

# Function to convert MD to TXT (strip Markdown formatting)
function Convert-MarkdownToText {
    param (
        [string]$SourcePath,
        [string]$DestinationPath
    )
    
    $content = Get-Content -Path $SourcePath -Raw -Encoding UTF8
    
    # Remove Markdown formatting for better plain text readability
    $content = $content -replace '```[\s\S]*?```', ''  # Remove code blocks
    $content = $content -replace '`([^`]+)`', '$1'      # Remove inline code backticks
    $content = $content -replace '^#{1,6}\s+', ''       # Remove heading markers
    $content = $content -replace '\*\*([^*]+)\*\*', '$1' # Remove bold
    $content = $content -replace '\*([^*]+)\*', '$1'    # Remove italic
    $content = $content -replace '^\s*[-*+]\s+', '  • ' # Convert bullet points
    $content = $content -replace '^\s*\d+\.\s+', ''     # Remove numbered list markers
    $content = $content -replace '\[([^\]]+)\]\([^\)]+\)', '$1' # Remove links, keep text
    
    # Clean up excessive whitespace
    $content = $content -replace '\n{3,}', "`n`n"
    
    $content | Out-File -FilePath $DestinationPath -Encoding UTF8
}

# Copy and convert installation guide to TXT
$readmeFile = "INSTALLATION_GUIDE_FOR_USERS.md"
if (Test-Path $readmeFile) {
    Convert-MarkdownToText -SourcePath $readmeFile -DestinationPath "$tempDir\README - HOW TO INSTALL.txt"
    Write-Host "  ✓ Added: README - HOW TO INSTALL.txt" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Warning: $readmeFile not found" -ForegroundColor Yellow
}

# Optional: Add user guide if exists
$userGuideHtml = "USER_GUIDE.html"
if (Test-Path $userGuideHtml) {
    Copy-Item -Path $userGuideHtml -Destination $tempDir
    Write-Host "  ✓ Added: USER_GUIDE.html" -ForegroundColor Green
}

Write-Host ""
Write-Host "Creating ZIP file..." -ForegroundColor Cyan

# Create ZIP file
$zipName = "PBIP-Studio-$version-Distribution.zip"
$zipPath = "dist\$zipName"

if (Test-Path $zipPath) {
    Remove-Item -Path $zipPath -Force
}

Compress-Archive -Path "$tempDir\*" -DestinationPath $zipPath -CompressionLevel Optimal

# Clean up temp directory
Remove-Item -Path $tempDir -Recurse -Force

if (Test-Path $zipPath) {
    $zipSize = (Get-Item $zipPath).Length
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✓ Package created successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Location: $zipPath" -ForegroundColor Cyan
    Write-Host "Size: $([math]::Round($zipSize / 1MB, 2)) MB" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Package contains:" -ForegroundColor Yellow
    Write-Host "  • $($msiFile.Name)" -ForegroundColor White
    Write-Host "  • README - HOW TO INSTALL.txt" -ForegroundColor White
    if (Test-Path $userGuideHtml) {
        Write-Host "  • USER_GUIDE.html" -ForegroundColor White
    }
    Write-Host ""
    Write-Host "✓ Ready to share with users!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Distribution instructions:" -ForegroundColor Yellow
    Write-Host "  1. Send users the ZIP file: $zipName" -ForegroundColor White
    Write-Host "  2. Tell them to extract all files" -ForegroundColor White
    Write-Host "  3. Tell them to read 'README - HOW TO INSTALL.txt' first" -ForegroundColor White
    Write-Host "  4. They can then run the MSI installer" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "ERROR: Failed to create ZIP file" -ForegroundColor Red
    exit 1
}
