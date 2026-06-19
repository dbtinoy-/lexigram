# AUDIT_RULES.md — Lexigram Framework Rules Audit

> **Source**: Static rule analysis for architectural boundaries, import policy, and package coverage.

---

## Severity Summary

| Severity | Count |
|----------|-------|
| critical | 74 |
| important | 36 |
| minor | 0 |

## Findings

| File | Line | Rule ID | Severity | Message |
|------|------|---------|----------|---------|
| `lexigram-admin/src/lexigram/admin/auth/services/password_reset_service.py` | 238 | `no-cross-extension-import` | `critical` | lexigram-admin directly imports lexigram-auth via lexigram.auth.authn.security; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-admin/src/lexigram/admin/cache/adapter.py` | 14 | `no-cross-extension-import` | `critical` | lexigram-admin directly imports lexigram-cache via lexigram.cache.service.core; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-admin/src/lexigram/admin/rbac/role_service.py` | 21 | `no-cross-extension-import` | `critical` | lexigram-admin directly imports lexigram-auth via lexigram.auth.authz.service; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-ai-governance/src/lexigram/ai/governance/admin/ledger_pages.py` | 17 | `no-cross-extension-import` | `critical` | lexigram-ai-governance directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-ai-governance/src/lexigram/ai/governance/admin/logs_pages.py` | 21 | `no-cross-extension-import` | `critical` | lexigram-ai-governance directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-ai-governance/src/lexigram/ai/governance/admin/pages.py` | 27 | `no-cross-extension-import` | `critical` | lexigram-ai-governance directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-ai-governance/src/lexigram/ai/governance/resource/reconciliation.py` | 18 | `no-cross-extension-import` | `critical` | lexigram-ai-governance directly imports lexigram-tasks via lexigram.tasks; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-ai-governance/src/lexigram/ai/governance/resource/reconciliation.py` | 22 | `no-cross-extension-import` | `critical` | lexigram-ai-governance directly imports lexigram-tasks via lexigram.tasks; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-ai-guard/src/lexigram/ai/guard/admin/pages/overview.py` | 10 | `no-cross-extension-import` | `critical` | lexigram-ai-guard directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-ai-llm/src/lexigram/ai/llm/admin/pages/overview.py` | 10 | `no-cross-extension-import` | `critical` | lexigram-ai-llm directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-ai-llm/src/lexigram/ai/llm/admin/pages/providers.py` | 10 | `no-cross-extension-import` | `critical` | lexigram-ai-llm directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-ai-llm/src/lexigram/ai/llm/admin/pages/providers.py` | 17 | `no-cross-extension-import` | `critical` | lexigram-ai-llm directly imports lexigram-ui via lexigram.ui.atoms.badge; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-ai-llm/src/lexigram/ai/llm/admin/pages/usage.py` | 10 | `no-cross-extension-import` | `critical` | lexigram-ai-llm directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-ai-relay-gateway/src/lexigram/ai/relay/gateway/admin/pages.py` | 28 | `no-cross-extension-import` | `critical` | lexigram-ai-relay-gateway directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-ai/src/lexigram/ai/admin/pages/overview.py` | 10 | `no-cross-extension-import` | `critical` | lexigram-ai directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-ai/src/lexigram/ai/cli/gateway.py` | 35 | `no-cross-extension-import` | `critical` | lexigram-ai directly imports lexigram-ai-relay-gateway via lexigram.ai.relay.gateway.config; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-ai/src/lexigram/ai/cli/gateway.py` | 112 | `no-cross-extension-import` | `critical` | lexigram-ai directly imports lexigram-web via lexigram.web.server.runner; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-audit/src/lexigram/audit/admin/pages/audit_log.py` | 9 | `no-cross-extension-import` | `critical` | lexigram-audit directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-audit/src/lexigram/audit/admin/pages/verification.py` | 9 | `no-cross-extension-import` | `critical` | lexigram-audit directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-auth/src/lexigram/auth/admin/pages/overview.py` | 13 | `no-cross-extension-import` | `critical` | lexigram-auth directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-auth/src/lexigram/auth/admin/pages/sessions.py` | 12 | `no-cross-extension-import` | `critical` | lexigram-auth directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-auth/src/lexigram/auth/admin/pages/tokens.py` | 11 | `no-cross-extension-import` | `critical` | lexigram-auth directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-auth/src/lexigram/auth/admin/pages/users.py` | 11 | `no-cross-extension-import` | `critical` | lexigram-auth directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-cache/src/lexigram/cache/admin/pages/keys.py` | 7 | `no-cross-extension-import` | `critical` | lexigram-cache directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-cache/src/lexigram/cache/admin/pages/overview.py` | 9 | `no-cross-extension-import` | `critical` | lexigram-cache directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-cache/src/lexigram/cache/admin/pages/stats.py` | 9 | `no-cross-extension-import` | `critical` | lexigram-cache directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-events/src/lexigram/events/admin/pages/dead_letter.py` | 9 | `no-cross-extension-import` | `critical` | lexigram-events directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-events/src/lexigram/events/admin/pages/history.py` | 9 | `no-cross-extension-import` | `critical` | lexigram-events directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-events/src/lexigram/events/admin/pages/overview.py` | 9 | `no-cross-extension-import` | `critical` | lexigram-events directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-monitor/src/lexigram/monitor/alerts/digest_worker.py` | 13 | `no-cross-extension-import` | `critical` | lexigram-monitor directly imports lexigram-tasks via lexigram.tasks; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-monitor/src/lexigram/monitor/alerts/digest_worker.py` | 19 | `no-cross-extension-import` | `critical` | lexigram-monitor directly imports lexigram-tasks via lexigram.tasks; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-monitor/src/lexigram/monitor/di/provider.py` | 393 | `no-cross-extension-import` | `critical` | lexigram-monitor directly imports lexigram-tasks via lexigram.tasks.background_task_manager; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-monitor/src/lexigram/monitor/di/provider.py` | 443 | `no-cross-extension-import` | `critical` | lexigram-monitor directly imports lexigram-tasks via lexigram.tasks.background_task_manager; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-monitor/src/lexigram/monitor/slo/worker.py` | 9 | `no-cross-extension-import` | `critical` | lexigram-monitor directly imports lexigram-tasks via lexigram.tasks.scheduled_worker; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-monitor/src/lexigram/monitor/slo/worker.py` | 12 | `no-cross-extension-import` | `critical` | lexigram-monitor directly imports lexigram-tasks via lexigram.tasks.background_task_manager; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-multimedia/src/lexigram/multimedia/config.py` | 8 | `no-cross-extension-import` | `critical` | lexigram-multimedia directly imports lexigram-multimedia-beat via lexigram.multimedia.beat.config; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-multimedia/src/lexigram/multimedia/config.py` | 9 | `no-cross-extension-import` | `critical` | lexigram-multimedia directly imports lexigram-multimedia-image via lexigram.multimedia.image.config; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-multimedia/src/lexigram/multimedia/config.py` | 10 | `no-cross-extension-import` | `critical` | lexigram-multimedia directly imports lexigram-multimedia-interpolate via lexigram.multimedia.interpolate.config; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-multimedia/src/lexigram/multimedia/config.py` | 11 | `no-cross-extension-import` | `critical` | lexigram-multimedia directly imports lexigram-multimedia-music via lexigram.multimedia.music.config; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-multimedia/src/lexigram/multimedia/config.py` | 12 | `no-cross-extension-import` | `critical` | lexigram-multimedia directly imports lexigram-multimedia-tts via lexigram.multimedia.tts.config; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-multimedia/src/lexigram/multimedia/config.py` | 13 | `no-cross-extension-import` | `critical` | lexigram-multimedia directly imports lexigram-multimedia-upscale via lexigram.multimedia.upscale.config; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-multimedia/src/lexigram/multimedia/config.py` | 14 | `no-cross-extension-import` | `critical` | lexigram-multimedia directly imports lexigram-multimedia-video via lexigram.multimedia.video.config; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-multimedia/src/lexigram/multimedia/di/provider.py` | 61 | `no-cross-extension-import` | `critical` | lexigram-multimedia directly imports lexigram-multimedia-beat via lexigram.multimedia.beat.di.provider; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-multimedia/src/lexigram/multimedia/di/provider.py` | 62 | `no-cross-extension-import` | `critical` | lexigram-multimedia directly imports lexigram-multimedia-image via lexigram.multimedia.image.di.provider; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-multimedia/src/lexigram/multimedia/di/provider.py` | 63 | `no-cross-extension-import` | `critical` | lexigram-multimedia directly imports lexigram-multimedia-interpolate via lexigram.multimedia.interpolate.di.provider; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-multimedia/src/lexigram/multimedia/di/provider.py` | 66 | `no-cross-extension-import` | `critical` | lexigram-multimedia directly imports lexigram-multimedia-music via lexigram.multimedia.music.di.provider; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-multimedia/src/lexigram/multimedia/di/provider.py` | 67 | `no-cross-extension-import` | `critical` | lexigram-multimedia directly imports lexigram-multimedia-tts via lexigram.multimedia.tts.di.provider; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-multimedia/src/lexigram/multimedia/di/provider.py` | 68 | `no-cross-extension-import` | `critical` | lexigram-multimedia directly imports lexigram-multimedia-upscale via lexigram.multimedia.upscale.di.provider; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-multimedia/src/lexigram/multimedia/di/provider.py` | 69 | `no-cross-extension-import` | `critical` | lexigram-multimedia directly imports lexigram-multimedia-video via lexigram.multimedia.video.di.provider; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-multimedia/src/lexigram/multimedia/di/provider.py` | 162 | `no-cross-extension-import` | `critical` | lexigram-multimedia directly imports lexigram-tasks via lexigram.tasks.di.provider; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-multimedia/src/lexigram/multimedia/di/provider.py` | 163 | `no-cross-extension-import` | `critical` | lexigram-multimedia directly imports lexigram-tasks via lexigram.tasks.execution.manager; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-multimedia/src/lexigram/multimedia/module.py` | 48 | `no-cross-extension-import` | `critical` | lexigram-multimedia directly imports lexigram-multimedia-beat via lexigram.multimedia.beat.module; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-multimedia/src/lexigram/multimedia/module.py` | 50 | `no-cross-extension-import` | `critical` | lexigram-multimedia directly imports lexigram-multimedia-image via lexigram.multimedia.image.module; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-multimedia/src/lexigram/multimedia/module.py` | 51 | `no-cross-extension-import` | `critical` | lexigram-multimedia directly imports lexigram-multimedia-interpolate via lexigram.multimedia.interpolate.module; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-multimedia/src/lexigram/multimedia/module.py` | 52 | `no-cross-extension-import` | `critical` | lexigram-multimedia directly imports lexigram-multimedia-music via lexigram.multimedia.music.module; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-multimedia/src/lexigram/multimedia/module.py` | 53 | `no-cross-extension-import` | `critical` | lexigram-multimedia directly imports lexigram-multimedia-tts via lexigram.multimedia.tts.module; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-multimedia/src/lexigram/multimedia/module.py` | 54 | `no-cross-extension-import` | `critical` | lexigram-multimedia directly imports lexigram-multimedia-upscale via lexigram.multimedia.upscale.module; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-multimedia/src/lexigram/multimedia/module.py` | 55 | `no-cross-extension-import` | `critical` | lexigram-multimedia directly imports lexigram-multimedia-video via lexigram.multimedia.video.module; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-notification/src/lexigram/notification/admin/pages/inbox.py` | 11 | `no-cross-extension-import` | `critical` | lexigram-notification directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-queue/src/lexigram/queue/admin/pages/consumers.py` | 9 | `no-cross-extension-import` | `critical` | lexigram-queue directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-queue/src/lexigram/queue/admin/pages/jobs.py` | 9 | `no-cross-extension-import` | `critical` | lexigram-queue directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-queue/src/lexigram/queue/admin/pages/overview.py` | 9 | `no-cross-extension-import` | `critical` | lexigram-queue directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-secrets/src/lexigram/secrets/di/provider.py` | 108 | `no-cross-extension-import` | `critical` | lexigram-secrets directly imports lexigram-testing via lexigram.testing.fakes; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-sql/src/lexigram/sql/admin/pages/migrations.py` | 9 | `no-cross-extension-import` | `critical` | lexigram-sql directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-sql/src/lexigram/sql/admin/pages/overview.py` | 12 | `no-cross-extension-import` | `critical` | lexigram-sql directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-sql/src/lexigram/sql/admin/pages/queries.py` | 9 | `no-cross-extension-import` | `critical` | lexigram-sql directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-tasks/src/lexigram/tasks/admin/pages/active.py` | 11 | `no-cross-extension-import` | `critical` | lexigram-tasks directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-tasks/src/lexigram/tasks/admin/pages/failed.py` | 11 | `no-cross-extension-import` | `critical` | lexigram-tasks directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-tasks/src/lexigram/tasks/admin/pages/history.py` | 11 | `no-cross-extension-import` | `critical` | lexigram-tasks directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-tasks/src/lexigram/tasks/admin/pages/overview.py` | 12 | `no-cross-extension-import` | `critical` | lexigram-tasks directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-webhook/src/lexigram/webhook/admin/pages/dead_letter.py` | 11 | `no-cross-extension-import` | `critical` | lexigram-webhook directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-webhook/src/lexigram/webhook/admin/pages/deliveries.py` | 11 | `no-cross-extension-import` | `critical` | lexigram-webhook directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-webhook/src/lexigram/webhook/admin/pages/deliveries.py` | 20 | `no-cross-extension-import` | `critical` | lexigram-webhook directly imports lexigram-ui via lexigram.ui.atoms.badge; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-webhook/src/lexigram/webhook/admin/pages/subscriptions.py` | 11 | `no-cross-extension-import` | `critical` | lexigram-webhook directly imports lexigram-ui via lexigram.ui; route cross-package behavior through contracts, providers, or container bindings instead. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 65 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'UserCreated' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 73 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'UserUpdated' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 81 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'UserDeactivated' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 88 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'UserDeleted' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 95 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ResourceCreated' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 105 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ResourceUpdated' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 115 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ResourceDeleted' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 125 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'BulkOperationCompleted' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 141 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'AdminEvent' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 148 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ResourceRestored' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 156 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ResourceViewed' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 164 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ExportStarted' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 174 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ExportCompleted' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 186 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ExportFailed' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 195 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ImportStarted' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 205 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ImportCompleted' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 217 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'AdminUserLoggedIn' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 226 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'AdminUserLoggedOut' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 233 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'AdminUserCreated' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 243 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'AdminUserUpdated' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 251 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'PasswordChanged' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 258 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'RolesAssigned' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 267 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ActionExecuted' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 278 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'SettingsUpdated' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 286 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'AdminStarted' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 294 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'AdminStopped' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/events/__init__.py` | 299 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/events/__init__.py declares ClassDef 'ConfigReloaded' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/integrations/__init__.py` | 19 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/integrations/__init__.py declares FunctionDef 'register' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/integrations/__init__.py` | 24 | `init-no-logic` | `important` | lexigram-admin/src/lexigram/admin/integrations/__init__.py declares FunctionDef 'get' in __init__.py. |
| `lexigram-admin/src/lexigram/admin/navigation/__init__.py` | 10 | `import-absolute-only` | `important` | lexigram-admin/src/lexigram/admin/navigation/__init__.py uses a relative import; replace it with an absolute import. |
| `lexigram-contracts/src/lexigram/contracts/ai/governance/__init__.py` | 44 | `init-no-logic` | `important` | lexigram-contracts/src/lexigram/contracts/ai/governance/__init__.py declares ClassDef 'GovernanceDecision' in __init__.py. |
| `lexigram-contracts/src/lexigram/contracts/ai/governance/__init__.py` | 53 | `init-no-logic` | `important` | lexigram-contracts/src/lexigram/contracts/ai/governance/__init__.py declares ClassDef 'CostTrackingProtocol' in __init__.py. |
| `lexigram-contracts/src/lexigram/contracts/ai/governance/__init__.py` | 71 | `init-no-logic` | `important` | lexigram-contracts/src/lexigram/contracts/ai/governance/__init__.py declares ClassDef 'AIGovernanceProtocol' in __init__.py. |
| `lexigram-contracts/src/lexigram/contracts/ai/governance/__init__.py` | 97 | `init-no-logic` | `important` | lexigram-contracts/src/lexigram/contracts/ai/governance/__init__.py declares ClassDef 'AuditEventType' in __init__.py. |
| `lexigram-contracts/src/lexigram/contracts/ai/governance/__init__.py` | 116 | `init-no-logic` | `important` | lexigram-contracts/src/lexigram/contracts/ai/governance/__init__.py declares ClassDef 'AIAuditEvent' in __init__.py. |
| `lexigram-contracts/src/lexigram/contracts/ai/governance/__init__.py` | 148 | `init-no-logic` | `important` | lexigram-contracts/src/lexigram/contracts/ai/governance/__init__.py declares ClassDef 'AIAuditStoreProtocol' in __init__.py. |

