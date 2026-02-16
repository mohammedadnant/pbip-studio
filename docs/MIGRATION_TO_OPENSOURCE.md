# Migration to Open Source

This document outlines the changes made to transform PBIP Studio into a free, open-source project.

## 🎉 What Changed

PBIP Studio is now **completely free and open-source** under the MIT License, similar to Tabular Editor 2 and DAX Studio.

### Removed Components

1. **License System**
   - ❌ License activation dialog
   - ❌ Machine fingerprinting (WMI)
   - ❌ Cryptography dependencies for licensing
   - ❌ Hardware ID generation
   - ❌ License key validation

2. **Removed Files**
   - `src/utils/license_manager.py` - License management system
   - `src/gui/license_dialog.py` - License activation UI
   - `get_machine_id.py` - Machine ID generation
   - `get_machine_id.ps1` - PowerShell machine ID script
   - `generate_license.py` - License key generator
   - `LICENSE_SYSTEM_SETUP.md` - License setup documentation
   - `GET_MACHINE_ID_README.md` - Machine ID documentation

3. **Updated Files**
   - `src/main.py` - Removed license checks on startup
   - `requirements.txt` - Removed `cryptography` and `WMI` dependencies
   - `setup.py` - Removed license-related packages from build

### Added Components

1. **Open Source Files**
   - ✅ `LICENSE` - MIT License
   - ✅ `README.md` - GitHub-friendly project readme
   - ✅ `CONTRIBUTING.md` - Contribution guidelines
   - ✅ `SECURITY.md` - Security policy
   - ✅ `CHANGELOG.md` - Version history
   - ✅ `.gitignore` - Git ignore patterns

2. **GitHub Integration**
   - ✅ `.github/ISSUE_TEMPLATE/bug_report.yml` - Bug report template
   - ✅ `.github/ISSUE_TEMPLATE/feature_request.yml` - Feature request template
   - ✅ `.github/pull_request_template.md` - PR template

3. **Documentation Reorganization**
   - ✅ `docs/INSTALLATION.md` - Installation guide
   - ✅ `docs/DEVELOPER.md` - Developer guide
   - ✅ `docs/USER_GUIDE.md` - User manual (moved and updated)

## 📦 Installation Changes

### Before (Licensed)
1. Download MSI installer
2. Run installer
3. Launch application
4. **Activate license with machine ID and key**
5. Use application

### After (Open Source)
1. Download MSI installer or ZIP
2. Run installer or extract ZIP
3. Launch application
4. ✅ **Start using immediately - no activation needed!**

## 🔧 Code Changes

### Main Application Entry Point

**Before:**
```python
# Check license after QApplication is created
license_manager = LicenseManager()
license_info = license_manager.get_current_license()

if not license_info.get('valid'):
    # Show license activation dialog
    license_dialog = LicenseDialog(current_license=license_info)
    # ... activation logic ...
```

**After:**
```python
# Start application immediately - no license check
# Create and show main window
window = MainWindow()
window.show()
```

### Dependencies

**Removed:**
```
cryptography>=41.0.0  # For license encryption
WMI>=1.5.1           # For hardware fingerprinting
```

**Kept:**
```
PyQt6>=6.6.0         # GUI framework
fastapi>=0.109.0     # Backend API
pandas>=2.0.0        # Data processing
# ... all other core dependencies
```

## 📚 Documentation Updates

### Removed Sections
- License activation instructions
- Machine ID generation steps
- Support contact for licensing
- Renewal process documentation

### Updated Sections
- Installation guide (simplified)
- Getting started (no activation needed)
- Troubleshooting (removed license errors)

## 🚀 Building from Source

### Before
Required signing and license system setup for distribution.

### After
```powershell
# Simple build process
python setup.py bdist_msi

# Or use PyInstaller
.\build.ps1
```

No code signing required (though recommended for production).

## 🤝 Community Model

### Before
- Proprietary licensing
- Controlled distribution
- Support-based model

### After
- MIT License (permissive)
- Open contribution
- Community-driven development
- GitHub-based collaboration

## 🎯 Next Steps for Users

If you were using a licensed version:

1. **Update Installation**
   - Download the latest open-source release
   - Uninstall the old version (optional)
   - Install the new version
   - Your data and settings are preserved in `%LOCALAPPDATA%\PBIP Studio\`

2. **No Migration Needed**
   - Database format is unchanged
   - Configuration files are compatible
   - All features remain the same

3. **Contribute Back**
   - Report bugs on GitHub
   - Suggest features
   - Submit pull requests
   - Help other users

## 📖 For Developers

### Contributing

The project now welcomes contributions:
- Bug fixes
- New features
- Documentation improvements
- Performance optimizations

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

### Building

Follow [DEVELOPER.md](DEVELOPER.md) for development setup.

### Testing

All functionality remains the same, but license-related tests have been removed.

## 🔄 Version History

- **v1.0.0 (Licensed)** - Initial release with license system
- **v1.0.0 (Open Source)** - Open-source release, license system removed

## ❓ FAQ

**Q: Will the licensed version continue to work?**  
A: Yes, if you have an active license. However, we recommend upgrading to the open-source version.

**Q: Are there any feature differences?**  
A: No, all features are identical. Only the license system was removed.

**Q: Can I still get support?**  
A: Yes! Use GitHub Issues for bug reports and GitHub Discussions for questions.

**Q: Is this really free forever?**  
A: Yes! MIT License means it's free and open-source forever.

**Q: Why open source?**  
A: To align with other Power BI community tools (Tabular Editor 2, DAX Studio) and encourage community contributions.

## 📄 License

PBIP Studio is now licensed under the MIT License. See [LICENSE](../LICENSE) for full text.

---

**Welcome to the open-source PBIP Studio community! 🎉**
