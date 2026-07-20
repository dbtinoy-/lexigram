# AUDIT_ENV_VARS.md — Lexigram Framework Environment Variables

> **Source**: Extracted from `config.py` root settings classes and known non-config env reads.

---

## Summary

- Packages scanned: 35
- Documented env var entries: 917
- Unique env var names: 916
- Duplicate env var names: 1
- Intentional non-config env sources: 3

## Duplicate Analysis

| Env Var | Occurrences |
|---------|-------------|
| `LEX_WEB__ENABLED` | 2 |

## Package Registry

### `lexigram-admin`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_ADMIN__API_PREFIX` | str | "/admin/api" |  | `lexigram-admin/src/lexigram/admin/config.py:AdminConfig.api_prefix` |
| `LEX_ADMIN__AUDIT__READ_AUDIT_ENABLED` | bool | False | Log read operations (off by default; compliance mode only). | `lexigram-admin/src/lexigram/admin/config.py:AdminAuditConfig.audit.read_audit_enabled` |
| `LEX_ADMIN__AUTH__CSRF_TOKEN_LIFETIME` | int | 3600 | CSRF token expiry in seconds | `lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.csrf_token_lifetime` |
| `LEX_ADMIN__AUTH__EMAIL_OTP__ENABLED` | bool | True | Enable email OTP factor | `lexigram-admin/src/lexigram/admin/config.py:AdminEmailOtpConfig.auth.email_otp.enabled` |
| `LEX_ADMIN__AUTH__EMAIL_OTP__RESEND_COOLDOWN_SECONDS` | int | 60 | Minimum seconds between email OTP sends | `lexigram-admin/src/lexigram/admin/config.py:AdminEmailOtpConfig.auth.email_otp.resend_cooldown_secon` |
| `LEX_ADMIN__AUTH__EMAIL_OTP__TTL_MINUTES` | int | 10 | Code validity window in minutes | `lexigram-admin/src/lexigram/admin/config.py:AdminEmailOtpConfig.auth.email_otp.ttl_minutes` |
| `LEX_ADMIN__AUTH__EMAIL_VERIFICATION__ENABLED` | bool | True | Enable email verification flow | `lexigram-admin/src/lexigram/admin/config.py:AdminEmailVerificationConfig.auth.email_verification.ena` |
| `LEX_ADMIN__AUTH__EMAIL_VERIFICATION__ENFORCEMENT` | bool | True | Block login until the email is verified | `lexigram-admin/src/lexigram/admin/config.py:AdminEmailVerificationConfig.auth.email_verification.enf` |
| `LEX_ADMIN__AUTH__EMAIL_VERIFICATION__TOKEN_TTL_HOURS` | int | 24 | Verify link validity in hours | `lexigram-admin/src/lexigram/admin/config.py:AdminEmailVerificationConfig.auth.email_verification.tok` |
| `LEX_ADMIN__AUTH__ENABLED` | bool | True | Enable authentication | `lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.enabled` |
| `LEX_ADMIN__AUTH__ENV` | Literal['development', 'staging', 'production'] | "development" | Deployment environment for cookie security defaults | `lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.env` |
| `LEX_ADMIN__AUTH__IDLE_TIMEOUT` | int | 3600 | Session idle timeout in seconds | `lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.idle_timeout` |
| `LEX_ADMIN__AUTH__LOGIN_URL` | str | "/admin/login" |  | `lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.login_url` |
| `LEX_ADMIN__AUTH__LOGOUT_URL` | str | "/admin/logout" |  | `lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.logout_url` |
| `LEX_ADMIN__AUTH__MFA__ENABLED` | bool | True | Enable TOTP 2FA | `lexigram-admin/src/lexigram/admin/config.py:AdminMfaConfig.auth.mfa.enabled` |
| `LEX_ADMIN__AUTH__MFA__FACTOR` | str | "totp" | Second factor used at login: 'totp' (authenticator app) or 'email' (one-time code) | `lexigram-admin/src/lexigram/admin/config.py:AdminMfaConfig.auth.mfa.factor` |
| `LEX_ADMIN__AUTH__MFA__ISSUER` | str | "Lexigram Admin" | TOTP issuer label shown in authenticator apps | `lexigram-admin/src/lexigram/admin/config.py:AdminMfaConfig.auth.mfa.issuer` |
| `LEX_ADMIN__AUTH__MFA__SKEW` | int | 1 | Allowed clock skew in 30 second steps | `lexigram-admin/src/lexigram/admin/config.py:AdminMfaConfig.auth.mfa.skew` |
| `LEX_ADMIN__AUTH__OAUTH_ENABLED` | bool | False |  | `lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.oauth_enabled` |
| `LEX_ADMIN__AUTH__OAUTH_PROVIDERS` | list[str] | (required) |  | `lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.oauth_providers` |
| `LEX_ADMIN__AUTH__PASSWORD_POLICY__MAX_LENGTH` | int | 128 |  | `lexigram-admin/src/lexigram/admin/config.py:AdminPasswordPolicyConfig.auth.password_policy.max_lengt` |
| `LEX_ADMIN__AUTH__PASSWORD_POLICY__MIN_LENGTH` | int | 12 |  | `lexigram-admin/src/lexigram/admin/config.py:AdminPasswordPolicyConfig.auth.password_policy.min_lengt` |
| `LEX_ADMIN__AUTH__PASSWORD_POLICY__REJECT_COMMON_PASSWORDS` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:AdminPasswordPolicyConfig.auth.password_policy.reject_co` |
| `LEX_ADMIN__AUTH__PASSWORD_POLICY__REJECT_CONTAINING_EMAIL` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:AdminPasswordPolicyConfig.auth.password_policy.reject_co` |
| `LEX_ADMIN__AUTH__PASSWORD_POLICY__REQUIRE_DIGIT` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:AdminPasswordPolicyConfig.auth.password_policy.require_d` |
| `LEX_ADMIN__AUTH__PASSWORD_POLICY__REQUIRE_LOWERCASE` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:AdminPasswordPolicyConfig.auth.password_policy.require_l` |
| `LEX_ADMIN__AUTH__PASSWORD_POLICY__REQUIRE_SPECIAL` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:AdminPasswordPolicyConfig.auth.password_policy.require_s` |
| `LEX_ADMIN__AUTH__PASSWORD_POLICY__REQUIRE_UPPERCASE` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:AdminPasswordPolicyConfig.auth.password_policy.require_u` |
| `LEX_ADMIN__AUTH__PERMISSION_CACHE_TTL` | int | 300 |  | `lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.permission_cache_ttl` |
| `LEX_ADMIN__AUTH__PRINCIPAL_SOURCE` | Literal['internal', 'app'] | "internal" |  | `lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.principal_source` |
| `LEX_ADMIN__AUTH__REGISTRATION__ALLOWED_EMAIL_DOMAINS` | list[str] | (required) | Restrict registration to these email domains (empty = any) | `lexigram-admin/src/lexigram/admin/config.py:AdminRegistrationConfig.auth.registration.allowed_email_` |
| `LEX_ADMIN__AUTH__REGISTRATION__DEFAULT_ROLE` | str | "admin" | Role granted to new accounts | `lexigram-admin/src/lexigram/admin/config.py:AdminRegistrationConfig.auth.registration.default_role` |
| `LEX_ADMIN__AUTH__REGISTRATION__ENABLED` | bool | False | Allow self-service registration | `lexigram-admin/src/lexigram/admin/config.py:AdminRegistrationConfig.auth.registration.enabled` |
| `LEX_ADMIN__AUTH__ROLES` | dict[str, Any] | (required) |  | `lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.roles` |
| `LEX_ADMIN__AUTH__SECURITY__IP_RATE_LIMIT_ENABLED` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:AdminSecurityConfig.auth.security.ip_rate_limit_enabled` |
| `LEX_ADMIN__AUTH__SECURITY__IP_RATE_LIMIT_PER_15_MINUTES` | int | 30 |  | `lexigram-admin/src/lexigram/admin/config.py:AdminSecurityConfig.auth.security.ip_rate_limit_per_15_m` |
| `LEX_ADMIN__AUTH__SECURITY__IP_RATE_LIMIT_PER_HOUR` | int | 60 |  | `lexigram-admin/src/lexigram/admin/config.py:AdminSecurityConfig.auth.security.ip_rate_limit_per_hour` |
| `LEX_ADMIN__AUTH__SECURITY__IP_RATE_LIMIT_PER_MINUTE` | int | 10 |  | `lexigram-admin/src/lexigram/admin/config.py:AdminSecurityConfig.auth.security.ip_rate_limit_per_minu` |
| `LEX_ADMIN__AUTH__SECURITY__LOCKOUT_THRESHOLDS` | list[tuple[int, int]] | (required) |  | `lexigram-admin/src/lexigram/admin/config.py:AdminSecurityConfig.auth.security.lockout_thresholds` |
| `LEX_ADMIN__AUTH__SECURITY__PERMANENT_LOCKOUT_THRESHOLD` | int | 50 |  | `lexigram-admin/src/lexigram/admin/config.py:AdminSecurityConfig.auth.security.permanent_lockout_thre` |
| `LEX_ADMIN__AUTH__SECURITY__SETUP_TOKEN` | str  \| None | None | Optional ADMIN_SETUP_TOKEN — when set, must be provided during first-run setup. | `lexigram-admin/src/lexigram/admin/config.py:AdminSecurityConfig.auth.security.setup_token` |
| `LEX_ADMIN__AUTH__SECURITY__SETUP_TOKEN_OPTIN_UNSAFE` | bool | False | Explicit escape hatch: boot without a setup token. Only for local/ephemeral environments — leaves the first-run wizard o | `lexigram-admin/src/lexigram/admin/config.py:AdminSecurityConfig.auth.security.setup_token_optin_unsa` |
| `LEX_ADMIN__AUTH__SESSION_LIFETIME` | int | 86400 |  | `lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.session_lifetime` |
| `LEX_ADMIN__AUTH__SESSION_SECRET` | SecretStr | SecretStr(...) | Session secret for signing | `lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.session_secret` |
| `LEX_ADMIN__AUTH__USERS` | list[Any] | (required) |  | `lexigram-admin/src/lexigram/admin/config.py:AdminAuthConfig.auth.users` |
| `LEX_ADMIN__CLUSTERS__EXTRA` | list[ClusterSpec] | (required) | Extra clusters beyond the built-in infrastructure cluster | `lexigram-admin/src/lexigram/admin/config.py:AdminClustersConfig.clusters.extra` |
| `LEX_ADMIN__COMMANDS` | list[dict[str, Any]] | (required) |  | `lexigram-admin/src/lexigram/admin/config.py:AdminConfig.commands` |
| `LEX_ADMIN__CONTRIBUTORS` | dict[str, ContributorConfig] | (required) |  | `lexigram-admin/src/lexigram/admin/config.py:AdminConfig.contributors` |
| `LEX_ADMIN__CONTRIBUTOR_COLLISION_MODE` | Literal['warn', 'error'] | "warn" | How to handle name collisions when multiple contributors register widgets, pages, or routes with the same name. 'warn' ( | `lexigram-admin/src/lexigram/admin/config.py:AdminConfig.contributor_collision_mode` |
| `LEX_ADMIN__DASHBOARD_LAYOUT__LAYOUT` | Literal['grid', 'masonry'] | "grid" |  | `lexigram-admin/src/lexigram/admin/config.py:DashboardLayoutConfig.dashboard_layout.layout` |
| `LEX_ADMIN__DASHBOARD_LAYOUT__MAX_WIDGETS` | int | 20 |  | `lexigram-admin/src/lexigram/admin/config.py:DashboardLayoutConfig.dashboard_layout.max_widgets` |
| `LEX_ADMIN__DASHBOARD_LAYOUT__WIDGET_REFRESH_DEFAULT` | int | 30 |  | `lexigram-admin/src/lexigram/admin/config.py:DashboardLayoutConfig.dashboard_layout.widget_refresh_de` |
| `LEX_ADMIN__DATA__QUERY_TIMEOUT_SECONDS` | int | 5 |  | `lexigram-admin/src/lexigram/admin/config.py:AdminDataConfig.data.query_timeout_seconds` |
| `LEX_ADMIN__DEBUG` | bool | False |  | `lexigram-admin/src/lexigram/admin/config.py:AdminConfig.debug` |
| `LEX_ADMIN__ENABLED` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:AdminConfig.enabled` |
| `LEX_ADMIN__EXTENSIONS` | dict[str, Any] | (required) |  | `lexigram-admin/src/lexigram/admin/config.py:AdminConfig.extensions` |
| `LEX_ADMIN__FEATURES__ACTIVITY_FEED` | bool | False |  | `lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.activity_feed` |
| `LEX_ADMIN__FEATURES__API_DOCS` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.api_docs` |
| `LEX_ADMIN__FEATURES__AUDIT_LOGGING` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.audit_logging` |
| `LEX_ADMIN__FEATURES__AUTOSAVE` | bool | False |  | `lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.autosave` |
| `LEX_ADMIN__FEATURES__COMMAND_PALETTE` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.command_palette` |
| `LEX_ADMIN__FEATURES__KEYBOARD_SHORTCUTS` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.keyboard_shortcuts` |
| `LEX_ADMIN__FEATURES__NOTIFICATIONS` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.notifications` |
| `LEX_ADMIN__FEATURES__OPTIMISTIC_UPDATES` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.optimistic_updates` |
| `LEX_ADMIN__FEATURES__SEARCH` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.search` |
| `LEX_ADMIN__FEATURES__THEME_TOGGLE` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.theme_toggle` |
| `LEX_ADMIN__FEATURES__UNDO_REDO` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.undo_redo` |
| `LEX_ADMIN__FEATURES__WEBHOOKS` | bool | False |  | `lexigram-admin/src/lexigram/admin/config.py:AdminFeaturesConfig.features.webhooks` |
| `LEX_ADMIN__FORM_DEFAULTS__AUTOSAVE_ENABLED` | bool | False |  | `lexigram-admin/src/lexigram/admin/config.py:FormDefaults.form_defaults.autosave_enabled` |
| `LEX_ADMIN__FORM_DEFAULTS__AUTOSAVE_INTERVAL_MS` | int | 30000 |  | `lexigram-admin/src/lexigram/admin/config.py:FormDefaults.form_defaults.autosave_interval_ms` |
| `LEX_ADMIN__FORM_DEFAULTS__CONFIRM_UNSAVED_CHANGES` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:FormDefaults.form_defaults.confirm_unsaved_changes` |
| `LEX_ADMIN__FORM_DEFAULTS__INLINE_VALIDATION` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:FormDefaults.form_defaults.inline_validation` |
| `LEX_ADMIN__FORM_DEFAULTS__SHOW_REQUIRED_INDICATOR` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:FormDefaults.form_defaults.show_required_indicator` |
| `LEX_ADMIN__FRAMEWORK_PAGES__ENABLED` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:FrameworkPagesConfig.framework_pages.enabled` |
| `LEX_ADMIN__FRAMEWORK_PAGES__REQUIRE_PERMISSION` | str | "admin:framework:access" |  | `lexigram-admin/src/lexigram/admin/config.py:FrameworkPagesConfig.framework_pages.require_permission` |
| `LEX_ADMIN__HTMX_PREFIX` | str | "/admin/htmx" |  | `lexigram-admin/src/lexigram/admin/config.py:AdminConfig.htmx_prefix` |
| `LEX_ADMIN__INTEGRATIONS__CACHE__DEFAULT_TTL_SECONDS` | int | 60 |  | `lexigram-admin/src/lexigram/admin/config.py:CacheIntegrationConfig.integrations.cache.default_ttl_se` |
| `LEX_ADMIN__INTEGRATIONS__CACHE__ENABLED` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:CacheIntegrationConfig.integrations.cache.enabled` |
| `LEX_ADMIN__INTEGRATIONS__CACHE__KEY_PREFIX` | str | "admin" |  | `lexigram-admin/src/lexigram/admin/config.py:CacheIntegrationConfig.integrations.cache.key_prefix` |
| `LEX_ADMIN__INTEGRATIONS__ENABLED` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:AdminIntegrationsConfig.integrations.enabled` |
| `LEX_ADMIN__INTEGRATIONS__FEATURES__ENABLED` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:FeaturesIntegrationConfig.integrations.features.enabled` |
| `LEX_ADMIN__INTEGRATIONS__MONITOR__ENABLED` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:MonitorIntegrationConfig.integrations.monitor.enabled` |
| `LEX_ADMIN__INTEGRATIONS__RESILIENCE__CIRCUIT_FAILURE_THRESHOLD` | int | 5 |  | `lexigram-admin/src/lexigram/admin/config.py:ResilienceIntegrationConfig.integrations.resilience.circ` |
| `LEX_ADMIN__INTEGRATIONS__RESILIENCE__ENABLED` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:ResilienceIntegrationConfig.integrations.resilience.enab` |
| `LEX_ADMIN__INTEGRATIONS__RESILIENCE__RETRY_MAX_ATTEMPTS` | int | 3 |  | `lexigram-admin/src/lexigram/admin/config.py:ResilienceIntegrationConfig.integrations.resilience.retr` |
| `LEX_ADMIN__INTEGRATIONS__SEARCH__ENABLED` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:SearchIntegrationConfig.integrations.search.enabled` |
| `LEX_ADMIN__INTEGRATIONS__SEARCH__FALLBACK_TO_LIKE` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:SearchIntegrationConfig.integrations.search.fallback_to_` |
| `LEX_ADMIN__INTEGRATIONS__STORAGE__ENABLED` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:StorageIntegrationConfig.integrations.storage.enabled` |
| `LEX_ADMIN__INTEGRATIONS__STORAGE__PRESIGNED_URL_EXPIRY` | int | 3600 |  | `lexigram-admin/src/lexigram/admin/config.py:StorageIntegrationConfig.integrations.storage.presigned_` |
| `LEX_ADMIN__INTEGRATIONS__TASKS__BULK_THRESHOLD` | int | 25 |  | `lexigram-admin/src/lexigram/admin/config.py:TasksIntegrationConfig.integrations.tasks.bulk_threshold` |
| `LEX_ADMIN__INTEGRATIONS__TASKS__ENABLED` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:TasksIntegrationConfig.integrations.tasks.enabled` |
| `LEX_ADMIN__NAME` | str | "admin" |  | `lexigram-admin/src/lexigram/admin/config.py:AdminConfig.name` |
| `LEX_ADMIN__NAVIGATION_GROUPS` | dict[str, AdminNavigationGroup] | (required) |  | `lexigram-admin/src/lexigram/admin/config.py:AdminConfig.navigation_groups` |
| `LEX_ADMIN__OBSERVABILITY__HIGH_CARDINALITY_LABELS_ENABLED` | bool | False |  | `lexigram-admin/src/lexigram/admin/config.py:AdminObservabilityConfig.observability.high_cardinality_` |
| `LEX_ADMIN__OBSERVABILITY__METRICS_ENABLED` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:AdminObservabilityConfig.observability.metrics_enabled` |
| `LEX_ADMIN__PREFIX` | str | "/admin" |  | `lexigram-admin/src/lexigram/admin/config.py:AdminConfig.prefix` |
| `LEX_ADMIN__RATE_LIMIT__BULK_PER_MINUTE` | int | 5 |  | `lexigram-admin/src/lexigram/admin/config.py:AdminRateLimitConfig.rate_limit.bulk_per_minute` |
| `LEX_ADMIN__RATE_LIMIT__BURST_SIZE` | int | 10 |  | `lexigram-admin/src/lexigram/admin/config.py:AdminRateLimitConfig.rate_limit.burst_size` |
| `LEX_ADMIN__RATE_LIMIT__CREATE_PER_MINUTE` | int | 30 |  | `lexigram-admin/src/lexigram/admin/config.py:AdminRateLimitConfig.rate_limit.create_per_minute` |
| `LEX_ADMIN__RATE_LIMIT__DELETE_PER_MINUTE` | int | 20 |  | `lexigram-admin/src/lexigram/admin/config.py:AdminRateLimitConfig.rate_limit.delete_per_minute` |
| `LEX_ADMIN__RATE_LIMIT__ENABLED` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:AdminRateLimitConfig.rate_limit.enabled` |
| `LEX_ADMIN__RATE_LIMIT__REQUESTS_PER_HOUR` | int | 1000 |  | `lexigram-admin/src/lexigram/admin/config.py:AdminRateLimitConfig.rate_limit.requests_per_hour` |
| `LEX_ADMIN__RATE_LIMIT__REQUESTS_PER_MINUTE` | int | 60 |  | `lexigram-admin/src/lexigram/admin/config.py:AdminRateLimitConfig.rate_limit.requests_per_minute` |
| `LEX_ADMIN__RATE_LIMIT__UPDATE_PER_MINUTE` | int | 60 |  | `lexigram-admin/src/lexigram/admin/config.py:AdminRateLimitConfig.rate_limit.update_per_minute` |
| `LEX_ADMIN__RBAC__SUPER_ADMIN_ROLE` | str | "superadmin" |  | `lexigram-admin/src/lexigram/admin/config.py:AdminRbacConfig.rbac.super_admin_role` |
| `LEX_ADMIN__REQUIRE_AUTH` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:AdminConfig.require_auth` |
| `LEX_ADMIN__RESOURCES` | dict[str, ResourceYAMLConfig] | (required) |  | `lexigram-admin/src/lexigram/admin/config.py:AdminConfig.resources` |
| `LEX_ADMIN__RESOURCE_DEFAULTS__ACTION_LAYOUT` | Literal['horizontal', 'vertical', 'dropdown'] | "horizontal" |  | `lexigram-admin/src/lexigram/admin/config.py:ResourceDefaults.resource_defaults.action_layout` |
| `LEX_ADMIN__RESOURCE_DEFAULTS__ENABLE_BULK_ACTIONS` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:ResourceDefaults.resource_defaults.enable_bulk_actions` |
| `LEX_ADMIN__RESOURCE_DEFAULTS__ENABLE_EXPORT` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:ResourceDefaults.resource_defaults.enable_export` |
| `LEX_ADMIN__RESOURCE_DEFAULTS__ENABLE_SEARCH` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:ResourceDefaults.resource_defaults.enable_search` |
| `LEX_ADMIN__RESOURCE_DEFAULTS__PER_PAGE` | int | 20 |  | `lexigram-admin/src/lexigram/admin/config.py:ResourceDefaults.resource_defaults.per_page` |
| `LEX_ADMIN__RESOURCE_DEFAULTS__SOFT_DELETE` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:ResourceDefaults.resource_defaults.soft_delete` |
| `LEX_ADMIN__RESOURCE_DEFAULTS__TIMESTAMP_FIELDS` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:ResourceDefaults.resource_defaults.timestamp_fields` |
| `LEX_ADMIN__STATIC_DIR` | str  \| None | None |  | `lexigram-admin/src/lexigram/admin/config.py:AdminConfig.static_dir` |
| `LEX_ADMIN__STATIC_PREFIX` | str | "/admin/static" |  | `lexigram-admin/src/lexigram/admin/config.py:AdminConfig.static_prefix` |
| `LEX_ADMIN__STRICT_RESOURCE_RESOLUTION` | bool | True | When True (production default), resource/controller resolution failures during AdminProvider.boot() raise immediately. W | `lexigram-admin/src/lexigram/admin/config.py:AdminConfig.strict_resource_resolution` |
| `LEX_ADMIN__TABLE_DEFAULTS__ENABLE_COLUMN_VISIBILITY` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:TableDefaults.table_defaults.enable_column_visibility` |
| `LEX_ADMIN__TABLE_DEFAULTS__HOVER_HIGHLIGHT` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:TableDefaults.table_defaults.hover_highlight` |
| `LEX_ADMIN__TABLE_DEFAULTS__REORDERABLE_COLUMNS` | bool | False |  | `lexigram-admin/src/lexigram/admin/config.py:TableDefaults.table_defaults.reorderable_columns` |
| `LEX_ADMIN__TABLE_DEFAULTS__ROW_HEIGHT` | int | 48 |  | `lexigram-admin/src/lexigram/admin/config.py:TableDefaults.table_defaults.row_height` |
| `LEX_ADMIN__TABLE_DEFAULTS__STICKY_HEADER` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:TableDefaults.table_defaults.sticky_header` |
| `LEX_ADMIN__TABLE_DEFAULTS__VIRTUALIZED` | bool | False |  | `lexigram-admin/src/lexigram/admin/config.py:TableDefaults.table_defaults.virtualized` |
| `LEX_ADMIN__TABLE_DEFAULTS__ZEBRA_STRIPES` | bool | True |  | `lexigram-admin/src/lexigram/admin/config.py:TableDefaults.table_defaults.zebra_stripes` |
| `LEX_ADMIN__TEMPLATES_DIR` | str  \| None | None |  | `lexigram-admin/src/lexigram/admin/config.py:AdminConfig.templates_dir` |
| `LEX_ADMIN__TENANCY__COOKIE_NAME` | str | "admin_tenant" |  | `lexigram-admin/src/lexigram/admin/config.py:TenancyConfig.tenancy.cookie_name` |
| `LEX_ADMIN__TENANCY__DEFAULT_TENANT_ID` | str | "" |  | `lexigram-admin/src/lexigram/admin/config.py:TenancyConfig.tenancy.default_tenant_id` |
| `LEX_ADMIN__TENANCY__ENABLED` | bool | False |  | `lexigram-admin/src/lexigram/admin/config.py:TenancyConfig.tenancy.enabled` |
| `LEX_ADMIN__TENANCY__HEADER_NAME` | str | "x-tenant-id" |  | `lexigram-admin/src/lexigram/admin/config.py:TenancyConfig.tenancy.header_name` |
| `LEX_ADMIN__TENANCY__ROUTE_PREFIX_TEMPLATE` | str | "" |  | `lexigram-admin/src/lexigram/admin/config.py:TenancyConfig.tenancy.route_prefix_template` |
| `LEX_ADMIN__TENANCY__TENANT_FIELD` | str | "tenant_id" |  | `lexigram-admin/src/lexigram/admin/config.py:TenancyConfig.tenancy.tenant_field` |
| `LEX_ADMIN__TITLE` | str | "Lexigram Admin" |  | `lexigram-admin/src/lexigram/admin/config.py:AdminConfig.title` |
| `LEX_ADMIN__UI__CONTENT_MAX_WIDTH` | int  \| None | None |  | `lexigram-admin/src/lexigram/admin/config.py:AdminUIConfig.ui.content_max_width` |
| `LEX_ADMIN__UI__FAVICON_URL` | str  \| None | None |  | `lexigram-admin/src/lexigram/admin/config.py:AdminUIConfig.ui.favicon_url` |
| `LEX_ADMIN__UI__LOGO_URL` | str  \| None | None |  | `lexigram-admin/src/lexigram/admin/config.py:AdminUIConfig.ui.logo_url` |
| `LEX_ADMIN__UI__PRIMARY_COLOR` | str | "#6B7280" |  | `lexigram-admin/src/lexigram/admin/config.py:AdminUIConfig.ui.primary_color` |
| `LEX_ADMIN__UI__SIDEBAR_COLLAPSED_WIDTH` | int | 64 |  | `lexigram-admin/src/lexigram/admin/config.py:AdminUIConfig.ui.sidebar_collapsed_width` |
| `LEX_ADMIN__UI__SIDEBAR_WIDTH` | int | 256 |  | `lexigram-admin/src/lexigram/admin/config.py:AdminUIConfig.ui.sidebar_width` |
| `LEX_ADMIN__UI__THEME` | Literal['light', 'dark', 'system'] | "system" |  | `lexigram-admin/src/lexigram/admin/config.py:AdminUIConfig.ui.theme` |

### `lexigram-ai`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_AI__ENABLED` | bool | True | Enable AI features | `lexigram-ai/src/lexigram/ai/config.py:AIConfig.enabled` |
| `LEX_AI__GOVERNANCE` | Any | (required) | AI governance configuration | `lexigram-ai/src/lexigram/ai/config.py:AIConfig.governance` |
| `LEX_AI__LLM` | Any  \| None | None | LLM configuration (optional) | `lexigram-ai/src/lexigram/ai/config.py:AIConfig.llm` |
| `LEX_AI__NAME` | str | "ai" | Configuration name | `lexigram-ai/src/lexigram/ai/config.py:AIConfig.name` |
| `LEX_AI__OBSERVABILITY` | Any | (required) | AI observability configuration (tracing and metrics) | `lexigram-ai/src/lexigram/ai/config.py:AIConfig.observability` |
| `LEX_AI__RAG` | Any  \| None | None | RAG pipeline configuration (optional) | `lexigram-ai/src/lexigram/ai/config.py:AIConfig.rag` |
| `LEX_AI__SUBSYSTEMS` | dict[str, dict[str, Any]] | (required) | Dynamic configuration for third-party AI subsystems discovered via entry points.  Keys are subsystem names; values are t | `lexigram-ai/src/lexigram/ai/config.py:AIConfig.subsystems` |
| `LEX_AI__VECTOR` | Any  \| None | None | Vector store configuration | `lexigram-ai/src/lexigram/ai/config.py:AIConfig.vector` |

