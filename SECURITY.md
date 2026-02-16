# Security Policy

## Supported Versions

We release patches for security vulnerabilities in the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of PBIP Studio seriously. If you discover a security vulnerability, please follow these steps:

### Where to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via:
- **Email**: security@pbipstudio.org (if available)
- **Private Security Advisory**: Use GitHub's [private vulnerability reporting](../../security/advisories/new)

### What to Include

When reporting a vulnerability, please include:

1. **Description**: A clear description of the vulnerability
2. **Impact**: What the vulnerability could allow an attacker to do
3. **Reproduction Steps**: Detailed steps to reproduce the vulnerability
4. **Proof of Concept**: If applicable, include a PoC
5. **Affected Versions**: Which versions are affected
6. **Suggested Fix**: If you have ideas for how to fix it

### What to Expect

- **Acknowledgment**: We'll acknowledge receipt within 48 hours
- **Updates**: We'll send updates on our progress every 5-7 days
- **Timeline**: We aim to release security patches within 30 days
- **Credit**: We'll credit you in the release notes (unless you prefer to remain anonymous)

## Security Best Practices for Users

When using PBIP Studio:

1. **Keep Updated**: Always use the latest version
2. **Azure Credentials**: Store Azure credentials securely (use environment variables, not hardcoded)
3. **Local Data**: Be aware that data is stored locally at `%LOCALAPPDATA%\PBIP Studio\`
4. **Network**: The application only makes network calls to Microsoft Fabric APIs (when configured)
5. **Permissions**: Run with standard user permissions (admin not required)

## Known Security Considerations

- **Local Storage**: All data is stored locally on your machine
- **Azure AD**: Uses standard Azure AD Service Principal authentication
- **No Telemetry**: No usage data is collected or sent to external servers
- **Open Source**: All code is publicly available for security review

## Security Updates

Security updates will be released as:
- Patch versions (e.g., 1.0.1)
- Clearly marked as security releases in release notes
- Distributed through GitHub Releases

## Disclosure Policy

- We follow **responsible disclosure** principles
- Security advisories will be published after patches are available
- We'll credit security researchers who report vulnerabilities (with permission)

Thank you for helping keep PBIP Studio secure!
