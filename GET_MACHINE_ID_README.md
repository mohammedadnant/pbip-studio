# Get Machine ID for License Activation

This folder contains simple scripts to get your **Machine ID** for PowerBI Desktop App license activation.

## 📋 What is Machine ID?

Your Machine ID is a unique identifier for your computer. You need to send it to **support@taik18.com** to receive your license key.

---

## 🚀 Quick Start - Choose One Method

### Method 1: PowerShell Script (Recommended for Windows Users)

**Easiest method - no installation required!**

1. **Right-click** on `get_machine_id.ps1`
2. Select **"Run with PowerShell"**
3. Your Machine ID will be displayed and automatically copied to clipboard
4. Email it to **support@taik18.com**

**Alternative (if right-click doesn't work):**
```powershell
powershell -ExecutionPolicy Bypass -File get_machine_id.ps1
```

---

### Method 2: Python Script

**If you have Python installed:**

1. Open terminal/command prompt
2. Navigate to this folder
3. Run:
   ```bash
   python get_machine_id.py
   ```
4. Your Machine ID will be displayed and copied to clipboard
5. Email it to **support@taik18.com**

**Optional: Install for better compatibility:**
```bash
pip install wmi pyperclip
```

---

## 📧 What to Send

**Email to:** support@taik18.com

**Subject:** License Request - [Your Name]

**Body:**
```
Hello,

I would like to request a license key for PowerBI Desktop App.

My Machine ID: [paste your Machine ID here]

Thank you!
```

---

## ⏱️ Response Time

You'll receive your license key within:
- ✅ **1-2 hours** (typical)
- ✅ **Maximum 24 hours**

---

## 🔐 Why Machine ID?

- **Security**: Ensures your license works only on your computer
- **Offline Activation**: No internet required after initial activation
- **One License Per Machine**: Prevents unauthorized sharing

---

## ❓ Troubleshooting

### "Cannot be loaded because running scripts is disabled"

If PowerShell script doesn't run:

1. Open PowerShell as Administrator
2. Run: `Set-ExecutionPolicy RemoteSigned`
3. Type `Y` and press Enter
4. Try running the script again

OR use the Python script instead.

### Python Script Issues

If you get errors with Python script:

1. Make sure Python is installed: `python --version`
2. Install dependencies: `pip install wmi pyperclip`
3. Or just use the PowerShell script (easier!)

### Machine ID Looks Different

**This is normal!** Machine IDs can vary slightly if:
- You reinstall Windows
- You change hardware
- System configuration changes

**Solution:** Just send the new Machine ID to support for a new license key.

---

## 📞 Support

**Email:** support@taik18.com

**For:**
- License requests
- License renewals
- Moving license to new computer
- Any activation issues

---

## 📝 Notes

- ✅ Keep your Machine ID safe (you might need it later)
- ✅ One Machine ID = One Computer
- ✅ Different computers have different Machine IDs
- ✅ Changing hardware may change your Machine ID

---

**Thank you for using PowerBI Desktop App!**