## Rule Diagnostics

| Rule ID | Severity | Findings | Detected Error About |
|---------|----------|----------|----------------------|
| `import-absolute-only` | `important` | 1 | Relative imports obscure package boundaries and are disallowed across the framework. |
| `init-no-logic` | `important` | 35 | __init__.py files should contain exports only so package entry points stay declarative. |
| `no-cross-extension-import` | `critical` | 74 | Core and extension packages must respect the declared dependency hierarchy instead of importing across forbidden boundaries. |

## Package Coverage

- Discovered packages: 54
- Covered packages: 54
- Missing packages: 0
- Coverage status: **PASS**

### Covered Packages

- `lexigram`
- `lexigram-admin`
- `lexigram-ai`
- `lexigram-ai-agents`
- `lexigram-ai-evaluation`
- `lexigram-ai-feedback`
- `lexigram-ai-governance`
- `lexigram-ai-guard`
- `lexigram-ai-llm`
- `lexigram-ai-mcp`
- `lexigram-ai-memory`
- `lexigram-ai-observability`
- `lexigram-ai-prompt`
- `lexigram-ai-rag`
- `lexigram-ai-relay`
- `lexigram-ai-relay-gateway`
- `lexigram-ai-session`
- `lexigram-ai-skills`
- `lexigram-ai-workers`
- `lexigram-audit`
- `lexigram-auth`
- `lexigram-cache`
- `lexigram-cli`
- `lexigram-contracts`
- `lexigram-events`
- `lexigram-features`
- `lexigram-graph`
- `lexigram-graphql`
- `lexigram-http`
- `lexigram-monitor`
- `lexigram-multimedia`
- `lexigram-multimedia-beat`
- `lexigram-multimedia-image`
- `lexigram-multimedia-interpolate`
- `lexigram-multimedia-music`
- `lexigram-multimedia-tts`
- `lexigram-multimedia-upscale`
- `lexigram-multimedia-video`
- `lexigram-nosql`
- `lexigram-notification`
- `lexigram-queue`
- `lexigram-resilience`
- `lexigram-search`
- `lexigram-secrets`
- `lexigram-sql`
- `lexigram-storage`
- `lexigram-tasks`
- `lexigram-tenancy`
- `lexigram-testing`
- `lexigram-ui`
- `lexigram-vector`
- `lexigram-web`
- `lexigram-webhook`
- `lexigram-workflow`

### Missing Packages

- `(none)`

## Resolution Guide

- `import-absolute-only`: Replace relative imports (for example `from .module import ...`) with absolute imports rooted at `lexigram...` so module ownership stays explicit.
- `init-no-logic`: Keep `__init__.py` export-only. Move functions/classes to dedicated modules and re-export symbols through `__all__` from `__init__.py`.
- `no-cross-extension-import`: Move shared contracts to `lexigram-contracts`, register implementations via providers, and resolve dependencies through the container instead of direct extension imports.

