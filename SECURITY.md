# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability within MACS, please follow these steps:

### 1. Do Not Report via Public GitHub Issues

Public issues are visible to everyone. Security vulnerabilities should be reported privately to give maintainers time to fix the issue before public disclosure.

### 2. Report Privately

Send a private report to the maintainers:

- **Email**: (add your contact email)
- **GitHub Private Advisory**: [Report via GitHub Security Advisories](https://github.com/blank5this/MACS/security/advisories/new)

### 3. What to Include

Please include the following in your report:

- Type of vulnerability (XSS, injection, data exposure, etc.)
- Full paths of source file(s) related to the vulnerability
- Location of the affected source code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact assessment — how this vulnerability could be exploited

### 4. Response Timeline

- **Initial Response**: Within 48 hours, we will acknowledge receipt and provide a timeline for fix
- **Status Update**: Within 7 days, we will provide an estimated fix date
- **Public Disclosure**: After the fix is released, we will credit reporters (unless anonymous) and publish a security advisory

### 5. Scope

This policy covers:

- Data exfiltration or unauthorized access
- Code injection or remote code execution
- Authentication/authorization bypasses
- Sensitive data exposure (API keys, user data)
- Denial of service vulnerabilities

### 6. Out of Scope

- Social engineering attacks
- Physical security issues
- Denial of service that requires unrealistic conditions
- Issues related to user's own infrastructure (e.g., unencrypted traffic within user's private network)

---

## Security Best Practices for Deployments

When deploying MACS in production:

1. **API Keys**: Never commit API keys to version control. Use environment variables.
2. **Network**: Use TLS for all external communications.
3. **Monitoring**: Enable OpenTelemetry export to monitor agent behavior in production.
4. **Isolation**: Run agents with minimal required permissions.
5. **Updates**: Keep dependencies updated — especially `pydantic` and `loguru`.

## Dependencies

We use [Dependabot](https://docs.github.com/en/code-security/dependabot) to monitor and update vulnerable dependencies. Security updates are automatically applied when critical CVEs are detected.
