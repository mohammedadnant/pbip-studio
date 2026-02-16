# License System Setup Guide

## Overview
This application uses a **simple offline license key system** with:
- ✅ 1-year licenses (365 days validity)
- ✅ Offline activation (no internet required)
- ✅ Machine-locked (1 license per machine)
- ✅ No server maintenance needed
- ✅ Manual revocation support
- ✅ Copy Machine ID button for easy customer workflow

---

## 🔑 IMPORTANT: Generate Your Secret Key

**BEFORE distributing your app**, you MUST change the master secret key in `src/utils/license_manager.py`:

### Step 1: Generate a Secret Key

Run this in PowerShell:
```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Example output:
```
XaB3Kp8Qm9Zr5Yw2Nv7Lj4Hg6Fd1Cs0=-
```

### Step 2: Update license_manager.py

Open `src/utils/license_manager.py` and find this line (around line 22):
```python
MASTER_SECRET = b'YOUR_SECRET_KEY_HERE_CHANGE_THIS_BEFORE_DISTRIBUTION'
```

Replace it with your generated key:
```python
MASTER_SECRET = b'XaB3Kp8Qm9Zr5Yw2Nv7Lj4Hg6Fd1Cs0=-'
```

⚠️ **CRITICAL**: 
- Keep this secret secure - it's used to sign all license keys
- Never share it publicly or commit it to public repos
- If compromised, anyone can generate valid licenses
- If lost, you cannot generate new licenses for existing customers

---

## 📦 How to Generate License Keys

### Customer Workflow (Machine-Locked Licenses):

**Step 1: Customer Purchases**
- Customer pays for the application
- You receive order confirmation with customer email

**Step 2: Request Machine ID**
Send customer this email:

```
Subject: PowerBI Desktop App - Activation Instructions

Thank you for purchasing PowerBI Desktop App!

To activate your license, please follow these steps:

1. Download and install the application from: [Google Drive Link]
2. Launch the application
3. When the License Activation dialog appears, click the "📋 Copy" button next to your Machine ID
4. Reply to this email with your Machine ID

We'll send you your license key within 1-2 hours (max 24 hours).

Best regards,
Support Team
```

**Step 3: Customer Sends Machine ID**
Customer replies with: `My Machine ID is: 3fd26d46a6cf64ae`

**Step 4: Generate Machine-Locked License**
```powershell
python generate_license.py customer@email.com --machine-id 3fd26d46a6cf64ae
```

**Output:**
```
============================================================
PowerBI Desktop App - License Key Generator
============================================================

Customer Email: customer@email.com
License Duration: 365 days (1 year)
Expiry Date: 2026-12-22
Machine-Locked: YES (ID: 3fd26d46a6cf64ae)

============================================================
LICENSE KEY (send this to customer):
============================================================

PBMT-eyJlbWFpbCI6ImN1c3RvbWVyQGVtYWlsLmNvbSIsImV4cGlyeSI6IjIwMjYtMTItMjJUMTI6MzQ6NTYiLCJtYWNoaW5lX2lkIjoiM2ZkMjZkNDZhNmNmNjRhZSJ9-a3b5c7d9e2f4

============================================================

✓ License key validated successfully
✓ Valid for 365 days
```

**Step 5: Send License Key to Customer**
Email the key to customer → They paste it → Works only on their specific PC!

### For 2-Year Licenses:
```powershell
python generate_license.py customer@email.com --machine-id 3fd26d46a6cf64ae --days 730
```

### For Custom Duration:
```powershell
python generate_license.py customer@email.com --machine-id abc123def456 --days 180  # 6 months
```

---

## 👤 Customer Usage Flow

### First Launch (No License):
1. User downloads and installs MSI from Google Drive
2. User launches app
3. **License activation dialog appears automatically**
4. User sees their unique Machine ID with a "📋 Copy" button
5. User clicks Copy button → Machine ID copied to clipboard
6. User emails Machine ID to support@taik18.com
7. Within 1-2 hours, user receives license key via email
8. User enters license key in the activation dialog
9. User clicks "Activate License"
10. ✅ App activates (license is permanently bound to this specific machine)
11. App opens normally

### Subsequent Launches:
1. User launches app
2. App checks stored license (offline)
3. If valid → app opens normally
4. If expired → shows activation dialog again

### Expiry Warning:
- If less than 30 days remaining, user sees warning notification
- User can continue using until expiry date
- After expiry, activation dialog appears again

### Moving to New Machine:
1. User clicks license key icon (🔑) in app header
2. User clicks "Revoke License" button
3. Confirms revocation
4. App closes
5. User installs on new machine
6. User copies new Machine ID and emails to support
7. You generate new license with new Machine ID
8. ✅ User activates on new machine

---

## 🛠️ Technical Details

### License Key Format:
```
PBMT-<base64-payload>-<hmac-signature>

