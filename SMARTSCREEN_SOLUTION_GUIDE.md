# Building SmartScreen Reputation Guide
# This guide helps you understand how to make your app trusted without buying a certificate

## What is SmartScreen Reputation?

Microsoft SmartScreen builds reputation for your application based on:
- Number of downloads
- Download sources
- User feedback
- Digital signature (if available)

## How to Build Reputation (Without Code Signing Certificate)

### 1. Consistent File Properties
Always use the same:
- File name (e.g., PBIP-Studio-1.0.0.msi)
- Publisher name in the MSI
- Product information

### 2. Distribution Strategy

**IMPORTANT:** SmartScreen tracks files by their hash. Each new build = new file = no reputation.

Best practices:
- Keep version stable for distribution
- Don't rebuild frequently for minor changes
- Distribute from consistent URLs
- Use GitHub Releases (helps with reputation)

### 3. Submit to Microsoft for Analysis
- Submit your installer to Microsoft: https://www.microsoft.com/en-us/wdsi/filesubmission
- This helps Microsoft verify your app is safe

### 4. User Installation Instructions

**For users getting the SmartScreen warning:**

1. Click "More info"
2. Click "Run anyway"
3. After several users do this successfully, reputation builds

### 5. Alternative: Build Reputation with Downloads

Microsoft SmartScreen tracks download counts from:
- Direct download links
- GitHub releases
- Other distribution channels

**Estimated timeline:**
- 10-50 downloads: May still show warnings
- 100+ downloads: Warnings may decrease
- 500+ downloads: Better reputation
- This can take weeks to months

## Realistic Options

### For Internal/Corporate Use:
1. Use self-signed certificate (see create_self_signed_cert.ps1)
2. Deploy certificate to company machines via Group Policy
3. Or add app to SmartScreen allowlist via Group Policy

### For Public Distribution:
1. **Buy a code signing certificate** ($200-500/year) - RECOMMENDED
   - DigiCert, Sectigo, GlobalSign
   - Instant trust, no warnings
   
2. **Free for Open Source**: 
   - Apply to SignPath Foundation: https://signpath.org/
   - Provides free code signing for OSS projects

### For Testing/Development:
1. Use self-signed certificate
2. Share certificate with testers
3. Testers install certificate to trust store

## Quick Workaround for End Users

Create an installation guide that shows users how to bypass the warning:

1. When SmartScreen blocks the file:
   - Click "More info"
   - Click "Run anyway"

2. Alternative - Disable SmartScreen temporarily (NOT RECOMMENDED):
   ``````
   Windows Security > App & browser control > Reputation-based protection settings
   Turn off "Check apps and files"
   ``````

## Recommended Approach

Based on your use case:

| Use Case | Solution |
|----------|----------|
| Internal company use | Self-signed cert + deploy to machines |
| Public/Customer distribution | Buy code signing certificate |
| Open source project | Apply for free SignPath certificate |
| Testing/Development | Self-signed cert + share with testers |
| Quick fix for friends | Share "Run anyway" instructions |

## Cost Comparison

| Method | Cost | Trust Level | Setup Time |
|--------|------|-------------|------------|
| Code Signing Cert | $200-500/year | 100% - No warnings | 1-3 days |
| Self-Signed + Deploy | Free | 100% (internal only) | 1 hour |
| SmartScreen Reputation | Free | 70-90% (takes time) | Weeks/months |
| SignPath (OSS) | Free | 100% - No warnings | 1-2 weeks approval |

## Next Steps

Choose your path and run the appropriate script:

1. **Professional distribution:** Buy certificate → run `sign_installer.ps1`
2. **Internal use:** Run `create_self_signed_cert.ps1` → deploy to machines
3. **Public free:** Apply to SignPath → run `sign_installer.ps1` once approved
4. **Quick start:** Share installation guide with users about "Run anyway"
