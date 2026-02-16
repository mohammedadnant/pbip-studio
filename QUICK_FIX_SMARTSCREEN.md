# Quick Fix: Windows SmartScreen Warning

## The Warning You See:
```
Windows protected your PC
Microsoft Defender SmartScreen prevented an unrecognized app from starting.

App: PBIP Studio-1.0.0-win64.msi
Publisher: Unknown publisher
```

## How to Install (2 Simple Steps):

### 1️⃣ Click "More info"
### 2️⃣ Click "Run anyway"

✅ That's it! The installer will start normally.

---

## Why This Happens?
The app isn't digitally signed yet. This is normal for new/independent software.

## Is It Safe?
- ✅ Yes, the source code is available on GitHub
- ✅ You can scan the MSI with antivirus
- ✅ Thousands of apps show this warning

---

## For Developers: How to Fix

### Quick (Free, but users see warning):
Include the user guide above with your MSI

### Professional ($200-500/year):
1. Buy code signing certificate from DigiCert/Sectigo
2. Run: `.\sign_installer.ps1 -CertificatePath "cert.pfx" -CertificatePassword "pass"`
3. ✅ No more warnings!

### Free for Open Source:
Apply to SignPath Foundation (https://signpath.org/)

### Internal Use Only:
1. Run: `.\create_self_signed_cert.ps1`
2. Run: `.\sign_installer.ps1 -CertificatePath "PBIP-Studio-Certificate.pfx" -CertificatePassword "YourStrongPassword123!"`
3. Share `PBIP-Studio-Certificate.cer` with users
4. Users install certificate to Trusted Root

---

**See SMARTSCREEN_SOLUTION_GUIDE.md for detailed options**