Payload contains:
- Customer email
- Expiry date (ISO format)
- Version number
- Machine ID (for machine-locked licenses)
```

### Security Features:
- ✅ HMAC-SHA256 signature prevents tampering
- ✅ Encrypted local storage using Fernet (AES-128)
- ✅ Machine ID embedded in license key (bulletproof machine locking)
- ✅ Machine fingerprint binding (CPU ID, motherboard serial, UUID)
- ✅ Offline validation (no network calls)
- ✅ One-click Machine ID copy for easy customer workflow

### Storage Location:
```
Windows: C:\Users\<username>\.powerbi_toolkit\license.dat
```

### Machine Fingerprint:
The app generates a unique fingerprint using:
1. Windows Machine UUID (from WMI)
2. CPU Processor ID
3. Motherboard Serial Number
4. Fallback to MAC address if above fail

Hashed to 16-character hex string for storage and display.

**Customer Experience**: 
- Machine ID is displayed in white, bold text (highly visible)
- One-click copy button eliminates typing errors
- Clear instructions guide customer through the process

---

## 🚨 Troubleshooting

### Customer Reports: "License is locked to a different machine"
**This means**: The license key was generated for a different Machine ID

**Solution:**
1. Ask customer to send their current Machine ID (click Copy button in dialog)
2. Generate new license with the correct Machine ID
3. Send new key to customer

### Customer Lost Access to Old Machine
**Scenario**: Customer wants to move to new PC but can't access old machine to revoke

**Solution:**
1. Customer sends new Machine ID from new PC
2. You generate new license with new Machine ID:
   ```powershell
   python generate_license.py customer@email.com --machine-id NEW_MACHINE_ID --days 365
   ```
3. Send new key to customer
4. Old license becomes useless (won't work on any machine)

### Customer Accidentally Revoked License
**Solution:**
Tell customer to re-enter their original license key - it will reactivate on the same machine.

### License Key Not Working
**Check:**
1. ✅ Verify Machine ID matches (customer may have sent wrong ID)
2. ✅ Ensure customer copied entire key (no line breaks)
3. ✅ Key format: must start with `PBMT-`
4. ✅ Secret key in `license_manager.py` matches what was used to generate
5. ✅ Generate new test key with same Machine ID and try

### Customer Can't Find Machine ID
**Guide them:**
1. Launch the application
2. License activation dialog appears automatically
3. Look for "Machine Information" section
4. Machine ID is displayed in white/bold text
5. Click the blue "📋 Copy" button
6. Machine ID is now in clipboard - paste into email

### App Won't Start After Adding License System
**Check:**
1. ✅ `cryptography` package installed: `pip install cryptography`
2. ✅ Check logs: `C:\Users\<username>\AppData\Local\PowerBI Migration Toolkit\logs\app.log`
3. ✅ Test license generation script first
4. ✅ Ensure MASTER_SECRET is set correctly

---

## 📋 Pre-Distribution Checklist

Before building and distributing your MSI:

- [ ] **Changed `MASTER_SECRET` in `license_manager.py`**
- [ ] **Backed up secret key in secure location**
- [ ] **Updated contact email in `license_dialog.py`** (should be `support@taik18.com`)
- [ ] **Tested license generation script with `--machine-id` parameter**
- [ ] **Generated test license and verified activation works**
- [ ] **Tested "Copy Machine ID" button functionality**
- [ ] **Built MSI with PyInstaller/cx-Freeze**
- [ ] **Tested installed MSI shows activation dialog with visible Machine ID**
- [ ] **Prepared email templates for customer communication**

---

## 📧 Customer Email Templates

### Initial Purchase Confirmation:

```
Subject: PowerBI Desktop App - Activation Instructions

