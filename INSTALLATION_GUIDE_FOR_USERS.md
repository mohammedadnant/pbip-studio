# How to Install PBIP Studio

## Windows SmartScreen Warning

When you try to install PBIP Studio, you may see a Windows SmartScreen warning that says:

> **"Windows protected your PC"**  
> Microsoft Defender SmartScreen prevented an unrecognized app from starting.
> 
> App: PBIP Studio-1.0.0-win64.msi  
> Publisher: Unknown publisher

**This is normal for new applications that aren't digitally signed yet.**

## How to Proceed Safely

### Step 1: Click "More info"
When you see the SmartScreen warning, click on the **"More info"** link.

### Step 2: Click "Run anyway"
A new button will appear at the bottom. Click **"Run anyway"** to continue with the installation.

### Step 3: Complete Installation
The Windows Installer will start normally. Follow the installation wizard to install PBIP Studio.

## Why This Happens

Windows SmartScreen shows this warning for applications that:
- Don't have a digital signature from a recognized publisher
- Haven't built up download reputation with Microsoft
- Are newly released or updated

**This doesn't mean the application is unsafe** - it just means Microsoft doesn't recognize the publisher yet.

## For IT Administrators

If you're deploying PBIP Studio in a corporate environment:

### Option 1: Group Policy Allowlist
Add the application to your SmartScreen allowlist via Group Policy.

### Option 2: Install Certificate
If the developer provides a certificate file (`.cer`):

1. Run as Administrator:
   ```powershell
   certutil -addstore -f "Root" "PBIP-Studio-Certificate.cer"
   ```

2. Or via GUI:
   - Right-click certificate → Install Certificate
   - Select "Local Machine"
   - Place in "Trusted Root Certification Authorities"

### Option 3: Silent Installation
For automated deployment:
```powershell
msiexec /i "PBIP-Studio-1.0.0-win64.msi" /quiet /qn
```

## Security Note

PBIP Studio is open-source software. You can:
- Review the source code on GitHub
- Verify the application doesn't contain malware
- Build it yourself from source if preferred

## Need Help?

If you have concerns or questions:
- Check the GitHub repository
- Review the source code
- Contact the development team
- Run a virus scan on the MSI file using your preferred antivirus

## Future Updates

In future versions, PBIP Studio may include:
- Digital code signing certificate (removes warnings completely)
- Automatic updates through Microsoft Store
- Alternative installation methods

---

**Thank you for using PBIP Studio!**
