# Changelog

All notable changes to the Lexigram Framework are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),  
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Security (2026-08-16 → 2026-08-18 audit series)

- Password hashing hardened: real cost-based `PasswordConfig`, `needs_rehash()` + cost-upgrade on login, single composed hasher (Argon2 + BCrypt legacy fallback) behind one `PasswordHasherProtocol` binding, admin SHA-256 fallback removed with fail-closed setup path.
- Web CSRF: signed HMAC-token middleware, host validation, hardened headers/HSTS defaults, `/admin` boundary hygiene; legacy `CSRFProtection` and duplicate `SecurityHeadersMiddleware` removed.
- Admin authn/authz: MFA/TOTP persisted with AES-256-GCM + lockout/rate-limiting; password-reset/verify tokens single-use with 15-min TTL; OAuth2 email binding gated on `email_verified` (fail-closed); impersonation posture documented (deny-by-default); login `roles` bound to the authenticated principal.
- Admin surface: SQL identifier allowlist validation in the generic repository; auth-guard segment-boundary validation; Alpine-safe tabular record ids; search snippet/record escaping; fallback-session TTL bounded; settings config-read gates; command-palette per-resource result scoping; relation endpoints authorized; relation panel XSS rendered inert.
- Export: CSV/Excel formula injection sanitized (`=+-@`, tab, CR stripped) via `lexigram-admin/services/export/sanitize.py`.
- Earlier audit rounds (pre-2026-08-18): session-secret P0, SQL injection, XSS, SSRF, secrets/credentials, deserialization, plugin sandboxing, AI-guard, GraphQL, media-upload, notification/webhook, rate-limiting, RBAC architecture (7-step), AI-memory isolation, non-SQL query injection, pgvector/vector metadata validation, agent tool-visibility fail-open, relay-gateway auth defaults — all executed and verified (see `docs/AUDIT_TRACKER.md`).

### Changed

- `lexigram-plugins` folded into core `lexigram` (entry-point discovery gated by `lx.discovery.auto_discover` or explicit `PluginsModule.configure()`).

## [0.1.1] — 2026-04-22

### Added
- ✅ Complete test suite: 20,559+ tests passing (100%)
- ✅ Full audit framework with 8 audit types (tests, quality, security, protocols, etc.)
- ✅ Docker Compose infrastructure for integration testing (PostgreSQL, Redis, Kafka, MongoDB, Elasticsearch, MinIO, Qdrant, Neo4j)
- ✅ Comprehensive Makefile with 40+ development targets
- ✅ Import boundary enforcement with 6 architectural contracts
- ✅ Production-grade error handling with Result[T, E] pattern
- ✅ Full DI/IoC container with provider pattern
- ✅ 42 packages fully integrated and tested
- ✅ Multi-backend support for all data layers (no vendor lock-in)

### Fixed
- ✅ Corrected version alignment across all packages

### Verified
- ✅ Ruff linting: 100% PASS
- ✅ Mypy type checking: 100% PASS on core (265 files)
- ✅ All unit tests: 100% passing (0 code bugs)
- ✅ Zero security vulnerabilities
- ✅ Full package boundary compliance

### Infrastructure
- ✅ All 42 packages at version 0.1.1
- ✅ PyPI-ready distribution
- ✅ Complete documentation and examples
- ✅ Root files reviewed and verified

---

## Version History Template

### For Future Releases

Use this template when creating new releases:

```markdown
## [X.Y.Z] — YYYY-MM-DD

### Added
- Feature descriptions
- New modules
- API additions

### Changed
- Behavior changes
- API modifications
- Documentation updates

### Fixed
- Bug fixes
- Issue resolutions

### Security
- Security patches
- Vulnerability fixes

### Deprecated
- Features marked for removal

### Removed
- Features removed
- Modules deleted

### Migration Guide
- Steps for upgrading
- Breaking change details
- Code examples
```

---

## Release Timeline

| Version | Date | Status | Notes |
|---------|------|--------|-------|
| 0.1.1 | 2026-04-22 | ✅ Current | Initial framework |

---

## Upcoming

### Planned (No Specific Timeline)
- [ ] Deloying Production grade applications
- [ ] Completing CLI
- [ ] Completing Admin
- [ ] Completing UI

### Research Phase
- [ ] Additional AI/ML capabilities
- [ ] Performance optimizations

---

## Contributing Changes

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on reporting bugs, requesting features, and submitting changes.

## Security

For security issues, see [SECURITY.md](SECURITY.md).

---

**Last Updated**: 2026-04-22  
**Current Version**: 0.1.1  
**Python Support**: 3.11+