Dear [Customer Name],

Thank you for purchasing PowerBI Desktop App!

To activate your license, please follow these steps:

STEP 1: Download & Install
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Download the installer from: [Google Drive Link]
Run the installer and complete the setup

STEP 2: Get Your Machine ID
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Launch the application
2. The License Activation dialog will appear
3. Find your Machine ID in the "Machine Information" section
4. Click the "📋 Copy" button next to your Machine ID

STEP 3: Send Us Your Machine ID
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Reply to this email with your copied Machine ID

STEP 4: Receive & Activate
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
We'll send you your license key within 1-2 hours (max 24 hours)
Enter the key in the activation dialog and click "Activate License"

IMPORTANT NOTES:
• Your license is valid for ONE computer only
• License keys are machine-specific for security
• Keep your license key safe for reinstallation
• Valid for 1 year from activation date

Need help? Contact: support@taik18.com

Best regards,
PowerBI Desktop App Team
```

### License Key Delivery:

```
Subject: Your PowerBI Desktop App License Key

Dear [Customer Name],

Your license key is ready! Here are your activation details:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LICENSE KEY:
PBMT-[generated-key-here]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ACTIVATION INSTRUCTIONS:
1. Open PowerBI Desktop App
2. Paste the license key above in the activation dialog
3. Click "Activate License"
4. ✓ You're ready to go!

LICENSE DETAILS:
• Email: [customer@email.com]
• Machine ID: [abc123def456]
• Valid for: 1 year
• Expires: [2026-12-22]

IMPORTANT:
✓ This license is locked to your specific computer (Machine ID: [abc123...])
✓ Cannot be used on other computers for security
✓ To move to a new computer, use "Revoke License" option first
✓ Keep this email safe - you'll need it if you reinstall

Need to move to a different computer? Contact support@taik18.com

Thank you for your purchase!

Best regards,
PowerBI Desktop App Team
```

---

## 🔄 Annual Renewal Process

When customer's license expires:

1. Customer contacts you for renewal
2. Ask if they're using the same computer (Machine ID)
3. **Same computer**:
   ```powershell
   python generate_license.py customer@email.com --machine-id SAME_MACHINE_ID --days 365
   ```
4. **New computer**: Request new Machine ID first, then generate
5. Email new key to customer
6. Customer enters new key in app (activation dialog appears automatically when expired)

**Note:** Since it's offline, no automatic renewal. Customer must manually get new key from you.

---

## 💰 Payment Integration (Optional Future Enhancement)

Currently manual process:
1. Customer pays (Stripe/PayPal/etc.)
2. You receive payment notification
3. Customer emails Machine ID
4. You run generator script with Machine ID
5. You email key

**Future automation options:**
- Payment → Auto-email requesting Machine ID → Customer replies → Auto-generate → Auto-email key
- Self-service portal: Customer enters Machine ID after payment → Instant key generation
- Integration with Gumroad/LemonSqueezy for automated delivery

---

## 🎯 Summary

**What You Do:**
1. Change secret key ONCE before distribution
2. Receive customer Machine ID via email
3. Run generator script with `--machine-id` parameter
4. Email license key to customer

**What Customer Does:**
1. Install MSI
2. Copy Machine ID (one-click button)
3. Email Machine ID to you
4. Receive license key (1-2 hours)
5. Paste key and activate
6. Use app for 1 year
7. Contact you for renewal

**What Happens Automatically:**
✅ License validation (offline)  
✅ Machine ID verification (embedded in key)  
✅ Expiry checking  
✅ Revocation support  
✅ One-click Machine ID copy  

**What You DON'T Need:**
❌ Web server  
❌ Database  
❌ API endpoints  
❌ Ongoing maintenance  
❌ Internet connection (except for initial customer communication)  

---

## 📞 Support

If you have questions about the license system:
- Check `src/utils/license_manager.py` for implementation details
- Check `src/gui/license_dialog.py` for UI flow (Copy button, Machine ID display)
- Check `src/main.py` for startup integration
- Test with: `python generate_license.py test@test.com --machine-id abc123` and activate in app

**System is production-ready with machine-locked licensing!** 🚀

---

## 🔑 IMPORTANT: Generate Your Secret Key

**BEFORE distributing your app**, you MUST change the master secret key in `src/utils/license_manager.py`:

### Step 1: Generate a Secret Key

Run this in PowerShell:
```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Example output:
```
XaB3Kp8Qm9Zr5Yw2Nv7Lj4Hg6Fd1Cs0=-
```

