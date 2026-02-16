# Files to Remove or Archive

This document lists files that should be removed or moved to an archive folder as part of the open-source migration.

## 🗑️ Files to Delete

### License System Files
These files are no longer needed:
- [ ] `src/utils/license_manager.py` - License management system
- [ ] `src/gui/license_dialog.py` - License activation dialog
- [ ] `get_machine_id.py` - Machine ID generation script
- [ ] `get_machine_id.ps1` - PowerShell machine ID script
- [ ] `generate_license.py` - License key generator
- [ ] `GET_MACHINE_ID_README.md` - Machine ID documentation
- [ ] `LICENSE_SYSTEM_SETUP.md` - License setup documentation

### Deprecated Documentation
- [ ] `QUICK_FIX_SMARTSCREEN.md` - Obsolete SmartScreen guide
- [ ] `SMARTSCREEN_SOLUTION_GUIDE.md` - Duplicate SmartScreen info
- [ ] `INSTALLATION_GUIDE_FOR_USERS.md` - Replaced by `docs/INSTALLATION.md`
- [ ] `readme.txt` - Replaced by `README.md`
- [ ] `README - HOW TO INSTALL.txt` - Replaced by `docs/INSTALLATION.md`
- [ ] `USER_GUIDE.html` - HTML version (can regenerate if needed)

### Build/Certificate Files (if present)
- [ ] `create_self_signed_cert.ps1` - Not needed for open source
- [ ] `sign_installer.ps1` - Optional for community releases
- [ ] Any `.pfx` or certificate files

## 📁 Files to Move to "archive" or "legacy" Folder

### Old Documentation
Move to `archive/docs/`:
- [ ] `COMPLETE_DOCUMENTATION.md` - Contains license info, needs cleanup
- [ ] `MIGRATION_FIX_SUMMARY.md` - Historical reference
- [ ] `THEME_SYSTEM_GUIDE.md` - Could be useful, review and update

### Build Scripts (Keep but Review)
These might still be useful but need updating:
- [ ] `build_log.txt` - Example build output  
- [ ] `package_for_distribution.ps1` - May need updates

### Old Implementations (Already in Others Old/)
These are already archived:
- ✅ `Others Old/` folder - Keep as historical reference

## 📄 Files to Keep (Core Project Files)

### Source Code
- ✅ `src/` - All source code (except license files listed above)
- ✅ `requirements.txt` - Updated dependencies
- ✅ `setup.py` - Updated build configuration
- ✅ `build.ps1` - Build script (update if needed)
- ✅ `build_msi.ps1` - MSI build script
- ✅ `start.ps1` - Quick start script

### Configuration
- ✅ `config.md` - Configuration template
- ✅ `.gitignore` - Git ignore patterns
- ✅ `.env.example` - Environment variables example (if created)

### Documentation (Updated)
- ✅ `README.md` - New main readme
- ✅ `LICENSE` - MIT License
- ✅ `CONTRIBUTING.md` - Contribution guidelines
- ✅ `SECURITY.md` - Security policy
- ✅ `CHANGELOG.md` - Version history
- ✅ `docs/` - All new documentation

### Assets
- ✅ `logos/` - Application icons
- ✅ `data/` - Database folder (gitignored content)
- ✅ `pbip-studio.ico` - Application icon

### GitHub Templates
- ✅ `.github/` - All GitHub templates and workflows

## 🔄 Actions Required

### Step 1: Backup
```powershell
# Create backup of entire project
Copy-Item -Path "." -Destination "../PBIP-Studio-Backup-$(Get-Date -Format 'yyyy-MM-dd')" -Recurse -Exclude ".git","venv","build","dist"
```

### Step 2: Remove License System Files
```powershell
# Remove license-related code files
Remove-Item "src/utils/license_manager.py" -Force
Remove-Item "src/gui/license_dialog.py" -Force
Remove-Item "get_machine_id.py" -Force -ErrorAction SilentlyContinue
Remove-Item "get_machine_id.ps1" -Force -ErrorAction SilentlyContinue
Remove-Item "generate_license.py" -Force -ErrorAction SilentlyContinue
Remove-Item "GET_MACHINE_ID_README.md" -Force -ErrorAction SilentlyContinue
Remove-Item "LICENSE_SYSTEM_SETUP.md" -Force -ErrorAction SilentlyContinue
```

### Step 3: Archive Old Documentation
```powershell
# Create archive folder
New-Item -Path "archive" -ItemType Directory -Force
New-Item -Path "archive/docs" -ItemType Directory -Force

# Move old documentation
Move-Item "QUICK_FIX_SMARTSCREEN.md" "archive/docs/" -Force -ErrorAction SilentlyContinue
Move-Item "SMARTSCREEN_SOLUTION_GUIDE.md" "archive/docs/" -Force -ErrorAction SilentlyContinue
Move-Item "INSTALLATION_GUIDE_FOR_USERS.md" "archive/docs/" -Force -ErrorAction SilentlyContinue
Move-Item "readme.txt" "archive/docs/" -Force -ErrorAction SilentlyContinue
Move-Item "README - HOW TO INSTALL.txt" "archive/docs/" -Force -ErrorAction SilentlyContinue
Move-Item "USER_GUIDE.html" "archive/docs/" -Force -ErrorAction SilentlyContinue
Move-Item "COMPLETE_DOCUMENTATION.md" "archive/docs/" -Force -ErrorAction SilentlyContinue
Move-Item "MIGRATION_FIX_SUMMARY.md" "archive/docs/" -Force -ErrorAction SilentlyContinue
```

### Step 4: Update Imports
Check for any imports of removed modules:
```powershell
# Search for license imports in code
Get-ChildItem -Path "src" -Recurse -Filter "*.py" | Select-String "license_manager|license_dialog|LicenseManager|LicenseDialog"
```

### Step 5: Test
```powershell
# Test that application still runs
python src/main.py
```

## ✅ Verification Checklist

After cleanup, verify:
- [ ] Application starts without errors
- [ ] No import errors for removed modules
- [ ] All features work (Assessment, Download, Migration, Rename, Upload)
- [ ] Build process works: `python setup.py bdist_msi`
- [ ] Documentation links work
- [ ] README.md displays correctly on GitHub

## 📝 Notes

- Keep `Others Old/` folder as historical reference
- The `Downloads/` folder should be gitignored (contains large Fabric exports)
- The `build/` folder is temporary (build outputs)
- Consider keeping certificate scripts in `archive/` for future reference

## 🎯 Final Project Structure (After Cleanup)

```
pbip-studio/
├── .github/              # GitHub templates
├── .gitignore
├── archive/              # Archived legacy files
│   └── docs/            # Old documentation
├── build/               # Build outputs (gitignored)
├── data/                # Database (gitignored)
├── docs/                # Current documentation
│   ├── INSTALLATION.md
│   ├── USER_GUIDE.md
│   ├── DEVELOPER.md
│   └── MIGRATION_TO_OPENSOURCE.md
├── logos/               # Icons and images
├── Others Old/          # Legacy code (kept for reference)
├── src/                 # Source code
│   ├── api/
│   ├── database/
│   ├── gui/
│   ├── models/
│   ├── parsers/
│   ├── services/
│   ├── utils/
│   └── main.py
├── build.ps1
├── build_msi.ps1
├── CHANGELOG.md
├── config.md
├── CONTRIBUTING.md
├── LICENSE
├── pbip-studio.ico
├── README.md
├── requirements.txt
├── SECURITY.md
├── setup.py
└── start.ps1
```
