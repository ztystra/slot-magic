# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest  | ✅ |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **DO NOT** open a public issue
2. Email: [create a GitHub Security Advisory](https://github.com/ztystra/slot-magic/security/advisories/new)
3. Include: description, steps to reproduce, potential impact

## Response Timeline

- **Acknowledgment:** ≤ 7 days
- **Initial assessment:** ≤ 14 days
- **Fix or mitigation:** ≤ 30 days

## Scope

**In scope:**
- Authentication/authorization bypass
- Remote code execution
- Data exposure
- API key leaks

**Out of scope:**
- Denial of service
- Social engineering
- Issues in dependencies (report upstream)

## Best Practices

- Never commit `.env` files
- Use environment variables for secrets
- Rotate API keys regularly
- Enable GitHub secret scanning