### Step 2: Update license_manager.py

Open `src/utils/license_manager.py` and find this line (around line 22):
```python
MASTER_SECRET = b'YOUR_SECRET_KEY_HERE_CHANGE_THIS_BEFORE_DISTRIBUTION'
```

Replace it with your generated key:
```python
MASTER_SECRET = b'XaB3Kp8Qm9Zr5Yw2Nv7Lj4Hg6Fd1Cs0=-'
```

⚠️ **CRITICAL**: 
- Keep this secret secure - it's used to sign all license keys
- Never share it publicly or commit it to public repos
- If compromised, anyone can generate valid licenses
- If lost, you cannot generate new licenses for existing customers

---

## 📦 How to Generate License Keys

### For Each Customer After Payment:

1. **Run the license generator script:**
   ```powershell
   python generate_license.py customer@email.com
   ```

2. **Output example:**
   ```
   ============================================================
   PowerBI Desktop App - License Key Generator
   ============================================================

   Customer Email: customer@email.com
   License Duration: 365 days (1 year)
   Expiry Date: 2026-12-22

   ============================================================
   LICENSE KEY (send this to customer):
   ============================================================

   PBMT-eyJlbWFpbCI6ImN1c3RvbWVyQGVtYWlsLmNvbSIsImV4cGlyeSI6IjIwMjYtMTItMjJUMTI6MzQ6NTYifQ-a3b5c7d9e2f4
   
   ============================================================

   ✓ License key validated successfully
   ✓ Valid for 365 days
   ```

3. **Email the license key to the customer**

### For 2-Year Licenses:
```powershell
python generate_license.py customer@email.com --days 730
```

### For Custom Duration:
```powershell
python generate_license.py customer@email.com --days 180  # 6 months
```

---

## 👤 Customer Usage Flow

### First Launch (No License):
1. User downloads and installs MSI from Google Drive
2. User launches app
3. **License activation dialog appears automatically**
4. User enters license key received via email
5. User clicks "Activate License"
6. ✅ App activates and stores encrypted license locally
7. App opens normally

### Subsequent Launches:
1. User launches app
2. App checks stored license (offline)
3. If valid → app opens normally
4. If expired → shows activation dialog again

### Expiry Warning:
- If less than 30 days remaining, user sees warning notification
- User can continue using until expiry date
- After expiry, activation dialog appears again

### Moving to New Machine:
1. User clicks license key icon (🔑) in app header
2. User clicks "Revoke License" button
3. Confirms revocation
4. App closes
5. User installs on new machine
6. Enters same license key
7. ✅ Activates on new machine

---

## 🛠️ Technical Details

### License Key Format:
```
PBMT-<base64-payload>-<hmac-signature>

Payload contains:
- Customer email
- Expiry date (ISO format)
- Version number
```

### Security Features:
- ✅ HMAC-SHA256 signature prevents tampering
- ✅ Encrypted local storage using Fernet (AES-128)
- ✅ Machine fingerprint binding (CPU ID, motherboard serial, UUID)
- ✅ Offline validation (no network calls)

### Storage Location:
```
Windows: C:\Users\<username>\.powerbi_toolkit\license.dat
```

### Machine Fingerprint:
The app generates a unique fingerprint using:
1. Windows Machine UUID (from WMI)
2. CPU Processor ID
3. Motherboard Serial Number
4. Fallback to MAC address if above fail

Hashed to 16-character hex string for storage.

---

## 🚨 Troubleshooting