### `lexigram-ai-agents`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_AI_AGENTS__DEFAULT_MAX_TOKENS` | int | 2048 | Default max tokens for LLM responses | `lexigram-ai-agents/src/lexigram/ai/agents/config.py:AgentConfig.default_max_tokens` |
| `LEX_AI_AGENTS__DEFAULT_TEMPERATURE` | float | 0.7 | Default temperature for LLM calls | `lexigram-ai-agents/src/lexigram/ai/agents/config.py:AgentConfig.default_temperature` |
| `LEX_AI_AGENTS__ENABLED` | bool | True | Enable the AI agents subsystem | `lexigram-ai-agents/src/lexigram/ai/agents/config.py:AgentConfig.enabled` |
| `LEX_AI_AGENTS__ENABLE_METRICS` | bool | True | Enable Prometheus metrics | `lexigram-ai-agents/src/lexigram/ai/agents/config.py:AgentConfig.enable_metrics` |
| `LEX_AI_AGENTS__ENABLE_TRACING` | bool | True | Enable OpenTelemetry tracing | `lexigram-ai-agents/src/lexigram/ai/agents/config.py:AgentConfig.enable_tracing` |
| `LEX_AI_AGENTS__MAX_ITERATIONS` | int | 10 | Maximum reasoning iterations per execution | `lexigram-ai-agents/src/lexigram/ai/agents/config.py:AgentConfig.max_iterations` |
| `LEX_AI_AGENTS__TOOL_MAX_RETRIES` | int | 3 | Number of retries for transient tool execution errors (ConnectionError, TimeoutError, OSError) | `lexigram-ai-agents/src/lexigram/ai/agents/config.py:AgentConfig.tool_max_retries` |

### `lexigram-ai-evaluation`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_AI_EVALUATION__DEFAULT_THRESHOLD` | float | 0.8 | Default score threshold for passing evaluations | `lexigram-ai-evaluation/src/lexigram/ai/evaluation/config.py:EvaluationConfig.default_threshold` |
| `LEX_AI_EVALUATION__EMBEDDING_MODEL` | str | "text-embedding-3-small" | Model to use for embedding-based evaluations | `lexigram-ai-evaluation/src/lexigram/ai/evaluation/config.py:EvaluationConfig.embedding_model` |
| `LEX_AI_EVALUATION__ENABLED` | bool | True | Enable the AI evaluation subsystem | `lexigram-ai-evaluation/src/lexigram/ai/evaluation/config.py:EvaluationConfig.enabled` |
| `LEX_AI_EVALUATION__INCLUDE_METADATA` | bool | True | Whether to include metadata in run reports | `lexigram-ai-evaluation/src/lexigram/ai/evaluation/config.py:EvaluationConfig.include_metadata` |
| `LEX_AI_EVALUATION__MAX_RETRIES` | int | 3 | Maximum retries for failed evaluations | `lexigram-ai-evaluation/src/lexigram/ai/evaluation/config.py:EvaluationConfig.max_retries` |
| `LEX_AI_EVALUATION__MAX_SAMPLES` | int  \| None | None | Maximum number of samples per evaluation run | `lexigram-ai-evaluation/src/lexigram/ai/evaluation/config.py:EvaluationConfig.max_samples` |
| `LEX_AI_EVALUATION__TIMEOUT_SECONDS` | int | 30 | Timeout for evaluation execution in seconds | `lexigram-ai-evaluation/src/lexigram/ai/evaluation/config.py:EvaluationConfig.timeout_seconds` |

### `lexigram-ai-feedback`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_AI_FEEDBACK__ASYNC_PROCESSING` | bool | True | Process feedback handlers asynchronously in the background | `lexigram-ai-feedback/src/lexigram/ai/feedback/config.py:FeedbackConfig.async_processing` |
| `LEX_AI_FEEDBACK__ENABLED` | bool | True | Master on/off switch for all feedback collection | `lexigram-ai-feedback/src/lexigram/ai/feedback/config.py:FeedbackConfig.enabled` |
| `LEX_AI_FEEDBACK__STORE_RAW_PAYLOADS` | bool | False | Persist raw incoming feedback payloads for auditing | `lexigram-ai-feedback/src/lexigram/ai/feedback/config.py:FeedbackConfig.store_raw_payloads` |

