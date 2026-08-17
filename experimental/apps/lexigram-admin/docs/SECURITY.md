# Security

Security model, threat mitigations, and configuration reference for
`lexigram-admin`.

---

## 1. Authentication

### 1.1 Session-Based Auth

Admin authentication uses **session cookies** signed by Starlette's
`SessionMiddleware`. The login flow is orchestrated by
`AdminAuthService.authenticate()`:

1. **IP rate-limit check** — sliding-window per-IP throttle.
2. **Account lockout check** — progressive lockout on repeated failures.
3. **Credential verification** — delegated to the configured
   `AdminUserStoreProtocol` implementation.
4. **Session creation** — `secrets.token_urlsafe(32)` session IDs stored
   in the `admin_sessions` table by `AdminSessionService`.
5. **Audit logging** — every attempt (success or failure) emits a security
   event. Audit failures are fire-and-forget; they never block auth.

Session validation in `AdminSessionService.get_session()` enforces **two
independent expiry gates**:

- **Absolute TTL** (default 24 h) — the session is revoked unconditionally
  after this window.
- **Idle timeout** (default 1 h) — if `last_active_at` exceeds this window,
  the session is revoked.

Both expiry checks immediately call `revoke()` on the repository so the
session cannot be reused even if `is_active` would still be `TRUE`.

### 1.2 Fingerprint HMAC (AUTH-05)

Each session stores an HMAC-SHA256 signature of the fingerprint JSON
(`email` + `roles`) in the `fingerprint_sig` column. On every `get_session()`
call, the signature is verified against the stored fingerprint. A mismatch
immediately revokes the session and returns `None`.

