# 30 — R34: CSP v2 groundwork — report-only candidate policy + violation reporting

## 1. Problem

Doc 14 fixed the enforced CSP (B14) but left "CSP v2" — dropping
`'unsafe-inline'`/`'unsafe-eval'` — as a roadmap. The full migration
(§14.3: Alpine CSP build, converting every inline directive expression,
externalizing inline scripts/styles) is a large UI rewrite that cannot be
responsibly landed here: real-browser verification is impossible in this
sandbox (Playwright CDN blocked), and a botched conversion silently kills
all admin interactivity.

The industry-standard way to approach a CSP tightening is **not** a
big-bang flip: it is to ship the strict candidate policy in
**`Content-Security-Policy-Report-Only`** alongside the enforced policy,
collect real violation reports, drive them to zero, then flip. lexigram-admin
has none of that machinery: no report-only header, no reporting endpoint,
no way for an operator to see what strict CSP would break. This round
builds exactly that groundwork — fully server-verifiable, zero risk of
breaking the UI (report-only headers never block anything).

## 2. Design

### 2.1 Strict candidate policy (`STRICT_CSP`, models.py)

Defined next to `DEFAULT_CSP`: identical except `script-src 'self'` and
`style-src 'self'` (no unsafe-inline/unsafe-eval). This is the v2 target.

### 2.2 Report-only header emission (security_headers.py)

`AdminSecurityHeaders` gains `report_only_csp: str | None` and
`report_endpoint: str | None`. When a policy is set:

- `Content-Security-Policy-Report-Only: <policy> report-uri <endpoint>;
  report-to csp-endpoint` — `report-uri` for the widest browser support,
  `report-to` for the modern Reporting API;
- `Reporting-Endpoints: csp-endpoint="<endpoint>"` companion header.

**Default ON** with `STRICT_CSP`: report-only cannot break anything, and
on-by-default is what actually moves deployments toward v2. Operators
control it via the existing settings store key
`admin.security.csp_report_only`: absent → strict candidate; one of
`off/0/false/disabled/none` → header suppressed; any other non-empty
string → used verbatim as a custom candidate policy. Resolution happens
in `SecurityHeadersMiddleware._resolve_headers` next to the existing
csp/hsts/frame reads. The enforced CSP is untouched.

### 2.3 Violation ingestion (new `services/security/csp_reports.py`)

- `parse_csp_reports(body, content_type)` — normalizes both wire formats:
  legacy `{"csp-report": {...}}` (`application/csp-report`) and Reporting
  API arrays `[{"type": "csp-violation", "body": {...}}]`
  (`application/reports+json`), tolerating kebab-case and camelCase keys.
  Malformed input → empty list, never raises.
- `CspReportStore` — in-memory, deduped by signature
  `(effective directive, blocked URI, source file)`: per-signature
  `count/first_seen/last_seen`, capped at 200 signatures (oldest evicted),
  `total_received` counter. Deliberately in-memory: diagnostics, not audit
  data; a SQL store can be swapped in later behind the same interface.
- `CspReportEndpoint`:
  - `POST {prefix}/security/csp-report` — body capped at 32 KB (413 when
    over), content-type restricted to the two report types (+
    `application/json` for tooling), always `204` otherwise (no oracle for
    probes); new signatures logged as `admin.csp_violation` (repeats only
    bump counters — no log spam).
  - `GET {prefix}/security/csp-reports` — superuser-only JSON summary
    (401 without user, 403 non-superuser) for operators/Security Center.

### 2.4 Middleware exemptions

Browsers POST reports without CSRF tokens, and violations fire on the
login page pre-auth, so `/security/csp-report` is added to the CSRF bypass
set and the auth-guard bypass suffixes. Safe: the handler only appends to
a capped in-memory buffer and returns 204 — no state mutation, no output
reflection. The GET viewer stays fully guarded.

### 2.5 Mount (`_mount_csp_reporting`, di/mount/contributors.py)