### Customer Reports: "License already activated on another machine"
**Solution:**
1. Ask customer to open app on old machine
2. Click license key icon (🔑) → "Revoke License"
3. OR: You manually tell them the license is revoked
4. They can now activate on new machine

### Customer Lost Access to Old Machine
**Option 1 - Generate New License:**
```powershell
python generate_license.py customer@email.com --days 365
```
Send new key to customer.

**Option 2 - Manual Reset:**
Tell customer to delete this file:
```
C:\Users\<username>\.powerbi_toolkit\license.dat
```
Then activate with original key.

### License Key Not Working
**Check:**
1. ✅ Verify secret key in `license_manager.py` matches what was used to generate
2. ✅ Ensure no extra spaces when customer pastes key
3. ✅ Key format: must start with `PBMT-`
4. ✅ Generate new test key and try yourself

### App Won't Start After Adding License System
**Check:**
1. ✅ `cryptography` package installed: `pip install cryptography`
2. ✅ Check logs: `C:\Users\<username>\AppData\Local\PowerBI Migration Toolkit\logs\app.log`
3. ✅ Test license generation script first

---

## 📋 Pre-Distribution Checklist

Before building and distributing your MSI:

- [ ] **Changed `MASTER_SECRET` in `license_manager.py`**
- [ ] **Backed up secret key in secure location**
- [ ] **Updated contact email in `license_dialog.py` (line 100)**
- [ ] **Tested license generation script**
- [ ] **Generated test license and verified activation works**
- [ ] **Built MSI with PyInstaller/cx-Freeze**
- [ ] **Tested installed MSI shows activation dialog**
- [ ] **Prepared email template for sending licenses**

---

## 📧 Suggested Customer Email Template

```
Subject: Your PowerBI Desktop App License Key

Dear [Customer Name],

Thank you for your purchase! Here is your license key for PowerBI Desktop App:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LICENSE KEY:
PBMT-[generated-key-here]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

INSTALLATION INSTRUCTIONS:
1. Download the installer from: [Google Drive Link]
2. Run the installer and complete setup
3. Launch the application
4. When prompted, enter your license key above
5. Click "Activate License"

Your license is valid for 1 year from today ([Expiry Date]).

IMPORTANT NOTES:
• This license is valid for ONE machine only
• To move to a new computer, use the "Revoke License" option in the app first
• Keep this email safe - you'll need the key if you reinstall

For support, contact: [your-email@example.com]

Best regards,
[Your Name]
```

---

## 🔄 Annual Renewal Process

When customer's license expires:

1. Customer contacts you for renewal
2. Generate new 1-year license:
   ```powershell
   python generate_license.py customer@email.com --days 365
   ```
3. Email new key to customer
4. Customer enters new key in app (activation dialog appears automatically when expired)

**Note:** Since it's offline, no automatic renewal. Customer must manually get new key from you.

---

## 💰 Payment Integration (Optional Future Enhancement)

Currently manual process:
1. Customer pays (Stripe/PayPal/etc.)
2. You receive payment notification
3. You run generator script
4. You email key

**Future automation options:**
- Stripe webhook → auto-generate key → auto-email
- Gumroad/LemonSqueezy (built-in license delivery)
- Self-service portal where customers retrieve keys after payment

---

## 🎯 Summary

**What You Do:**
1. Change secret key ONCE before distribution
2. Run generator script after each sale
3. Email key to customer

**What Customer Does:**
1. Install MSI
2. Enter license key
3. Use app for 1 year
4. Contact you for renewal

**What Happens Automatically:**
✅ License validation (offline)  
✅ Machine binding  
✅ Expiry checking  
✅ Revocation support  

**What You DON'T Need:**
❌ Web server  
❌ Database  
❌ API endpoints  
❌ Ongoing maintenance  
❌ Internet connection  

---

## 📞 Support

If you have questions about the license system:
- Check `src/utils/license_manager.py` for implementation details
- Check `src/gui/license_dialog.py` for UI flow
- Check `src/main.py` for startup integration
- Test with: `python generate_license.py test@test.com` and activate in app

**System is production-ready!** 🚀
