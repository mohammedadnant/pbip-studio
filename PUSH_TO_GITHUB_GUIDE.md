# 🚀 Push to GitHub - Step-by-Step Guide

Follow these exact steps to publish your project to GitHub.

## ✅ Prerequisites

1. **GitHub Account** - Create one at https://github.com/signup (if you don't have one)
2. **Git Installed** - Check by running: `git --version`
   - If not installed, download from: https://git-scm.com/download/win

---

## 📝 Step 1: Create GitHub Repository

### Option A: Using GitHub Website (Easiest)

1. **Go to GitHub** and sign in: https://github.com

2. **Click the "+" button** (top right) → "New repository"

3. **Fill in the details:**
   ```
   Repository name: pbip-studio
   Description: Free and open-source Power BI development toolkit for PBIP/TMDL files
   
   ☑️ Public
   ☐ Add a README file (we already have one)
   ☐ Add .gitignore (we already have one)
   ☐ Choose a license (we already have MIT license)
   ```

4. **Click "Create repository"**

5. **Copy the repository URL** (you'll see it on the next page):
   ```
   https://github.com/YOUR-USERNAME/pbip-studio.git
   ```

---

## 💻 Step 2: Initialize and Push from PowerShell

### Open PowerShell in your project folder:

Your current directory should be:
```
C:\Users\moham\Documents\Adnan Github Community\PowerBI-Desktop-App
```

### Run these commands one by one:

#### 1. Configure Git (First time only)
```powershell
# Set your name (will appear in commits)
git config --global user.name "Your Name"

# Set your email (use your GitHub email)
git config --global user.email "your.email@example.com"
```

#### 2. Initialize Git Repository
```powershell
# Initialize git in your project
git init

# Check status (see what files will be added)
git status
```

#### 3. Add Files to Git
```powershell
# Add all files (respects .gitignore)
git add .

# Verify what was added
git status
```

#### 4. Create First Commit
```powershell
# Commit with message
git commit -m "Initial open-source release - PBIP Studio v1.0.0"
```

#### 5. Set Main Branch
```powershell
# Rename branch to 'main' (GitHub standard)
git branch -M main
```

#### 6. Connect to GitHub
```powershell
# Add remote (replace YOUR-USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR-USERNAME/pbip-studio.git

# Verify remote was added
git remote -v
```

#### 7. Push to GitHub
```powershell
# Push code to GitHub
git push -u origin main
```

You'll be prompted for credentials:
- **Username**: Your GitHub username
- **Password**: Use a **Personal Access Token** (not your password)

---

## 🔑 Step 3: Create Personal Access Token (If Needed)

If you get authentication error, you need a token:

1. **Go to GitHub** → Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Direct link: https://github.com/settings/tokens

2. **Click "Generate new token" → "Generate new token (classic)"**

3. **Configure token:**
   ```
   Note: PBIP Studio - Git Push
   Expiration: 90 days (or custom)
   
   Select scopes:
   ☑️ repo (Full control of private repositories)
   ```

4. **Click "Generate token"**

5. **COPY THE TOKEN** (you won't see it again!)

6. **Use token as password** when pushing to GitHub

---

## 🎯 Alternative: GitHub Desktop (GUI Method)

If you prefer a graphical interface:

1. **Download GitHub Desktop**: https://desktop.github.com/

2. **Install and sign in** to your GitHub account

3. **Add local repository:**
   - File → Add Local Repository
   - Choose: `C:\Users\moham\Documents\Adnan Github Community\PowerBI-Desktop-App`

4. **Publish repository:**
   - Click "Publish repository"
   - Name: `pbip-studio`
   - Description: Free and open-source Power BI development toolkit
   - ☐ Keep this code private
   - Click "Publish Repository"

**Done!** Your code is now on GitHub.

---

## ⚙️ Step 4: Configure Repository Settings

After pushing, configure your repository on GitHub:

### 1. Go to your repository page:
```
https://github.com/YOUR-USERNAME/pbip-studio
```

### 2. About Section (top right):
Click ⚙️ (gear icon) next to "About":
```
Description: Free and open-source Power BI development toolkit for PBIP/TMDL files
Website: (leave blank for now)
Topics: powerbi, fabric, pbip, tmdl, windows, desktop-app, python, pyqt6, data-engineering
☑️ Releases
☑️ Packages
```

### 3. Settings → General:
```
Features:
☑️ Issues
☑️ Discussions (recommended - for Q&A)
☐ Projects
☐ Wiki (you have docs/ folder)
☑️ Preserve this repository (optional)

Pull Requests:
☑️ Allow merge commits
☑️ Allow squash merging
☑️ Allow rebase merging
☑️ Always suggest updating pull request branches
☑️ Automatically delete head branches
```

### 4. Settings → Branches:
Click "Add rule":
```
Branch name pattern: main

Protect matching branches:
☑️ Require a pull request before merging
  ☑️ Require approvals (1)
☐ Require status checks to pass before merging
☐ Require conversation resolution before merging
☑️ Require linear history
☐ Include administrators (recommended to leave off for solo projects)
```

### 5. Enable Issue Templates:
Your templates are already in `.github/ISSUE_TEMPLATE/`
They'll appear automatically when users create issues.

---

## ✅ Step 5: Create First Release

1. **Go to your repository** → Releases → "Create a new release"

2. **Choose a tag:**
   - Click "Choose a tag"
   - Type: `v1.0.0`
   - Click "Create new tag: v1.0.0 on publish"

3. **Fill in release details:**
   ```
   Release title: PBIP Studio v1.0.0 - Initial Open Source Release
   
   Description: Copy from CHANGELOG.md (sections for v1.0.0)
   ```

4. **Attach binaries (if you have MSI built):**
   - Click "Attach binaries by dropping them here"
   - Upload: `PBIP-Studio-1.0.0-win64.msi`

5. **Publish:**
   - ☑️ Set as the latest release
   - Click "Publish release"

---

## 🎊 You're Done!

Your project is now public on GitHub at:
```
https://github.com/YOUR-USERNAME/pbip-studio
```

### Share your project:
- Copy the URL and share it
- Others can now:
  - ⭐ Star your repository
  - 👁️ Watch for updates
  - 🍴 Fork to contribute
  - 🐛 Report issues
  - 💬 Start discussions

---

## 🔄 Future Updates

When you make changes:

```powershell
# Add changed files
git add .

# Commit changes
git commit -m "Description of what changed"

# Push to GitHub
git push
```

---

## ❓ Troubleshooting

### "Permission denied" error:
- Use Personal Access Token instead of password
- Or use GitHub Desktop

### "Repository already exists":
- Skip "Create repository" on GitHub
- Use existing repository URL

### "Failed to push":
- Check your internet connection
- Verify repository URL: `git remote -v`
- Try: `git pull origin main --rebase` then `git push`

### Can't find .gitignore:
```powershell
# Show hidden files
Get-ChildItem -Force | Where-Object { $_.Name -like ".*" }
```

---

## 📞 Need Help?

If you encounter issues:
1. Check the error message carefully
2. Google the exact error message
3. Ask on GitHub Discussions (after repo is created)
4. Share the error here and I can help troubleshoot

---

## 🎯 Quick Reference Commands

```powershell
# Initialize
git init
git add .
git commit -m "Initial commit"
git branch -M main

# Connect to GitHub (replace YOUR-USERNAME)
git remote add origin https://github.com/YOUR-USERNAME/pbip-studio.git

# Push
git push -u origin main

# Future updates
git add .
git commit -m "Update description"
git push
```

---

**You've got this! 🚀**

The steps are straightforward - just follow them one by one. Let me know if you hit any issues!