### `lexigram-ai-governance`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_AI_GOVERNANCE__ENABLED` | bool | True | Enable AI governance | `lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.enabled` |
| `LEX_AI_GOVERNANCE__ENFORCE_BUDGET` | bool | True | Enforce budget limits | `lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.enforce_budget` |
| `LEX_AI_GOVERNANCE__FAIL_OPEN_ON_PERSISTENCE_ERROR` | bool | False | Allow requests when the persistence backend is unavailable. When False (default, fail-closed), a persistence failure (e. | `lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.fail_open_on_persistenc` |
| `LEX_AI_GOVERNANCE__MAX_REQUEST_COST` | float  \| None | None | Maximum cost in dollars for a single request. Requests with an estimated cost above this threshold are rejected before t | `lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.max_request_cost` |
| `LEX_AI_GOVERNANCE__MAX_TOKENS_PER_REQUEST` | int  \| None | None | Max tokens per request | `lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.max_tokens_per_request` |
| `LEX_AI_GOVERNANCE__MODEL_ALLOWLIST` | dict[str, list[str]] | (required) | Per-user/role model allowlist. Keys are user IDs or role names; values are lists of allowed model patterns (supports glo | `lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.model_allowlist` |
| `LEX_AI_GOVERNANCE__MODEL_DENYLIST` | dict[str, list[str]] | (required) | Per-user/role model denylist. Keys are user IDs or role names; values are lists of denied model patterns (supports glob  | `lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.model_denylist` |
| `LEX_AI_GOVERNANCE__MONTHLY_BUDGET` | float  \| None | None | Monthly budget in dollars | `lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.monthly_budget` |
| `LEX_AI_GOVERNANCE__RESOURCE_UNITS` | list | (required) | Resource units this governance instance tracks. Per-tenant limits are configured via TenantConfigService overrides. | `lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.resource_units` |
| `LEX_AI_GOVERNANCE__RESTRICTED_MODELS` | list[str] | (required) | List of restricted models | `lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.restricted_models` |
| `LEX_AI_GOVERNANCE__RPM_LIMIT` | int  \| None | None | Requests Per Minute limit | `lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.rpm_limit` |
| `LEX_AI_GOVERNANCE__SOFT_LIMIT_PCT` | float  \| None | None | Fraction of monthly_budget at which to emit a soft-limit warning (e.g. 0.8 = warn at 80%). No hard block is applied at t | `lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.soft_limit_pct` |
| `LEX_AI_GOVERNANCE__TPM_LIMIT` | int  \| None | None | Tokens Per Minute limit | `lexigram-ai-governance/src/lexigram/ai/governance/config.py:GovernanceConfig.tpm_limit` |

### `lexigram-ai-guard`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_AI_GUARD__ENABLED` | bool | True |  | `lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.enabled` |
| `LEX_AI_GUARD__ENABLE_LLM_GUARDS` | bool | False |  | `lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.enable_llm_guards` |
| `LEX_AI_GUARD__GUARD_MODEL` | str | "gpt-4o-mini" |  | `lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.guard_model` |
| `LEX_AI_GUARD__INJECTION_ACTION` | str | "block" |  | `lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.injection_action` |
| `LEX_AI_GUARD__INJECTION_DETECTION` | bool | True |  | `lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.injection_detection` |
| `LEX_AI_GUARD__LENGTH_ACTION` | str | "block" |  | `lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.length_action` |
| `LEX_AI_GUARD__LLM_GUARD_FAIL_OPEN` | bool | False |  | `lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.llm_guard_fail_open` |
| `LEX_AI_GUARD__LLM_GUARD_THRESHOLD` | float | 0.7 |  | `lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.llm_guard_threshold` |
| `LEX_AI_GUARD__MAX_INPUT_CHARS` | int | 0 |  | `lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.max_input_chars` |
| `LEX_AI_GUARD__MAX_OUTPUT_CHARS` | int | 0 |  | `lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.max_output_chars` |
| `LEX_AI_GUARD__PARALLEL_EXECUTION` | bool | False |  | `lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.parallel_execution` |
| `LEX_AI_GUARD__PII_ACTION` | str | "redact" |  | `lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.pii_action` |
| `LEX_AI_GUARD__PII_DETECTION` | bool | True |  | `lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.pii_detection` |
| `LEX_AI_GUARD__PII_ENTITIES` | list[str] | field(...) |  | `lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.pii_entities` |
| `LEX_AI_GUARD__PII_REDACTION_OUTPUT` | bool | True |  | `lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.pii_redaction_output` |
| `LEX_AI_GUARD__RESTRICTED_TOPICS` | list[str] | field(...) |  | `lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.restricted_topics` |
| `LEX_AI_GUARD__SENSITIVITY_LEVEL` | str | "medium" |  | `lexigram-ai-guard/src/lexigram/ai/guard/config.py:GuardConfig.sensitivity_level` |

### `lexigram-ai-mcp`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_AI_MCP__ALLOW_UNAUTHENTICATED` | bool | False |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.allow_unauthenticated` |
| `LEX_AI_MCP__CLIENT_STDIO_COMMAND` | list[str] | field(...) |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.client_stdio_command` |
| `LEX_AI_MCP__CLIENT_URL` | str  \| None | None |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.client_url` |
| `LEX_AI_MCP__CONNECTORS__FILESYSTEM__READ_ONLY` | bool | False |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:FilesystemConnectorConfig.connectors.filesystem.read_o` |
| `LEX_AI_MCP__CONNECTORS__FILESYSTEM__ROOT_DIR` | str | "" |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:FilesystemConnectorConfig.connectors.filesystem.root_d` |
| `LEX_AI_MCP__CONNECTORS__GITHUB__API_URL` | str | "https://api.github.com" |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:GitHubConnectorConfig.connectors.github.api_url` |
| `LEX_AI_MCP__CONNECTORS__GITHUB__TOKEN` | str | "" |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:GitHubConnectorConfig.connectors.github.token` |
| `LEX_AI_MCP__CONNECTORS__GOOGLE_DRIVE__IMPERSONATED_EMAIL` | str | "" |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:GoogleDriveConnectorConfig.connectors.google_drive.imp` |
| `LEX_AI_MCP__CONNECTORS__GOOGLE_DRIVE__SERVICE_ACCOUNT_JSON` | str | "" |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:GoogleDriveConnectorConfig.connectors.google_drive.ser` |
| `LEX_AI_MCP__CONNECTORS__SLACK__BOT_TOKEN` | str | "" |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:SlackConnectorConfig.connectors.slack.bot_token` |
| `LEX_AI_MCP__CONNECTORS__SLACK__MAX_MESSAGES` | int | 100 |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:SlackConnectorConfig.connectors.slack.max_messages` |
| `LEX_AI_MCP__CONNECTORS__SQL__ALLOWED_TABLES` | list[str] | field(...) |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:SQLConnectorConfig.connectors.sql.allowed_tables` |
| `LEX_AI_MCP__CONNECTORS__SQL__DSN` | str | "" |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:SQLConnectorConfig.connectors.sql.dsn` |
| `LEX_AI_MCP__CONNECTORS__SQL__READ_ONLY` | bool | True |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:SQLConnectorConfig.connectors.sql.read_only` |
| `LEX_AI_MCP__CONNECTORS__WEB_FETCH__ENABLED` | bool | False |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:WebFetchConnectorConfig.connectors.web_fetch.enabled` |
| `LEX_AI_MCP__CONNECTORS__WEB_FETCH__MAX_CONTENT_BYTES` | int | (complex) |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:WebFetchConnectorConfig.connectors.web_fetch.max_conte` |
| `LEX_AI_MCP__CONNECTORS__WEB_FETCH__USER_AGENT` | str | "lexigram-mcp/1.0" |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:WebFetchConnectorConfig.connectors.web_fetch.user_agen` |
| `LEX_AI_MCP__CONNECTORS__WEB_SEARCH__API_KEY` | str | "" |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:WebSearchConnectorConfig.connectors.web_search.api_key` |
| `LEX_AI_MCP__CONNECTORS__WEB_SEARCH__MAX_RESULTS` | int | 10 |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:WebSearchConnectorConfig.connectors.web_search.max_res` |
| `LEX_AI_MCP__CONNECTORS__WEB_SEARCH__PROVIDER` | str | "brave" |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:WebSearchConnectorConfig.connectors.web_search.provide` |
| `LEX_AI_MCP__CORS_ORIGINS` | list[str] | field(...) |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.cors_origins` |
| `LEX_AI_MCP__ENABLED` | bool | True | Enable the MCP server subsystem | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.enabled` |
| `LEX_AI_MCP__ENABLE_SSE` | bool | True |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.enable_sse` |
| `LEX_AI_MCP__HOST` | str | "0.0.0.0" |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.host` |
| `LEX_AI_MCP__MAX_REQUEST_SIZE` | int | (complex) |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.max_request_size` |
| `LEX_AI_MCP__PATH` | str | "/mcp" |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.path` |
| `LEX_AI_MCP__PORT` | int | 8080 |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.port` |
| `LEX_AI_MCP__REQUEST_TIMEOUT` | float | 30.0 |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.request_timeout` |
| `LEX_AI_MCP__SERVER_NAME` | str | "lexigram-mcp" |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.server_name` |
| `LEX_AI_MCP__SERVER_VERSION` | str | "1.0.0" |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.server_version` |
| `LEX_AI_MCP__STDIO_MODE` | bool | False |  | `lexigram-ai-mcp/src/lexigram/ai/mcp/config.py:MCPConfig.stdio_mode` |

### `lexigram-ai-memory`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_AI_MEMORY__CONSOLIDATION__AGE_THRESHOLD_HOURS` | float | (complex) | Minimum entry age (hours) before it can be consolidated | `lexigram-ai-memory/src/lexigram/ai/memory/config.py:ConsolidationConfig.consolidation.age_threshold_` |
| `LEX_AI_MEMORY__CONSOLIDATION__BATCH_SIZE` | int | (complex) | Maximum entries processed per consolidation pass | `lexigram-ai-memory/src/lexigram/ai/memory/config.py:ConsolidationConfig.consolidation.batch_size` |
| `LEX_AI_MEMORY__CONSOLIDATION__ENABLED` | bool | True | Whether automatic background consolidation is active | `lexigram-ai-memory/src/lexigram/ai/memory/config.py:ConsolidationConfig.consolidation.enabled` |
| `LEX_AI_MEMORY__CONSOLIDATION__IMPORTANCE_PRUNE_THRESHOLD` | float | (complex) | Entries below this importance score are eligible for pruning | `lexigram-ai-memory/src/lexigram/ai/memory/config.py:ConsolidationConfig.consolidation.importance_pru` |
| `LEX_AI_MEMORY__CONSOLIDATION__INTERVAL_SECONDS` | float | (complex) | How often to run a consolidation pass (seconds) | `lexigram-ai-memory/src/lexigram/ai/memory/config.py:ConsolidationConfig.consolidation.interval_secon` |
| `LEX_AI_MEMORY__DEFAULT_BACKEND` | str | (complex) | Backend type to use ('in_memory', 'cache', 'database', 'vector') | `lexigram-ai-memory/src/lexigram/ai/memory/config.py:MemoryConfig.default_backend` |
| `LEX_AI_MEMORY__ENABLED` | bool | True | Enable the AI memory subsystem | `lexigram-ai-memory/src/lexigram/ai/memory/config.py:MemoryConfig.enabled` |
| `LEX_AI_MEMORY__EPISODIC__DEFAULT_TOP_K` | int | (complex) | Default number of episodes to retrieve | `lexigram-ai-memory/src/lexigram/ai/memory/config.py:EpisodicMemoryConfig.episodic.default_top_k` |
| `LEX_AI_MEMORY__EPISODIC__IMPORTANCE_WEIGHT` | float | (complex) | Weight applied to entry importance during scoring | `lexigram-ai-memory/src/lexigram/ai/memory/config.py:EpisodicMemoryConfig.episodic.importance_weight` |
| `LEX_AI_MEMORY__EPISODIC__RECENCY_WEIGHT` | float | (complex) | Weight applied to temporal recency during scoring | `lexigram-ai-memory/src/lexigram/ai/memory/config.py:EpisodicMemoryConfig.episodic.recency_weight` |
| `LEX_AI_MEMORY__EPISODIC__RELEVANCE_WEIGHT` | float | (complex) | Weight applied to semantic similarity during scoring | `lexigram-ai-memory/src/lexigram/ai/memory/config.py:EpisodicMemoryConfig.episodic.relevance_weight` |
| `LEX_AI_MEMORY__EPISODIC__TTL_SECONDS` | int | (complex) | Time-to-live for entries in seconds (0 = never expire) | `lexigram-ai-memory/src/lexigram/ai/memory/config.py:EpisodicMemoryConfig.episodic.ttl_seconds` |
| `LEX_AI_MEMORY__SEMANTIC__MAX_FACTS_PER_ENTITY` | int | (complex) | Hard cap on stored facts per entity | `lexigram-ai-memory/src/lexigram/ai/memory/config.py:SemanticMemoryConfig.semantic.max_facts_per_enti` |
| `LEX_AI_MEMORY__SEMANTIC__MIN_CONFIDENCE` | float | (complex) | Minimum confidence score required to store a fact | `lexigram-ai-memory/src/lexigram/ai/memory/config.py:SemanticMemoryConfig.semantic.min_confidence` |
| `LEX_AI_MEMORY__TTL_SECONDS` | int | (complex) | Default entry TTL in seconds (0 = never expire) | `lexigram-ai-memory/src/lexigram/ai/memory/config.py:MemoryConfig.ttl_seconds` |
| `LEX_AI_MEMORY__WORKING__EPISODIC_FRACTION` | float | (complex) | Fraction of remaining budget for episodic recall | `lexigram-ai-memory/src/lexigram/ai/memory/config.py:WorkingMemoryConfig.working.episodic_fraction` |
| `LEX_AI_MEMORY__WORKING__MAX_RECENT_TURNS` | int | (complex) | Hard cap on recent turns regardless of budget | `lexigram-ai-memory/src/lexigram/ai/memory/config.py:WorkingMemoryConfig.working.max_recent_turns` |
| `LEX_AI_MEMORY__WORKING__RECENT_TURNS_FRACTION` | float | (complex) | Fraction of remaining budget for recent turns | `lexigram-ai-memory/src/lexigram/ai/memory/config.py:WorkingMemoryConfig.working.recent_turns_fractio` |
| `LEX_AI_MEMORY__WORKING__SEMANTIC_FRACTION` | float | (complex) | Fraction of remaining budget for semantic facts | `lexigram-ai-memory/src/lexigram/ai/memory/config.py:WorkingMemoryConfig.working.semantic_fraction` |
| `LEX_AI_MEMORY__WORKING__SYSTEM_PROMPT_TOKENS` | int | (complex) | Fixed token allocation for system prompt | `lexigram-ai-memory/src/lexigram/ai/memory/config.py:WorkingMemoryConfig.working.system_prompt_tokens` |
| `LEX_AI_MEMORY__WORKING__TOOL_DESCRIPTIONS_FRACTION` | float | (complex) | Fraction of remaining budget for tool descriptions | `lexigram-ai-memory/src/lexigram/ai/memory/config.py:WorkingMemoryConfig.working.tool_descriptions_fr` |

### `lexigram-ai-observability`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_AI_OBSERVABILITY__ENABLED` | bool | True | Master on/off switch for all observability | `lexigram-ai-observability/src/lexigram/ai/observability/config.py:ObservabilityConfig.enabled` |
| `LEX_AI_OBSERVABILITY__HEALTH_CHECKS_ENABLED` | bool | True | Enable background health checking for AI components | `lexigram-ai-observability/src/lexigram/ai/observability/config.py:ObservabilityConfig.health_checks_` |
| `LEX_AI_OBSERVABILITY__METRICS_ENABLED` | bool | True | Enable metrics collection | `lexigram-ai-observability/src/lexigram/ai/observability/config.py:ObservabilityConfig.metrics_enable` |
| `LEX_AI_OBSERVABILITY__TRACE_MAX_ATTRIBUTE_LENGTH` | int | 0 | Cap on string attribute values written to trace spans, in characters. 0 disables the cap. | `lexigram-ai-observability/src/lexigram/ai/observability/config.py:ObservabilityConfig.trace_max_attr` |
| `LEX_AI_OBSERVABILITY__TRACE_REDACTION_ENABLED` | bool | False | Redact secret-shaped keys (e.g. token, password, api_key) from trace span attributes and audit metadata. Strongly recomm | `lexigram-ai-observability/src/lexigram/ai/observability/config.py:ObservabilityConfig.trace_redactio` |
| `LEX_AI_OBSERVABILITY__TRACING_ENABLED` | bool | True | Enable distributed tracing | `lexigram-ai-observability/src/lexigram/ai/observability/config.py:ObservabilityConfig.tracing_enable` |

### `lexigram-ai-prompt`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_AI_PROMPT__DEFAULT_FORMAT` | RenderFormat | DEFAULT_RENDER_FORMAT |  | `lexigram-ai-prompt/src/lexigram/ai/prompt/config.py:PromptConfig.default_format` |
| `LEX_AI_PROMPT__ENABLED` | bool | True | Enable the AI prompt subsystem | `lexigram-ai-prompt/src/lexigram/ai/prompt/config.py:PromptConfig.enabled` |
| `LEX_AI_PROMPT__MAX_VARIABLE_LENGTH` | int | 0 |  | `lexigram-ai-prompt/src/lexigram/ai/prompt/config.py:PromptConfig.max_variable_length` |
| `LEX_AI_PROMPT__SANITIZE_INPUTS` | bool | True |  | `lexigram-ai-prompt/src/lexigram/ai/prompt/config.py:PromptConfig.sanitize_inputs` |
| `LEX_AI_PROMPT__STRICT_SANITIZER` | bool | True |  | `lexigram-ai-prompt/src/lexigram/ai/prompt/config.py:PromptConfig.strict_sanitizer` |

### `lexigram-ai-rag`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_AI_RAG__CACHE_TTL` | int | 3600 | Cache TTL in seconds (default: 1 hour) | `lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.cache_ttl` |
| `LEX_AI_RAG__CHUNKING_STRATEGY` | str | "recursive" | Chunking strategy (recursive, semantic, token) | `lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.chunking_strategy` |
| `LEX_AI_RAG__CHUNK_OVERLAP` | int | 50 | Overlap between consecutive chunks | `lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.chunk_overlap` |
| `LEX_AI_RAG__CHUNK_SIZE` | int | 512 | Text chunk size in tokens | `lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.chunk_size` |
| `LEX_AI_RAG__CITATION_STYLE` | str | "inline" | Citation style (inline, footnote, numbered) | `lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.citation_style` |
| `LEX_AI_RAG__COLLECTION_NAME` | str | "default" | Collection/index name for vector store | `lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.collection_name` |
| `LEX_AI_RAG__EMBEDDING_MODEL` | str  \| None | None | Embedding model identifier. Must be set explicitly — no vendor-specific default. | `lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.embedding_model` |
| `LEX_AI_RAG__EMBEDDING_PROVIDER` | str | "openai" | Embedding provider (openai, cohere, etc.) | `lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.embedding_provider` |
| `LEX_AI_RAG__ENABLED` | bool | True | Enable the RAG pipeline | `lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.enabled` |
| `LEX_AI_RAG__ENABLE_CACHING` | bool | True | Enable caching for RAG queries | `lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.enable_caching` |
| `LEX_AI_RAG__ENABLE_CITATIONS` | bool | True | Include source citations in responses | `lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.enable_citations` |
| `LEX_AI_RAG__ENABLE_HALLUCINATION_DETECTION` | bool | True | Enable hallucination detection for AI responses | `lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.enable_hallucination_detection` |
| `LEX_AI_RAG__ENABLE_HYDE` | bool | False | Enable HyDE (Hypothetical Document Embeddings) | `lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.enable_hyde` |
| `LEX_AI_RAG__ENABLE_QUERY_EXPANSION` | bool | True | Enable query expansion techniques | `lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.enable_query_expansion` |
| `LEX_AI_RAG__MIN_CITATION_CONFIDENCE` | float | 0.6 | Minimum confidence for citation inclusion | `lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.min_citation_confidence` |
| `LEX_AI_RAG__PERSIST_DIRECTORY` | str  \| None | None | Local directory path for vector store persistence (e.g. Chroma) | `lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.persist_directory` |
| `LEX_AI_RAG__SIMILARITY_THRESHOLD` | float | 0.7 | Minimum similarity score threshold | `lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.similarity_threshold` |
| `LEX_AI_RAG__SYNTHESIS_STRATEGY` | str | "hybrid" | Synthesis strategy (direct, extractive, abstractive, hybrid) | `lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.synthesis_strategy` |
| `LEX_AI_RAG__TENANCY__ENABLED` | bool | False | Enable tenant-aware collection resolution in RAG pipeline | `lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGTenancyConfig.tenancy.enabled` |
| `LEX_AI_RAG__TOP_K` | int | 5 | Number of documents to retrieve | `lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.top_k` |
| `LEX_AI_RAG__USE_HYBRID_SEARCH` | bool | True | Enable hybrid search (semantic + keyword) | `lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.use_hybrid_search` |
| `LEX_AI_RAG__VECTOR_DIMENSION` | int | 1536 | Embedding vector dimension (1536 for OpenAI ada-002) | `lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.vector_dimension` |
| `LEX_AI_RAG__VECTOR_STORE_TYPE` | str | "pgvector" | Vector store backend (pgvector, chroma, qdrant, mock) | `lexigram-ai-rag/src/lexigram/ai/rag/config.py:RAGConfig.vector_store_type` |

### `lexigram-ai-session`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_AI_SESSION__AUTO_CHECKPOINT_INTERVAL` | int  \| None | (complex) | Checkpoint every N turns; None to disable | `lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.auto_checkpoint_interval` |
| `LEX_AI_SESSION__BACKEND` | str | (complex) | Persistence backend (in_memory, cache, database) | `lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.backend` |
| `LEX_AI_SESSION__CLEANUP_INTERVAL_S` | int | (complex) | How often the cleanup scheduler sweeps for expired sessions | `lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.cleanup_interval_s` |
| `LEX_AI_SESSION__CONSOLIDATE_ON_CLOSE` | bool | (complex) | Whether to trigger memory consolidation on session close | `lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.consolidate_on_close` |
| `LEX_AI_SESSION__COOKIE_NAME` | str  \| None | (complex) | Cookie name for web session ID; None disables cookies | `lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.cookie_name` |
| `LEX_AI_SESSION__DEFAULT_SYSTEM_PROMPT` | str  \| None | None | System prompt injected into every new session | `lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.default_system_prompt` |
| `LEX_AI_SESSION__DEFAULT_TURN_STRATEGY` | str | (complex) | Default turn-selection strategy (round_robin, priority, llm_directed) | `lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.default_turn_strategy` |
| `LEX_AI_SESSION__ENABLED` | bool | True | Enable the AI session subsystem | `lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.enabled` |
| `LEX_AI_SESSION__HEADER_NAME` | str | (complex) | HTTP header name for session ID pass-through | `lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.header_name` |
| `LEX_AI_SESSION__MAX_AGENTS_PER_GROUP` | int | (complex) | Maximum agents in a multi-agent group session | `lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.max_agents_per_group` |
| `LEX_AI_SESSION__MAX_BRANCHES_PER_SESSION` | int | (complex) | Maximum forked branches per session | `lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.max_branches_per_session` |
| `LEX_AI_SESSION__MAX_CHECKPOINTS_PER_SESSION` | int | (complex) | Maximum retained checkpoints per session | `lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.max_checkpoints_per_session` |
| `LEX_AI_SESSION__MAX_SESSIONS_PER_USER` | int | (complex) | Maximum concurrent sessions per user | `lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.max_sessions_per_user` |
| `LEX_AI_SESSION__MAX_TURNS_PER_SESSION` | int | (complex) | Hard cap on turns before the session is closed | `lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.max_turns_per_session` |
| `LEX_AI_SESSION__NAME` | str | "ai-session" | Logical name used for DI registration keys | `lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.name` |
| `LEX_AI_SESSION__SESSION_TTL` | int | (complex) | Maximum age of a session in seconds (0 to disable) | `lexigram-ai-session/src/lexigram/ai/session/config.py:SessionConfig.session_ttl` |

### `lexigram-ai-skills`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_AI_SKILLS__ALLOWED_SCRIPT_TYPES` | list[str] | (required) | Allowed script types (py, sh, js) | `lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.allowed_script_types` |
| `LEX_AI_SKILLS__AUTO_DISCOVER` | bool | (complex) | Whether to auto-scan packages for skills on boot | `lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.auto_discover` |
| `LEX_AI_SKILLS__BUILTIN_SKILLS` | list[str] | (required) | Names of built-in skills to register | `lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.builtin_skills` |
| `LEX_AI_SKILLS__CACHE_BACKEND` | str | (complex) | Which cache backend to use (in_memory, cache) | `lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.cache_backend` |
| `LEX_AI_SKILLS__CACHE_ENABLED` | bool | (complex) | Whether result caching is globally enabled | `lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.cache_enabled` |
| `LEX_AI_SKILLS__CACHE_TTL_SECONDS` | int | (complex) | Default TTL for cached skill results (seconds) | `lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.cache_ttl_seconds` |
| `LEX_AI_SKILLS__DEFAULT_TIMEOUT_SECONDS` | float | (complex) | Default execution timeout per skill (seconds) | `lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.default_timeout_seconds` |
| `LEX_AI_SKILLS__ENABLED_DIRECTORIES` | list[str] | (required) | Which skill directories to enable (claude_code, opencode, cursor, etc.) | `lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.enabled_directories` |
| `LEX_AI_SKILLS__ENABLE_BUILTIN` | bool | (complex) | Whether built-in skills are registered on boot | `lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.enable_builtin` |
| `LEX_AI_SKILLS__ENABLE_SKILL_SOURCES` | bool | True | Whether to scan for external skill sources on boot | `lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.enable_skill_sources` |
| `LEX_AI_SKILLS__ENFORCE_PERMISSIONS` | bool | (complex) | Whether permission checks are enforced | `lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.enforce_permissions` |
| `LEX_AI_SKILLS__LAZY_LOAD_CONTEXT` | bool | (complex) | Whether to lazily load skill context files | `lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.lazy_load_context` |
| `LEX_AI_SKILLS__MAX_CONCURRENT_EXECUTIONS` | int | (complex) | Semaphore cap on concurrent skill executions | `lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.max_concurrent_executions` |
| `LEX_AI_SKILLS__MAX_RETRIES` | int | (complex) | Default maximum retry attempts for skill execution | `lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.max_retries` |
| `LEX_AI_SKILLS__NAME` | str | "ai-skills" | Logical name used for DI registration keys | `lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.name` |
| `LEX_AI_SKILLS__SCAN_PACKAGES` | list[str] | (required) | Fully-qualified package names to scan for skills | `lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.scan_packages` |
| `LEX_AI_SKILLS__SCRIPT_TIMEOUT_SECONDS` | int | (complex) | Timeout for skill script execution (seconds) | `lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.script_timeout_seconds` |
| `LEX_AI_SKILLS__SKILL_PATHS` | list[str] | (required) | Paths to scan for skills (SKILL.md folders) | `lexigram-ai-skills/src/lexigram/ai/skills/config.py:SkillsConfig.skill_paths` |

### `lexigram-ai-workers`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_AI_WORKERS__BATCH_EMBEDDING_CONCURRENCY` | int | 3 | Concurrency level for batch embedding execution | `lexigram-ai-workers/src/lexigram/ai/workers/config.py:WorkersConfig.batch_embedding_concurrency` |
| `LEX_AI_WORKERS__DLQ_CHECK_INTERVAL` | int | 60 | Interval in seconds for DLQ recovery sweeps | `lexigram-ai-workers/src/lexigram/ai/workers/config.py:WorkersConfig.dlq_check_interval` |
| `LEX_AI_WORKERS__DOCUMENT_INGESTION_CONCURRENCY` | int | 3 | Concurrency level for document parsing and chunking | `lexigram-ai-workers/src/lexigram/ai/workers/config.py:WorkersConfig.document_ingestion_concurrency` |
| `LEX_AI_WORKERS__ENABLED` | bool | True | Master on/off switch for all background workers | `lexigram-ai-workers/src/lexigram/ai/workers/config.py:WorkersConfig.enabled` |
| `LEX_AI_WORKERS__ENABLE_MAINTENANCE` | bool | True | Enable vector store and cache maintenance tasks | `lexigram-ai-workers/src/lexigram/ai/workers/config.py:WorkersConfig.enable_maintenance` |

### `lexigram-audit`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_AUDIT__ENABLE_ADMIN` | bool | True | Whether to register the AuditAdminContributor | `lexigram-audit/src/lexigram/audit/config.py:AuditConfig.enable_admin` |
| `LEX_AUDIT__HMAC_KEY` | bytes  \| None | None | HMAC key for checksum computation | `lexigram-audit/src/lexigram/audit/config.py:AuditConfig.hmac_key` |
| `LEX_AUDIT__RETENTION_POLICY` | RetentionPolicy | (required) | Retention rules | `lexigram-audit/src/lexigram/audit/config.py:AuditConfig.retention_policy` |
| `LEX_AUDIT__STORE_BACKEND` | str | (complex) | Backend type — 'sql' or 'memory' | `lexigram-audit/src/lexigram/audit/config.py:AuditConfig.store_backend` |
| `LEX_AUDIT__TABLE_NAME` | str | (complex) | SQL table name for the unified audit store | `lexigram-audit/src/lexigram/audit/config.py:AuditConfig.table_name` |
| `LEX_AUDIT__VERIFICATION_BATCH_SIZE` | int | (complex) | Entries to verify per verification run | `lexigram-audit/src/lexigram/audit/config.py:AuditConfig.verification_batch_size` |
| `LEX_AUDIT__VERIFICATION_SCHEDULE` | str | (complex) | Cron expression for scheduled verification | `lexigram-audit/src/lexigram/audit/config.py:AuditConfig.verification_schedule` |

### `lexigram-auth`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_AUTH__ADMIN_EMAIL` | str  \| None | None | Initial admin email | `lexigram-auth/src/lexigram/auth/config.py:AuthConfig.admin_email` |
| `LEX_AUTH__ADMIN_PASSWORD` | str  \| None | None | Initial admin password | `lexigram-auth/src/lexigram/auth/config.py:AuthConfig.admin_password` |
| `LEX_AUTH__ENABLED` | bool | True |  | `lexigram-auth/src/lexigram/auth/config.py:AuthConfig.enabled` |
| `LEX_AUTH__LOGIN_RATE_LIMIT` | str | "5/minute" | Default rate limit | `lexigram-auth/src/lexigram/auth/config.py:AuthConfig.login_rate_limit` |
| `LEX_AUTH__MAX_SESSIONS_PER_USER` | int  \| None | None | Maximum number of concurrent sessions allowed per user. ``None`` (the default) means unlimited.  When a positive integer | `lexigram-auth/src/lexigram/auth/config.py:AuthConfig.max_sessions_per_user` |
| `LEX_AUTH__MIDDLEWARE__BACKEND` | str | "session" | Auth backend type | `lexigram-auth/src/lexigram/auth/config.py:AuthMiddlewareConfig.middleware.backend` |
| `LEX_AUTH__MIDDLEWARE__EXCLUDE_PATHS` | list[str] | (required) | Paths excluded from auth | `lexigram-auth/src/lexigram/auth/config.py:AuthMiddlewareConfig.middleware.exclude_paths` |
| `LEX_AUTH__MIDDLEWARE__EXCLUDE_PREFIXES` | list[str] | (required) | Path prefixes excluded | `lexigram-auth/src/lexigram/auth/config.py:AuthMiddlewareConfig.middleware.exclude_prefixes` |
| `LEX_AUTH__MIDDLEWARE__HEADER_NAME` | str | "Authorization" | Header name for token | `lexigram-auth/src/lexigram/auth/config.py:AuthMiddlewareConfig.middleware.header_name` |
| `LEX_AUTH__MIDDLEWARE__LOGIN_RATE_LIMIT` | str | "5/minute" | Rate limit for auth endpoints | `lexigram-auth/src/lexigram/auth/config.py:AuthMiddlewareConfig.middleware.login_rate_limit` |
| `LEX_AUTH__MIDDLEWARE__LOGIN_URL` | str  \| None | None | URL to redirect for login | `lexigram-auth/src/lexigram/auth/config.py:AuthMiddlewareConfig.middleware.login_url` |
| `LEX_AUTH__MIDDLEWARE__OPTIONAL_AUTH` | bool | False | Whether authentication is optional | `lexigram-auth/src/lexigram/auth/config.py:AuthMiddlewareConfig.middleware.optional_auth` |
| `LEX_AUTH__MIDDLEWARE__PERMISSIONS_REQUIRED` | list[str] | (required) | Permissions required | `lexigram-auth/src/lexigram/auth/config.py:AuthMiddlewareConfig.middleware.permissions_required` |
| `LEX_AUTH__MIDDLEWARE__ROLES_REQUIRED` | list[str] | (required) | Roles required | `lexigram-auth/src/lexigram/auth/config.py:AuthMiddlewareConfig.middleware.roles_required` |
| `LEX_AUTH__MIDDLEWARE__SCHEME` | str | (complex) | Token scheme | `lexigram-auth/src/lexigram/auth/config.py:AuthMiddlewareConfig.middleware.scheme` |
| `LEX_AUTH__NAME` | str | "auth" |  | `lexigram-auth/src/lexigram/auth/config.py:AuthConfig.name` |
| `LEX_AUTH__OAUTH2_PROVIDERS` | dict[str, dict[str, str]] | (required) | OAuth2 configs | `lexigram-auth/src/lexigram/auth/config.py:AuthConfig.oauth2_providers` |
| `LEX_AUTH__PASSWORD__ARGON2_MEMORY_COST` | int | 65536 | Argon2id memory cost in KiB (OWASP floor is 19456) | `lexigram-auth/src/lexigram/auth/config.py:PasswordConfig.password.argon2_memory_cost` |
| `LEX_AUTH__PASSWORD__ARGON2_PARALLELISM` | int | 4 | Argon2id parallelism | `lexigram-auth/src/lexigram/auth/config.py:PasswordConfig.password.argon2_parallelism` |
| `LEX_AUTH__PASSWORD__ARGON2_TIME_COST` | int | 3 | Argon2id time cost | `lexigram-auth/src/lexigram/auth/config.py:PasswordConfig.password.argon2_time_cost` |
| `LEX_AUTH__PASSWORD__BANNED_PATTERNS` | list[str] | (required) | Substrings that must not appear in the password (case-insensitive). Use to reject common passwords or the user's own nam | `lexigram-auth/src/lexigram/auth/config.py:PasswordConfig.password.banned_patterns` |
| `LEX_AUTH__PASSWORD__BCRYPT_ROUNDS` | int | 12 | bcrypt cost factor for new hashes (minimum 12 in production) | `lexigram-auth/src/lexigram/auth/config.py:PasswordConfig.password.bcrypt_rounds` |
| `LEX_AUTH__PASSWORD__MAX_LENGTH` | int | 128 | Maximum password length | `lexigram-auth/src/lexigram/auth/config.py:PasswordConfig.password.max_length` |
| `LEX_AUTH__PASSWORD__MIN_LENGTH` | int | 12 | Minimum password length | `lexigram-auth/src/lexigram/auth/config.py:PasswordConfig.password.min_length` |
| `LEX_AUTH__PASSWORD__REQUIRE_DIGITS` | bool | True | Require at least one digit | `lexigram-auth/src/lexigram/auth/config.py:PasswordConfig.password.require_digits` |
| `LEX_AUTH__PASSWORD__REQUIRE_LOWERCASE` | bool | False | Require at least one lowercase letter | `lexigram-auth/src/lexigram/auth/config.py:PasswordConfig.password.require_lowercase` |
| `LEX_AUTH__PASSWORD__REQUIRE_SPECIAL` | bool | False | Require at least one special character (non-alphanumeric) | `lexigram-auth/src/lexigram/auth/config.py:PasswordConfig.password.require_special` |
| `LEX_AUTH__PASSWORD__REQUIRE_UPPERCASE` | bool | True | Require at least one uppercase letter | `lexigram-auth/src/lexigram/auth/config.py:PasswordConfig.password.require_uppercase` |
| `LEX_AUTH__RBAC__CACHE_PERMISSIONS` | bool | True | Cache resolved permissions | `lexigram-auth/src/lexigram/auth/config.py:RBACConfig.rbac.cache_permissions` |
| `LEX_AUTH__RBAC__DEFAULT_ROLE` | str | "viewer" | Default role for new users | `lexigram-auth/src/lexigram/auth/config.py:RBACConfig.rbac.default_role` |
| `LEX_AUTH__RBAC__ENABLED` | bool | True | Enable RBAC enforcement | `lexigram-auth/src/lexigram/auth/config.py:RBACConfig.rbac.enabled` |
| `LEX_AUTH__RBAC__PERMISSION_CACHE_TTL` | int | 300 | Permission cache TTL in seconds | `lexigram-auth/src/lexigram/auth/config.py:RBACConfig.rbac.permission_cache_ttl` |
| `LEX_AUTH__RBAC__SUPERUSER_BYPASS` | bool | True | Allow superuser role to bypass all checks | `lexigram-auth/src/lexigram/auth/config.py:RBACConfig.rbac.superuser_bypass` |
| `LEX_AUTH__RELAY_VERIFICATION` | bool | False | Enable binding ``RelayAuthVerifierProtocol`` for the relay gateway's inbound API-key authentication.  When ``False`` (de | `lexigram-auth/src/lexigram/auth/config.py:AuthConfig.relay_verification` |
| `LEX_AUTH__ROLES` | dict[str, AuthRoleConfig] | (required) | Role definitions | `lexigram-auth/src/lexigram/auth/config.py:AuthConfig.roles` |
| `LEX_AUTH__SECRET_KEY` | str | (required) | Secret key for signing | `lexigram-auth/src/lexigram/auth/config.py:AuthConfig.secret_key` |
| `LEX_AUTH__TOKEN__ACCESS_TOKEN_EXPIRE` | Duration | Duration.minutes(...) | Access token expiry duration | `lexigram-auth/src/lexigram/auth/config.py:JWTConfig.token.access_token_expire` |
| `LEX_AUTH__TOKEN__ALGORITHM` | str | (complex) | Algorithm | `lexigram-auth/src/lexigram/auth/config.py:JWTConfig.token.algorithm` |
| `LEX_AUTH__TOKEN__ID_TOKEN_EXPIRE` | Duration | Duration.hours(...) | ID token expiry duration | `lexigram-auth/src/lexigram/auth/config.py:JWTConfig.token.id_token_expire` |
| `LEX_AUTH__TOKEN__KEY_ROTATION_GRACE_PERIOD` | Duration | Duration.seconds(...) | Duration during which tokens signed by a rotated-out key remain accepted. Prevents immediate logout on key rotation. | `lexigram-auth/src/lexigram/auth/config.py:JWTConfig.token.key_rotation_grace_period` |
| `LEX_AUTH__TOKEN__REFRESH_TOKEN_EXPIRE` | Duration | Duration.days(...) | Refresh token expiry duration | `lexigram-auth/src/lexigram/auth/config.py:JWTConfig.token.refresh_token_expire` |
| `LEX_AUTH__TOKEN__REQUIRED_AUDIENCE` | str  \| None | None | Expected ``aud`` claim for every token verified by this service. When set, tokens whose audience does not match are reje | `lexigram-auth/src/lexigram/auth/config.py:JWTConfig.token.required_audience` |
| `LEX_AUTH__TOKEN__SECRET_KEY` | SecretStr | Ellipsis | Secret key for signing tokens | `lexigram-auth/src/lexigram/auth/config.py:JWTConfig.token.secret_key` |
| `LEX_AUTH__USERS` | list[AuthUserConfig] | (required) | Initial users | `lexigram-auth/src/lexigram/auth/config.py:AuthConfig.users` |

### `lexigram-cache`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_CACHE__BACKENDS` | list[CacheBackendConfig] | (required) | Backend configs | `lexigram-cache/src/lexigram/cache/config.py:CacheConfig.backends` |
| `LEX_CACHE__DEBUG` | bool | (complex) | Debug mode | `lexigram-cache/src/lexigram/cache/config.py:CacheConfig.debug` |
| `LEX_CACHE__ENABLED` | bool | (complex) | Whether cache is enabled | `lexigram-cache/src/lexigram/cache/config.py:CacheConfig.enabled` |
| `LEX_CACHE__ENV` | str  \| None | None | Environment (development/staging/production) | `lexigram-cache/src/lexigram/cache/config.py:CacheConfig.env` |
| `LEX_CACHE__ENVIRONMENT` | str | (complex) | Environment | `lexigram-cache/src/lexigram/cache/config.py:CacheConfig.environment` |
| `LEX_CACHE__NAME` | str | (complex) | Provider name | `lexigram-cache/src/lexigram/cache/config.py:CacheConfig.name` |
| `LEX_CACHE__SERVICE__CIRCUIT_BREAKER_ENABLED` | bool | (complex) | Enable circuit breaker | `lexigram-cache/src/lexigram/cache/config.py:CacheServiceConfig.service.circuit_breaker_enabled` |
| `LEX_CACHE__SERVICE__CIRCUIT_BREAKER_THRESHOLD` | int | (complex) | Circuit breaker threshold | `lexigram-cache/src/lexigram/cache/config.py:CacheServiceConfig.service.circuit_breaker_threshold` |
| `LEX_CACHE__SERVICE__DEFAULT_BACKEND` | str  \| None | None | Default backend name | `lexigram-cache/src/lexigram/cache/config.py:CacheServiceConfig.service.default_backend` |
| `LEX_CACHE__SERVICE__DEFAULT_SERIALIZER` | str | (complex) | Default serializer | `lexigram-cache/src/lexigram/cache/config.py:CacheServiceConfig.service.default_serializer` |
| `LEX_CACHE__SERVICE__ENABLE_HEALTH_CHECKS` | bool | (complex) | Enable health checks | `lexigram-cache/src/lexigram/cache/config.py:CacheServiceConfig.service.enable_health_checks` |
| `LEX_CACHE__SERVICE__ENABLE_METRICS` | bool | (complex) | Enable metrics | `lexigram-cache/src/lexigram/cache/config.py:CacheServiceConfig.service.enable_metrics` |
| `LEX_CACHE__SERVICE__ENABLE_PROTECTION` | bool | (complex) | Enable stampede protection | `lexigram-cache/src/lexigram/cache/config.py:CacheServiceConfig.service.enable_protection` |
| `LEX_CACHE__SERVICE__PROTECTION_LOCK_TTL` | int | (complex) | Protection lock TTL | `lexigram-cache/src/lexigram/cache/config.py:CacheServiceConfig.service.protection_lock_ttl` |
| `LEX_CACHE__SERVICE__PROTECTION_MAX_WAIT` | float | (complex) | Max wait for locks | `lexigram-cache/src/lexigram/cache/config.py:CacheServiceConfig.service.protection_max_wait` |
| `LEX_CACHE__SERVICE__PROTECTION_RETRY_INTERVAL` | float | (complex) | Lock retry interval | `lexigram-cache/src/lexigram/cache/config.py:CacheServiceConfig.service.protection_retry_interval` |
| `LEX_CACHE__VERSION` | str | (complex) | Config version | `lexigram-cache/src/lexigram/cache/config.py:CacheConfig.version` |

### `lexigram-events`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_EVENTS__COMMAND_BUS__ENABLE_LOGGING` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:CommandBusConfig.command_bus.enable_logging` |
| `LEX_EVENTS__COMMAND_BUS__ENABLE_METRICS` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:CommandBusConfig.command_bus.enable_metrics` |
| `LEX_EVENTS__COMMAND_BUS__ENABLE_VALIDATION` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:CommandBusConfig.command_bus.enable_validation` |
| `LEX_EVENTS__COMMAND_BUS__MAX_RETRIES` | int | 3 |  | `lexigram-events/src/lexigram/events/config.py:CommandBusConfig.command_bus.max_retries` |
| `LEX_EVENTS__COMMAND_BUS__RETRY_DELAY_SECONDS` | float | 1.0 |  | `lexigram-events/src/lexigram/events/config.py:CommandBusConfig.command_bus.retry_delay_seconds` |
| `LEX_EVENTS__COMMAND_BUS__TIMEOUT_SECONDS` | float | 30.0 |  | `lexigram-events/src/lexigram/events/config.py:CommandBusConfig.command_bus.timeout_seconds` |
| `LEX_EVENTS__DEBUG` | bool | False |  | `lexigram-events/src/lexigram/events/config.py:EventsConfig.debug` |
| `LEX_EVENTS__ENABLED` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:EventsConfig.enabled` |
| `LEX_EVENTS__ENV` | str  \| None | None | Environment (development/staging/production) | `lexigram-events/src/lexigram/events/config.py:EventsConfig.env` |
| `LEX_EVENTS__EVENT_BUS__ALLOW_NO_HANDLERS` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:EventBusConfig.event_bus.allow_no_handlers` |
| `LEX_EVENTS__EVENT_BUS__CONTINUE_ON_ERROR` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:EventBusConfig.event_bus.continue_on_error` |
| `LEX_EVENTS__EVENT_BUS__ENABLE_DEAD_LETTER` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:EventBusConfig.event_bus.enable_dead_letter` |
| `LEX_EVENTS__EVENT_BUS__HANDLER_TIMEOUT_SECONDS` | float | 30.0 |  | `lexigram-events/src/lexigram/events/config.py:EventBusConfig.event_bus.handler_timeout_seconds` |
| `LEX_EVENTS__EVENT_BUS__MAX_CONCURRENT_HANDLERS` | int | 10 |  | `lexigram-events/src/lexigram/events/config.py:EventBusConfig.event_bus.max_concurrent_handlers` |
| `LEX_EVENTS__EVENT_BUS__MAX_HANDLER_RETRIES` | int | 3 |  | `lexigram-events/src/lexigram/events/config.py:EventBusConfig.event_bus.max_handler_retries` |
| `LEX_EVENTS__EVENT_BUS__MAX_QUEUE_PER_SUBSCRIBER` | int | 1000 | Maximum number of events queued per event type before backpressure is applied. 0 means unbounded (no backpressure). | `lexigram-events/src/lexigram/events/config.py:EventBusConfig.event_bus.max_queue_per_subscriber` |
| `LEX_EVENTS__EVENT_BUS__PARALLEL_DISPATCH` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:EventBusConfig.event_bus.parallel_dispatch` |
| `LEX_EVENTS__EVENT_BUS__RETRY_FAILED_HANDLERS` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:EventBusConfig.event_bus.retry_failed_handlers` |
| `LEX_EVENTS__EVENT_STORE_BACKEND` | EventStoreBackend | (complex) |  | `lexigram-events/src/lexigram/events/config.py:EventsConfig.event_store_backend` |
| `LEX_EVENTS__KAFKA__AUTO_OFFSET_RESET` | str | "earliest" |  | `lexigram-events/src/lexigram/events/config.py:KafkaConfig.kafka.auto_offset_reset` |
| `LEX_EVENTS__KAFKA__BOOTSTRAP_SERVERS` | str | Ellipsis | Kafka bootstrap servers | `lexigram-events/src/lexigram/events/config.py:KafkaConfig.kafka.bootstrap_servers` |
| `LEX_EVENTS__KAFKA__CONSUMER_GROUP` | str | "events-consumers" |  | `lexigram-events/src/lexigram/events/config.py:KafkaConfig.kafka.consumer_group` |
| `LEX_EVENTS__KAFKA__ENABLE_AUTO_COMMIT` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:KafkaConfig.kafka.enable_auto_commit` |
| `LEX_EVENTS__KAFKA__TOPIC_PREFIX` | str | "events" |  | `lexigram-events/src/lexigram/events/config.py:KafkaConfig.kafka.topic_prefix` |
| `LEX_EVENTS__LOGGING_MIDDLEWARE__ENABLED` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:LoggingMiddlewareConfig.logging_middleware.enabled` |
| `LEX_EVENTS__LOGGING_MIDDLEWARE__INCLUDE_PAYLOAD` | bool | False |  | `lexigram-events/src/lexigram/events/config.py:LoggingMiddlewareConfig.logging_middleware.include_pay` |
| `LEX_EVENTS__LOGGING_MIDDLEWARE__LOG_LEVEL` | str | "INFO" |  | `lexigram-events/src/lexigram/events/config.py:LoggingMiddlewareConfig.logging_middleware.log_level` |
| `LEX_EVENTS__LOGGING_MIDDLEWARE__MAX_PAYLOAD_LENGTH` | int | 1000 |  | `lexigram-events/src/lexigram/events/config.py:LoggingMiddlewareConfig.logging_middleware.max_payload` |
| `LEX_EVENTS__MEMORY__ENABLE_SNAPSHOTS` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:InMemoryEventStoreConfig.memory.enable_snapshots` |
| `LEX_EVENTS__MEMORY__MAX_EVENTS_PER_STREAM` | int | 10000 |  | `lexigram-events/src/lexigram/events/config.py:InMemoryEventStoreConfig.memory.max_events_per_stream` |
| `LEX_EVENTS__METRICS_MIDDLEWARE__ENABLED` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:MetricsMiddlewareConfig.metrics_middleware.enabled` |
| `LEX_EVENTS__METRICS_MIDDLEWARE__HISTOGRAM_BUCKETS` | list[float] | (required) |  | `lexigram-events/src/lexigram/events/config.py:MetricsMiddlewareConfig.metrics_middleware.histogram_b` |
| `LEX_EVENTS__METRICS_MIDDLEWARE__INCLUDE_HISTOGRAMS` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:MetricsMiddlewareConfig.metrics_middleware.include_his` |
| `LEX_EVENTS__METRICS_MIDDLEWARE__PREFIX` | str | "events" |  | `lexigram-events/src/lexigram/events/config.py:MetricsMiddlewareConfig.metrics_middleware.prefix` |
| `LEX_EVENTS__MONGODB__CONNECTION_STRING` | SecretStr | Ellipsis | MongoDB connection string | `lexigram-events/src/lexigram/events/config.py:MongoDBEventStoreConfig.mongodb.connection_string` |
| `LEX_EVENTS__MONGODB__DATABASE_NAME` | str | "events" |  | `lexigram-events/src/lexigram/events/config.py:MongoDBEventStoreConfig.mongodb.database_name` |
| `LEX_EVENTS__MONGODB__EVENTS_COLLECTION` | str | "domain_events" |  | `lexigram-events/src/lexigram/events/config.py:MongoDBEventStoreConfig.mongodb.events_collection` |
| `LEX_EVENTS__MONGODB__MAX_POOL_SIZE` | int | 10 |  | `lexigram-events/src/lexigram/events/config.py:MongoDBEventStoreConfig.mongodb.max_pool_size` |
| `LEX_EVENTS__MONGODB__SERVER_SELECTION_TIMEOUT` | int | 30000 |  | `lexigram-events/src/lexigram/events/config.py:MongoDBEventStoreConfig.mongodb.server_selection_timeo` |
| `LEX_EVENTS__MONGODB__SNAPSHOTS_COLLECTION` | str | "snapshots" |  | `lexigram-events/src/lexigram/events/config.py:MongoDBEventStoreConfig.mongodb.snapshots_collection` |
| `LEX_EVENTS__NAME` | str | "events" |  | `lexigram-events/src/lexigram/events/config.py:EventsConfig.name` |
| `LEX_EVENTS__POSTGRES` | PostgresEventStoreConfig  \| None | None |  | `lexigram-events/src/lexigram/events/config.py:EventsConfig.postgres` |
| `LEX_EVENTS__PROJECTION__BATCH_SIZE` | int | 100 |  | `lexigram-events/src/lexigram/events/config.py:ProjectionConfig.projection.batch_size` |
| `LEX_EVENTS__PROJECTION__CHECKPOINT_INTERVAL` | int | 100 |  | `lexigram-events/src/lexigram/events/config.py:ProjectionConfig.projection.checkpoint_interval` |
| `LEX_EVENTS__PROJECTION__ENABLE_PARALLEL_PROJECTIONS` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:ProjectionConfig.projection.enable_parallel_projection` |
| `LEX_EVENTS__PROJECTION__MAX_CATCH_UP_EVENTS` | int | 10000 |  | `lexigram-events/src/lexigram/events/config.py:ProjectionConfig.projection.max_catch_up_events` |
| `LEX_EVENTS__PROJECTION__REBUILD_BATCH_SIZE` | int | 1000 |  | `lexigram-events/src/lexigram/events/config.py:ProjectionConfig.projection.rebuild_batch_size` |
| `LEX_EVENTS__QUERY_BUS__ENABLE_LOGGING` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:QueryBusConfig.query_bus.enable_logging` |
| `LEX_EVENTS__QUERY_BUS__ENABLE_METRICS` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:QueryBusConfig.query_bus.enable_metrics` |
| `LEX_EVENTS__QUERY_BUS__TIMEOUT_SECONDS` | float | 30.0 |  | `lexigram-events/src/lexigram/events/config.py:QueryBusConfig.query_bus.timeout_seconds` |
| `LEX_EVENTS__RABBITMQ__DURABLE` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:RabbitMQConfig.rabbitmq.durable` |
| `LEX_EVENTS__RABBITMQ__EXCHANGE_NAME` | str | "events" |  | `lexigram-events/src/lexigram/events/config.py:RabbitMQConfig.rabbitmq.exchange_name` |
| `LEX_EVENTS__RABBITMQ__PREFETCH_COUNT` | int | 10 |  | `lexigram-events/src/lexigram/events/config.py:RabbitMQConfig.rabbitmq.prefetch_count` |
| `LEX_EVENTS__RABBITMQ__QUEUE_PREFIX` | str | "events" |  | `lexigram-events/src/lexigram/events/config.py:RabbitMQConfig.rabbitmq.queue_prefix` |
| `LEX_EVENTS__RABBITMQ__URL` | SecretStr | Ellipsis | AMQP connection URL | `lexigram-events/src/lexigram/events/config.py:RabbitMQConfig.rabbitmq.url` |
| `LEX_EVENTS__RETRY_MIDDLEWARE__ENABLED` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:RetryMiddlewareConfig.retry_middleware.enabled` |
| `LEX_EVENTS__RETRY_MIDDLEWARE__EXPONENTIAL_BASE` | float | 2.0 |  | `lexigram-events/src/lexigram/events/config.py:RetryMiddlewareConfig.retry_middleware.exponential_bas` |
| `LEX_EVENTS__RETRY_MIDDLEWARE__INITIAL_DELAY_SECONDS` | float | 0.1 |  | `lexigram-events/src/lexigram/events/config.py:RetryMiddlewareConfig.retry_middleware.initial_delay_s` |
| `LEX_EVENTS__RETRY_MIDDLEWARE__MAX_DELAY_SECONDS` | float | 10.0 |  | `lexigram-events/src/lexigram/events/config.py:RetryMiddlewareConfig.retry_middleware.max_delay_secon` |
| `LEX_EVENTS__RETRY_MIDDLEWARE__MAX_RETRIES` | int | 3 |  | `lexigram-events/src/lexigram/events/config.py:RetryMiddlewareConfig.retry_middleware.max_retries` |
| `LEX_EVENTS__SAGA__CLEANUP_COMPLETED_AFTER_HOURS` | int | 24 |  | `lexigram-events/src/lexigram/events/config.py:SagaConfig.saga.cleanup_completed_after_hours` |
| `LEX_EVENTS__SAGA__DEFAULT_TIMEOUT_SECONDS` | float | 300.0 |  | `lexigram-events/src/lexigram/events/config.py:SagaConfig.saga.default_timeout_seconds` |
| `LEX_EVENTS__SAGA__ENABLE_COMPENSATION` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:SagaConfig.saga.enable_compensation` |
| `LEX_EVENTS__SAGA__MAX_RETRIES_PER_STEP` | int | 3 |  | `lexigram-events/src/lexigram/events/config.py:SagaConfig.saga.max_retries_per_step` |
| `LEX_EVENTS__SAGA__PERSIST_STATE` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:SagaConfig.saga.persist_state` |
| `LEX_EVENTS__SAGA__RETRY_DELAY_SECONDS` | float | 1.0 |  | `lexigram-events/src/lexigram/events/config.py:SagaConfig.saga.retry_delay_seconds` |
| `LEX_EVENTS__SNAPSHOTS__ENABLED` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:SnapshotConfig.snapshots.enabled` |
| `LEX_EVENTS__SNAPSHOTS__EVENT_COUNT_THRESHOLD` | int | 100 |  | `lexigram-events/src/lexigram/events/config.py:SnapshotConfig.snapshots.event_count_threshold` |
| `LEX_EVENTS__SNAPSHOTS__MAX_SNAPSHOTS_PER_AGGREGATE` | int | 5 |  | `lexigram-events/src/lexigram/events/config.py:SnapshotConfig.snapshots.max_snapshots_per_aggregate` |
| `LEX_EVENTS__SNAPSHOTS__STRATEGY` | SnapshotStrategy | (complex) |  | `lexigram-events/src/lexigram/events/config.py:SnapshotConfig.snapshots.strategy` |
| `LEX_EVENTS__SNAPSHOTS__TIME_THRESHOLD_SECONDS` | int | 3600 |  | `lexigram-events/src/lexigram/events/config.py:SnapshotConfig.snapshots.time_threshold_seconds` |
| `LEX_EVENTS__SQLITE__DATABASE` | str | "./events.db" |  | `lexigram-events/src/lexigram/events/config.py:SqliteConfig.sqlite.database` |
| `LEX_EVENTS__SQLITE__JOURNAL_MODE` | str | "WAL" |  | `lexigram-events/src/lexigram/events/config.py:SqliteConfig.sqlite.journal_mode` |
| `LEX_EVENTS__SQLITE__PRAGMAS` | dict[str, str] | (required) |  | `lexigram-events/src/lexigram/events/config.py:SqliteConfig.sqlite.pragmas` |
| `LEX_EVENTS__SQLITE__WAL_MODE` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:SqliteConfig.sqlite.wal_mode` |
| `LEX_EVENTS__STREAMING__BATCH_SIZE` | int | 100 |  | `lexigram-events/src/lexigram/events/config.py:StreamingConfig.streaming.batch_size` |
| `LEX_EVENTS__STREAMING__BUFFER_SIZE` | int | 1000 |  | `lexigram-events/src/lexigram/events/config.py:StreamingConfig.streaming.buffer_size` |
| `LEX_EVENTS__STREAMING__ENABLE_WEBSOCKET` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:StreamingConfig.streaming.enable_websocket` |
| `LEX_EVENTS__STREAMING__MAX_SUBSCRIBERS` | int | 100 |  | `lexigram-events/src/lexigram/events/config.py:StreamingConfig.streaming.max_subscribers` |
| `LEX_EVENTS__STREAMING__POLL_INTERVAL_MS` | int | 100 |  | `lexigram-events/src/lexigram/events/config.py:StreamingConfig.streaming.poll_interval_ms` |
| `LEX_EVENTS__STREAMING__WEBSOCKET_PING_INTERVAL` | int | 30 |  | `lexigram-events/src/lexigram/events/config.py:StreamingConfig.streaming.websocket_ping_interval` |
| `LEX_EVENTS__TRANSACTION_MIDDLEWARE__ENABLED` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:TransactionMiddlewareConfig.transaction_middleware.ena` |
| `LEX_EVENTS__TRANSACTION_MIDDLEWARE__ISOLATION_LEVEL` | str | "READ_COMMITTED" |  | `lexigram-events/src/lexigram/events/config.py:TransactionMiddlewareConfig.transaction_middleware.iso` |
| `LEX_EVENTS__TRANSACTION_MIDDLEWARE__TIMEOUT_SECONDS` | float | 30.0 |  | `lexigram-events/src/lexigram/events/config.py:TransactionMiddlewareConfig.transaction_middleware.tim` |
| `LEX_EVENTS__VALIDATION_MIDDLEWARE__ENABLED` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:ValidationMiddlewareConfig.validation_middleware.enabl` |
| `LEX_EVENTS__VALIDATION_MIDDLEWARE__STRICT_MODE` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:ValidationMiddlewareConfig.validation_middleware.stric` |
| `LEX_EVENTS__VERSION_SKEW_ALERTS_ENABLED` | bool | True |  | `lexigram-events/src/lexigram/events/config.py:EventsConfig.version_skew_alerts_enabled` |

### `lexigram-features`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_FEATURES__CACHE_TTL` | int | DEFAULT_CACHE_TTL | Seconds to cache flag evaluations (0 = disabled). | `lexigram-features/src/lexigram/features/config.py:FeatureFlagsConfig.cache_ttl` |
| `LEX_FEATURES__DEFAULT_ENABLED` | bool | DEFAULT_ENABLED | Default value when a flag is not found in the provider. | `lexigram-features/src/lexigram/features/config.py:FeatureFlagsConfig.default_enabled` |
| `LEX_FEATURES__ENABLED` | bool | True | Enable the feature flags subsystem | `lexigram-features/src/lexigram/features/config.py:FeatureFlagsConfig.enabled` |
| `LEX_FEATURES__FLAG_ENV_PREFIX` | str | FLAG_ENV_PREFIX | Env var prefix used by EnvProvider when reading flag values. | `lexigram-features/src/lexigram/features/config.py:FeatureFlagsConfig.flag_env_prefix` |
| `LEX_FEATURES__INITIAL_FLAGS` | dict[str, bool] | (required) | Seed flags for the in-memory provider (name -> enabled). | `lexigram-features/src/lexigram/features/config.py:FeatureFlagsConfig.initial_flags` |

### `lexigram-graph`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_GRAPH__BACKEND` | str | (complex) | Graph store backend to use | `lexigram-graph/src/lexigram/graph/config.py:GraphConfig.backend` |
| `LEX_GRAPH__BULK_BATCH_SIZE` | int | (complex) | Batch size for bulk operations | `lexigram-graph/src/lexigram/graph/config.py:GraphConfig.bulk_batch_size` |
| `LEX_GRAPH__DEFAULT_QUERY_LIMIT` | int | (complex) | Default limit for query results | `lexigram-graph/src/lexigram/graph/config.py:GraphConfig.default_query_limit` |
| `LEX_GRAPH__DEFAULT_TRAVERSAL_MAX_DEPTH` | int | (complex) | Default maximum depth for traversals | `lexigram-graph/src/lexigram/graph/config.py:GraphConfig.default_traversal_max_depth` |
| `LEX_GRAPH__ENABLED` | bool | True | Enable the graph store subsystem | `lexigram-graph/src/lexigram/graph/config.py:GraphConfig.enabled` |
| `LEX_GRAPH__MAX_RETRIES` | int | (complex) | Maximum number of retries for operations | `lexigram-graph/src/lexigram/graph/config.py:GraphConfig.max_retries` |
| `LEX_GRAPH__MEMORY__MAX_EDGES` | int | (complex) | Maximum number of edges in memory | `lexigram-graph/src/lexigram/graph/config.py:MemoryConfig.memory.max_edges` |
| `LEX_GRAPH__MEMORY__MAX_NODES` | int | (complex) | Maximum number of nodes in memory | `lexigram-graph/src/lexigram/graph/config.py:MemoryConfig.memory.max_nodes` |
| `LEX_GRAPH__NEO4J__CONNECTION_TIMEOUT` | float | (complex) | Connection timeout in seconds | `lexigram-graph/src/lexigram/graph/config.py:Neo4jConfig.neo4j.connection_timeout` |
| `LEX_GRAPH__NEO4J__DATABASE` | str | (complex) | Target database name | `lexigram-graph/src/lexigram/graph/config.py:Neo4jConfig.neo4j.database` |
| `LEX_GRAPH__NEO4J__ENCRYPTED` | bool | False | Whether to use SSL/TLS encryption | `lexigram-graph/src/lexigram/graph/config.py:Neo4jConfig.neo4j.encrypted` |
| `LEX_GRAPH__NEO4J__FETCH_SIZE` | int | (complex) | Default fetch size for results | `lexigram-graph/src/lexigram/graph/config.py:Neo4jConfig.neo4j.fetch_size` |
| `LEX_GRAPH__NEO4J__MAX_CONNECTION_POOL_SIZE` | int | (complex) | Maximum number of connections in the pool | `lexigram-graph/src/lexigram/graph/config.py:Neo4jConfig.neo4j.max_connection_pool_size` |
| `LEX_GRAPH__NEO4J__MAX_TRANSACTION_RETRY_TIME` | float | 30.0 | Maximum time for transaction retries | `lexigram-graph/src/lexigram/graph/config.py:Neo4jConfig.neo4j.max_transaction_retry_time` |
| `LEX_GRAPH__NEO4J__PASSWORD` | SecretStr | (required) | Neo4j password | `lexigram-graph/src/lexigram/graph/config.py:Neo4jConfig.neo4j.password` |
| `LEX_GRAPH__NEO4J__TRUST` | str | "TRUST_SYSTEM_CA_SIGNED_CERTIFICATES" | Trust strategy for SSL | `lexigram-graph/src/lexigram/graph/config.py:Neo4jConfig.neo4j.trust` |
| `LEX_GRAPH__NEO4J__URI` | str | "bolt://localhost:7687" | Neo4j BOLT URI | `lexigram-graph/src/lexigram/graph/config.py:Neo4jConfig.neo4j.uri` |
| `LEX_GRAPH__NEO4J__USERNAME` | str | "neo4j" | Neo4j username | `lexigram-graph/src/lexigram/graph/config.py:Neo4jConfig.neo4j.username` |
| `LEX_GRAPH__RETRY_DELAY` | float | (complex) | Delay between retries in seconds | `lexigram-graph/src/lexigram/graph/config.py:GraphConfig.retry_delay` |
| `LEX_GRAPH__TENANCY__ENABLED` | bool | False | Enable tenant-aware graph resolution | `lexigram-graph/src/lexigram/graph/config.py:GraphTenancyConfig.tenancy.enabled` |
| `LEX_GRAPH__TENANCY__STRATEGY` | str | "node_property" | Which tenancy strategy to use. One of ``"node_property"`` or ``"graph_per_tenant"``. | `lexigram-graph/src/lexigram/graph/config.py:GraphTenancyConfig.tenancy.strategy` |
| `LEX_GRAPH__TENANCY__TEMPLATE` | str | "{logical}_t_{tenant}" | Collection name template for ``GRAPH_PER_TENANT`` strategy. Supports ``{logical}`` and ``{tenant}`` placeholders. | `lexigram-graph/src/lexigram/graph/config.py:GraphTenancyConfig.tenancy.template` |

### `lexigram-graphql`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_GRAPHQL__ALIAS_LIMIT__ENABLED` | bool | True |  | `lexigram-graphql/src/lexigram/graphql/config.py:AliasLimitConfig.alias_limit.enabled` |
| `LEX_GRAPHQL__ALIAS_LIMIT__MAX_ALIASES` | int | (complex) |  | `lexigram-graphql/src/lexigram/graphql/config.py:AliasLimitConfig.alias_limit.max_aliases` |
| `LEX_GRAPHQL__BATCH__ENABLED` | bool | False |  | `lexigram-graphql/src/lexigram/graphql/config.py:BatchConfig.batch.enabled` |
| `LEX_GRAPHQL__BATCH__MAX_BATCH_SIZE` | int | 10 |  | `lexigram-graphql/src/lexigram/graphql/config.py:BatchConfig.batch.max_batch_size` |
| `LEX_GRAPHQL__CACHE__DEFAULT_MAX_AGE` | Duration  \| int | (complex) |  | `lexigram-graphql/src/lexigram/graphql/config.py:CacheConfig.cache.default_max_age` |
| `LEX_GRAPHQL__CACHE__DEFAULT_SCOPE` | CacheScope | (complex) |  | `lexigram-graphql/src/lexigram/graphql/config.py:CacheConfig.cache.default_scope` |
| `LEX_GRAPHQL__CACHE__ENABLED` | bool | True |  | `lexigram-graphql/src/lexigram/graphql/config.py:CacheConfig.cache.enabled` |
| `LEX_GRAPHQL__CACHE__VARY_HEADERS` | list[str] | (required) |  | `lexigram-graphql/src/lexigram/graphql/config.py:CacheConfig.cache.vary_headers` |
| `LEX_GRAPHQL__COMPLEXITY__DEFAULT_FIELD_COST` | float | 1.0 |  | `lexigram-graphql/src/lexigram/graphql/config.py:ComplexityConfig.complexity.default_field_cost` |
| `LEX_GRAPHQL__COMPLEXITY__DEFAULT_LIST_COST` | float | 10.0 |  | `lexigram-graphql/src/lexigram/graphql/config.py:ComplexityConfig.complexity.default_list_cost` |
| `LEX_GRAPHQL__COMPLEXITY__ENABLED` | bool | True |  | `lexigram-graphql/src/lexigram/graphql/config.py:ComplexityConfig.complexity.enabled` |
| `LEX_GRAPHQL__COMPLEXITY__MAX_COMPLEXITY` | int | (complex) |  | `lexigram-graphql/src/lexigram/graphql/config.py:ComplexityConfig.complexity.max_complexity` |
| `LEX_GRAPHQL__DATALOADER__BATCH_DELAY_MS` | float | 2.0 | Delay in milliseconds before executing a DataLoaderProtocol batch. A small non-zero value (2ms) lets more keys accumulat | `lexigram-graphql/src/lexigram/graphql/config.py:DataLoaderConfig.dataloader.batch_delay_ms` |
| `LEX_GRAPHQL__DATALOADER__BATCH_ENABLED` | bool | True |  | `lexigram-graphql/src/lexigram/graphql/config.py:DataLoaderConfig.dataloader.batch_enabled` |
| `LEX_GRAPHQL__DATALOADER__CACHE_ENABLED` | bool | True |  | `lexigram-graphql/src/lexigram/graphql/config.py:DataLoaderConfig.dataloader.cache_enabled` |
| `LEX_GRAPHQL__DATALOADER__ENABLED` | bool | True |  | `lexigram-graphql/src/lexigram/graphql/config.py:DataLoaderConfig.dataloader.enabled` |
| `LEX_GRAPHQL__DATALOADER__MAX_BATCH_SIZE` | int | 100 |  | `lexigram-graphql/src/lexigram/graphql/config.py:DataLoaderConfig.dataloader.max_batch_size` |
| `LEX_GRAPHQL__DEBUG` | bool | False |  | `lexigram-graphql/src/lexigram/graphql/config.py:GraphQLConfig.debug` |
| `LEX_GRAPHQL__DEPTH_LIMIT__ENABLED` | bool | True |  | `lexigram-graphql/src/lexigram/graphql/config.py:DepthLimitConfig.depth_limit.enabled` |
| `LEX_GRAPHQL__DEPTH_LIMIT__IGNORE_INTROSPECTION` | bool | True |  | `lexigram-graphql/src/lexigram/graphql/config.py:DepthLimitConfig.depth_limit.ignore_introspection` |
| `LEX_GRAPHQL__DEPTH_LIMIT__MAX_DEPTH` | int | (complex) |  | `lexigram-graphql/src/lexigram/graphql/config.py:DepthLimitConfig.depth_limit.max_depth` |
| `LEX_GRAPHQL__ENABLED` | bool | True |  | `lexigram-graphql/src/lexigram/graphql/config.py:GraphQLConfig.enabled` |
| `LEX_GRAPHQL__ENABLE_IDENTITY_RESOLUTION` | bool | False |  | `lexigram-graphql/src/lexigram/graphql/config.py:GraphQLConfig.enable_identity_resolution` |
| `LEX_GRAPHQL__ENV` | str  \| None | None | Environment (development/staging/production) | `lexigram-graphql/src/lexigram/graphql/config.py:GraphQLConfig.env` |
| `LEX_GRAPHQL__ERRORS__DEBUG_MODE` | bool | False |  | `lexigram-graphql/src/lexigram/graphql/config.py:ErrorConfig.errors.debug_mode` |
| `LEX_GRAPHQL__ERRORS__INCLUDE_STACKTRACE` | bool | False |  | `lexigram-graphql/src/lexigram/graphql/config.py:ErrorConfig.errors.include_stacktrace` |
| `LEX_GRAPHQL__ERRORS__LOG_ERRORS` | bool | True |  | `lexigram-graphql/src/lexigram/graphql/config.py:ErrorConfig.errors.log_errors` |
| `LEX_GRAPHQL__ERRORS__MASK_ERRORS` | bool | True |  | `lexigram-graphql/src/lexigram/graphql/config.py:ErrorConfig.errors.mask_errors` |
| `LEX_GRAPHQL__INTROSPECTION__ALLOWED_ENVIRONMENTS` | set[str] | (required) |  | `lexigram-graphql/src/lexigram/graphql/config.py:IntrospectionConfig.introspection.allowed_environmen` |
| `LEX_GRAPHQL__INTROSPECTION__ENABLED` | bool | True |  | `lexigram-graphql/src/lexigram/graphql/config.py:IntrospectionConfig.introspection.enabled` |
| `LEX_GRAPHQL__METRICS__ENABLED` | bool | False |  | `lexigram-graphql/src/lexigram/graphql/config.py:MetricsConfig.metrics.enabled` |
| `LEX_GRAPHQL__METRICS__HISTOGRAM_BUCKETS` | list[float] | (required) |  | `lexigram-graphql/src/lexigram/graphql/config.py:MetricsConfig.metrics.histogram_buckets` |
| `LEX_GRAPHQL__METRICS__INCLUDE_LABELS` | list[str] | (required) |  | `lexigram-graphql/src/lexigram/graphql/config.py:MetricsConfig.metrics.include_labels` |
| `LEX_GRAPHQL__METRICS__NAMESPACE` | str | "lexigram_graphql" |  | `lexigram-graphql/src/lexigram/graphql/config.py:MetricsConfig.metrics.namespace` |
| `LEX_GRAPHQL__NAME` | str | "graphql" |  | `lexigram-graphql/src/lexigram/graphql/config.py:GraphQLConfig.name` |
| `LEX_GRAPHQL__PATH` | str | (complex) |  | `lexigram-graphql/src/lexigram/graphql/config.py:GraphQLConfig.path` |
| `LEX_GRAPHQL__PERSISTED_QUERIES__ENABLED` | bool | True |  | `lexigram-graphql/src/lexigram/graphql/config.py:PersistedQueryConfig.persisted_queries.enabled` |
| `LEX_GRAPHQL__PERSISTED_QUERIES__STORE_TYPE` | str | "memory" |  | `lexigram-graphql/src/lexigram/graphql/config.py:PersistedQueryConfig.persisted_queries.store_type` |
| `LEX_GRAPHQL__PERSISTED_QUERIES__TTL_SECONDS` | Duration  \| int | 86400 |  | `lexigram-graphql/src/lexigram/graphql/config.py:PersistedQueryConfig.persisted_queries.ttl_seconds` |
| `LEX_GRAPHQL__PLAYGROUND__ENABLED` | bool | True |  | `lexigram-graphql/src/lexigram/graphql/config.py:PlaygroundConfig.playground.enabled` |
| `LEX_GRAPHQL__PLAYGROUND__PATH` | str | (complex) |  | `lexigram-graphql/src/lexigram/graphql/config.py:PlaygroundConfig.playground.path` |
| `LEX_GRAPHQL__PLAYGROUND__TITLE` | str | "Lexigram GraphQL Playground" |  | `lexigram-graphql/src/lexigram/graphql/config.py:PlaygroundConfig.playground.title` |
| `LEX_GRAPHQL__RATE_LIMIT` | RateLimitConfig | (required) |  | `lexigram-graphql/src/lexigram/graphql/config.py:GraphQLConfig.rate_limit` |
| `LEX_GRAPHQL__SCHEMA_BASELINE_PATH` | str  \| None | None | Path to a GraphQL SDL (.graphql) file containing the baseline schema. When set, GraphQLProvider.boot() compares the curr | `lexigram-graphql/src/lexigram/graphql/config.py:GraphQLConfig.schema_baseline_path` |
| `LEX_GRAPHQL__SUBSCRIPTIONS__CONNECTION_TIMEOUT` | Duration  \| int | 60 |  | `lexigram-graphql/src/lexigram/graphql/config.py:SubscriptionConfig.subscriptions.connection_timeout` |
| `LEX_GRAPHQL__SUBSCRIPTIONS__ENABLED` | bool | True |  | `lexigram-graphql/src/lexigram/graphql/config.py:SubscriptionConfig.subscriptions.enabled` |
| `LEX_GRAPHQL__SUBSCRIPTIONS__KEEPALIVE_INTERVAL` | Duration  \| int | (complex) |  | `lexigram-graphql/src/lexigram/graphql/config.py:SubscriptionConfig.subscriptions.keepalive_interval` |
| `LEX_GRAPHQL__SUBSCRIPTIONS__PATH` | str | (complex) |  | `lexigram-graphql/src/lexigram/graphql/config.py:SubscriptionConfig.subscriptions.path` |
| `LEX_GRAPHQL__SUBSCRIPTIONS__PROTOCOL` | SubscriptionProtocol | (complex) |  | `lexigram-graphql/src/lexigram/graphql/config.py:SubscriptionConfig.subscriptions.protocol` |
| `LEX_GRAPHQL__TRACING__ENABLED` | bool | False |  | `lexigram-graphql/src/lexigram/graphql/config.py:TracingConfig.tracing.enabled` |
| `LEX_GRAPHQL__TRACING__SAMPLE_RATE` | float | 1.0 |  | `lexigram-graphql/src/lexigram/graphql/config.py:TracingConfig.tracing.sample_rate` |
| `LEX_GRAPHQL__TRACING__SERVICE_NAME` | str | "lexigram-graphql" |  | `lexigram-graphql/src/lexigram/graphql/config.py:TracingConfig.tracing.service_name` |
| `LEX_GRAPHQL__TRACING__TRACE_DATALOADERS` | bool | True |  | `lexigram-graphql/src/lexigram/graphql/config.py:TracingConfig.tracing.trace_dataloaders` |
| `LEX_GRAPHQL__TRACING__TRACE_RESOLVERS` | bool | True |  | `lexigram-graphql/src/lexigram/graphql/config.py:TracingConfig.tracing.trace_resolvers` |

### `lexigram-monitor`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_MONITOR__DEBUG` | bool | False | Enable debug mode | `lexigram-monitor/src/lexigram/monitor/config.py:MonitorConfig.debug` |
| `LEX_MONITOR__ENABLED` | bool | True | Enable monitoring | `lexigram-monitor/src/lexigram/monitor/config.py:MonitorConfig.enabled` |
| `LEX_MONITOR__ENV` | str  \| None | None | Environment (development/staging/production) | `lexigram-monitor/src/lexigram/monitor/config.py:MonitorConfig.env` |
| `LEX_MONITOR__ENVIRONMENT` | Environment | (complex) | Deployment environment | `lexigram-monitor/src/lexigram/monitor/config.py:MonitorConfig.environment` |
| `LEX_MONITOR__HEALTH__CHECKS` | list[str] | (required) | List of health check names to run | `lexigram-monitor/src/lexigram/monitor/config.py:HealthCheckConfig.health.checks` |
| `LEX_MONITOR__HEALTH__ENABLED` | bool | True | Enable health checks | `lexigram-monitor/src/lexigram/monitor/config.py:HealthCheckConfig.health.enabled` |
| `LEX_MONITOR__HEALTH__INCLUDE_DETAILS` | bool | True | Include detailed health info in response | `lexigram-monitor/src/lexigram/monitor/config.py:HealthCheckConfig.health.include_details` |
| `LEX_MONITOR__HEALTH__INTERVAL` | int | (complex) | Health check interval in seconds | `lexigram-monitor/src/lexigram/monitor/config.py:HealthCheckConfig.health.interval` |
| `LEX_MONITOR__HEALTH__PATH` | str | "/health" | Health endpoint path | `lexigram-monitor/src/lexigram/monitor/config.py:HealthCheckConfig.health.path` |
| `LEX_MONITOR__HEALTH__TIMEOUT` | float | 5.0 | Health check timeout in seconds | `lexigram-monitor/src/lexigram/monitor/config.py:HealthCheckConfig.health.timeout` |
| `LEX_MONITOR__LOGGING__ENABLED` | bool | True | Enable structured logging | `lexigram-monitor/src/lexigram/monitor/config.py:LoggingConfig.logging.enabled` |
| `LEX_MONITOR__LOGGING__FORMAT` | str | "json" | Log format (json, text) | `lexigram-monitor/src/lexigram/monitor/config.py:LoggingConfig.logging.format` |
| `LEX_MONITOR__LOGGING__INCLUDE_TRACE_CONTEXT` | bool | True | Include trace context in logs | `lexigram-monitor/src/lexigram/monitor/config.py:LoggingConfig.logging.include_trace_context` |
| `LEX_MONITOR__LOGGING__LEVEL` | str | "INFO" | Default log level | `lexigram-monitor/src/lexigram/monitor/config.py:LoggingConfig.logging.level` |
| `LEX_MONITOR__LOGGING__REDACT_FIELDS` | list[str] | (required) | Fields to redact from logs | `lexigram-monitor/src/lexigram/monitor/config.py:LoggingConfig.logging.redact_fields` |
| `LEX_MONITOR__METRICS__COLLECTION_INTERVAL` | float | 60.0 | Metrics collection interval in seconds | `lexigram-monitor/src/lexigram/monitor/config.py:MetricsConfig.metrics.collection_interval` |
| `LEX_MONITOR__METRICS__DEFAULT_LABELS` | dict[str, str] | (required) | Default labels for all metrics | `lexigram-monitor/src/lexigram/monitor/config.py:MetricsConfig.metrics.default_labels` |
| `LEX_MONITOR__METRICS__ENABLED` | bool | True | Enable metrics collection | `lexigram-monitor/src/lexigram/monitor/config.py:MetricsConfig.metrics.enabled` |
| `LEX_MONITOR__METRICS__HISTOGRAM_BUCKETS` | list[float] | (required) | Default histogram bucket boundaries | `lexigram-monitor/src/lexigram/monitor/config.py:MetricsConfig.metrics.histogram_buckets` |
| `LEX_MONITOR__METRICS__PREFIX` | str | (complex) | MetricProtocol name prefix | `lexigram-monitor/src/lexigram/monitor/config.py:MetricsConfig.metrics.prefix` |
| `LEX_MONITOR__NAME` | str | (complex) | Provider name | `lexigram-monitor/src/lexigram/monitor/config.py:MonitorConfig.name` |
| `LEX_MONITOR__OPENTELEMETRY__BATCH_SIZE` | int | 512 | Export batch size | `lexigram-monitor/src/lexigram/monitor/config.py:OpenTelemetryConfig.opentelemetry.batch_size` |
| `LEX_MONITOR__OPENTELEMETRY__COMPRESSION` | str | "none" | Compression type (none, gzip) | `lexigram-monitor/src/lexigram/monitor/config.py:OpenTelemetryConfig.opentelemetry.compression` |
| `LEX_MONITOR__OPENTELEMETRY__ENDPOINT` | str  \| None | None | OTLP endpoint URL | `lexigram-monitor/src/lexigram/monitor/config.py:OpenTelemetryConfig.opentelemetry.endpoint` |
| `LEX_MONITOR__OPENTELEMETRY__EXPORT_INTERVAL` | float | 5.0 | Export interval seconds | `lexigram-monitor/src/lexigram/monitor/config.py:OpenTelemetryConfig.opentelemetry.export_interval` |
| `LEX_MONITOR__OPENTELEMETRY__HEADERS` | dict[str, str] | (required) | OTLP request headers | `lexigram-monitor/src/lexigram/monitor/config.py:OpenTelemetryConfig.opentelemetry.headers` |
| `LEX_MONITOR__OPENTELEMETRY__INSECURE` | bool | False | Use insecure connection | `lexigram-monitor/src/lexigram/monitor/config.py:OpenTelemetryConfig.opentelemetry.insecure` |
| `LEX_MONITOR__OPENTELEMETRY__METRICS_EXPORTERS` | list[OTelExporterConfig] | (required) | List of metrics exporters to build. | `lexigram-monitor/src/lexigram/monitor/config.py:OpenTelemetryConfig.opentelemetry.metrics_exporters` |
| `LEX_MONITOR__OPENTELEMETRY__TIMEOUT` | float | 30.0 | Export timeout seconds | `lexigram-monitor/src/lexigram/monitor/config.py:OpenTelemetryConfig.opentelemetry.timeout` |
| `LEX_MONITOR__OPENTELEMETRY__TRACING_EXPORTERS` | list[OTelExporterConfig] | (required) | List of tracing exporters to build. | `lexigram-monitor/src/lexigram/monitor/config.py:OpenTelemetryConfig.opentelemetry.tracing_exporters` |
| `LEX_MONITOR__PROMETHEUS__ENABLE_DEFAULT_METRICS` | bool | True | Enable default process metrics | `lexigram-monitor/src/lexigram/monitor/config.py:PrometheusConfig.prometheus.enable_default_metrics` |
| `LEX_MONITOR__PROMETHEUS__METRICS_TABLE` | str | "metrics_samples" | Table name for metrics samples | `lexigram-monitor/src/lexigram/monitor/config.py:PrometheusConfig.prometheus.metrics_table` |
| `LEX_MONITOR__PROMETHEUS__PATH` | str | "/metrics" | Metrics endpoint path | `lexigram-monitor/src/lexigram/monitor/config.py:PrometheusConfig.prometheus.path` |
| `LEX_MONITOR__PROMETHEUS__PORT` | int | (complex) | Metrics server port | `lexigram-monitor/src/lexigram/monitor/config.py:PrometheusConfig.prometheus.port` |
| `LEX_MONITOR__PROMETHEUS__PUSHGATEWAY_URL` | str  \| None | None | Pushgateway URL for push-based metrics | `lexigram-monitor/src/lexigram/monitor/config.py:PrometheusConfig.prometheus.pushgateway_url` |
| `LEX_MONITOR__PROMETHEUS__PUSH_INTERVAL` | float | 10.0 | Push interval for Pushgateway | `lexigram-monitor/src/lexigram/monitor/config.py:PrometheusConfig.prometheus.push_interval` |
| `LEX_MONITOR__PROMETHEUS__STORE_IN_DB` | bool | False | Persist metrics observations to DB | `lexigram-monitor/src/lexigram/monitor/config.py:PrometheusConfig.prometheus.store_in_db` |
| `LEX_MONITOR__SLO__ALERT_CHANNELS` | list[str] | (required) | Alert channel names for SLO violation dispatch | `lexigram-monitor/src/lexigram/monitor/config.py:SLOConfig.slo.alert_channels` |
| `LEX_MONITOR__SLO__ENABLED` | bool | True | Enable periodic SLO evaluation worker | `lexigram-monitor/src/lexigram/monitor/config.py:SLOConfig.slo.enabled` |
| `LEX_MONITOR__SLO__EVALUATION_INTERVAL` | float | 60.0 | SLO evaluation interval in seconds | `lexigram-monitor/src/lexigram/monitor/config.py:SLOConfig.slo.evaluation_interval` |
| `LEX_MONITOR__SLO__SUPPRESSION_WINDOW_SECONDS` | int | 300 | Alert suppression window in seconds | `lexigram-monitor/src/lexigram/monitor/config.py:SLOConfig.slo.suppression_window_seconds` |
| `LEX_MONITOR__TRACING__ENABLED` | bool | True | Enable tracing | `lexigram-monitor/src/lexigram/monitor/config.py:TracingConfig.tracing.enabled` |
| `LEX_MONITOR__TRACING__MAX_ATTRIBUTES` | int | 128 | Max attributes per span | `lexigram-monitor/src/lexigram/monitor/config.py:TracingConfig.tracing.max_attributes` |
| `LEX_MONITOR__TRACING__MAX_EVENTS` | int | 128 | Max events per span | `lexigram-monitor/src/lexigram/monitor/config.py:TracingConfig.tracing.max_events` |
| `LEX_MONITOR__TRACING__MAX_LINKS` | int | 128 | Max links per span | `lexigram-monitor/src/lexigram/monitor/config.py:TracingConfig.tracing.max_links` |
| `LEX_MONITOR__TRACING__MAX_SPANS` | int | (complex) | Max number of spans to keep in memory | `lexigram-monitor/src/lexigram/monitor/config.py:TracingConfig.tracing.max_spans` |
| `LEX_MONITOR__TRACING__MAX_TRACES_PER_SECOND` | int | 100 | Max traces to sample per second | `lexigram-monitor/src/lexigram/monitor/config.py:TracingConfig.tracing.max_traces_per_second` |
| `LEX_MONITOR__TRACING__PROPAGATION_FORMATS` | list[str] | (required) | Propagation format list | `lexigram-monitor/src/lexigram/monitor/config.py:TracingConfig.tracing.propagation_formats` |
| `LEX_MONITOR__TRACING__SAMPLE_RATE` | float | 1.0 | Sample rate (0.0 to 1.0) | `lexigram-monitor/src/lexigram/monitor/config.py:TracingConfig.tracing.sample_rate` |
| `LEX_MONITOR__TRACING__SERVICE_NAME` | str | (complex) | Service name for traces | `lexigram-monitor/src/lexigram/monitor/config.py:TracingConfig.tracing.service_name` |

### `lexigram-nosql`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_NOSQL__BACKENDS` | list[NamedNoSQLConfig] | (required) | Named NoSQL backends for multi-store support. When non-empty, the provider registers each backend under Annotated[Docume | `lexigram-nosql/src/lexigram/nosql/config.py:NoSQLConfig.backends` |
| `LEX_NOSQL__DRIVER` | str | "mongodb" | NoSQL driver name | `lexigram-nosql/src/lexigram/nosql/config.py:NoSQLConfig.driver` |
| `LEX_NOSQL__ENABLED` | bool | True | Enable NoSQL support | `lexigram-nosql/src/lexigram/nosql/config.py:NoSQLConfig.enabled` |
| `LEX_NOSQL__FIRESTORE__CREDENTIALS_JSON` | str  \| None | None | Path to a service account JSON key file, or the raw JSON string. When ``None``, Application Default Credentials (ADC) ar | `lexigram-nosql/src/lexigram/nosql/config.py:FirestoreConfig.firestore.credentials_json` |
| `LEX_NOSQL__FIRESTORE__DATABASE_ID` | str | "(default)" | Firestore database ID (use '(default)' for the default database) | `lexigram-nosql/src/lexigram/nosql/config.py:FirestoreConfig.firestore.database_id` |
| `LEX_NOSQL__FIRESTORE__PROJECT_ID` | str | Ellipsis | Google Cloud project ID | `lexigram-nosql/src/lexigram/nosql/config.py:FirestoreConfig.firestore.project_id` |
| `LEX_NOSQL__MONGODB__AUTH_SOURCE` | str | "admin" | Authentication database | `lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.auth_source` |
| `LEX_NOSQL__MONGODB__CONNECT_TIMEOUT_MS` | int | 10000 | Connection timeout (ms) | `lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.connect_timeout_ms` |
| `LEX_NOSQL__MONGODB__DATABASE` | str | "lexigram" | Database name | `lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.database` |
| `LEX_NOSQL__MONGODB__MAX_POOL_SIZE` | int | 100 | Maximum connection pool size | `lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.max_pool_size` |
| `LEX_NOSQL__MONGODB__MIN_POOL_SIZE` | int | 10 | Minimum connection pool size | `lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.min_pool_size` |
| `LEX_NOSQL__MONGODB__READ_PREFERENCE` | str | "primaryPreferred" | Read preference mode | `lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.read_preference` |
| `LEX_NOSQL__MONGODB__RETRY_READS` | bool | True | Enable read retries | `lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.retry_reads` |
| `LEX_NOSQL__MONGODB__RETRY_WRITES` | bool | True | Enable write retries | `lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.retry_writes` |
| `LEX_NOSQL__MONGODB__SERVER_SELECTION_TIMEOUT_MS` | int | 5000 | Server selection timeout (ms) | `lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.server_selection_timeout_ms` |
| `LEX_NOSQL__MONGODB__SOCKET_TIMEOUT_MS` | int | 30000 | Socket timeout (ms) | `lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.socket_timeout_ms` |
| `LEX_NOSQL__MONGODB__URI` | str | "mongodb://localhost:27017" | MongoDB connection URI | `lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.uri` |
| `LEX_NOSQL__MONGODB__WRITE_CONCERN_W` | str  \| int | "majority" | Write concern level | `lexigram-nosql/src/lexigram/nosql/config.py:MongoDBConfig.mongodb.write_concern_w` |

### `lexigram-notification`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_NOTIFICATION__INBOX__MARK_READ_ON_FETCH` | bool | False | Automatically mark messages as read when fetched. | `lexigram-notification/src/lexigram/notification/config.py:InboxConfig.mark_read_on_fetch` |
| `LEX_NOTIFICATION__INBOX__MAX_PAGE_SIZE` | int | 50 | Maximum messages returned per page. | `lexigram-notification/src/lexigram/notification/config.py:InboxConfig.max_page_size` |
| `LEX_NOTIFICATION__INBOX__RETENTION_DAYS` | int | 30 | Days to retain inbox messages before pruning. | `lexigram-notification/src/lexigram/notification/config.py:InboxConfig.retention_days` |
| `LEX_NOTIFICATION__INBOX__STORE_BACKEND` | str | "database" | Storage backend. One of 'database' or 'memory'. | `lexigram-notification/src/lexigram/notification/config.py:InboxConfig.store_backend` |
| `LEX_NOTIFICATION__MAILER__BACKENDS` | list[NamedMailerConfig] | (required) | Named mailer backends for multi-backend support. When non-empty, the provider registers each backend under Annotated[Mai | `lexigram-notification/src/lexigram/notification/config.py:MailerConfig.backends` |
| `LEX_NOTIFICATION__MAILER__CONSOLE_FALLBACK` | bool | True | When no backends are configured, bind a ConsoleMailer as the default MailerProtocol so emails are logged to the applicat | `lexigram-notification/src/lexigram/notification/config.py:MailerConfig.console_fallback` |
| `LEX_NOTIFICATION__PUSH_BACKENDS` | list[NamedPushConfig] | (required) | Named push notification backends for multi-backend support. When non-empty, the provider registers each backend under An | `lexigram-notification/src/lexigram/notification/config.py:NotificationConfig.push_backends` |
| `LEX_NOTIFICATION__SMS_BACKENDS` | list[NamedSMSConfig] | (required) | Named SMS backends for multi-backend support. When non-empty, the provider registers each backend under Annotated[SMSCha | `lexigram-notification/src/lexigram/notification/config.py:NotificationConfig.sms_backends` |

### `lexigram-resilience`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_RESILIENCE__BULKHEAD__MAX_CONCURRENT` | int | 10 | Max concurrent requests | `lexigram-resilience/src/lexigram/resilience/config.py:BulkheadConfig.bulkhead.max_concurrent` |
| `LEX_RESILIENCE__BULKHEAD__NAME` | str | "" | Bulkhead name | `lexigram-resilience/src/lexigram/resilience/config.py:BulkheadConfig.bulkhead.name` |
| `LEX_RESILIENCE__BULKHEAD__QUEUE_SIZE` | int | 100 | Max queue size | `lexigram-resilience/src/lexigram/resilience/config.py:BulkheadConfig.bulkhead.queue_size` |
| `LEX_RESILIENCE__BULKHEAD__TIMEOUT` | float | 30.0 | Execution timeout | `lexigram-resilience/src/lexigram/resilience/config.py:BulkheadConfig.bulkhead.timeout` |
| `LEX_RESILIENCE__CIRCUIT_BREAKER` | CircuitBreakerConfig | field(...) |  | `lexigram-resilience/src/lexigram/resilience/config.py:ResilienceConfig.circuit_breaker` |
| `LEX_RESILIENCE__IDEMPOTENCY__AUTO_CLEANUP` | bool | True | Start background cleanup task on init. | `lexigram-resilience/src/lexigram/resilience/config.py:IdempotencyConfig.auto_cleanup` |
| `LEX_RESILIENCE__IDEMPOTENCY__CLEANUP_INTERVAL` | float | 300.0 | Seconds between background cleanup sweeps. | `lexigram-resilience/src/lexigram/resilience/config.py:IdempotencyConfig.cleanup_interval` |
| `LEX_RESILIENCE__IDEMPOTENCY__KEY_PREFIX` | str | "idempotency:" | Prefix for all keys in backing stores. | `lexigram-resilience/src/lexigram/resilience/config.py:IdempotencyConfig.key_prefix` |
| `LEX_RESILIENCE__IDEMPOTENCY__MAX_ENTRIES` | int | 10000 | Maximum in-memory entries before FIFO eviction. | `lexigram-resilience/src/lexigram/resilience/config.py:IdempotencyConfig.max_entries` |
| `LEX_RESILIENCE__IDEMPOTENCY__MAX_KEY_LENGTH` | int | 512 | Maximum allowed idempotency key length. | `lexigram-resilience/src/lexigram/resilience/config.py:IdempotencyConfig.max_key_length` |
| `LEX_RESILIENCE__IDEMPOTENCY__TTL` | int | 3600 | TTL for cached results in seconds. | `lexigram-resilience/src/lexigram/resilience/config.py:IdempotencyConfig.ttl` |
| `LEX_RESILIENCE__RETRY` | RetryConfig | field(...) |  | `lexigram-resilience/src/lexigram/resilience/config.py:ResilienceConfig.retry` |
| `LEX_RESILIENCE__TIMEOUT` | TimeoutConfig | field(...) |  | `lexigram-resilience/src/lexigram/resilience/config.py:ResilienceConfig.timeout` |

### `lexigram-search`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_SEARCH__BACKENDS` | list[NamedSearchConfig] | (required) | Named search backends for multi-backend support. When non-empty, the provider registers each backend under Annotated[Sea | `lexigram-search/src/lexigram/search/config.py:SearchConfig.backends` |
| `LEX_SEARCH__DATABASE` | str  \| None | None | Named database to use for DB-backed backends (postgres/mysql). References a named database registered via Annotated[Data | `lexigram-search/src/lexigram/search/config.py:SearchConfig.database` |
| `LEX_SEARCH__ELASTICSEARCH__API_KEY` | SecretStr  \| None | None |  | `lexigram-search/src/lexigram/search/config.py:ElasticsearchConfig.elasticsearch.api_key` |
| `LEX_SEARCH__ELASTICSEARCH__HOSTS` | list[str] | (required) | Elasticsearch hosts | `lexigram-search/src/lexigram/search/config.py:ElasticsearchConfig.elasticsearch.hosts` |
| `LEX_SEARCH__ELASTICSEARCH__INDEX_PREFIX` | str | "lexigram_search_" |  | `lexigram-search/src/lexigram/search/config.py:ElasticsearchConfig.elasticsearch.index_prefix` |
| `LEX_SEARCH__ELASTICSEARCH__NUMBER_OF_REPLICAS` | int | 0 |  | `lexigram-search/src/lexigram/search/config.py:ElasticsearchConfig.elasticsearch.number_of_replicas` |
| `LEX_SEARCH__ELASTICSEARCH__NUMBER_OF_SHARDS` | int | 1 |  | `lexigram-search/src/lexigram/search/config.py:ElasticsearchConfig.elasticsearch.number_of_shards` |
| `LEX_SEARCH__ELASTICSEARCH__PASSWORD` | SecretStr  \| None | None |  | `lexigram-search/src/lexigram/search/config.py:ElasticsearchConfig.elasticsearch.password` |
| `LEX_SEARCH__ELASTICSEARCH__USERNAME` | str  \| None | None |  | `lexigram-search/src/lexigram/search/config.py:ElasticsearchConfig.elasticsearch.username` |
| `LEX_SEARCH__ELASTICSEARCH__USE_SSL` | bool | False |  | `lexigram-search/src/lexigram/search/config.py:ElasticsearchConfig.elasticsearch.use_ssl` |
| `LEX_SEARCH__ELASTICSEARCH__VERIFY_CERTS` | bool | True |  | `lexigram-search/src/lexigram/search/config.py:ElasticsearchConfig.elasticsearch.verify_certs` |
| `LEX_SEARCH__ENABLED` | bool | True | Enable the search subsystem | `lexigram-search/src/lexigram/search/config.py:SearchConfig.enabled` |
| `LEX_SEARCH__MEILISEARCH__API_KEY` | SecretStr  \| None | None | MeiliSearch API key | `lexigram-search/src/lexigram/search/config.py:MeiliSearchConfig.meilisearch.api_key` |
| `LEX_SEARCH__MEILISEARCH__DISPLAYED_ATTRIBUTES` | list[str] | (required) | Fields to return in results | `lexigram-search/src/lexigram/search/config.py:MeiliSearchConfig.meilisearch.displayed_attributes` |
| `LEX_SEARCH__MEILISEARCH__FILTERABLE_ATTRIBUTES` | list[str] | (required) | Attributes that can be filtered | `lexigram-search/src/lexigram/search/config.py:MeiliSearchConfig.meilisearch.filterable_attributes` |
| `LEX_SEARCH__MEILISEARCH__MAX_CONNECTIONS` | int | 10 | Maximum number of connections | `lexigram-search/src/lexigram/search/config.py:MeiliSearchConfig.meilisearch.max_connections` |
| `LEX_SEARCH__MEILISEARCH__MIN_WORD_SIZE_FOR_TYPOS` | dict[str, int] | (required) | Minimum word size for typo tolerance | `lexigram-search/src/lexigram/search/config.py:MeiliSearchConfig.meilisearch.min_word_size_for_typos` |
| `LEX_SEARCH__MEILISEARCH__RANKING_RULES` | list[str] | (required) | Ranking rules in order | `lexigram-search/src/lexigram/search/config.py:MeiliSearchConfig.meilisearch.ranking_rules` |
| `LEX_SEARCH__MEILISEARCH__SEARCHABLE_ATTRIBUTES` | list[str] | (required) | Fields to search in | `lexigram-search/src/lexigram/search/config.py:MeiliSearchConfig.meilisearch.searchable_attributes` |
| `LEX_SEARCH__MEILISEARCH__SORTABLE_ATTRIBUTES` | list[str] | (required) | Attributes that can be sorted | `lexigram-search/src/lexigram/search/config.py:MeiliSearchConfig.meilisearch.sortable_attributes` |
| `LEX_SEARCH__MEILISEARCH__TIMEOUT` | int | 30 | Request timeout in seconds | `lexigram-search/src/lexigram/search/config.py:MeiliSearchConfig.meilisearch.timeout` |
| `LEX_SEARCH__MEILISEARCH__TYPO_TOLERANCE_ENABLED` | bool | True | Enable typo tolerance | `lexigram-search/src/lexigram/search/config.py:MeiliSearchConfig.meilisearch.typo_tolerance_enabled` |
| `LEX_SEARCH__MEILISEARCH__URL` | str | "http://localhost:7700" | MeiliSearch server URL | `lexigram-search/src/lexigram/search/config.py:MeiliSearchConfig.meilisearch.url` |
| `LEX_SEARCH__MONGO__CONNECTION_STRING` | SecretStr | SecretStr(...) |  | `lexigram-search/src/lexigram/search/config.py:MongoSearchConfig.mongo.connection_string` |
| `LEX_SEARCH__MONGO__DATABASE_NAME` | str | "search" |  | `lexigram-search/src/lexigram/search/config.py:MongoSearchConfig.mongo.database_name` |
| `LEX_SEARCH__MONGO__USE_ATLAS_SEARCH` | bool | False |  | `lexigram-search/src/lexigram/search/config.py:MongoSearchConfig.mongo.use_atlas_search` |
| `LEX_SEARCH__MYSQL__CONNECTION_STRING` | SecretStr | SecretStr(...) |  | `lexigram-search/src/lexigram/search/config.py:MySQLSearchConfig.mysql.connection_string` |
| `LEX_SEARCH__MYSQL__FULLTEXT_MODE` | str | "natural_language" |  | `lexigram-search/src/lexigram/search/config.py:MySQLSearchConfig.mysql.fulltext_mode` |
| `LEX_SEARCH__MYSQL__MIN_WORD_LENGTH` | int | 3 |  | `lexigram-search/src/lexigram/search/config.py:MySQLSearchConfig.mysql.min_word_length` |
| `LEX_SEARCH__OPENSEARCH__HOSTS` | list[str] | (required) | OpenSearch hosts | `lexigram-search/src/lexigram/search/config.py:OpenSearchConfig.opensearch.hosts` |
| `LEX_SEARCH__OPENSEARCH__INDEX_PREFIX` | str | "lexigram_search_" |  | `lexigram-search/src/lexigram/search/config.py:OpenSearchConfig.opensearch.index_prefix` |
| `LEX_SEARCH__OPENSEARCH__PASSWORD` | str  \| None | None |  | `lexigram-search/src/lexigram/search/config.py:OpenSearchConfig.opensearch.password` |
| `LEX_SEARCH__OPENSEARCH__TIMEOUT` | int | 30 |  | `lexigram-search/src/lexigram/search/config.py:OpenSearchConfig.opensearch.timeout` |
| `LEX_SEARCH__OPENSEARCH__USERNAME` | str  \| None | None |  | `lexigram-search/src/lexigram/search/config.py:OpenSearchConfig.opensearch.username` |
| `LEX_SEARCH__OPENSEARCH__USE_SSL` | bool | False |  | `lexigram-search/src/lexigram/search/config.py:OpenSearchConfig.opensearch.use_ssl` |
| `LEX_SEARCH__OPENSEARCH__VERIFY_SSL` | bool | True |  | `lexigram-search/src/lexigram/search/config.py:OpenSearchConfig.opensearch.verify_ssl` |
| `LEX_SEARCH__OPERATIONS__BULK_CHUNK_SIZE` | int | 500 | Bulk request chunk size | `lexigram-search/src/lexigram/search/config.py:SearchOperationsConfig.operations.bulk_chunk_size` |
| `LEX_SEARCH__OPERATIONS__MAX_RETRIES` | int | 3 | Max retry attempts | `lexigram-search/src/lexigram/search/config.py:SearchOperationsConfig.operations.max_retries` |
| `LEX_SEARCH__OPERATIONS__REQUEST_TIMEOUT` | float | 30.0 | Request timeout seconds | `lexigram-search/src/lexigram/search/config.py:SearchOperationsConfig.operations.request_timeout` |
| `LEX_SEARCH__OPERATIONS__RETRY_BACKOFF` | float | 0.5 | Retry backoff multiplier | `lexigram-search/src/lexigram/search/config.py:SearchOperationsConfig.operations.retry_backoff` |
| `LEX_SEARCH__POSTGRES__AUTO_CREATE_TABLES` | bool | True |  | `lexigram-search/src/lexigram/search/config.py:PostgresSearchConfig.postgres.auto_create_tables` |
| `LEX_SEARCH__POSTGRES__CONNECTION_STRING` | SecretStr | SecretStr(...) | PostgreSQL connection string | `lexigram-search/src/lexigram/search/config.py:PostgresSearchConfig.postgres.connection_string` |
| `LEX_SEARCH__POSTGRES__ENABLE_TRIGRAM` | bool | True | Enable pg_trgm fuzzy matching | `lexigram-search/src/lexigram/search/config.py:PostgresSearchConfig.postgres.enable_trigram` |
| `LEX_SEARCH__POSTGRES__TEXT_SEARCH_CONFIG` | str | "english" | PostgreSQL text search config | `lexigram-search/src/lexigram/search/config.py:PostgresSearchConfig.postgres.text_search_config` |
| `LEX_SEARCH__QUERY__DEFAULT_LIMIT` | int | (complex) |  | `lexigram-search/src/lexigram/search/config.py:QueryConfig.query.default_limit` |
| `LEX_SEARCH__QUERY__ENABLE_AGGREGATIONS` | bool | False |  | `lexigram-search/src/lexigram/search/config.py:QueryConfig.query.enable_aggregations` |
| `LEX_SEARCH__QUERY__ENABLE_FACETING` | bool | True |  | `lexigram-search/src/lexigram/search/config.py:QueryConfig.query.enable_faceting` |
| `LEX_SEARCH__QUERY__ENABLE_HIGHLIGHTING` | bool | True |  | `lexigram-search/src/lexigram/search/config.py:QueryConfig.query.enable_highlighting` |
| `LEX_SEARCH__QUERY__FUZZY_THRESHOLD` | float | 0.8 |  | `lexigram-search/src/lexigram/search/config.py:QueryConfig.query.fuzzy_threshold` |
| `LEX_SEARCH__QUERY__MAX_LIMIT` | int | (complex) |  | `lexigram-search/src/lexigram/search/config.py:QueryConfig.query.max_limit` |
| `LEX_SEARCH__QUERY__STRATEGY` | str | "fuzzy" |  | `lexigram-search/src/lexigram/search/config.py:QueryConfig.query.strategy` |
| `LEX_SEARCH__SQLITE__AUTO_CREATE_TABLES` | bool | True |  | `lexigram-search/src/lexigram/search/config.py:SQLiteSearchConfig.sqlite.auto_create_tables` |
| `LEX_SEARCH__SQLITE__DB_PATH` | str | ":memory:" |  | `lexigram-search/src/lexigram/search/config.py:SQLiteSearchConfig.sqlite.db_path` |
| `LEX_SEARCH__SQLITE__TOKENIZER` | str | "porter unicode61" |  | `lexigram-search/src/lexigram/search/config.py:SQLiteSearchConfig.sqlite.tokenizer` |
| `LEX_SEARCH__TIMEOUT` | float | 30.0 | Default request timeout seconds | `lexigram-search/src/lexigram/search/config.py:SearchConfig.timeout` |
| `LEX_SEARCH__TYPESENSE__API_KEY` | SecretStr  \| None | None | Typesense API key | `lexigram-search/src/lexigram/search/config.py:TypesenseConfig.typesense.api_key` |
| `LEX_SEARCH__TYPESENSE__CONNECTION_TIMEOUT` | int | 30 | Connection timeout | `lexigram-search/src/lexigram/search/config.py:TypesenseConfig.typesense.connection_timeout` |
| `LEX_SEARCH__TYPESENSE__HEALTH_CHECK_INTERVAL` | int | 60 | Health check interval | `lexigram-search/src/lexigram/search/config.py:TypesenseConfig.typesense.health_check_interval` |
| `LEX_SEARCH__TYPESENSE__NODES` | list[dict[str, str]] | (required) | Typesense node connections | `lexigram-search/src/lexigram/search/config.py:TypesenseConfig.typesense.nodes` |

### `lexigram-sql`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_SQL__AUDIT_HMAC_KEY` | str  \| None | None | HMAC key for audit checksum signing. Plain text or base64. | `lexigram-sql/src/lexigram/sql/config.py:DatabaseConfig.audit_hmac_key` |
| `LEX_SQL__BACKENDS` | list[NamedDatabaseConfig] | (required) | Multi-database backends list. When non-empty, drives multi-DB mode. The entry with primary=True (or the first entry) als | `lexigram-sql/src/lexigram/sql/config.py:DatabaseConfig.backends` |
| `LEX_SQL__BACKEND__URL` | SecretStr | Ellipsis | Database connection URL (may contain credentials) | `lexigram-sql/src/lexigram/sql/config.py:DatabaseBackendConfig.backend.url` |
| `LEX_SQL__ENABLED` | bool | True |  | `lexigram-sql/src/lexigram/sql/config.py:DatabaseConfig.enabled` |
| `LEX_SQL__MIGRATIONS__LOCK_TIMEOUT` | Duration | Duration.seconds(...) |  | `lexigram-sql/src/lexigram/sql/config.py:DatabaseMigrationConfig.migrations.lock_timeout` |
| `LEX_SQL__NAME` | str | "database" |  | `lexigram-sql/src/lexigram/sql/config.py:DatabaseConfig.name` |
| `LEX_SQL__OPERATIONS__ECHO` | bool | False |  | `lexigram-sql/src/lexigram/sql/config.py:DatabaseOperationConfig.operations.echo` |
| `LEX_SQL__OPERATIONS__STATEMENT_TIMEOUT` | Duration | Duration.seconds(...) |  | `lexigram-sql/src/lexigram/sql/config.py:DatabaseOperationConfig.operations.statement_timeout` |
| `LEX_SQL__OUTBOX__BATCH_MAX_AGE` | Duration | Duration.seconds(...) |  | `lexigram-sql/src/lexigram/sql/config.py:DatabaseOutboxConfig.outbox.batch_max_age` |
| `LEX_SQL__OUTBOX__ENABLED` | bool | True |  | `lexigram-sql/src/lexigram/sql/config.py:DatabaseOutboxConfig.outbox.enabled` |
| `LEX_SQL__OUTBOX__POLL_INTERVAL` | Duration | Duration.seconds(...) |  | `lexigram-sql/src/lexigram/sql/config.py:DatabaseOutboxConfig.outbox.poll_interval` |
| `LEX_SQL__POOL__ACQUIRE_TIMEOUT` | Duration | Duration.seconds(...) |  | `lexigram-sql/src/lexigram/sql/config.py:DatabasePoolConfig.pool.acquire_timeout` |
| `LEX_SQL__POOL__IDLE_TIMEOUT` | Duration | Duration.minutes(...) |  | `lexigram-sql/src/lexigram/sql/config.py:DatabasePoolConfig.pool.idle_timeout` |
| `LEX_SQL__POOL__MAX_LIFETIME` | Duration | Duration.hours(...) |  | `lexigram-sql/src/lexigram/sql/config.py:DatabasePoolConfig.pool.max_lifetime` |
| `LEX_SQL__POOL__MAX_OVERFLOW` | int | 5 |  | `lexigram-sql/src/lexigram/sql/config.py:DatabasePoolConfig.pool.max_overflow` |
| `LEX_SQL__POOL__MAX_SIZE` | int | (complex) |  | `lexigram-sql/src/lexigram/sql/config.py:DatabasePoolConfig.pool.max_size` |
| `LEX_SQL__POOL__MIN_SIZE` | int | (complex) |  | `lexigram-sql/src/lexigram/sql/config.py:DatabasePoolConfig.pool.min_size` |
| `LEX_SQL__POOL__RECYCLE` | int | 3600 |  | `lexigram-sql/src/lexigram/sql/config.py:DatabasePoolConfig.pool.recycle` |
| `LEX_SQL__POOL__TIMEOUT` | float | (complex) |  | `lexigram-sql/src/lexigram/sql/config.py:DatabasePoolConfig.pool.timeout` |

### `lexigram-storage`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_STORAGE__BACKENDS` | list[NamedStorageConfig] | (required) | Named storage backends for multi-store support. When non-empty, the provider registers each backend under Annotated[Blob | `lexigram-storage/src/lexigram/storage/config.py:StorageConfig.backends` |
| `LEX_STORAGE__DEFAULT_DRIVER` | Literal['local', 's3', 'gcs', 'azure', 'memory', 'r2'] | (complex) | Default storage driver to use | `lexigram-storage/src/lexigram/storage/config.py:StorageConfig.default_driver` |
| `LEX_STORAGE__DRIVERS` | dict[str, StorageLocalConfig  \| StorageS3Config  \| StorageGCSConfig  \| Storag | (required) | Driver-specific configurations | `lexigram-storage/src/lexigram/storage/config.py:StorageConfig.drivers` |
| `LEX_STORAGE__ENABLED` | bool | True |  | `lexigram-storage/src/lexigram/storage/config.py:StorageConfig.enabled` |
| `LEX_STORAGE__ENV` | str  \| None | None | Environment (development/staging/production) | `lexigram-storage/src/lexigram/storage/config.py:StorageConfig.env` |
| `LEX_STORAGE__HEALTH_CHECK_TIMEOUT` | float | 5.0 | Timeout in seconds for the startup health check in StorageProvider.boot() | `lexigram-storage/src/lexigram/storage/config.py:StorageConfig.health_check_timeout` |
| `LEX_STORAGE__NAME` | str | "storage" |  | `lexigram-storage/src/lexigram/storage/config.py:StorageConfig.name` |
| `LEX_STORAGE__SERVICE__ALLOWED_MIME_TYPES` | list[str] | (required) | Allowed MIME types for upload validation. Defaults to a safe set of common image types: ['image/jpeg', 'image/png', 'ima | `lexigram-storage/src/lexigram/storage/config.py:StorageOperationConfig.service.allowed_mime_types` |
| `LEX_STORAGE__SERVICE__MAX_FILE_SIZE_MB` | int | (complex) | Maximum file size in MB | `lexigram-storage/src/lexigram/storage/config.py:StorageOperationConfig.service.max_file_size_mb` |

### `lexigram-tasks`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_TASKS__BACKENDS` | list[NamedTaskConfig] | (required) | Named task queue backends for multi-queue support. When non-empty, the provider registers each backend under Annotated[T | `lexigram-tasks/src/lexigram/tasks/config.py:TaskConfig.backends` |
| `LEX_TASKS__BACKEND__AMQP_URL` | SecretStr | SecretStr(...) | AMQP connection URL (may contain credentials). | `lexigram-tasks/src/lexigram/tasks/config.py:TaskBackendConfig.backend.amqp_url` |
| `LEX_TASKS__BACKEND__POSTGRES_DSN` | SecretStr  \| None | None | Postgres DSN (required when type="postgres"; may contain credentials). | `lexigram-tasks/src/lexigram/tasks/config.py:TaskBackendConfig.backend.postgres_dsn` |
| `LEX_TASKS__BACKEND__QUEUE_NAME` | str | (complex) | Name of the task queue | `lexigram-tasks/src/lexigram/tasks/config.py:TaskBackendConfig.backend.queue_name` |
| `LEX_TASKS__BACKEND__REDIS_URL` | SecretStr | SecretStr(...) | Redis connection URL (may contain credentials). | `lexigram-tasks/src/lexigram/tasks/config.py:TaskBackendConfig.backend.redis_url` |
| `LEX_TASKS__BACKEND__TYPE` | str | (complex) | Queue backend type | `lexigram-tasks/src/lexigram/tasks/config.py:TaskBackendConfig.backend.type` |
| `LEX_TASKS__ENABLED` | bool | True | Whether tasks module is enabled | `lexigram-tasks/src/lexigram/tasks/config.py:TaskConfig.enabled` |
| `LEX_TASKS__ENV` | str  \| None | None | Environment (development/staging/production) | `lexigram-tasks/src/lexigram/tasks/config.py:TaskConfig.env` |
| `LEX_TASKS__EXTRA` | dict[str, Any] | (required) |  | `lexigram-tasks/src/lexigram/tasks/config.py:TaskConfig.extra` |
| `LEX_TASKS__NAME` | str | "tasks" | Configuration name | `lexigram-tasks/src/lexigram/tasks/config.py:TaskConfig.name` |
| `LEX_TASKS__RATE_LIMIT__BURST` | int  \| None | None | Maximum burst size | `lexigram-tasks/src/lexigram/tasks/config.py:TaskRateLimitConfig.rate_limit.burst` |
| `LEX_TASKS__RATE_LIMIT__ENABLED` | bool | False | Whether rate limiting is enabled | `lexigram-tasks/src/lexigram/tasks/config.py:TaskRateLimitConfig.rate_limit.enabled` |
| `LEX_TASKS__RATE_LIMIT__PER` | float | 1.0 | Time period in seconds | `lexigram-tasks/src/lexigram/tasks/config.py:TaskRateLimitConfig.rate_limit.per` |
| `LEX_TASKS__RATE_LIMIT__RATE` | int | 100 | Number of tasks allowed per time period | `lexigram-tasks/src/lexigram/tasks/config.py:TaskRateLimitConfig.rate_limit.rate` |
| `LEX_TASKS__RETRY` | RetryConfig | (required) |  | `lexigram-tasks/src/lexigram/tasks/config.py:TaskConfig.retry` |
| `LEX_TASKS__SCHEDULER__CHECK_INTERVAL` | float | (complex) | Interval between schedule checks (seconds) | `lexigram-tasks/src/lexigram/tasks/config.py:TaskSchedulerConfig.scheduler.check_interval` |
| `LEX_TASKS__SCHEDULER__ENABLED` | bool | True | Whether scheduling is enabled | `lexigram-tasks/src/lexigram/tasks/config.py:TaskSchedulerConfig.scheduler.enabled` |
| `LEX_TASKS__SCHEDULER__TIMEZONE` | str | (complex) | Timezone for cron expressions | `lexigram-tasks/src/lexigram/tasks/config.py:TaskSchedulerConfig.scheduler.timezone` |
| `LEX_TASKS__TIMEOUT__DEFAULT_TIMEOUT` | float | (complex) | Default timeout | `lexigram-tasks/src/lexigram/tasks/config.py:TaskTimeoutConfig.timeout.default_timeout` |
| `LEX_TASKS__TIMEOUT__ENFORCE_TIMEOUT` | bool | True | Enforce timeouts | `lexigram-tasks/src/lexigram/tasks/config.py:TaskTimeoutConfig.timeout.enforce_timeout` |
| `LEX_TASKS__TIMEOUT__MAX_TIMEOUT` | float | (complex) | Maximum allowed timeout | `lexigram-tasks/src/lexigram/tasks/config.py:TaskTimeoutConfig.timeout.max_timeout` |
| `LEX_TASKS__WORKER__DEFAULT_TIMEOUT` | float | (complex) | Default timeout for tasks without an explicit timeout (seconds) | `lexigram-tasks/src/lexigram/tasks/config.py:TaskWorkerConfig.worker.default_timeout` |
| `LEX_TASKS__WORKER__ENFORCE_TIMEOUT` | bool | True | Whether to enforce timeouts on all tasks | `lexigram-tasks/src/lexigram/tasks/config.py:TaskWorkerConfig.worker.enforce_timeout` |
| `LEX_TASKS__WORKER__MAX_CONCURRENT_TASKS` | int | (complex) | Maximum concurrent tasks per worker | `lexigram-tasks/src/lexigram/tasks/config.py:TaskWorkerConfig.worker.max_concurrent_tasks` |
| `LEX_TASKS__WORKER__MAX_TIMEOUT` | float | (complex) | Maximum allowed timeout for any task (seconds) | `lexigram-tasks/src/lexigram/tasks/config.py:TaskWorkerConfig.worker.max_timeout` |
| `LEX_TASKS__WORKER__POLL_INTERVAL` | float | (complex) | Interval between queue polls (seconds) | `lexigram-tasks/src/lexigram/tasks/config.py:TaskWorkerConfig.worker.poll_interval` |
| `LEX_TASKS__WORKER__SHUTDOWN_TIMEOUT` | float | (complex) | Timeout for graceful shutdown (seconds) | `lexigram-tasks/src/lexigram/tasks/config.py:TaskWorkerConfig.worker.shutdown_timeout` |
| `LEX_TASKS__WORKER__WORKER_COUNT` | int | (complex) | Number of worker instances | `lexigram-tasks/src/lexigram/tasks/config.py:TaskWorkerConfig.worker.worker_count` |

### `lexigram-tenancy`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_TENANCY__INTEGRATION__CACHE_KEY_PREFIX` | bool | True |  | `lexigram-tenancy/src/lexigram/tenancy/config.py:IntegrationConfig.integration.cache_key_prefix` |
| `LEX_TENANCY__INTEGRATION__SQL_CONTEXT_BRIDGE` | bool | True |  | `lexigram-tenancy/src/lexigram/tenancy/config.py:IntegrationConfig.integration.sql_context_bridge` |
| `LEX_TENANCY__LIFECYCLE__AUTO_PROVISION_ISOLATION` | bool | True |  | `lexigram-tenancy/src/lexigram/tenancy/config.py:LifecycleConfig.lifecycle.auto_provision_isolation` |
| `LEX_TENANCY__LIFECYCLE__ISOLATION_STRATEGY` | str | "row_level" |  | `lexigram-tenancy/src/lexigram/tenancy/config.py:LifecycleConfig.lifecycle.isolation_strategy` |
| `LEX_TENANCY__OVERRIDES__CACHE_TTL` | int | DEFAULT_CONFIG_CACHE_TTL |  | `lexigram-tenancy/src/lexigram/tenancy/config.py:ConfigOverridesConfig.overrides.cache_ttl` |
| `LEX_TENANCY__RESOLUTION__HEADER_NAME` | str | DEFAULT_HEADER_NAME |  | `lexigram-tenancy/src/lexigram/tenancy/config.py:ResolutionConfig.resolution.header_name` |
| `LEX_TENANCY__RESOLUTION__JWT_CLAIM_KEY` | str | DEFAULT_JWT_CLAIM_KEY |  | `lexigram-tenancy/src/lexigram/tenancy/config.py:ResolutionConfig.resolution.jwt_claim_key` |
| `LEX_TENANCY__RESOLUTION__PATH_PATTERN` | str  \| None | DEFAULT_PATH_PATTERN |  | `lexigram-tenancy/src/lexigram/tenancy/config.py:ResolutionConfig.resolution.path_pattern` |
| `LEX_TENANCY__RESOLUTION__RESOLVERS` | list[str] | field(...) |  | `lexigram-tenancy/src/lexigram/tenancy/config.py:ResolutionConfig.resolution.resolvers` |
| `LEX_TENANCY__RESOLUTION__STRICT_MEMBERSHIP` | bool | True |  | `lexigram-tenancy/src/lexigram/tenancy/config.py:ResolutionConfig.resolution.strict_membership` |
| `LEX_TENANCY__RESOLUTION__SUBDOMAIN_PATTERN` | str  \| None | None |  | `lexigram-tenancy/src/lexigram/tenancy/config.py:ResolutionConfig.resolution.subdomain_pattern` |
| `LEX_TENANCY__RESOLUTION__TRUSTED_RESOLVERS` | list[str] | field(...) |  | `lexigram-tenancy/src/lexigram/tenancy/config.py:ResolutionConfig.resolution.trusted_resolvers` |
| `LEX_TENANCY__RESOLUTION__VALIDATOR_CACHE_TTL` | int | DEFAULT_VALIDATOR_CACHE_TTL |  | `lexigram-tenancy/src/lexigram/tenancy/config.py:ResolutionConfig.resolution.validator_cache_ttl` |

### `lexigram-testing`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_TESTING__CLEANUP_TEMP_FILES` | bool | True | Clean up temporary files after tests | `lexigram-testing/src/lexigram/testing/config.py:TestingConfig.cleanup_temp_files` |
| `LEX_TESTING__DB_REUSE` | bool | True | Reuse test databases between tests | `lexigram-testing/src/lexigram/testing/config.py:TestingConfig.db_reuse` |
| `LEX_TESTING__ENABLED` | bool | True |  | `lexigram-testing/src/lexigram/testing/config.py:TestingConfig.enabled` |
| `LEX_TESTING__MOCK_EXTERNAL_SERVICES` | bool | True | Mock external service calls | `lexigram-testing/src/lexigram/testing/config.py:TestingConfig.mock_external_services` |

### `lexigram-ui`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_UI__AUTO_ESCAPE` | bool | True | HTML-escape user strings by default. | `lexigram-ui/src/lexigram/ui/config.py:UIConfig.auto_escape` |
| `LEX_UI__DEBUG_COMPONENTS` | bool | False | Render data-component debug attributes. | `lexigram-ui/src/lexigram/ui/config.py:UIConfig.debug_components` |
| `LEX_UI__DEFAULT_THEME` | str | "default" | Default CSS theme name. | `lexigram-ui/src/lexigram/ui/config.py:UIConfig.default_theme` |
| `LEX_UI__ENABLE_REALTIME` | bool | False | Enable realtime update features. | `lexigram-ui/src/lexigram/ui/config.py:UIConfig.enable_realtime` |
| `LEX_UI__ENABLE_SSE` | bool | False | Enable Server-Sent Events support. | `lexigram-ui/src/lexigram/ui/config.py:UIConfig.enable_sse` |
| `LEX_UI__HTMX_VERSION` | str | "2.0.4" | HTMX CDN version. | `lexigram-ui/src/lexigram/ui/config.py:UIConfig.htmx_version` |
| `LEX_UI__THEME` | str | "light" | Active UI theme. | `lexigram-ui/src/lexigram/ui/config.py:UIConfig.theme` |

### `lexigram-vector`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_VECTOR__BACKEND` | str | (complex) | Vector store backend to use | `lexigram-vector/src/lexigram/vector/config.py:VectorConfig.backend` |
| `LEX_VECTOR__BACKENDS` | list[NamedVectorConfig] | (required) | Named vector store backends for multi-store support. When non-empty, the provider registers each backend under Annotated | `lexigram-vector/src/lexigram/vector/config.py:VectorConfig.backends` |
| `LEX_VECTOR__CACHE_TTL` | int | 86400 | Cache TTL in seconds (default: 24 hours) | `lexigram-vector/src/lexigram/vector/config.py:VectorConfig.cache_ttl` |
| `LEX_VECTOR__COLLECTION_NAME` | str | "default" | Default collection name for AI-layer operations | `lexigram-vector/src/lexigram/vector/config.py:VectorConfig.collection_name` |
| `LEX_VECTOR__DEFAULT_DIMENSION` | int | 1536 | Default vector dimension | `lexigram-vector/src/lexigram/vector/config.py:VectorConfig.default_dimension` |
| `LEX_VECTOR__DEFAULT_DISTANCE_METRIC` | DistanceMetric | (complex) | Default distance metric for new collections | `lexigram-vector/src/lexigram/vector/config.py:VectorConfig.default_distance_metric` |
| `LEX_VECTOR__DEFAULT_INDEX_TYPE` | IndexType | (complex) | Default index type for new collections | `lexigram-vector/src/lexigram/vector/config.py:VectorConfig.default_index_type` |
| `LEX_VECTOR__EMBEDDING_MODEL` | str | "text-embedding-3-small" | Embedding model name for AI-layer embedding generation | `lexigram-vector/src/lexigram/vector/config.py:VectorConfig.embedding_model` |
| `LEX_VECTOR__EMBEDDING__API_BASE` | str | "http://fastembed" | Base URL of the embedding API. The client appends '/embeddings' to this URL. | `lexigram-vector/src/lexigram/vector/embedding/config.py:EmbeddingClientConfig.api_base` |
| `LEX_VECTOR__EMBEDDING__API_KEY` | str  \| None | None | API key sent as Bearer token (required for OpenAI and most cloud providers). | `lexigram-vector/src/lexigram/vector/embedding/config.py:EmbeddingClientConfig.api_key` |
| `LEX_VECTOR__EMBEDDING__BATCH_SIZE` | int | 64 | Maximum number of texts per embedding API request. | `lexigram-vector/src/lexigram/vector/embedding/config.py:EmbeddingClientConfig.batch_size` |
| `LEX_VECTOR__EMBEDDING__DIMENSION` | int | 768 | Expected output vector dimension. Must match the model (768 for nomic-embed-text-v1.5, 1536 for text-embedding-ada-002). | `lexigram-vector/src/lexigram/vector/embedding/config.py:EmbeddingClientConfig.dimension` |
| `LEX_VECTOR__EMBEDDING__FORMAT` | Literal['openai', 'fastembed', 'cohere'] | "openai" | API payload format. 'openai' uses {'input': [...]}, 'fastembed' uses {'texts': [...]}, 'cohere' uses {'texts': [...]}. | `lexigram-vector/src/lexigram/vector/embedding/config.py:EmbeddingClientConfig.format` |
| `LEX_VECTOR__EMBEDDING__MODEL` | str | "nomic-ai/nomic-embed-text-v1.5" | Embedding model identifier passed to the API. | `lexigram-vector/src/lexigram/vector/embedding/config.py:EmbeddingClientConfig.model` |
| `LEX_VECTOR__EMBEDDING__TIMEOUT` | float | 30.0 | HTTP request timeout in seconds. | `lexigram-vector/src/lexigram/vector/embedding/config.py:EmbeddingClientConfig.timeout` |
| `LEX_VECTOR__ENABLED` | bool | True | Enable the vector store subsystem | `lexigram-vector/src/lexigram/vector/config.py:VectorConfig.enabled` |
| `LEX_VECTOR__ENABLE_CACHE` | bool | False | Enable embedding caching (requires a CacheBackend binding) | `lexigram-vector/src/lexigram/vector/config.py:VectorConfig.enable_cache` |
| `LEX_VECTOR__MAX_RETRIES` | int | (complex) | Maximum number of retries for operations | `lexigram-vector/src/lexigram/vector/config.py:VectorConfig.max_retries` |
| `LEX_VECTOR__MEMORY__MAX_COLLECTIONS` | int | 100 | Maximum number of collections in memory | `lexigram-vector/src/lexigram/vector/config.py:MemoryConfig.memory.max_collections` |
| `LEX_VECTOR__MEMORY__MAX_VECTORS_PER_COLLECTION` | int | 100000 | Maximum number of vectors per collection | `lexigram-vector/src/lexigram/vector/config.py:MemoryConfig.memory.max_vectors_per_collection` |
| `LEX_VECTOR__PGVECTOR__CREATE_EXTENSION` | bool | True | Whether to create pgvector extension if missing | `lexigram-vector/src/lexigram/vector/config.py:PgVectorConfig.pgvector.create_extension` |
| `LEX_VECTOR__PGVECTOR__DATABASE` | str | "primary" | Name of the database backend from db.backends to use for pgvector. Matches a 'name:' entry in the db.backends list. Defa | `lexigram-vector/src/lexigram/vector/config.py:PgVectorConfig.pgvector.database` |
| `LEX_VECTOR__PGVECTOR__DEFAULT_EF_SEARCH` | int | (complex) | Default ef_search for HNSW index | `lexigram-vector/src/lexigram/vector/config.py:PgVectorConfig.pgvector.default_ef_search` |
| `LEX_VECTOR__PGVECTOR__DEFAULT_LISTS` | int | (complex) | Default number of lists for IVFFlat index | `lexigram-vector/src/lexigram/vector/config.py:PgVectorConfig.pgvector.default_lists` |
| `LEX_VECTOR__PGVECTOR__DEFAULT_PROBES` | int | (complex) | Default number of probes for IVFFlat index | `lexigram-vector/src/lexigram/vector/config.py:PgVectorConfig.pgvector.default_probes` |
| `LEX_VECTOR__PGVECTOR__SCHEMA` | str | "public" | Database schema for vector tables | `lexigram-vector/src/lexigram/vector/config.py:PgVectorConfig.pgvector.schema` |
| `LEX_VECTOR__PGVECTOR__TABLE_PREFIX` | str | "vec_" | Prefix for vector storage tables | `lexigram-vector/src/lexigram/vector/config.py:PgVectorConfig.pgvector.table_prefix` |
| `LEX_VECTOR__PINECONE__API_KEY` | SecretStr | SecretStr(...) | Pinecone API key | `lexigram-vector/src/lexigram/vector/config.py:PineconeConfig.pinecone.api_key` |
| `LEX_VECTOR__PINECONE__ENVIRONMENT` | str | "" | Pinecone environment (e.g. 'us-west1-gcp') | `lexigram-vector/src/lexigram/vector/config.py:PineconeConfig.pinecone.environment` |
| `LEX_VECTOR__PINECONE__INDEX_NAME` | str | "" | Name of the Pinecone index | `lexigram-vector/src/lexigram/vector/config.py:PineconeConfig.pinecone.index_name` |
| `LEX_VECTOR__PINECONE__NAMESPACE` | str | "" | Default namespace for the index | `lexigram-vector/src/lexigram/vector/config.py:PineconeConfig.pinecone.namespace` |
| `LEX_VECTOR__PINECONE__POOL_THREADS` | int | 4 | Number of threads for the connection pool | `lexigram-vector/src/lexigram/vector/config.py:PineconeConfig.pinecone.pool_threads` |
| `LEX_VECTOR__PINECONE__TIMEOUT` | float | (complex) | Request timeout in seconds | `lexigram-vector/src/lexigram/vector/config.py:PineconeConfig.pinecone.timeout` |
| `LEX_VECTOR__QDRANT__API_KEY` | SecretStr  \| None | None | Qdrant API key | `lexigram-vector/src/lexigram/vector/config.py:QdrantConfig.qdrant.api_key` |
| `LEX_VECTOR__QDRANT__GRPC_PORT` | int | 6334 | gRPC port for Qdrant | `lexigram-vector/src/lexigram/vector/config.py:QdrantConfig.qdrant.grpc_port` |
| `LEX_VECTOR__QDRANT__PREFER_GRPC` | bool | True | Whether to prefer gRPC over HTTP | `lexigram-vector/src/lexigram/vector/config.py:QdrantConfig.qdrant.prefer_grpc` |
| `LEX_VECTOR__QDRANT__TIMEOUT` | float | (complex) | Request timeout in seconds | `lexigram-vector/src/lexigram/vector/config.py:QdrantConfig.qdrant.timeout` |
| `LEX_VECTOR__QDRANT__URL` | str | "http://localhost:6333" | Qdrant server URL | `lexigram-vector/src/lexigram/vector/config.py:QdrantConfig.qdrant.url` |
| `LEX_VECTOR__RETRY_DELAY` | float | (complex) | Delay between retries in seconds | `lexigram-vector/src/lexigram/vector/config.py:VectorConfig.retry_delay` |
| `LEX_VECTOR__TENANCY__ENABLED` | bool | False | Enable tenant-aware collection name resolution | `lexigram-vector/src/lexigram/vector/config.py:VectorTenancyConfig.tenancy.enabled` |
| `LEX_VECTOR__TENANCY__RESOLVER_KIND` | str | "templated" | Which ``TenantCollectionResolver`` to use. One of ``"templated"`` or ``"pinecone_namespace"``. | `lexigram-vector/src/lexigram/vector/config.py:VectorTenancyConfig.tenancy.resolver_kind` |
| `LEX_VECTOR__UPSERT_BATCH_SIZE` | int | (complex) | Number of vectors per upsert batch | `lexigram-vector/src/lexigram/vector/config.py:VectorConfig.upsert_batch_size` |
| `LEX_VECTOR__WEAVIATE__API_KEY` | SecretStr  \| None | None | Weaviate API key for authenticated clusters | `lexigram-vector/src/lexigram/vector/config.py:WeaviateConfig.weaviate.api_key` |
| `LEX_VECTOR__WEAVIATE__GRPC_PORT` | int | 50051 | gRPC port for the Weaviate cluster | `lexigram-vector/src/lexigram/vector/config.py:WeaviateConfig.weaviate.grpc_port` |
| `LEX_VECTOR__WEAVIATE__TIMEOUT` | float | (complex) | Request timeout in seconds | `lexigram-vector/src/lexigram/vector/config.py:WeaviateConfig.weaviate.timeout` |
| `LEX_VECTOR__WEAVIATE__URL` | str | "http://localhost:8080" | Weaviate cluster URL (HTTP) | `lexigram-vector/src/lexigram/vector/config.py:WeaviateConfig.weaviate.url` |

### `lexigram-web`

| Env Var | Type | Default | Description | Source |
|---------|------|---------|-------------|--------|
| `LEX_WEB__ALLOWED_HOSTS` | list[str] | (required) | Hostnames permitted to reach the application. Empty by default; must be configured before production deployment. | `lexigram-web/src/lexigram/web/security/config.py:SecurityConfig.allowed_hosts` |
| `LEX_WEB__API_DOCS__ENABLED` | bool | True | Enable API documentation endpoints (/docs, /redoc) and auto-configure CSP for their CDN assets | `lexigram-web/src/lexigram/web/config.py:APIDocsConfig.api_docs.enabled` |
| `LEX_WEB__API_DOCS__PROVIDER` | str | "both" | Documentation provider: 'swagger', 'redoc', or 'both' | `lexigram-web/src/lexigram/web/config.py:APIDocsConfig.api_docs.provider` |
| `LEX_WEB__AUTH_EXCLUDE_PATHS` | list[str] | (required) | Paths to exclude from authentication | `lexigram-web/src/lexigram/web/config.py:WebConfig.auth_exclude_paths` |
| `LEX_WEB__COMPRESSION_ENABLED` | bool | True |  | `lexigram-web/src/lexigram/web/config.py:WebConfig.compression_enabled` |
| `LEX_WEB__CORS` | CORSConfig | (required) |  | `lexigram-web/src/lexigram/web/config.py:WebConfig.cors` |
| `LEX_WEB__CORS__ALLOWED_ORIGINS` | list[str] | (required) | Allowed origins (use ['*'] to allow all) | `lexigram-web/src/lexigram/web/security/config.py:CORSConfig.cors.allowed_origins` |
| `LEX_WEB__CORS__ALLOW_CREDENTIALS` | bool | False |  | `lexigram-web/src/lexigram/web/security/config.py:CORSConfig.cors.allow_credentials` |
| `LEX_WEB__CORS__ALLOW_HEADERS` | list[str] | (required) |  | `lexigram-web/src/lexigram/web/security/config.py:CORSConfig.cors.allow_headers` |
| `LEX_WEB__CORS__ALLOW_METHODS` | list[str] | (required) |  | `lexigram-web/src/lexigram/web/security/config.py:CORSConfig.cors.allow_methods` |
| `LEX_WEB__CORS__ALLOW_ORIGIN_REGEX` | str  \| None | None | Regex pattern for allowed origins (matched when not in allowed_origins) | `lexigram-web/src/lexigram/web/security/config.py:CORSConfig.cors.allow_origin_regex` |
| `LEX_WEB__CORS__DEBUG_PERMISSIVE` | bool | False | When True and debug mode is active, allow any origin via wildcard (explicit opt-in replacement for the old implicit debu | `lexigram-web/src/lexigram/web/security/config.py:CORSConfig.cors.debug_permissive` |
| `LEX_WEB__CORS__ENABLED` | bool | True | Enable CORS | `lexigram-web/src/lexigram/web/security/config.py:CORSConfig.cors.enabled` |
| `LEX_WEB__CORS__EXPOSE_HEADERS` | list[str] | (required) |  | `lexigram-web/src/lexigram/web/security/config.py:CORSConfig.cors.expose_headers` |
| `LEX_WEB__CORS__MAX_AGE` | int | 600 |  | `lexigram-web/src/lexigram/web/security/config.py:CORSConfig.cors.max_age` |
| `LEX_WEB__CROSS_ORIGIN__EMBEDDER_POLICY` | str | "require-corp" | Cross-Origin-Embedder-Policy header value | `lexigram-web/src/lexigram/web/security/config.py:CrossOriginConfig.cross_origin.embedder_policy` |
| `LEX_WEB__CROSS_ORIGIN__ENABLED` | bool | False | Emit cross-origin isolation headers | `lexigram-web/src/lexigram/web/security/config.py:CrossOriginConfig.cross_origin.enabled` |
| `LEX_WEB__CROSS_ORIGIN__OPENER_POLICY` | str | "same-origin" | Cross-Origin-Opener-Policy header value | `lexigram-web/src/lexigram/web/security/config.py:CrossOriginConfig.cross_origin.opener_policy` |
| `LEX_WEB__CROSS_ORIGIN__RESOURCE_POLICY` | str | "same-origin" | Cross-Origin-Resource-Policy header value | `lexigram-web/src/lexigram/web/security/config.py:CrossOriginConfig.cross_origin.resource_policy` |
| `LEX_WEB__CSP__DIRECTIVES` | dict[str, Any] | (required) | CSP directives mapping directive name to source expression(s) | `lexigram-web/src/lexigram/web/security/config.py:CSPConfig.csp.directives` |
| `LEX_WEB__CSP__ENABLED` | bool | True | Emit the Content-Security-Policy header | `lexigram-web/src/lexigram/web/security/config.py:CSPConfig.csp.enabled` |
| `LEX_WEB__CSRF__COOKIE_DOMAIN` | str  \| None | None |  | `lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.cookie_domain` |
| `LEX_WEB__CSRF__COOKIE_HTTPONLY` | bool | True |  | `lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.cookie_httponly` |
| `LEX_WEB__CSRF__COOKIE_NAME` | str | "csrf_token" |  | `lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.cookie_name` |
| `LEX_WEB__CSRF__COOKIE_PATH` | str | "/" |  | `lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.cookie_path` |
| `LEX_WEB__CSRF__COOKIE_SAMESITE` | str | "Lax" |  | `lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.cookie_samesite` |
| `LEX_WEB__CSRF__COOKIE_SECURE` | bool | True |  | `lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.cookie_secure` |
| `LEX_WEB__CSRF__ENABLED` | bool | False |  | `lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.enabled` |
| `LEX_WEB__CSRF__EXCLUDED_PATHS` | list[str] | (required) | URL path prefixes exempt from CSRF validation for cookie-less requests; cookie-bearing requests on these paths are still | `lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.excluded_paths` |
| `LEX_WEB__CSRF__EXCLUDE_AUTH_SCHEMES` | list[str] | (required) | Authorization header schemes that bypass CSRF validation (explicit opt-in). | `lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.exclude_auth_schemes` |
| `LEX_WEB__CSRF__EXCLUDE_CONTENT_TYPES` | list[str] | (required) | Content-Type values that bypass CSRF validation (explicit opt-in — JSON requests are validated by default so cookie-auth | `lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.exclude_content_types` |
| `LEX_WEB__CSRF__HEADER_NAME` | str | "X-CSRF-Token" |  | `lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.header_name` |
| `LEX_WEB__CSRF__SECRET_KEY` | str  \| None | None | HMAC secret used to sign and verify CSRF tokens (populated via LEX_WEB__SECURITY__CSRF__SECRET_KEY) | `lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.secret_key` |
| `LEX_WEB__CSRF__TOKEN_LENGTH` | int | 32 |  | `lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.token_length` |
| `LEX_WEB__CSRF__TOKEN_TTL` | int | 3600 | TTL in seconds for synchronizer-mode tokens stored in cache. | `lexigram-web/src/lexigram/web/security/config.py:CSRFConfig.csrf.token_ttl` |
| `LEX_WEB__CUSTOM_HEADERS` | dict[str, str] | (required) | Additional HTTP response headers emitted verbatim | `lexigram-web/src/lexigram/web/security/config.py:SecurityConfig.custom_headers` |
| `LEX_WEB__DEBUG_ROUTES` | bool | False | Enable debug routes | `lexigram-web/src/lexigram/web/config.py:WebConfig.debug_routes` |
| `LEX_WEB__DEBUG_ROUTES_TOKEN` | SecretStr  \| None | None | Token required to access debug routes (sent as X-Debug-Token header). | `lexigram-web/src/lexigram/web/config.py:WebConfig.debug_routes_token` |
| `LEX_WEB__ENABLED` | bool | True | Enable the security subsystem | `lexigram-web/src/lexigram/web/security/config.py:SecurityConfig.enabled` |
| `LEX_WEB__ENABLED` | bool | True |  | `lexigram-web/src/lexigram/web/config.py:WebConfig.enabled` |
| `LEX_WEB__ENABLE_AUTH` | bool | False | Enable built-in authentication middleware. Requires authenticators to be registered in the container. | `lexigram-web/src/lexigram/web/config.py:WebConfig.enable_auth` |
| `LEX_WEB__ENABLE_CORS` | bool | True |  | `lexigram-web/src/lexigram/web/security/config.py:SecurityConfig.enable_cors` |
| `LEX_WEB__ENABLE_CSRF` | bool | True |  | `lexigram-web/src/lexigram/web/security/config.py:SecurityConfig.enable_csrf` |
| `LEX_WEB__ENABLE_DEBUG_ROUTES_ENV_GATE` | bool | False | Require explicit opt-in for debug route registration. | `lexigram-web/src/lexigram/web/config.py:WebConfig.enable_debug_routes_env_gate` |
| `LEX_WEB__ENABLE_IDENTITY_RESOLUTION` | bool | False | Automatically resolve OAuth external IDs to internal UUIDs in authenticated requests | `lexigram-web/src/lexigram/web/config.py:WebConfig.enable_identity_resolution` |
| `LEX_WEB__ENV` | str  \| None | None | Environment (development/staging/production) | `lexigram-web/src/lexigram/web/config.py:WebConfig.env` |
| `LEX_WEB__HEADERS__CONTENT_TYPE_NOSNIFF` | bool | True |  | `lexigram-web/src/lexigram/web/security/config.py:SecurityHeadersConfig.headers.content_type_nosniff` |
| `LEX_WEB__HEADERS__CSP` | str  \| None | None |  | `lexigram-web/src/lexigram/web/security/config.py:SecurityHeadersConfig.headers.csp` |
| `LEX_WEB__HEADERS__FRAME_OPTIONS` | str | "DENY" |  | `lexigram-web/src/lexigram/web/security/config.py:SecurityHeadersConfig.headers.frame_options` |
| `LEX_WEB__HEADERS__HSTS_INCLUDE_SUBDOMAINS` | bool | True |  | `lexigram-web/src/lexigram/web/security/config.py:SecurityHeadersConfig.headers.hsts_include_subdomai` |
| `LEX_WEB__HEADERS__HSTS_MAX_AGE` | int | 31536000 |  | `lexigram-web/src/lexigram/web/security/config.py:SecurityHeadersConfig.headers.hsts_max_age` |
| `LEX_WEB__HEADERS__PERMISSIONS_POLICY` | str  \| None | None |  | `lexigram-web/src/lexigram/web/security/config.py:SecurityHeadersConfig.headers.permissions_policy` |
| `LEX_WEB__HEADERS__REFERRER_POLICY` | str | "strict-origin-when-cross-origin" |  | `lexigram-web/src/lexigram/web/security/config.py:SecurityHeadersConfig.headers.referrer_policy` |
| `LEX_WEB__HEADERS__XSS_PROTECTION` | str | "1; mode=block" |  | `lexigram-web/src/lexigram/web/security/config.py:SecurityHeadersConfig.headers.xss_protection` |
| `LEX_WEB__HSTS__ENABLED` | bool | False | Emit the Strict-Transport-Security header | `lexigram-web/src/lexigram/web/security/config.py:HSTSConfig.hsts.enabled` |
| `LEX_WEB__HSTS__INCLUDE_SUBDOMAINS` | bool | True | Apply HSTS to all subdomains | `lexigram-web/src/lexigram/web/security/config.py:HSTSConfig.hsts.include_subdomains` |
| `LEX_WEB__HSTS__MAX_AGE` | int | 31536000 | HSTS max-age in seconds (default 1 year) | `lexigram-web/src/lexigram/web/security/config.py:HSTSConfig.hsts.max_age` |
| `LEX_WEB__HSTS__PRELOAD` | bool | False | Include site in HSTS preload list | `lexigram-web/src/lexigram/web/security/config.py:HSTSConfig.hsts.preload` |
| `LEX_WEB__MAX_BODY_SIZE` | int  \| None | (complex) | Maximum allowed request body size in bytes. Requests with a Content-Length header exceeding this limit receive a 413 res | `lexigram-web/src/lexigram/web/config.py:WebConfig.max_body_size` |
| `LEX_WEB__NAME` | str | "web" |  | `lexigram-web/src/lexigram/web/config.py:WebConfig.name` |
| `LEX_WEB__OPENAPI_TITLE` | str | "API" | OpenAPI Title | `lexigram-web/src/lexigram/web/config.py:WebConfig.openapi_title` |
| `LEX_WEB__OPENAPI_URL` | str  \| None | (complex) |  | `lexigram-web/src/lexigram/web/config.py:WebConfig.openapi_url` |
| `LEX_WEB__OPENAPI_VERSION` | str | "1.0.0" | OpenAPI Version | `lexigram-web/src/lexigram/web/config.py:WebConfig.openapi_version` |
| `LEX_WEB__PERMISSIONS_POLICY` | dict[str, str] | (required) | Permissions-Policy directive map | `lexigram-web/src/lexigram/web/security/config.py:SecurityConfig.permissions_policy` |
| `LEX_WEB__RATE_LIMIT__DEFAULT_LIMIT` | int | (complex) | Max requests per window | `lexigram-web/src/lexigram/web/config.py:RateLimitConfig.rate_limit.default_limit` |
| `LEX_WEB__RATE_LIMIT__DEFAULT_WINDOW` | int | (complex) | Window size in seconds | `lexigram-web/src/lexigram/web/config.py:RateLimitConfig.rate_limit.default_window` |
| `LEX_WEB__RATE_LIMIT__ENABLED` | bool | True | Enable rate limiting. When true, RateLimitMiddleware enforces the matched per-path rule or the default_limit/default_win | `lexigram-web/src/lexigram/web/config.py:RateLimitConfig.rate_limit.enabled` |
| `LEX_WEB__RATE_LIMIT__RULES` | dict[str, RateLimitRuleConfig] | (required) | Per-path rate limit rules; longest-prefix match wins | `lexigram-web/src/lexigram/web/config.py:RateLimitConfig.rate_limit.rules` |
| `LEX_WEB__RATE_LIMIT__STORAGE_BACKEND` | str | "memory" | Storage backend (memory/redis) | `lexigram-web/src/lexigram/web/config.py:RateLimitConfig.rate_limit.storage_backend` |
| `LEX_WEB__RATE_LIMIT__WHITELIST_IPS` | list[str] | (required) | Exempt IP addresses | `lexigram-web/src/lexigram/web/config.py:RateLimitConfig.rate_limit.whitelist_ips` |
| `LEX_WEB__REDOC_JS_URL` | str  \| None | None |  | `lexigram-web/src/lexigram/web/config.py:WebConfig.redoc_js_url` |
| `LEX_WEB__REDOC_URL` | str  \| None | "/redoc" |  | `lexigram-web/src/lexigram/web/config.py:WebConfig.redoc_url` |
| `LEX_WEB__REFERRER_POLICY` | str | "strict-origin-when-cross-origin" | Referrer-Policy header value | `lexigram-web/src/lexigram/web/security/config.py:SecurityConfig.referrer_policy` |
| `LEX_WEB__ROLE_GUARD__RULES` | list[RoleGuardRuleConfig] | (required) | Role guard rules in declaration order | `lexigram-web/src/lexigram/web/config.py:RoleGuardConfig.role_guard.rules` |
| `LEX_WEB__SECURITY` | SecurityConfig | (required) | Security configuration (HSTS, CSP, cross-origin, CSRF, headers) | `lexigram-web/src/lexigram/web/config.py:WebConfig.security` |
| `LEX_WEB__SERVER__DEBUG` | bool | False | Enable debug mode | `lexigram-web/src/lexigram/web/config.py:ServerConfig.server.debug` |
| `LEX_WEB__SERVER__HOST` | str | (complex) | Bind host | `lexigram-web/src/lexigram/web/config.py:ServerConfig.server.host` |
| `LEX_WEB__SERVER__PORT` | int | (complex) | Bind port | `lexigram-web/src/lexigram/web/config.py:ServerConfig.server.port` |
| `LEX_WEB__SERVER__RELOAD` | bool | (complex) | Enable auto-reload | `lexigram-web/src/lexigram/web/config.py:ServerConfig.server.reload` |
| `LEX_WEB__SERVER__WORKERS` | int | (complex) | Number of workers | `lexigram-web/src/lexigram/web/config.py:ServerConfig.server.workers` |
| `LEX_WEB__STATIC__DIRECTORY` | str | "static" | Directory to serve | `lexigram-web/src/lexigram/web/config.py:StaticFileConfig.static.directory` |
| `LEX_WEB__STATIC__ENABLED` | bool | False | Enable static file serving | `lexigram-web/src/lexigram/web/config.py:StaticFileConfig.static.enabled` |
| `LEX_WEB__STATIC__HTML` | bool | False | Serve HTML files (SPA mode) | `lexigram-web/src/lexigram/web/config.py:StaticFileConfig.static.html` |
| `LEX_WEB__STATIC__PREFIX` | str | "/static" | URL prefix for static files | `lexigram-web/src/lexigram/web/config.py:StaticFileConfig.static.prefix` |
| `LEX_WEB__SWAGGER_CSS_URL` | str  \| None | None |  | `lexigram-web/src/lexigram/web/config.py:WebConfig.swagger_css_url` |
| `LEX_WEB__SWAGGER_JS_URL` | str  \| None | None |  | `lexigram-web/src/lexigram/web/config.py:WebConfig.swagger_js_url` |
| `LEX_WEB__SWAGGER_UI_URL` | str  \| None | (complex) |  | `lexigram-web/src/lexigram/web/config.py:WebConfig.swagger_ui_url` |
| `LEX_WEB__TEMPLATE_DIRECTORY` | str | "templates" | Directory for Jinja2 templates | `lexigram-web/src/lexigram/web/config.py:WebConfig.template_directory` |

## Non-Config ENV Sources

| Env Var | Source | Rationale |
|---------|--------|-----------|
| `LEX_DEBUG` | `lexigram/src/lexigram/logging/debug.py` | Early-boot logging toggle before typed config is available. |
| `LEX_QUIET` | `lexigram/src/lexigram/app/base.py` | Controls startup banner suppression during process bootstrap. |
| `LEX_CONFIG` | `lexigram-cli/src/lexigram/cli/lib/config_loader.py` | CLI override for explicit configuration file path. |

---

*This document is auto-generated. Do not edit manually.*
