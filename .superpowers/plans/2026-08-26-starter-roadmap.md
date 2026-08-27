# lexigram-starter-fullstack — Roadmap

> **Source of truth for "what's next" on the starter.** Companion audits live in
> the starter repo: `.superpowers/audits/2026-08-25-lexigram-bugs.md` (framework
> bugs + fix status) and
> `starter-fullstack/.superpowers/plans/2026-08-25-starter-improvements.md`
> (original improvement plan; Phases 0–2 shipped).

**Baseline:** starter `2072116` · framework `4f8a97322` (auth revocation fixes)
**Status legend:** ☐ todo · ◐ partially done · ✅ done

---

## 1. Adopt what this week's framework fixes just unlocked

These are now possible because of the auth/notification commits
(`00fcab86d`, `bf26c35de`, `32e1c3e7b`, `34753ccb5`, b61bf8454):

### 1.1 Switch durable mail to the framework stack ✅→☐ (starter-side swap pending)
Starter still carries its own `infrastructure/delivery_store.py` +
migration `0009`. The framework now ships `MemoryDeliveryStore` /
`SqlDeliveryStore` / `flush_retries()` / `MailerConfig.retry_max_attempts`.

**Task:** set `mailer.retry_max_attempts: 3` in application.yaml, resolve the
wrapped MailerProtocol in InfraProvider, delete `delivery_store.py`,
`storage_setup.py` stays, drop migration 0009 (replace with a no-op or a
drop-table revision), delete `mail.flush_retrying` wiring.
**Effort:** ~half day. **Blocks:** nothing.

### 1.2 Blacklist-based revocation (supersede token_version) ☐
With F10/A5 fixed, `logout_all_user_tokens()` works against CacheModule's
memory backend. Two adoption levels:
- **Now (cheap):** `AccountController.sign_out_everywhere` additionally calls
  `logout_all_user_tokens(user_id)` via injected JWTTokenManager — belt and
  braces alongside token_version.
- **Later (cleanup):** once deployments guarantee a cache backend, drop
  `token_version` column + migration path entirely and rely on blacklist.

### 1.3 Webhook admin pages ☐
Blocked upstream on AdminModule visibility for webhook contracts (F1 root
cause is fixed for resolution; the AdminModule import-scope piece remains).
When framework lane lands it: flip `WebhookConfig(enable_admin=True)` in
app.py and delete the comment.

---

## 2. Starter Phase 3 modules (from improvement plan)

Priority by product value:

| # | Module | One-liner | Effort |
|---|---|---|---|
| P3-1 | **Invites** | Registration optionally requires single-use invite codes (reuses SingleUseToken purpose="invite"); flag `invites_beta`; admin generates codes | ~1 day |
| P3-2 | **Announcements plugin** | Admin-authored banners → SPA header polling `/api/announcements/active` | ~1 day |
| P3-3 | **API keys module** | Hashed `lk_…` keys with scopes; Bearer principal path through role guard; profile manages keys | ~1–2 days |
| P3-4 | **Changelog plugin** | Public semver-tagged release notes page + admin authoring | ~½ day |

Each ships as its own plugin/module following the feedback/webhooks template:
domain → repository(+SQL `_ensure_table`) → service → controllers → provider →
module, tests in the same commit.

## 3. Framework-lane handoffs (not starter work)

Tracked in detail in the starter's bugs audit; summary for visibility:

- **F11 (new):** Admin host serves HTTP-200 error pages for legacy
  (`PageResponse`) handlers — add boot-time contract validation so
  contributors fail at startup instead of silently rendering violations.
- **RetryingMailer auto-wrap:** `MailerProvider` should wrap the primary
  backend when `retry_max_attempts > 0` (stores/worker now shipped in
  `32e1c3e7b`, so only the provider-side composition remains).
- **Auth dual-checkout env issue:** full auth test-suite runs require
  `lexigram-testing` installed in the *repo* venv; currently resolvable only
  from the other checkout (`/applications/framework/...`). Consider making
  the monorepo uv workspace authoritative.
- **OpenAPI exposure:** `/docs` + `/redoc` exist behind JWT; decide whether
  dev profiles should add them to `auth_exclude_paths` by default.

## 4. Hygiene backlog

- [ ] Replace remaining `# type: ignore[arg-type]` on webhook admin handler
      registration once AdminModule visibility lands (see 1.3).
- [ ] Delete migration `0009` usage together with 1.1.
- [ ] README: document `starter.extra_insecure_defaults` yaml key next to the
      production-guard paragraph (config support shipped, doc line exists —
      verify placement after docs restructure).

---

## Suggested next session

Pick **one** of:
1. §1.1 + §1.2 (finish the mail/revocation story end-to-end in the starter),
2. P3-1 Invites (new feature, exercises the whole plugin pattern again),
3. Handoff review with the framework lane on §3 items.