Same pattern as the export center: best-effort step creating one store +
endpoint pair and registering both routes (`admin_csp_report_ingest`,
`admin_csp_reports_list`); failures log `admin.csp_reporting_skipped`
without aborting the mount. Middleware wiring passes
`report_endpoint={prefix}/security/csp-report` where the bundle provider
constructs `SecurityHeadersMiddleware`.

### 2.6 Out of scope

- The actual inline-code migration and the enforcement flip (needs real
  browsers + violation data from this machinery).
- Persistent violation storage / charts.

## 3. Implementation steps

1. `models.py`: `STRICT_CSP`.
2. `security_headers.py`: report-only kwargs + settings resolution +
   `Reporting-Endpoints`.
3. `services/security/csp_reports.py`: parser, store, endpoint.
4. `middleware/csrf.py` + `middleware/auth_guard.py`: bypass entries.
5. `di/mount/contributors.py`: `_mount_csp_reporting`; bundle provider
   passes `report_endpoint` to the middleware.
6. Tests: parser formats/malformed; store dedupe/cap; endpoint
   ingest/413/content-type/viewer auth matrix; headers on/off/custom;
   bypass checks; mount registration.
7. Live verify: Report-Only + Reporting-Endpoints headers on authed and
   login routes; POST legacy-format report → 204; viewer JSON shows the
   deduped violation; anon viewer redirected.
8. Fill §4, README row, commit + push (PR #26 stays unmerged).

## 4. Verification

**Unit tests.** New `tests/unit/services/test_csp_reports.py` (24 tests): strict-policy
shape (no `unsafe-inline`/`unsafe-eval`), Report-Only + `Reporting-Endpoints` header
emission with/without endpoint, off-switch and custom-policy resolution
(`resolve_report_only_csp`), parser for legacy + Reporting-API formats and five
malformed bodies, store dedupe/cap/ordering, ingest 204/413/content-type filtering,
viewer 401/403/200 matrix, and all three middleware bypass lists. Existing
`test_resolution_is_cached_once_per_process` updated (3 → 4 settings reads — new
`admin.security.csp_report_only` key). Targeted run: **147 passed**. Full suite:
**5604 passed / 7 skipped**, coverage 77.04% (≥ 60% gate).

**Implementation deviation found live.** The plan listed CSRF + auth-guard bypasses
only; live testing returned **302 → /admin/login?next=…** on anonymous report POSTs.
The `AuthorizationMiddleware` keeps its *own* public-path list
(`middleware/authorization.py::_public_paths`) — added
`{prefix}/security/csp-report` there as well (exact/boundary matching cannot leak
the `/csp-reports` viewer). Lesson recorded: three independent gate lists guard
admin paths (csrf, auth_guard, authorization).

**Live verification (playground, restart of serve.py).**

- `GET /admin/login` and authenticated `GET /admin/` both emit:
  - `Content-Security-Policy` (unchanged DEFAULT_CSP — enforcement untouched);
  - `Content-Security-Policy-Report-Only: <STRICT_CSP> report-uri
    /admin/security/csp-report; report-to csp-endpoint`;
  - `Reporting-Endpoints: csp-endpoint="/admin/security/csp-report"`.
- Mount log: `admin.csp_reporting_registered path=/admin/security/csp-report`.
- Anonymous `POST` legacy report ×2 → `204 204`; Reporting-API batch → `204`;
  garbage body → `204`; 33 KB body → `413`.
- Superuser `GET /admin/security/csp-reports` → JSON with `total_received: 3` and
  two deduped signatures (script-src count 2, style-src count 1).
- Anonymous `GET /admin/security/csp-reports` → `307` to login (viewer guarded).

**Known limits (accepted).** Store is in-memory per-process (diagnostics, not
audit); no real-browser validation of report delivery in this sandbox (no
Playwright browsers) — wire formats covered by unit fixtures matching the CSP2/CSP3
specs; enforcement flip and inline-code migration remain out of scope (doc 14 §3).
