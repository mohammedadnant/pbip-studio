# Changelog

All notable changes to PBIP Studio will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.1] - 2026-03-16

### Added
- New transformation option: `lowercase_to_pascal` for improved naming conventions
- PostgreSQL schema detection in PowerBIParser
- Enhanced connection info preview (excludes schema for clarity)
- Detailed debug logging for table renaming operations

### Improved
- Data source migration logic with PostgreSQL schema support
- Table renaming with accurate M query schema updates
- User feedback during table loading and renaming processes
- Schema-only changes without requiring prefix/suffix transformations

### Changed
- Refactored table rename logic for better traceability
- Enhanced data source migration to handle PostgreSQL connections

## [1.0.0] - 2026-02-16

### Added
- Initial public release
- PBIP/TMDL file parsing and analysis
- Semantic model indexing
- Microsoft Fabric workspace download
- Data source migration capabilities
- Bulk table renaming with DAX updates
- Column renaming with reference updates
- Fabric workspace upload
- Local SQLite metadata database
- PyQt6 desktop GUI
- FastAPI REST API backend
- Azure AD authentication support
- Theme support (light/dark)
- User guide and documentation

### Core Features
- **Assessment Tab**: Index and analyze Power BI exports
- **Download Tab**: Download workspaces from Microsoft Fabric
- **Data Source Migration**: Transform connections between platforms
- **Table Rename**: Bulk rename with automatic DAX updates
- **Column Rename**: Smart column renaming with reference tracking
- **Upload Tab**: Deploy changes back to Fabric
- **Configuration**: Azure credentials and app settings

### Technical Stack
- Python 3.10+
- PyQt6 for GUI
- FastAPI for backend API
- SQLite for local database
- TMDL/PBIR custom parsers

---

## Release Notes Format

### Added
- New features

### Changed
- Changes in existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security updates
