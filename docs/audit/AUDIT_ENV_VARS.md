# AUDIT_ENV_VARS.md — Lexigram Framework Environment Variables

> **Source**: Extracted from `config.py` root settings classes and known non-config env reads.

---

## Summary

- Packages scanned: 1
- Documented env var entries: 2255
- Unique env var names: 1806
- Duplicate env var names: 207
- Intentional non-config env sources: 3

## Duplicate Analysis

| Env Var | Occurrences |
|---------|-------------|
| `LEX_ADMIN__BACKEND` | 2 |
| `LEX_ADMIN__BACKENDS` | 6 |
| `LEX_ADMIN__CACHE_TTL` | 2 |
| `LEX_ADMIN__COLLECTION_NAME` | 2 |
| `LEX_ADMIN__DEBUG` | 5 |
| `LEX_ADMIN__EMBEDDING_MODEL` | 2 |
| `LEX_ADMIN__ENABLED` | 19 |
| `LEX_ADMIN__ENABLE_SSE` | 2 |
| `LEX_ADMIN__ENV` | 6 |
| `LEX_ADMIN__ENVIRONMENT` | 2 |
| `LEX_ADMIN__MAX_RETRIES` | 2 |
| `LEX_ADMIN__METRICS__ENABLED` | 2 |
| `LEX_ADMIN__METRICS__HISTOGRAM_BUCKETS` | 2 |
| `LEX_ADMIN__MONGODB__MAX_POOL_SIZE` | 2 |
| `LEX_ADMIN__NAME` | 10 |
| `LEX_ADMIN__PATH` | 2 |
| `LEX_ADMIN__RATE_LIMIT__ENABLED` | 2 |
| `LEX_ADMIN__RETRY` | 2 |
| `LEX_ADMIN__RETRY_DELAY` | 2 |
| `LEX_ADMIN__TENANCY__ENABLED` | 4 |
| `LEX_ADMIN__TRACING__ENABLED` | 2 |
| `LEX_ADMIN__TRACING__SAMPLE_RATE` | 2 |
| `LEX_ADMIN__TRACING__SERVICE_NAME` | 2 |
| `LEX_AUTH__ADMIN_EMAIL` | 3 |
| `LEX_AUTH__ADMIN_PASSWORD` | 3 |
| `LEX_AUTH__ENABLED` | 3 |
| `LEX_AUTH__LOGIN_RATE_LIMIT` | 3 |
| `LEX_AUTH__MAX_SESSIONS_PER_USER` | 3 |
| `LEX_AUTH__MIDDLEWARE__BACKEND` | 3 |
| `LEX_AUTH__MIDDLEWARE__EXCLUDE_PATHS` | 3 |
| `LEX_AUTH__MIDDLEWARE__EXCLUDE_PREFIXES` | 3 |
| `LEX_AUTH__MIDDLEWARE__HEADER_NAME` | 3 |
| `LEX_AUTH__MIDDLEWARE__LOGIN_RATE_LIMIT` | 3 |
| `LEX_AUTH__MIDDLEWARE__LOGIN_URL` | 3 |
| `LEX_AUTH__MIDDLEWARE__OPTIONAL_AUTH` | 3 |
| `LEX_AUTH__MIDDLEWARE__PERMISSIONS_REQUIRED` | 3 |
| `LEX_AUTH__MIDDLEWARE__ROLES_REQUIRED` | 3 |
| `LEX_AUTH__MIDDLEWARE__SCHEME` | 3 |
| `LEX_AUTH__NAME` | 3 |
| `LEX_AUTH__OAUTH2_PROVIDERS` | 3 |
| `LEX_AUTH__PASSWORD__ARGON2_MEMORY_COST` | 3 |
| `LEX_AUTH__PASSWORD__ARGON2_PARALLELISM` | 3 |
| `LEX_AUTH__PASSWORD__ARGON2_TIME_COST` | 3 |
| `LEX_AUTH__PASSWORD__BANNED_PATTERNS` | 3 |
| `LEX_AUTH__PASSWORD__BCRYPT_ROUNDS` | 3 |
| `LEX_AUTH__PASSWORD__MAX_LENGTH` | 3 |
| `LEX_AUTH__PASSWORD__MIN_LENGTH` | 3 |
| `LEX_AUTH__PASSWORD__REQUIRE_DIGITS` | 3 |
| `LEX_AUTH__PASSWORD__REQUIRE_LOWERCASE` | 3 |
| `LEX_AUTH__PASSWORD__REQUIRE_SPECIAL` | 3 |
| `LEX_AUTH__PASSWORD__REQUIRE_UPPERCASE` | 3 |
| `LEX_AUTH__RBAC__CACHE_PERMISSIONS` | 3 |
| `LEX_AUTH__RBAC__DEFAULT_ROLE` | 3 |
| `LEX_AUTH__RBAC__ENABLED` | 3 |
| `LEX_AUTH__RBAC__PERMISSION_CACHE_TTL` | 3 |
| `LEX_AUTH__RBAC__SUPERUSER_BYPASS` | 3 |
| `LEX_AUTH__RELAY_VERIFICATION` | 3 |
| `LEX_AUTH__ROLES` | 3 |
| `LEX_AUTH__SECRET_KEY` | 3 |
| `LEX_AUTH__TOKEN__ACCESS_TOKEN_EXPIRE` | 3 |
| `LEX_AUTH__TOKEN__ALGORITHM` | 3 |
| `LEX_AUTH__TOKEN__ALLOW_UNVERIFIED_DEV` | 2 |
| `LEX_AUTH__TOKEN__ID_TOKEN_EXPIRE` | 3 |
| `LEX_AUTH__TOKEN__KEY_ROTATION_GRACE_PERIOD` | 3 |
| `LEX_AUTH__TOKEN__REFRESH_TOKEN_EXPIRE` | 3 |
| `LEX_AUTH__TOKEN__REQUIRED_AUDIENCE` | 3 |
| `LEX_AUTH__TOKEN__SECRET_KEY` | 3 |
| `LEX_AUTH__USERS` | 3 |
| `LEX_CLI__BACKEND` | 2 |
| `LEX_CLI__BACKENDS` | 6 |
| `LEX_CLI__CACHE_TTL` | 2 |
| `LEX_CLI__COLLECTION_NAME` | 2 |
| `LEX_CLI__DEBUG` | 4 |
| `LEX_CLI__EMBEDDING_MODEL` | 2 |
| `LEX_CLI__ENABLED` | 16 |
| `LEX_CLI__ENV` | 6 |
| `LEX_CLI__ENVIRONMENT` | 2 |
| `LEX_CLI__MAX_RETRIES` | 2 |
| `LEX_CLI__METRICS__ENABLED` | 2 |
| `LEX_CLI__METRICS__HISTOGRAM_BUCKETS` | 2 |
| `LEX_CLI__MONGODB__MAX_POOL_SIZE` | 2 |
| `LEX_CLI__NAME` | 8 |
| `LEX_CLI__PATH` | 2 |
| `LEX_CLI__RETRY` | 2 |
| `LEX_CLI__RETRY_DELAY` | 2 |
| `LEX_CLI__TENANCY__ENABLED` | 3 |
| `LEX_CLI__TRACING__ENABLED` | 2 |
| `LEX_CLI__TRACING__SAMPLE_RATE` | 2 |
| `LEX_CLI__TRACING__SERVICE_NAME` | 2 |
| `LEX_FEATURES__CACHE_TTL` | 3 |
| `LEX_FEATURES__DEFAULT_ENABLED` | 3 |
| `LEX_FEATURES__ENABLED` | 3 |
| `LEX_FEATURES__FLAG_ENV_PREFIX` | 3 |
| `LEX_FEATURES__INITIAL_FLAGS` | 3 |
| `LEX_NOTIFICATION__INBOX__MARK_READ_ON_FETCH` | 3 |
| `LEX_NOTIFICATION__INBOX__MAX_PAGE_SIZE` | 3 |
| `LEX_NOTIFICATION__INBOX__RETENTION_DAYS` | 3 |
| `LEX_NOTIFICATION__INBOX__STORE_BACKEND` | 3 |
| `LEX_NOTIFICATION__MAILER__BACKENDS` | 3 |
| `LEX_NOTIFICATION__MAILER__CONSOLE_FALLBACK` | 3 |
| `LEX_RESILIENCE__IDEMPOTENCY__AUTO_CLEANUP` | 3 |
| `LEX_RESILIENCE__IDEMPOTENCY__CLEANUP_INTERVAL` | 3 |
| `LEX_RESILIENCE__IDEMPOTENCY__KEY_PREFIX` | 3 |
| `LEX_RESILIENCE__IDEMPOTENCY__MAX_ENTRIES` | 3 |
| `LEX_RESILIENCE__IDEMPOTENCY__MAX_KEY_LENGTH` | 3 |
| `LEX_RESILIENCE__IDEMPOTENCY__TTL` | 3 |
| `LEX_SEARCH__BACKENDS` | 3 |
| `LEX_SEARCH__DATABASE` | 3 |
| `LEX_SEARCH__ELASTICSEARCH__API_KEY` | 3 |
| `LEX_SEARCH__ELASTICSEARCH__HOSTS` | 3 |
| `LEX_SEARCH__ELASTICSEARCH__INDEX_PREFIX` | 3 |
| `LEX_SEARCH__ELASTICSEARCH__NUMBER_OF_REPLICAS` | 3 |
| `LEX_SEARCH__ELASTICSEARCH__NUMBER_OF_SHARDS` | 3 |
| `LEX_SEARCH__ELASTICSEARCH__PASSWORD` | 3 |
| `LEX_SEARCH__ELASTICSEARCH__USERNAME` | 3 |
| `LEX_SEARCH__ELASTICSEARCH__USE_SSL` | 3 |
| `LEX_SEARCH__ELASTICSEARCH__VERIFY_CERTS` | 3 |
| `LEX_SEARCH__ENABLED` | 3 |
| `LEX_SEARCH__MEILISEARCH__API_KEY` | 3 |
| `LEX_SEARCH__MEILISEARCH__DISPLAYED_ATTRIBUTES` | 3 |
| `LEX_SEARCH__MEILISEARCH__FILTERABLE_ATTRIBUTES` | 3 |
| `LEX_SEARCH__MEILISEARCH__MAX_CONNECTIONS` | 3 |
| `LEX_SEARCH__MEILISEARCH__MIN_WORD_SIZE_FOR_TYPOS` | 3 |
| `LEX_SEARCH__MEILISEARCH__RANKING_RULES` | 3 |
| `LEX_SEARCH__MEILISEARCH__SEARCHABLE_ATTRIBUTES` | 3 |
| `LEX_SEARCH__MEILISEARCH__SORTABLE_ATTRIBUTES` | 3 |
| `LEX_SEARCH__MEILISEARCH__TIMEOUT` | 3 |
| `LEX_SEARCH__MEILISEARCH__TYPO_TOLERANCE_ENABLED` | 3 |
| `LEX_SEARCH__MEILISEARCH__URL` | 3 |
| `LEX_SEARCH__MONGO__CONNECTION_STRING` | 3 |
| `LEX_SEARCH__MONGO__DATABASE_NAME` | 3 |
| `LEX_SEARCH__MONGO__USE_ATLAS_SEARCH` | 3 |
| `LEX_SEARCH__MYSQL__CONNECTION_STRING` | 3 |
| `LEX_SEARCH__MYSQL__FULLTEXT_MODE` | 3 |
| `LEX_SEARCH__MYSQL__MIN_WORD_LENGTH` | 3 |
| `LEX_SEARCH__OPENSEARCH__HOSTS` | 3 |
| `LEX_SEARCH__OPENSEARCH__INDEX_PREFIX` | 3 |
| `LEX_SEARCH__OPENSEARCH__PASSWORD` | 3 |
| `LEX_SEARCH__OPENSEARCH__TIMEOUT` | 3 |
| `LEX_SEARCH__OPENSEARCH__USERNAME` | 3 |
| `LEX_SEARCH__OPENSEARCH__USE_SSL` | 3 |
| `LEX_SEARCH__OPENSEARCH__VERIFY_SSL` | 3 |
| `LEX_SEARCH__OPERATIONS__BULK_CHUNK_SIZE` | 3 |
| `LEX_SEARCH__OPERATIONS__MAX_RETRIES` | 3 |
| `LEX_SEARCH__OPERATIONS__REQUEST_TIMEOUT` | 3 |
| `LEX_SEARCH__OPERATIONS__RETRY_BACKOFF` | 3 |
| `LEX_SEARCH__POSTGRES__AUTO_CREATE_TABLES` | 3 |
| `LEX_SEARCH__POSTGRES__CONNECTION_STRING` | 3 |
| `LEX_SEARCH__POSTGRES__ENABLE_TRIGRAM` | 3 |
| `LEX_SEARCH__POSTGRES__TEXT_SEARCH_CONFIG` | 3 |
| `LEX_SEARCH__QUERY__DEFAULT_LIMIT` | 3 |
| `LEX_SEARCH__QUERY__ENABLE_AGGREGATIONS` | 3 |
| `LEX_SEARCH__QUERY__ENABLE_FACETING` | 3 |
| `LEX_SEARCH__QUERY__ENABLE_HIGHLIGHTING` | 3 |
| `LEX_SEARCH__QUERY__FUZZY_THRESHOLD` | 3 |
| `LEX_SEARCH__QUERY__MAX_LIMIT` | 3 |
| `LEX_SEARCH__QUERY__STRATEGY` | 3 |
| `LEX_SEARCH__SQLITE__AUTO_CREATE_TABLES` | 3 |
| `LEX_SEARCH__SQLITE__DB_PATH` | 3 |
| `LEX_SEARCH__SQLITE__TOKENIZER` | 3 |
| `LEX_SEARCH__TIMEOUT` | 3 |
| `LEX_SEARCH__TYPESENSE__API_KEY` | 3 |
| `LEX_SEARCH__TYPESENSE__CONNECTION_TIMEOUT` | 3 |
| `LEX_SEARCH__TYPESENSE__HEALTH_CHECK_INTERVAL` | 3 |
| `LEX_SEARCH__TYPESENSE__NODES` | 3 |
| `LEX_VECTOR__EMBEDDING__API_BASE` | 3 |
| `LEX_VECTOR__EMBEDDING__API_KEY` | 3 |
| `LEX_VECTOR__EMBEDDING__BATCH_SIZE` | 3 |
| `LEX_VECTOR__EMBEDDING__DIMENSION` | 3 |
| `LEX_VECTOR__EMBEDDING__FORMAT` | 3 |
| `LEX_VECTOR__EMBEDDING__MODEL` | 3 |
| `LEX_VECTOR__EMBEDDING__TIMEOUT` | 3 |
| `LEX_WEB__API_DOCS__ENABLED` | 3 |
| `LEX_WEB__API_DOCS__PROVIDER` | 3 |
| `LEX_WEB__AUTH_EXCLUDE_PATHS` | 3 |
| `LEX_WEB__COMPRESSION_ENABLED` | 3 |
| `LEX_WEB__CORS` | 3 |
| `LEX_WEB__DEBUG_ROUTES` | 3 |
| `LEX_WEB__DEBUG_ROUTES_TOKEN` | 3 |
| `LEX_WEB__ENABLED` | 4 |
| `LEX_WEB__ENABLE_AUTH` | 3 |
| `LEX_WEB__ENABLE_DEBUG_ROUTES_ENV_GATE` | 3 |
| `LEX_WEB__ENABLE_IDENTITY_RESOLUTION` | 3 |
| `LEX_WEB__ENV` | 3 |
| `LEX_WEB__MAX_BODY_SIZE` | 3 |
| `LEX_WEB__NAME` | 3 |
| `LEX_WEB__OPENAPI_TITLE` | 3 |
| `LEX_WEB__OPENAPI_URL` | 3 |
| `LEX_WEB__OPENAPI_VERSION` | 3 |
| `LEX_WEB__RATE_LIMIT__DEFAULT_LIMIT` | 3 |
| `LEX_WEB__RATE_LIMIT__DEFAULT_WINDOW` | 3 |
| `LEX_WEB__RATE_LIMIT__ENABLED` | 3 |
| `LEX_WEB__RATE_LIMIT__RULES` | 3 |
| `LEX_WEB__RATE_LIMIT__STORAGE_BACKEND` | 3 |
| `LEX_WEB__RATE_LIMIT__WHITELIST_IPS` | 3 |
| `LEX_WEB__REDOC_JS_URL` | 3 |
| `LEX_WEB__REDOC_URL` | 3 |
| `LEX_WEB__ROLE_GUARD__RULES` | 3 |
| `LEX_WEB__SECURITY` | 3 |
| `LEX_WEB__SERVER__DEBUG` | 3 |
| `LEX_WEB__SERVER__HOST` | 3 |
| `LEX_WEB__SERVER__PORT` | 3 |
| `LEX_WEB__SERVER__RELOAD` | 3 |
| `LEX_WEB__SERVER__WORKERS` | 3 |
| `LEX_WEB__STATIC__DIRECTORY` | 3 |
| `LEX_WEB__STATIC__ENABLED` | 3 |
| `LEX_WEB__STATIC__HTML` | 3 |
| `LEX_WEB__STATIC__PREFIX` | 3 |
| `LEX_WEB__SWAGGER_CSS_URL` | 3 |
| `LEX_WEB__SWAGGER_JS_URL` | 3 |
| `LEX_WEB__SWAGGER_UI_URL` | 3 |
| `LEX_WEB__TEMPLATE_DIRECTORY` | 3 |

## Package Registry

### `lexigram-dev`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_ADMIN__ALIAS_LIMIT__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Alias` |
| `LEX_ADMIN__ALIAS_LIMIT__MAX_ALIASES` | int | (complex) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Alias` |
| `LEX_ADMIN__ALLOWED_HOSTS` | list[str] | (required) | Hostnames permitted to reach the application. Empty by default; must be configured before production deployment. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__ALLOW_UNAUTHENTICATED` | bool | False |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPCon` |
| `LEX_ADMIN__API_PREFIX` | str | "/admin/api" |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminConfig.api_prefix` |
| `LEX_ADMIN__ASYNC_PROCESSING` | bool | True | Process feedback handlers asynchronously in the background | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/feedback/config.py:F` |
| `LEX_ADMIN__AUDIT_ACTOR_ID` | str | (complex) | Actor identifier for audit log entries | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/secrets/config.py:Secre` |
| `LEX_ADMIN__AUDIT_HMAC_KEY` | str  \| None | None | HMAC key for audit checksum signing. Plain text or base64. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseC` |
| `LEX_ADMIN__AUDIT__READ_AUDIT_ENABLED` | bool | False | Log read operations (off by default; compliance mode only). | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminAuditConfig.audit.read_audit_enab` |
| `LEX_ADMIN__AUTH__CSRF_TOKEN_LIFETIME` | int | 3600 | CSRF token expiry in seconds | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.csrf_token_lifeti` |
| `LEX_ADMIN__AUTH__EMAIL_OTP__ENABLED` | bool | True | Enable email OTP factor | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminEmailOtpConfig.auth.email_otp.ena` |
| `LEX_ADMIN__AUTH__EMAIL_OTP__RESEND_COOLDOWN_SECONDS` | int | 60 | Minimum seconds between email OTP sends | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminEmailOtpConfig.auth.email_otp.res` |
| `LEX_ADMIN__AUTH__EMAIL_OTP__TTL_MINUTES` | int | 10 | Code validity window in minutes | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminEmailOtpConfig.auth.email_otp.ttl` |
| `LEX_ADMIN__AUTH__EMAIL_VERIFICATION__ENABLED` | bool | True | Enable email verification flow | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminEmailVerificationConfig.auth.emai` |
| `LEX_ADMIN__AUTH__EMAIL_VERIFICATION__ENFORCEMENT` | bool | True | Block login until the email is verified | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminEmailVerificationConfig.auth.emai` |
| `LEX_ADMIN__AUTH__EMAIL_VERIFICATION__TOKEN_TTL_HOURS` | int | 24 | Verify link validity in hours | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminEmailVerificationConfig.auth.emai` |
| `LEX_ADMIN__AUTH__ENABLED` | bool | True | Enable authentication | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.enabled` |
| `LEX_ADMIN__AUTH__ENV` | Literal['development', 'staging', 'production'] | "development" | Deployment environment for cookie security defaults | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.env` |
| `LEX_ADMIN__AUTH__IDLE_TIMEOUT` | int | 3600 | Session idle timeout in seconds | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.idle_timeout` |
| `LEX_ADMIN__AUTH__LOGIN_URL` | str | "/admin/login" |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.login_url` |
| `LEX_ADMIN__AUTH__LOGOUT_URL` | str | "/admin/logout" |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.logout_url` |
| `LEX_ADMIN__AUTH__MFA__ENABLED` | bool | True | Enable TOTP 2FA | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminMfaConfig.auth.mfa.enabled` |
| `LEX_ADMIN__AUTH__MFA__FACTOR` | str | "totp" | Second factor used at login: 'totp' (authenticator app) or 'email' (one-time code) | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminMfaConfig.auth.mfa.factor` |
| `LEX_ADMIN__AUTH__MFA__ISSUER` | str | "Lexigram Admin" | TOTP issuer label shown in authenticator apps | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminMfaConfig.auth.mfa.issuer` |
| `LEX_ADMIN__AUTH__MFA__SKEW` | int | 1 | Allowed clock skew in 30 second steps | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminMfaConfig.auth.mfa.skew` |
| `LEX_ADMIN__AUTH__OAUTH_ENABLED` | bool | False |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.oauth_enabled` |
| `LEX_ADMIN__AUTH__OAUTH_PROVIDERS` | list[str] | (required) |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.oauth_providers` |
| `LEX_ADMIN__AUTH__PASSWORD_POLICY__MAX_LENGTH` | int | 128 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminPasswordPolicyConfig.auth.passwor` |
| `LEX_ADMIN__AUTH__PASSWORD_POLICY__MIN_LENGTH` | int | 12 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminPasswordPolicyConfig.auth.passwor` |
| `LEX_ADMIN__AUTH__PASSWORD_POLICY__REJECT_COMMON_PASSWORDS` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminPasswordPolicyConfig.auth.passwor` |
| `LEX_ADMIN__AUTH__PASSWORD_POLICY__REJECT_CONTAINING_EMAIL` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminPasswordPolicyConfig.auth.passwor` |
| `LEX_ADMIN__AUTH__PASSWORD_POLICY__REQUIRE_DIGIT` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminPasswordPolicyConfig.auth.passwor` |
| `LEX_ADMIN__AUTH__PASSWORD_POLICY__REQUIRE_LOWERCASE` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminPasswordPolicyConfig.auth.passwor` |
| `LEX_ADMIN__AUTH__PASSWORD_POLICY__REQUIRE_SPECIAL` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminPasswordPolicyConfig.auth.passwor` |
| `LEX_ADMIN__AUTH__PASSWORD_POLICY__REQUIRE_UPPERCASE` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminPasswordPolicyConfig.auth.passwor` |
| `LEX_ADMIN__AUTH__PERMISSION_CACHE_TTL` | int | 300 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.permission_cache_` |
| `LEX_ADMIN__AUTH__PRINCIPAL_SOURCE` | Literal['internal', 'app'] | "internal" |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.principal_source` |
| `LEX_ADMIN__AUTH__REGISTRATION__ALLOWED_EMAIL_DOMAINS` | list[str] | (required) | Restrict registration to these email domains (empty = any) | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminRegistrationConfig.auth.registrat` |
| `LEX_ADMIN__AUTH__REGISTRATION__DEFAULT_ROLE` | str | "admin" | Role granted to new accounts | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminRegistrationConfig.auth.registrat` |
| `LEX_ADMIN__AUTH__REGISTRATION__ENABLED` | bool | False | Allow self-service registration | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminRegistrationConfig.auth.registrat` |
| `LEX_ADMIN__AUTH__ROLES` | dict[str, Any] | (required) |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.roles` |
| `LEX_ADMIN__AUTH__SECURITY__IP_RATE_LIMIT_ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminSecurityConfig.auth.security.ip_r` |
| `LEX_ADMIN__AUTH__SECURITY__IP_RATE_LIMIT_PER_15_MINUTES` | int | 30 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminSecurityConfig.auth.security.ip_r` |
| `LEX_ADMIN__AUTH__SECURITY__IP_RATE_LIMIT_PER_HOUR` | int | 60 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminSecurityConfig.auth.security.ip_r` |
| `LEX_ADMIN__AUTH__SECURITY__IP_RATE_LIMIT_PER_MINUTE` | int | 10 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminSecurityConfig.auth.security.ip_r` |
| `LEX_ADMIN__AUTH__SECURITY__LOCKOUT_THRESHOLDS` | list[tuple[int, int]] | (required) |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminSecurityConfig.auth.security.lock` |
| `LEX_ADMIN__AUTH__SECURITY__PERMANENT_LOCKOUT_THRESHOLD` | int | 50 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminSecurityConfig.auth.security.perm` |
| `LEX_ADMIN__AUTH__SECURITY__SETUP_TOKEN` | str  \| None | None | Optional ADMIN_SETUP_TOKEN — when set, must be provided during first-run setup. | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminSecurityConfig.auth.security.setu` |
| `LEX_ADMIN__AUTH__SECURITY__SETUP_TOKEN_OPTIN_UNSAFE` | bool | False | Explicit escape hatch: boot without a setup token. Only for local/ephemeral environments — leaves the first-run wizard o | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminSecurityConfig.auth.security.setu` |
| `LEX_ADMIN__AUTH__SESSION_LIFETIME` | int | 86400 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.session_lifetime` |
| `LEX_ADMIN__AUTH__SESSION_SECRET` | SecretStr | SecretStr(...) | Session secret for signing | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.session_secret` |
| `LEX_ADMIN__AUTH__USERS` | list[Any] | (required) |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.users` |
| `LEX_ADMIN__AUTO_ESCAPE` | bool | True | HTML-escape user strings by default. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ui/config.py:UIConfig.a` |
| `LEX_ADMIN__BACKEND` | str | (complex) | Graph store backend to use | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:GraphCo` |
| `LEX_ADMIN__BACKEND` | str | (complex) | Vector store backend to use | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Vector` |
| `LEX_ADMIN__BACKENDS` | list[CacheBackendConfig] | (required) | Backend configs | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheCo` |
| `LEX_ADMIN__BACKENDS` | list[NamedDatabaseConfig] | (required) | Multi-database backends list. When non-empty, drives multi-DB mode. The entry with primary=True (or the first entry) als | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseC` |
| `LEX_ADMIN__BACKENDS` | list[NamedNoSQLConfig] | (required) | Named NoSQL backends for multi-store support. When non-empty, the provider registers each backend under Annotated[Docume | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:NoSQLCo` |
| `LEX_ADMIN__BACKENDS` | list[NamedStorageConfig] | (required) | Named storage backends for multi-store support. When non-empty, the provider registers each backend under Annotated[Blob | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/storage/config.py:Stora` |
| `LEX_ADMIN__BACKENDS` | list[NamedTaskConfig] | (required) | Named task queue backends for multi-queue support. When non-empty, the provider registers each backend under Annotated[T | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskCon` |
| `LEX_ADMIN__BACKENDS` | list[NamedVectorConfig] | (required) | Named vector store backends for multi-store support. When non-empty, the provider registers each backend under Annotated | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Vector` |
| `LEX_ADMIN__BACKEND_OPTIONS` | dict | (required) | Keyword arguments for backend constructor | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/secrets/config.py:Secre` |
| `LEX_ADMIN__BACKEND_TYPE` | str | (complex) | Backend store type (memory, vault, ...) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/secrets/config.py:Secre` |
| `LEX_ADMIN__BACKEND__AMQP_URL` | SecretStr | SecretStr(...) | AMQP connection URL (may contain credentials). | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskBac` |
| `LEX_ADMIN__BACKEND__POSTGRES_DSN` | SecretStr  \| None | None | Postgres DSN (required when type="postgres"; may contain credentials). | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskBac` |
| `LEX_ADMIN__BACKEND__QUEUE_NAME` | str | (complex) | Name of the task queue | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskBac` |
| `LEX_ADMIN__BACKEND__REDIS_URL` | SecretStr | SecretStr(...) | Redis connection URL (may contain credentials). | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskBac` |
| `LEX_ADMIN__BACKEND__TYPE` | str | (complex) | Queue backend type | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskBac` |
| `LEX_ADMIN__BACKEND__URL` | SecretStr | Ellipsis | Database connection URL (may contain credentials) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseB` |
| `LEX_ADMIN__BATCH__ENABLED` | bool | False |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Batch` |
| `LEX_ADMIN__BATCH__MAX_BATCH_SIZE` | int | 10 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Batch` |
| `LEX_ADMIN__BULKHEAD__MAX_CONCURRENT` | int | 10 | Max concurrent requests | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Bu` |
| `LEX_ADMIN__BULKHEAD__NAME` | str | "" | Bulkhead name | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Bu` |
| `LEX_ADMIN__BULKHEAD__QUEUE_SIZE` | int | 100 | Max queue size | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Bu` |
| `LEX_ADMIN__BULKHEAD__TIMEOUT` | float | 30.0 | Execution timeout | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Bu` |
| `LEX_ADMIN__BULK_BATCH_SIZE` | int | (complex) | Batch size for bulk operations | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:GraphCo` |
| `LEX_ADMIN__CACHE_TTL` | int | 3600 | Cache TTL in seconds (default: 1 hour) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGCon` |
| `LEX_ADMIN__CACHE_TTL` | int | 86400 | Cache TTL in seconds (default: 24 hours) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Vector` |
| `LEX_ADMIN__CACHE__DEFAULT_MAX_AGE` | Duration  \| int | (complex) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Cache` |
| `LEX_ADMIN__CACHE__DEFAULT_SCOPE` | CacheScope | (complex) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Cache` |
| `LEX_ADMIN__CACHE__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Cache` |
| `LEX_ADMIN__CACHE__VARY_HEADERS` | list[str] | (required) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Cache` |
| `LEX_ADMIN__CHUNKING_STRATEGY` | str | "recursive" | Chunking strategy (recursive, semantic, token) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGCon` |
| `LEX_ADMIN__CHUNK_OVERLAP` | int | 50 | Overlap between consecutive chunks | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGCon` |
| `LEX_ADMIN__CHUNK_SIZE` | int | 512 | Text chunk size in tokens | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGCon` |
| `LEX_ADMIN__CIRCUIT_BREAKER` | CircuitBreakerConfig | field(...) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Re` |
| `LEX_ADMIN__CITATION_STYLE` | str | "inline" | Citation style (inline, footnote, numbered) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGCon` |
| `LEX_ADMIN__CLEANUP_TEMP_FILES` | bool | True | Clean up temporary files after tests | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/testing/config.py:Testi` |
| `LEX_ADMIN__CLIENT_STDIO_COMMAND` | list[str] | field(...) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPCon` |
| `LEX_ADMIN__CLIENT_URL` | str  \| None | None |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPCon` |
| `LEX_ADMIN__CLUSTERS__EXTRA` | list[ClusterSpec] | (required) | Extra clusters beyond the built-in infrastructure cluster | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminClustersConfig.clusters.extra` |
| `LEX_ADMIN__COLLECTION_NAME` | str | "default" | Collection/index name for vector store | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGCon` |
| `LEX_ADMIN__COLLECTION_NAME` | str | "default" | Default collection name for AI-layer operations | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Vector` |
| `LEX_ADMIN__COMMANDS` | list[dict[str, Any]] | (required) |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminConfig.commands` |
| `LEX_ADMIN__COMMAND_BUS__ENABLE_LOGGING` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Comman` |
| `LEX_ADMIN__COMMAND_BUS__ENABLE_METRICS` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Comman` |
| `LEX_ADMIN__COMMAND_BUS__ENABLE_VALIDATION` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Comman` |
| `LEX_ADMIN__COMMAND_BUS__MAX_RETRIES` | int | 3 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Comman` |
| `LEX_ADMIN__COMMAND_BUS__RETRY_DELAY_SECONDS` | float | 1.0 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Comman` |
| `LEX_ADMIN__COMMAND_BUS__TIMEOUT_SECONDS` | float | 30.0 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Comman` |
| `LEX_ADMIN__COMPLEXITY__DEFAULT_FIELD_COST` | float | 1.0 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Compl` |
| `LEX_ADMIN__COMPLEXITY__DEFAULT_LIST_COST` | float | 10.0 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Compl` |
| `LEX_ADMIN__COMPLEXITY__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Compl` |
| `LEX_ADMIN__COMPLEXITY__MAX_COMPLEXITY` | int | (complex) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Compl` |
| `LEX_ADMIN__CONNECTORS__FILESYSTEM__READ_ONLY` | bool | False |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:Filesy` |
| `LEX_ADMIN__CONNECTORS__FILESYSTEM__ROOT_DIR` | str | "" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:Filesy` |
| `LEX_ADMIN__CONNECTORS__GITHUB__API_URL` | str | "https://api.github.com" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:GitHub` |
| `LEX_ADMIN__CONNECTORS__GITHUB__TOKEN` | str | "" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:GitHub` |
| `LEX_ADMIN__CONNECTORS__GOOGLE_DRIVE__IMPERSONATED_EMAIL` | str | "" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:Google` |
| `LEX_ADMIN__CONNECTORS__GOOGLE_DRIVE__SERVICE_ACCOUNT_JSON` | str | "" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:Google` |
| `LEX_ADMIN__CONNECTORS__SLACK__BOT_TOKEN` | str | "" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:SlackC` |
| `LEX_ADMIN__CONNECTORS__SLACK__MAX_MESSAGES` | int | 100 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:SlackC` |
| `LEX_ADMIN__CONNECTORS__SQL__ALLOWED_TABLES` | list[str] | field(...) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:SQLCon` |
| `LEX_ADMIN__CONNECTORS__SQL__DSN` | str | "" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:SQLCon` |
| `LEX_ADMIN__CONNECTORS__SQL__READ_ONLY` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:SQLCon` |
| `LEX_ADMIN__CONNECTORS__WEB_FETCH__ENABLED` | bool | False |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:WebFet` |
| `LEX_ADMIN__CONNECTORS__WEB_FETCH__MAX_CONTENT_BYTES` | int | (complex) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:WebFet` |
| `LEX_ADMIN__CONNECTORS__WEB_FETCH__USER_AGENT` | str | "lexigram-mcp/1.0" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:WebFet` |
| `LEX_ADMIN__CONNECTORS__WEB_SEARCH__API_KEY` | str | "" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:WebSea` |
| `LEX_ADMIN__CONNECTORS__WEB_SEARCH__MAX_RESULTS` | int | 10 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:WebSea` |
| `LEX_ADMIN__CONNECTORS__WEB_SEARCH__PROVIDER` | str | "brave" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:WebSea` |
| `LEX_ADMIN__CONTRIBUTORS` | dict[str, ContributorConfig] | (required) |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminConfig.contributors` |
| `LEX_ADMIN__CONTRIBUTOR_COLLISION_MODE` | Literal['warn', 'error'] | "warn" | How to handle name collisions when multiple contributors register widgets, pages, or routes with the same name. 'warn' ( | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminConfig.contributor_collision_mode` |
| `LEX_ADMIN__CORS_ORIGINS` | list[str] | field(...) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPCon` |
| `LEX_ADMIN__CORS__ALLOWED_ORIGINS` | list[str] | (required) | Allowed origins (use ['*'] to allow all) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CORS__ALLOW_CREDENTIALS` | bool | False |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CORS__ALLOW_HEADERS` | list[str] | (required) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CORS__ALLOW_METHODS` | list[str] | (required) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CORS__ALLOW_ORIGIN_REGEX` | str  \| None | None | Regex pattern for allowed origins (matched when not in allowed_origins) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CORS__DEBUG_PERMISSIVE` | bool | False | When True and debug mode is active, allow any origin via wildcard (explicit opt-in replacement for the old implicit debu | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CORS__ENABLED` | bool | True | Enable CORS | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CORS__EXPOSE_HEADERS` | list[str] | (required) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CORS__MAX_AGE` | int | 600 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CROSS_ORIGIN__EMBEDDER_POLICY` | str | "require-corp" | Cross-Origin-Embedder-Policy header value | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CROSS_ORIGIN__ENABLED` | bool | False | Emit cross-origin isolation headers | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CROSS_ORIGIN__OPENER_POLICY` | str | "same-origin" | Cross-Origin-Opener-Policy header value | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CROSS_ORIGIN__RESOURCE_POLICY` | str | "same-origin" | Cross-Origin-Resource-Policy header value | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CSP__DIRECTIVES` | dict[str, Any] | (required) | CSP directives mapping directive name to source expression(s) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CSP__ENABLED` | bool | True | Emit the Content-Security-Policy header | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CSRF__COOKIE_DOMAIN` | str  \| None | None |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CSRF__COOKIE_HTTPONLY` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CSRF__COOKIE_NAME` | str | "csrf_token" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CSRF__COOKIE_PATH` | str | "/" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CSRF__COOKIE_SAMESITE` | str | "Lax" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CSRF__COOKIE_SECURE` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CSRF__ENABLED` | bool | False |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CSRF__EXCLUDED_PATHS` | list[str] | (required) | URL path prefixes exempt from CSRF validation for cookie-less requests; cookie-bearing requests on these paths are still | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CSRF__EXCLUDE_AUTH_SCHEMES` | list[str] | (required) | Authorization header schemes that bypass CSRF validation (explicit opt-in). | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CSRF__EXCLUDE_CONTENT_TYPES` | list[str] | (required) | Content-Type values that bypass CSRF validation (explicit opt-in — JSON requests are validated by default so cookie-auth | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CSRF__HEADER_NAME` | str | "X-CSRF-Token" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CSRF__SECRET_KEY` | str  \| None | None | HMAC secret used to sign and verify CSRF tokens (populated via LEX_WEB__SECURITY__CSRF__SECRET_KEY) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CSRF__TOKEN_LENGTH` | int | 32 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CSRF__TOKEN_TTL` | int | 3600 | TTL in seconds for synchronizer-mode tokens stored in cache. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__CUSTOM_HEADERS` | dict[str, str] | (required) | Additional HTTP response headers emitted verbatim | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__DASHBOARD_LAYOUT__LAYOUT` | Literal['grid', 'masonry'] | "grid" |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:DashboardLayoutConfig.dashboard_layout` |
| `LEX_ADMIN__DASHBOARD_LAYOUT__MAX_WIDGETS` | int | 20 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:DashboardLayoutConfig.dashboard_layout` |
| `LEX_ADMIN__DASHBOARD_LAYOUT__WIDGET_REFRESH_DEFAULT` | int | 30 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:DashboardLayoutConfig.dashboard_layout` |
| `LEX_ADMIN__DATALOADER__BATCH_DELAY_MS` | float | 2.0 | Delay in milliseconds before executing a DataLoaderProtocol batch. A small non-zero value (2ms) lets more keys accumulat | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:DataL` |
| `LEX_ADMIN__DATALOADER__BATCH_ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:DataL` |
| `LEX_ADMIN__DATALOADER__CACHE_ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:DataL` |
| `LEX_ADMIN__DATALOADER__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:DataL` |
| `LEX_ADMIN__DATALOADER__MAX_BATCH_SIZE` | int | 100 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:DataL` |
| `LEX_ADMIN__DATA__QUERY_TIMEOUT_SECONDS` | int | 5 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminDataConfig.data.query_timeout_sec` |
| `LEX_ADMIN__DB_REUSE` | bool | True | Reuse test databases between tests | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/testing/config.py:Testi` |
| `LEX_ADMIN__DEBUG` | bool | False |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminConfig.debug` |
| `LEX_ADMIN__DEBUG` | bool | (complex) | Debug mode | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheCo` |
| `LEX_ADMIN__DEBUG` | bool | False |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Events` |
| `LEX_ADMIN__DEBUG` | bool | False |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Graph` |
| `LEX_ADMIN__DEBUG` | bool | False | Enable debug mode | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Monit` |
| `LEX_ADMIN__DEBUG_COMPONENTS` | bool | False | Render data-component debug attributes. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ui/config.py:UIConfig.d` |
| `LEX_ADMIN__DEFAULT_DIMENSION` | int | 1536 | Default vector dimension | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Vector` |
| `LEX_ADMIN__DEFAULT_DISTANCE_METRIC` | DistanceMetric | (complex) | Default distance metric for new collections | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Vector` |
| `LEX_ADMIN__DEFAULT_DRIVER` | Literal['local', 's3', 'gcs', 'azure', 'memory', 'r2'] | (complex) | Default storage driver to use | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/storage/config.py:Stora` |
| `LEX_ADMIN__DEFAULT_INDEX_TYPE` | IndexType | (complex) | Default index type for new collections | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Vector` |
| `LEX_ADMIN__DEFAULT_QUERY_LIMIT` | int | (complex) | Default limit for query results | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:GraphCo` |
| `LEX_ADMIN__DEFAULT_THEME` | str | "default" | Default CSS theme name. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ui/config.py:UIConfig.d` |
| `LEX_ADMIN__DEFAULT_TRAVERSAL_MAX_DEPTH` | int | (complex) | Default maximum depth for traversals | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:GraphCo` |
| `LEX_ADMIN__DEPTH_LIMIT__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Depth` |
| `LEX_ADMIN__DEPTH_LIMIT__IGNORE_INTROSPECTION` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Depth` |
| `LEX_ADMIN__DEPTH_LIMIT__MAX_DEPTH` | int | (complex) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Depth` |
| `LEX_ADMIN__DRIVER` | str | "mongodb" | NoSQL driver name | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:NoSQLCo` |
| `LEX_ADMIN__DRIVERS` | dict[str, StorageLocalConfig  \| StorageS3Config  \| StorageGCSConfig  \| Storag | (required) | Driver-specific configurations | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/storage/config.py:Stora` |
| `LEX_ADMIN__EMBEDDING_MODEL` | str  \| None | None | Embedding model identifier. Must be set explicitly — no vendor-specific default. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGCon` |
| `LEX_ADMIN__EMBEDDING_MODEL` | str | "text-embedding-3-small" | Embedding model name for AI-layer embedding generation | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Vector` |
| `LEX_ADMIN__EMBEDDING_PROVIDER` | str | "openai" | Embedding provider (openai, cohere, etc.) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGCon` |
| `LEX_ADMIN__ENABLED` | bool | True | Enable AI features | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/config.py:AIConfig.e` |
| `LEX_ADMIN__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminConfig.enabled` |
| `LEX_ADMIN__ENABLED` | bool | (complex) | Whether cache is enabled | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheCo` |
| `LEX_ADMIN__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseC` |
| `LEX_ADMIN__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Events` |
| `LEX_ADMIN__ENABLED` | bool | True | Master on/off switch for all feedback collection | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/feedback/config.py:F` |
| `LEX_ADMIN__ENABLED` | bool | True | Enable the graph store subsystem | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:GraphCo` |
| `LEX_ADMIN__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Graph` |
| `LEX_ADMIN__ENABLED` | bool | True | Enable the MCP server subsystem | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPCon` |
| `LEX_ADMIN__ENABLED` | bool | True | Enable monitoring | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Monit` |
| `LEX_ADMIN__ENABLED` | bool | True | Enable NoSQL support | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:NoSQLCo` |
| `LEX_ADMIN__ENABLED` | bool | True | Master on/off switch for all observability | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/observability/config` |
| `LEX_ADMIN__ENABLED` | bool | True | Enable the RAG pipeline | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGCon` |
| `LEX_ADMIN__ENABLED` | bool | True | Whether secrets subsystem is enabled | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/secrets/config.py:Secre` |
| `LEX_ADMIN__ENABLED` | bool | True | Enable the security subsystem | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/storage/config.py:Stora` |
| `LEX_ADMIN__ENABLED` | bool | True | Whether tasks module is enabled | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskCon` |
| `LEX_ADMIN__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/testing/config.py:Testi` |
| `LEX_ADMIN__ENABLED` | bool | True | Enable the vector store subsystem | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Vector` |
| `LEX_ADMIN__ENABLE_ADMIN` | bool | True | Whether to register the AuditAdminContributor | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/audit/config.py:AuditCo` |
| `LEX_ADMIN__ENABLE_CACHE` | bool | False | Enable embedding caching (requires a CacheBackend binding) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Vector` |
| `LEX_ADMIN__ENABLE_CACHING` | bool | True | Enable caching for RAG queries | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGCon` |
| `LEX_ADMIN__ENABLE_CITATIONS` | bool | True | Include source citations in responses | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGCon` |
| `LEX_ADMIN__ENABLE_CORS` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__ENABLE_CSRF` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__ENABLE_HALLUCINATION_DETECTION` | bool | True | Enable hallucination detection for AI responses | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGCon` |
| `LEX_ADMIN__ENABLE_HYDE` | bool | False | Enable HyDE (Hypothetical Document Embeddings) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGCon` |
| `LEX_ADMIN__ENABLE_IDENTITY_RESOLUTION` | bool | False |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Graph` |
| `LEX_ADMIN__ENABLE_QUERY_EXPANSION` | bool | True | Enable query expansion techniques | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGCon` |
| `LEX_ADMIN__ENABLE_REALTIME` | bool | False | Enable realtime update features. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ui/config.py:UIConfig.e` |
| `LEX_ADMIN__ENABLE_SSE` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPCon` |
| `LEX_ADMIN__ENABLE_SSE` | bool | False | Enable Server-Sent Events support. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ui/config.py:UIConfig.e` |
| `LEX_ADMIN__ENV` | str  \| None | None | Environment (development/staging/production) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheCo` |
| `LEX_ADMIN__ENV` | str  \| None | None | Environment (development/staging/production) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Events` |
| `LEX_ADMIN__ENV` | str  \| None | None | Environment (development/staging/production) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Graph` |
| `LEX_ADMIN__ENV` | str  \| None | None | Environment (development/staging/production) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Monit` |
| `LEX_ADMIN__ENV` | str  \| None | None | Environment (development/staging/production) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/storage/config.py:Stora` |
| `LEX_ADMIN__ENV` | str  \| None | None | Environment (development/staging/production) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskCon` |
| `LEX_ADMIN__ENVIRONMENT` | str | (complex) | Environment | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheCo` |
| `LEX_ADMIN__ENVIRONMENT` | Environment | (complex) | Deployment environment | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Monit` |
| `LEX_ADMIN__ERRORS__DEBUG_MODE` | bool | False |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Error` |
| `LEX_ADMIN__ERRORS__INCLUDE_STACKTRACE` | bool | False |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Error` |
| `LEX_ADMIN__ERRORS__LOG_ERRORS` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Error` |
| `LEX_ADMIN__ERRORS__MASK_ERRORS` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Error` |
| `LEX_ADMIN__EVENT_BUS__ALLOW_NO_HANDLERS` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventB` |
| `LEX_ADMIN__EVENT_BUS__CONTINUE_ON_ERROR` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventB` |
| `LEX_ADMIN__EVENT_BUS__ENABLE_DEAD_LETTER` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventB` |
| `LEX_ADMIN__EVENT_BUS__HANDLER_TIMEOUT_SECONDS` | float | 30.0 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventB` |
| `LEX_ADMIN__EVENT_BUS__MAX_CONCURRENT_HANDLERS` | int | 10 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventB` |
| `LEX_ADMIN__EVENT_BUS__MAX_HANDLER_RETRIES` | int | 3 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventB` |
| `LEX_ADMIN__EVENT_BUS__MAX_QUEUE_PER_SUBSCRIBER` | int | 1000 | Maximum number of events queued per event type before backpressure is applied. 0 means unbounded (no backpressure). | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventB` |
| `LEX_ADMIN__EVENT_BUS__PARALLEL_DISPATCH` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventB` |
| `LEX_ADMIN__EVENT_BUS__RETRY_FAILED_HANDLERS` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventB` |
| `LEX_ADMIN__EVENT_STORE_BACKEND` | EventStoreBackend | (complex) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Events` |
| `LEX_ADMIN__EXTENSIONS` | dict[str, Any] | (required) |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminConfig.extensions` |
| `LEX_ADMIN__EXTRA` | dict[str, Any] | (required) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskCon` |
| `LEX_ADMIN__FEATURES__ACTIVITY_FEED` | bool | False |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.activity_` |
| `LEX_ADMIN__FEATURES__API_DOCS` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.api_docs` |
| `LEX_ADMIN__FEATURES__AUDIT_LOGGING` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.audit_log` |
| `LEX_ADMIN__FEATURES__AUTOSAVE` | bool | False |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.autosave` |
| `LEX_ADMIN__FEATURES__COMMAND_PALETTE` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.command_p` |
| `LEX_ADMIN__FEATURES__KEYBOARD_SHORTCUTS` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.keyboard_` |
| `LEX_ADMIN__FEATURES__NOTIFICATIONS` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.notificat` |
| `LEX_ADMIN__FEATURES__OPTIMISTIC_UPDATES` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.optimisti` |
| `LEX_ADMIN__FEATURES__SEARCH` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.search` |
| `LEX_ADMIN__FEATURES__THEME_TOGGLE` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.theme_tog` |
| `LEX_ADMIN__FEATURES__UNDO_REDO` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.undo_redo` |
| `LEX_ADMIN__FEATURES__WEBHOOKS` | bool | False |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.webhooks` |
| `LEX_ADMIN__FIRESTORE__CREDENTIALS_JSON` | str  \| None | None | Path to a service account JSON key file, or the raw JSON string. When ``None``, Application Default Credentials (ADC) ar | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:Firesto` |
| `LEX_ADMIN__FIRESTORE__DATABASE_ID` | str | "(default)" | Firestore database ID (use '(default)' for the default database) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:Firesto` |
| `LEX_ADMIN__FIRESTORE__PROJECT_ID` | str | Ellipsis | Google Cloud project ID | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:Firesto` |
| `LEX_ADMIN__FORM_DEFAULTS__AUTOSAVE_ENABLED` | bool | False |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:FormDefaults.form_defaults.autosave_en` |
| `LEX_ADMIN__FORM_DEFAULTS__AUTOSAVE_INTERVAL_MS` | int | 30000 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:FormDefaults.form_defaults.autosave_in` |
| `LEX_ADMIN__FORM_DEFAULTS__CONFIRM_UNSAVED_CHANGES` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:FormDefaults.form_defaults.confirm_uns` |
| `LEX_ADMIN__FORM_DEFAULTS__INLINE_VALIDATION` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:FormDefaults.form_defaults.inline_vali` |
| `LEX_ADMIN__FORM_DEFAULTS__SHOW_REQUIRED_INDICATOR` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:FormDefaults.form_defaults.show_requir` |
| `LEX_ADMIN__FRAMEWORK_PAGES__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:FrameworkPagesConfig.framework_pages.e` |
| `LEX_ADMIN__FRAMEWORK_PAGES__REQUIRE_PERMISSION` | str | "admin:framework:access" |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:FrameworkPagesConfig.framework_pages.r` |
| `LEX_ADMIN__GOVERNANCE` | Any | (required) | AI governance configuration | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/config.py:AIConfig.g` |
| `LEX_ADMIN__HEADERS__CONTENT_TYPE_NOSNIFF` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__HEADERS__CSP` | str  \| None | None |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__HEADERS__FRAME_OPTIONS` | str | "DENY" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__HEADERS__HSTS_INCLUDE_SUBDOMAINS` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__HEADERS__HSTS_MAX_AGE` | int | 31536000 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__HEADERS__PERMISSIONS_POLICY` | str  \| None | None |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__HEADERS__REFERRER_POLICY` | str | "strict-origin-when-cross-origin" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__HEADERS__XSS_PROTECTION` | str | "1; mode=block" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__HEALTH_CHECKS_ENABLED` | bool | True | Enable background health checking for AI components | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/observability/config` |
| `LEX_ADMIN__HEALTH_CHECK_TIMEOUT` | float | 5.0 | Timeout in seconds for the startup health check in StorageProvider.boot() | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/storage/config.py:Stora` |
| `LEX_ADMIN__HEALTH__CHECKS` | list[str] | (required) | List of health check names to run | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Healt` |
| `LEX_ADMIN__HEALTH__ENABLED` | bool | True | Enable health checks | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Healt` |
| `LEX_ADMIN__HEALTH__INCLUDE_DETAILS` | bool | True | Include detailed health info in response | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Healt` |
| `LEX_ADMIN__HEALTH__INTERVAL` | int | (complex) | Health check interval in seconds | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Healt` |
| `LEX_ADMIN__HEALTH__PATH` | str | "/health" | Health endpoint path | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Healt` |
| `LEX_ADMIN__HEALTH__TIMEOUT` | float | 5.0 | Health check timeout in seconds | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Healt` |
| `LEX_ADMIN__HMAC_KEY` | bytes  \| None | None | HMAC key for checksum computation | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/audit/config.py:AuditCo` |
| `LEX_ADMIN__HOST` | str | "0.0.0.0" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPCon` |
| `LEX_ADMIN__HSTS__ENABLED` | bool | False | Emit the Strict-Transport-Security header | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__HSTS__INCLUDE_SUBDOMAINS` | bool | True | Apply HSTS to all subdomains | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__HSTS__MAX_AGE` | int | 31536000 | HSTS max-age in seconds (default 1 year) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__HSTS__PRELOAD` | bool | False | Include site in HSTS preload list | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__HTMX_PREFIX` | str | "/admin/htmx" |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminConfig.htmx_prefix` |
| `LEX_ADMIN__HTMX_VERSION` | str | "2.0.4" | HTMX CDN version. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ui/config.py:UIConfig.h` |
| `LEX_ADMIN__INTEGRATIONS__CACHE__DEFAULT_TTL_SECONDS` | int | 60 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:CacheIntegrationConfig.integrations.ca` |
| `LEX_ADMIN__INTEGRATIONS__CACHE__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:CacheIntegrationConfig.integrations.ca` |
| `LEX_ADMIN__INTEGRATIONS__CACHE__KEY_PREFIX` | str | "admin" |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:CacheIntegrationConfig.integrations.ca` |
| `LEX_ADMIN__INTEGRATIONS__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminIntegrationsConfig.integrations.e` |
| `LEX_ADMIN__INTEGRATIONS__FEATURES__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:FeaturesIntegrationConfig.integrations` |
| `LEX_ADMIN__INTEGRATIONS__MONITOR__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:MonitorIntegrationConfig.integrations.` |
| `LEX_ADMIN__INTEGRATIONS__RESILIENCE__CIRCUIT_FAILURE_THRESHOLD` | int | 5 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:ResilienceIntegrationConfig.integratio` |
| `LEX_ADMIN__INTEGRATIONS__RESILIENCE__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:ResilienceIntegrationConfig.integratio` |
| `LEX_ADMIN__INTEGRATIONS__RESILIENCE__RETRY_MAX_ATTEMPTS` | int | 3 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:ResilienceIntegrationConfig.integratio` |
| `LEX_ADMIN__INTEGRATIONS__SEARCH__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:SearchIntegrationConfig.integrations.s` |
| `LEX_ADMIN__INTEGRATIONS__SEARCH__FALLBACK_TO_LIKE` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:SearchIntegrationConfig.integrations.s` |
| `LEX_ADMIN__INTEGRATIONS__STORAGE__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:StorageIntegrationConfig.integrations.` |
| `LEX_ADMIN__INTEGRATIONS__STORAGE__PRESIGNED_URL_EXPIRY` | int | 3600 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:StorageIntegrationConfig.integrations.` |
| `LEX_ADMIN__INTEGRATIONS__TASKS__BULK_THRESHOLD` | int | 25 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:TasksIntegrationConfig.integrations.ta` |
| `LEX_ADMIN__INTEGRATIONS__TASKS__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:TasksIntegrationConfig.integrations.ta` |
| `LEX_ADMIN__INTEGRATION__CACHE_KEY_PREFIX` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Integ` |
| `LEX_ADMIN__INTEGRATION__SQL_CONTEXT_BRIDGE` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Integ` |
| `LEX_ADMIN__INTROSPECTION__ALLOWED_ENVIRONMENTS` | set[str] | (required) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Intro` |
| `LEX_ADMIN__INTROSPECTION__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Intro` |
| `LEX_ADMIN__KAFKA__AUTO_OFFSET_RESET` | str | "earliest" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:KafkaC` |
| `LEX_ADMIN__KAFKA__BOOTSTRAP_SERVERS` | str | Ellipsis | Kafka bootstrap servers | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:KafkaC` |
| `LEX_ADMIN__KAFKA__CONSUMER_GROUP` | str | "events-consumers" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:KafkaC` |
| `LEX_ADMIN__KAFKA__ENABLE_AUTO_COMMIT` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:KafkaC` |
| `LEX_ADMIN__KAFKA__TOPIC_PREFIX` | str | "events" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:KafkaC` |
| `LEX_ADMIN__LIFECYCLE__AUTO_PROVISION_ISOLATION` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Lifec` |
| `LEX_ADMIN__LIFECYCLE__ISOLATION_STRATEGY` | str | "row_level" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Lifec` |
| `LEX_ADMIN__LLM` | Any  \| None | None | LLM configuration (optional) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/config.py:AIConfig.l` |
| `LEX_ADMIN__LOGGING_MIDDLEWARE__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Loggin` |
| `LEX_ADMIN__LOGGING_MIDDLEWARE__INCLUDE_PAYLOAD` | bool | False |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Loggin` |
| `LEX_ADMIN__LOGGING_MIDDLEWARE__LOG_LEVEL` | str | "INFO" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Loggin` |
| `LEX_ADMIN__LOGGING_MIDDLEWARE__MAX_PAYLOAD_LENGTH` | int | 1000 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Loggin` |
| `LEX_ADMIN__LOGGING__ENABLED` | bool | True | Enable structured logging | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Loggi` |
| `LEX_ADMIN__LOGGING__FORMAT` | str | "json" | Log format (json, text) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Loggi` |
| `LEX_ADMIN__LOGGING__INCLUDE_TRACE_CONTEXT` | bool | True | Include trace context in logs | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Loggi` |
| `LEX_ADMIN__LOGGING__LEVEL` | str | "INFO" | Default log level | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Loggi` |
| `LEX_ADMIN__LOGGING__REDACT_FIELDS` | list[str] | (required) | Fields to redact from logs | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Loggi` |
| `LEX_ADMIN__MAX_AGE_SECONDS` | float | (complex) | Seconds before automatic rotation | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/secrets/config.py:Secre` |
| `LEX_ADMIN__MAX_REQUEST_SIZE` | int | (complex) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPCon` |
| `LEX_ADMIN__MAX_RETRIES` | int | (complex) | Maximum number of retries for operations | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:GraphCo` |
| `LEX_ADMIN__MAX_RETRIES` | int | (complex) | Maximum number of retries for operations | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Vector` |
| `LEX_ADMIN__MEMORY__ENABLE_SNAPSHOTS` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:InMemo` |
| `LEX_ADMIN__MEMORY__MAX_COLLECTIONS` | int | 100 | Maximum number of collections in memory | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Memory` |
| `LEX_ADMIN__MEMORY__MAX_EDGES` | int | (complex) | Maximum number of edges in memory | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:MemoryC` |
| `LEX_ADMIN__MEMORY__MAX_EVENTS_PER_STREAM` | int | 10000 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:InMemo` |
| `LEX_ADMIN__MEMORY__MAX_NODES` | int | (complex) | Maximum number of nodes in memory | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:MemoryC` |
| `LEX_ADMIN__MEMORY__MAX_VECTORS_PER_COLLECTION` | int | 100000 | Maximum number of vectors per collection | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Memory` |
| `LEX_ADMIN__METRICS_ENABLED` | bool | True | Enable metrics collection | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/observability/config` |
| `LEX_ADMIN__METRICS_MIDDLEWARE__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Metric` |
| `LEX_ADMIN__METRICS_MIDDLEWARE__HISTOGRAM_BUCKETS` | list[float] | (required) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Metric` |
| `LEX_ADMIN__METRICS_MIDDLEWARE__INCLUDE_HISTOGRAMS` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Metric` |
| `LEX_ADMIN__METRICS_MIDDLEWARE__PREFIX` | str | "events" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Metric` |
| `LEX_ADMIN__METRICS__COLLECTION_INTERVAL` | float | 60.0 | Metrics collection interval in seconds | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Metri` |
| `LEX_ADMIN__METRICS__DEFAULT_LABELS` | dict[str, str] | (required) | Default labels for all metrics | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Metri` |
| `LEX_ADMIN__METRICS__ENABLED` | bool | True | Enable metrics collection | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Metri` |
| `LEX_ADMIN__METRICS__ENABLED` | bool | False |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Metri` |
| `LEX_ADMIN__METRICS__HISTOGRAM_BUCKETS` | list[float] | (required) | Default histogram bucket boundaries | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Metri` |
| `LEX_ADMIN__METRICS__HISTOGRAM_BUCKETS` | list[float] | (required) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Metri` |
| `LEX_ADMIN__METRICS__INCLUDE_LABELS` | list[str] | (required) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Metri` |
| `LEX_ADMIN__METRICS__NAMESPACE` | str | "lexigram_graphql" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Metri` |
| `LEX_ADMIN__METRICS__PREFIX` | str | (complex) | MetricProtocol name prefix | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Metri` |
| `LEX_ADMIN__MIGRATIONS__LOCK_TIMEOUT` | Duration | Duration.seconds(...) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseM` |
| `LEX_ADMIN__MIN_CITATION_CONFIDENCE` | float | 0.6 | Minimum confidence for citation inclusion | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGCon` |
| `LEX_ADMIN__MOCK_EXTERNAL_SERVICES` | bool | True | Mock external service calls | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/testing/config.py:Testi` |
| `LEX_ADMIN__MONGODB__AUTH_SOURCE` | str | "admin" | Authentication database | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDB` |
| `LEX_ADMIN__MONGODB__CONNECTION_STRING` | SecretStr | Ellipsis | MongoDB connection string | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:MongoD` |
| `LEX_ADMIN__MONGODB__CONNECT_TIMEOUT_MS` | int | 10000 | Connection timeout (ms) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDB` |
| `LEX_ADMIN__MONGODB__DATABASE` | str | "lexigram" | Database name | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDB` |
| `LEX_ADMIN__MONGODB__DATABASE_NAME` | str | "events" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:MongoD` |
| `LEX_ADMIN__MONGODB__EVENTS_COLLECTION` | str | "domain_events" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:MongoD` |
| `LEX_ADMIN__MONGODB__MAX_POOL_SIZE` | int | 100 | Maximum connection pool size | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDB` |
| `LEX_ADMIN__MONGODB__MAX_POOL_SIZE` | int | 10 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:MongoD` |
| `LEX_ADMIN__MONGODB__MIN_POOL_SIZE` | int | 10 | Minimum connection pool size | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDB` |
| `LEX_ADMIN__MONGODB__READ_PREFERENCE` | str | "primaryPreferred" | Read preference mode | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDB` |
| `LEX_ADMIN__MONGODB__RETRY_READS` | bool | True | Enable read retries | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDB` |
| `LEX_ADMIN__MONGODB__RETRY_WRITES` | bool | True | Enable write retries | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDB` |
| `LEX_ADMIN__MONGODB__SERVER_SELECTION_TIMEOUT` | int | 30000 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:MongoD` |
| `LEX_ADMIN__MONGODB__SERVER_SELECTION_TIMEOUT_MS` | int | 5000 | Server selection timeout (ms) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDB` |
| `LEX_ADMIN__MONGODB__SNAPSHOTS_COLLECTION` | str | "snapshots" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:MongoD` |
| `LEX_ADMIN__MONGODB__SOCKET_TIMEOUT_MS` | int | 30000 | Socket timeout (ms) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDB` |
| `LEX_ADMIN__MONGODB__URI` | str | "mongodb://localhost:27017" | MongoDB connection URI | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDB` |
| `LEX_ADMIN__MONGODB__WRITE_CONCERN_W` | str  \| int | "majority" | Write concern level | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDB` |
| `LEX_ADMIN__NAME` | str | "ai" | Configuration name | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/config.py:AIConfig.n` |
| `LEX_ADMIN__NAME` | str | "admin" |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminConfig.name` |
| `LEX_ADMIN__NAME` | str | (complex) | Provider name | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheCo` |
| `LEX_ADMIN__NAME` | str | "database" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseC` |
| `LEX_ADMIN__NAME` | str | "events" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Events` |
| `LEX_ADMIN__NAME` | str | "graphql" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Graph` |
| `LEX_ADMIN__NAME` | str | (complex) | Provider name | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Monit` |
| `LEX_ADMIN__NAME` | str | "secrets" | Configuration name | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/secrets/config.py:Secre` |
| `LEX_ADMIN__NAME` | str | "storage" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/storage/config.py:Stora` |
| `LEX_ADMIN__NAME` | str | "tasks" | Configuration name | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskCon` |
| `LEX_ADMIN__NAVIGATION_GROUPS` | dict[str, AdminNavigationGroup] | (required) |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminConfig.navigation_groups` |
| `LEX_ADMIN__NEO4J__CONNECTION_TIMEOUT` | float | (complex) | Connection timeout in seconds | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:Neo4jCo` |
| `LEX_ADMIN__NEO4J__DATABASE` | str | (complex) | Target database name | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:Neo4jCo` |
| `LEX_ADMIN__NEO4J__ENCRYPTED` | bool | False | Whether to use SSL/TLS encryption | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:Neo4jCo` |
| `LEX_ADMIN__NEO4J__FETCH_SIZE` | int | (complex) | Default fetch size for results | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:Neo4jCo` |
| `LEX_ADMIN__NEO4J__MAX_CONNECTION_POOL_SIZE` | int | (complex) | Maximum number of connections in the pool | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:Neo4jCo` |
| `LEX_ADMIN__NEO4J__MAX_TRANSACTION_RETRY_TIME` | float | 30.0 | Maximum time for transaction retries | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:Neo4jCo` |
| `LEX_ADMIN__NEO4J__PASSWORD` | SecretStr | (required) | Neo4j password | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:Neo4jCo` |
| `LEX_ADMIN__NEO4J__TRUST` | str | "TRUST_SYSTEM_CA_SIGNED_CERTIFICATES" | Trust strategy for SSL | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:Neo4jCo` |
| `LEX_ADMIN__NEO4J__URI` | str | "bolt://localhost:7687" | Neo4j BOLT URI | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:Neo4jCo` |
| `LEX_ADMIN__NEO4J__USERNAME` | str | "neo4j" | Neo4j username | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:Neo4jCo` |
| `LEX_ADMIN__OBSERVABILITY` | Any | (required) | AI observability configuration (tracing and metrics) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/config.py:AIConfig.o` |
| `LEX_ADMIN__OBSERVABILITY__HIGH_CARDINALITY_LABELS_ENABLED` | bool | False |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminObservabilityConfig.observability` |
| `LEX_ADMIN__OBSERVABILITY__METRICS_ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminObservabilityConfig.observability` |
| `LEX_ADMIN__OPENTELEMETRY__BATCH_SIZE` | int | 512 | Export batch size | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:OpenT` |
| `LEX_ADMIN__OPENTELEMETRY__COMPRESSION` | str | "none" | Compression type (none, gzip) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:OpenT` |
| `LEX_ADMIN__OPENTELEMETRY__ENDPOINT` | str  \| None | None | OTLP endpoint URL | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:OpenT` |
| `LEX_ADMIN__OPENTELEMETRY__EXPORT_INTERVAL` | float | 5.0 | Export interval seconds | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:OpenT` |
| `LEX_ADMIN__OPENTELEMETRY__HEADERS` | dict[str, str] | (required) | OTLP request headers | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:OpenT` |
| `LEX_ADMIN__OPENTELEMETRY__INSECURE` | bool | False | Use insecure connection | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:OpenT` |
| `LEX_ADMIN__OPENTELEMETRY__METRICS_EXPORTERS` | list[OTelExporterConfig] | (required) | List of metrics exporters to build. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:OpenT` |
| `LEX_ADMIN__OPENTELEMETRY__TIMEOUT` | float | 30.0 | Export timeout seconds | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:OpenT` |
| `LEX_ADMIN__OPENTELEMETRY__TRACING_EXPORTERS` | list[OTelExporterConfig] | (required) | List of tracing exporters to build. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:OpenT` |
| `LEX_ADMIN__OPERATIONS__ECHO` | bool | False |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseO` |
| `LEX_ADMIN__OPERATIONS__STATEMENT_TIMEOUT` | Duration | Duration.seconds(...) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseO` |
| `LEX_ADMIN__OUTBOX__BATCH_MAX_AGE` | Duration | Duration.seconds(...) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseO` |
| `LEX_ADMIN__OUTBOX__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseO` |
| `LEX_ADMIN__OUTBOX__POLL_INTERVAL` | Duration | Duration.seconds(...) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseO` |
| `LEX_ADMIN__OVERRIDES__CACHE_TTL` | int | DEFAULT_CONFIG_CACHE_TTL |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Confi` |
| `LEX_ADMIN__PATH` | str | (complex) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Graph` |
| `LEX_ADMIN__PATH` | str | "/mcp" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPCon` |
| `LEX_ADMIN__PERMISSIONS_POLICY` | dict[str, str] | (required) | Permissions-Policy directive map | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__PERSISTED_QUERIES__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Persi` |
| `LEX_ADMIN__PERSISTED_QUERIES__STORE_TYPE` | str | "memory" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Persi` |
| `LEX_ADMIN__PERSISTED_QUERIES__TTL_SECONDS` | Duration  \| int | 86400 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Persi` |
| `LEX_ADMIN__PERSIST_DIRECTORY` | str  \| None | None | Local directory path for vector store persistence (e.g. Chroma) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGCon` |
| `LEX_ADMIN__PGVECTOR__CREATE_EXTENSION` | bool | True | Whether to create pgvector extension if missing | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:PgVect` |
| `LEX_ADMIN__PGVECTOR__DATABASE` | str | "primary" | Name of the database backend from db.backends to use for pgvector. Matches a 'name:' entry in the db.backends list. Defa | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:PgVect` |
| `LEX_ADMIN__PGVECTOR__DEFAULT_EF_SEARCH` | int | (complex) | Default ef_search for HNSW index | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:PgVect` |
| `LEX_ADMIN__PGVECTOR__DEFAULT_LISTS` | int | (complex) | Default number of lists for IVFFlat index | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:PgVect` |
| `LEX_ADMIN__PGVECTOR__DEFAULT_PROBES` | int | (complex) | Default number of probes for IVFFlat index | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:PgVect` |
| `LEX_ADMIN__PGVECTOR__SCHEMA` | str | "public" | Database schema for vector tables | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:PgVect` |
| `LEX_ADMIN__PGVECTOR__TABLE_PREFIX` | str | "vec_" | Prefix for vector storage tables | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:PgVect` |
| `LEX_ADMIN__PINECONE__API_KEY` | SecretStr | SecretStr(...) | Pinecone API key | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Pineco` |
| `LEX_ADMIN__PINECONE__ENVIRONMENT` | str | "" | Pinecone environment (e.g. 'us-west1-gcp') | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Pineco` |
| `LEX_ADMIN__PINECONE__INDEX_NAME` | str | "" | Name of the Pinecone index | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Pineco` |
| `LEX_ADMIN__PINECONE__NAMESPACE` | str | "" | Default namespace for the index | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Pineco` |
| `LEX_ADMIN__PINECONE__POOL_THREADS` | int | 4 | Number of threads for the connection pool | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Pineco` |
| `LEX_ADMIN__PINECONE__TIMEOUT` | float | (complex) | Request timeout in seconds | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Pineco` |
| `LEX_ADMIN__PLAYGROUND__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Playg` |
| `LEX_ADMIN__PLAYGROUND__PATH` | str | (complex) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Playg` |
| `LEX_ADMIN__PLAYGROUND__TITLE` | str | "Lexigram GraphQL Playground" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Playg` |
| `LEX_ADMIN__POOL__ACQUIRE_TIMEOUT` | Duration | Duration.seconds(...) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseP` |
| `LEX_ADMIN__POOL__IDLE_TIMEOUT` | Duration | Duration.minutes(...) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseP` |
| `LEX_ADMIN__POOL__MAX_LIFETIME` | Duration | Duration.hours(...) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseP` |
| `LEX_ADMIN__POOL__MAX_OVERFLOW` | int | 5 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseP` |
| `LEX_ADMIN__POOL__MAX_SIZE` | int | (complex) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseP` |
| `LEX_ADMIN__POOL__MIN_SIZE` | int | (complex) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseP` |
| `LEX_ADMIN__POOL__RECYCLE` | int | 3600 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseP` |
| `LEX_ADMIN__POOL__TIMEOUT` | float | (complex) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseP` |
| `LEX_ADMIN__PORT` | int | 8080 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPCon` |
| `LEX_ADMIN__POSTGRES` | PostgresEventStoreConfig  \| None | None |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Events` |
| `LEX_ADMIN__PREFIX` | str | "/admin" |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminConfig.prefix` |
| `LEX_ADMIN__PROJECTION__BATCH_SIZE` | int | 100 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Projec` |
| `LEX_ADMIN__PROJECTION__CHECKPOINT_INTERVAL` | int | 100 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Projec` |
| `LEX_ADMIN__PROJECTION__ENABLE_PARALLEL_PROJECTIONS` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Projec` |
| `LEX_ADMIN__PROJECTION__MAX_CATCH_UP_EVENTS` | int | 10000 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Projec` |
| `LEX_ADMIN__PROJECTION__REBUILD_BATCH_SIZE` | int | 1000 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Projec` |
| `LEX_ADMIN__PROMETHEUS__ENABLE_DEFAULT_METRICS` | bool | True | Enable default process metrics | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Prome` |
| `LEX_ADMIN__PROMETHEUS__METRICS_TABLE` | str | "metrics_samples" | Table name for metrics samples | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Prome` |
| `LEX_ADMIN__PROMETHEUS__PATH` | str | "/metrics" | Metrics endpoint path | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Prome` |
| `LEX_ADMIN__PROMETHEUS__PORT` | int | (complex) | Metrics server port | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Prome` |
| `LEX_ADMIN__PROMETHEUS__PUSHGATEWAY_URL` | str  \| None | None | Pushgateway URL for push-based metrics | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Prome` |
| `LEX_ADMIN__PROMETHEUS__PUSH_INTERVAL` | float | 10.0 | Push interval for Pushgateway | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Prome` |
| `LEX_ADMIN__PROMETHEUS__STORE_IN_DB` | bool | False | Persist metrics observations to DB | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Prome` |
| `LEX_ADMIN__PUSH_BACKENDS` | list[NamedPushConfig] | (required) | Named push notification backends for multi-backend support. When non-empty, the provider registers each backend under An | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/notification/config.py:` |
| `LEX_ADMIN__QDRANT__API_KEY` | SecretStr  \| None | None | Qdrant API key | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Qdrant` |
| `LEX_ADMIN__QDRANT__GRPC_PORT` | int | 6334 | gRPC port for Qdrant | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Qdrant` |
| `LEX_ADMIN__QDRANT__PREFER_GRPC` | bool | True | Whether to prefer gRPC over HTTP | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Qdrant` |
| `LEX_ADMIN__QDRANT__TIMEOUT` | float | (complex) | Request timeout in seconds | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Qdrant` |
| `LEX_ADMIN__QDRANT__URL` | str | "http://localhost:6333" | Qdrant server URL | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Qdrant` |
| `LEX_ADMIN__QUERY_BUS__ENABLE_LOGGING` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:QueryB` |
| `LEX_ADMIN__QUERY_BUS__ENABLE_METRICS` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:QueryB` |
| `LEX_ADMIN__QUERY_BUS__TIMEOUT_SECONDS` | float | 30.0 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:QueryB` |
| `LEX_ADMIN__RABBITMQ__DURABLE` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Rabbit` |
| `LEX_ADMIN__RABBITMQ__EXCHANGE_NAME` | str | "events" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Rabbit` |
| `LEX_ADMIN__RABBITMQ__PREFETCH_COUNT` | int | 10 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Rabbit` |
| `LEX_ADMIN__RABBITMQ__QUEUE_PREFIX` | str | "events" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Rabbit` |
| `LEX_ADMIN__RABBITMQ__URL` | SecretStr | Ellipsis | AMQP connection URL | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Rabbit` |
| `LEX_ADMIN__RAG` | Any  \| None | None | RAG pipeline configuration (optional) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/config.py:AIConfig.r` |
| `LEX_ADMIN__RATE_LIMIT` | RateLimitConfig | (required) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Graph` |
| `LEX_ADMIN__RATE_LIMIT__BULK_PER_MINUTE` | int | 5 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminRateLimitConfig.rate_limit.bulk_p` |
| `LEX_ADMIN__RATE_LIMIT__BURST` | int  \| None | None | Maximum burst size | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskRat` |
| `LEX_ADMIN__RATE_LIMIT__BURST_SIZE` | int | 10 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminRateLimitConfig.rate_limit.burst_` |
| `LEX_ADMIN__RATE_LIMIT__CREATE_PER_MINUTE` | int | 30 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminRateLimitConfig.rate_limit.create` |
| `LEX_ADMIN__RATE_LIMIT__DELETE_PER_MINUTE` | int | 20 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminRateLimitConfig.rate_limit.delete` |
| `LEX_ADMIN__RATE_LIMIT__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminRateLimitConfig.rate_limit.enable` |
| `LEX_ADMIN__RATE_LIMIT__ENABLED` | bool | False | Whether rate limiting is enabled | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskRat` |
| `LEX_ADMIN__RATE_LIMIT__PER` | float | 1.0 | Time period in seconds | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskRat` |
| `LEX_ADMIN__RATE_LIMIT__RATE` | int | 100 | Number of tasks allowed per time period | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskRat` |
| `LEX_ADMIN__RATE_LIMIT__REQUESTS_PER_HOUR` | int | 1000 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminRateLimitConfig.rate_limit.reques` |
| `LEX_ADMIN__RATE_LIMIT__REQUESTS_PER_MINUTE` | int | 60 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminRateLimitConfig.rate_limit.reques` |
| `LEX_ADMIN__RATE_LIMIT__UPDATE_PER_MINUTE` | int | 60 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminRateLimitConfig.rate_limit.update` |
| `LEX_ADMIN__RBAC__SUPER_ADMIN_ROLE` | str | "superadmin" |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminRbacConfig.rbac.super_admin_role` |
| `LEX_ADMIN__REFERRER_POLICY` | str | "strict-origin-when-cross-origin" | Referrer-Policy header value | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:` |
| `LEX_ADMIN__REQUEST_TIMEOUT` | float | 30.0 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPCon` |
| `LEX_ADMIN__REQUIRE_AUTH` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminConfig.require_auth` |
| `LEX_ADMIN__RESOLUTION__HEADER_NAME` | str | DEFAULT_HEADER_NAME |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Resol` |
| `LEX_ADMIN__RESOLUTION__JWT_CLAIM_KEY` | str | DEFAULT_JWT_CLAIM_KEY |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Resol` |
| `LEX_ADMIN__RESOLUTION__PATH_PATTERN` | str  \| None | DEFAULT_PATH_PATTERN |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Resol` |
| `LEX_ADMIN__RESOLUTION__RESOLVERS` | list[str] | field(...) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Resol` |
| `LEX_ADMIN__RESOLUTION__STRICT_MEMBERSHIP` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Resol` |
| `LEX_ADMIN__RESOLUTION__SUBDOMAIN_PATTERN` | str  \| None | None |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Resol` |
| `LEX_ADMIN__RESOLUTION__TRUSTED_RESOLVERS` | list[str] | field(...) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Resol` |
| `LEX_ADMIN__RESOLUTION__VALIDATOR_CACHE_TTL` | int | DEFAULT_VALIDATOR_CACHE_TTL |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Resol` |
| `LEX_ADMIN__RESOURCES` | dict[str, ResourceYAMLConfig] | (required) |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminConfig.resources` |
| `LEX_ADMIN__RESOURCE_DEFAULTS__ACTION_LAYOUT` | Literal['horizontal', 'vertical', 'dropdown'] | "horizontal" |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:ResourceDefaults.resource_defaults.act` |
| `LEX_ADMIN__RESOURCE_DEFAULTS__ENABLE_BULK_ACTIONS` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:ResourceDefaults.resource_defaults.ena` |
| `LEX_ADMIN__RESOURCE_DEFAULTS__ENABLE_EXPORT` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:ResourceDefaults.resource_defaults.ena` |
| `LEX_ADMIN__RESOURCE_DEFAULTS__ENABLE_SEARCH` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:ResourceDefaults.resource_defaults.ena` |
| `LEX_ADMIN__RESOURCE_DEFAULTS__PER_PAGE` | int | 20 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:ResourceDefaults.resource_defaults.per` |
| `LEX_ADMIN__RESOURCE_DEFAULTS__SOFT_DELETE` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:ResourceDefaults.resource_defaults.sof` |
| `LEX_ADMIN__RESOURCE_DEFAULTS__TIMESTAMP_FIELDS` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:ResourceDefaults.resource_defaults.tim` |
| `LEX_ADMIN__RETENTION_POLICY` | RetentionPolicy | (required) | Retention rules | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/audit/config.py:AuditCo` |
| `LEX_ADMIN__RETRY` | RetryConfig | field(...) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Re` |
| `LEX_ADMIN__RETRY` | RetryConfig | (required) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskCon` |
| `LEX_ADMIN__RETRY_DELAY` | float | (complex) | Delay between retries in seconds | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:GraphCo` |
| `LEX_ADMIN__RETRY_DELAY` | float | (complex) | Delay between retries in seconds | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Vector` |
| `LEX_ADMIN__RETRY_MIDDLEWARE__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:RetryM` |
| `LEX_ADMIN__RETRY_MIDDLEWARE__EXPONENTIAL_BASE` | float | 2.0 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:RetryM` |
| `LEX_ADMIN__RETRY_MIDDLEWARE__INITIAL_DELAY_SECONDS` | float | 0.1 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:RetryM` |
| `LEX_ADMIN__RETRY_MIDDLEWARE__MAX_DELAY_SECONDS` | float | 10.0 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:RetryM` |
| `LEX_ADMIN__RETRY_MIDDLEWARE__MAX_RETRIES` | int | 3 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:RetryM` |
| `LEX_ADMIN__SAGA__CLEANUP_COMPLETED_AFTER_HOURS` | int | 24 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:SagaCo` |
| `LEX_ADMIN__SAGA__DEFAULT_TIMEOUT_SECONDS` | float | 300.0 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:SagaCo` |
| `LEX_ADMIN__SAGA__ENABLE_COMPENSATION` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:SagaCo` |
| `LEX_ADMIN__SAGA__MAX_RETRIES_PER_STEP` | int | 3 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:SagaCo` |
| `LEX_ADMIN__SAGA__PERSIST_STATE` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:SagaCo` |
| `LEX_ADMIN__SAGA__RETRY_DELAY_SECONDS` | float | 1.0 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:SagaCo` |
| `LEX_ADMIN__SCHEDULER__CHECK_INTERVAL` | float | (complex) | Interval between schedule checks (seconds) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskSch` |
| `LEX_ADMIN__SCHEDULER__ENABLED` | bool | True | Whether scheduling is enabled | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskSch` |
| `LEX_ADMIN__SCHEDULER__TIMEZONE` | str | (complex) | Timezone for cron expressions | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskSch` |
| `LEX_ADMIN__SCHEMA_BASELINE_PATH` | str  \| None | None | Path to a GraphQL SDL (.graphql) file containing the baseline schema. When set, GraphQLProvider.boot() compares the curr | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Graph` |
| `LEX_ADMIN__SERVER_NAME` | str | "lexigram-mcp" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPCon` |
| `LEX_ADMIN__SERVER_VERSION` | str | "1.0.0" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPCon` |
| `LEX_ADMIN__SERVICE__ALLOWED_MIME_TYPES` | list[str] | (required) | Allowed MIME types for upload validation. Defaults to a safe set of common image types: ['image/jpeg', 'image/png', 'ima | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/storage/config.py:Stora` |
| `LEX_ADMIN__SERVICE__CIRCUIT_BREAKER_ENABLED` | bool | (complex) | Enable circuit breaker | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheSe` |
| `LEX_ADMIN__SERVICE__CIRCUIT_BREAKER_THRESHOLD` | int | (complex) | Circuit breaker threshold | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheSe` |
| `LEX_ADMIN__SERVICE__DEFAULT_BACKEND` | str  \| None | None | Default backend name | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheSe` |
| `LEX_ADMIN__SERVICE__DEFAULT_SERIALIZER` | str | (complex) | Default serializer | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheSe` |
| `LEX_ADMIN__SERVICE__ENABLE_HEALTH_CHECKS` | bool | (complex) | Enable health checks | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheSe` |
| `LEX_ADMIN__SERVICE__ENABLE_METRICS` | bool | (complex) | Enable metrics | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheSe` |
| `LEX_ADMIN__SERVICE__ENABLE_PROTECTION` | bool | (complex) | Enable stampede protection | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheSe` |
| `LEX_ADMIN__SERVICE__MAX_FILE_SIZE_MB` | int | (complex) | Maximum file size in MB | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/storage/config.py:Stora` |
| `LEX_ADMIN__SERVICE__PROTECTION_LOCK_TTL` | int | (complex) | Protection lock TTL | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheSe` |
| `LEX_ADMIN__SERVICE__PROTECTION_MAX_WAIT` | float | (complex) | Max wait for locks | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheSe` |
| `LEX_ADMIN__SERVICE__PROTECTION_RETRY_INTERVAL` | float | (complex) | Lock retry interval | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheSe` |
| `LEX_ADMIN__SIMILARITY_THRESHOLD` | float | 0.7 | Minimum similarity score threshold | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGCon` |
| `LEX_ADMIN__SLO__ALERT_CHANNELS` | list[str] | (required) | Alert channel names for SLO violation dispatch | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:SLOCo` |
| `LEX_ADMIN__SLO__ENABLED` | bool | True | Enable periodic SLO evaluation worker | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:SLOCo` |
| `LEX_ADMIN__SLO__EVALUATION_INTERVAL` | float | 60.0 | SLO evaluation interval in seconds | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:SLOCo` |
| `LEX_ADMIN__SLO__SUPPRESSION_WINDOW_SECONDS` | int | 300 | Alert suppression window in seconds | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:SLOCo` |
| `LEX_ADMIN__SMS_BACKENDS` | list[NamedSMSConfig] | (required) | Named SMS backends for multi-backend support. When non-empty, the provider registers each backend under Annotated[SMSCha | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/notification/config.py:` |
| `LEX_ADMIN__SNAPSHOTS__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Snapsh` |
| `LEX_ADMIN__SNAPSHOTS__EVENT_COUNT_THRESHOLD` | int | 100 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Snapsh` |
| `LEX_ADMIN__SNAPSHOTS__MAX_SNAPSHOTS_PER_AGGREGATE` | int | 5 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Snapsh` |
| `LEX_ADMIN__SNAPSHOTS__STRATEGY` | SnapshotStrategy | (complex) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Snapsh` |
| `LEX_ADMIN__SNAPSHOTS__TIME_THRESHOLD_SECONDS` | int | 3600 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Snapsh` |
| `LEX_ADMIN__SQLITE__DATABASE` | str | "./events.db" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Sqlite` |
| `LEX_ADMIN__SQLITE__JOURNAL_MODE` | str | "WAL" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Sqlite` |
| `LEX_ADMIN__SQLITE__PRAGMAS` | dict[str, str] | (required) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Sqlite` |
| `LEX_ADMIN__SQLITE__WAL_MODE` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Sqlite` |
| `LEX_ADMIN__STATIC_DIR` | str  \| None | None |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminConfig.static_dir` |
| `LEX_ADMIN__STATIC_PREFIX` | str | "/admin/static" |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminConfig.static_prefix` |
| `LEX_ADMIN__STDIO_MODE` | bool | False |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPCon` |
| `LEX_ADMIN__STORE_BACKEND` | str | (complex) | Backend type — 'sql' or 'memory' | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/audit/config.py:AuditCo` |
| `LEX_ADMIN__STORE_RAW_PAYLOADS` | bool | False | Persist raw incoming feedback payloads for auditing | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/feedback/config.py:F` |
| `LEX_ADMIN__STREAMING__BATCH_SIZE` | int | 100 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Stream` |
| `LEX_ADMIN__STREAMING__BUFFER_SIZE` | int | 1000 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Stream` |
| `LEX_ADMIN__STREAMING__ENABLE_WEBSOCKET` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Stream` |
| `LEX_ADMIN__STREAMING__MAX_SUBSCRIBERS` | int | 100 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Stream` |
| `LEX_ADMIN__STREAMING__POLL_INTERVAL_MS` | int | 100 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Stream` |
| `LEX_ADMIN__STREAMING__WEBSOCKET_PING_INTERVAL` | int | 30 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Stream` |
| `LEX_ADMIN__STRICT_RESOURCE_RESOLUTION` | bool | True | When True (production default), resource/controller resolution failures during AdminProvider.boot() raise immediately. W | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminConfig.strict_resource_resolution` |
| `LEX_ADMIN__SUBSCRIPTIONS__CONNECTION_TIMEOUT` | Duration  \| int | 60 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Subsc` |
| `LEX_ADMIN__SUBSCRIPTIONS__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Subsc` |
| `LEX_ADMIN__SUBSCRIPTIONS__KEEPALIVE_INTERVAL` | Duration  \| int | (complex) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Subsc` |
| `LEX_ADMIN__SUBSCRIPTIONS__PATH` | str | (complex) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Subsc` |
| `LEX_ADMIN__SUBSCRIPTIONS__PROTOCOL` | SubscriptionProtocol | (complex) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Subsc` |
| `LEX_ADMIN__SUBSYSTEMS` | dict[str, dict[str, Any]] | (required) | Dynamic configuration for third-party AI subsystems discovered via entry points.  Keys are subsystem names; values are t | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/config.py:AIConfig.s` |
| `LEX_ADMIN__SYNTHESIS_STRATEGY` | str | "hybrid" | Synthesis strategy (direct, extractive, abstractive, hybrid) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGCon` |
| `LEX_ADMIN__TABLE_DEFAULTS__ENABLE_COLUMN_VISIBILITY` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:TableDefaults.table_defaults.enable_co` |
| `LEX_ADMIN__TABLE_DEFAULTS__HOVER_HIGHLIGHT` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:TableDefaults.table_defaults.hover_hig` |
| `LEX_ADMIN__TABLE_DEFAULTS__REORDERABLE_COLUMNS` | bool | False |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:TableDefaults.table_defaults.reorderab` |
| `LEX_ADMIN__TABLE_DEFAULTS__ROW_HEIGHT` | int | 48 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:TableDefaults.table_defaults.row_heigh` |
| `LEX_ADMIN__TABLE_DEFAULTS__STICKY_HEADER` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:TableDefaults.table_defaults.sticky_he` |
| `LEX_ADMIN__TABLE_DEFAULTS__VIRTUALIZED` | bool | False |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:TableDefaults.table_defaults.virtualiz` |
| `LEX_ADMIN__TABLE_DEFAULTS__ZEBRA_STRIPES` | bool | True |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:TableDefaults.table_defaults.zebra_str` |
| `LEX_ADMIN__TABLE_NAME` | str | (complex) | SQL table name for the unified audit store | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/audit/config.py:AuditCo` |
| `LEX_ADMIN__TEMPLATES_DIR` | str  \| None | None |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminConfig.templates_dir` |
| `LEX_ADMIN__TENANCY__COOKIE_NAME` | str | "admin_tenant" |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:TenancyConfig.tenancy.cookie_name` |
| `LEX_ADMIN__TENANCY__DEFAULT_TENANT_ID` | str | "" |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:TenancyConfig.tenancy.default_tenant_i` |
| `LEX_ADMIN__TENANCY__ENABLED` | bool | False | Enable tenant-aware graph resolution | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:GraphTe` |
| `LEX_ADMIN__TENANCY__ENABLED` | bool | False | Enable tenant-aware collection resolution in RAG pipeline | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGTen` |
| `LEX_ADMIN__TENANCY__ENABLED` | bool | False |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:TenancyConfig.tenancy.enabled` |
| `LEX_ADMIN__TENANCY__ENABLED` | bool | False | Enable tenant-aware collection name resolution | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Vector` |
| `LEX_ADMIN__TENANCY__HEADER_NAME` | str | "x-tenant-id" |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:TenancyConfig.tenancy.header_name` |
| `LEX_ADMIN__TENANCY__RESOLVER_KIND` | str | "templated" | Which ``TenantCollectionResolver`` to use. One of ``"templated"`` or ``"pinecone_namespace"``. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Vector` |
| `LEX_ADMIN__TENANCY__ROUTE_PREFIX_TEMPLATE` | str | "" |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:TenancyConfig.tenancy.route_prefix_tem` |
| `LEX_ADMIN__TENANCY__STRATEGY` | str | "node_property" | Which tenancy strategy to use. One of ``"node_property"`` or ``"graph_per_tenant"``. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:GraphTe` |
| `LEX_ADMIN__TENANCY__TEMPLATE` | str | "{logical}_t_{tenant}" | Collection name template for ``GRAPH_PER_TENANT`` strategy. Supports ``{logical}`` and ``{tenant}`` placeholders. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:GraphTe` |
| `LEX_ADMIN__TENANCY__TENANT_FIELD` | str | "tenant_id" |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:TenancyConfig.tenancy.tenant_field` |
| `LEX_ADMIN__TENANT_ID` | str  \| None | None | Optional tenant namespace | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/secrets/config.py:Secre` |
| `LEX_ADMIN__THEME` | str | "light" | Active UI theme. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ui/config.py:UIConfig.t` |
| `LEX_ADMIN__TIMEOUT` | TimeoutConfig | field(...) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Re` |
| `LEX_ADMIN__TIMEOUT__DEFAULT_TIMEOUT` | float | (complex) | Default timeout | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskTim` |
| `LEX_ADMIN__TIMEOUT__ENFORCE_TIMEOUT` | bool | True | Enforce timeouts | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskTim` |
| `LEX_ADMIN__TIMEOUT__MAX_TIMEOUT` | float | (complex) | Maximum allowed timeout | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskTim` |
| `LEX_ADMIN__TITLE` | str | "Lexigram Admin" |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminConfig.title` |
| `LEX_ADMIN__TOP_K` | int | 5 | Number of documents to retrieve | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGCon` |
| `LEX_ADMIN__TRACE_MAX_ATTRIBUTE_LENGTH` | int | 0 | Cap on string attribute values written to trace spans, in characters. 0 disables the cap. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/observability/config` |
| `LEX_ADMIN__TRACE_REDACTION_ENABLED` | bool | False | Redact secret-shaped keys (e.g. token, password, api_key) from trace span attributes and audit metadata. Strongly recomm | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/observability/config` |
| `LEX_ADMIN__TRACING_ENABLED` | bool | True | Enable distributed tracing | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/observability/config` |
| `LEX_ADMIN__TRACING__ENABLED` | bool | True | Enable tracing | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Traci` |
| `LEX_ADMIN__TRACING__ENABLED` | bool | False |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Traci` |
| `LEX_ADMIN__TRACING__MAX_ATTRIBUTES` | int | 128 | Max attributes per span | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Traci` |
| `LEX_ADMIN__TRACING__MAX_EVENTS` | int | 128 | Max events per span | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Traci` |
| `LEX_ADMIN__TRACING__MAX_LINKS` | int | 128 | Max links per span | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Traci` |
| `LEX_ADMIN__TRACING__MAX_SPANS` | int | (complex) | Max number of spans to keep in memory | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Traci` |
| `LEX_ADMIN__TRACING__MAX_TRACES_PER_SECOND` | int | 100 | Max traces to sample per second | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Traci` |
| `LEX_ADMIN__TRACING__PROPAGATION_FORMATS` | list[str] | (required) | Propagation format list | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Traci` |
| `LEX_ADMIN__TRACING__SAMPLE_RATE` | float | 1.0 | Sample rate (0.0 to 1.0) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Traci` |
| `LEX_ADMIN__TRACING__SAMPLE_RATE` | float | 1.0 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Traci` |
| `LEX_ADMIN__TRACING__SERVICE_NAME` | str | (complex) | Service name for traces | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Traci` |
| `LEX_ADMIN__TRACING__SERVICE_NAME` | str | "lexigram-graphql" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Traci` |
| `LEX_ADMIN__TRACING__TRACE_DATALOADERS` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Traci` |
| `LEX_ADMIN__TRACING__TRACE_RESOLVERS` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Traci` |
| `LEX_ADMIN__TRANSACTION_MIDDLEWARE__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Transa` |
| `LEX_ADMIN__TRANSACTION_MIDDLEWARE__ISOLATION_LEVEL` | str | "READ_COMMITTED" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Transa` |
| `LEX_ADMIN__TRANSACTION_MIDDLEWARE__TIMEOUT_SECONDS` | float | 30.0 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Transa` |
| `LEX_ADMIN__UI__CONTENT_MAX_WIDTH` | int  \| None | None |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminUIConfig.ui.content_max_width` |
| `LEX_ADMIN__UI__FAVICON_URL` | str  \| None | None |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminUIConfig.ui.favicon_url` |
| `LEX_ADMIN__UI__LOGO_URL` | str  \| None | None |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminUIConfig.ui.logo_url` |
| `LEX_ADMIN__UI__PRIMARY_COLOR` | str | "#6B7280" |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminUIConfig.ui.primary_color` |
| `LEX_ADMIN__UI__SIDEBAR_COLLAPSED_WIDTH` | int | 64 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminUIConfig.ui.sidebar_collapsed_wid` |
| `LEX_ADMIN__UI__SIDEBAR_WIDTH` | int | 256 |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminUIConfig.ui.sidebar_width` |
| `LEX_ADMIN__UI__THEME` | Literal['light', 'dark', 'system'] | "system" |  | `experimental/apps/lexigram-admin/src/lexigram/admin/config.py:AdminUIConfig.ui.theme` |
| `LEX_ADMIN__UPSERT_BATCH_SIZE` | int | (complex) | Number of vectors per upsert batch | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Vector` |
| `LEX_ADMIN__USE_HYBRID_SEARCH` | bool | True | Enable hybrid search (semantic + keyword) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGCon` |
| `LEX_ADMIN__VALIDATION_MIDDLEWARE__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Valida` |
| `LEX_ADMIN__VALIDATION_MIDDLEWARE__STRICT_MODE` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Valida` |
| `LEX_ADMIN__VECTOR` | Any  \| None | None | Vector store configuration | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/config.py:AIConfig.v` |
| `LEX_ADMIN__VECTOR_DIMENSION` | int | 1536 | Embedding vector dimension (1536 for OpenAI ada-002) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGCon` |
| `LEX_ADMIN__VECTOR_STORE_TYPE` | str | "pgvector" | Vector store backend (pgvector, chroma, qdrant, mock) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGCon` |
| `LEX_ADMIN__VERIFICATION_BATCH_SIZE` | int | (complex) | Entries to verify per verification run | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/audit/config.py:AuditCo` |
| `LEX_ADMIN__VERIFICATION_SCHEDULE` | str | (complex) | Cron expression for scheduled verification | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/audit/config.py:AuditCo` |
| `LEX_ADMIN__VERSION` | str | (complex) | Config version | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheCo` |
| `LEX_ADMIN__VERSION_SKEW_ALERTS_ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Events` |
| `LEX_ADMIN__WARNING_BEFORE_SECONDS` | float | (complex) | Seconds before expiry to warn | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/secrets/config.py:Secre` |
| `LEX_ADMIN__WEAVIATE__API_KEY` | SecretStr  \| None | None | Weaviate API key for authenticated clusters | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Weavia` |
| `LEX_ADMIN__WEAVIATE__GRPC_PORT` | int | 50051 | gRPC port for the Weaviate cluster | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Weavia` |
| `LEX_ADMIN__WEAVIATE__TIMEOUT` | float | (complex) | Request timeout in seconds | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Weavia` |
| `LEX_ADMIN__WEAVIATE__URL` | str | "http://localhost:8080" | Weaviate cluster URL (HTTP) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Weavia` |
| `LEX_ADMIN__WORKER__DEFAULT_TIMEOUT` | float | (complex) | Default timeout for tasks without an explicit timeout (seconds) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskWor` |
| `LEX_ADMIN__WORKER__ENFORCE_TIMEOUT` | bool | True | Whether to enforce timeouts on all tasks | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskWor` |
| `LEX_ADMIN__WORKER__MAX_CONCURRENT_TASKS` | int | (complex) | Maximum concurrent tasks per worker | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskWor` |
| `LEX_ADMIN__WORKER__MAX_TIMEOUT` | float | (complex) | Maximum allowed timeout for any task (seconds) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskWor` |
| `LEX_ADMIN__WORKER__POLL_INTERVAL` | float | (complex) | Interval between queue polls (seconds) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskWor` |
| `LEX_ADMIN__WORKER__SHUTDOWN_TIMEOUT` | float | (complex) | Timeout for graceful shutdown (seconds) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskWor` |
| `LEX_ADMIN__WORKER__WORKER_COUNT` | int | (complex) | Number of worker instances | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskWor` |
| `LEX_AI_AGENTS__DEFAULT_MAX_TOKENS` | int | 2048 | Default max tokens for LLM responses | `experimental/ai/lexigram-ai-agents/src/lexigram/ai/agents/config.py:AgentConfig.default_max_tokens` |
| `LEX_AI_AGENTS__DEFAULT_TEMPERATURE` | float | 0.7 | Default temperature for LLM calls | `experimental/ai/lexigram-ai-agents/src/lexigram/ai/agents/config.py:AgentConfig.default_temperature` |
| `LEX_AI_AGENTS__ENABLED` | bool | True | Enable the AI agents subsystem | `experimental/ai/lexigram-ai-agents/src/lexigram/ai/agents/config.py:AgentConfig.enabled` |
| `LEX_AI_AGENTS__ENABLE_METRICS` | bool | True | Enable Prometheus metrics | `experimental/ai/lexigram-ai-agents/src/lexigram/ai/agents/config.py:AgentConfig.enable_metrics` |
| `LEX_AI_AGENTS__ENABLE_TRACING` | bool | True | Enable OpenTelemetry tracing | `experimental/ai/lexigram-ai-agents/src/lexigram/ai/agents/config.py:AgentConfig.enable_tracing` |
| `LEX_AI_AGENTS__MAX_ITERATIONS` | int | 10 | Maximum reasoning iterations per execution | `experimental/ai/lexigram-ai-agents/src/lexigram/ai/agents/config.py:AgentConfig.max_iterations` |
| `LEX_AI_AGENTS__TOOL_MAX_RETRIES` | int | 3 | Number of retries for transient tool execution errors (ConnectionError, TimeoutError, OSError) | `experimental/ai/lexigram-ai-agents/src/lexigram/ai/agents/config.py:AgentConfig.tool_max_retries` |
| `LEX_AI_EVALUATION__DEFAULT_SEED` | int  \| None | None | Default seed for reproducible experiment runs | `experimental/ai/lexigram-ai-evaluation/src/lexigram/ai/evaluation/config.py:EvaluationConfig.default` |
| `LEX_AI_EVALUATION__DEFAULT_THRESHOLD` | float | 0.8 | Default score threshold for passing evaluations | `experimental/ai/lexigram-ai-evaluation/src/lexigram/ai/evaluation/config.py:EvaluationConfig.default` |
| `LEX_AI_EVALUATION__EMBEDDING_MODEL` | str | "text-embedding-3-small" | Model to use for embedding-based evaluations | `experimental/ai/lexigram-ai-evaluation/src/lexigram/ai/evaluation/config.py:EvaluationConfig.embeddi` |
| `LEX_AI_EVALUATION__ENABLED` | bool | True | Enable the AI evaluation subsystem | `experimental/ai/lexigram-ai-evaluation/src/lexigram/ai/evaluation/config.py:EvaluationConfig.enabled` |
| `LEX_AI_EVALUATION__EXPERIMENT_DIR` | str  \| None | None | Base directory for experiment tracking and checkpoint artifacts | `experimental/ai/lexigram-ai-evaluation/src/lexigram/ai/evaluation/config.py:EvaluationConfig.experim` |
| `LEX_AI_EVALUATION__INCLUDE_METADATA` | bool | True | Whether to include metadata in run reports | `experimental/ai/lexigram-ai-evaluation/src/lexigram/ai/evaluation/config.py:EvaluationConfig.include` |
| `LEX_AI_EVALUATION__MAX_RETRIES` | int | 3 | Maximum retries for failed evaluations | `experimental/ai/lexigram-ai-evaluation/src/lexigram/ai/evaluation/config.py:EvaluationConfig.max_ret` |
| `LEX_AI_EVALUATION__MAX_SAMPLES` | int  \| None | None | Maximum number of samples per evaluation run | `experimental/ai/lexigram-ai-evaluation/src/lexigram/ai/evaluation/config.py:EvaluationConfig.max_sam` |
| `LEX_AI_EVALUATION__TIMEOUT_SECONDS` | int | 30 | Timeout for evaluation execution in seconds | `experimental/ai/lexigram-ai-evaluation/src/lexigram/ai/evaluation/config.py:EvaluationConfig.timeout` |
| `LEX_AI_FEEDBACK__ASYNC_PROCESSING` | bool | True | Process feedback handlers asynchronously in the background | `experimental/ai/lexigram-ai-feedback/src/lexigram/ai/feedback/config.py:FeedbackConfig.async_process` |
| `LEX_AI_FEEDBACK__ENABLED` | bool | True | Master on/off switch for all feedback collection | `experimental/ai/lexigram-ai-feedback/src/lexigram/ai/feedback/config.py:FeedbackConfig.enabled` |
| `LEX_AI_FEEDBACK__STORE_RAW_PAYLOADS` | bool | False | Persist raw incoming feedback payloads for auditing | `experimental/ai/lexigram-ai-feedback/src/lexigram/ai/feedback/config.py:FeedbackConfig.store_raw_pay` |
| `LEX_AI_GOVERNANCE__ENABLED` | bool | True | Enable AI governance | `experimental/ai/lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.enabled` |
| `LEX_AI_GOVERNANCE__ENFORCE_BUDGET` | bool | True | Enforce budget limits | `experimental/ai/lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.enforce` |
| `LEX_AI_GOVERNANCE__FAIL_OPEN_ON_PERSISTENCE_ERROR` | bool | False | Allow requests when the persistence backend is unavailable. When False (default, fail-closed), a persistence failure (e. | `experimental/ai/lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.fail_op` |
| `LEX_AI_GOVERNANCE__MAX_REQUEST_COST` | float  \| None | None | Maximum cost in dollars for a single request. Requests with an estimated cost above this threshold are rejected before t | `experimental/ai/lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.max_req` |
| `LEX_AI_GOVERNANCE__MAX_TOKENS_PER_REQUEST` | int  \| None | None | Max tokens per request | `experimental/ai/lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.max_tok` |
| `LEX_AI_GOVERNANCE__MODEL_ALLOWLIST` | dict[str, list[str]] | (required) | Per-user/role model allowlist. Keys are user IDs or role names; values are lists of allowed model patterns (supports glo | `experimental/ai/lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.model_a` |
| `LEX_AI_GOVERNANCE__MODEL_DENYLIST` | dict[str, list[str]] | (required) | Per-user/role model denylist. Keys are user IDs or role names; values are lists of denied model patterns (supports glob  | `experimental/ai/lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.model_d` |
| `LEX_AI_GOVERNANCE__MONTHLY_BUDGET` | float  \| None | None | Monthly budget in dollars | `experimental/ai/lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.monthly` |
| `LEX_AI_GOVERNANCE__RESOURCE_UNITS` | list | (required) | Resource units this governance instance tracks. Per-tenant limits are configured via TenantConfigService overrides. | `experimental/ai/lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.resourc` |
| `LEX_AI_GOVERNANCE__RESTRICTED_MODELS` | list[str] | (required) | List of restricted models | `experimental/ai/lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.restric` |
| `LEX_AI_GOVERNANCE__RPM_LIMIT` | int  \| None | None | Requests Per Minute limit | `experimental/ai/lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.rpm_lim` |
| `LEX_AI_GOVERNANCE__SOFT_LIMIT_PCT` | float  \| None | None | Fraction of monthly_budget at which to emit a soft-limit warning (e.g. 0.8 = warn at 80%). No hard block is applied at t | `experimental/ai/lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.soft_li` |
| `LEX_AI_GOVERNANCE__TPM_LIMIT` | int  \| None | None | Tokens Per Minute limit | `experimental/ai/lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.tpm_lim` |
| `LEX_AI_GUARD__ENABLED` | bool | True |  | `experimental/ai/lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.enabled` |
| `LEX_AI_GUARD__ENABLE_LLM_GUARDS` | bool | False |  | `experimental/ai/lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.enable_llm_guards` |
| `LEX_AI_GUARD__GUARD_MODEL` | str | "gpt-4o-mini" |  | `experimental/ai/lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.guard_model` |
| `LEX_AI_GUARD__INJECTION_ACTION` | str | "block" |  | `experimental/ai/lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.injection_action` |
| `LEX_AI_GUARD__INJECTION_DETECTION` | bool | True |  | `experimental/ai/lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.injection_detection` |
| `LEX_AI_GUARD__LENGTH_ACTION` | str | "block" |  | `experimental/ai/lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.length_action` |
| `LEX_AI_GUARD__LLM_GUARD_FAIL_OPEN` | bool | False |  | `experimental/ai/lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.llm_guard_fail_open` |
| `LEX_AI_GUARD__LLM_GUARD_THRESHOLD` | float | 0.7 |  | `experimental/ai/lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.llm_guard_threshold` |
| `LEX_AI_GUARD__MAX_INPUT_CHARS` | int | 0 |  | `experimental/ai/lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.max_input_chars` |
| `LEX_AI_GUARD__MAX_OUTPUT_CHARS` | int | 0 |  | `experimental/ai/lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.max_output_chars` |
| `LEX_AI_GUARD__PARALLEL_EXECUTION` | bool | False |  | `experimental/ai/lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.parallel_execution` |
| `LEX_AI_GUARD__PII_ACTION` | str | "redact" |  | `experimental/ai/lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.pii_action` |
| `LEX_AI_GUARD__PII_DETECTION` | bool | True |  | `experimental/ai/lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.pii_detection` |
| `LEX_AI_GUARD__PII_ENTITIES` | list[str] | field(...) |  | `experimental/ai/lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.pii_entities` |
| `LEX_AI_GUARD__PII_REDACTION_OUTPUT` | bool | True |  | `experimental/ai/lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.pii_redaction_output` |
| `LEX_AI_GUARD__RESTRICTED_TOPICS` | list[str] | field(...) |  | `experimental/ai/lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.restricted_topics` |
| `LEX_AI_GUARD__SENSITIVITY_LEVEL` | str | "medium" |  | `experimental/ai/lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.sensitivity_level` |
| `LEX_AI_MCP__ALLOW_UNAUTHENTICATED` | bool | False |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.allow_unauthenticated` |
| `LEX_AI_MCP__CLIENT_STDIO_COMMAND` | list[str] | field(...) |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.client_stdio_command` |
| `LEX_AI_MCP__CLIENT_URL` | str  \| None | None |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.client_url` |
| `LEX_AI_MCP__CONNECTORS__FILESYSTEM__READ_ONLY` | bool | False |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:FilesystemConnectorConfig.connectors.f` |
| `LEX_AI_MCP__CONNECTORS__FILESYSTEM__ROOT_DIR` | str | "" |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:FilesystemConnectorConfig.connectors.f` |
| `LEX_AI_MCP__CONNECTORS__GITHUB__API_URL` | str | "https://api.github.com" |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:GitHubConnectorConfig.connectors.githu` |
| `LEX_AI_MCP__CONNECTORS__GITHUB__TOKEN` | str | "" |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:GitHubConnectorConfig.connectors.githu` |
| `LEX_AI_MCP__CONNECTORS__GOOGLE_DRIVE__IMPERSONATED_EMAIL` | str | "" |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:GoogleDriveConnectorConfig.connectors.` |
| `LEX_AI_MCP__CONNECTORS__GOOGLE_DRIVE__SERVICE_ACCOUNT_JSON` | str | "" |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:GoogleDriveConnectorConfig.connectors.` |
| `LEX_AI_MCP__CONNECTORS__SLACK__BOT_TOKEN` | str | "" |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:SlackConnectorConfig.connectors.slack.` |
| `LEX_AI_MCP__CONNECTORS__SLACK__MAX_MESSAGES` | int | 100 |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:SlackConnectorConfig.connectors.slack.` |
| `LEX_AI_MCP__CONNECTORS__SQL__ALLOWED_TABLES` | list[str] | field(...) |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:SQLConnectorConfig.connectors.sql.allo` |
| `LEX_AI_MCP__CONNECTORS__SQL__DSN` | str | "" |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:SQLConnectorConfig.connectors.sql.dsn` |
| `LEX_AI_MCP__CONNECTORS__SQL__READ_ONLY` | bool | True |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:SQLConnectorConfig.connectors.sql.read` |
| `LEX_AI_MCP__CONNECTORS__WEB_FETCH__ENABLED` | bool | False |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:WebFetchConnectorConfig.connectors.web` |
| `LEX_AI_MCP__CONNECTORS__WEB_FETCH__MAX_CONTENT_BYTES` | int | (complex) |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:WebFetchConnectorConfig.connectors.web` |
| `LEX_AI_MCP__CONNECTORS__WEB_FETCH__USER_AGENT` | str | "lexigram-mcp/1.0" |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:WebFetchConnectorConfig.connectors.web` |
| `LEX_AI_MCP__CONNECTORS__WEB_SEARCH__API_KEY` | str | "" |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:WebSearchConnectorConfig.connectors.we` |
| `LEX_AI_MCP__CONNECTORS__WEB_SEARCH__MAX_RESULTS` | int | 10 |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:WebSearchConnectorConfig.connectors.we` |
| `LEX_AI_MCP__CONNECTORS__WEB_SEARCH__PROVIDER` | str | "brave" |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:WebSearchConnectorConfig.connectors.we` |
| `LEX_AI_MCP__CORS_ORIGINS` | list[str] | field(...) |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.cors_origins` |
| `LEX_AI_MCP__ENABLED` | bool | True | Enable the MCP server subsystem | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.enabled` |
| `LEX_AI_MCP__ENABLE_SSE` | bool | True |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.enable_sse` |
| `LEX_AI_MCP__HOST` | str | "0.0.0.0" |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.host` |
| `LEX_AI_MCP__MAX_REQUEST_SIZE` | int | (complex) |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.max_request_size` |
| `LEX_AI_MCP__PATH` | str | "/mcp" |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.path` |
| `LEX_AI_MCP__PORT` | int | 8080 |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.port` |
| `LEX_AI_MCP__REQUEST_TIMEOUT` | float | 30.0 |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.request_timeout` |
| `LEX_AI_MCP__SERVER_NAME` | str | "lexigram-mcp" |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.server_name` |
| `LEX_AI_MCP__SERVER_VERSION` | str | "1.0.0" |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.server_version` |
| `LEX_AI_MCP__STDIO_MODE` | bool | False |  | `experimental/ai/lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.stdio_mode` |
| `LEX_AI_MEMORY__CONSOLIDATION__AGE_THRESHOLD_HOURS` | float | (complex) | Minimum entry age (hours) before it can be consolidated | `experimental/ai/lexigram-ai-memory/src/lexigram/ai/memory/config.py:ConsolidationConfig.consolidatio` |
| `LEX_AI_MEMORY__CONSOLIDATION__BATCH_SIZE` | int | (complex) | Maximum entries processed per consolidation pass | `experimental/ai/lexigram-ai-memory/src/lexigram/ai/memory/config.py:ConsolidationConfig.consolidatio` |
| `LEX_AI_MEMORY__CONSOLIDATION__ENABLED` | bool | True | Whether automatic background consolidation is active | `experimental/ai/lexigram-ai-memory/src/lexigram/ai/memory/config.py:ConsolidationConfig.consolidatio` |
| `LEX_AI_MEMORY__CONSOLIDATION__IMPORTANCE_PRUNE_THRESHOLD` | float | (complex) | Entries below this importance score are eligible for pruning | `experimental/ai/lexigram-ai-memory/src/lexigram/ai/memory/config.py:ConsolidationConfig.consolidatio` |
| `LEX_AI_MEMORY__CONSOLIDATION__INTERVAL_SECONDS` | float | (complex) | How often to run a consolidation pass (seconds) | `experimental/ai/lexigram-ai-memory/src/lexigram/ai/memory/config.py:ConsolidationConfig.consolidatio` |
| `LEX_AI_MEMORY__DEFAULT_BACKEND` | str | (complex) | Backend type to use ('in_memory', 'cache', 'database', 'vector') | `experimental/ai/lexigram-ai-memory/src/lexigram/ai/memory/config.py:MemoryConfig.default_backend` |
| `LEX_AI_MEMORY__ENABLED` | bool | True | Enable the AI memory subsystem | `experimental/ai/lexigram-ai-memory/src/lexigram/ai/memory/config.py:MemoryConfig.enabled` |
| `LEX_AI_MEMORY__EPISODIC__DEFAULT_TOP_K` | int | (complex) | Default number of episodes to retrieve | `experimental/ai/lexigram-ai-memory/src/lexigram/ai/memory/config.py:EpisodicMemoryConfig.episodic.de` |
| `LEX_AI_MEMORY__EPISODIC__IMPORTANCE_WEIGHT` | float | (complex) | Weight applied to entry importance during scoring | `experimental/ai/lexigram-ai-memory/src/lexigram/ai/memory/config.py:EpisodicMemoryConfig.episodic.im` |
| `LEX_AI_MEMORY__EPISODIC__RECENCY_WEIGHT` | float | (complex) | Weight applied to temporal recency during scoring | `experimental/ai/lexigram-ai-memory/src/lexigram/ai/memory/config.py:EpisodicMemoryConfig.episodic.re` |
| `LEX_AI_MEMORY__EPISODIC__RELEVANCE_WEIGHT` | float | (complex) | Weight applied to semantic similarity during scoring | `experimental/ai/lexigram-ai-memory/src/lexigram/ai/memory/config.py:EpisodicMemoryConfig.episodic.re` |
| `LEX_AI_MEMORY__EPISODIC__TTL_SECONDS` | int | (complex) | Time-to-live for entries in seconds (0 = never expire) | `experimental/ai/lexigram-ai-memory/src/lexigram/ai/memory/config.py:EpisodicMemoryConfig.episodic.tt` |
| `LEX_AI_MEMORY__SEMANTIC__MAX_FACTS_PER_ENTITY` | int | (complex) | Hard cap on stored facts per entity | `experimental/ai/lexigram-ai-memory/src/lexigram/ai/memory/config.py:SemanticMemoryConfig.semantic.ma` |
| `LEX_AI_MEMORY__SEMANTIC__MIN_CONFIDENCE` | float | (complex) | Minimum confidence score required to store a fact | `experimental/ai/lexigram-ai-memory/src/lexigram/ai/memory/config.py:SemanticMemoryConfig.semantic.mi` |
| `LEX_AI_MEMORY__TTL_SECONDS` | int | (complex) | Default entry TTL in seconds (0 = never expire) | `experimental/ai/lexigram-ai-memory/src/lexigram/ai/memory/config.py:MemoryConfig.ttl_seconds` |
| `LEX_AI_MEMORY__WORKING__EPISODIC_FRACTION` | float | (complex) | Fraction of remaining budget for episodic recall | `experimental/ai/lexigram-ai-memory/src/lexigram/ai/memory/config.py:WorkingMemoryConfig.working.epis` |
| `LEX_AI_MEMORY__WORKING__MAX_RECENT_TURNS` | int | (complex) | Hard cap on recent turns regardless of budget | `experimental/ai/lexigram-ai-memory/src/lexigram/ai/memory/config.py:WorkingMemoryConfig.working.max_` |
| `LEX_AI_MEMORY__WORKING__RECENT_TURNS_FRACTION` | float | (complex) | Fraction of remaining budget for recent turns | `experimental/ai/lexigram-ai-memory/src/lexigram/ai/memory/config.py:WorkingMemoryConfig.working.rece` |
| `LEX_AI_MEMORY__WORKING__SEMANTIC_FRACTION` | float | (complex) | Fraction of remaining budget for semantic facts | `experimental/ai/lexigram-ai-memory/src/lexigram/ai/memory/config.py:WorkingMemoryConfig.working.sema` |
| `LEX_AI_MEMORY__WORKING__SYSTEM_PROMPT_TOKENS` | int | (complex) | Fixed token allocation for system prompt | `experimental/ai/lexigram-ai-memory/src/lexigram/ai/memory/config.py:WorkingMemoryConfig.working.syst` |
| `LEX_AI_MEMORY__WORKING__TOOL_DESCRIPTIONS_FRACTION` | float | (complex) | Fraction of remaining budget for tool descriptions | `experimental/ai/lexigram-ai-memory/src/lexigram/ai/memory/config.py:WorkingMemoryConfig.working.tool` |
| `LEX_AI_OBSERVABILITY__ENABLED` | bool | True | Master on/off switch for all observability | `experimental/ai/lexigram-ai-observability/src/lexigram/ai/observability/config.py:ObservabilityConfi` |
| `LEX_AI_OBSERVABILITY__HEALTH_CHECKS_ENABLED` | bool | True | Enable background health checking for AI components | `experimental/ai/lexigram-ai-observability/src/lexigram/ai/observability/config.py:ObservabilityConfi` |
| `LEX_AI_OBSERVABILITY__METRICS_ENABLED` | bool | True | Enable metrics collection | `experimental/ai/lexigram-ai-observability/src/lexigram/ai/observability/config.py:ObservabilityConfi` |
| `LEX_AI_OBSERVABILITY__TRACE_MAX_ATTRIBUTE_LENGTH` | int | 0 | Cap on string attribute values written to trace spans, in characters. 0 disables the cap. | `experimental/ai/lexigram-ai-observability/src/lexigram/ai/observability/config.py:ObservabilityConfi` |
| `LEX_AI_OBSERVABILITY__TRACE_REDACTION_ENABLED` | bool | False | Redact secret-shaped keys (e.g. token, password, api_key) from trace span attributes and audit metadata. Strongly recomm | `experimental/ai/lexigram-ai-observability/src/lexigram/ai/observability/config.py:ObservabilityConfi` |
| `LEX_AI_OBSERVABILITY__TRACING_ENABLED` | bool | True | Enable distributed tracing | `experimental/ai/lexigram-ai-observability/src/lexigram/ai/observability/config.py:ObservabilityConfi` |
| `LEX_AI_PROMPT__DEFAULT_FORMAT` | RenderFormat | DEFAULT_RENDER_FORMAT |  | `experimental/ai/lexigram-ai-prompt/src/lexigram/ai/prompt/config.py:PromptConfig.default_format` |
| `LEX_AI_PROMPT__ENABLED` | bool | True | Enable the AI prompt subsystem | `experimental/ai/lexigram-ai-prompt/src/lexigram/ai/prompt/config.py:PromptConfig.enabled` |
| `LEX_AI_PROMPT__MAX_VARIABLE_LENGTH` | int | 0 |  | `experimental/ai/lexigram-ai-prompt/src/lexigram/ai/prompt/config.py:PromptConfig.max_variable_length` |
| `LEX_AI_PROMPT__SANITIZE_INPUTS` | bool | True |  | `experimental/ai/lexigram-ai-prompt/src/lexigram/ai/prompt/config.py:PromptConfig.sanitize_inputs` |
| `LEX_AI_PROMPT__STRICT_SANITIZER` | bool | True |  | `experimental/ai/lexigram-ai-prompt/src/lexigram/ai/prompt/config.py:PromptConfig.strict_sanitizer` |
| `LEX_AI_RAG__CACHE_TTL` | int | 3600 | Cache TTL in seconds (default: 1 hour) | `experimental/ai/lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.cache_ttl` |
| `LEX_AI_RAG__CHUNKING_STRATEGY` | str | "recursive" | Chunking strategy (recursive, semantic, token) | `experimental/ai/lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.chunking_strategy` |
| `LEX_AI_RAG__CHUNK_OVERLAP` | int | 50 | Overlap between consecutive chunks | `experimental/ai/lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.chunk_overlap` |
| `LEX_AI_RAG__CHUNK_SIZE` | int | 512 | Text chunk size in tokens | `experimental/ai/lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.chunk_size` |
| `LEX_AI_RAG__CITATION_STYLE` | str | "inline" | Citation style (inline, footnote, numbered) | `experimental/ai/lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.citation_style` |
| `LEX_AI_RAG__COLLECTION_NAME` | str | "default" | Collection/index name for vector store | `experimental/ai/lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.collection_name` |
| `LEX_AI_RAG__EMBEDDING_MODEL` | str  \| None | None | Embedding model identifier. Must be set explicitly — no vendor-specific default. | `experimental/ai/lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.embedding_model` |
| `LEX_AI_RAG__EMBEDDING_PROVIDER` | str | "openai" | Embedding provider (openai, cohere, etc.) | `experimental/ai/lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.embedding_provider` |
| `LEX_AI_RAG__ENABLED` | bool | True | Enable the RAG pipeline | `experimental/ai/lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.enabled` |
| `LEX_AI_RAG__ENABLE_CACHING` | bool | True | Enable caching for RAG queries | `experimental/ai/lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.enable_caching` |
| `LEX_AI_RAG__ENABLE_CITATIONS` | bool | True | Include source citations in responses | `experimental/ai/lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.enable_citations` |
| `LEX_AI_RAG__ENABLE_HALLUCINATION_DETECTION` | bool | True | Enable hallucination detection for AI responses | `experimental/ai/lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.enable_hallucination_detecti` |
| `LEX_AI_RAG__ENABLE_HYDE` | bool | False | Enable HyDE (Hypothetical Document Embeddings) | `experimental/ai/lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.enable_hyde` |
| `LEX_AI_RAG__ENABLE_QUERY_EXPANSION` | bool | True | Enable query expansion techniques | `experimental/ai/lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.enable_query_expansion` |
| `LEX_AI_RAG__MIN_CITATION_CONFIDENCE` | float | 0.6 | Minimum confidence for citation inclusion | `experimental/ai/lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.min_citation_confidence` |
| `LEX_AI_RAG__PERSIST_DIRECTORY` | str  \| None | None | Local directory path for vector store persistence (e.g. Chroma) | `experimental/ai/lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.persist_directory` |
| `LEX_AI_RAG__SIMILARITY_THRESHOLD` | float | 0.7 | Minimum similarity score threshold | `experimental/ai/lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.similarity_threshold` |
| `LEX_AI_RAG__SYNTHESIS_STRATEGY` | str | "hybrid" | Synthesis strategy (direct, extractive, abstractive, hybrid) | `experimental/ai/lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.synthesis_strategy` |
| `LEX_AI_RAG__TENANCY__ENABLED` | bool | False | Enable tenant-aware collection resolution in RAG pipeline | `experimental/ai/lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGTenancyConfig.tenancy.enabled` |
| `LEX_AI_RAG__TOP_K` | int | 5 | Number of documents to retrieve | `experimental/ai/lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.top_k` |
| `LEX_AI_RAG__USE_HYBRID_SEARCH` | bool | True | Enable hybrid search (semantic + keyword) | `experimental/ai/lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.use_hybrid_search` |
| `LEX_AI_RAG__VECTOR_DIMENSION` | int | 1536 | Embedding vector dimension (1536 for OpenAI ada-002) | `experimental/ai/lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.vector_dimension` |
| `LEX_AI_RAG__VECTOR_STORE_TYPE` | str | "pgvector" | Vector store backend (pgvector, chroma, qdrant, mock) | `experimental/ai/lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.vector_store_type` |
| `LEX_AI_SESSION__AUTO_CHECKPOINT_INTERVAL` | int  \| None | (complex) | Checkpoint every N turns; None to disable | `experimental/ai/lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.auto_checkpoint_` |
| `LEX_AI_SESSION__BACKEND` | str | (complex) | Persistence backend (in_memory, cache, database) | `experimental/ai/lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.backend` |
| `LEX_AI_SESSION__CLEANUP_INTERVAL_S` | int | (complex) | How often the cleanup scheduler sweeps for expired sessions | `experimental/ai/lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.cleanup_interval` |
| `LEX_AI_SESSION__CONSOLIDATE_ON_CLOSE` | bool | (complex) | Whether to trigger memory consolidation on session close | `experimental/ai/lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.consolidate_on_c` |
| `LEX_AI_SESSION__COOKIE_NAME` | str  \| None | (complex) | Cookie name for web session ID; None disables cookies | `experimental/ai/lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.cookie_name` |
| `LEX_AI_SESSION__DEFAULT_SYSTEM_PROMPT` | str  \| None | None | System prompt injected into every new session | `experimental/ai/lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.default_system_p` |
| `LEX_AI_SESSION__DEFAULT_TURN_STRATEGY` | str | (complex) | Default turn-selection strategy (round_robin, priority, llm_directed) | `experimental/ai/lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.default_turn_str` |
| `LEX_AI_SESSION__ENABLED` | bool | True | Enable the AI session subsystem | `experimental/ai/lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.enabled` |
| `LEX_AI_SESSION__HEADER_NAME` | str | (complex) | HTTP header name for session ID pass-through | `experimental/ai/lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.header_name` |
| `LEX_AI_SESSION__MAX_AGENTS_PER_GROUP` | int | (complex) | Maximum agents in a multi-agent group session | `experimental/ai/lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.max_agents_per_g` |
| `LEX_AI_SESSION__MAX_BRANCHES_PER_SESSION` | int | (complex) | Maximum forked branches per session | `experimental/ai/lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.max_branches_per` |
| `LEX_AI_SESSION__MAX_CHECKPOINTS_PER_SESSION` | int | (complex) | Maximum retained checkpoints per session | `experimental/ai/lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.max_checkpoints_` |
| `LEX_AI_SESSION__MAX_SESSIONS_PER_USER` | int | (complex) | Maximum concurrent sessions per user | `experimental/ai/lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.max_sessions_per` |
| `LEX_AI_SESSION__MAX_TURNS_PER_SESSION` | int | (complex) | Hard cap on turns before the session is closed | `experimental/ai/lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.max_turns_per_se` |
| `LEX_AI_SESSION__NAME` | str | "ai-session" | Logical name used for DI registration keys | `experimental/ai/lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.name` |
| `LEX_AI_SESSION__SESSION_TTL` | int | (complex) | Maximum age of a session in seconds (0 to disable) | `experimental/ai/lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.session_ttl` |
| `LEX_AI_SKILLS__ALLOWED_SCRIPT_TYPES` | list[str] | (required) | Allowed script types (py, sh, js) | `experimental/ai/lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.allowed_script_type` |
| `LEX_AI_SKILLS__AUTO_DISCOVER` | bool | (complex) | Whether to auto-scan packages for skills on boot | `experimental/ai/lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.auto_discover` |
| `LEX_AI_SKILLS__BUILTIN_SKILLS` | list[str] | (required) | Names of built-in skills to register | `experimental/ai/lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.builtin_skills` |
| `LEX_AI_SKILLS__CACHE_BACKEND` | str | (complex) | Which cache backend to use (in_memory, cache) | `experimental/ai/lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.cache_backend` |
| `LEX_AI_SKILLS__CACHE_ENABLED` | bool | (complex) | Whether result caching is globally enabled | `experimental/ai/lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.cache_enabled` |
| `LEX_AI_SKILLS__CACHE_TTL_SECONDS` | int | (complex) | Default TTL for cached skill results (seconds) | `experimental/ai/lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.cache_ttl_seconds` |
| `LEX_AI_SKILLS__DEFAULT_TIMEOUT_SECONDS` | float | (complex) | Default execution timeout per skill (seconds) | `experimental/ai/lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.default_timeout_sec` |
| `LEX_AI_SKILLS__ENABLED_DIRECTORIES` | list[str] | (required) | Which skill directories to enable (claude_code, opencode, cursor, etc.) | `experimental/ai/lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.enabled_directories` |
| `LEX_AI_SKILLS__ENABLE_BUILTIN` | bool | (complex) | Whether built-in skills are registered on boot | `experimental/ai/lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.enable_builtin` |
| `LEX_AI_SKILLS__ENABLE_SKILL_SOURCES` | bool | True | Whether to scan for external skill sources on boot | `experimental/ai/lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.enable_skill_source` |
| `LEX_AI_SKILLS__ENFORCE_PERMISSIONS` | bool | (complex) | Whether permission checks are enforced | `experimental/ai/lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.enforce_permissions` |
| `LEX_AI_SKILLS__LAZY_LOAD_CONTEXT` | bool | (complex) | Whether to lazily load skill context files | `experimental/ai/lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.lazy_load_context` |
| `LEX_AI_SKILLS__MAX_CONCURRENT_EXECUTIONS` | int | (complex) | Semaphore cap on concurrent skill executions | `experimental/ai/lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.max_concurrent_exec` |
| `LEX_AI_SKILLS__MAX_RETRIES` | int | (complex) | Default maximum retry attempts for skill execution | `experimental/ai/lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.max_retries` |
| `LEX_AI_SKILLS__NAME` | str | "ai-skills" | Logical name used for DI registration keys | `experimental/ai/lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.name` |
| `LEX_AI_SKILLS__SCAN_PACKAGES` | list[str] | (required) | Fully-qualified package names to scan for skills | `experimental/ai/lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.scan_packages` |
| `LEX_AI_SKILLS__SCRIPT_TIMEOUT_SECONDS` | int | (complex) | Timeout for skill script execution (seconds) | `experimental/ai/lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.script_timeout_seco` |
| `LEX_AI_SKILLS__SKILL_PATHS` | list[str] | (required) | Paths to scan for skills (SKILL.md folders) | `experimental/ai/lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.skill_paths` |
| `LEX_AI_WORKERS__BATCH_EMBEDDING_CONCURRENCY` | int | 3 | Concurrency level for batch embedding execution | `experimental/ai/lexigram-ai-workers/src/lexigram/ai/workers/config.py:WorkersConfig.batch_embedding_` |
| `LEX_AI_WORKERS__DLQ_CHECK_INTERVAL` | int | 60 | Interval in seconds for DLQ recovery sweeps | `experimental/ai/lexigram-ai-workers/src/lexigram/ai/workers/config.py:WorkersConfig.dlq_check_interv` |
| `LEX_AI_WORKERS__DOCUMENT_INGESTION_CONCURRENCY` | int | 3 | Concurrency level for document parsing and chunking | `experimental/ai/lexigram-ai-workers/src/lexigram/ai/workers/config.py:WorkersConfig.document_ingesti` |
| `LEX_AI_WORKERS__ENABLED` | bool | True | Master on/off switch for all background workers | `experimental/ai/lexigram-ai-workers/src/lexigram/ai/workers/config.py:WorkersConfig.enabled` |
| `LEX_AI_WORKERS__ENABLE_MAINTENANCE` | bool | True | Enable vector store and cache maintenance tasks | `experimental/ai/lexigram-ai-workers/src/lexigram/ai/workers/config.py:WorkersConfig.enable_maintenan` |
| `LEX_AI__ENABLED` | bool | True | Enable AI features | `experimental/ai/lexigram-ai/src/lexigram/ai/config.py:AIConfig.enabled` |
| `LEX_AI__GOVERNANCE` | Any | (required) | AI governance configuration | `experimental/ai/lexigram-ai/src/lexigram/ai/config.py:AIConfig.governance` |
| `LEX_AI__LLM` | Any  \| None | None | LLM configuration (optional) | `experimental/ai/lexigram-ai/src/lexigram/ai/config.py:AIConfig.llm` |
| `LEX_AI__NAME` | str | "ai" | Configuration name | `experimental/ai/lexigram-ai/src/lexigram/ai/config.py:AIConfig.name` |
| `LEX_AI__OBSERVABILITY` | Any | (required) | AI observability configuration (tracing and metrics) | `experimental/ai/lexigram-ai/src/lexigram/ai/config.py:AIConfig.observability` |
| `LEX_AI__RAG` | Any  \| None | None | RAG pipeline configuration (optional) | `experimental/ai/lexigram-ai/src/lexigram/ai/config.py:AIConfig.rag` |
| `LEX_AI__SUBSYSTEMS` | dict[str, dict[str, Any]] | (required) | Dynamic configuration for third-party AI subsystems discovered via entry points.  Keys are subsystem names; values are t | `experimental/ai/lexigram-ai/src/lexigram/ai/config.py:AIConfig.subsystems` |
| `LEX_AI__VECTOR` | Any  \| None | None | Vector store configuration | `experimental/ai/lexigram-ai/src/lexigram/ai/config.py:AIConfig.vector` |
| `LEX_AUDIT__ENABLE_ADMIN` | bool | True | Whether to register the AuditAdminContributor | `packages/lexigram-audit/src/lexigram/audit/config.py:AuditConfig.enable_admin` |
| `LEX_AUDIT__HMAC_KEY` | bytes  \| None | None | HMAC key for checksum computation | `packages/lexigram-audit/src/lexigram/audit/config.py:AuditConfig.hmac_key` |
| `LEX_AUDIT__RETENTION_POLICY` | RetentionPolicy | (required) | Retention rules | `packages/lexigram-audit/src/lexigram/audit/config.py:AuditConfig.retention_policy` |
| `LEX_AUDIT__STORE_BACKEND` | str | (complex) | Backend type — 'sql' or 'memory' | `packages/lexigram-audit/src/lexigram/audit/config.py:AuditConfig.store_backend` |
| `LEX_AUDIT__TABLE_NAME` | str | (complex) | SQL table name for the unified audit store | `packages/lexigram-audit/src/lexigram/audit/config.py:AuditConfig.table_name` |
| `LEX_AUDIT__VERIFICATION_BATCH_SIZE` | int | (complex) | Entries to verify per verification run | `packages/lexigram-audit/src/lexigram/audit/config.py:AuditConfig.verification_batch_size` |
| `LEX_AUDIT__VERIFICATION_SCHEDULE` | str | (complex) | Cron expression for scheduled verification | `packages/lexigram-audit/src/lexigram/audit/config.py:AuditConfig.verification_schedule` |
| `LEX_AUTH__ADMIN_EMAIL` | str  \| None | None | Initial admin email | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthConf` |
| `LEX_AUTH__ADMIN_EMAIL` | str  \| None | None | Initial admin email | `packages/lexigram-auth/src/lexigram/auth/config.py:AuthConfig.admin_email` |
| `LEX_AUTH__ADMIN_EMAIL` | str  \| None | None | Initial admin email | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthConfig` |
| `LEX_AUTH__ADMIN_PASSWORD` | str  \| None | None | Initial admin password | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthConf` |
| `LEX_AUTH__ADMIN_PASSWORD` | str  \| None | None | Initial admin password | `packages/lexigram-auth/src/lexigram/auth/config.py:AuthConfig.admin_password` |
| `LEX_AUTH__ADMIN_PASSWORD` | str  \| None | None | Initial admin password | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthConfig` |
| `LEX_AUTH__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthConf` |
| `LEX_AUTH__ENABLED` | bool | True |  | `packages/lexigram-auth/src/lexigram/auth/config.py:AuthConfig.enabled` |
| `LEX_AUTH__ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthConfig` |
| `LEX_AUTH__LOGIN_RATE_LIMIT` | str | "5/minute" | Default rate limit | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthConf` |
| `LEX_AUTH__LOGIN_RATE_LIMIT` | str | "5/minute" | Default rate limit | `packages/lexigram-auth/src/lexigram/auth/config.py:AuthConfig.login_rate_limit` |
| `LEX_AUTH__LOGIN_RATE_LIMIT` | str | "5/minute" | Default rate limit | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthConfig` |
| `LEX_AUTH__MAX_SESSIONS_PER_USER` | int  \| None | None | Maximum number of concurrent sessions allowed per user. ``None`` (the default) means unlimited.  When a positive integer | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthConf` |
| `LEX_AUTH__MAX_SESSIONS_PER_USER` | int  \| None | None | Maximum number of concurrent sessions allowed per user. ``None`` (the default) means unlimited.  When a positive integer | `packages/lexigram-auth/src/lexigram/auth/config.py:AuthConfig.max_sessions_per_user` |
| `LEX_AUTH__MAX_SESSIONS_PER_USER` | int  \| None | None | Maximum number of concurrent sessions allowed per user. ``None`` (the default) means unlimited.  When a positive integer | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthConfig` |
| `LEX_AUTH__MIDDLEWARE__BACKEND` | str | "session" | Auth backend type | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthMidd` |
| `LEX_AUTH__MIDDLEWARE__BACKEND` | str | "session" | Auth backend type | `packages/lexigram-auth/src/lexigram/auth/config.py:AuthMiddlewareConfig.middleware.backend` |
| `LEX_AUTH__MIDDLEWARE__BACKEND` | str | "session" | Auth backend type | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthMiddle` |
| `LEX_AUTH__MIDDLEWARE__EXCLUDE_PATHS` | list[str] | (required) | Paths excluded from auth | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthMidd` |
| `LEX_AUTH__MIDDLEWARE__EXCLUDE_PATHS` | list[str] | (required) | Paths excluded from auth | `packages/lexigram-auth/src/lexigram/auth/config.py:AuthMiddlewareConfig.middleware.exclude_paths` |
| `LEX_AUTH__MIDDLEWARE__EXCLUDE_PATHS` | list[str] | (required) | Paths excluded from auth | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthMiddle` |
| `LEX_AUTH__MIDDLEWARE__EXCLUDE_PREFIXES` | list[str] | (required) | Path prefixes excluded | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthMidd` |
| `LEX_AUTH__MIDDLEWARE__EXCLUDE_PREFIXES` | list[str] | (required) | Path prefixes excluded | `packages/lexigram-auth/src/lexigram/auth/config.py:AuthMiddlewareConfig.middleware.exclude_prefixes` |
| `LEX_AUTH__MIDDLEWARE__EXCLUDE_PREFIXES` | list[str] | (required) | Path prefixes excluded | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthMiddle` |
| `LEX_AUTH__MIDDLEWARE__HEADER_NAME` | str | "Authorization" | Header name for token | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthMidd` |
| `LEX_AUTH__MIDDLEWARE__HEADER_NAME` | str | "Authorization" | Header name for token | `packages/lexigram-auth/src/lexigram/auth/config.py:AuthMiddlewareConfig.middleware.header_name` |
| `LEX_AUTH__MIDDLEWARE__HEADER_NAME` | str | "Authorization" | Header name for token | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthMiddle` |
| `LEX_AUTH__MIDDLEWARE__LOGIN_RATE_LIMIT` | str | "5/minute" | Rate limit for auth endpoints | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthMidd` |
| `LEX_AUTH__MIDDLEWARE__LOGIN_RATE_LIMIT` | str | "5/minute" | Rate limit for auth endpoints | `packages/lexigram-auth/src/lexigram/auth/config.py:AuthMiddlewareConfig.middleware.login_rate_limit` |
| `LEX_AUTH__MIDDLEWARE__LOGIN_RATE_LIMIT` | str | "5/minute" | Rate limit for auth endpoints | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthMiddle` |
| `LEX_AUTH__MIDDLEWARE__LOGIN_URL` | str  \| None | None | URL to redirect for login | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthMidd` |
| `LEX_AUTH__MIDDLEWARE__LOGIN_URL` | str  \| None | None | URL to redirect for login | `packages/lexigram-auth/src/lexigram/auth/config.py:AuthMiddlewareConfig.middleware.login_url` |
| `LEX_AUTH__MIDDLEWARE__LOGIN_URL` | str  \| None | None | URL to redirect for login | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthMiddle` |
| `LEX_AUTH__MIDDLEWARE__OPTIONAL_AUTH` | bool | False | Whether authentication is optional | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthMidd` |
| `LEX_AUTH__MIDDLEWARE__OPTIONAL_AUTH` | bool | False | Whether authentication is optional | `packages/lexigram-auth/src/lexigram/auth/config.py:AuthMiddlewareConfig.middleware.optional_auth` |
| `LEX_AUTH__MIDDLEWARE__OPTIONAL_AUTH` | bool | False | Whether authentication is optional | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthMiddle` |
| `LEX_AUTH__MIDDLEWARE__PERMISSIONS_REQUIRED` | list[str] | (required) | Permissions required | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthMidd` |
| `LEX_AUTH__MIDDLEWARE__PERMISSIONS_REQUIRED` | list[str] | (required) | Permissions required | `packages/lexigram-auth/src/lexigram/auth/config.py:AuthMiddlewareConfig.middleware.permissions_requi` |
| `LEX_AUTH__MIDDLEWARE__PERMISSIONS_REQUIRED` | list[str] | (required) | Permissions required | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthMiddle` |
| `LEX_AUTH__MIDDLEWARE__ROLES_REQUIRED` | list[str] | (required) | Roles required | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthMidd` |
| `LEX_AUTH__MIDDLEWARE__ROLES_REQUIRED` | list[str] | (required) | Roles required | `packages/lexigram-auth/src/lexigram/auth/config.py:AuthMiddlewareConfig.middleware.roles_required` |
| `LEX_AUTH__MIDDLEWARE__ROLES_REQUIRED` | list[str] | (required) | Roles required | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthMiddle` |
| `LEX_AUTH__MIDDLEWARE__SCHEME` | str | (complex) | Token scheme | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthMidd` |
| `LEX_AUTH__MIDDLEWARE__SCHEME` | str | (complex) | Token scheme | `packages/lexigram-auth/src/lexigram/auth/config.py:AuthMiddlewareConfig.middleware.scheme` |
| `LEX_AUTH__MIDDLEWARE__SCHEME` | str | (complex) | Token scheme | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthMiddle` |
| `LEX_AUTH__NAME` | str | "auth" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthConf` |
| `LEX_AUTH__NAME` | str | "auth" |  | `packages/lexigram-auth/src/lexigram/auth/config.py:AuthConfig.name` |
| `LEX_AUTH__NAME` | str | "auth" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthConfig` |
| `LEX_AUTH__OAUTH2_PROVIDERS` | dict[str, dict[str, str]] | (required) | OAuth2 configs | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthConf` |
| `LEX_AUTH__OAUTH2_PROVIDERS` | dict[str, dict[str, str]] | (required) | OAuth2 configs | `packages/lexigram-auth/src/lexigram/auth/config.py:AuthConfig.oauth2_providers` |
| `LEX_AUTH__OAUTH2_PROVIDERS` | dict[str, dict[str, str]] | (required) | OAuth2 configs | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthConfig` |
| `LEX_AUTH__PASSWORD__ARGON2_MEMORY_COST` | int | 65536 | Argon2id memory cost in KiB (OWASP floor is 19456) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:Password` |
| `LEX_AUTH__PASSWORD__ARGON2_MEMORY_COST` | int | 65536 | Argon2id memory cost in KiB (OWASP floor is 19456) | `packages/lexigram-auth/src/lexigram/auth/config.py:PasswordConfig.password.argon2_memory_cost` |
| `LEX_AUTH__PASSWORD__ARGON2_MEMORY_COST` | int | 65536 | Argon2id memory cost in KiB (OWASP floor is 19456) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:PasswordCo` |
| `LEX_AUTH__PASSWORD__ARGON2_PARALLELISM` | int | 4 | Argon2id parallelism | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:Password` |
| `LEX_AUTH__PASSWORD__ARGON2_PARALLELISM` | int | 4 | Argon2id parallelism | `packages/lexigram-auth/src/lexigram/auth/config.py:PasswordConfig.password.argon2_parallelism` |
| `LEX_AUTH__PASSWORD__ARGON2_PARALLELISM` | int | 4 | Argon2id parallelism | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:PasswordCo` |
| `LEX_AUTH__PASSWORD__ARGON2_TIME_COST` | int | 3 | Argon2id time cost | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:Password` |
| `LEX_AUTH__PASSWORD__ARGON2_TIME_COST` | int | 3 | Argon2id time cost | `packages/lexigram-auth/src/lexigram/auth/config.py:PasswordConfig.password.argon2_time_cost` |
| `LEX_AUTH__PASSWORD__ARGON2_TIME_COST` | int | 3 | Argon2id time cost | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:PasswordCo` |
| `LEX_AUTH__PASSWORD__BANNED_PATTERNS` | list[str] | (required) | Substrings that must not appear in the password (case-insensitive). Use to reject common passwords or the user's own nam | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:Password` |
| `LEX_AUTH__PASSWORD__BANNED_PATTERNS` | list[str] | (required) | Substrings that must not appear in the password (case-insensitive). Use to reject common passwords or the user's own nam | `packages/lexigram-auth/src/lexigram/auth/config.py:PasswordConfig.password.banned_patterns` |
| `LEX_AUTH__PASSWORD__BANNED_PATTERNS` | list[str] | (required) | Substrings that must not appear in the password (case-insensitive). Use to reject common passwords or the user's own nam | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:PasswordCo` |
| `LEX_AUTH__PASSWORD__BCRYPT_ROUNDS` | int | 12 | bcrypt cost factor for new hashes (minimum 12 in production) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:Password` |
| `LEX_AUTH__PASSWORD__BCRYPT_ROUNDS` | int | 12 | bcrypt cost factor for new hashes (minimum 12 in production) | `packages/lexigram-auth/src/lexigram/auth/config.py:PasswordConfig.password.bcrypt_rounds` |
| `LEX_AUTH__PASSWORD__BCRYPT_ROUNDS` | int | 12 | bcrypt cost factor for new hashes (minimum 12 in production) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:PasswordCo` |
| `LEX_AUTH__PASSWORD__MAX_LENGTH` | int | 128 | Maximum password length | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:Password` |
| `LEX_AUTH__PASSWORD__MAX_LENGTH` | int | 128 | Maximum password length | `packages/lexigram-auth/src/lexigram/auth/config.py:PasswordConfig.password.max_length` |
| `LEX_AUTH__PASSWORD__MAX_LENGTH` | int | 128 | Maximum password length | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:PasswordCo` |
| `LEX_AUTH__PASSWORD__MIN_LENGTH` | int | 12 | Minimum password length | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:Password` |
| `LEX_AUTH__PASSWORD__MIN_LENGTH` | int | 12 | Minimum password length | `packages/lexigram-auth/src/lexigram/auth/config.py:PasswordConfig.password.min_length` |
| `LEX_AUTH__PASSWORD__MIN_LENGTH` | int | 12 | Minimum password length | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:PasswordCo` |
| `LEX_AUTH__PASSWORD__REQUIRE_DIGITS` | bool | True | Require at least one digit | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:Password` |
| `LEX_AUTH__PASSWORD__REQUIRE_DIGITS` | bool | True | Require at least one digit | `packages/lexigram-auth/src/lexigram/auth/config.py:PasswordConfig.password.require_digits` |
| `LEX_AUTH__PASSWORD__REQUIRE_DIGITS` | bool | True | Require at least one digit | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:PasswordCo` |
| `LEX_AUTH__PASSWORD__REQUIRE_LOWERCASE` | bool | False | Require at least one lowercase letter | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:Password` |
| `LEX_AUTH__PASSWORD__REQUIRE_LOWERCASE` | bool | False | Require at least one lowercase letter | `packages/lexigram-auth/src/lexigram/auth/config.py:PasswordConfig.password.require_lowercase` |
| `LEX_AUTH__PASSWORD__REQUIRE_LOWERCASE` | bool | False | Require at least one lowercase letter | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:PasswordCo` |
| `LEX_AUTH__PASSWORD__REQUIRE_SPECIAL` | bool | False | Require at least one special character (non-alphanumeric) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:Password` |
| `LEX_AUTH__PASSWORD__REQUIRE_SPECIAL` | bool | False | Require at least one special character (non-alphanumeric) | `packages/lexigram-auth/src/lexigram/auth/config.py:PasswordConfig.password.require_special` |
| `LEX_AUTH__PASSWORD__REQUIRE_SPECIAL` | bool | False | Require at least one special character (non-alphanumeric) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:PasswordCo` |
| `LEX_AUTH__PASSWORD__REQUIRE_UPPERCASE` | bool | True | Require at least one uppercase letter | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:Password` |
| `LEX_AUTH__PASSWORD__REQUIRE_UPPERCASE` | bool | True | Require at least one uppercase letter | `packages/lexigram-auth/src/lexigram/auth/config.py:PasswordConfig.password.require_uppercase` |
| `LEX_AUTH__PASSWORD__REQUIRE_UPPERCASE` | bool | True | Require at least one uppercase letter | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:PasswordCo` |
| `LEX_AUTH__RBAC__CACHE_PERMISSIONS` | bool | True | Cache resolved permissions | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:RBACConf` |
| `LEX_AUTH__RBAC__CACHE_PERMISSIONS` | bool | True | Cache resolved permissions | `packages/lexigram-auth/src/lexigram/auth/config.py:RBACConfig.rbac.cache_permissions` |
| `LEX_AUTH__RBAC__CACHE_PERMISSIONS` | bool | True | Cache resolved permissions | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:RBACConfig` |
| `LEX_AUTH__RBAC__DEFAULT_ROLE` | str | "viewer" | Default role for new users | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:RBACConf` |
| `LEX_AUTH__RBAC__DEFAULT_ROLE` | str | "viewer" | Default role for new users | `packages/lexigram-auth/src/lexigram/auth/config.py:RBACConfig.rbac.default_role` |
| `LEX_AUTH__RBAC__DEFAULT_ROLE` | str | "viewer" | Default role for new users | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:RBACConfig` |
| `LEX_AUTH__RBAC__ENABLED` | bool | True | Enable RBAC enforcement | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:RBACConf` |
| `LEX_AUTH__RBAC__ENABLED` | bool | True | Enable RBAC enforcement | `packages/lexigram-auth/src/lexigram/auth/config.py:RBACConfig.rbac.enabled` |
| `LEX_AUTH__RBAC__ENABLED` | bool | True | Enable RBAC enforcement | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:RBACConfig` |
| `LEX_AUTH__RBAC__PERMISSION_CACHE_TTL` | int | 300 | Permission cache TTL in seconds | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:RBACConf` |
| `LEX_AUTH__RBAC__PERMISSION_CACHE_TTL` | int | 300 | Permission cache TTL in seconds | `packages/lexigram-auth/src/lexigram/auth/config.py:RBACConfig.rbac.permission_cache_ttl` |
| `LEX_AUTH__RBAC__PERMISSION_CACHE_TTL` | int | 300 | Permission cache TTL in seconds | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:RBACConfig` |
| `LEX_AUTH__RBAC__SUPERUSER_BYPASS` | bool | True | Allow superuser role to bypass all checks | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:RBACConf` |
| `LEX_AUTH__RBAC__SUPERUSER_BYPASS` | bool | True | Allow superuser role to bypass all checks | `packages/lexigram-auth/src/lexigram/auth/config.py:RBACConfig.rbac.superuser_bypass` |
| `LEX_AUTH__RBAC__SUPERUSER_BYPASS` | bool | True | Allow superuser role to bypass all checks | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:RBACConfig` |
| `LEX_AUTH__RELAY_VERIFICATION` | bool | False | Enable binding ``RelayAuthVerifierProtocol`` for the relay gateway's inbound API-key authentication.  When ``False`` (de | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthConf` |
| `LEX_AUTH__RELAY_VERIFICATION` | bool | False | Enable binding ``RelayAuthVerifierProtocol`` for the relay gateway's inbound API-key authentication.  When ``False`` (de | `packages/lexigram-auth/src/lexigram/auth/config.py:AuthConfig.relay_verification` |
| `LEX_AUTH__RELAY_VERIFICATION` | bool | False | Enable binding ``RelayAuthVerifierProtocol`` for the relay gateway's inbound API-key authentication.  When ``False`` (de | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthConfig` |
| `LEX_AUTH__ROLES` | dict[str, AuthRoleConfig] | (required) | Role definitions | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthConf` |
| `LEX_AUTH__ROLES` | dict[str, AuthRoleConfig] | (required) | Role definitions | `packages/lexigram-auth/src/lexigram/auth/config.py:AuthConfig.roles` |
| `LEX_AUTH__ROLES` | dict[str, AuthRoleConfig] | (required) | Role definitions | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthConfig` |
| `LEX_AUTH__SECRET_KEY` | str | (required) | Secret key for signing | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthConf` |
| `LEX_AUTH__SECRET_KEY` | str | (required) | Secret key for signing | `packages/lexigram-auth/src/lexigram/auth/config.py:AuthConfig.secret_key` |
| `LEX_AUTH__SECRET_KEY` | str | (required) | Secret key for signing | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthConfig` |
| `LEX_AUTH__TOKEN__ACCESS_TOKEN_EXPIRE` | Duration | Duration.minutes(...) | Access token expiry duration | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:JWTConfi` |
| `LEX_AUTH__TOKEN__ACCESS_TOKEN_EXPIRE` | Duration | Duration.minutes(...) | Access token expiry duration | `packages/lexigram-auth/src/lexigram/auth/config.py:JWTConfig.token.access_token_expire` |
| `LEX_AUTH__TOKEN__ACCESS_TOKEN_EXPIRE` | Duration | Duration.minutes(...) | Access token expiry duration | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:JWTConfig.` |
| `LEX_AUTH__TOKEN__ALGORITHM` | str | (complex) | Algorithm | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:JWTConfi` |
| `LEX_AUTH__TOKEN__ALGORITHM` | str | (complex) | Algorithm | `packages/lexigram-auth/src/lexigram/auth/config.py:JWTConfig.token.algorithm` |
| `LEX_AUTH__TOKEN__ALGORITHM` | str | (complex) | Algorithm | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:JWTConfig.` |
| `LEX_AUTH__TOKEN__ALLOW_UNVERIFIED_DEV` | bool | False | Allow unverified JWT decode when the secret is absent. ONLY effective in Environment.DEVELOPMENT. Silently overridden to | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:JWTConfi` |
| `LEX_AUTH__TOKEN__ALLOW_UNVERIFIED_DEV` | bool | False | Allow unverified JWT decode when the secret is absent. ONLY effective in Environment.DEVELOPMENT. Silently overridden to | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:JWTConfig.` |
| `LEX_AUTH__TOKEN__ID_TOKEN_EXPIRE` | Duration | Duration.hours(...) | ID token expiry duration | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:JWTConfi` |
| `LEX_AUTH__TOKEN__ID_TOKEN_EXPIRE` | Duration | Duration.hours(...) | ID token expiry duration | `packages/lexigram-auth/src/lexigram/auth/config.py:JWTConfig.token.id_token_expire` |
| `LEX_AUTH__TOKEN__ID_TOKEN_EXPIRE` | Duration | Duration.hours(...) | ID token expiry duration | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:JWTConfig.` |
| `LEX_AUTH__TOKEN__KEY_ROTATION_GRACE_PERIOD` | Duration | Duration.seconds(...) | Duration during which tokens signed by a rotated-out key remain accepted. Prevents immediate logout on key rotation. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:JWTConfi` |
| `LEX_AUTH__TOKEN__KEY_ROTATION_GRACE_PERIOD` | Duration | Duration.seconds(...) | Duration during which tokens signed by a rotated-out key remain accepted. Prevents immediate logout on key rotation. | `packages/lexigram-auth/src/lexigram/auth/config.py:JWTConfig.token.key_rotation_grace_period` |
| `LEX_AUTH__TOKEN__KEY_ROTATION_GRACE_PERIOD` | Duration | Duration.seconds(...) | Duration during which tokens signed by a rotated-out key remain accepted. Prevents immediate logout on key rotation. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:JWTConfig.` |
| `LEX_AUTH__TOKEN__REFRESH_TOKEN_EXPIRE` | Duration | Duration.days(...) | Refresh token expiry duration | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:JWTConfi` |
| `LEX_AUTH__TOKEN__REFRESH_TOKEN_EXPIRE` | Duration | Duration.days(...) | Refresh token expiry duration | `packages/lexigram-auth/src/lexigram/auth/config.py:JWTConfig.token.refresh_token_expire` |
| `LEX_AUTH__TOKEN__REFRESH_TOKEN_EXPIRE` | Duration | Duration.days(...) | Refresh token expiry duration | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:JWTConfig.` |
| `LEX_AUTH__TOKEN__REQUIRED_AUDIENCE` | str  \| None | None | Expected ``aud`` claim for every token verified by this service. When set, tokens whose audience does not match are reje | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:JWTConfi` |
| `LEX_AUTH__TOKEN__REQUIRED_AUDIENCE` | str  \| None | None | Expected ``aud`` claim for every token verified by this service. When set, tokens whose audience does not match are reje | `packages/lexigram-auth/src/lexigram/auth/config.py:JWTConfig.token.required_audience` |
| `LEX_AUTH__TOKEN__REQUIRED_AUDIENCE` | str  \| None | None | Expected ``aud`` claim for every token verified by this service. When set, tokens whose audience does not match are reje | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:JWTConfig.` |
| `LEX_AUTH__TOKEN__SECRET_KEY` | SecretStr | Ellipsis | Secret key for signing tokens | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:JWTConfi` |
| `LEX_AUTH__TOKEN__SECRET_KEY` | SecretStr | Ellipsis | Secret key for signing tokens | `packages/lexigram-auth/src/lexigram/auth/config.py:JWTConfig.token.secret_key` |
| `LEX_AUTH__TOKEN__SECRET_KEY` | SecretStr | Ellipsis | Secret key for signing tokens | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:JWTConfig.` |
| `LEX_AUTH__USERS` | list[AuthUserConfig] | (required) | Initial users | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthConf` |
| `LEX_AUTH__USERS` | list[AuthUserConfig] | (required) | Initial users | `packages/lexigram-auth/src/lexigram/auth/config.py:AuthConfig.users` |
| `LEX_AUTH__USERS` | list[AuthUserConfig] | (required) | Initial users | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/auth/config.py:AuthConfig` |
| `LEX_CACHE__BACKENDS` | list[CacheBackendConfig] | (required) | Backend configs | `packages/lexigram-cache/src/lexigram/cache/config.py:CacheConfig.backends` |
| `LEX_CACHE__DEBUG` | bool | (complex) | Debug mode | `packages/lexigram-cache/src/lexigram/cache/config.py:CacheConfig.debug` |
| `LEX_CACHE__ENABLED` | bool | (complex) | Whether cache is enabled | `packages/lexigram-cache/src/lexigram/cache/config.py:CacheConfig.enabled` |
| `LEX_CACHE__ENV` | str  \| None | None | Environment (development/staging/production) | `packages/lexigram-cache/src/lexigram/cache/config.py:CacheConfig.env` |
| `LEX_CACHE__ENVIRONMENT` | str | (complex) | Environment | `packages/lexigram-cache/src/lexigram/cache/config.py:CacheConfig.environment` |
| `LEX_CACHE__NAME` | str | (complex) | Provider name | `packages/lexigram-cache/src/lexigram/cache/config.py:CacheConfig.name` |
| `LEX_CACHE__SERVICE__CIRCUIT_BREAKER_ENABLED` | bool | (complex) | Enable circuit breaker | `packages/lexigram-cache/src/lexigram/cache/config.py:CacheServiceConfig.service.circuit_breaker_enab` |
| `LEX_CACHE__SERVICE__CIRCUIT_BREAKER_THRESHOLD` | int | (complex) | Circuit breaker threshold | `packages/lexigram-cache/src/lexigram/cache/config.py:CacheServiceConfig.service.circuit_breaker_thre` |
| `LEX_CACHE__SERVICE__DEFAULT_BACKEND` | str  \| None | None | Default backend name | `packages/lexigram-cache/src/lexigram/cache/config.py:CacheServiceConfig.service.default_backend` |
| `LEX_CACHE__SERVICE__DEFAULT_SERIALIZER` | str | (complex) | Default serializer | `packages/lexigram-cache/src/lexigram/cache/config.py:CacheServiceConfig.service.default_serializer` |
| `LEX_CACHE__SERVICE__ENABLE_HEALTH_CHECKS` | bool | (complex) | Enable health checks | `packages/lexigram-cache/src/lexigram/cache/config.py:CacheServiceConfig.service.enable_health_checks` |
| `LEX_CACHE__SERVICE__ENABLE_METRICS` | bool | (complex) | Enable metrics | `packages/lexigram-cache/src/lexigram/cache/config.py:CacheServiceConfig.service.enable_metrics` |
| `LEX_CACHE__SERVICE__ENABLE_PROTECTION` | bool | (complex) | Enable stampede protection | `packages/lexigram-cache/src/lexigram/cache/config.py:CacheServiceConfig.service.enable_protection` |
| `LEX_CACHE__SERVICE__PROTECTION_LOCK_TTL` | int | (complex) | Protection lock TTL | `packages/lexigram-cache/src/lexigram/cache/config.py:CacheServiceConfig.service.protection_lock_ttl` |
| `LEX_CACHE__SERVICE__PROTECTION_MAX_WAIT` | float | (complex) | Max wait for locks | `packages/lexigram-cache/src/lexigram/cache/config.py:CacheServiceConfig.service.protection_max_wait` |
| `LEX_CACHE__SERVICE__PROTECTION_RETRY_INTERVAL` | float | (complex) | Lock retry interval | `packages/lexigram-cache/src/lexigram/cache/config.py:CacheServiceConfig.service.protection_retry_int` |
| `LEX_CACHE__VERSION` | str | (complex) | Config version | `packages/lexigram-cache/src/lexigram/cache/config.py:CacheConfig.version` |
| `LEX_CLI__ALIAS_LIMIT__ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:AliasLi` |
| `LEX_CLI__ALIAS_LIMIT__MAX_ALIASES` | int | (complex) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:AliasLi` |
| `LEX_CLI__ALLOWED_HOSTS` | list[str] | (required) | Hostnames permitted to reach the application. Empty by default; must be configured before production deployment. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:Se` |
| `LEX_CLI__ALLOW_UNAUTHENTICATED` | bool | False |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPConfi` |
| `LEX_CLI__ASYNC_PROCESSING` | bool | True | Process feedback handlers asynchronously in the background | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/feedback/config.py:Fee` |
| `LEX_CLI__AUDIT_HMAC_KEY` | str  \| None | None | HMAC key for audit checksum signing. Plain text or base64. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseCon` |
| `LEX_CLI__BACKEND` | str | (complex) | Graph store backend to use | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:GraphConf` |
| `LEX_CLI__BACKEND` | str | (complex) | Vector store backend to use | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:VectorCo` |
| `LEX_CLI__BACKENDS` | list[CacheBackendConfig] | (required) | Backend configs | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheConf` |
| `LEX_CLI__BACKENDS` | list[NamedDatabaseConfig] | (required) | Multi-database backends list. When non-empty, drives multi-DB mode. The entry with primary=True (or the first entry) als | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseCon` |
| `LEX_CLI__BACKENDS` | list[NamedNoSQLConfig] | (required) | Named NoSQL backends for multi-store support. When non-empty, the provider registers each backend under Annotated[Docume | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:NoSQLConf` |
| `LEX_CLI__BACKENDS` | list[NamedStorageConfig] | (required) | Named storage backends for multi-store support. When non-empty, the provider registers each backend under Annotated[Blob | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/storage/config.py:Storage` |
| `LEX_CLI__BACKENDS` | list[NamedTaskConfig] | (required) | Named task queue backends for multi-queue support. When non-empty, the provider registers each backend under Annotated[T | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskConfi` |
| `LEX_CLI__BACKENDS` | list[NamedVectorConfig] | (required) | Named vector store backends for multi-store support. When non-empty, the provider registers each backend under Annotated | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:VectorCo` |
| `LEX_CLI__BACKEND__AMQP_URL` | SecretStr | SecretStr(...) | AMQP connection URL (may contain credentials). | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskBacke` |
| `LEX_CLI__BACKEND__POSTGRES_DSN` | SecretStr  \| None | None | Postgres DSN (required when type="postgres"; may contain credentials). | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskBacke` |
| `LEX_CLI__BACKEND__QUEUE_NAME` | str | (complex) | Name of the task queue | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskBacke` |
| `LEX_CLI__BACKEND__REDIS_URL` | SecretStr | SecretStr(...) | Redis connection URL (may contain credentials). | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskBacke` |
| `LEX_CLI__BACKEND__TYPE` | str | (complex) | Queue backend type | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskBacke` |
| `LEX_CLI__BACKEND__URL` | SecretStr | Ellipsis | Database connection URL (may contain credentials) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseBac` |
| `LEX_CLI__BATCH__ENABLED` | bool | False |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:BatchCo` |
| `LEX_CLI__BATCH__MAX_BATCH_SIZE` | int | 10 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:BatchCo` |
| `LEX_CLI__BULKHEAD__MAX_CONCURRENT` | int | 10 | Max concurrent requests | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Bulk` |
| `LEX_CLI__BULKHEAD__NAME` | str | "" | Bulkhead name | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Bulk` |
| `LEX_CLI__BULKHEAD__QUEUE_SIZE` | int | 100 | Max queue size | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Bulk` |
| `LEX_CLI__BULKHEAD__TIMEOUT` | float | 30.0 | Execution timeout | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Bulk` |
| `LEX_CLI__BULK_BATCH_SIZE` | int | (complex) | Batch size for bulk operations | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:GraphConf` |
| `LEX_CLI__CACHE_TTL` | int | 3600 | Cache TTL in seconds (default: 1 hour) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGConfi` |
| `LEX_CLI__CACHE_TTL` | int | 86400 | Cache TTL in seconds (default: 24 hours) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:VectorCo` |
| `LEX_CLI__CACHE__DEFAULT_MAX_AGE` | Duration  \| int | (complex) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:CacheCo` |
| `LEX_CLI__CACHE__DEFAULT_SCOPE` | CacheScope | (complex) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:CacheCo` |
| `LEX_CLI__CACHE__ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:CacheCo` |
| `LEX_CLI__CACHE__VARY_HEADERS` | list[str] | (required) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:CacheCo` |
| `LEX_CLI__CHUNKING_STRATEGY` | str | "recursive" | Chunking strategy (recursive, semantic, token) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGConfi` |
| `LEX_CLI__CHUNK_OVERLAP` | int | 50 | Overlap between consecutive chunks | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGConfi` |
| `LEX_CLI__CHUNK_SIZE` | int | 512 | Text chunk size in tokens | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGConfi` |
| `LEX_CLI__CIRCUIT_BREAKER` | CircuitBreakerConfig | field(...) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Resi` |
| `LEX_CLI__CITATION_STYLE` | str | "inline" | Citation style (inline, footnote, numbered) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGConfi` |
| `LEX_CLI__CLIENT_STDIO_COMMAND` | list[str] | field(...) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPConfi` |
| `LEX_CLI__CLIENT_URL` | str  \| None | None |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPConfi` |
| `LEX_CLI__COLLECTION_NAME` | str | "default" | Collection/index name for vector store | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGConfi` |
| `LEX_CLI__COLLECTION_NAME` | str | "default" | Default collection name for AI-layer operations | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:VectorCo` |
| `LEX_CLI__COMMAND_BUS__ENABLE_LOGGING` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:CommandB` |
| `LEX_CLI__COMMAND_BUS__ENABLE_METRICS` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:CommandB` |
| `LEX_CLI__COMMAND_BUS__ENABLE_VALIDATION` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:CommandB` |
| `LEX_CLI__COMMAND_BUS__MAX_RETRIES` | int | 3 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:CommandB` |
| `LEX_CLI__COMMAND_BUS__RETRY_DELAY_SECONDS` | float | 1.0 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:CommandB` |
| `LEX_CLI__COMMAND_BUS__TIMEOUT_SECONDS` | float | 30.0 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:CommandB` |
| `LEX_CLI__COMPLEXITY__DEFAULT_FIELD_COST` | float | 1.0 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Complex` |
| `LEX_CLI__COMPLEXITY__DEFAULT_LIST_COST` | float | 10.0 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Complex` |
| `LEX_CLI__COMPLEXITY__ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Complex` |
| `LEX_CLI__COMPLEXITY__MAX_COMPLEXITY` | int | (complex) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Complex` |
| `LEX_CLI__CONNECTORS__FILESYSTEM__READ_ONLY` | bool | False |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:Filesyst` |
| `LEX_CLI__CONNECTORS__FILESYSTEM__ROOT_DIR` | str | "" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:Filesyst` |
| `LEX_CLI__CONNECTORS__GITHUB__API_URL` | str | "https://api.github.com" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:GitHubCo` |
| `LEX_CLI__CONNECTORS__GITHUB__TOKEN` | str | "" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:GitHubCo` |
| `LEX_CLI__CONNECTORS__GOOGLE_DRIVE__IMPERSONATED_EMAIL` | str | "" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:GoogleDr` |
| `LEX_CLI__CONNECTORS__GOOGLE_DRIVE__SERVICE_ACCOUNT_JSON` | str | "" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:GoogleDr` |
| `LEX_CLI__CONNECTORS__SLACK__BOT_TOKEN` | str | "" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:SlackCon` |
| `LEX_CLI__CONNECTORS__SLACK__MAX_MESSAGES` | int | 100 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:SlackCon` |
| `LEX_CLI__CONNECTORS__SQL__ALLOWED_TABLES` | list[str] | field(...) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:SQLConne` |
| `LEX_CLI__CONNECTORS__SQL__DSN` | str | "" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:SQLConne` |
| `LEX_CLI__CONNECTORS__SQL__READ_ONLY` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:SQLConne` |
| `LEX_CLI__CONNECTORS__WEB_FETCH__ENABLED` | bool | False |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:WebFetch` |
| `LEX_CLI__CONNECTORS__WEB_FETCH__MAX_CONTENT_BYTES` | int | (complex) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:WebFetch` |
| `LEX_CLI__CONNECTORS__WEB_FETCH__USER_AGENT` | str | "lexigram-mcp/1.0" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:WebFetch` |
| `LEX_CLI__CONNECTORS__WEB_SEARCH__API_KEY` | str | "" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:WebSearc` |
| `LEX_CLI__CONNECTORS__WEB_SEARCH__MAX_RESULTS` | int | 10 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:WebSearc` |
| `LEX_CLI__CONNECTORS__WEB_SEARCH__PROVIDER` | str | "brave" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:WebSearc` |
| `LEX_CLI__CORS_ORIGINS` | list[str] | field(...) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPConfi` |
| `LEX_CLI__CORS__ALLOWED_ORIGINS` | list[str] | (required) | Allowed origins (use ['*'] to allow all) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CO` |
| `LEX_CLI__CORS__ALLOW_CREDENTIALS` | bool | False |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CO` |
| `LEX_CLI__CORS__ALLOW_HEADERS` | list[str] | (required) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CO` |
| `LEX_CLI__CORS__ALLOW_METHODS` | list[str] | (required) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CO` |
| `LEX_CLI__CORS__ALLOW_ORIGIN_REGEX` | str  \| None | None | Regex pattern for allowed origins (matched when not in allowed_origins) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CO` |
| `LEX_CLI__CORS__DEBUG_PERMISSIVE` | bool | False | When True and debug mode is active, allow any origin via wildcard (explicit opt-in replacement for the old implicit debu | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CO` |
| `LEX_CLI__CORS__ENABLED` | bool | True | Enable CORS | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CO` |
| `LEX_CLI__CORS__EXPOSE_HEADERS` | list[str] | (required) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CO` |
| `LEX_CLI__CORS__MAX_AGE` | int | 600 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CO` |
| `LEX_CLI__CROSS_ORIGIN__EMBEDDER_POLICY` | str | "require-corp" | Cross-Origin-Embedder-Policy header value | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:Cr` |
| `LEX_CLI__CROSS_ORIGIN__ENABLED` | bool | False | Emit cross-origin isolation headers | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:Cr` |
| `LEX_CLI__CROSS_ORIGIN__OPENER_POLICY` | str | "same-origin" | Cross-Origin-Opener-Policy header value | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:Cr` |
| `LEX_CLI__CROSS_ORIGIN__RESOURCE_POLICY` | str | "same-origin" | Cross-Origin-Resource-Policy header value | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:Cr` |
| `LEX_CLI__CSP__DIRECTIVES` | dict[str, Any] | (required) | CSP directives mapping directive name to source expression(s) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CS` |
| `LEX_CLI__CSP__ENABLED` | bool | True | Emit the Content-Security-Policy header | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CS` |
| `LEX_CLI__CSRF__COOKIE_DOMAIN` | str  \| None | None |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CS` |
| `LEX_CLI__CSRF__COOKIE_HTTPONLY` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CS` |
| `LEX_CLI__CSRF__COOKIE_NAME` | str | "csrf_token" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CS` |
| `LEX_CLI__CSRF__COOKIE_PATH` | str | "/" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CS` |
| `LEX_CLI__CSRF__COOKIE_SAMESITE` | str | "Lax" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CS` |
| `LEX_CLI__CSRF__COOKIE_SECURE` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CS` |
| `LEX_CLI__CSRF__ENABLED` | bool | False |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CS` |
| `LEX_CLI__CSRF__EXCLUDED_PATHS` | list[str] | (required) | URL path prefixes exempt from CSRF validation for cookie-less requests; cookie-bearing requests on these paths are still | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CS` |
| `LEX_CLI__CSRF__EXCLUDE_AUTH_SCHEMES` | list[str] | (required) | Authorization header schemes that bypass CSRF validation (explicit opt-in). | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CS` |
| `LEX_CLI__CSRF__EXCLUDE_CONTENT_TYPES` | list[str] | (required) | Content-Type values that bypass CSRF validation (explicit opt-in — JSON requests are validated by default so cookie-auth | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CS` |
| `LEX_CLI__CSRF__HEADER_NAME` | str | "X-CSRF-Token" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CS` |
| `LEX_CLI__CSRF__SECRET_KEY` | str  \| None | None | HMAC secret used to sign and verify CSRF tokens (populated via LEX_WEB__SECURITY__CSRF__SECRET_KEY) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CS` |
| `LEX_CLI__CSRF__TOKEN_LENGTH` | int | 32 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CS` |
| `LEX_CLI__CSRF__TOKEN_TTL` | int | 3600 | TTL in seconds for synchronizer-mode tokens stored in cache. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:CS` |
| `LEX_CLI__CUSTOM_HEADERS` | dict[str, str] | (required) | Additional HTTP response headers emitted verbatim | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:Se` |
| `LEX_CLI__DATALOADER__BATCH_DELAY_MS` | float | 2.0 | Delay in milliseconds before executing a DataLoaderProtocol batch. A small non-zero value (2ms) lets more keys accumulat | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:DataLoa` |
| `LEX_CLI__DATALOADER__BATCH_ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:DataLoa` |
| `LEX_CLI__DATALOADER__CACHE_ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:DataLoa` |
| `LEX_CLI__DATALOADER__ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:DataLoa` |
| `LEX_CLI__DATALOADER__MAX_BATCH_SIZE` | int | 100 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:DataLoa` |
| `LEX_CLI__DEBUG` | bool | (complex) | Debug mode | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheConf` |
| `LEX_CLI__DEBUG` | bool | False |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventsCo` |
| `LEX_CLI__DEBUG` | bool | False |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:GraphQL` |
| `LEX_CLI__DEBUG` | bool | False | Enable debug mode | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Monitor` |
| `LEX_CLI__DEFAULT_DIMENSION` | int | 1536 | Default vector dimension | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:VectorCo` |
| `LEX_CLI__DEFAULT_DISTANCE_METRIC` | DistanceMetric | (complex) | Default distance metric for new collections | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:VectorCo` |
| `LEX_CLI__DEFAULT_DRIVER` | Literal['local', 's3', 'gcs', 'azure', 'memory', 'r2'] | (complex) | Default storage driver to use | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/storage/config.py:Storage` |
| `LEX_CLI__DEFAULT_INDEX_TYPE` | IndexType | (complex) | Default index type for new collections | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:VectorCo` |
| `LEX_CLI__DEFAULT_QUERY_LIMIT` | int | (complex) | Default limit for query results | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:GraphConf` |
| `LEX_CLI__DEFAULT_TRAVERSAL_MAX_DEPTH` | int | (complex) | Default maximum depth for traversals | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:GraphConf` |
| `LEX_CLI__DEPTH_LIMIT__ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:DepthLi` |
| `LEX_CLI__DEPTH_LIMIT__IGNORE_INTROSPECTION` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:DepthLi` |
| `LEX_CLI__DEPTH_LIMIT__MAX_DEPTH` | int | (complex) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:DepthLi` |
| `LEX_CLI__DRIVER` | str | "mongodb" | NoSQL driver name | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:NoSQLConf` |
| `LEX_CLI__DRIVERS` | dict[str, StorageLocalConfig  \| StorageS3Config  \| StorageGCSConfig  \| Storag | (required) | Driver-specific configurations | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/storage/config.py:Storage` |
| `LEX_CLI__EMBEDDING_MODEL` | str  \| None | None | Embedding model identifier. Must be set explicitly — no vendor-specific default. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGConfi` |
| `LEX_CLI__EMBEDDING_MODEL` | str | "text-embedding-3-small" | Embedding model name for AI-layer embedding generation | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:VectorCo` |
| `LEX_CLI__EMBEDDING_PROVIDER` | str | "openai" | Embedding provider (openai, cohere, etc.) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGConfi` |
| `LEX_CLI__ENABLED` | bool | True | Enable AI features | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/config.py:AIConfig.ena` |
| `LEX_CLI__ENABLED` | bool | (complex) | Whether cache is enabled | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheConf` |
| `LEX_CLI__ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseCon` |
| `LEX_CLI__ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventsCo` |
| `LEX_CLI__ENABLED` | bool | True | Master on/off switch for all feedback collection | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/feedback/config.py:Fee` |
| `LEX_CLI__ENABLED` | bool | True | Enable the graph store subsystem | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:GraphConf` |
| `LEX_CLI__ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:GraphQL` |
| `LEX_CLI__ENABLED` | bool | True | Enable the MCP server subsystem | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPConfi` |
| `LEX_CLI__ENABLED` | bool | True | Enable monitoring | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Monitor` |
| `LEX_CLI__ENABLED` | bool | True | Enable NoSQL support | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:NoSQLConf` |
| `LEX_CLI__ENABLED` | bool | True | Master on/off switch for all observability | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/observability/config.p` |
| `LEX_CLI__ENABLED` | bool | True | Enable the RAG pipeline | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGConfi` |
| `LEX_CLI__ENABLED` | bool | True | Enable the security subsystem | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:Se` |
| `LEX_CLI__ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/storage/config.py:Storage` |
| `LEX_CLI__ENABLED` | bool | True | Whether tasks module is enabled | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskConfi` |
| `LEX_CLI__ENABLED` | bool | True | Enable the vector store subsystem | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:VectorCo` |
| `LEX_CLI__ENABLE_ADMIN` | bool | True | Whether to register the AuditAdminContributor | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/audit/config.py:AuditConf` |
| `LEX_CLI__ENABLE_CACHE` | bool | False | Enable embedding caching (requires a CacheBackend binding) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:VectorCo` |
| `LEX_CLI__ENABLE_CACHING` | bool | True | Enable caching for RAG queries | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGConfi` |
| `LEX_CLI__ENABLE_CITATIONS` | bool | True | Include source citations in responses | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGConfi` |
| `LEX_CLI__ENABLE_CORS` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:Se` |
| `LEX_CLI__ENABLE_CSRF` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:Se` |
| `LEX_CLI__ENABLE_HALLUCINATION_DETECTION` | bool | True | Enable hallucination detection for AI responses | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGConfi` |
| `LEX_CLI__ENABLE_HYDE` | bool | False | Enable HyDE (Hypothetical Document Embeddings) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGConfi` |
| `LEX_CLI__ENABLE_IDENTITY_RESOLUTION` | bool | False |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:GraphQL` |
| `LEX_CLI__ENABLE_QUERY_EXPANSION` | bool | True | Enable query expansion techniques | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGConfi` |
| `LEX_CLI__ENABLE_SSE` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPConfi` |
| `LEX_CLI__ENV` | str  \| None | None | Environment (development/staging/production) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheConf` |
| `LEX_CLI__ENV` | str  \| None | None | Environment (development/staging/production) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventsCo` |
| `LEX_CLI__ENV` | str  \| None | None | Environment (development/staging/production) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:GraphQL` |
| `LEX_CLI__ENV` | str  \| None | None | Environment (development/staging/production) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Monitor` |
| `LEX_CLI__ENV` | str  \| None | None | Environment (development/staging/production) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/storage/config.py:Storage` |
| `LEX_CLI__ENV` | str  \| None | None | Environment (development/staging/production) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskConfi` |
| `LEX_CLI__ENVIRONMENT` | str | (complex) | Environment | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheConf` |
| `LEX_CLI__ENVIRONMENT` | Environment | (complex) | Deployment environment | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Monitor` |
| `LEX_CLI__ERRORS__DEBUG_MODE` | bool | False |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:ErrorCo` |
| `LEX_CLI__ERRORS__INCLUDE_STACKTRACE` | bool | False |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:ErrorCo` |
| `LEX_CLI__ERRORS__LOG_ERRORS` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:ErrorCo` |
| `LEX_CLI__ERRORS__MASK_ERRORS` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:ErrorCo` |
| `LEX_CLI__EVENT_BUS__ALLOW_NO_HANDLERS` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventBus` |
| `LEX_CLI__EVENT_BUS__CONTINUE_ON_ERROR` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventBus` |
| `LEX_CLI__EVENT_BUS__ENABLE_DEAD_LETTER` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventBus` |
| `LEX_CLI__EVENT_BUS__HANDLER_TIMEOUT_SECONDS` | float | 30.0 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventBus` |
| `LEX_CLI__EVENT_BUS__MAX_CONCURRENT_HANDLERS` | int | 10 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventBus` |
| `LEX_CLI__EVENT_BUS__MAX_HANDLER_RETRIES` | int | 3 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventBus` |
| `LEX_CLI__EVENT_BUS__MAX_QUEUE_PER_SUBSCRIBER` | int | 1000 | Maximum number of events queued per event type before backpressure is applied. 0 means unbounded (no backpressure). | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventBus` |
| `LEX_CLI__EVENT_BUS__PARALLEL_DISPATCH` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventBus` |
| `LEX_CLI__EVENT_BUS__RETRY_FAILED_HANDLERS` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventBus` |
| `LEX_CLI__EVENT_STORE_BACKEND` | EventStoreBackend | (complex) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventsCo` |
| `LEX_CLI__EXTRA` | dict[str, Any] | (required) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskConfi` |
| `LEX_CLI__FIRESTORE__CREDENTIALS_JSON` | str  \| None | None | Path to a service account JSON key file, or the raw JSON string. When ``None``, Application Default Credentials (ADC) ar | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:Firestore` |
| `LEX_CLI__FIRESTORE__DATABASE_ID` | str | "(default)" | Firestore database ID (use '(default)' for the default database) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:Firestore` |
| `LEX_CLI__FIRESTORE__PROJECT_ID` | str | Ellipsis | Google Cloud project ID | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:Firestore` |
| `LEX_CLI__GOVERNANCE` | Any | (required) | AI governance configuration | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/config.py:AIConfig.gov` |
| `LEX_CLI__HEADERS__CONTENT_TYPE_NOSNIFF` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:Se` |
| `LEX_CLI__HEADERS__CSP` | str  \| None | None |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:Se` |
| `LEX_CLI__HEADERS__FRAME_OPTIONS` | str | "DENY" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:Se` |
| `LEX_CLI__HEADERS__HSTS_INCLUDE_SUBDOMAINS` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:Se` |
| `LEX_CLI__HEADERS__HSTS_MAX_AGE` | int | 31536000 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:Se` |
| `LEX_CLI__HEADERS__PERMISSIONS_POLICY` | str  \| None | None |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:Se` |
| `LEX_CLI__HEADERS__REFERRER_POLICY` | str | "strict-origin-when-cross-origin" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:Se` |
| `LEX_CLI__HEADERS__XSS_PROTECTION` | str | "1; mode=block" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:Se` |
| `LEX_CLI__HEALTH_CHECKS_ENABLED` | bool | True | Enable background health checking for AI components | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/observability/config.p` |
| `LEX_CLI__HEALTH_CHECK_TIMEOUT` | float | 5.0 | Timeout in seconds for the startup health check in StorageProvider.boot() | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/storage/config.py:Storage` |
| `LEX_CLI__HEALTH__CHECKS` | list[str] | (required) | List of health check names to run | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:HealthC` |
| `LEX_CLI__HEALTH__ENABLED` | bool | True | Enable health checks | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:HealthC` |
| `LEX_CLI__HEALTH__INCLUDE_DETAILS` | bool | True | Include detailed health info in response | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:HealthC` |
| `LEX_CLI__HEALTH__INTERVAL` | int | (complex) | Health check interval in seconds | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:HealthC` |
| `LEX_CLI__HEALTH__PATH` | str | "/health" | Health endpoint path | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:HealthC` |
| `LEX_CLI__HEALTH__TIMEOUT` | float | 5.0 | Health check timeout in seconds | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:HealthC` |
| `LEX_CLI__HMAC_KEY` | bytes  \| None | None | HMAC key for checksum computation | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/audit/config.py:AuditConf` |
| `LEX_CLI__HOST` | str | "0.0.0.0" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPConfi` |
| `LEX_CLI__HSTS__ENABLED` | bool | False | Emit the Strict-Transport-Security header | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:HS` |
| `LEX_CLI__HSTS__INCLUDE_SUBDOMAINS` | bool | True | Apply HSTS to all subdomains | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:HS` |
| `LEX_CLI__HSTS__MAX_AGE` | int | 31536000 | HSTS max-age in seconds (default 1 year) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:HS` |
| `LEX_CLI__HSTS__PRELOAD` | bool | False | Include site in HSTS preload list | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:HS` |
| `LEX_CLI__INTEGRATION__CACHE_KEY_PREFIX` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Integra` |
| `LEX_CLI__INTEGRATION__SQL_CONTEXT_BRIDGE` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Integra` |
| `LEX_CLI__INTROSPECTION__ALLOWED_ENVIRONMENTS` | set[str] | (required) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Introsp` |
| `LEX_CLI__INTROSPECTION__ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Introsp` |
| `LEX_CLI__KAFKA__AUTO_OFFSET_RESET` | str | "earliest" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:KafkaCon` |
| `LEX_CLI__KAFKA__BOOTSTRAP_SERVERS` | str | Ellipsis | Kafka bootstrap servers | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:KafkaCon` |
| `LEX_CLI__KAFKA__CONSUMER_GROUP` | str | "events-consumers" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:KafkaCon` |
| `LEX_CLI__KAFKA__ENABLE_AUTO_COMMIT` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:KafkaCon` |
| `LEX_CLI__KAFKA__TOPIC_PREFIX` | str | "events" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:KafkaCon` |
| `LEX_CLI__LIFECYCLE__AUTO_PROVISION_ISOLATION` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Lifecyc` |
| `LEX_CLI__LIFECYCLE__ISOLATION_STRATEGY` | str | "row_level" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Lifecyc` |
| `LEX_CLI__LLM` | Any  \| None | None | LLM configuration (optional) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/config.py:AIConfig.llm` |
| `LEX_CLI__LOGGING_MIDDLEWARE__ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:LoggingM` |
| `LEX_CLI__LOGGING_MIDDLEWARE__INCLUDE_PAYLOAD` | bool | False |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:LoggingM` |
| `LEX_CLI__LOGGING_MIDDLEWARE__LOG_LEVEL` | str | "INFO" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:LoggingM` |
| `LEX_CLI__LOGGING_MIDDLEWARE__MAX_PAYLOAD_LENGTH` | int | 1000 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:LoggingM` |
| `LEX_CLI__LOGGING__ENABLED` | bool | True | Enable structured logging | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Logging` |
| `LEX_CLI__LOGGING__FORMAT` | str | "json" | Log format (json, text) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Logging` |
| `LEX_CLI__LOGGING__INCLUDE_TRACE_CONTEXT` | bool | True | Include trace context in logs | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Logging` |
| `LEX_CLI__LOGGING__LEVEL` | str | "INFO" | Default log level | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Logging` |
| `LEX_CLI__LOGGING__REDACT_FIELDS` | list[str] | (required) | Fields to redact from logs | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Logging` |
| `LEX_CLI__MAX_REQUEST_SIZE` | int | (complex) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPConfi` |
| `LEX_CLI__MAX_RETRIES` | int | (complex) | Maximum number of retries for operations | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:GraphConf` |
| `LEX_CLI__MAX_RETRIES` | int | (complex) | Maximum number of retries for operations | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:VectorCo` |
| `LEX_CLI__MEMORY__ENABLE_SNAPSHOTS` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:InMemory` |
| `LEX_CLI__MEMORY__MAX_COLLECTIONS` | int | 100 | Maximum number of collections in memory | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:MemoryCo` |
| `LEX_CLI__MEMORY__MAX_EDGES` | int | (complex) | Maximum number of edges in memory | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:MemoryCon` |
| `LEX_CLI__MEMORY__MAX_EVENTS_PER_STREAM` | int | 10000 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:InMemory` |
| `LEX_CLI__MEMORY__MAX_NODES` | int | (complex) | Maximum number of nodes in memory | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:MemoryCon` |
| `LEX_CLI__MEMORY__MAX_VECTORS_PER_COLLECTION` | int | 100000 | Maximum number of vectors per collection | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:MemoryCo` |
| `LEX_CLI__METRICS_ENABLED` | bool | True | Enable metrics collection | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/observability/config.p` |
| `LEX_CLI__METRICS_MIDDLEWARE__ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:MetricsM` |
| `LEX_CLI__METRICS_MIDDLEWARE__HISTOGRAM_BUCKETS` | list[float] | (required) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:MetricsM` |
| `LEX_CLI__METRICS_MIDDLEWARE__INCLUDE_HISTOGRAMS` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:MetricsM` |
| `LEX_CLI__METRICS_MIDDLEWARE__PREFIX` | str | "events" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:MetricsM` |
| `LEX_CLI__METRICS__COLLECTION_INTERVAL` | float | 60.0 | Metrics collection interval in seconds | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Metrics` |
| `LEX_CLI__METRICS__DEFAULT_LABELS` | dict[str, str] | (required) | Default labels for all metrics | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Metrics` |
| `LEX_CLI__METRICS__ENABLED` | bool | True | Enable metrics collection | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Metrics` |
| `LEX_CLI__METRICS__ENABLED` | bool | False |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Metrics` |
| `LEX_CLI__METRICS__HISTOGRAM_BUCKETS` | list[float] | (required) | Default histogram bucket boundaries | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Metrics` |
| `LEX_CLI__METRICS__HISTOGRAM_BUCKETS` | list[float] | (required) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Metrics` |
| `LEX_CLI__METRICS__INCLUDE_LABELS` | list[str] | (required) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Metrics` |
| `LEX_CLI__METRICS__NAMESPACE` | str | "lexigram_graphql" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Metrics` |
| `LEX_CLI__METRICS__PREFIX` | str | (complex) | MetricProtocol name prefix | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Metrics` |
| `LEX_CLI__MIGRATIONS__LOCK_TIMEOUT` | Duration | Duration.seconds(...) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseMig` |
| `LEX_CLI__MIN_CITATION_CONFIDENCE` | float | 0.6 | Minimum confidence for citation inclusion | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGConfi` |
| `LEX_CLI__MONGODB__AUTH_SOURCE` | str | "admin" | Authentication database | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDBCo` |
| `LEX_CLI__MONGODB__CONNECTION_STRING` | SecretStr | Ellipsis | MongoDB connection string | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:MongoDBE` |
| `LEX_CLI__MONGODB__CONNECT_TIMEOUT_MS` | int | 10000 | Connection timeout (ms) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDBCo` |
| `LEX_CLI__MONGODB__DATABASE` | str | "lexigram" | Database name | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDBCo` |
| `LEX_CLI__MONGODB__DATABASE_NAME` | str | "events" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:MongoDBE` |
| `LEX_CLI__MONGODB__EVENTS_COLLECTION` | str | "domain_events" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:MongoDBE` |
| `LEX_CLI__MONGODB__MAX_POOL_SIZE` | int | 100 | Maximum connection pool size | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDBCo` |
| `LEX_CLI__MONGODB__MAX_POOL_SIZE` | int | 10 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:MongoDBE` |
| `LEX_CLI__MONGODB__MIN_POOL_SIZE` | int | 10 | Minimum connection pool size | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDBCo` |
| `LEX_CLI__MONGODB__READ_PREFERENCE` | str | "primaryPreferred" | Read preference mode | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDBCo` |
| `LEX_CLI__MONGODB__RETRY_READS` | bool | True | Enable read retries | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDBCo` |
| `LEX_CLI__MONGODB__RETRY_WRITES` | bool | True | Enable write retries | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDBCo` |
| `LEX_CLI__MONGODB__SERVER_SELECTION_TIMEOUT` | int | 30000 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:MongoDBE` |
| `LEX_CLI__MONGODB__SERVER_SELECTION_TIMEOUT_MS` | int | 5000 | Server selection timeout (ms) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDBCo` |
| `LEX_CLI__MONGODB__SNAPSHOTS_COLLECTION` | str | "snapshots" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:MongoDBE` |
| `LEX_CLI__MONGODB__SOCKET_TIMEOUT_MS` | int | 30000 | Socket timeout (ms) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDBCo` |
| `LEX_CLI__MONGODB__URI` | str | "mongodb://localhost:27017" | MongoDB connection URI | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDBCo` |
| `LEX_CLI__MONGODB__WRITE_CONCERN_W` | str  \| int | "majority" | Write concern level | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/nosql/config.py:MongoDBCo` |
| `LEX_CLI__NAME` | str | "ai" | Configuration name | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/config.py:AIConfig.nam` |
| `LEX_CLI__NAME` | str | (complex) | Provider name | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheConf` |
| `LEX_CLI__NAME` | str | "database" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseCon` |
| `LEX_CLI__NAME` | str | "events" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventsCo` |
| `LEX_CLI__NAME` | str | "graphql" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:GraphQL` |
| `LEX_CLI__NAME` | str | (complex) | Provider name | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Monitor` |
| `LEX_CLI__NAME` | str | "storage" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/storage/config.py:Storage` |
| `LEX_CLI__NAME` | str | "tasks" | Configuration name | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskConfi` |
| `LEX_CLI__NEO4J__CONNECTION_TIMEOUT` | float | (complex) | Connection timeout in seconds | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:Neo4jConf` |
| `LEX_CLI__NEO4J__DATABASE` | str | (complex) | Target database name | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:Neo4jConf` |
| `LEX_CLI__NEO4J__ENCRYPTED` | bool | False | Whether to use SSL/TLS encryption | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:Neo4jConf` |
| `LEX_CLI__NEO4J__FETCH_SIZE` | int | (complex) | Default fetch size for results | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:Neo4jConf` |
| `LEX_CLI__NEO4J__MAX_CONNECTION_POOL_SIZE` | int | (complex) | Maximum number of connections in the pool | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:Neo4jConf` |
| `LEX_CLI__NEO4J__MAX_TRANSACTION_RETRY_TIME` | float | 30.0 | Maximum time for transaction retries | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:Neo4jConf` |
| `LEX_CLI__NEO4J__PASSWORD` | SecretStr | (required) | Neo4j password | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:Neo4jConf` |
| `LEX_CLI__NEO4J__TRUST` | str | "TRUST_SYSTEM_CA_SIGNED_CERTIFICATES" | Trust strategy for SSL | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:Neo4jConf` |
| `LEX_CLI__NEO4J__URI` | str | "bolt://localhost:7687" | Neo4j BOLT URI | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:Neo4jConf` |
| `LEX_CLI__NEO4J__USERNAME` | str | "neo4j" | Neo4j username | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:Neo4jConf` |
| `LEX_CLI__OBSERVABILITY` | Any | (required) | AI observability configuration (tracing and metrics) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/config.py:AIConfig.obs` |
| `LEX_CLI__OPENTELEMETRY__BATCH_SIZE` | int | 512 | Export batch size | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:OpenTel` |
| `LEX_CLI__OPENTELEMETRY__COMPRESSION` | str | "none" | Compression type (none, gzip) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:OpenTel` |
| `LEX_CLI__OPENTELEMETRY__ENDPOINT` | str  \| None | None | OTLP endpoint URL | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:OpenTel` |
| `LEX_CLI__OPENTELEMETRY__EXPORT_INTERVAL` | float | 5.0 | Export interval seconds | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:OpenTel` |
| `LEX_CLI__OPENTELEMETRY__HEADERS` | dict[str, str] | (required) | OTLP request headers | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:OpenTel` |
| `LEX_CLI__OPENTELEMETRY__INSECURE` | bool | False | Use insecure connection | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:OpenTel` |
| `LEX_CLI__OPENTELEMETRY__METRICS_EXPORTERS` | list[OTelExporterConfig] | (required) | List of metrics exporters to build. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:OpenTel` |
| `LEX_CLI__OPENTELEMETRY__TIMEOUT` | float | 30.0 | Export timeout seconds | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:OpenTel` |
| `LEX_CLI__OPENTELEMETRY__TRACING_EXPORTERS` | list[OTelExporterConfig] | (required) | List of tracing exporters to build. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:OpenTel` |
| `LEX_CLI__OPERATIONS__ECHO` | bool | False |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseOpe` |
| `LEX_CLI__OPERATIONS__STATEMENT_TIMEOUT` | Duration | Duration.seconds(...) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseOpe` |
| `LEX_CLI__OUTBOX__BATCH_MAX_AGE` | Duration | Duration.seconds(...) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseOut` |
| `LEX_CLI__OUTBOX__ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseOut` |
| `LEX_CLI__OUTBOX__POLL_INTERVAL` | Duration | Duration.seconds(...) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabaseOut` |
| `LEX_CLI__OVERRIDES__CACHE_TTL` | int | DEFAULT_CONFIG_CACHE_TTL |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:ConfigO` |
| `LEX_CLI__PATH` | str | (complex) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:GraphQL` |
| `LEX_CLI__PATH` | str | "/mcp" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPConfi` |
| `LEX_CLI__PERMISSIONS_POLICY` | dict[str, str] | (required) | Permissions-Policy directive map | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:Se` |
| `LEX_CLI__PERSISTED_QUERIES__ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Persist` |
| `LEX_CLI__PERSISTED_QUERIES__STORE_TYPE` | str | "memory" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Persist` |
| `LEX_CLI__PERSISTED_QUERIES__TTL_SECONDS` | Duration  \| int | 86400 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Persist` |
| `LEX_CLI__PERSIST_DIRECTORY` | str  \| None | None | Local directory path for vector store persistence (e.g. Chroma) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGConfi` |
| `LEX_CLI__PGVECTOR__CREATE_EXTENSION` | bool | True | Whether to create pgvector extension if missing | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:PgVector` |
| `LEX_CLI__PGVECTOR__DATABASE` | str | "primary" | Name of the database backend from db.backends to use for pgvector. Matches a 'name:' entry in the db.backends list. Defa | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:PgVector` |
| `LEX_CLI__PGVECTOR__DEFAULT_EF_SEARCH` | int | (complex) | Default ef_search for HNSW index | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:PgVector` |
| `LEX_CLI__PGVECTOR__DEFAULT_LISTS` | int | (complex) | Default number of lists for IVFFlat index | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:PgVector` |
| `LEX_CLI__PGVECTOR__DEFAULT_PROBES` | int | (complex) | Default number of probes for IVFFlat index | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:PgVector` |
| `LEX_CLI__PGVECTOR__SCHEMA` | str | "public" | Database schema for vector tables | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:PgVector` |
| `LEX_CLI__PGVECTOR__TABLE_PREFIX` | str | "vec_" | Prefix for vector storage tables | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:PgVector` |
| `LEX_CLI__PINECONE__API_KEY` | SecretStr | SecretStr(...) | Pinecone API key | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Pinecone` |
| `LEX_CLI__PINECONE__ENVIRONMENT` | str | "" | Pinecone environment (e.g. 'us-west1-gcp') | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Pinecone` |
| `LEX_CLI__PINECONE__INDEX_NAME` | str | "" | Name of the Pinecone index | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Pinecone` |
| `LEX_CLI__PINECONE__NAMESPACE` | str | "" | Default namespace for the index | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Pinecone` |
| `LEX_CLI__PINECONE__POOL_THREADS` | int | 4 | Number of threads for the connection pool | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Pinecone` |
| `LEX_CLI__PINECONE__TIMEOUT` | float | (complex) | Request timeout in seconds | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Pinecone` |
| `LEX_CLI__PLAYGROUND__ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Playgro` |
| `LEX_CLI__PLAYGROUND__PATH` | str | (complex) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Playgro` |
| `LEX_CLI__PLAYGROUND__TITLE` | str | "Lexigram GraphQL Playground" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Playgro` |
| `LEX_CLI__POOL__ACQUIRE_TIMEOUT` | Duration | Duration.seconds(...) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabasePoo` |
| `LEX_CLI__POOL__IDLE_TIMEOUT` | Duration | Duration.minutes(...) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabasePoo` |
| `LEX_CLI__POOL__MAX_LIFETIME` | Duration | Duration.hours(...) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabasePoo` |
| `LEX_CLI__POOL__MAX_OVERFLOW` | int | 5 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabasePoo` |
| `LEX_CLI__POOL__MAX_SIZE` | int | (complex) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabasePoo` |
| `LEX_CLI__POOL__MIN_SIZE` | int | (complex) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabasePoo` |
| `LEX_CLI__POOL__RECYCLE` | int | 3600 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabasePoo` |
| `LEX_CLI__POOL__TIMEOUT` | float | (complex) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/sql/config.py:DatabasePoo` |
| `LEX_CLI__PORT` | int | 8080 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPConfi` |
| `LEX_CLI__POSTGRES` | PostgresEventStoreConfig  \| None | None |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventsCo` |
| `LEX_CLI__PROJECTION__BATCH_SIZE` | int | 100 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Projecti` |
| `LEX_CLI__PROJECTION__CHECKPOINT_INTERVAL` | int | 100 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Projecti` |
| `LEX_CLI__PROJECTION__ENABLE_PARALLEL_PROJECTIONS` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Projecti` |
| `LEX_CLI__PROJECTION__MAX_CATCH_UP_EVENTS` | int | 10000 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Projecti` |
| `LEX_CLI__PROJECTION__REBUILD_BATCH_SIZE` | int | 1000 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Projecti` |
| `LEX_CLI__PROMETHEUS__ENABLE_DEFAULT_METRICS` | bool | True | Enable default process metrics | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Prometh` |
| `LEX_CLI__PROMETHEUS__METRICS_TABLE` | str | "metrics_samples" | Table name for metrics samples | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Prometh` |
| `LEX_CLI__PROMETHEUS__PATH` | str | "/metrics" | Metrics endpoint path | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Prometh` |
| `LEX_CLI__PROMETHEUS__PORT` | int | (complex) | Metrics server port | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Prometh` |
| `LEX_CLI__PROMETHEUS__PUSHGATEWAY_URL` | str  \| None | None | Pushgateway URL for push-based metrics | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Prometh` |
| `LEX_CLI__PROMETHEUS__PUSH_INTERVAL` | float | 10.0 | Push interval for Pushgateway | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Prometh` |
| `LEX_CLI__PROMETHEUS__STORE_IN_DB` | bool | False | Persist metrics observations to DB | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Prometh` |
| `LEX_CLI__PUSH_BACKENDS` | list[NamedPushConfig] | (required) | Named push notification backends for multi-backend support. When non-empty, the provider registers each backend under An | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/notification/config.py:No` |
| `LEX_CLI__QDRANT__API_KEY` | SecretStr  \| None | None | Qdrant API key | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:QdrantCo` |
| `LEX_CLI__QDRANT__GRPC_PORT` | int | 6334 | gRPC port for Qdrant | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:QdrantCo` |
| `LEX_CLI__QDRANT__PREFER_GRPC` | bool | True | Whether to prefer gRPC over HTTP | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:QdrantCo` |
| `LEX_CLI__QDRANT__TIMEOUT` | float | (complex) | Request timeout in seconds | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:QdrantCo` |
| `LEX_CLI__QDRANT__URL` | str | "http://localhost:6333" | Qdrant server URL | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:QdrantCo` |
| `LEX_CLI__QUERY_BUS__ENABLE_LOGGING` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:QueryBus` |
| `LEX_CLI__QUERY_BUS__ENABLE_METRICS` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:QueryBus` |
| `LEX_CLI__QUERY_BUS__TIMEOUT_SECONDS` | float | 30.0 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:QueryBus` |
| `LEX_CLI__RABBITMQ__DURABLE` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:RabbitMQ` |
| `LEX_CLI__RABBITMQ__EXCHANGE_NAME` | str | "events" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:RabbitMQ` |
| `LEX_CLI__RABBITMQ__PREFETCH_COUNT` | int | 10 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:RabbitMQ` |
| `LEX_CLI__RABBITMQ__QUEUE_PREFIX` | str | "events" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:RabbitMQ` |
| `LEX_CLI__RABBITMQ__URL` | SecretStr | Ellipsis | AMQP connection URL | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:RabbitMQ` |
| `LEX_CLI__RAG` | Any  \| None | None | RAG pipeline configuration (optional) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/config.py:AIConfig.rag` |
| `LEX_CLI__RATE_LIMIT` | RateLimitConfig | (required) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:GraphQL` |
| `LEX_CLI__RATE_LIMIT__BURST` | int  \| None | None | Maximum burst size | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskRateL` |
| `LEX_CLI__RATE_LIMIT__ENABLED` | bool | False | Whether rate limiting is enabled | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskRateL` |
| `LEX_CLI__RATE_LIMIT__PER` | float | 1.0 | Time period in seconds | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskRateL` |
| `LEX_CLI__RATE_LIMIT__RATE` | int | 100 | Number of tasks allowed per time period | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskRateL` |
| `LEX_CLI__REFERRER_POLICY` | str | "strict-origin-when-cross-origin" | Referrer-Policy header value | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/security/config.py:Se` |
| `LEX_CLI__REQUEST_TIMEOUT` | float | 30.0 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPConfi` |
| `LEX_CLI__RESOLUTION__HEADER_NAME` | str | DEFAULT_HEADER_NAME |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Resolut` |
| `LEX_CLI__RESOLUTION__JWT_CLAIM_KEY` | str | DEFAULT_JWT_CLAIM_KEY |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Resolut` |
| `LEX_CLI__RESOLUTION__PATH_PATTERN` | str  \| None | DEFAULT_PATH_PATTERN |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Resolut` |
| `LEX_CLI__RESOLUTION__RESOLVERS` | list[str] | field(...) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Resolut` |
| `LEX_CLI__RESOLUTION__STRICT_MEMBERSHIP` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Resolut` |
| `LEX_CLI__RESOLUTION__SUBDOMAIN_PATTERN` | str  \| None | None |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Resolut` |
| `LEX_CLI__RESOLUTION__TRUSTED_RESOLVERS` | list[str] | field(...) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Resolut` |
| `LEX_CLI__RESOLUTION__VALIDATOR_CACHE_TTL` | int | DEFAULT_VALIDATOR_CACHE_TTL |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tenancy/config.py:Resolut` |
| `LEX_CLI__RETENTION_POLICY` | RetentionPolicy | (required) | Retention rules | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/audit/config.py:AuditConf` |
| `LEX_CLI__RETRY` | RetryConfig | field(...) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Resi` |
| `LEX_CLI__RETRY` | RetryConfig | (required) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskConfi` |
| `LEX_CLI__RETRY_DELAY` | float | (complex) | Delay between retries in seconds | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:GraphConf` |
| `LEX_CLI__RETRY_DELAY` | float | (complex) | Delay between retries in seconds | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:VectorCo` |
| `LEX_CLI__RETRY_MIDDLEWARE__ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:RetryMid` |
| `LEX_CLI__RETRY_MIDDLEWARE__EXPONENTIAL_BASE` | float | 2.0 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:RetryMid` |
| `LEX_CLI__RETRY_MIDDLEWARE__INITIAL_DELAY_SECONDS` | float | 0.1 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:RetryMid` |
| `LEX_CLI__RETRY_MIDDLEWARE__MAX_DELAY_SECONDS` | float | 10.0 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:RetryMid` |
| `LEX_CLI__RETRY_MIDDLEWARE__MAX_RETRIES` | int | 3 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:RetryMid` |
| `LEX_CLI__SAGA__CLEANUP_COMPLETED_AFTER_HOURS` | int | 24 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:SagaConf` |
| `LEX_CLI__SAGA__DEFAULT_TIMEOUT_SECONDS` | float | 300.0 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:SagaConf` |
| `LEX_CLI__SAGA__ENABLE_COMPENSATION` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:SagaConf` |
| `LEX_CLI__SAGA__MAX_RETRIES_PER_STEP` | int | 3 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:SagaConf` |
| `LEX_CLI__SAGA__PERSIST_STATE` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:SagaConf` |
| `LEX_CLI__SAGA__RETRY_DELAY_SECONDS` | float | 1.0 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:SagaConf` |
| `LEX_CLI__SCHEDULER__CHECK_INTERVAL` | float | (complex) | Interval between schedule checks (seconds) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskSched` |
| `LEX_CLI__SCHEDULER__ENABLED` | bool | True | Whether scheduling is enabled | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskSched` |
| `LEX_CLI__SCHEDULER__TIMEZONE` | str | (complex) | Timezone for cron expressions | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskSched` |
| `LEX_CLI__SCHEMA_BASELINE_PATH` | str  \| None | None | Path to a GraphQL SDL (.graphql) file containing the baseline schema. When set, GraphQLProvider.boot() compares the curr | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:GraphQL` |
| `LEX_CLI__SERVER_NAME` | str | "lexigram-mcp" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPConfi` |
| `LEX_CLI__SERVER_VERSION` | str | "1.0.0" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPConfi` |
| `LEX_CLI__SERVICE__ALLOWED_MIME_TYPES` | list[str] | (required) | Allowed MIME types for upload validation. Defaults to a safe set of common image types: ['image/jpeg', 'image/png', 'ima | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/storage/config.py:Storage` |
| `LEX_CLI__SERVICE__CIRCUIT_BREAKER_ENABLED` | bool | (complex) | Enable circuit breaker | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheServ` |
| `LEX_CLI__SERVICE__CIRCUIT_BREAKER_THRESHOLD` | int | (complex) | Circuit breaker threshold | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheServ` |
| `LEX_CLI__SERVICE__DEFAULT_BACKEND` | str  \| None | None | Default backend name | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheServ` |
| `LEX_CLI__SERVICE__DEFAULT_SERIALIZER` | str | (complex) | Default serializer | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheServ` |
| `LEX_CLI__SERVICE__ENABLE_HEALTH_CHECKS` | bool | (complex) | Enable health checks | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheServ` |
| `LEX_CLI__SERVICE__ENABLE_METRICS` | bool | (complex) | Enable metrics | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheServ` |
| `LEX_CLI__SERVICE__ENABLE_PROTECTION` | bool | (complex) | Enable stampede protection | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheServ` |
| `LEX_CLI__SERVICE__MAX_FILE_SIZE_MB` | int | (complex) | Maximum file size in MB | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/storage/config.py:Storage` |
| `LEX_CLI__SERVICE__PROTECTION_LOCK_TTL` | int | (complex) | Protection lock TTL | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheServ` |
| `LEX_CLI__SERVICE__PROTECTION_MAX_WAIT` | float | (complex) | Max wait for locks | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheServ` |
| `LEX_CLI__SERVICE__PROTECTION_RETRY_INTERVAL` | float | (complex) | Lock retry interval | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheServ` |
| `LEX_CLI__SIMILARITY_THRESHOLD` | float | 0.7 | Minimum similarity score threshold | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGConfi` |
| `LEX_CLI__SLO__ALERT_CHANNELS` | list[str] | (required) | Alert channel names for SLO violation dispatch | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:SLOConf` |
| `LEX_CLI__SLO__ENABLED` | bool | True | Enable periodic SLO evaluation worker | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:SLOConf` |
| `LEX_CLI__SLO__EVALUATION_INTERVAL` | float | 60.0 | SLO evaluation interval in seconds | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:SLOConf` |
| `LEX_CLI__SLO__SUPPRESSION_WINDOW_SECONDS` | int | 300 | Alert suppression window in seconds | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:SLOConf` |
| `LEX_CLI__SMS_BACKENDS` | list[NamedSMSConfig] | (required) | Named SMS backends for multi-backend support. When non-empty, the provider registers each backend under Annotated[SMSCha | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/notification/config.py:No` |
| `LEX_CLI__SNAPSHOTS__ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Snapshot` |
| `LEX_CLI__SNAPSHOTS__EVENT_COUNT_THRESHOLD` | int | 100 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Snapshot` |
| `LEX_CLI__SNAPSHOTS__MAX_SNAPSHOTS_PER_AGGREGATE` | int | 5 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Snapshot` |
| `LEX_CLI__SNAPSHOTS__STRATEGY` | SnapshotStrategy | (complex) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Snapshot` |
| `LEX_CLI__SNAPSHOTS__TIME_THRESHOLD_SECONDS` | int | 3600 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Snapshot` |
| `LEX_CLI__SQLITE__DATABASE` | str | "./events.db" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:SqliteCo` |
| `LEX_CLI__SQLITE__JOURNAL_MODE` | str | "WAL" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:SqliteCo` |
| `LEX_CLI__SQLITE__PRAGMAS` | dict[str, str] | (required) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:SqliteCo` |
| `LEX_CLI__SQLITE__WAL_MODE` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:SqliteCo` |
| `LEX_CLI__STDIO_MODE` | bool | False |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/mcp/config.py:MCPConfi` |
| `LEX_CLI__STORE_BACKEND` | str | (complex) | Backend type — 'sql' or 'memory' | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/audit/config.py:AuditConf` |
| `LEX_CLI__STORE_RAW_PAYLOADS` | bool | False | Persist raw incoming feedback payloads for auditing | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/feedback/config.py:Fee` |
| `LEX_CLI__STREAMING__BATCH_SIZE` | int | 100 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Streamin` |
| `LEX_CLI__STREAMING__BUFFER_SIZE` | int | 1000 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Streamin` |
| `LEX_CLI__STREAMING__ENABLE_WEBSOCKET` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Streamin` |
| `LEX_CLI__STREAMING__MAX_SUBSCRIBERS` | int | 100 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Streamin` |
| `LEX_CLI__STREAMING__POLL_INTERVAL_MS` | int | 100 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Streamin` |
| `LEX_CLI__STREAMING__WEBSOCKET_PING_INTERVAL` | int | 30 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Streamin` |
| `LEX_CLI__SUBSCRIPTIONS__CONNECTION_TIMEOUT` | Duration  \| int | 60 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Subscri` |
| `LEX_CLI__SUBSCRIPTIONS__ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Subscri` |
| `LEX_CLI__SUBSCRIPTIONS__KEEPALIVE_INTERVAL` | Duration  \| int | (complex) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Subscri` |
| `LEX_CLI__SUBSCRIPTIONS__PATH` | str | (complex) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Subscri` |
| `LEX_CLI__SUBSCRIPTIONS__PROTOCOL` | SubscriptionProtocol | (complex) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Subscri` |
| `LEX_CLI__SUBSYSTEMS` | dict[str, dict[str, Any]] | (required) | Dynamic configuration for third-party AI subsystems discovered via entry points.  Keys are subsystem names; values are t | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/config.py:AIConfig.sub` |
| `LEX_CLI__SYNTHESIS_STRATEGY` | str | "hybrid" | Synthesis strategy (direct, extractive, abstractive, hybrid) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGConfi` |
| `LEX_CLI__TABLE_NAME` | str | (complex) | SQL table name for the unified audit store | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/audit/config.py:AuditConf` |
| `LEX_CLI__TENANCY__ENABLED` | bool | False | Enable tenant-aware graph resolution | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:GraphTena` |
| `LEX_CLI__TENANCY__ENABLED` | bool | False | Enable tenant-aware collection resolution in RAG pipeline | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGTenan` |
| `LEX_CLI__TENANCY__ENABLED` | bool | False | Enable tenant-aware collection name resolution | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:VectorTe` |
| `LEX_CLI__TENANCY__RESOLVER_KIND` | str | "templated" | Which ``TenantCollectionResolver`` to use. One of ``"templated"`` or ``"pinecone_namespace"``. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:VectorTe` |
| `LEX_CLI__TENANCY__STRATEGY` | str | "node_property" | Which tenancy strategy to use. One of ``"node_property"`` or ``"graph_per_tenant"``. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:GraphTena` |
| `LEX_CLI__TENANCY__TEMPLATE` | str | "{logical}_t_{tenant}" | Collection name template for ``GRAPH_PER_TENANT`` strategy. Supports ``{logical}`` and ``{tenant}`` placeholders. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graph/config.py:GraphTena` |
| `LEX_CLI__TIMEOUT` | TimeoutConfig | field(...) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Resi` |
| `LEX_CLI__TIMEOUT__DEFAULT_TIMEOUT` | float | (complex) | Default timeout | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskTimeo` |
| `LEX_CLI__TIMEOUT__ENFORCE_TIMEOUT` | bool | True | Enforce timeouts | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskTimeo` |
| `LEX_CLI__TIMEOUT__MAX_TIMEOUT` | float | (complex) | Maximum allowed timeout | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskTimeo` |
| `LEX_CLI__TOP_K` | int | 5 | Number of documents to retrieve | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGConfi` |
| `LEX_CLI__TRACE_MAX_ATTRIBUTE_LENGTH` | int | 0 | Cap on string attribute values written to trace spans, in characters. 0 disables the cap. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/observability/config.p` |
| `LEX_CLI__TRACE_REDACTION_ENABLED` | bool | False | Redact secret-shaped keys (e.g. token, password, api_key) from trace span attributes and audit metadata. Strongly recomm | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/observability/config.p` |
| `LEX_CLI__TRACING_ENABLED` | bool | True | Enable distributed tracing | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/observability/config.p` |
| `LEX_CLI__TRACING__ENABLED` | bool | True | Enable tracing | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Tracing` |
| `LEX_CLI__TRACING__ENABLED` | bool | False |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Tracing` |
| `LEX_CLI__TRACING__MAX_ATTRIBUTES` | int | 128 | Max attributes per span | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Tracing` |
| `LEX_CLI__TRACING__MAX_EVENTS` | int | 128 | Max events per span | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Tracing` |
| `LEX_CLI__TRACING__MAX_LINKS` | int | 128 | Max links per span | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Tracing` |
| `LEX_CLI__TRACING__MAX_SPANS` | int | (complex) | Max number of spans to keep in memory | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Tracing` |
| `LEX_CLI__TRACING__MAX_TRACES_PER_SECOND` | int | 100 | Max traces to sample per second | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Tracing` |
| `LEX_CLI__TRACING__PROPAGATION_FORMATS` | list[str] | (required) | Propagation format list | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Tracing` |
| `LEX_CLI__TRACING__SAMPLE_RATE` | float | 1.0 | Sample rate (0.0 to 1.0) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Tracing` |
| `LEX_CLI__TRACING__SAMPLE_RATE` | float | 1.0 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Tracing` |
| `LEX_CLI__TRACING__SERVICE_NAME` | str | (complex) | Service name for traces | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/monitor/config.py:Tracing` |
| `LEX_CLI__TRACING__SERVICE_NAME` | str | "lexigram-graphql" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Tracing` |
| `LEX_CLI__TRACING__TRACE_DATALOADERS` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Tracing` |
| `LEX_CLI__TRACING__TRACE_RESOLVERS` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/graphql/config.py:Tracing` |
| `LEX_CLI__TRANSACTION_MIDDLEWARE__ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Transact` |
| `LEX_CLI__TRANSACTION_MIDDLEWARE__ISOLATION_LEVEL` | str | "READ_COMMITTED" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Transact` |
| `LEX_CLI__TRANSACTION_MIDDLEWARE__TIMEOUT_SECONDS` | float | 30.0 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Transact` |
| `LEX_CLI__UPSERT_BATCH_SIZE` | int | (complex) | Number of vectors per upsert batch | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:VectorCo` |
| `LEX_CLI__USE_HYBRID_SEARCH` | bool | True | Enable hybrid search (semantic + keyword) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGConfi` |
| `LEX_CLI__VALIDATION_MIDDLEWARE__ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Validati` |
| `LEX_CLI__VALIDATION_MIDDLEWARE__STRICT_MODE` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:Validati` |
| `LEX_CLI__VECTOR` | Any  \| None | None | Vector store configuration | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/config.py:AIConfig.vec` |
| `LEX_CLI__VECTOR_DIMENSION` | int | 1536 | Embedding vector dimension (1536 for OpenAI ada-002) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGConfi` |
| `LEX_CLI__VECTOR_STORE_TYPE` | str | "pgvector" | Vector store backend (pgvector, chroma, qdrant, mock) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/ai/rag/config.py:RAGConfi` |
| `LEX_CLI__VERIFICATION_BATCH_SIZE` | int | (complex) | Entries to verify per verification run | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/audit/config.py:AuditConf` |
| `LEX_CLI__VERIFICATION_SCHEDULE` | str | (complex) | Cron expression for scheduled verification | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/audit/config.py:AuditConf` |
| `LEX_CLI__VERSION` | str | (complex) | Config version | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/cache/config.py:CacheConf` |
| `LEX_CLI__VERSION_SKEW_ALERTS_ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/events/config.py:EventsCo` |
| `LEX_CLI__WEAVIATE__API_KEY` | SecretStr  \| None | None | Weaviate API key for authenticated clusters | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Weaviate` |
| `LEX_CLI__WEAVIATE__GRPC_PORT` | int | 50051 | gRPC port for the Weaviate cluster | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Weaviate` |
| `LEX_CLI__WEAVIATE__TIMEOUT` | float | (complex) | Request timeout in seconds | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Weaviate` |
| `LEX_CLI__WEAVIATE__URL` | str | "http://localhost:8080" | Weaviate cluster URL (HTTP) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/config.py:Weaviate` |
| `LEX_CLI__WORKER__DEFAULT_TIMEOUT` | float | (complex) | Default timeout for tasks without an explicit timeout (seconds) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskWorke` |
| `LEX_CLI__WORKER__ENFORCE_TIMEOUT` | bool | True | Whether to enforce timeouts on all tasks | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskWorke` |
| `LEX_CLI__WORKER__MAX_CONCURRENT_TASKS` | int | (complex) | Maximum concurrent tasks per worker | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskWorke` |
| `LEX_CLI__WORKER__MAX_TIMEOUT` | float | (complex) | Maximum allowed timeout for any task (seconds) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskWorke` |
| `LEX_CLI__WORKER__POLL_INTERVAL` | float | (complex) | Interval between queue polls (seconds) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskWorke` |
| `LEX_CLI__WORKER__SHUTDOWN_TIMEOUT` | float | (complex) | Timeout for graceful shutdown (seconds) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskWorke` |
| `LEX_CLI__WORKER__WORKER_COUNT` | int | (complex) | Number of worker instances | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/tasks/config.py:TaskWorke` |
| `LEX_EVENTS__COMMAND_BUS__ENABLE_LOGGING` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:CommandBusConfig.command_bus.enable_logging` |
| `LEX_EVENTS__COMMAND_BUS__ENABLE_METRICS` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:CommandBusConfig.command_bus.enable_metrics` |
| `LEX_EVENTS__COMMAND_BUS__ENABLE_VALIDATION` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:CommandBusConfig.command_bus.enable_validatio` |
| `LEX_EVENTS__COMMAND_BUS__MAX_RETRIES` | int | 3 |  | `packages/lexigram-events/src/lexigram/events/config.py:CommandBusConfig.command_bus.max_retries` |
| `LEX_EVENTS__COMMAND_BUS__RETRY_DELAY_SECONDS` | float | 1.0 |  | `packages/lexigram-events/src/lexigram/events/config.py:CommandBusConfig.command_bus.retry_delay_seco` |
| `LEX_EVENTS__COMMAND_BUS__TIMEOUT_SECONDS` | float | 30.0 |  | `packages/lexigram-events/src/lexigram/events/config.py:CommandBusConfig.command_bus.timeout_seconds` |
| `LEX_EVENTS__DEBUG` | bool | False |  | `packages/lexigram-events/src/lexigram/events/config.py:EventsConfig.debug` |
| `LEX_EVENTS__ENABLED` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:EventsConfig.enabled` |
| `LEX_EVENTS__ENV` | str  \| None | None | Environment (development/staging/production) | `packages/lexigram-events/src/lexigram/events/config.py:EventsConfig.env` |
| `LEX_EVENTS__EVENT_BUS__ALLOW_NO_HANDLERS` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:EventBusConfig.event_bus.allow_no_handlers` |
| `LEX_EVENTS__EVENT_BUS__CONTINUE_ON_ERROR` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:EventBusConfig.event_bus.continue_on_error` |
| `LEX_EVENTS__EVENT_BUS__ENABLE_DEAD_LETTER` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:EventBusConfig.event_bus.enable_dead_letter` |
| `LEX_EVENTS__EVENT_BUS__HANDLER_TIMEOUT_SECONDS` | float | 30.0 |  | `packages/lexigram-events/src/lexigram/events/config.py:EventBusConfig.event_bus.handler_timeout_seco` |
| `LEX_EVENTS__EVENT_BUS__MAX_CONCURRENT_HANDLERS` | int | 10 |  | `packages/lexigram-events/src/lexigram/events/config.py:EventBusConfig.event_bus.max_concurrent_handl` |
| `LEX_EVENTS__EVENT_BUS__MAX_HANDLER_RETRIES` | int | 3 |  | `packages/lexigram-events/src/lexigram/events/config.py:EventBusConfig.event_bus.max_handler_retries` |
| `LEX_EVENTS__EVENT_BUS__MAX_QUEUE_PER_SUBSCRIBER` | int | 1000 | Maximum number of events queued per event type before backpressure is applied. 0 means unbounded (no backpressure). | `packages/lexigram-events/src/lexigram/events/config.py:EventBusConfig.event_bus.max_queue_per_subscr` |
| `LEX_EVENTS__EVENT_BUS__PARALLEL_DISPATCH` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:EventBusConfig.event_bus.parallel_dispatch` |
| `LEX_EVENTS__EVENT_BUS__RETRY_FAILED_HANDLERS` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:EventBusConfig.event_bus.retry_failed_handler` |
| `LEX_EVENTS__EVENT_STORE_BACKEND` | EventStoreBackend | (complex) |  | `packages/lexigram-events/src/lexigram/events/config.py:EventsConfig.event_store_backend` |
| `LEX_EVENTS__KAFKA__AUTO_OFFSET_RESET` | str | "earliest" |  | `packages/lexigram-events/src/lexigram/events/config.py:KafkaConfig.kafka.auto_offset_reset` |
| `LEX_EVENTS__KAFKA__BOOTSTRAP_SERVERS` | str | Ellipsis | Kafka bootstrap servers | `packages/lexigram-events/src/lexigram/events/config.py:KafkaConfig.kafka.bootstrap_servers` |
| `LEX_EVENTS__KAFKA__CONSUMER_GROUP` | str | "events-consumers" |  | `packages/lexigram-events/src/lexigram/events/config.py:KafkaConfig.kafka.consumer_group` |
| `LEX_EVENTS__KAFKA__ENABLE_AUTO_COMMIT` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:KafkaConfig.kafka.enable_auto_commit` |
| `LEX_EVENTS__KAFKA__TOPIC_PREFIX` | str | "events" |  | `packages/lexigram-events/src/lexigram/events/config.py:KafkaConfig.kafka.topic_prefix` |
| `LEX_EVENTS__LOGGING_MIDDLEWARE__ENABLED` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:LoggingMiddlewareConfig.logging_middleware.en` |
| `LEX_EVENTS__LOGGING_MIDDLEWARE__INCLUDE_PAYLOAD` | bool | False |  | `packages/lexigram-events/src/lexigram/events/config.py:LoggingMiddlewareConfig.logging_middleware.in` |
| `LEX_EVENTS__LOGGING_MIDDLEWARE__LOG_LEVEL` | str | "INFO" |  | `packages/lexigram-events/src/lexigram/events/config.py:LoggingMiddlewareConfig.logging_middleware.lo` |
| `LEX_EVENTS__LOGGING_MIDDLEWARE__MAX_PAYLOAD_LENGTH` | int | 1000 |  | `packages/lexigram-events/src/lexigram/events/config.py:LoggingMiddlewareConfig.logging_middleware.ma` |
| `LEX_EVENTS__MEMORY__ENABLE_SNAPSHOTS` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:InMemoryEventStoreConfig.memory.enable_snapsh` |
| `LEX_EVENTS__MEMORY__MAX_EVENTS_PER_STREAM` | int | 10000 |  | `packages/lexigram-events/src/lexigram/events/config.py:InMemoryEventStoreConfig.memory.max_events_pe` |
| `LEX_EVENTS__METRICS_MIDDLEWARE__ENABLED` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:MetricsMiddlewareConfig.metrics_middleware.en` |
| `LEX_EVENTS__METRICS_MIDDLEWARE__HISTOGRAM_BUCKETS` | list[float] | (required) |  | `packages/lexigram-events/src/lexigram/events/config.py:MetricsMiddlewareConfig.metrics_middleware.hi` |
| `LEX_EVENTS__METRICS_MIDDLEWARE__INCLUDE_HISTOGRAMS` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:MetricsMiddlewareConfig.metrics_middleware.in` |
| `LEX_EVENTS__METRICS_MIDDLEWARE__PREFIX` | str | "events" |  | `packages/lexigram-events/src/lexigram/events/config.py:MetricsMiddlewareConfig.metrics_middleware.pr` |
| `LEX_EVENTS__MONGODB__CONNECTION_STRING` | SecretStr | Ellipsis | MongoDB connection string | `packages/lexigram-events/src/lexigram/events/config.py:MongoDBEventStoreConfig.mongodb.connection_st` |
| `LEX_EVENTS__MONGODB__DATABASE_NAME` | str | "events" |  | `packages/lexigram-events/src/lexigram/events/config.py:MongoDBEventStoreConfig.mongodb.database_name` |
| `LEX_EVENTS__MONGODB__EVENTS_COLLECTION` | str | "domain_events" |  | `packages/lexigram-events/src/lexigram/events/config.py:MongoDBEventStoreConfig.mongodb.events_collec` |
| `LEX_EVENTS__MONGODB__MAX_POOL_SIZE` | int | 10 |  | `packages/lexigram-events/src/lexigram/events/config.py:MongoDBEventStoreConfig.mongodb.max_pool_size` |
| `LEX_EVENTS__MONGODB__SERVER_SELECTION_TIMEOUT` | int | 30000 |  | `packages/lexigram-events/src/lexigram/events/config.py:MongoDBEventStoreConfig.mongodb.server_select` |
| `LEX_EVENTS__MONGODB__SNAPSHOTS_COLLECTION` | str | "snapshots" |  | `packages/lexigram-events/src/lexigram/events/config.py:MongoDBEventStoreConfig.mongodb.snapshots_col` |
| `LEX_EVENTS__NAME` | str | "events" |  | `packages/lexigram-events/src/lexigram/events/config.py:EventsConfig.name` |
| `LEX_EVENTS__POSTGRES` | PostgresEventStoreConfig  \| None | None |  | `packages/lexigram-events/src/lexigram/events/config.py:EventsConfig.postgres` |
| `LEX_EVENTS__PROJECTION__BATCH_SIZE` | int | 100 |  | `packages/lexigram-events/src/lexigram/events/config.py:ProjectionConfig.projection.batch_size` |
| `LEX_EVENTS__PROJECTION__CHECKPOINT_INTERVAL` | int | 100 |  | `packages/lexigram-events/src/lexigram/events/config.py:ProjectionConfig.projection.checkpoint_interv` |
| `LEX_EVENTS__PROJECTION__ENABLE_PARALLEL_PROJECTIONS` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:ProjectionConfig.projection.enable_parallel_p` |
| `LEX_EVENTS__PROJECTION__MAX_CATCH_UP_EVENTS` | int | 10000 |  | `packages/lexigram-events/src/lexigram/events/config.py:ProjectionConfig.projection.max_catch_up_even` |
| `LEX_EVENTS__PROJECTION__REBUILD_BATCH_SIZE` | int | 1000 |  | `packages/lexigram-events/src/lexigram/events/config.py:ProjectionConfig.projection.rebuild_batch_siz` |
| `LEX_EVENTS__QUERY_BUS__ENABLE_LOGGING` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:QueryBusConfig.query_bus.enable_logging` |
| `LEX_EVENTS__QUERY_BUS__ENABLE_METRICS` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:QueryBusConfig.query_bus.enable_metrics` |
| `LEX_EVENTS__QUERY_BUS__TIMEOUT_SECONDS` | float | 30.0 |  | `packages/lexigram-events/src/lexigram/events/config.py:QueryBusConfig.query_bus.timeout_seconds` |
| `LEX_EVENTS__RABBITMQ__DURABLE` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:RabbitMQConfig.rabbitmq.durable` |
| `LEX_EVENTS__RABBITMQ__EXCHANGE_NAME` | str | "events" |  | `packages/lexigram-events/src/lexigram/events/config.py:RabbitMQConfig.rabbitmq.exchange_name` |
| `LEX_EVENTS__RABBITMQ__PREFETCH_COUNT` | int | 10 |  | `packages/lexigram-events/src/lexigram/events/config.py:RabbitMQConfig.rabbitmq.prefetch_count` |
| `LEX_EVENTS__RABBITMQ__QUEUE_PREFIX` | str | "events" |  | `packages/lexigram-events/src/lexigram/events/config.py:RabbitMQConfig.rabbitmq.queue_prefix` |
| `LEX_EVENTS__RABBITMQ__URL` | SecretStr | Ellipsis | AMQP connection URL | `packages/lexigram-events/src/lexigram/events/config.py:RabbitMQConfig.rabbitmq.url` |
| `LEX_EVENTS__RETRY_MIDDLEWARE__ENABLED` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:RetryMiddlewareConfig.retry_middleware.enable` |
| `LEX_EVENTS__RETRY_MIDDLEWARE__EXPONENTIAL_BASE` | float | 2.0 |  | `packages/lexigram-events/src/lexigram/events/config.py:RetryMiddlewareConfig.retry_middleware.expone` |
| `LEX_EVENTS__RETRY_MIDDLEWARE__INITIAL_DELAY_SECONDS` | float | 0.1 |  | `packages/lexigram-events/src/lexigram/events/config.py:RetryMiddlewareConfig.retry_middleware.initia` |
| `LEX_EVENTS__RETRY_MIDDLEWARE__MAX_DELAY_SECONDS` | float | 10.0 |  | `packages/lexigram-events/src/lexigram/events/config.py:RetryMiddlewareConfig.retry_middleware.max_de` |
| `LEX_EVENTS__RETRY_MIDDLEWARE__MAX_RETRIES` | int | 3 |  | `packages/lexigram-events/src/lexigram/events/config.py:RetryMiddlewareConfig.retry_middleware.max_re` |
| `LEX_EVENTS__SAGA__CLEANUP_COMPLETED_AFTER_HOURS` | int | 24 |  | `packages/lexigram-events/src/lexigram/events/config.py:SagaConfig.saga.cleanup_completed_after_hours` |
| `LEX_EVENTS__SAGA__DEFAULT_TIMEOUT_SECONDS` | float | 300.0 |  | `packages/lexigram-events/src/lexigram/events/config.py:SagaConfig.saga.default_timeout_seconds` |
| `LEX_EVENTS__SAGA__ENABLE_COMPENSATION` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:SagaConfig.saga.enable_compensation` |
| `LEX_EVENTS__SAGA__MAX_RETRIES_PER_STEP` | int | 3 |  | `packages/lexigram-events/src/lexigram/events/config.py:SagaConfig.saga.max_retries_per_step` |
| `LEX_EVENTS__SAGA__PERSIST_STATE` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:SagaConfig.saga.persist_state` |
| `LEX_EVENTS__SAGA__RETRY_DELAY_SECONDS` | float | 1.0 |  | `packages/lexigram-events/src/lexigram/events/config.py:SagaConfig.saga.retry_delay_seconds` |
| `LEX_EVENTS__SNAPSHOTS__ENABLED` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:SnapshotConfig.snapshots.enabled` |
| `LEX_EVENTS__SNAPSHOTS__EVENT_COUNT_THRESHOLD` | int | 100 |  | `packages/lexigram-events/src/lexigram/events/config.py:SnapshotConfig.snapshots.event_count_threshol` |
| `LEX_EVENTS__SNAPSHOTS__MAX_SNAPSHOTS_PER_AGGREGATE` | int | 5 |  | `packages/lexigram-events/src/lexigram/events/config.py:SnapshotConfig.snapshots.max_snapshots_per_ag` |
| `LEX_EVENTS__SNAPSHOTS__STRATEGY` | SnapshotStrategy | (complex) |  | `packages/lexigram-events/src/lexigram/events/config.py:SnapshotConfig.snapshots.strategy` |
| `LEX_EVENTS__SNAPSHOTS__TIME_THRESHOLD_SECONDS` | int | 3600 |  | `packages/lexigram-events/src/lexigram/events/config.py:SnapshotConfig.snapshots.time_threshold_secon` |
| `LEX_EVENTS__SQLITE__DATABASE` | str | "./events.db" |  | `packages/lexigram-events/src/lexigram/events/config.py:SqliteConfig.sqlite.database` |
| `LEX_EVENTS__SQLITE__JOURNAL_MODE` | str | "WAL" |  | `packages/lexigram-events/src/lexigram/events/config.py:SqliteConfig.sqlite.journal_mode` |
| `LEX_EVENTS__SQLITE__PRAGMAS` | dict[str, str] | (required) |  | `packages/lexigram-events/src/lexigram/events/config.py:SqliteConfig.sqlite.pragmas` |
| `LEX_EVENTS__SQLITE__WAL_MODE` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:SqliteConfig.sqlite.wal_mode` |
| `LEX_EVENTS__STREAMING__BATCH_SIZE` | int | 100 |  | `packages/lexigram-events/src/lexigram/events/config.py:StreamingConfig.streaming.batch_size` |
| `LEX_EVENTS__STREAMING__BUFFER_SIZE` | int | 1000 |  | `packages/lexigram-events/src/lexigram/events/config.py:StreamingConfig.streaming.buffer_size` |
| `LEX_EVENTS__STREAMING__ENABLE_WEBSOCKET` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:StreamingConfig.streaming.enable_websocket` |
| `LEX_EVENTS__STREAMING__MAX_SUBSCRIBERS` | int | 100 |  | `packages/lexigram-events/src/lexigram/events/config.py:StreamingConfig.streaming.max_subscribers` |
| `LEX_EVENTS__STREAMING__POLL_INTERVAL_MS` | int | 100 |  | `packages/lexigram-events/src/lexigram/events/config.py:StreamingConfig.streaming.poll_interval_ms` |
| `LEX_EVENTS__STREAMING__WEBSOCKET_PING_INTERVAL` | int | 30 |  | `packages/lexigram-events/src/lexigram/events/config.py:StreamingConfig.streaming.websocket_ping_inte` |
| `LEX_EVENTS__TRANSACTION_MIDDLEWARE__ENABLED` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:TransactionMiddlewareConfig.transaction_middl` |
| `LEX_EVENTS__TRANSACTION_MIDDLEWARE__ISOLATION_LEVEL` | str | "READ_COMMITTED" |  | `packages/lexigram-events/src/lexigram/events/config.py:TransactionMiddlewareConfig.transaction_middl` |
| `LEX_EVENTS__TRANSACTION_MIDDLEWARE__TIMEOUT_SECONDS` | float | 30.0 |  | `packages/lexigram-events/src/lexigram/events/config.py:TransactionMiddlewareConfig.transaction_middl` |
| `LEX_EVENTS__VALIDATION_MIDDLEWARE__ENABLED` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:ValidationMiddlewareConfig.validation_middlew` |
| `LEX_EVENTS__VALIDATION_MIDDLEWARE__STRICT_MODE` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:ValidationMiddlewareConfig.validation_middlew` |
| `LEX_EVENTS__VERSION_SKEW_ALERTS_ENABLED` | bool | True |  | `packages/lexigram-events/src/lexigram/events/config.py:EventsConfig.version_skew_alerts_enabled` |
| `LEX_FEATURES__CACHE_TTL` | int | DEFAULT_CACHE_TTL | Seconds to cache flag evaluations (0 = disabled). | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/features/config.py:Feat` |
| `LEX_FEATURES__CACHE_TTL` | int | DEFAULT_CACHE_TTL | Seconds to cache flag evaluations (0 = disabled). | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/features/config.py:Featur` |
| `LEX_FEATURES__CACHE_TTL` | int | DEFAULT_CACHE_TTL | Seconds to cache flag evaluations (0 = disabled). | `packages/lexigram-features/src/lexigram/features/config.py:FeatureFlagsConfig.cache_ttl` |
| `LEX_FEATURES__DEFAULT_ENABLED` | bool | DEFAULT_ENABLED | Default value when a flag is not found in the provider. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/features/config.py:Feat` |
| `LEX_FEATURES__DEFAULT_ENABLED` | bool | DEFAULT_ENABLED | Default value when a flag is not found in the provider. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/features/config.py:Featur` |
| `LEX_FEATURES__DEFAULT_ENABLED` | bool | DEFAULT_ENABLED | Default value when a flag is not found in the provider. | `packages/lexigram-features/src/lexigram/features/config.py:FeatureFlagsConfig.default_enabled` |
| `LEX_FEATURES__ENABLED` | bool | True | Enable the feature flags subsystem | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/features/config.py:Feat` |
| `LEX_FEATURES__ENABLED` | bool | True | Enable the feature flags subsystem | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/features/config.py:Featur` |
| `LEX_FEATURES__ENABLED` | bool | True | Enable the feature flags subsystem | `packages/lexigram-features/src/lexigram/features/config.py:FeatureFlagsConfig.enabled` |
| `LEX_FEATURES__FLAG_ENV_PREFIX` | str | FLAG_ENV_PREFIX | Env var prefix used by EnvProvider when reading flag values. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/features/config.py:Feat` |
| `LEX_FEATURES__FLAG_ENV_PREFIX` | str | FLAG_ENV_PREFIX | Env var prefix used by EnvProvider when reading flag values. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/features/config.py:Featur` |
| `LEX_FEATURES__FLAG_ENV_PREFIX` | str | FLAG_ENV_PREFIX | Env var prefix used by EnvProvider when reading flag values. | `packages/lexigram-features/src/lexigram/features/config.py:FeatureFlagsConfig.flag_env_prefix` |
| `LEX_FEATURES__INITIAL_FLAGS` | dict[str, bool] | (required) | Seed flags for the in-memory provider (name -> enabled). | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/features/config.py:Feat` |
| `LEX_FEATURES__INITIAL_FLAGS` | dict[str, bool] | (required) | Seed flags for the in-memory provider (name -> enabled). | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/features/config.py:Featur` |
| `LEX_FEATURES__INITIAL_FLAGS` | dict[str, bool] | (required) | Seed flags for the in-memory provider (name -> enabled). | `packages/lexigram-features/src/lexigram/features/config.py:FeatureFlagsConfig.initial_flags` |
| `LEX_GRAPHQL__ALIAS_LIMIT__ENABLED` | bool | True |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:AliasLimitConfig.alias_limit.enabled` |
| `LEX_GRAPHQL__ALIAS_LIMIT__MAX_ALIASES` | int | (complex) |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:AliasLimitConfig.alias_limit.max_aliases` |
| `LEX_GRAPHQL__BATCH__ENABLED` | bool | False |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:BatchConfig.batch.enabled` |
| `LEX_GRAPHQL__BATCH__MAX_BATCH_SIZE` | int | 10 |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:BatchConfig.batch.max_batch_size` |
| `LEX_GRAPHQL__CACHE__DEFAULT_MAX_AGE` | Duration  \| int | (complex) |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:CacheConfig.cache.default_max_age` |
| `LEX_GRAPHQL__CACHE__DEFAULT_SCOPE` | CacheScope | (complex) |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:CacheConfig.cache.default_scope` |
| `LEX_GRAPHQL__CACHE__ENABLED` | bool | True |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:CacheConfig.cache.enabled` |
| `LEX_GRAPHQL__CACHE__VARY_HEADERS` | list[str] | (required) |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:CacheConfig.cache.vary_headers` |
| `LEX_GRAPHQL__COMPLEXITY__DEFAULT_FIELD_COST` | float | 1.0 |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:ComplexityConfig.complexity.default_field_c` |
| `LEX_GRAPHQL__COMPLEXITY__DEFAULT_LIST_COST` | float | 10.0 |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:ComplexityConfig.complexity.default_list_co` |
| `LEX_GRAPHQL__COMPLEXITY__ENABLED` | bool | True |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:ComplexityConfig.complexity.enabled` |
| `LEX_GRAPHQL__COMPLEXITY__MAX_COMPLEXITY` | int | (complex) |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:ComplexityConfig.complexity.max_complexity` |
| `LEX_GRAPHQL__DATALOADER__BATCH_DELAY_MS` | float | 2.0 | Delay in milliseconds before executing a DataLoaderProtocol batch. A small non-zero value (2ms) lets more keys accumulat | `packages/lexigram-graphql/src/lexigram/graphql/config.py:DataLoaderConfig.dataloader.batch_delay_ms` |
| `LEX_GRAPHQL__DATALOADER__BATCH_ENABLED` | bool | True |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:DataLoaderConfig.dataloader.batch_enabled` |
| `LEX_GRAPHQL__DATALOADER__CACHE_ENABLED` | bool | True |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:DataLoaderConfig.dataloader.cache_enabled` |
| `LEX_GRAPHQL__DATALOADER__ENABLED` | bool | True |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:DataLoaderConfig.dataloader.enabled` |
| `LEX_GRAPHQL__DATALOADER__MAX_BATCH_SIZE` | int | 100 |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:DataLoaderConfig.dataloader.max_batch_size` |
| `LEX_GRAPHQL__DEBUG` | bool | False |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:GraphQLConfig.debug` |
| `LEX_GRAPHQL__DEPTH_LIMIT__ENABLED` | bool | True |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:DepthLimitConfig.depth_limit.enabled` |
| `LEX_GRAPHQL__DEPTH_LIMIT__IGNORE_INTROSPECTION` | bool | True |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:DepthLimitConfig.depth_limit.ignore_introsp` |
| `LEX_GRAPHQL__DEPTH_LIMIT__MAX_DEPTH` | int | (complex) |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:DepthLimitConfig.depth_limit.max_depth` |
| `LEX_GRAPHQL__ENABLED` | bool | True |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:GraphQLConfig.enabled` |
| `LEX_GRAPHQL__ENABLE_IDENTITY_RESOLUTION` | bool | False |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:GraphQLConfig.enable_identity_resolution` |
| `LEX_GRAPHQL__ENV` | str  \| None | None | Environment (development/staging/production) | `packages/lexigram-graphql/src/lexigram/graphql/config.py:GraphQLConfig.env` |
| `LEX_GRAPHQL__ERRORS__DEBUG_MODE` | bool | False |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:ErrorConfig.errors.debug_mode` |
| `LEX_GRAPHQL__ERRORS__INCLUDE_STACKTRACE` | bool | False |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:ErrorConfig.errors.include_stacktrace` |
| `LEX_GRAPHQL__ERRORS__LOG_ERRORS` | bool | True |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:ErrorConfig.errors.log_errors` |
| `LEX_GRAPHQL__ERRORS__MASK_ERRORS` | bool | True |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:ErrorConfig.errors.mask_errors` |
| `LEX_GRAPHQL__INTROSPECTION__ALLOWED_ENVIRONMENTS` | set[str] | (required) |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:IntrospectionConfig.introspection.allowed_e` |
| `LEX_GRAPHQL__INTROSPECTION__ENABLED` | bool | True |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:IntrospectionConfig.introspection.enabled` |
| `LEX_GRAPHQL__METRICS__ENABLED` | bool | False |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:MetricsConfig.metrics.enabled` |
| `LEX_GRAPHQL__METRICS__HISTOGRAM_BUCKETS` | list[float] | (required) |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:MetricsConfig.metrics.histogram_buckets` |
| `LEX_GRAPHQL__METRICS__INCLUDE_LABELS` | list[str] | (required) |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:MetricsConfig.metrics.include_labels` |
| `LEX_GRAPHQL__METRICS__NAMESPACE` | str | "lexigram_graphql" |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:MetricsConfig.metrics.namespace` |
| `LEX_GRAPHQL__NAME` | str | "graphql" |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:GraphQLConfig.name` |
| `LEX_GRAPHQL__PATH` | str | (complex) |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:GraphQLConfig.path` |
| `LEX_GRAPHQL__PERSISTED_QUERIES__ENABLED` | bool | True |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:PersistedQueryConfig.persisted_queries.enab` |
| `LEX_GRAPHQL__PERSISTED_QUERIES__STORE_TYPE` | str | "memory" |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:PersistedQueryConfig.persisted_queries.stor` |
| `LEX_GRAPHQL__PERSISTED_QUERIES__TTL_SECONDS` | Duration  \| int | 86400 |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:PersistedQueryConfig.persisted_queries.ttl_` |
| `LEX_GRAPHQL__PLAYGROUND__ENABLED` | bool | True |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:PlaygroundConfig.playground.enabled` |
| `LEX_GRAPHQL__PLAYGROUND__PATH` | str | (complex) |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:PlaygroundConfig.playground.path` |
| `LEX_GRAPHQL__PLAYGROUND__TITLE` | str | "Lexigram GraphQL Playground" |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:PlaygroundConfig.playground.title` |
| `LEX_GRAPHQL__RATE_LIMIT` | RateLimitConfig | (required) |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:GraphQLConfig.rate_limit` |
| `LEX_GRAPHQL__SCHEMA_BASELINE_PATH` | str  \| None | None | Path to a GraphQL SDL (.graphql) file containing the baseline schema. When set, GraphQLProvider.boot() compares the curr | `packages/lexigram-graphql/src/lexigram/graphql/config.py:GraphQLConfig.schema_baseline_path` |
| `LEX_GRAPHQL__SUBSCRIPTIONS__CONNECTION_TIMEOUT` | Duration  \| int | 60 |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:SubscriptionConfig.subscriptions.connection` |
| `LEX_GRAPHQL__SUBSCRIPTIONS__ENABLED` | bool | True |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:SubscriptionConfig.subscriptions.enabled` |
| `LEX_GRAPHQL__SUBSCRIPTIONS__KEEPALIVE_INTERVAL` | Duration  \| int | (complex) |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:SubscriptionConfig.subscriptions.keepalive_` |
| `LEX_GRAPHQL__SUBSCRIPTIONS__PATH` | str | (complex) |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:SubscriptionConfig.subscriptions.path` |
| `LEX_GRAPHQL__SUBSCRIPTIONS__PROTOCOL` | SubscriptionProtocol | (complex) |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:SubscriptionConfig.subscriptions.protocol` |
| `LEX_GRAPHQL__TRACING__ENABLED` | bool | False |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:TracingConfig.tracing.enabled` |
| `LEX_GRAPHQL__TRACING__SAMPLE_RATE` | float | 1.0 |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:TracingConfig.tracing.sample_rate` |
| `LEX_GRAPHQL__TRACING__SERVICE_NAME` | str | "lexigram-graphql" |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:TracingConfig.tracing.service_name` |
| `LEX_GRAPHQL__TRACING__TRACE_DATALOADERS` | bool | True |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:TracingConfig.tracing.trace_dataloaders` |
| `LEX_GRAPHQL__TRACING__TRACE_RESOLVERS` | bool | True |  | `packages/lexigram-graphql/src/lexigram/graphql/config.py:TracingConfig.tracing.trace_resolvers` |
| `LEX_GRAPH__BACKEND` | str | (complex) | Graph store backend to use | `packages/lexigram-graph/src/lexigram/graph/config.py:GraphConfig.backend` |
| `LEX_GRAPH__BULK_BATCH_SIZE` | int | (complex) | Batch size for bulk operations | `packages/lexigram-graph/src/lexigram/graph/config.py:GraphConfig.bulk_batch_size` |
| `LEX_GRAPH__DEFAULT_QUERY_LIMIT` | int | (complex) | Default limit for query results | `packages/lexigram-graph/src/lexigram/graph/config.py:GraphConfig.default_query_limit` |
| `LEX_GRAPH__DEFAULT_TRAVERSAL_MAX_DEPTH` | int | (complex) | Default maximum depth for traversals | `packages/lexigram-graph/src/lexigram/graph/config.py:GraphConfig.default_traversal_max_depth` |
| `LEX_GRAPH__ENABLED` | bool | True | Enable the graph store subsystem | `packages/lexigram-graph/src/lexigram/graph/config.py:GraphConfig.enabled` |
| `LEX_GRAPH__MAX_RETRIES` | int | (complex) | Maximum number of retries for operations | `packages/lexigram-graph/src/lexigram/graph/config.py:GraphConfig.max_retries` |
| `LEX_GRAPH__MEMORY__MAX_EDGES` | int | (complex) | Maximum number of edges in memory | `packages/lexigram-graph/src/lexigram/graph/config.py:MemoryConfig.memory.max_edges` |
| `LEX_GRAPH__MEMORY__MAX_NODES` | int | (complex) | Maximum number of nodes in memory | `packages/lexigram-graph/src/lexigram/graph/config.py:MemoryConfig.memory.max_nodes` |
| `LEX_GRAPH__NEO4J__CONNECTION_TIMEOUT` | float | (complex) | Connection timeout in seconds | `packages/lexigram-graph/src/lexigram/graph/config.py:Neo4jConfig.neo4j.connection_timeout` |
| `LEX_GRAPH__NEO4J__DATABASE` | str | (complex) | Target database name | `packages/lexigram-graph/src/lexigram/graph/config.py:Neo4jConfig.neo4j.database` |
| `LEX_GRAPH__NEO4J__ENCRYPTED` | bool | False | Whether to use SSL/TLS encryption | `packages/lexigram-graph/src/lexigram/graph/config.py:Neo4jConfig.neo4j.encrypted` |
| `LEX_GRAPH__NEO4J__FETCH_SIZE` | int | (complex) | Default fetch size for results | `packages/lexigram-graph/src/lexigram/graph/config.py:Neo4jConfig.neo4j.fetch_size` |
| `LEX_GRAPH__NEO4J__MAX_CONNECTION_POOL_SIZE` | int | (complex) | Maximum number of connections in the pool | `packages/lexigram-graph/src/lexigram/graph/config.py:Neo4jConfig.neo4j.max_connection_pool_size` |
| `LEX_GRAPH__NEO4J__MAX_TRANSACTION_RETRY_TIME` | float | 30.0 | Maximum time for transaction retries | `packages/lexigram-graph/src/lexigram/graph/config.py:Neo4jConfig.neo4j.max_transaction_retry_time` |
| `LEX_GRAPH__NEO4J__PASSWORD` | SecretStr | (required) | Neo4j password | `packages/lexigram-graph/src/lexigram/graph/config.py:Neo4jConfig.neo4j.password` |
| `LEX_GRAPH__NEO4J__TRUST` | str | "TRUST_SYSTEM_CA_SIGNED_CERTIFICATES" | Trust strategy for SSL | `packages/lexigram-graph/src/lexigram/graph/config.py:Neo4jConfig.neo4j.trust` |
| `LEX_GRAPH__NEO4J__URI` | str | "bolt://localhost:7687" | Neo4j BOLT URI | `packages/lexigram-graph/src/lexigram/graph/config.py:Neo4jConfig.neo4j.uri` |
| `LEX_GRAPH__NEO4J__USERNAME` | str | "neo4j" | Neo4j username | `packages/lexigram-graph/src/lexigram/graph/config.py:Neo4jConfig.neo4j.username` |
| `LEX_GRAPH__RETRY_DELAY` | float | (complex) | Delay between retries in seconds | `packages/lexigram-graph/src/lexigram/graph/config.py:GraphConfig.retry_delay` |
| `LEX_GRAPH__TENANCY__ENABLED` | bool | False | Enable tenant-aware graph resolution | `packages/lexigram-graph/src/lexigram/graph/config.py:GraphTenancyConfig.tenancy.enabled` |
| `LEX_GRAPH__TENANCY__STRATEGY` | str | "node_property" | Which tenancy strategy to use. One of ``"node_property"`` or ``"graph_per_tenant"``. | `packages/lexigram-graph/src/lexigram/graph/config.py:GraphTenancyConfig.tenancy.strategy` |
| `LEX_GRAPH__TENANCY__TEMPLATE` | str | "{logical}_t_{tenant}" | Collection name template for ``GRAPH_PER_TENANT`` strategy. Supports ``{logical}`` and ``{tenant}`` placeholders. | `packages/lexigram-graph/src/lexigram/graph/config.py:GraphTenancyConfig.tenancy.template` |
| `LEX_MONITOR__DEBUG` | bool | False | Enable debug mode | `packages/lexigram-monitor/src/lexigram/monitor/config.py:MonitorConfig.debug` |
| `LEX_MONITOR__ENABLED` | bool | True | Enable monitoring | `packages/lexigram-monitor/src/lexigram/monitor/config.py:MonitorConfig.enabled` |
| `LEX_MONITOR__ENV` | str  \| None | None | Environment (development/staging/production) | `packages/lexigram-monitor/src/lexigram/monitor/config.py:MonitorConfig.env` |
| `LEX_MONITOR__ENVIRONMENT` | Environment | (complex) | Deployment environment | `packages/lexigram-monitor/src/lexigram/monitor/config.py:MonitorConfig.environment` |
| `LEX_MONITOR__ERROR_TRACKING__DSN` | str  \| None | None | Sentry DSN; error tracking is a no-op when unset | `packages/lexigram-monitor/src/lexigram/monitor/config.py:ErrorTrackingConfig.error_tracking.dsn` |
| `LEX_MONITOR__ERROR_TRACKING__ENVIRONMENT` | str  \| None | None | Environment tag for captured events | `packages/lexigram-monitor/src/lexigram/monitor/config.py:ErrorTrackingConfig.error_tracking.environm` |
| `LEX_MONITOR__ERROR_TRACKING__SEND_DEFAULT_PII` | bool | False | Send default PII fields to the error tracker | `packages/lexigram-monitor/src/lexigram/monitor/config.py:ErrorTrackingConfig.error_tracking.send_def` |
| `LEX_MONITOR__ERROR_TRACKING__TRACES_SAMPLE_RATE` | float | 1.0 | Traces sample rate (0.0 to 1.0) | `packages/lexigram-monitor/src/lexigram/monitor/config.py:ErrorTrackingConfig.error_tracking.traces_s` |
| `LEX_MONITOR__HEALTH__CHECKS` | list[str] | (required) | List of health check names to run | `packages/lexigram-monitor/src/lexigram/monitor/config.py:HealthCheckConfig.health.checks` |
| `LEX_MONITOR__HEALTH__ENABLED` | bool | True | Enable health checks | `packages/lexigram-monitor/src/lexigram/monitor/config.py:HealthCheckConfig.health.enabled` |
| `LEX_MONITOR__HEALTH__INCLUDE_DETAILS` | bool | True | Include detailed health info in response | `packages/lexigram-monitor/src/lexigram/monitor/config.py:HealthCheckConfig.health.include_details` |
| `LEX_MONITOR__HEALTH__INTERVAL` | int | (complex) | Health check interval in seconds | `packages/lexigram-monitor/src/lexigram/monitor/config.py:HealthCheckConfig.health.interval` |
| `LEX_MONITOR__HEALTH__PATH` | str | "/health" | Health endpoint path | `packages/lexigram-monitor/src/lexigram/monitor/config.py:HealthCheckConfig.health.path` |
| `LEX_MONITOR__HEALTH__TIMEOUT` | float | 5.0 | Health check timeout in seconds | `packages/lexigram-monitor/src/lexigram/monitor/config.py:HealthCheckConfig.health.timeout` |
| `LEX_MONITOR__METRICS__COLLECTION_INTERVAL` | float | 60.0 | Metrics collection interval in seconds | `packages/lexigram-monitor/src/lexigram/monitor/config.py:MetricsConfig.metrics.collection_interval` |
| `LEX_MONITOR__METRICS__DEFAULT_LABELS` | dict[str, str] | (required) | Default labels for all metrics | `packages/lexigram-monitor/src/lexigram/monitor/config.py:MetricsConfig.metrics.default_labels` |
| `LEX_MONITOR__METRICS__ENABLED` | bool | True | Enable metrics collection | `packages/lexigram-monitor/src/lexigram/monitor/config.py:MetricsConfig.metrics.enabled` |
| `LEX_MONITOR__METRICS__HISTOGRAM_BUCKETS` | list[float] | (required) | Default histogram bucket boundaries | `packages/lexigram-monitor/src/lexigram/monitor/config.py:MetricsConfig.metrics.histogram_buckets` |
| `LEX_MONITOR__METRICS__PREFIX` | str | (complex) | MetricProtocol name prefix | `packages/lexigram-monitor/src/lexigram/monitor/config.py:MetricsConfig.metrics.prefix` |
| `LEX_MONITOR__NAME` | str | (complex) | Provider name | `packages/lexigram-monitor/src/lexigram/monitor/config.py:MonitorConfig.name` |
| `LEX_MONITOR__OPENTELEMETRY__BATCH_SIZE` | int | 512 | Export batch size | `packages/lexigram-monitor/src/lexigram/monitor/config.py:OpenTelemetryConfig.opentelemetry.batch_siz` |
| `LEX_MONITOR__OPENTELEMETRY__COMPRESSION` | str | "none" | Compression type (none, gzip) | `packages/lexigram-monitor/src/lexigram/monitor/config.py:OpenTelemetryConfig.opentelemetry.compressi` |
| `LEX_MONITOR__OPENTELEMETRY__ENDPOINT` | str  \| None | None | OTLP endpoint URL | `packages/lexigram-monitor/src/lexigram/monitor/config.py:OpenTelemetryConfig.opentelemetry.endpoint` |
| `LEX_MONITOR__OPENTELEMETRY__EXPORT_INTERVAL` | float | 5.0 | Export interval seconds | `packages/lexigram-monitor/src/lexigram/monitor/config.py:OpenTelemetryConfig.opentelemetry.export_in` |
| `LEX_MONITOR__OPENTELEMETRY__HEADERS` | dict[str, str] | (required) | OTLP request headers | `packages/lexigram-monitor/src/lexigram/monitor/config.py:OpenTelemetryConfig.opentelemetry.headers` |
| `LEX_MONITOR__OPENTELEMETRY__INSECURE` | bool | False | Use insecure connection | `packages/lexigram-monitor/src/lexigram/monitor/config.py:OpenTelemetryConfig.opentelemetry.insecure` |
| `LEX_MONITOR__OPENTELEMETRY__METRICS_EXPORTERS` | list[OTelExporterConfig] | (required) | List of metrics exporters to build. | `packages/lexigram-monitor/src/lexigram/monitor/config.py:OpenTelemetryConfig.opentelemetry.metrics_e` |
| `LEX_MONITOR__OPENTELEMETRY__TIMEOUT` | float | 30.0 | Export timeout seconds | `packages/lexigram-monitor/src/lexigram/monitor/config.py:OpenTelemetryConfig.opentelemetry.timeout` |
| `LEX_MONITOR__OPENTELEMETRY__TRACING_EXPORTERS` | list[OTelExporterConfig] | (required) | List of tracing exporters to build. | `packages/lexigram-monitor/src/lexigram/monitor/config.py:OpenTelemetryConfig.opentelemetry.tracing_e` |
| `LEX_MONITOR__PROMETHEUS__ENABLE_DEFAULT_METRICS` | bool | True | Enable default process metrics | `packages/lexigram-monitor/src/lexigram/monitor/config.py:PrometheusConfig.prometheus.enable_default_` |
| `LEX_MONITOR__PROMETHEUS__METRICS_TABLE` | str | "metrics_samples" | Table name for metrics samples | `packages/lexigram-monitor/src/lexigram/monitor/config.py:PrometheusConfig.prometheus.metrics_table` |
| `LEX_MONITOR__PROMETHEUS__PATH` | str | "/metrics" | Metrics endpoint path | `packages/lexigram-monitor/src/lexigram/monitor/config.py:PrometheusConfig.prometheus.path` |
| `LEX_MONITOR__PROMETHEUS__PORT` | int | (complex) | Metrics server port | `packages/lexigram-monitor/src/lexigram/monitor/config.py:PrometheusConfig.prometheus.port` |
| `LEX_MONITOR__PROMETHEUS__PUSHGATEWAY_URL` | str  \| None | None | Pushgateway URL for push-based metrics | `packages/lexigram-monitor/src/lexigram/monitor/config.py:PrometheusConfig.prometheus.pushgateway_url` |
| `LEX_MONITOR__PROMETHEUS__PUSH_INTERVAL` | float | 10.0 | Push interval for Pushgateway | `packages/lexigram-monitor/src/lexigram/monitor/config.py:PrometheusConfig.prometheus.push_interval` |
| `LEX_MONITOR__PROMETHEUS__STORE_IN_DB` | bool | False | Persist metrics observations to DB | `packages/lexigram-monitor/src/lexigram/monitor/config.py:PrometheusConfig.prometheus.store_in_db` |
| `LEX_MONITOR__SLO__ALERT_CHANNELS` | list[str] | (required) | Alert channel names for SLO violation dispatch | `packages/lexigram-monitor/src/lexigram/monitor/config.py:SLOConfig.slo.alert_channels` |
| `LEX_MONITOR__SLO__ENABLED` | bool | True | Enable periodic SLO evaluation worker | `packages/lexigram-monitor/src/lexigram/monitor/config.py:SLOConfig.slo.enabled` |
| `LEX_MONITOR__SLO__EVALUATION_INTERVAL` | float | 60.0 | SLO evaluation interval in seconds | `packages/lexigram-monitor/src/lexigram/monitor/config.py:SLOConfig.slo.evaluation_interval` |
| `LEX_MONITOR__SLO__SUPPRESSION_WINDOW_SECONDS` | int | 300 | Alert suppression window in seconds | `packages/lexigram-monitor/src/lexigram/monitor/config.py:SLOConfig.slo.suppression_window_seconds` |
| `LEX_MONITOR__TRACING__ENABLED` | bool | True | Enable tracing | `packages/lexigram-monitor/src/lexigram/monitor/config.py:TracingConfig.tracing.enabled` |
| `LEX_MONITOR__TRACING__MAX_ATTRIBUTES` | int | 128 | Max attributes per span | `packages/lexigram-monitor/src/lexigram/monitor/config.py:TracingConfig.tracing.max_attributes` |
| `LEX_MONITOR__TRACING__MAX_EVENTS` | int | 128 | Max events per span | `packages/lexigram-monitor/src/lexigram/monitor/config.py:TracingConfig.tracing.max_events` |
| `LEX_MONITOR__TRACING__MAX_LINKS` | int | 128 | Max links per span | `packages/lexigram-monitor/src/lexigram/monitor/config.py:TracingConfig.tracing.max_links` |
| `LEX_MONITOR__TRACING__MAX_SPANS` | int | (complex) | Max number of spans to keep in memory | `packages/lexigram-monitor/src/lexigram/monitor/config.py:TracingConfig.tracing.max_spans` |
| `LEX_MONITOR__TRACING__MAX_TRACES_PER_SECOND` | int | 100 | Max traces to sample per second | `packages/lexigram-monitor/src/lexigram/monitor/config.py:TracingConfig.tracing.max_traces_per_second` |
| `LEX_MONITOR__TRACING__PROPAGATION_FORMATS` | list[str] | (required) | Propagation format list | `packages/lexigram-monitor/src/lexigram/monitor/config.py:TracingConfig.tracing.propagation_formats` |
| `LEX_MONITOR__TRACING__SAMPLE_RATE` | float | 1.0 | Sample rate (0.0 to 1.0) | `packages/lexigram-monitor/src/lexigram/monitor/config.py:TracingConfig.tracing.sample_rate` |
| `LEX_MONITOR__TRACING__SERVICE_NAME` | str | (complex) | Service name for traces | `packages/lexigram-monitor/src/lexigram/monitor/config.py:TracingConfig.tracing.service_name` |
| `LEX_NOSQL__BACKENDS` | list[NamedNoSQLConfig] | (required) | Named NoSQL backends for multi-store support. When non-empty, the provider registers each backend under Annotated[Docume | `packages/lexigram-nosql/src/lexigram/nosql/config.py:NoSQLConfig.backends` |
| `LEX_NOSQL__DRIVER` | str | "mongodb" | NoSQL driver name | `packages/lexigram-nosql/src/lexigram/nosql/config.py:NoSQLConfig.driver` |
| `LEX_NOSQL__ENABLED` | bool | True | Enable NoSQL support | `packages/lexigram-nosql/src/lexigram/nosql/config.py:NoSQLConfig.enabled` |
| `LEX_NOSQL__FIRESTORE__CREDENTIALS_JSON` | str  \| None | None | Path to a service account JSON key file, or the raw JSON string. When ``None``, Application Default Credentials (ADC) ar | `packages/lexigram-nosql/src/lexigram/nosql/config.py:FirestoreConfig.firestore.credentials_json` |
| `LEX_NOSQL__FIRESTORE__DATABASE_ID` | str | "(default)" | Firestore database ID (use '(default)' for the default database) | `packages/lexigram-nosql/src/lexigram/nosql/config.py:FirestoreConfig.firestore.database_id` |
| `LEX_NOSQL__FIRESTORE__PROJECT_ID` | str | Ellipsis | Google Cloud project ID | `packages/lexigram-nosql/src/lexigram/nosql/config.py:FirestoreConfig.firestore.project_id` |
| `LEX_NOSQL__MONGODB__AUTH_SOURCE` | str | "admin" | Authentication database | `packages/lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.auth_source` |
| `LEX_NOSQL__MONGODB__CONNECT_TIMEOUT_MS` | int | 10000 | Connection timeout (ms) | `packages/lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.connect_timeout_ms` |
| `LEX_NOSQL__MONGODB__DATABASE` | str | "lexigram" | Database name | `packages/lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.database` |
| `LEX_NOSQL__MONGODB__MAX_POOL_SIZE` | int | 100 | Maximum connection pool size | `packages/lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.max_pool_size` |
| `LEX_NOSQL__MONGODB__MIN_POOL_SIZE` | int | 10 | Minimum connection pool size | `packages/lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.min_pool_size` |
| `LEX_NOSQL__MONGODB__READ_PREFERENCE` | str | "primaryPreferred" | Read preference mode | `packages/lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.read_preference` |
| `LEX_NOSQL__MONGODB__RETRY_READS` | bool | True | Enable read retries | `packages/lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.retry_reads` |
| `LEX_NOSQL__MONGODB__RETRY_WRITES` | bool | True | Enable write retries | `packages/lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.retry_writes` |
| `LEX_NOSQL__MONGODB__SERVER_SELECTION_TIMEOUT_MS` | int | 5000 | Server selection timeout (ms) | `packages/lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.server_selection_timeout_` |
| `LEX_NOSQL__MONGODB__SOCKET_TIMEOUT_MS` | int | 30000 | Socket timeout (ms) | `packages/lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.socket_timeout_ms` |
| `LEX_NOSQL__MONGODB__URI` | str | "mongodb://localhost:27017" | MongoDB connection URI | `packages/lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.uri` |
| `LEX_NOSQL__MONGODB__WRITE_CONCERN_W` | str  \| int | "majority" | Write concern level | `packages/lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.write_concern_w` |
| `LEX_NOTIFICATION__INBOX__MARK_READ_ON_FETCH` | bool | False | Automatically mark messages as read when fetched. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/notification/config.py:` |
| `LEX_NOTIFICATION__INBOX__MARK_READ_ON_FETCH` | bool | False | Automatically mark messages as read when fetched. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/notification/config.py:In` |
| `LEX_NOTIFICATION__INBOX__MARK_READ_ON_FETCH` | bool | False | Automatically mark messages as read when fetched. | `packages/lexigram-notification/src/lexigram/notification/config.py:InboxConfig.mark_read_on_fetch` |
| `LEX_NOTIFICATION__INBOX__MAX_PAGE_SIZE` | int | 50 | Maximum messages returned per page. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/notification/config.py:` |
| `LEX_NOTIFICATION__INBOX__MAX_PAGE_SIZE` | int | 50 | Maximum messages returned per page. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/notification/config.py:In` |
| `LEX_NOTIFICATION__INBOX__MAX_PAGE_SIZE` | int | 50 | Maximum messages returned per page. | `packages/lexigram-notification/src/lexigram/notification/config.py:InboxConfig.max_page_size` |
| `LEX_NOTIFICATION__INBOX__RETENTION_DAYS` | int | 30 | Days to retain inbox messages before pruning. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/notification/config.py:` |
| `LEX_NOTIFICATION__INBOX__RETENTION_DAYS` | int | 30 | Days to retain inbox messages before pruning. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/notification/config.py:In` |
| `LEX_NOTIFICATION__INBOX__RETENTION_DAYS` | int | 30 | Days to retain inbox messages before pruning. | `packages/lexigram-notification/src/lexigram/notification/config.py:InboxConfig.retention_days` |
| `LEX_NOTIFICATION__INBOX__STORE_BACKEND` | str | "database" | Storage backend. One of 'database' or 'memory'. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/notification/config.py:` |
| `LEX_NOTIFICATION__INBOX__STORE_BACKEND` | str | "database" | Storage backend. One of 'database' or 'memory'. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/notification/config.py:In` |
| `LEX_NOTIFICATION__INBOX__STORE_BACKEND` | str | "database" | Storage backend. One of 'database' or 'memory'. | `packages/lexigram-notification/src/lexigram/notification/config.py:InboxConfig.store_backend` |
| `LEX_NOTIFICATION__MAILER__BACKENDS` | list[NamedMailerConfig] | (required) | Named mailer backends for multi-backend support. When non-empty, the provider registers each backend under Annotated[Mai | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/notification/config.py:` |
| `LEX_NOTIFICATION__MAILER__BACKENDS` | list[NamedMailerConfig] | (required) | Named mailer backends for multi-backend support. When non-empty, the provider registers each backend under Annotated[Mai | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/notification/config.py:Ma` |
| `LEX_NOTIFICATION__MAILER__BACKENDS` | list[NamedMailerConfig] | (required) | Named mailer backends for multi-backend support. When non-empty, the provider registers each backend under Annotated[Mai | `packages/lexigram-notification/src/lexigram/notification/config.py:MailerConfig.backends` |
| `LEX_NOTIFICATION__MAILER__CONSOLE_FALLBACK` | bool | True | When no backends are configured, bind a ConsoleMailer as the default MailerProtocol so emails are logged to the applicat | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/notification/config.py:` |
| `LEX_NOTIFICATION__MAILER__CONSOLE_FALLBACK` | bool | True | When no backends are configured, bind a ConsoleMailer as the default MailerProtocol so emails are logged to the applicat | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/notification/config.py:Ma` |
| `LEX_NOTIFICATION__MAILER__CONSOLE_FALLBACK` | bool | True | When no backends are configured, bind a ConsoleMailer as the default MailerProtocol so emails are logged to the applicat | `packages/lexigram-notification/src/lexigram/notification/config.py:MailerConfig.console_fallback` |
| `LEX_NOTIFICATION__PUSH_BACKENDS` | list[NamedPushConfig] | (required) | Named push notification backends for multi-backend support. When non-empty, the provider registers each backend under An | `packages/lexigram-notification/src/lexigram/notification/config.py:NotificationConfig.push_backends` |
| `LEX_NOTIFICATION__SMS_BACKENDS` | list[NamedSMSConfig] | (required) | Named SMS backends for multi-backend support. When non-empty, the provider registers each backend under Annotated[SMSCha | `packages/lexigram-notification/src/lexigram/notification/config.py:NotificationConfig.sms_backends` |
| `LEX_RESILIENCE__BULKHEAD__MAX_CONCURRENT` | int | 10 | Max concurrent requests | `packages/lexigram-resilience/src/lexigram/resilience/config.py:BulkheadConfig.bulkhead.max_concurren` |
| `LEX_RESILIENCE__BULKHEAD__NAME` | str | "" | Bulkhead name | `packages/lexigram-resilience/src/lexigram/resilience/config.py:BulkheadConfig.bulkhead.name` |
| `LEX_RESILIENCE__BULKHEAD__QUEUE_SIZE` | int | 100 | Max queue size | `packages/lexigram-resilience/src/lexigram/resilience/config.py:BulkheadConfig.bulkhead.queue_size` |
| `LEX_RESILIENCE__BULKHEAD__TIMEOUT` | float | 30.0 | Execution timeout | `packages/lexigram-resilience/src/lexigram/resilience/config.py:BulkheadConfig.bulkhead.timeout` |
| `LEX_RESILIENCE__CIRCUIT_BREAKER` | CircuitBreakerConfig | field(...) |  | `packages/lexigram-resilience/src/lexigram/resilience/config.py:ResilienceConfig.circuit_breaker` |
| `LEX_RESILIENCE__IDEMPOTENCY__AUTO_CLEANUP` | bool | True | Start background cleanup task on init. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Id` |
| `LEX_RESILIENCE__IDEMPOTENCY__AUTO_CLEANUP` | bool | True | Start background cleanup task on init. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Idem` |
| `LEX_RESILIENCE__IDEMPOTENCY__AUTO_CLEANUP` | bool | True | Start background cleanup task on init. | `packages/lexigram-resilience/src/lexigram/resilience/config.py:IdempotencyConfig.auto_cleanup` |
| `LEX_RESILIENCE__IDEMPOTENCY__CLEANUP_INTERVAL` | float | 300.0 | Seconds between background cleanup sweeps. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Id` |
| `LEX_RESILIENCE__IDEMPOTENCY__CLEANUP_INTERVAL` | float | 300.0 | Seconds between background cleanup sweeps. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Idem` |
| `LEX_RESILIENCE__IDEMPOTENCY__CLEANUP_INTERVAL` | float | 300.0 | Seconds between background cleanup sweeps. | `packages/lexigram-resilience/src/lexigram/resilience/config.py:IdempotencyConfig.cleanup_interval` |
| `LEX_RESILIENCE__IDEMPOTENCY__KEY_PREFIX` | str | "idempotency:" | Prefix for all keys in backing stores. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Id` |
| `LEX_RESILIENCE__IDEMPOTENCY__KEY_PREFIX` | str | "idempotency:" | Prefix for all keys in backing stores. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Idem` |
| `LEX_RESILIENCE__IDEMPOTENCY__KEY_PREFIX` | str | "idempotency:" | Prefix for all keys in backing stores. | `packages/lexigram-resilience/src/lexigram/resilience/config.py:IdempotencyConfig.key_prefix` |
| `LEX_RESILIENCE__IDEMPOTENCY__MAX_ENTRIES` | int | 10000 | Maximum in-memory entries before FIFO eviction. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Id` |
| `LEX_RESILIENCE__IDEMPOTENCY__MAX_ENTRIES` | int | 10000 | Maximum in-memory entries before FIFO eviction. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Idem` |
| `LEX_RESILIENCE__IDEMPOTENCY__MAX_ENTRIES` | int | 10000 | Maximum in-memory entries before FIFO eviction. | `packages/lexigram-resilience/src/lexigram/resilience/config.py:IdempotencyConfig.max_entries` |
| `LEX_RESILIENCE__IDEMPOTENCY__MAX_KEY_LENGTH` | int | 512 | Maximum allowed idempotency key length. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Id` |
| `LEX_RESILIENCE__IDEMPOTENCY__MAX_KEY_LENGTH` | int | 512 | Maximum allowed idempotency key length. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Idem` |
| `LEX_RESILIENCE__IDEMPOTENCY__MAX_KEY_LENGTH` | int | 512 | Maximum allowed idempotency key length. | `packages/lexigram-resilience/src/lexigram/resilience/config.py:IdempotencyConfig.max_key_length` |
| `LEX_RESILIENCE__IDEMPOTENCY__TTL` | int | 3600 | TTL for cached results in seconds. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Id` |
| `LEX_RESILIENCE__IDEMPOTENCY__TTL` | int | 3600 | TTL for cached results in seconds. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/resilience/config.py:Idem` |
| `LEX_RESILIENCE__IDEMPOTENCY__TTL` | int | 3600 | TTL for cached results in seconds. | `packages/lexigram-resilience/src/lexigram/resilience/config.py:IdempotencyConfig.ttl` |
| `LEX_RESILIENCE__RETRY` | RetryConfig | field(...) |  | `packages/lexigram-resilience/src/lexigram/resilience/config.py:ResilienceConfig.retry` |
| `LEX_RESILIENCE__TIMEOUT` | TimeoutConfig | field(...) |  | `packages/lexigram-resilience/src/lexigram/resilience/config.py:ResilienceConfig.timeout` |
| `LEX_SEARCH__BACKENDS` | list[NamedSearchConfig] | (required) | Named search backends for multi-backend support. When non-empty, the provider registers each backend under Annotated[Sea | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Search` |
| `LEX_SEARCH__BACKENDS` | list[NamedSearchConfig] | (required) | Named search backends for multi-backend support. When non-empty, the provider registers each backend under Annotated[Sea | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:SearchCo` |
| `LEX_SEARCH__BACKENDS` | list[NamedSearchConfig] | (required) | Named search backends for multi-backend support. When non-empty, the provider registers each backend under Annotated[Sea | `packages/lexigram-search/src/lexigram/search/config.py:SearchConfig.backends` |
| `LEX_SEARCH__DATABASE` | str  \| None | None | Named database to use for DB-backed backends (postgres/mysql). References a named database registered via Annotated[Data | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Search` |
| `LEX_SEARCH__DATABASE` | str  \| None | None | Named database to use for DB-backed backends (postgres/mysql). References a named database registered via Annotated[Data | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:SearchCo` |
| `LEX_SEARCH__DATABASE` | str  \| None | None | Named database to use for DB-backed backends (postgres/mysql). References a named database registered via Annotated[Data | `packages/lexigram-search/src/lexigram/search/config.py:SearchConfig.database` |
| `LEX_SEARCH__ELASTICSEARCH__API_KEY` | SecretStr  \| None | None |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Elasti` |
| `LEX_SEARCH__ELASTICSEARCH__API_KEY` | SecretStr  \| None | None |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Elastics` |
| `LEX_SEARCH__ELASTICSEARCH__API_KEY` | SecretStr  \| None | None |  | `packages/lexigram-search/src/lexigram/search/config.py:ElasticsearchConfig.elasticsearch.api_key` |
| `LEX_SEARCH__ELASTICSEARCH__HOSTS` | list[str] | (required) | Elasticsearch hosts | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Elasti` |
| `LEX_SEARCH__ELASTICSEARCH__HOSTS` | list[str] | (required) | Elasticsearch hosts | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Elastics` |
| `LEX_SEARCH__ELASTICSEARCH__HOSTS` | list[str] | (required) | Elasticsearch hosts | `packages/lexigram-search/src/lexigram/search/config.py:ElasticsearchConfig.elasticsearch.hosts` |
| `LEX_SEARCH__ELASTICSEARCH__INDEX_PREFIX` | str | "lexigram_search_" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Elasti` |
| `LEX_SEARCH__ELASTICSEARCH__INDEX_PREFIX` | str | "lexigram_search_" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Elastics` |
| `LEX_SEARCH__ELASTICSEARCH__INDEX_PREFIX` | str | "lexigram_search_" |  | `packages/lexigram-search/src/lexigram/search/config.py:ElasticsearchConfig.elasticsearch.index_prefi` |
| `LEX_SEARCH__ELASTICSEARCH__NUMBER_OF_REPLICAS` | int | 0 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Elasti` |
| `LEX_SEARCH__ELASTICSEARCH__NUMBER_OF_REPLICAS` | int | 0 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Elastics` |
| `LEX_SEARCH__ELASTICSEARCH__NUMBER_OF_REPLICAS` | int | 0 |  | `packages/lexigram-search/src/lexigram/search/config.py:ElasticsearchConfig.elasticsearch.number_of_r` |
| `LEX_SEARCH__ELASTICSEARCH__NUMBER_OF_SHARDS` | int | 1 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Elasti` |
| `LEX_SEARCH__ELASTICSEARCH__NUMBER_OF_SHARDS` | int | 1 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Elastics` |
| `LEX_SEARCH__ELASTICSEARCH__NUMBER_OF_SHARDS` | int | 1 |  | `packages/lexigram-search/src/lexigram/search/config.py:ElasticsearchConfig.elasticsearch.number_of_s` |
| `LEX_SEARCH__ELASTICSEARCH__PASSWORD` | SecretStr  \| None | None |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Elasti` |
| `LEX_SEARCH__ELASTICSEARCH__PASSWORD` | SecretStr  \| None | None |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Elastics` |
| `LEX_SEARCH__ELASTICSEARCH__PASSWORD` | SecretStr  \| None | None |  | `packages/lexigram-search/src/lexigram/search/config.py:ElasticsearchConfig.elasticsearch.password` |
| `LEX_SEARCH__ELASTICSEARCH__USERNAME` | str  \| None | None |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Elasti` |
| `LEX_SEARCH__ELASTICSEARCH__USERNAME` | str  \| None | None |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Elastics` |
| `LEX_SEARCH__ELASTICSEARCH__USERNAME` | str  \| None | None |  | `packages/lexigram-search/src/lexigram/search/config.py:ElasticsearchConfig.elasticsearch.username` |
| `LEX_SEARCH__ELASTICSEARCH__USE_SSL` | bool | False |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Elasti` |
| `LEX_SEARCH__ELASTICSEARCH__USE_SSL` | bool | False |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Elastics` |
| `LEX_SEARCH__ELASTICSEARCH__USE_SSL` | bool | False |  | `packages/lexigram-search/src/lexigram/search/config.py:ElasticsearchConfig.elasticsearch.use_ssl` |
| `LEX_SEARCH__ELASTICSEARCH__VERIFY_CERTS` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Elasti` |
| `LEX_SEARCH__ELASTICSEARCH__VERIFY_CERTS` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Elastics` |
| `LEX_SEARCH__ELASTICSEARCH__VERIFY_CERTS` | bool | True |  | `packages/lexigram-search/src/lexigram/search/config.py:ElasticsearchConfig.elasticsearch.verify_cert` |
| `LEX_SEARCH__ENABLED` | bool | True | Enable the search subsystem | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Search` |
| `LEX_SEARCH__ENABLED` | bool | True | Enable the search subsystem | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:SearchCo` |
| `LEX_SEARCH__ENABLED` | bool | True | Enable the search subsystem | `packages/lexigram-search/src/lexigram/search/config.py:SearchConfig.enabled` |
| `LEX_SEARCH__MEILISEARCH__API_KEY` | SecretStr  \| None | None | MeiliSearch API key | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MeiliS` |
| `LEX_SEARCH__MEILISEARCH__API_KEY` | SecretStr  \| None | None | MeiliSearch API key | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MeiliSea` |
| `LEX_SEARCH__MEILISEARCH__API_KEY` | SecretStr  \| None | None | MeiliSearch API key | `packages/lexigram-search/src/lexigram/search/config.py:MeiliSearchConfig.meilisearch.api_key` |
| `LEX_SEARCH__MEILISEARCH__DISPLAYED_ATTRIBUTES` | list[str] | (required) | Fields to return in results | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MeiliS` |
| `LEX_SEARCH__MEILISEARCH__DISPLAYED_ATTRIBUTES` | list[str] | (required) | Fields to return in results | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MeiliSea` |
| `LEX_SEARCH__MEILISEARCH__DISPLAYED_ATTRIBUTES` | list[str] | (required) | Fields to return in results | `packages/lexigram-search/src/lexigram/search/config.py:MeiliSearchConfig.meilisearch.displayed_attri` |
| `LEX_SEARCH__MEILISEARCH__FILTERABLE_ATTRIBUTES` | list[str] | (required) | Attributes that can be filtered | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MeiliS` |
| `LEX_SEARCH__MEILISEARCH__FILTERABLE_ATTRIBUTES` | list[str] | (required) | Attributes that can be filtered | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MeiliSea` |
| `LEX_SEARCH__MEILISEARCH__FILTERABLE_ATTRIBUTES` | list[str] | (required) | Attributes that can be filtered | `packages/lexigram-search/src/lexigram/search/config.py:MeiliSearchConfig.meilisearch.filterable_attr` |
| `LEX_SEARCH__MEILISEARCH__MAX_CONNECTIONS` | int | 10 | Maximum number of connections | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MeiliS` |
| `LEX_SEARCH__MEILISEARCH__MAX_CONNECTIONS` | int | 10 | Maximum number of connections | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MeiliSea` |
| `LEX_SEARCH__MEILISEARCH__MAX_CONNECTIONS` | int | 10 | Maximum number of connections | `packages/lexigram-search/src/lexigram/search/config.py:MeiliSearchConfig.meilisearch.max_connections` |
| `LEX_SEARCH__MEILISEARCH__MIN_WORD_SIZE_FOR_TYPOS` | dict[str, int] | (required) | Minimum word size for typo tolerance | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MeiliS` |
| `LEX_SEARCH__MEILISEARCH__MIN_WORD_SIZE_FOR_TYPOS` | dict[str, int] | (required) | Minimum word size for typo tolerance | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MeiliSea` |
| `LEX_SEARCH__MEILISEARCH__MIN_WORD_SIZE_FOR_TYPOS` | dict[str, int] | (required) | Minimum word size for typo tolerance | `packages/lexigram-search/src/lexigram/search/config.py:MeiliSearchConfig.meilisearch.min_word_size_f` |
| `LEX_SEARCH__MEILISEARCH__RANKING_RULES` | list[str] | (required) | Ranking rules in order | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MeiliS` |
| `LEX_SEARCH__MEILISEARCH__RANKING_RULES` | list[str] | (required) | Ranking rules in order | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MeiliSea` |
| `LEX_SEARCH__MEILISEARCH__RANKING_RULES` | list[str] | (required) | Ranking rules in order | `packages/lexigram-search/src/lexigram/search/config.py:MeiliSearchConfig.meilisearch.ranking_rules` |
| `LEX_SEARCH__MEILISEARCH__SEARCHABLE_ATTRIBUTES` | list[str] | (required) | Fields to search in | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MeiliS` |
| `LEX_SEARCH__MEILISEARCH__SEARCHABLE_ATTRIBUTES` | list[str] | (required) | Fields to search in | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MeiliSea` |
| `LEX_SEARCH__MEILISEARCH__SEARCHABLE_ATTRIBUTES` | list[str] | (required) | Fields to search in | `packages/lexigram-search/src/lexigram/search/config.py:MeiliSearchConfig.meilisearch.searchable_attr` |
| `LEX_SEARCH__MEILISEARCH__SORTABLE_ATTRIBUTES` | list[str] | (required) | Attributes that can be sorted | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MeiliS` |
| `LEX_SEARCH__MEILISEARCH__SORTABLE_ATTRIBUTES` | list[str] | (required) | Attributes that can be sorted | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MeiliSea` |
| `LEX_SEARCH__MEILISEARCH__SORTABLE_ATTRIBUTES` | list[str] | (required) | Attributes that can be sorted | `packages/lexigram-search/src/lexigram/search/config.py:MeiliSearchConfig.meilisearch.sortable_attrib` |
| `LEX_SEARCH__MEILISEARCH__TIMEOUT` | int | 30 | Request timeout in seconds | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MeiliS` |
| `LEX_SEARCH__MEILISEARCH__TIMEOUT` | int | 30 | Request timeout in seconds | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MeiliSea` |
| `LEX_SEARCH__MEILISEARCH__TIMEOUT` | int | 30 | Request timeout in seconds | `packages/lexigram-search/src/lexigram/search/config.py:MeiliSearchConfig.meilisearch.timeout` |
| `LEX_SEARCH__MEILISEARCH__TYPO_TOLERANCE_ENABLED` | bool | True | Enable typo tolerance | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MeiliS` |
| `LEX_SEARCH__MEILISEARCH__TYPO_TOLERANCE_ENABLED` | bool | True | Enable typo tolerance | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MeiliSea` |
| `LEX_SEARCH__MEILISEARCH__TYPO_TOLERANCE_ENABLED` | bool | True | Enable typo tolerance | `packages/lexigram-search/src/lexigram/search/config.py:MeiliSearchConfig.meilisearch.typo_tolerance_` |
| `LEX_SEARCH__MEILISEARCH__URL` | str | "http://localhost:7700" | MeiliSearch server URL | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MeiliS` |
| `LEX_SEARCH__MEILISEARCH__URL` | str | "http://localhost:7700" | MeiliSearch server URL | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MeiliSea` |
| `LEX_SEARCH__MEILISEARCH__URL` | str | "http://localhost:7700" | MeiliSearch server URL | `packages/lexigram-search/src/lexigram/search/config.py:MeiliSearchConfig.meilisearch.url` |
| `LEX_SEARCH__MONGO__CONNECTION_STRING` | SecretStr | SecretStr(...) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MongoS` |
| `LEX_SEARCH__MONGO__CONNECTION_STRING` | SecretStr | SecretStr(...) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MongoSea` |
| `LEX_SEARCH__MONGO__CONNECTION_STRING` | SecretStr | SecretStr(...) |  | `packages/lexigram-search/src/lexigram/search/config.py:MongoSearchConfig.mongo.connection_string` |
| `LEX_SEARCH__MONGO__DATABASE_NAME` | str | "search" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MongoS` |
| `LEX_SEARCH__MONGO__DATABASE_NAME` | str | "search" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MongoSea` |
| `LEX_SEARCH__MONGO__DATABASE_NAME` | str | "search" |  | `packages/lexigram-search/src/lexigram/search/config.py:MongoSearchConfig.mongo.database_name` |
| `LEX_SEARCH__MONGO__USE_ATLAS_SEARCH` | bool | False |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MongoS` |
| `LEX_SEARCH__MONGO__USE_ATLAS_SEARCH` | bool | False |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MongoSea` |
| `LEX_SEARCH__MONGO__USE_ATLAS_SEARCH` | bool | False |  | `packages/lexigram-search/src/lexigram/search/config.py:MongoSearchConfig.mongo.use_atlas_search` |
| `LEX_SEARCH__MYSQL__CONNECTION_STRING` | SecretStr | SecretStr(...) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MySQLS` |
| `LEX_SEARCH__MYSQL__CONNECTION_STRING` | SecretStr | SecretStr(...) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MySQLSea` |
| `LEX_SEARCH__MYSQL__CONNECTION_STRING` | SecretStr | SecretStr(...) |  | `packages/lexigram-search/src/lexigram/search/config.py:MySQLSearchConfig.mysql.connection_string` |
| `LEX_SEARCH__MYSQL__FULLTEXT_MODE` | str | "natural_language" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MySQLS` |
| `LEX_SEARCH__MYSQL__FULLTEXT_MODE` | str | "natural_language" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MySQLSea` |
| `LEX_SEARCH__MYSQL__FULLTEXT_MODE` | str | "natural_language" |  | `packages/lexigram-search/src/lexigram/search/config.py:MySQLSearchConfig.mysql.fulltext_mode` |
| `LEX_SEARCH__MYSQL__MIN_WORD_LENGTH` | int | 3 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MySQLS` |
| `LEX_SEARCH__MYSQL__MIN_WORD_LENGTH` | int | 3 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:MySQLSea` |
| `LEX_SEARCH__MYSQL__MIN_WORD_LENGTH` | int | 3 |  | `packages/lexigram-search/src/lexigram/search/config.py:MySQLSearchConfig.mysql.min_word_length` |
| `LEX_SEARCH__OPENSEARCH__HOSTS` | list[str] | (required) | OpenSearch hosts | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:OpenSe` |
| `LEX_SEARCH__OPENSEARCH__HOSTS` | list[str] | (required) | OpenSearch hosts | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:OpenSear` |
| `LEX_SEARCH__OPENSEARCH__HOSTS` | list[str] | (required) | OpenSearch hosts | `packages/lexigram-search/src/lexigram/search/config.py:OpenSearchConfig.opensearch.hosts` |
| `LEX_SEARCH__OPENSEARCH__INDEX_PREFIX` | str | "lexigram_search_" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:OpenSe` |
| `LEX_SEARCH__OPENSEARCH__INDEX_PREFIX` | str | "lexigram_search_" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:OpenSear` |
| `LEX_SEARCH__OPENSEARCH__INDEX_PREFIX` | str | "lexigram_search_" |  | `packages/lexigram-search/src/lexigram/search/config.py:OpenSearchConfig.opensearch.index_prefix` |
| `LEX_SEARCH__OPENSEARCH__PASSWORD` | str  \| None | None |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:OpenSe` |
| `LEX_SEARCH__OPENSEARCH__PASSWORD` | str  \| None | None |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:OpenSear` |
| `LEX_SEARCH__OPENSEARCH__PASSWORD` | str  \| None | None |  | `packages/lexigram-search/src/lexigram/search/config.py:OpenSearchConfig.opensearch.password` |
| `LEX_SEARCH__OPENSEARCH__TIMEOUT` | int | 30 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:OpenSe` |
| `LEX_SEARCH__OPENSEARCH__TIMEOUT` | int | 30 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:OpenSear` |
| `LEX_SEARCH__OPENSEARCH__TIMEOUT` | int | 30 |  | `packages/lexigram-search/src/lexigram/search/config.py:OpenSearchConfig.opensearch.timeout` |
| `LEX_SEARCH__OPENSEARCH__USERNAME` | str  \| None | None |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:OpenSe` |
| `LEX_SEARCH__OPENSEARCH__USERNAME` | str  \| None | None |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:OpenSear` |
| `LEX_SEARCH__OPENSEARCH__USERNAME` | str  \| None | None |  | `packages/lexigram-search/src/lexigram/search/config.py:OpenSearchConfig.opensearch.username` |
| `LEX_SEARCH__OPENSEARCH__USE_SSL` | bool | False |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:OpenSe` |
| `LEX_SEARCH__OPENSEARCH__USE_SSL` | bool | False |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:OpenSear` |
| `LEX_SEARCH__OPENSEARCH__USE_SSL` | bool | False |  | `packages/lexigram-search/src/lexigram/search/config.py:OpenSearchConfig.opensearch.use_ssl` |
| `LEX_SEARCH__OPENSEARCH__VERIFY_SSL` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:OpenSe` |
| `LEX_SEARCH__OPENSEARCH__VERIFY_SSL` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:OpenSear` |
| `LEX_SEARCH__OPENSEARCH__VERIFY_SSL` | bool | True |  | `packages/lexigram-search/src/lexigram/search/config.py:OpenSearchConfig.opensearch.verify_ssl` |
| `LEX_SEARCH__OPERATIONS__BULK_CHUNK_SIZE` | int | 500 | Bulk request chunk size | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Search` |
| `LEX_SEARCH__OPERATIONS__BULK_CHUNK_SIZE` | int | 500 | Bulk request chunk size | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:SearchOp` |
| `LEX_SEARCH__OPERATIONS__BULK_CHUNK_SIZE` | int | 500 | Bulk request chunk size | `packages/lexigram-search/src/lexigram/search/config.py:SearchOperationsConfig.operations.bulk_chunk_` |
| `LEX_SEARCH__OPERATIONS__MAX_RETRIES` | int | 3 | Max retry attempts | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Search` |
| `LEX_SEARCH__OPERATIONS__MAX_RETRIES` | int | 3 | Max retry attempts | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:SearchOp` |
| `LEX_SEARCH__OPERATIONS__MAX_RETRIES` | int | 3 | Max retry attempts | `packages/lexigram-search/src/lexigram/search/config.py:SearchOperationsConfig.operations.max_retries` |
| `LEX_SEARCH__OPERATIONS__REQUEST_TIMEOUT` | float | 30.0 | Request timeout seconds | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Search` |
| `LEX_SEARCH__OPERATIONS__REQUEST_TIMEOUT` | float | 30.0 | Request timeout seconds | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:SearchOp` |
| `LEX_SEARCH__OPERATIONS__REQUEST_TIMEOUT` | float | 30.0 | Request timeout seconds | `packages/lexigram-search/src/lexigram/search/config.py:SearchOperationsConfig.operations.request_tim` |
| `LEX_SEARCH__OPERATIONS__RETRY_BACKOFF` | float | 0.5 | Retry backoff multiplier | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Search` |
| `LEX_SEARCH__OPERATIONS__RETRY_BACKOFF` | float | 0.5 | Retry backoff multiplier | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:SearchOp` |
| `LEX_SEARCH__OPERATIONS__RETRY_BACKOFF` | float | 0.5 | Retry backoff multiplier | `packages/lexigram-search/src/lexigram/search/config.py:SearchOperationsConfig.operations.retry_backo` |
| `LEX_SEARCH__POSTGRES__AUTO_CREATE_TABLES` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Postgr` |
| `LEX_SEARCH__POSTGRES__AUTO_CREATE_TABLES` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Postgres` |
| `LEX_SEARCH__POSTGRES__AUTO_CREATE_TABLES` | bool | True |  | `packages/lexigram-search/src/lexigram/search/config.py:PostgresSearchConfig.postgres.auto_create_tab` |
| `LEX_SEARCH__POSTGRES__CONNECTION_STRING` | SecretStr | SecretStr(...) | PostgreSQL connection string | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Postgr` |
| `LEX_SEARCH__POSTGRES__CONNECTION_STRING` | SecretStr | SecretStr(...) | PostgreSQL connection string | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Postgres` |
| `LEX_SEARCH__POSTGRES__CONNECTION_STRING` | SecretStr | SecretStr(...) | PostgreSQL connection string | `packages/lexigram-search/src/lexigram/search/config.py:PostgresSearchConfig.postgres.connection_stri` |
| `LEX_SEARCH__POSTGRES__ENABLE_TRIGRAM` | bool | True | Enable pg_trgm fuzzy matching | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Postgr` |
| `LEX_SEARCH__POSTGRES__ENABLE_TRIGRAM` | bool | True | Enable pg_trgm fuzzy matching | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Postgres` |
| `LEX_SEARCH__POSTGRES__ENABLE_TRIGRAM` | bool | True | Enable pg_trgm fuzzy matching | `packages/lexigram-search/src/lexigram/search/config.py:PostgresSearchConfig.postgres.enable_trigram` |
| `LEX_SEARCH__POSTGRES__TEXT_SEARCH_CONFIG` | str | "english" | PostgreSQL text search config | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Postgr` |
| `LEX_SEARCH__POSTGRES__TEXT_SEARCH_CONFIG` | str | "english" | PostgreSQL text search config | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Postgres` |
| `LEX_SEARCH__POSTGRES__TEXT_SEARCH_CONFIG` | str | "english" | PostgreSQL text search config | `packages/lexigram-search/src/lexigram/search/config.py:PostgresSearchConfig.postgres.text_search_con` |
| `LEX_SEARCH__QUERY__DEFAULT_LIMIT` | int | (complex) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:QueryC` |
| `LEX_SEARCH__QUERY__DEFAULT_LIMIT` | int | (complex) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:QueryCon` |
| `LEX_SEARCH__QUERY__DEFAULT_LIMIT` | int | (complex) |  | `packages/lexigram-search/src/lexigram/search/config.py:QueryConfig.query.default_limit` |
| `LEX_SEARCH__QUERY__ENABLE_AGGREGATIONS` | bool | False |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:QueryC` |
| `LEX_SEARCH__QUERY__ENABLE_AGGREGATIONS` | bool | False |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:QueryCon` |
| `LEX_SEARCH__QUERY__ENABLE_AGGREGATIONS` | bool | False |  | `packages/lexigram-search/src/lexigram/search/config.py:QueryConfig.query.enable_aggregations` |
| `LEX_SEARCH__QUERY__ENABLE_FACETING` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:QueryC` |
| `LEX_SEARCH__QUERY__ENABLE_FACETING` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:QueryCon` |
| `LEX_SEARCH__QUERY__ENABLE_FACETING` | bool | True |  | `packages/lexigram-search/src/lexigram/search/config.py:QueryConfig.query.enable_faceting` |
| `LEX_SEARCH__QUERY__ENABLE_HIGHLIGHTING` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:QueryC` |
| `LEX_SEARCH__QUERY__ENABLE_HIGHLIGHTING` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:QueryCon` |
| `LEX_SEARCH__QUERY__ENABLE_HIGHLIGHTING` | bool | True |  | `packages/lexigram-search/src/lexigram/search/config.py:QueryConfig.query.enable_highlighting` |
| `LEX_SEARCH__QUERY__FUZZY_THRESHOLD` | float | 0.8 |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:QueryC` |
| `LEX_SEARCH__QUERY__FUZZY_THRESHOLD` | float | 0.8 |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:QueryCon` |
| `LEX_SEARCH__QUERY__FUZZY_THRESHOLD` | float | 0.8 |  | `packages/lexigram-search/src/lexigram/search/config.py:QueryConfig.query.fuzzy_threshold` |
| `LEX_SEARCH__QUERY__MAX_LIMIT` | int | (complex) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:QueryC` |
| `LEX_SEARCH__QUERY__MAX_LIMIT` | int | (complex) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:QueryCon` |
| `LEX_SEARCH__QUERY__MAX_LIMIT` | int | (complex) |  | `packages/lexigram-search/src/lexigram/search/config.py:QueryConfig.query.max_limit` |
| `LEX_SEARCH__QUERY__STRATEGY` | str | "fuzzy" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:QueryC` |
| `LEX_SEARCH__QUERY__STRATEGY` | str | "fuzzy" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:QueryCon` |
| `LEX_SEARCH__QUERY__STRATEGY` | str | "fuzzy" |  | `packages/lexigram-search/src/lexigram/search/config.py:QueryConfig.query.strategy` |
| `LEX_SEARCH__SQLITE__AUTO_CREATE_TABLES` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:SQLite` |
| `LEX_SEARCH__SQLITE__AUTO_CREATE_TABLES` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:SQLiteSe` |
| `LEX_SEARCH__SQLITE__AUTO_CREATE_TABLES` | bool | True |  | `packages/lexigram-search/src/lexigram/search/config.py:SQLiteSearchConfig.sqlite.auto_create_tables` |
| `LEX_SEARCH__SQLITE__DB_PATH` | str | ":memory:" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:SQLite` |
| `LEX_SEARCH__SQLITE__DB_PATH` | str | ":memory:" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:SQLiteSe` |
| `LEX_SEARCH__SQLITE__DB_PATH` | str | ":memory:" |  | `packages/lexigram-search/src/lexigram/search/config.py:SQLiteSearchConfig.sqlite.db_path` |
| `LEX_SEARCH__SQLITE__TOKENIZER` | str | "porter unicode61" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:SQLite` |
| `LEX_SEARCH__SQLITE__TOKENIZER` | str | "porter unicode61" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:SQLiteSe` |
| `LEX_SEARCH__SQLITE__TOKENIZER` | str | "porter unicode61" |  | `packages/lexigram-search/src/lexigram/search/config.py:SQLiteSearchConfig.sqlite.tokenizer` |
| `LEX_SEARCH__TIMEOUT` | float | 30.0 | Default request timeout seconds | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Search` |
| `LEX_SEARCH__TIMEOUT` | float | 30.0 | Default request timeout seconds | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:SearchCo` |
| `LEX_SEARCH__TIMEOUT` | float | 30.0 | Default request timeout seconds | `packages/lexigram-search/src/lexigram/search/config.py:SearchConfig.timeout` |
| `LEX_SEARCH__TYPESENSE__API_KEY` | SecretStr  \| None | None | Typesense API key | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Typese` |
| `LEX_SEARCH__TYPESENSE__API_KEY` | SecretStr  \| None | None | Typesense API key | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Typesens` |
| `LEX_SEARCH__TYPESENSE__API_KEY` | SecretStr  \| None | None | Typesense API key | `packages/lexigram-search/src/lexigram/search/config.py:TypesenseConfig.typesense.api_key` |
| `LEX_SEARCH__TYPESENSE__CONNECTION_TIMEOUT` | int | 30 | Connection timeout | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Typese` |
| `LEX_SEARCH__TYPESENSE__CONNECTION_TIMEOUT` | int | 30 | Connection timeout | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Typesens` |
| `LEX_SEARCH__TYPESENSE__CONNECTION_TIMEOUT` | int | 30 | Connection timeout | `packages/lexigram-search/src/lexigram/search/config.py:TypesenseConfig.typesense.connection_timeout` |
| `LEX_SEARCH__TYPESENSE__HEALTH_CHECK_INTERVAL` | int | 60 | Health check interval | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Typese` |
| `LEX_SEARCH__TYPESENSE__HEALTH_CHECK_INTERVAL` | int | 60 | Health check interval | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Typesens` |
| `LEX_SEARCH__TYPESENSE__HEALTH_CHECK_INTERVAL` | int | 60 | Health check interval | `packages/lexigram-search/src/lexigram/search/config.py:TypesenseConfig.typesense.health_check_interv` |
| `LEX_SEARCH__TYPESENSE__NODES` | list[dict[str, str]] | (required) | Typesense node connections | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Typese` |
| `LEX_SEARCH__TYPESENSE__NODES` | list[dict[str, str]] | (required) | Typesense node connections | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/search/config.py:Typesens` |
| `LEX_SEARCH__TYPESENSE__NODES` | list[dict[str, str]] | (required) | Typesense node connections | `packages/lexigram-search/src/lexigram/search/config.py:TypesenseConfig.typesense.nodes` |
| `LEX_SQL__AUDIT_HMAC_KEY` | str  \| None | None | HMAC key for audit checksum signing. Plain text or base64. | `packages/lexigram-sql/src/lexigram/sql/config.py:DatabaseConfig.audit_hmac_key` |
| `LEX_SQL__BACKENDS` | list[NamedDatabaseConfig] | (required) | Multi-database backends list. When non-empty, drives multi-DB mode. The entry with primary=True (or the first entry) als | `packages/lexigram-sql/src/lexigram/sql/config.py:DatabaseConfig.backends` |
| `LEX_SQL__BACKEND__URL` | SecretStr | Ellipsis | Database connection URL (may contain credentials) | `packages/lexigram-sql/src/lexigram/sql/config.py:DatabaseBackendConfig.backend.url` |
| `LEX_SQL__ENABLED` | bool | True |  | `packages/lexigram-sql/src/lexigram/sql/config.py:DatabaseConfig.enabled` |
| `LEX_SQL__MIGRATIONS__LOCK_TIMEOUT` | Duration | Duration.seconds(...) |  | `packages/lexigram-sql/src/lexigram/sql/config.py:DatabaseMigrationConfig.migrations.lock_timeout` |
| `LEX_SQL__NAME` | str | "database" |  | `packages/lexigram-sql/src/lexigram/sql/config.py:DatabaseConfig.name` |
| `LEX_SQL__OPERATIONS__ECHO` | bool | False |  | `packages/lexigram-sql/src/lexigram/sql/config.py:DatabaseOperationConfig.operations.echo` |
| `LEX_SQL__OPERATIONS__STATEMENT_TIMEOUT` | Duration | Duration.seconds(...) |  | `packages/lexigram-sql/src/lexigram/sql/config.py:DatabaseOperationConfig.operations.statement_timeou` |
| `LEX_SQL__OUTBOX__BATCH_MAX_AGE` | Duration | Duration.seconds(...) |  | `packages/lexigram-sql/src/lexigram/sql/config.py:DatabaseOutboxConfig.outbox.batch_max_age` |
| `LEX_SQL__OUTBOX__ENABLED` | bool | True |  | `packages/lexigram-sql/src/lexigram/sql/config.py:DatabaseOutboxConfig.outbox.enabled` |
| `LEX_SQL__OUTBOX__POLL_INTERVAL` | Duration | Duration.seconds(...) |  | `packages/lexigram-sql/src/lexigram/sql/config.py:DatabaseOutboxConfig.outbox.poll_interval` |
| `LEX_SQL__POOL__ACQUIRE_TIMEOUT` | Duration | Duration.seconds(...) |  | `packages/lexigram-sql/src/lexigram/sql/config.py:DatabasePoolConfig.pool.acquire_timeout` |
| `LEX_SQL__POOL__IDLE_TIMEOUT` | Duration | Duration.minutes(...) |  | `packages/lexigram-sql/src/lexigram/sql/config.py:DatabasePoolConfig.pool.idle_timeout` |
| `LEX_SQL__POOL__MAX_LIFETIME` | Duration | Duration.hours(...) |  | `packages/lexigram-sql/src/lexigram/sql/config.py:DatabasePoolConfig.pool.max_lifetime` |
| `LEX_SQL__POOL__MAX_OVERFLOW` | int | 5 |  | `packages/lexigram-sql/src/lexigram/sql/config.py:DatabasePoolConfig.pool.max_overflow` |
| `LEX_SQL__POOL__MAX_SIZE` | int | (complex) |  | `packages/lexigram-sql/src/lexigram/sql/config.py:DatabasePoolConfig.pool.max_size` |
| `LEX_SQL__POOL__MIN_SIZE` | int | (complex) |  | `packages/lexigram-sql/src/lexigram/sql/config.py:DatabasePoolConfig.pool.min_size` |
| `LEX_SQL__POOL__RECYCLE` | int | 3600 |  | `packages/lexigram-sql/src/lexigram/sql/config.py:DatabasePoolConfig.pool.recycle` |
| `LEX_SQL__POOL__TIMEOUT` | float | (complex) |  | `packages/lexigram-sql/src/lexigram/sql/config.py:DatabasePoolConfig.pool.timeout` |
| `LEX_STORAGE__BACKENDS` | list[NamedStorageConfig] | (required) | Named storage backends for multi-store support. When non-empty, the provider registers each backend under Annotated[Blob | `packages/lexigram-storage/src/lexigram/storage/config.py:StorageConfig.backends` |
| `LEX_STORAGE__DEFAULT_DRIVER` | Literal['local', 's3', 'gcs', 'azure', 'memory', 'r2'] | (complex) | Default storage driver to use | `packages/lexigram-storage/src/lexigram/storage/config.py:StorageConfig.default_driver` |
| `LEX_STORAGE__DRIVERS` | dict[str, StorageLocalConfig  \| StorageS3Config  \| StorageGCSConfig  \| Storag | (required) | Driver-specific configurations | `packages/lexigram-storage/src/lexigram/storage/config.py:StorageConfig.drivers` |
| `LEX_STORAGE__ENABLED` | bool | True |  | `packages/lexigram-storage/src/lexigram/storage/config.py:StorageConfig.enabled` |
| `LEX_STORAGE__ENV` | str  \| None | None | Environment (development/staging/production) | `packages/lexigram-storage/src/lexigram/storage/config.py:StorageConfig.env` |
| `LEX_STORAGE__HEALTH_CHECK_TIMEOUT` | float | 5.0 | Timeout in seconds for the startup health check in StorageProvider.boot() | `packages/lexigram-storage/src/lexigram/storage/config.py:StorageConfig.health_check_timeout` |
| `LEX_STORAGE__NAME` | str | "storage" |  | `packages/lexigram-storage/src/lexigram/storage/config.py:StorageConfig.name` |
| `LEX_STORAGE__SERVICE__ALLOWED_MIME_TYPES` | list[str] | (required) | Allowed MIME types for upload validation. Defaults to a safe set of common image types: ['image/jpeg', 'image/png', 'ima | `packages/lexigram-storage/src/lexigram/storage/config.py:StorageOperationConfig.service.allowed_mime` |
| `LEX_STORAGE__SERVICE__MAX_FILE_SIZE_MB` | int | (complex) | Maximum file size in MB | `packages/lexigram-storage/src/lexigram/storage/config.py:StorageOperationConfig.service.max_file_siz` |
| `LEX_TASKS__BACKENDS` | list[NamedTaskConfig] | (required) | Named task queue backends for multi-queue support. When non-empty, the provider registers each backend under Annotated[T | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskConfig.backends` |
| `LEX_TASKS__BACKEND__AMQP_URL` | SecretStr | SecretStr(...) | AMQP connection URL (may contain credentials). | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskBackendConfig.backend.amqp_url` |
| `LEX_TASKS__BACKEND__POSTGRES_DSN` | SecretStr  \| None | None | Postgres DSN (required when type="postgres"; may contain credentials). | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskBackendConfig.backend.postgres_dsn` |
| `LEX_TASKS__BACKEND__QUEUE_NAME` | str | (complex) | Name of the task queue | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskBackendConfig.backend.queue_name` |
| `LEX_TASKS__BACKEND__REDIS_URL` | SecretStr | SecretStr(...) | Redis connection URL (may contain credentials). | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskBackendConfig.backend.redis_url` |
| `LEX_TASKS__BACKEND__TYPE` | str | (complex) | Queue backend type | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskBackendConfig.backend.type` |
| `LEX_TASKS__ENABLED` | bool | True | Whether tasks module is enabled | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskConfig.enabled` |
| `LEX_TASKS__ENV` | str  \| None | None | Environment (development/staging/production) | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskConfig.env` |
| `LEX_TASKS__EXTRA` | dict[str, Any] | (required) |  | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskConfig.extra` |
| `LEX_TASKS__NAME` | str | "tasks" | Configuration name | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskConfig.name` |
| `LEX_TASKS__RATE_LIMIT__BURST` | int  \| None | None | Maximum burst size | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskRateLimitConfig.rate_limit.burst` |
| `LEX_TASKS__RATE_LIMIT__ENABLED` | bool | False | Whether rate limiting is enabled | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskRateLimitConfig.rate_limit.enabled` |
| `LEX_TASKS__RATE_LIMIT__PER` | float | 1.0 | Time period in seconds | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskRateLimitConfig.rate_limit.per` |
| `LEX_TASKS__RATE_LIMIT__RATE` | int | 100 | Number of tasks allowed per time period | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskRateLimitConfig.rate_limit.rate` |
| `LEX_TASKS__RETRY` | RetryConfig | (required) |  | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskConfig.retry` |
| `LEX_TASKS__SCHEDULER__CHECK_INTERVAL` | float | (complex) | Interval between schedule checks (seconds) | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskSchedulerConfig.scheduler.check_interval` |
| `LEX_TASKS__SCHEDULER__ENABLED` | bool | True | Whether scheduling is enabled | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskSchedulerConfig.scheduler.enabled` |
| `LEX_TASKS__SCHEDULER__TIMEZONE` | str | (complex) | Timezone for cron expressions | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskSchedulerConfig.scheduler.timezone` |
| `LEX_TASKS__TIMEOUT__DEFAULT_TIMEOUT` | float | (complex) | Default timeout | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskTimeoutConfig.timeout.default_timeout` |
| `LEX_TASKS__TIMEOUT__ENFORCE_TIMEOUT` | bool | True | Enforce timeouts | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskTimeoutConfig.timeout.enforce_timeout` |
| `LEX_TASKS__TIMEOUT__MAX_TIMEOUT` | float | (complex) | Maximum allowed timeout | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskTimeoutConfig.timeout.max_timeout` |
| `LEX_TASKS__WORKER__DEFAULT_TIMEOUT` | float | (complex) | Default timeout for tasks without an explicit timeout (seconds) | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskWorkerConfig.worker.default_timeout` |
| `LEX_TASKS__WORKER__ENFORCE_TIMEOUT` | bool | True | Whether to enforce timeouts on all tasks | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskWorkerConfig.worker.enforce_timeout` |
| `LEX_TASKS__WORKER__MAX_CONCURRENT_TASKS` | int | (complex) | Maximum concurrent tasks per worker | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskWorkerConfig.worker.max_concurrent_tasks` |
| `LEX_TASKS__WORKER__MAX_TIMEOUT` | float | (complex) | Maximum allowed timeout for any task (seconds) | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskWorkerConfig.worker.max_timeout` |
| `LEX_TASKS__WORKER__POLL_INTERVAL` | float | (complex) | Interval between queue polls (seconds) | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskWorkerConfig.worker.poll_interval` |
| `LEX_TASKS__WORKER__SHUTDOWN_TIMEOUT` | float | (complex) | Timeout for graceful shutdown (seconds) | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskWorkerConfig.worker.shutdown_timeout` |
| `LEX_TASKS__WORKER__WORKER_COUNT` | int | (complex) | Number of worker instances | `packages/lexigram-tasks/src/lexigram/tasks/config.py:TaskWorkerConfig.worker.worker_count` |
| `LEX_TENANCY__INTEGRATION__CACHE_KEY_PREFIX` | bool | True |  | `packages/lexigram-tenancy/src/lexigram/tenancy/config.py:IntegrationConfig.integration.cache_key_pre` |
| `LEX_TENANCY__INTEGRATION__SQL_CONTEXT_BRIDGE` | bool | True |  | `packages/lexigram-tenancy/src/lexigram/tenancy/config.py:IntegrationConfig.integration.sql_context_b` |
| `LEX_TENANCY__LIFECYCLE__AUTO_PROVISION_ISOLATION` | bool | True |  | `packages/lexigram-tenancy/src/lexigram/tenancy/config.py:LifecycleConfig.lifecycle.auto_provision_is` |
| `LEX_TENANCY__LIFECYCLE__ISOLATION_STRATEGY` | str | "row_level" |  | `packages/lexigram-tenancy/src/lexigram/tenancy/config.py:LifecycleConfig.lifecycle.isolation_strateg` |
| `LEX_TENANCY__OVERRIDES__CACHE_TTL` | int | DEFAULT_CONFIG_CACHE_TTL |  | `packages/lexigram-tenancy/src/lexigram/tenancy/config.py:ConfigOverridesConfig.overrides.cache_ttl` |
| `LEX_TENANCY__RESOLUTION__HEADER_NAME` | str | DEFAULT_HEADER_NAME |  | `packages/lexigram-tenancy/src/lexigram/tenancy/config.py:ResolutionConfig.resolution.header_name` |
| `LEX_TENANCY__RESOLUTION__JWT_CLAIM_KEY` | str | DEFAULT_JWT_CLAIM_KEY |  | `packages/lexigram-tenancy/src/lexigram/tenancy/config.py:ResolutionConfig.resolution.jwt_claim_key` |
| `LEX_TENANCY__RESOLUTION__PATH_PATTERN` | str  \| None | DEFAULT_PATH_PATTERN |  | `packages/lexigram-tenancy/src/lexigram/tenancy/config.py:ResolutionConfig.resolution.path_pattern` |
| `LEX_TENANCY__RESOLUTION__RESOLVERS` | list[str] | field(...) |  | `packages/lexigram-tenancy/src/lexigram/tenancy/config.py:ResolutionConfig.resolution.resolvers` |
| `LEX_TENANCY__RESOLUTION__STRICT_MEMBERSHIP` | bool | True |  | `packages/lexigram-tenancy/src/lexigram/tenancy/config.py:ResolutionConfig.resolution.strict_membersh` |
| `LEX_TENANCY__RESOLUTION__SUBDOMAIN_PATTERN` | str  \| None | None |  | `packages/lexigram-tenancy/src/lexigram/tenancy/config.py:ResolutionConfig.resolution.subdomain_patte` |
| `LEX_TENANCY__RESOLUTION__TRUSTED_RESOLVERS` | list[str] | field(...) |  | `packages/lexigram-tenancy/src/lexigram/tenancy/config.py:ResolutionConfig.resolution.trusted_resolve` |
| `LEX_TENANCY__RESOLUTION__VALIDATOR_CACHE_TTL` | int | DEFAULT_VALIDATOR_CACHE_TTL |  | `packages/lexigram-tenancy/src/lexigram/tenancy/config.py:ResolutionConfig.resolution.validator_cache` |
| `LEX_TESTING__CLEANUP_TEMP_FILES` | bool | True | Clean up temporary files after tests | `packages/lexigram-testing/src/lexigram/testing/config.py:TestingConfig.cleanup_temp_files` |
| `LEX_TESTING__DB_REUSE` | bool | True | Reuse test databases between tests | `packages/lexigram-testing/src/lexigram/testing/config.py:TestingConfig.db_reuse` |
| `LEX_TESTING__ENABLED` | bool | True |  | `packages/lexigram-testing/src/lexigram/testing/config.py:TestingConfig.enabled` |
| `LEX_TESTING__MOCK_EXTERNAL_SERVICES` | bool | True | Mock external service calls | `packages/lexigram-testing/src/lexigram/testing/config.py:TestingConfig.mock_external_services` |
| `LEX_UI__AUTO_ESCAPE` | bool | True | HTML-escape user strings by default. | `experimental/apps/lexigram-ui/src/lexigram/ui/config.py:UIConfig.auto_escape` |
| `LEX_UI__DEBUG_COMPONENTS` | bool | False | Render data-component debug attributes. | `experimental/apps/lexigram-ui/src/lexigram/ui/config.py:UIConfig.debug_components` |
| `LEX_UI__DEFAULT_THEME` | str | "default" | Default CSS theme name. | `experimental/apps/lexigram-ui/src/lexigram/ui/config.py:UIConfig.default_theme` |
| `LEX_UI__ENABLE_REALTIME` | bool | False | Enable realtime update features. | `experimental/apps/lexigram-ui/src/lexigram/ui/config.py:UIConfig.enable_realtime` |
| `LEX_UI__ENABLE_SSE` | bool | False | Enable Server-Sent Events support. | `experimental/apps/lexigram-ui/src/lexigram/ui/config.py:UIConfig.enable_sse` |
| `LEX_UI__HTMX_VERSION` | str | "2.0.4" | HTMX CDN version. | `experimental/apps/lexigram-ui/src/lexigram/ui/config.py:UIConfig.htmx_version` |
| `LEX_UI__THEME` | str | "light" | Active UI theme. | `experimental/apps/lexigram-ui/src/lexigram/ui/config.py:UIConfig.theme` |
| `LEX_VECTOR__BACKEND` | str | (complex) | Vector store backend to use | `packages/lexigram-vector/src/lexigram/vector/config.py:VectorConfig.backend` |
| `LEX_VECTOR__BACKENDS` | list[NamedVectorConfig] | (required) | Named vector store backends for multi-store support. When non-empty, the provider registers each backend under Annotated | `packages/lexigram-vector/src/lexigram/vector/config.py:VectorConfig.backends` |
| `LEX_VECTOR__CACHE_TTL` | int | 86400 | Cache TTL in seconds (default: 24 hours) | `packages/lexigram-vector/src/lexigram/vector/config.py:VectorConfig.cache_ttl` |
| `LEX_VECTOR__COLLECTION_NAME` | str | "default" | Default collection name for AI-layer operations | `packages/lexigram-vector/src/lexigram/vector/config.py:VectorConfig.collection_name` |
| `LEX_VECTOR__DEFAULT_DIMENSION` | int | 1536 | Default vector dimension | `packages/lexigram-vector/src/lexigram/vector/config.py:VectorConfig.default_dimension` |
| `LEX_VECTOR__DEFAULT_DISTANCE_METRIC` | DistanceMetric | (complex) | Default distance metric for new collections | `packages/lexigram-vector/src/lexigram/vector/config.py:VectorConfig.default_distance_metric` |
| `LEX_VECTOR__DEFAULT_INDEX_TYPE` | IndexType | (complex) | Default index type for new collections | `packages/lexigram-vector/src/lexigram/vector/config.py:VectorConfig.default_index_type` |
| `LEX_VECTOR__EMBEDDING_MODEL` | str | "text-embedding-3-small" | Embedding model name for AI-layer embedding generation | `packages/lexigram-vector/src/lexigram/vector/config.py:VectorConfig.embedding_model` |
| `LEX_VECTOR__EMBEDDING__API_BASE` | str | "http://fastembed" | Base URL of the embedding API. The client appends '/embeddings' to this URL. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/embedding/config` |
| `LEX_VECTOR__EMBEDDING__API_BASE` | str | "http://fastembed" | Base URL of the embedding API. The client appends '/embeddings' to this URL. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/embedding/config.p` |
| `LEX_VECTOR__EMBEDDING__API_BASE` | str | "http://fastembed" | Base URL of the embedding API. The client appends '/embeddings' to this URL. | `packages/lexigram-vector/src/lexigram/vector/embedding/config.py:EmbeddingClientConfig.api_base` |
| `LEX_VECTOR__EMBEDDING__API_KEY` | str  \| None | None | API key sent as Bearer token (required for OpenAI and most cloud providers). | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/embedding/config` |
| `LEX_VECTOR__EMBEDDING__API_KEY` | str  \| None | None | API key sent as Bearer token (required for OpenAI and most cloud providers). | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/embedding/config.p` |
| `LEX_VECTOR__EMBEDDING__API_KEY` | str  \| None | None | API key sent as Bearer token (required for OpenAI and most cloud providers). | `packages/lexigram-vector/src/lexigram/vector/embedding/config.py:EmbeddingClientConfig.api_key` |
| `LEX_VECTOR__EMBEDDING__BATCH_SIZE` | int | 64 | Maximum number of texts per embedding API request. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/embedding/config` |
| `LEX_VECTOR__EMBEDDING__BATCH_SIZE` | int | 64 | Maximum number of texts per embedding API request. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/embedding/config.p` |
| `LEX_VECTOR__EMBEDDING__BATCH_SIZE` | int | 64 | Maximum number of texts per embedding API request. | `packages/lexigram-vector/src/lexigram/vector/embedding/config.py:EmbeddingClientConfig.batch_size` |
| `LEX_VECTOR__EMBEDDING__DIMENSION` | int | 768 | Expected output vector dimension. Must match the model (768 for nomic-embed-text-v1.5, 1536 for text-embedding-ada-002). | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/embedding/config` |
| `LEX_VECTOR__EMBEDDING__DIMENSION` | int | 768 | Expected output vector dimension. Must match the model (768 for nomic-embed-text-v1.5, 1536 for text-embedding-ada-002). | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/embedding/config.p` |
| `LEX_VECTOR__EMBEDDING__DIMENSION` | int | 768 | Expected output vector dimension. Must match the model (768 for nomic-embed-text-v1.5, 1536 for text-embedding-ada-002). | `packages/lexigram-vector/src/lexigram/vector/embedding/config.py:EmbeddingClientConfig.dimension` |
| `LEX_VECTOR__EMBEDDING__FORMAT` | Literal['openai', 'fastembed', 'cohere'] | "openai" | API payload format. 'openai' uses {'input': [...]}, 'fastembed' uses {'texts': [...]}, 'cohere' uses {'texts': [...]}. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/embedding/config` |
| `LEX_VECTOR__EMBEDDING__FORMAT` | Literal['openai', 'fastembed', 'cohere'] | "openai" | API payload format. 'openai' uses {'input': [...]}, 'fastembed' uses {'texts': [...]}, 'cohere' uses {'texts': [...]}. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/embedding/config.p` |
| `LEX_VECTOR__EMBEDDING__FORMAT` | Literal['openai', 'fastembed', 'cohere'] | "openai" | API payload format. 'openai' uses {'input': [...]}, 'fastembed' uses {'texts': [...]}, 'cohere' uses {'texts': [...]}. | `packages/lexigram-vector/src/lexigram/vector/embedding/config.py:EmbeddingClientConfig.format` |
| `LEX_VECTOR__EMBEDDING__MODEL` | str | "nomic-ai/nomic-embed-text-v1.5" | Embedding model identifier passed to the API. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/embedding/config` |
| `LEX_VECTOR__EMBEDDING__MODEL` | str | "nomic-ai/nomic-embed-text-v1.5" | Embedding model identifier passed to the API. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/embedding/config.p` |
| `LEX_VECTOR__EMBEDDING__MODEL` | str | "nomic-ai/nomic-embed-text-v1.5" | Embedding model identifier passed to the API. | `packages/lexigram-vector/src/lexigram/vector/embedding/config.py:EmbeddingClientConfig.model` |
| `LEX_VECTOR__EMBEDDING__TIMEOUT` | float | 30.0 | HTTP request timeout in seconds. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/vector/embedding/config` |
| `LEX_VECTOR__EMBEDDING__TIMEOUT` | float | 30.0 | HTTP request timeout in seconds. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/vector/embedding/config.p` |
| `LEX_VECTOR__EMBEDDING__TIMEOUT` | float | 30.0 | HTTP request timeout in seconds. | `packages/lexigram-vector/src/lexigram/vector/embedding/config.py:EmbeddingClientConfig.timeout` |
| `LEX_VECTOR__ENABLED` | bool | True | Enable the vector store subsystem | `packages/lexigram-vector/src/lexigram/vector/config.py:VectorConfig.enabled` |
| `LEX_VECTOR__ENABLE_CACHE` | bool | False | Enable embedding caching (requires a CacheBackend binding) | `packages/lexigram-vector/src/lexigram/vector/config.py:VectorConfig.enable_cache` |
| `LEX_VECTOR__MAX_RETRIES` | int | (complex) | Maximum number of retries for operations | `packages/lexigram-vector/src/lexigram/vector/config.py:VectorConfig.max_retries` |
| `LEX_VECTOR__MEMORY__MAX_COLLECTIONS` | int | 100 | Maximum number of collections in memory | `packages/lexigram-vector/src/lexigram/vector/config.py:MemoryConfig.memory.max_collections` |
| `LEX_VECTOR__MEMORY__MAX_VECTORS_PER_COLLECTION` | int | 100000 | Maximum number of vectors per collection | `packages/lexigram-vector/src/lexigram/vector/config.py:MemoryConfig.memory.max_vectors_per_collectio` |
| `LEX_VECTOR__PGVECTOR__CREATE_EXTENSION` | bool | True | Whether to create pgvector extension if missing | `packages/lexigram-vector/src/lexigram/vector/config.py:PgVectorConfig.pgvector.create_extension` |
| `LEX_VECTOR__PGVECTOR__DATABASE` | str | "primary" | Name of the database backend from db.backends to use for pgvector. Matches a 'name:' entry in the db.backends list. Defa | `packages/lexigram-vector/src/lexigram/vector/config.py:PgVectorConfig.pgvector.database` |
| `LEX_VECTOR__PGVECTOR__DEFAULT_EF_SEARCH` | int | (complex) | Default ef_search for HNSW index | `packages/lexigram-vector/src/lexigram/vector/config.py:PgVectorConfig.pgvector.default_ef_search` |
| `LEX_VECTOR__PGVECTOR__DEFAULT_LISTS` | int | (complex) | Default number of lists for IVFFlat index | `packages/lexigram-vector/src/lexigram/vector/config.py:PgVectorConfig.pgvector.default_lists` |
| `LEX_VECTOR__PGVECTOR__DEFAULT_PROBES` | int | (complex) | Default number of probes for IVFFlat index | `packages/lexigram-vector/src/lexigram/vector/config.py:PgVectorConfig.pgvector.default_probes` |
| `LEX_VECTOR__PGVECTOR__SCHEMA` | str | "public" | Database schema for vector tables | `packages/lexigram-vector/src/lexigram/vector/config.py:PgVectorConfig.pgvector.schema` |
| `LEX_VECTOR__PGVECTOR__TABLE_PREFIX` | str | "vec_" | Prefix for vector storage tables | `packages/lexigram-vector/src/lexigram/vector/config.py:PgVectorConfig.pgvector.table_prefix` |
| `LEX_VECTOR__PINECONE__API_KEY` | SecretStr | SecretStr(...) | Pinecone API key | `packages/lexigram-vector/src/lexigram/vector/config.py:PineconeConfig.pinecone.api_key` |
| `LEX_VECTOR__PINECONE__ENVIRONMENT` | str | "" | Pinecone environment (e.g. 'us-west1-gcp') | `packages/lexigram-vector/src/lexigram/vector/config.py:PineconeConfig.pinecone.environment` |
| `LEX_VECTOR__PINECONE__INDEX_NAME` | str | "" | Name of the Pinecone index | `packages/lexigram-vector/src/lexigram/vector/config.py:PineconeConfig.pinecone.index_name` |
| `LEX_VECTOR__PINECONE__NAMESPACE` | str | "" | Default namespace for the index | `packages/lexigram-vector/src/lexigram/vector/config.py:PineconeConfig.pinecone.namespace` |
| `LEX_VECTOR__PINECONE__POOL_THREADS` | int | 4 | Number of threads for the connection pool | `packages/lexigram-vector/src/lexigram/vector/config.py:PineconeConfig.pinecone.pool_threads` |
| `LEX_VECTOR__PINECONE__TIMEOUT` | float | (complex) | Request timeout in seconds | `packages/lexigram-vector/src/lexigram/vector/config.py:PineconeConfig.pinecone.timeout` |
| `LEX_VECTOR__QDRANT__API_KEY` | SecretStr  \| None | None | Qdrant API key | `packages/lexigram-vector/src/lexigram/vector/config.py:QdrantConfig.qdrant.api_key` |
| `LEX_VECTOR__QDRANT__GRPC_PORT` | int | 6334 | gRPC port for Qdrant | `packages/lexigram-vector/src/lexigram/vector/config.py:QdrantConfig.qdrant.grpc_port` |
| `LEX_VECTOR__QDRANT__PREFER_GRPC` | bool | True | Whether to prefer gRPC over HTTP | `packages/lexigram-vector/src/lexigram/vector/config.py:QdrantConfig.qdrant.prefer_grpc` |
| `LEX_VECTOR__QDRANT__TIMEOUT` | float | (complex) | Request timeout in seconds | `packages/lexigram-vector/src/lexigram/vector/config.py:QdrantConfig.qdrant.timeout` |
| `LEX_VECTOR__QDRANT__URL` | str | "http://localhost:6333" | Qdrant server URL | `packages/lexigram-vector/src/lexigram/vector/config.py:QdrantConfig.qdrant.url` |
| `LEX_VECTOR__RETRY_DELAY` | float | (complex) | Delay between retries in seconds | `packages/lexigram-vector/src/lexigram/vector/config.py:VectorConfig.retry_delay` |
| `LEX_VECTOR__TENANCY__ENABLED` | bool | False | Enable tenant-aware collection name resolution | `packages/lexigram-vector/src/lexigram/vector/config.py:VectorTenancyConfig.tenancy.enabled` |
| `LEX_VECTOR__TENANCY__RESOLVER_KIND` | str | "templated" | Which ``TenantCollectionResolver`` to use. One of ``"templated"`` or ``"pinecone_namespace"``. | `packages/lexigram-vector/src/lexigram/vector/config.py:VectorTenancyConfig.tenancy.resolver_kind` |
| `LEX_VECTOR__UPSERT_BATCH_SIZE` | int | (complex) | Number of vectors per upsert batch | `packages/lexigram-vector/src/lexigram/vector/config.py:VectorConfig.upsert_batch_size` |
| `LEX_VECTOR__WEAVIATE__API_KEY` | SecretStr  \| None | None | Weaviate API key for authenticated clusters | `packages/lexigram-vector/src/lexigram/vector/config.py:WeaviateConfig.weaviate.api_key` |
| `LEX_VECTOR__WEAVIATE__GRPC_PORT` | int | 50051 | gRPC port for the Weaviate cluster | `packages/lexigram-vector/src/lexigram/vector/config.py:WeaviateConfig.weaviate.grpc_port` |
| `LEX_VECTOR__WEAVIATE__TIMEOUT` | float | (complex) | Request timeout in seconds | `packages/lexigram-vector/src/lexigram/vector/config.py:WeaviateConfig.weaviate.timeout` |
| `LEX_VECTOR__WEAVIATE__URL` | str | "http://localhost:8080" | Weaviate cluster URL (HTTP) | `packages/lexigram-vector/src/lexigram/vector/config.py:WeaviateConfig.weaviate.url` |
| `LEX_WEB__ALLOWED_HOSTS` | list[str] | (required) | Hostnames permitted to reach the application. Empty by default; must be configured before production deployment. | `packages/lexigram-web/src/lexigram/web/security/config.py:SecurityConfig.allowed_hosts` |
| `LEX_WEB__API_DOCS__ENABLED` | bool | True | Enable API documentation endpoints (/docs, /redoc) and auto-configure CSP for their CDN assets | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:APIDocsCo` |
| `LEX_WEB__API_DOCS__ENABLED` | bool | True | Enable API documentation endpoints (/docs, /redoc) and auto-configure CSP for their CDN assets | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:APIDocsConf` |
| `LEX_WEB__API_DOCS__ENABLED` | bool | True | Enable API documentation endpoints (/docs, /redoc) and auto-configure CSP for their CDN assets | `packages/lexigram-web/src/lexigram/web/config.py:APIDocsConfig.api_docs.enabled` |
| `LEX_WEB__API_DOCS__PROVIDER` | str | "both" | Documentation provider: 'swagger', 'redoc', or 'both' | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:APIDocsCo` |
| `LEX_WEB__API_DOCS__PROVIDER` | str | "both" | Documentation provider: 'swagger', 'redoc', or 'both' | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:APIDocsConf` |
| `LEX_WEB__API_DOCS__PROVIDER` | str | "both" | Documentation provider: 'swagger', 'redoc', or 'both' | `packages/lexigram-web/src/lexigram/web/config.py:APIDocsConfig.api_docs.provider` |
| `LEX_WEB__AUTH_EXCLUDE_PATHS` | list[str] | (required) | Paths to exclude from authentication | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig` |
| `LEX_WEB__AUTH_EXCLUDE_PATHS` | list[str] | (required) | Paths to exclude from authentication | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig.a` |
| `LEX_WEB__AUTH_EXCLUDE_PATHS` | list[str] | (required) | Paths to exclude from authentication | `packages/lexigram-web/src/lexigram/web/config.py:WebConfig.auth_exclude_paths` |
| `LEX_WEB__COMPRESSION_ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig` |
| `LEX_WEB__COMPRESSION_ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig.c` |
| `LEX_WEB__COMPRESSION_ENABLED` | bool | True |  | `packages/lexigram-web/src/lexigram/web/config.py:WebConfig.compression_enabled` |
| `LEX_WEB__CORS` | CORSConfig | (required) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig` |
| `LEX_WEB__CORS` | CORSConfig | (required) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig.c` |
| `LEX_WEB__CORS` | CORSConfig | (required) |  | `packages/lexigram-web/src/lexigram/web/config.py:WebConfig.cors` |
| `LEX_WEB__CORS__ALLOWED_ORIGINS` | list[str] | (required) | Allowed origins (use ['*'] to allow all) | `packages/lexigram-web/src/lexigram/web/security/config.py:CORSConfig.cors.allowed_origins` |
| `LEX_WEB__CORS__ALLOW_CREDENTIALS` | bool | False |  | `packages/lexigram-web/src/lexigram/web/security/config.py:CORSConfig.cors.allow_credentials` |
| `LEX_WEB__CORS__ALLOW_HEADERS` | list[str] | (required) |  | `packages/lexigram-web/src/lexigram/web/security/config.py:CORSConfig.cors.allow_headers` |
| `LEX_WEB__CORS__ALLOW_METHODS` | list[str] | (required) |  | `packages/lexigram-web/src/lexigram/web/security/config.py:CORSConfig.cors.allow_methods` |
| `LEX_WEB__CORS__ALLOW_ORIGIN_REGEX` | str  \| None | None | Regex pattern for allowed origins (matched when not in allowed_origins) | `packages/lexigram-web/src/lexigram/web/security/config.py:CORSConfig.cors.allow_origin_regex` |
| `LEX_WEB__CORS__DEBUG_PERMISSIVE` | bool | False | When True and debug mode is active, allow any origin via wildcard (explicit opt-in replacement for the old implicit debu | `packages/lexigram-web/src/lexigram/web/security/config.py:CORSConfig.cors.debug_permissive` |
| `LEX_WEB__CORS__ENABLED` | bool | True | Enable CORS | `packages/lexigram-web/src/lexigram/web/security/config.py:CORSConfig.cors.enabled` |
| `LEX_WEB__CORS__EXPOSE_HEADERS` | list[str] | (required) |  | `packages/lexigram-web/src/lexigram/web/security/config.py:CORSConfig.cors.expose_headers` |
| `LEX_WEB__CORS__MAX_AGE` | int | 600 |  | `packages/lexigram-web/src/lexigram/web/security/config.py:CORSConfig.cors.max_age` |
| `LEX_WEB__CROSS_ORIGIN__EMBEDDER_POLICY` | str | "require-corp" | Cross-Origin-Embedder-Policy header value | `packages/lexigram-web/src/lexigram/web/security/config.py:CrossOriginConfig.cross_origin.embedder_po` |
| `LEX_WEB__CROSS_ORIGIN__ENABLED` | bool | False | Emit cross-origin isolation headers | `packages/lexigram-web/src/lexigram/web/security/config.py:CrossOriginConfig.cross_origin.enabled` |
| `LEX_WEB__CROSS_ORIGIN__OPENER_POLICY` | str | "same-origin" | Cross-Origin-Opener-Policy header value | `packages/lexigram-web/src/lexigram/web/security/config.py:CrossOriginConfig.cross_origin.opener_poli` |
| `LEX_WEB__CROSS_ORIGIN__RESOURCE_POLICY` | str | "same-origin" | Cross-Origin-Resource-Policy header value | `packages/lexigram-web/src/lexigram/web/security/config.py:CrossOriginConfig.cross_origin.resource_po` |
| `LEX_WEB__CSP__DIRECTIVES` | dict[str, Any] | (required) | CSP directives mapping directive name to source expression(s) | `packages/lexigram-web/src/lexigram/web/security/config.py:CSPConfig.csp.directives` |
| `LEX_WEB__CSP__ENABLED` | bool | True | Emit the Content-Security-Policy header | `packages/lexigram-web/src/lexigram/web/security/config.py:CSPConfig.csp.enabled` |
| `LEX_WEB__CSRF__COOKIE_DOMAIN` | str  \| None | None |  | `packages/lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.cookie_domain` |
| `LEX_WEB__CSRF__COOKIE_HTTPONLY` | bool | True |  | `packages/lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.cookie_httponly` |
| `LEX_WEB__CSRF__COOKIE_NAME` | str | "csrf_token" |  | `packages/lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.cookie_name` |
| `LEX_WEB__CSRF__COOKIE_PATH` | str | "/" |  | `packages/lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.cookie_path` |
| `LEX_WEB__CSRF__COOKIE_SAMESITE` | str | "Lax" |  | `packages/lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.cookie_samesite` |
| `LEX_WEB__CSRF__COOKIE_SECURE` | bool | True |  | `packages/lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.cookie_secure` |
| `LEX_WEB__CSRF__ENABLED` | bool | False |  | `packages/lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.enabled` |
| `LEX_WEB__CSRF__EXCLUDED_PATHS` | list[str] | (required) | URL path prefixes exempt from CSRF validation for cookie-less requests; cookie-bearing requests on these paths are still | `packages/lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.excluded_paths` |
| `LEX_WEB__CSRF__EXCLUDE_AUTH_SCHEMES` | list[str] | (required) | Authorization header schemes that bypass CSRF validation (explicit opt-in). | `packages/lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.exclude_auth_schemes` |
| `LEX_WEB__CSRF__EXCLUDE_CONTENT_TYPES` | list[str] | (required) | Content-Type values that bypass CSRF validation (explicit opt-in — JSON requests are validated by default so cookie-auth | `packages/lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.exclude_content_types` |
| `LEX_WEB__CSRF__HEADER_NAME` | str | "X-CSRF-Token" |  | `packages/lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.header_name` |
| `LEX_WEB__CSRF__SECRET_KEY` | str  \| None | None | HMAC secret used to sign and verify CSRF tokens (populated via LEX_WEB__SECURITY__CSRF__SECRET_KEY) | `packages/lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.secret_key` |
| `LEX_WEB__CSRF__TOKEN_LENGTH` | int | 32 |  | `packages/lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.token_length` |
| `LEX_WEB__CSRF__TOKEN_TTL` | int | 3600 | TTL in seconds for synchronizer-mode tokens stored in cache. | `packages/lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.token_ttl` |
| `LEX_WEB__CUSTOM_HEADERS` | dict[str, str] | (required) | Additional HTTP response headers emitted verbatim | `packages/lexigram-web/src/lexigram/web/security/config.py:SecurityConfig.custom_headers` |
| `LEX_WEB__DEBUG_ROUTES` | bool | False | Enable debug routes | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig` |
| `LEX_WEB__DEBUG_ROUTES` | bool | False | Enable debug routes | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig.d` |
| `LEX_WEB__DEBUG_ROUTES` | bool | False | Enable debug routes | `packages/lexigram-web/src/lexigram/web/config.py:WebConfig.debug_routes` |
| `LEX_WEB__DEBUG_ROUTES_TOKEN` | SecretStr  \| None | None | Token required to access debug routes (sent as X-Debug-Token header). | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig` |
| `LEX_WEB__DEBUG_ROUTES_TOKEN` | SecretStr  \| None | None | Token required to access debug routes (sent as X-Debug-Token header). | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig.d` |
| `LEX_WEB__DEBUG_ROUTES_TOKEN` | SecretStr  \| None | None | Token required to access debug routes (sent as X-Debug-Token header). | `packages/lexigram-web/src/lexigram/web/config.py:WebConfig.debug_routes_token` |
| `LEX_WEB__ENABLED` | bool | True | Enable the security subsystem | `packages/lexigram-web/src/lexigram/web/security/config.py:SecurityConfig.enabled` |
| `LEX_WEB__ENABLED` | bool | True |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig` |
| `LEX_WEB__ENABLED` | bool | True |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig.e` |
| `LEX_WEB__ENABLED` | bool | True |  | `packages/lexigram-web/src/lexigram/web/config.py:WebConfig.enabled` |
| `LEX_WEB__ENABLE_AUTH` | bool | False | Enable built-in authentication middleware. Requires authenticators to be registered in the container. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig` |
| `LEX_WEB__ENABLE_AUTH` | bool | False | Enable built-in authentication middleware. Requires authenticators to be registered in the container. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig.e` |
| `LEX_WEB__ENABLE_AUTH` | bool | False | Enable built-in authentication middleware. Requires authenticators to be registered in the container. | `packages/lexigram-web/src/lexigram/web/config.py:WebConfig.enable_auth` |
| `LEX_WEB__ENABLE_CORS` | bool | True |  | `packages/lexigram-web/src/lexigram/web/security/config.py:SecurityConfig.enable_cors` |
| `LEX_WEB__ENABLE_CSRF` | bool | True |  | `packages/lexigram-web/src/lexigram/web/security/config.py:SecurityConfig.enable_csrf` |
| `LEX_WEB__ENABLE_DEBUG_ROUTES_ENV_GATE` | bool | False | Require explicit opt-in for debug route registration. | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig` |
| `LEX_WEB__ENABLE_DEBUG_ROUTES_ENV_GATE` | bool | False | Require explicit opt-in for debug route registration. | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig.e` |
| `LEX_WEB__ENABLE_DEBUG_ROUTES_ENV_GATE` | bool | False | Require explicit opt-in for debug route registration. | `packages/lexigram-web/src/lexigram/web/config.py:WebConfig.enable_debug_routes_env_gate` |
| `LEX_WEB__ENABLE_IDENTITY_RESOLUTION` | bool | False | Automatically resolve OAuth external IDs to internal UUIDs in authenticated requests | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig` |
| `LEX_WEB__ENABLE_IDENTITY_RESOLUTION` | bool | False | Automatically resolve OAuth external IDs to internal UUIDs in authenticated requests | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig.e` |
| `LEX_WEB__ENABLE_IDENTITY_RESOLUTION` | bool | False | Automatically resolve OAuth external IDs to internal UUIDs in authenticated requests | `packages/lexigram-web/src/lexigram/web/config.py:WebConfig.enable_identity_resolution` |
| `LEX_WEB__ENV` | str  \| None | None | Environment (development/staging/production) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig` |
| `LEX_WEB__ENV` | str  \| None | None | Environment (development/staging/production) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig.e` |
| `LEX_WEB__ENV` | str  \| None | None | Environment (development/staging/production) | `packages/lexigram-web/src/lexigram/web/config.py:WebConfig.env` |
| `LEX_WEB__HEADERS__CONTENT_TYPE_NOSNIFF` | bool | True |  | `packages/lexigram-web/src/lexigram/web/security/config.py:SecurityHeadersConfig.headers.content_type` |
| `LEX_WEB__HEADERS__CSP` | str  \| None | None |  | `packages/lexigram-web/src/lexigram/web/security/config.py:SecurityHeadersConfig.headers.csp` |
| `LEX_WEB__HEADERS__FRAME_OPTIONS` | str | "DENY" |  | `packages/lexigram-web/src/lexigram/web/security/config.py:SecurityHeadersConfig.headers.frame_option` |
| `LEX_WEB__HEADERS__HSTS_INCLUDE_SUBDOMAINS` | bool | True |  | `packages/lexigram-web/src/lexigram/web/security/config.py:SecurityHeadersConfig.headers.hsts_include` |
| `LEX_WEB__HEADERS__HSTS_MAX_AGE` | int | 31536000 |  | `packages/lexigram-web/src/lexigram/web/security/config.py:SecurityHeadersConfig.headers.hsts_max_age` |
| `LEX_WEB__HEADERS__PERMISSIONS_POLICY` | str  \| None | None |  | `packages/lexigram-web/src/lexigram/web/security/config.py:SecurityHeadersConfig.headers.permissions_` |
| `LEX_WEB__HEADERS__REFERRER_POLICY` | str | "strict-origin-when-cross-origin" |  | `packages/lexigram-web/src/lexigram/web/security/config.py:SecurityHeadersConfig.headers.referrer_pol` |
| `LEX_WEB__HEADERS__XSS_PROTECTION` | str | "1; mode=block" |  | `packages/lexigram-web/src/lexigram/web/security/config.py:SecurityHeadersConfig.headers.xss_protecti` |
| `LEX_WEB__HSTS__ENABLED` | bool | False | Emit the Strict-Transport-Security header | `packages/lexigram-web/src/lexigram/web/security/config.py:HSTSConfig.hsts.enabled` |
| `LEX_WEB__HSTS__INCLUDE_SUBDOMAINS` | bool | True | Apply HSTS to all subdomains | `packages/lexigram-web/src/lexigram/web/security/config.py:HSTSConfig.hsts.include_subdomains` |
| `LEX_WEB__HSTS__MAX_AGE` | int | 31536000 | HSTS max-age in seconds (default 1 year) | `packages/lexigram-web/src/lexigram/web/security/config.py:HSTSConfig.hsts.max_age` |
| `LEX_WEB__HSTS__PRELOAD` | bool | False | Include site in HSTS preload list | `packages/lexigram-web/src/lexigram/web/security/config.py:HSTSConfig.hsts.preload` |
| `LEX_WEB__MAX_BODY_SIZE` | int  \| None | (complex) | Maximum allowed request body size in bytes. Requests with a Content-Length header exceeding this limit receive a 413 res | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig` |
| `LEX_WEB__MAX_BODY_SIZE` | int  \| None | (complex) | Maximum allowed request body size in bytes. Requests with a Content-Length header exceeding this limit receive a 413 res | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig.m` |
| `LEX_WEB__MAX_BODY_SIZE` | int  \| None | (complex) | Maximum allowed request body size in bytes. Requests with a Content-Length header exceeding this limit receive a 413 res | `packages/lexigram-web/src/lexigram/web/config.py:WebConfig.max_body_size` |
| `LEX_WEB__NAME` | str | "web" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig` |
| `LEX_WEB__NAME` | str | "web" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig.n` |
| `LEX_WEB__NAME` | str | "web" |  | `packages/lexigram-web/src/lexigram/web/config.py:WebConfig.name` |
| `LEX_WEB__OPENAPI_TITLE` | str | "API" | OpenAPI Title | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig` |
| `LEX_WEB__OPENAPI_TITLE` | str | "API" | OpenAPI Title | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig.o` |
| `LEX_WEB__OPENAPI_TITLE` | str | "API" | OpenAPI Title | `packages/lexigram-web/src/lexigram/web/config.py:WebConfig.openapi_title` |
| `LEX_WEB__OPENAPI_URL` | str  \| None | (complex) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig` |
| `LEX_WEB__OPENAPI_URL` | str  \| None | (complex) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig.o` |
| `LEX_WEB__OPENAPI_URL` | str  \| None | (complex) |  | `packages/lexigram-web/src/lexigram/web/config.py:WebConfig.openapi_url` |
| `LEX_WEB__OPENAPI_VERSION` | str | "1.0.0" | OpenAPI Version | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig` |
| `LEX_WEB__OPENAPI_VERSION` | str | "1.0.0" | OpenAPI Version | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig.o` |
| `LEX_WEB__OPENAPI_VERSION` | str | "1.0.0" | OpenAPI Version | `packages/lexigram-web/src/lexigram/web/config.py:WebConfig.openapi_version` |
| `LEX_WEB__PERMISSIONS_POLICY` | dict[str, str] | (required) | Permissions-Policy directive map | `packages/lexigram-web/src/lexigram/web/security/config.py:SecurityConfig.permissions_policy` |
| `LEX_WEB__RATE_LIMIT__DEFAULT_LIMIT` | int | (complex) | Max requests per window | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:RateLimit` |
| `LEX_WEB__RATE_LIMIT__DEFAULT_LIMIT` | int | (complex) | Max requests per window | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:RateLimitCo` |
| `LEX_WEB__RATE_LIMIT__DEFAULT_LIMIT` | int | (complex) | Max requests per window | `packages/lexigram-web/src/lexigram/web/config.py:RateLimitConfig.rate_limit.default_limit` |
| `LEX_WEB__RATE_LIMIT__DEFAULT_WINDOW` | int | (complex) | Window size in seconds | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:RateLimit` |
| `LEX_WEB__RATE_LIMIT__DEFAULT_WINDOW` | int | (complex) | Window size in seconds | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:RateLimitCo` |
| `LEX_WEB__RATE_LIMIT__DEFAULT_WINDOW` | int | (complex) | Window size in seconds | `packages/lexigram-web/src/lexigram/web/config.py:RateLimitConfig.rate_limit.default_window` |
| `LEX_WEB__RATE_LIMIT__ENABLED` | bool | True | Enable rate limiting. When true, RateLimitMiddleware enforces the matched per-path rule or the default_limit/default_win | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:RateLimit` |
| `LEX_WEB__RATE_LIMIT__ENABLED` | bool | True | Enable rate limiting. When true, RateLimitMiddleware enforces the matched per-path rule or the default_limit/default_win | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:RateLimitCo` |
| `LEX_WEB__RATE_LIMIT__ENABLED` | bool | True | Enable rate limiting. When true, RateLimitMiddleware enforces the matched per-path rule or the default_limit/default_win | `packages/lexigram-web/src/lexigram/web/config.py:RateLimitConfig.rate_limit.enabled` |
| `LEX_WEB__RATE_LIMIT__RULES` | dict[str, RateLimitRuleConfig] | (required) | Per-path rate limit rules; longest-prefix match wins | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:RateLimit` |
| `LEX_WEB__RATE_LIMIT__RULES` | dict[str, RateLimitRuleConfig] | (required) | Per-path rate limit rules; longest-prefix match wins | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:RateLimitCo` |
| `LEX_WEB__RATE_LIMIT__RULES` | dict[str, RateLimitRuleConfig] | (required) | Per-path rate limit rules; longest-prefix match wins | `packages/lexigram-web/src/lexigram/web/config.py:RateLimitConfig.rate_limit.rules` |
| `LEX_WEB__RATE_LIMIT__STORAGE_BACKEND` | str | "memory" | Storage backend (memory/redis) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:RateLimit` |
| `LEX_WEB__RATE_LIMIT__STORAGE_BACKEND` | str | "memory" | Storage backend (memory/redis) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:RateLimitCo` |
| `LEX_WEB__RATE_LIMIT__STORAGE_BACKEND` | str | "memory" | Storage backend (memory/redis) | `packages/lexigram-web/src/lexigram/web/config.py:RateLimitConfig.rate_limit.storage_backend` |
| `LEX_WEB__RATE_LIMIT__WHITELIST_IPS` | list[str] | (required) | Exempt IP addresses | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:RateLimit` |
| `LEX_WEB__RATE_LIMIT__WHITELIST_IPS` | list[str] | (required) | Exempt IP addresses | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:RateLimitCo` |
| `LEX_WEB__RATE_LIMIT__WHITELIST_IPS` | list[str] | (required) | Exempt IP addresses | `packages/lexigram-web/src/lexigram/web/config.py:RateLimitConfig.rate_limit.whitelist_ips` |
| `LEX_WEB__REDOC_JS_URL` | str  \| None | None |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig` |
| `LEX_WEB__REDOC_JS_URL` | str  \| None | None |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig.r` |
| `LEX_WEB__REDOC_JS_URL` | str  \| None | None |  | `packages/lexigram-web/src/lexigram/web/config.py:WebConfig.redoc_js_url` |
| `LEX_WEB__REDOC_URL` | str  \| None | "/redoc" |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig` |
| `LEX_WEB__REDOC_URL` | str  \| None | "/redoc" |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig.r` |
| `LEX_WEB__REDOC_URL` | str  \| None | "/redoc" |  | `packages/lexigram-web/src/lexigram/web/config.py:WebConfig.redoc_url` |
| `LEX_WEB__REFERRER_POLICY` | str | "strict-origin-when-cross-origin" | Referrer-Policy header value | `packages/lexigram-web/src/lexigram/web/security/config.py:SecurityConfig.referrer_policy` |
| `LEX_WEB__ROLE_GUARD__RULES` | list[RoleGuardRuleConfig] | (required) | Role guard rules in declaration order | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:RoleGuard` |
| `LEX_WEB__ROLE_GUARD__RULES` | list[RoleGuardRuleConfig] | (required) | Role guard rules in declaration order | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:RoleGuardCo` |
| `LEX_WEB__ROLE_GUARD__RULES` | list[RoleGuardRuleConfig] | (required) | Role guard rules in declaration order | `packages/lexigram-web/src/lexigram/web/config.py:RoleGuardConfig.role_guard.rules` |
| `LEX_WEB__SECURITY` | SecurityConfig | (required) | Security configuration (HSTS, CSP, cross-origin, CSRF, headers) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig` |
| `LEX_WEB__SECURITY` | SecurityConfig | (required) | Security configuration (HSTS, CSP, cross-origin, CSRF, headers) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig.s` |
| `LEX_WEB__SECURITY` | SecurityConfig | (required) | Security configuration (HSTS, CSP, cross-origin, CSRF, headers) | `packages/lexigram-web/src/lexigram/web/config.py:WebConfig.security` |
| `LEX_WEB__SERVER__DEBUG` | bool | False | Enable debug mode | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:ServerCon` |
| `LEX_WEB__SERVER__DEBUG` | bool | False | Enable debug mode | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:ServerConfi` |
| `LEX_WEB__SERVER__DEBUG` | bool | False | Enable debug mode | `packages/lexigram-web/src/lexigram/web/config.py:ServerConfig.server.debug` |
| `LEX_WEB__SERVER__HOST` | str | (complex) | Bind host | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:ServerCon` |
| `LEX_WEB__SERVER__HOST` | str | (complex) | Bind host | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:ServerConfi` |
| `LEX_WEB__SERVER__HOST` | str | (complex) | Bind host | `packages/lexigram-web/src/lexigram/web/config.py:ServerConfig.server.host` |
| `LEX_WEB__SERVER__PORT` | int | (complex) | Bind port | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:ServerCon` |
| `LEX_WEB__SERVER__PORT` | int | (complex) | Bind port | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:ServerConfi` |
| `LEX_WEB__SERVER__PORT` | int | (complex) | Bind port | `packages/lexigram-web/src/lexigram/web/config.py:ServerConfig.server.port` |
| `LEX_WEB__SERVER__RELOAD` | bool | (complex) | Enable auto-reload | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:ServerCon` |
| `LEX_WEB__SERVER__RELOAD` | bool | (complex) | Enable auto-reload | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:ServerConfi` |
| `LEX_WEB__SERVER__RELOAD` | bool | (complex) | Enable auto-reload | `packages/lexigram-web/src/lexigram/web/config.py:ServerConfig.server.reload` |
| `LEX_WEB__SERVER__WORKERS` | int | (complex) | Number of workers | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:ServerCon` |
| `LEX_WEB__SERVER__WORKERS` | int | (complex) | Number of workers | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:ServerConfi` |
| `LEX_WEB__SERVER__WORKERS` | int | (complex) | Number of workers | `packages/lexigram-web/src/lexigram/web/config.py:ServerConfig.server.workers` |
| `LEX_WEB__STATIC__DIRECTORY` | str | "static" | Directory to serve | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:StaticFil` |
| `LEX_WEB__STATIC__DIRECTORY` | str | "static" | Directory to serve | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:StaticFileC` |
| `LEX_WEB__STATIC__DIRECTORY` | str | "static" | Directory to serve | `packages/lexigram-web/src/lexigram/web/config.py:StaticFileConfig.static.directory` |
| `LEX_WEB__STATIC__ENABLED` | bool | False | Enable static file serving | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:StaticFil` |
| `LEX_WEB__STATIC__ENABLED` | bool | False | Enable static file serving | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:StaticFileC` |
| `LEX_WEB__STATIC__ENABLED` | bool | False | Enable static file serving | `packages/lexigram-web/src/lexigram/web/config.py:StaticFileConfig.static.enabled` |
| `LEX_WEB__STATIC__HTML` | bool | False | Serve HTML files (SPA mode) | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:StaticFil` |
| `LEX_WEB__STATIC__HTML` | bool | False | Serve HTML files (SPA mode) | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:StaticFileC` |
| `LEX_WEB__STATIC__HTML` | bool | False | Serve HTML files (SPA mode) | `packages/lexigram-web/src/lexigram/web/config.py:StaticFileConfig.static.html` |
| `LEX_WEB__STATIC__PREFIX` | str | "/static" | URL prefix for static files | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:StaticFil` |
| `LEX_WEB__STATIC__PREFIX` | str | "/static" | URL prefix for static files | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:StaticFileC` |
| `LEX_WEB__STATIC__PREFIX` | str | "/static" | URL prefix for static files | `packages/lexigram-web/src/lexigram/web/config.py:StaticFileConfig.static.prefix` |
| `LEX_WEB__SWAGGER_CSS_URL` | str  \| None | None |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig` |
| `LEX_WEB__SWAGGER_CSS_URL` | str  \| None | None |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig.s` |
| `LEX_WEB__SWAGGER_CSS_URL` | str  \| None | None |  | `packages/lexigram-web/src/lexigram/web/config.py:WebConfig.swagger_css_url` |
| `LEX_WEB__SWAGGER_JS_URL` | str  \| None | None |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig` |
| `LEX_WEB__SWAGGER_JS_URL` | str  \| None | None |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig.s` |
| `LEX_WEB__SWAGGER_JS_URL` | str  \| None | None |  | `packages/lexigram-web/src/lexigram/web/config.py:WebConfig.swagger_js_url` |
| `LEX_WEB__SWAGGER_UI_URL` | str  \| None | (complex) |  | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig` |
| `LEX_WEB__SWAGGER_UI_URL` | str  \| None | (complex) |  | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig.s` |
| `LEX_WEB__SWAGGER_UI_URL` | str  \| None | (complex) |  | `packages/lexigram-web/src/lexigram/web/config.py:WebConfig.swagger_ui_url` |
| `LEX_WEB__TEMPLATE_DIRECTORY` | str | "templates" | Directory for Jinja2 templates | `experimental/apps/lexigram-admin/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig` |
| `LEX_WEB__TEMPLATE_DIRECTORY` | str | "templates" | Directory for Jinja2 templates | `experimental/apps/lexigram-cli/.venv/lib/python3.13/site-packages/lexigram/web/config.py:WebConfig.t` |
| `LEX_WEB__TEMPLATE_DIRECTORY` | str | "templates" | Directory for Jinja2 templates | `packages/lexigram-web/src/lexigram/web/config.py:WebConfig.template_directory` |

## Non-Config ENV Sources

| Env Var | Source | Rationale |
|---------|--------|-----------|
| `LEX_DEBUG` | `core/lexigram/src/lexigram/logging/debug.py` | Early-boot logging toggle before typed config is available. |
| `LEX_QUIET` | `core/lexigram/src/lexigram/app/base.py` | Controls startup banner suppression during process bootstrap. |
| `LEX_CONFIG` | `experimental/apps/lexigram-cli/src/lexigram/cli/lib/config_loader.py` | CLI override for explicit configuration file path. |

---

*This document is auto-generated. Do not edit manually.*