The signing key is derived from the configured `session_secret` via SHA-256.
When `session_secret` is empty, signing is disabled (backward compatibility
for deployments that haven't yet configured a secret).

### 1.3 Structured Error Payloads (AUTH-17)

`AccountLockedError` and `RateLimitExceededError` expose a `to_payload()`
method returning structured data for API responses:

```python
# RateLimitExceededError
{"reason": "rate_limit", "retry_after": 300}

# AccountLockedError
{"reason": "lockout", "unlock_at": "2026-05-26T19:00:00+00:00", "retry_after": 600}
```

These payloads are returned through the auth service's `Result[_, AdminAuthError]`
pattern as `Err` values, where the caller can extract the structured payload
for API serialization.

### 1.2 Middleware Stack

| Middleware | File | Purpose |
|---|---|---|
| `AdminErrorMiddleware` | `middleware/error.py` | Catches exceptions and returns HTMX-aware error responses. HTMX 401 returns `{"error": "session_expired", "login_url": "/admin/login"}` JSON — no `HX-Redirect` to avoid redirect loops. |
| `AdminSessionService` | `auth/services/session_service.py` | Session lifecycle management with **absolute TTL** (default 24 h), **idle timeout** (default 1 h), and **HMAC-signed fingerprint** verification. |
| `AdminAuthMiddleware` | `middleware/auth.py` | Pure-ASGI middleware. Extracts user from signed session cookie via `AdminSessionService.get_session()`, injects into `request.state`. Enforces idle + absolute TTL. Rate limiting is handled by the service layer, not the middleware. |
| `AdminAuthorizationMiddleware` | `middleware/authorization.py` | Request-entry RBAC middleware. Consults `AdminAuthorizerProtocol` on every non-public request. Returns **401** (unauthenticated) or **403** (forbidden). HTMX-aware: returns JSON with `login_url` on 401. |
| `AdminCsrfMiddleware` | `middleware/csrf.py` | Validates CSRF token per request. Enforces Content-Type binding (form tokens require `application/x-www-form-urlencoded`; JSON/JS requests use `X-CSRF-Token` header). Token lifetime aligns with session idle timeout. |
| `AuthGuardMiddleware` | `auth/guards.py` | Starrette `BaseHTTPMiddleware`. Enforces authentication on all non-exempt routes. HTMX-aware — returns `HX-Redirect` instead of 302. Optionally loads permissions into `request.state`. |
| `AdminGuardChain` | `auth/guard_chain.py` | Composable guard pipeline. Executes a sequence of `GuardProtocol` implementations, short-circuiting on first denial with `GuardDeniedError`. |

### 1.3 Bearer Token Policy

By default, admin routes **do not accept** `Authorization: Bearer`
tokens. This keeps a strict separation between admin sessions
(cookie-based) and application JWTs. To enable, set
`GuardConfig.allow_bearer_tokens = True`.

### 1.4 Exempt Paths

The following paths bypass authentication by default:

```
/admin/login
/admin/static
/admin/health
```

Configure via `GuardConfig.exempt_paths`.

### 1.5 Password Policy

`AdminPasswordPolicyService` enforces NIST SP 800-63B guidelines:

| Rule | Default | Configurable |
|---|---|---|
| Minimum length | 12 | Yes |
| Maximum length | 128 | Yes |
| Uppercase required | Yes | Yes |
| Lowercase required | Yes | Yes |
| Digit required | Yes | Yes |
| Special character required | Yes | Yes |
| Reject common passwords | Yes | Yes |
| Reject passwords containing email | Yes | Yes |

Returns **all** violations in one call, not just the first.

---

## 2. Authorization (RBAC)

### 2.1 Architecture

Authorization is layered across three tiers:

```
Role-based (RBAC)     → Resource-level CRUD permissions
Record-level (RLS)    → Row-level policies (owner-only, team-scoped)
Action-level          → Per-action permission checks
```

### 2.2 Permission Schema

Resources define their permission schema via `ResourcePermissions`:

```python
@dataclass
class ResourcePermissions:
    can_list: set[str] = field(default_factory=lambda: {"*"})
    can_view: set[str] = field(default_factory=lambda: {"*"})
    can_create: set[str] = field(default_factory=lambda: {"*"})
    can_edit: set[str] = field(default_factory=lambda: {"*"})
    can_delete: set[str] = field(default_factory=lambda: {"admin"})
    fields: dict[str, FieldPermission] = field(default_factory=dict)
    actions: dict[str, ActionPermission] = field(default_factory=dict)
    rls_policy: str | None = None
```

`"*"` means any authenticated role. `"admin"` is the default for
destructive operations. Wildcard permissions (`"users.*"`) are
supported at the `PermissionSet` level.

**Field-level permissions** control visibility and editability
per-field, and can mask values for specific roles:

```python
FieldPermission(
    view_roles={"admin", "editor"},
    edit_roles={"admin"},
    mask_for={"support"},  # Support sees "••••@example.com"
)
```

### 2.3 `AdminAuthorizerProtocol`

The canonical authorization protocol for the admin subsystem. Defined
in `protocols.py` at line ~419:

```python
class AdminAuthorizerProtocol(Protocol):
    async def can_view(self, user, resource, record=None) -> bool: ...
    async def can_create(self, user, resource) -> bool: ...
    async def can_update(self, user, resource, record=None) -> bool: ...
    async def can_delete(self, user, resource, record=None) -> bool: ...
    async def can_execute_action(self, user, resource, action, record=None) -> bool: ...
```

This is distinct from `lexigram.contracts.auth.AuthorizerProtocol`,
which is the framework-wide contract. Admin-specific checks go through
`AdminAuthorizerProtocol`; framework-level auth goes through
`AuthorizerProtocol`.

### 2.4 `PermissionService`

`PermissionService` is the central runtime for checks. It delegates to
an `AuthorizerProtocol` implementation:

```python
class PermissionService:
    def can_list(self, user, resource_name) -> bool: ...
    def can_view(self, user, resource_name) -> bool: ...
    def can_create(self, user, resource_name) -> bool: ...
    def can_edit(self, user, resource_name, record=None) -> bool: ...
    def can_delete(self, user, resource_name, record=None) -> bool: ...
    def can_view_field(self, user, resource_name, field_name) -> bool: ...
    def can_edit_field(self, user, resource_name, field_name) -> bool: ...
    def should_mask_field(self, user, resource_name, field_name) -> bool: ...
    def can_perform_action(self, user, resource_name, action_name) -> bool: ...
```

`can_edit` and `can_delete` apply **RLS policies** when a record is
provided.

### 2.5 RLS Policies

Registered in `policies.py` and referenced by name in
`ResourcePermissions.rls_policy`:

| Policy | Implemented In | Logic |
|---|---|---|
| `owner_only` | `rbac/policies.py` | `record.user_id == user.id` |
| `team_scoped` | `rbac/policies.py` | `record.team_id == user.team_id` |

Register custom policies with `register_policy(name, callable)`.

### 2.6 Guard Decorators

```python
# Permission check (any matches)
@require_permission("users.delete")
async def delete_user(request): ...

# Permission check (all required)
@require_all_permissions("users.read", "users.export")
async def export_users(request): ...

# Role check
@require_role("admin")
async def admin_only(request): ...

# Composable guard
guard = CompositeGuard(
    PermissionGuard("users.list"),
    RoleGuard("admin"),
    logic="or",  # User needs permission OR role
)
```

Decorators expect permissions to be pre-loaded in `request.state.permissions`
by `AuthGuardMiddleware`.

---

## 3. Action-Level Permissions

### 3.1 `Action.authorize()`

Every action can override `authorize()` for per-action permission logic.
The method receives the target record and the authenticated user:

```python
class DeleteAction(RowAction):
    def authorize(
        self, record: R, user: Any | None = None
    ) -> Result[None, PermissionDenied]:
        if not user or not user.has_role("admin"):
            return Err(PermissionDenied("Admin role required"))
        return Ok(None)
```

The default implementation returns `Ok(None)` (permit all).

### 3.2 Visibility

Actions can also implement `visible_for()` to hide the action button
from the UI entirely:

```python
def visible_for(self, record: R, user: Any | None = None) -> bool:
    return user is not None and user.has_role("editor")
```

Visibility is a UI concern — it does not replace `authorize()` as the
security boundary.

### 3.3 RBAC Integration

The `AdminAuthorizerProtocol.can_execute_action()` method is called by
the action executor before an action is invoked. This covers
resource-level action permissions defined in `ResourcePermissions`:

```python
ActionPermission(allowed_roles={"admin", "manager"})
```

### 3.4 Rigorous Guarding Strategy

Actions are protected at **three layers**:

1. **Resource-level** — `ResourcePermissions.actions[name]` defines
   which roles may invoke the action.
2. **Action-level** — `Action.authorize()` implements per-record
   business logic.
3. **Controller-level** — `@require_permission` or `PermissionGuard`
   decorators on the route handler.

All three layers must pass for the action to execute. A failure at any
layer returns a `Result[..., PermissionDenied]` to the caller.

---

## 4. Cluster (Navigation) Permissions

### 4.1 Cluster Model

Clusters group related resources and pages in the admin navigation.
Defined in `clusters/base.py`:

```python
@dataclass(frozen=True, kw_only=True)
class Cluster:
    name: str
    label: str
    icon: str | None = None
    order: int = 0
    collapsible: bool = True
    resources: list[type] = field(default_factory=list)
    pages: list[type] = field(default_factory=list)
```

### 4.2 Cluster Visibility

Navigation visibility is controlled by the same permission checks as
resource access. A cluster is rendered in the sidebar only when the
user has permission to view at least one resource or page within it.

The `AdminAuthorizerProtocol.can_view()` check applies: if a user
cannot `can_view` any resource in a cluster, the cluster is hidden
from their navigation entirely.

### 4.3 Cluster Permission Schemas (Future)

The planned `ClusterPermissions` schema will allow explicit
`view`/`manage` permissions on clusters themselves:

```python
Cluster(
    name="users",
    label="Users & Access",
    icon="users",
    permissions=ClusterPermissions(view="admin.users.view"),
)
```

Until this is implemented, cluster visibility is derived from
resource-level permissions and the `navigations` mechanism.

---

## 5. CSRF Protection

### 5.1 Token Service

`AdminCsrfService` generates and validates HMAC-SHA256 signed CSRF
tokens scoped to a specific session:

```
Token wire format (before base64url):
  "{timestamp}:{nonce}:{hmac_signature}"

HMAC message:  f"{session_id}:{timestamp}:{nonce}"
HMAC key:      sha256(secret.encode())
```

- Tokens expire after a configurable lifetime that aligns with the session
  idle timeout (default 1 h).
- Validation uses `hmac.compare_digest` for timing-safe comparison.
- Session scoping prevents token reuse across sessions.

### 5.2 Content-Type Binding (AUTH-07)

`AdminCsrfMiddleware` enforces Content-Type binding:

| Content-Type | Expected Token Location |
|---|---|
| `application/x-www-form-urlencoded` | `csrf_token` form field |
| `application/json` or other | `X-CSRF-Token` header |

A token presented in the wrong location (e.g., a form-style token embedded
in a JSON body) is rejected with **403**. This prevents session-rich CSRF
attacks via `Content-Type` confusion.

### 5.3 Per-Form Nonce (AUTH-03)

The login GET endpoint issues a per-form CSRF nonce via a dedicated
`csrf_token` endpoint. This eliminates the pre-auth session requirement
for CSRF token issuance and provides a fresh nonce for each login form
render.

### 5.4 HTMX Integration

HTMX requests carry the CSRF token via `hx-headers`:

```html
<meta name="csrf-token" content="{{ csrf_token }}">
<script>
  document.body.addEventListener('htmx:configRequest', (e) => {
    e.detail.headers['X-CSRF-Token'] = document.querySelector(
      '[name=csrf-token]'
    ).content;
  });
</script>
```

### 5.5 Decorator Protection

The `@csrf_protect` decorator in `auth/guards.py` protects
state-changing routes:

```python
@csrf_protect
async def delete_user(request): ...
```

It checks for the token in:

1. `X-CSRF-Token` header (primary — used by HTMX and fetch/XHR).
2. `csrf_token` form field (fallback — used by traditional forms).

Safe methods (`GET`, `HEAD`, `OPTIONS`) bypass the check.

### 5.6 Service-Level Validation

For programmatic callers, the `AdminCsrfService` is injected directly:

```python
from lexigram.admin.auth.services.csrf_service import AdminCsrfService

csrf.validate_token(session_id, token)  # Returns bool
```

---

## 6. Audit Logging

### 6.1 Security Event Audit

`AdminAuditLogService` records security events (login attempts, session
revocations, permission denials) to the `admin_security_audit_log` table.

**Events tracked** (via `AdminSecurityEventType`):

| Event | Description |
|---|---|
| `login_success` | Successful authentication |
| `login_failure` | Invalid credentials |
| `login_blocked_ip` | Rate-limit triggered |
| `login_blocked_lockout` | Account lockout triggered |
| `logout` | Session revoked |
| `session_created` / `session_expired` / `session_revoked` | Session lifecycle |
| `password_changed` / `password_reset_requested` | Credential changes |
| `csrf_violation` | Invalid or missing CSRF token |
| `permission_denied` | Authorization failure |
| `suspicious_activity` | Catch-all for anomalous events |

### 6.2 Fire-and-Forget Design

All audit methods **never raise**. Exceptions are logged at WARNING
level and absorbed. An audit store outage must never block login or
other auth flows.

### 6.3 CRUD Audit

The `Auditable` protocol provides audit logging for individual resource
operations. Implementations record field-level change tracking:

```python
protocol Auditable:
    async def log_operation(self, operation, record_id, changes, user_id): ...
    async def get_audit_log(self, record_id=None, user_id=None): ...
```

### 6.4 AdminSecurityEventType Classification

Events form two categories:

- **Auth events** (`LOGIN_*`, `LOGOUT`, `SESSION_*`) — generated by
  `AdminAuthService` during the login/logout pipeline.
- **Operational events** (`PERMISSION_DENIED`, `CSRF_VIOLATION`,
  `SUSPICIOUS_ACTIVITY`) — generated by guards and middleware.

---

## 7. Rate Limiting

### 7.1 Login Rate Limiting

Rate limiting is implemented at the **service layer** via `AdminLoginAttemptService`, which uses the DB-backed attempt store for accuracy and an optional `CacheBackendProtocol` for fast hard-block lookups.

| Tier | Default Limit | Cache Hard-Block TTL |
|---|---|---|
| Per minute | 10 failures | 5 min |
| Per 15 minutes | 30 failures | 15 min |
| Per hour | 60 failures | 1 h |

IPs are hashed (SHA-256, first 16 hex chars) before storage to avoid
PII in cache keys. An optional `CacheBackendProtocol` is used for fast
lookups; when unavailable, rate limiting gracefully degrades open.

### 7.2 Account Lockout

Progressive lockout on per-email consecutive failures:

| Consecutive Failures | Lockout Duration |
|---|---|
| 5 | 15 min |
| 10 | 1 h |
| 15 | 4 h |
| 20 | 24 h |
| 50 | Permanent (admin unlock required) |

Lockouts are DB-persisted and survive restarts. On successful login,
the lockout is cleared.

### 7.3 Configuration

```python
class AdminAuthConfig:
    ip_rate_limit_enabled: bool = True
    ip_rate_limit_per_minute: int = 10
    ip_rate_limit_per_15_minutes: int = 30
    ip_rate_limit_per_hour: int = 60
    lockout_thresholds: list[tuple[int, int]] = [
        (5, 15), (10, 60), (15, 240), (20, 1440),
    ]
    permanent_lockout_threshold: int = 50
```

---

## 8. Input Validation

### 8.1 SchemaField Validators

Fields defined via the schema system carry validators that execute
before any data is persisted:

```python
from lexigram.admin.schema.validators import EmailValidator, LengthValidator

fields = [
    TextField(name="email", validators=[EmailValidator()]),
    TextField(name="name", validators=[LengthValidator(min=2, max=100)]),
]
```

Built-in validators:

| Validator | Description |
|---|---|
| `LengthValidator(min, max)` | String length bounds |
| `EmailValidator()` | RFC-compatible email format |
| `AsyncValidator` | Base for async validators (e.g. uniqueness checks) |

### 8.2 Validation Pipeline

Validation runs at the `Validatable` protocol boundary:

1. **Client-side** — HTML5 form validation (first pass).
2. **Schema validators** — `SchemaField.validate()` runs synchronously.
3. **Async validators** — `AsyncValidator.validate()` runs after sync
   pass (e.g. unique-email DB queries).
4. **Data source** — `DataSourceProtocol` implementations may apply
   additional constraints.

### 8.3 Error Reporting

Validation errors return structured `AdminValidationError` with machine-
readable `ErrorCode.VALIDATION_FAILED` and field-level messages. The UI
renders errors inline on each field.

---

## 9. Security Best Practices

### 9.1 Result Over Exceptions

Use `Result[T, E]` for domain-level authorization checks. Exceptions
are for infrastructure failures only:

```python
# ✅ Correct: domain check returns Result
class DeleteAction(RowAction):
    def authorize(self, record, user) -> Result[None, PermissionDenied]:
        if not user or not user.is_active:
            return Err(PermissionDenied("Account deactivated"))
        return Ok(None)

# ✅ Correct: infrastructure failure raises
async def _load_user(self, request) -> AuthenticatedUserProtocol | None:
    try:
        user = await self.user_store.get_by_id(user_id)
    except ConnectionError as e:
        raise AuthInfrastructureError("User store unreachable") from e
```

### 9.2 Permission Boundary Discipline

Checks happen at the authorization boundary, not inside business logic:

```
HTTP Route
  → Guard middleware (auth check)
    → Controller decorator (@require_permission)
      → Action.authorize() (per-action check)
        → Business logic (no permission checks here)
```

Business logic receives an already-authorized context and does not
re-check permissions.

### 9.3 `TYPE_CHECKING` Guards

Sensitive imports (auth dependencies, session types) use
`TYPE_CHECKING` guards to prevent runtime coupling:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.admin.auth.errors import AdminAuthError
```

This keeps protocol files lightweight at runtime while providing full
type safety for tooling.

### 9.4 Session Secrets

The HMAC signing secret for CSRF tokens and session signatures must be:

- **Unique** — different from any other secret in the application.
- **Rotated** — on any security incident involving session compromise.
- **Adequate length** — ≥ 32 bytes of cryptographically random entropy.
- **Environment-configured** — never committed to version control.

### 9.5 CSRF Token Rotation

CSRF tokens are re-generated on login. Sessions never share a CSRF
secret across different sessions. Token expiry (default 1 h) limits
the window for replay attacks.

### 9.6 Audit Never Blocks

Every audit method is wrapped in `try/except` and absorbs failures.
An unavailable database or serialisation error must never prevent the
user from logging in or performing an admin action. The only acceptable
behaviour is a WARNING-level log entry.

### 9.7 Audit Logging (AUTH-12, AUTH-13, AUTH-15, OB-02, OB-03)

Admin audit logging provides a forensically complete trail of all
administrative operations.

**Captured per entry:**
- Actor (`admin_user_id`) — the authenticated admin user performing the
  action.
- Action and resource (`action`, `resource_type`, `resource_id`) — what
  was done to which entity.
- Outcome (`AuditOutcome`) — categorised as `success`, `denied`, or
  `errored`.
- Before/after snapshots (`before`, `after`) — field-level state diffs
  (PII-redacted).
- Request context (`correlation_id`, `request_id`, `request_ip`) — for
  tracing the originating HTTP request.

**PII redaction (AUTH-13):**

Before persistence, `before` and `after` payloads are passed through a
`PiiRedactorProtocol` implementation. The default redactor applies:

1. **Field-name denylist** — any key matching a denylist name (`email`,
   `phone`, `password_hash`, `ssn` by default) has its value replaced
   with `"<redacted>"`.
2. **Pattern matching** — string values are scanned for email addresses
   and phone numbers via regex and replaced with `"<redacted>"`.

Both lists are configurable via `AdminAuditConfig.redaction_field_denylist`
and `AdminAuditConfig.redaction_patterns`.

**Transactional guarantees (AUTH-15):**

The `UowAuditWriter` enqueues audit entries against the active unit of
work when one is present:

- On **commit** — the audit entry is flushed to the underlying logger.
- On **rollback** — the entry is discarded, preserving consistency
  between the mutation and its audit trail.

When no UoW is active, the entry is written immediately.

**Correlation IDs (OB-03):**

Every request receives a correlation ID (`X-Request-ID`) that is echoed
in the response and propagated through:

- The `AdminCorrelationMiddleware` (first in the middleware chain).
- A `ContextVar` (`correlation_id_ctx`) accessible via
  `get_correlation_id()` / `set_correlation_id()`.
- The `ActionContext` object at action execution time.

This enables tracing a single admin operation from HTTP request through
auth checks, execution, and audit persistence.

**Read-audit (AUTH-14):**

Read-audit is disabled by default. When enabled via
`AdminAuditConfig.read_audit_enabled = True`, GET requests to admin
resource paths are logged as low-verbosity entries with no before/after
diff. Enable only when compliance requirements mandate read tracking.

---

## 10. Reporting Issues

Report security vulnerabilities to the project maintainers via the
repository's security advisory process or by contacting the core team
directly. Do not report security issues in public GitHub issues.

When reporting, include:

- Affected version(s).
- Reproduction steps.
- Proof of concept (if applicable).
- Suggested fix or mitigation (optional).

The project aims to acknowledge reports within 48 hours and publish
fixes based on severity.
