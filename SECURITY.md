# Security Policy

## Supported versions

Lexigram is currently **alpha (0.1.x)**. Only the latest `0.1.x` release line
receives security fixes. APIs and packages may change before 1.0.

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ (latest only) |
| < 0.1   | ❌ |

## Reporting a vulnerability

**Please do not open public GitHub issues for security vulnerabilities.**

Email **security@lexigram.dev** with:

- a description of the issue and its impact,
- affected package(s) and version(s),
- steps to reproduce or a proof of concept, if available,
- a suggested fix, if you have one.

We aim to acknowledge reports within a few business days. As a small team we
cannot commit to a fixed response or fix SLA, but we take security seriously and
will keep you informed of progress. Please allow reasonable time for a fix
before public disclosure. Reporters who wish to be credited will be acknowledged.

## Security practices

- No hardcoded secrets; configuration is read from the environment at runtime.
- Dependencies are pinned and updated as issues are found.
- Import boundaries are enforced (`.importlinter`).
- We follow OWASP Top 10 guidance as a baseline.

## Security checklist for contributors

Before submitting a PR, verify:

- [ ] No hardcoded secrets, API keys, or credentials
- [ ] No sensitive data in logs or error messages
- [ ] Input is validated and sanitized
- [ ] No SQL injection vulnerabilities
- [ ] Authentication/authorization properly implemented
- [ ] No unsafe deserialization
- [ ] No shell command injection risks
- [ ] CORS / rate limiting configured where applicable

## No warranty

Lexigram's open-source packages are provided "as is" under the MIT License
without warranty of any kind. See [`LICENSE`](./LICENSE).
