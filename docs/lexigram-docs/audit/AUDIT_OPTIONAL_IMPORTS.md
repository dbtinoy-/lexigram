# AUDIT_OPTIONAL_IMPORTS.md

> Audit of module-level third-party imports against `pyproject.toml`
> dependency declarations. An optional or undeclared third-party
> package imported at module level raises at import time when the
> extra is not installed.
>
> Imports inside `try` blocks, `if TYPE_CHECKING:`, or function and
> class bodies are treated as guarded/lazy imports.

## Summary

| Package | Findings | Violations | Unused optional extras |
|---|---|---|---|
| lexigram | 14 | 0 | 1 |
| lexigram-admin | 121 | 0 | 4 |
| lexigram-ai | 2 | 0 | 31 |
| lexigram-ai-agents | 0 | 0 | 0 |
| lexigram-ai-evaluation | 0 | 0 | 0 |
| lexigram-ai-feedback | 0 | 0 | 0 |
| lexigram-ai-governance | 3 | 0 | 0 |
| lexigram-ai-guard | 1 | 0 | 0 |
| lexigram-ai-llm | 16 | 0 | 10 |
| lexigram-ai-mcp | 1 | 0 | 0 |
| lexigram-ai-memory | 0 | 0 | 1 |
| lexigram-ai-observability | 0 | 0 | 0 |
| lexigram-ai-prompt | 0 | 0 | 0 |
| lexigram-ai-rag | 11 | 0 | 7 |
| lexigram-ai-relay | 0 | 0 | 0 |
| lexigram-ai-relay-gateway | 12 | 0 | 0 |
| lexigram-ai-session | 0 | 0 | 0 |
| lexigram-ai-skills | 1 | 0 | 0 |
| lexigram-ai-workers | 0 | 0 | 0 |
| lexigram-audit | 3 | 0 | 0 |
| lexigram-auth | 29 | 0 | 0 |
| lexigram-cache | 13 | 0 | 3 |
| lexigram-cli | 34 | 0 | 0 |
| lexigram-contracts | 4 | 0 | 0 |
| lexigram-events | 7 | 0 | 5 |
| lexigram-features | 1 | 0 | 1 |
| lexigram-graph | 2 | 0 | 0 |
| lexigram-graphql | 22 | 0 | 1 |
| lexigram-http | 3 | 0 | 1 |
| lexigram-monitor | 22 | 0 | 3 |
| lexigram-multimedia | 0 | 0 | 0 |
| lexigram-multimedia-beat | 3 | 0 | 4 |
| lexigram-multimedia-image | 4 | 0 | 0 |
| lexigram-multimedia-interpolate | 2 | 0 | 1 |
| lexigram-multimedia-music | 5 | 0 | 3 |
| lexigram-multimedia-tts | 11 | 0 | 7 |
| lexigram-multimedia-upscale | 5 | 0 | 0 |
| lexigram-multimedia-video | 11 | 0 | 4 |
| lexigram-nosql | 3 | 0 | 3 |
| lexigram-notification | 4 | 0 | 5 |
| lexigram-queue | 4 | 0 | 6 |
| lexigram-resilience | 0 | 0 | 0 |
| lexigram-search | 1 | 0 | 7 |
| lexigram-secrets | 0 | 0 | 5 |
| lexigram-sql | 20 | 0 | 0 |
| lexigram-storage | 9 | 0 | 3 |
| lexigram-tasks | 11 | 0 | 3 |
| lexigram-tenancy | 1 | 0 | 0 |
| lexigram-testing | 47 | 0 | 9 |
| lexigram-ui | 11 | 0 | 2 |
| lexigram-vector | 7 | 0 | 3 |
| lexigram-web | 88 | 0 | 9 |
| lexigram-webhook | 4 | 0 | 0 |
| lexigram-workflow | 1 | 0 | 0 |

## lexigram

| module | status | guard | location |
|---|---|---|---|
| `jinja2` | declared | module | lexigram/src/lexigram/codegen/base.py:10 |
| `structlog` | declared | module | lexigram/src/lexigram/logging/configurator.py:13 |
| `structlog` | declared | module | lexigram/src/lexigram/logging/configurator.py:14 |
| `structlog` | declared | module | lexigram/src/lexigram/logging/factory.py:12 |
| `structlog` | declared | module | lexigram/src/lexigram/logging/processors.py:14 |
| `cryptography` | guarded | guard | lexigram/src/lexigram/security/encryption/service.py:14 |
| `cryptography` | guarded | guard | lexigram/src/lexigram/security/encryption/service.py:15 |
| `nh3` | guarded | guard | lexigram/src/lexigram/security/sanitization/html.py:14 |
| `orjson` | declared | guard | lexigram/src/lexigram/serialization/backends/json.py:13 |
| `pydantic` | declared | module | lexigram/src/lexigram/validation/schema/fields.py:20 |
| `pydantic` | declared | module | lexigram/src/lexigram/validation/schema/fields.py:21 |
| `pydantic` | declared | module | lexigram/src/lexigram/validation/schema/fields.py:22 |
| `pydantic` | declared | module | lexigram/src/lexigram/validation/schema/fields.py:23 |
| `pydantic` | declared | module | lexigram/src/lexigram/validation/schema/fields.py:24 |

Optional extras not imported by package sources: `uvicorn`

## lexigram-admin

| module | status | guard | location |
|---|---|---|---|
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/auth/guards.py:13 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/auth/guards.py:14 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/auth/guards.py:15 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/auth/services/delegating_auth_adapter.py:20 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/auth/services/delegating_auth_adapter.py:21 |
| `pyotp` | declared | module | lexigram-admin/src/lexigram/admin/auth/services/mfa_service.py:11 |
| `segno` | declared | module | lexigram-admin/src/lexigram/admin/auth/services/mfa_service.py:12 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/bootstrap/factory.py:8 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/bootstrap/factory.py:9 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/bootstrap/factory.py:10 |
| `typer` | declared | module | lexigram-admin/src/lexigram/admin/cli/commands/search.py:8 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/auth.py:12 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/auth.py:13 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/base.py:13 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/base.py:14 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/clusters.py:15 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/clusters.py:16 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/command_palette.py:7 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/command_palette.py:8 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/dashboard.py:10 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/dashboard.py:11 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/error.py:8 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/error.py:9 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/plugins.py:18 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/plugins.py:19 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/pool_health.py:11 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/pool_health.py:12 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/profile.py:15 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/profile.py:16 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/progress.py:9 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/progress.py:10 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/rbac.py:17 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/rbac.py:18 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/resource.py:14 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/resource.py:15 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/search.py:12 |
| `starlette` | declared | type-only | lexigram-admin/src/lexigram/admin/controllers/search.py:15 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/settings.py:11 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/settings.py:12 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/setup.py:13 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/setup.py:14 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/widgets.py:8 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/controllers/widgets.py:9 |
| `starlette` | declared | type-only | lexigram-admin/src/lexigram/admin/core/rendering.py:9 |
| `starlette` | declared | type-only | lexigram-admin/src/lexigram/admin/core/rendering.py:10 |
| `starlette` | declared | type-only | lexigram-admin/src/lexigram/admin/core/rendering.py:11 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/core/routing.py:6 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/core/routing.py:7 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/core/routing.py:8 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/core/routing.py:9 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/dashboard/route_integrator.py:9 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/dashboard/route_integrator.py:10 |
| `httpx` | declared | guard | lexigram-admin/src/lexigram/admin/data/adapters/api_adapter.py:8 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/engine/renderer.py:12 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/engine/renderer.py:13 |
| `markupsafe` | declared | guard | lexigram-admin/src/lexigram/admin/engine/renderer.py:19 |
| `pydantic` | declared | type-only | lexigram-admin/src/lexigram/admin/forms/components.py:22 |
| `markupsafe` | declared | module | lexigram-admin/src/lexigram/admin/lib/template.py:11 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/auth.py:11 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/auth.py:12 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/auth.py:13 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/auth_guard.py:12 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/auth_guard.py:13 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/authorization.py:12 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/authorization.py:13 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/authorization.py:14 |
| `starlette` | declared | type-only | lexigram-admin/src/lexigram/admin/middleware/authorization.py:20 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/cache.py:8 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/correlation.py:5 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/correlation.py:6 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/correlation.py:7 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/correlation.py:8 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/csrf.py:7 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/csrf.py:8 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/error.py:9 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/error.py:10 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/error.py:11 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/error.py:12 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/error.py:13 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/nav_push.py:13 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/read_audit.py:5 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/read_audit.py:6 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/read_audit.py:7 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/read_audit.py:8 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/middleware/setup.py:7 |
| `starlette` | declared | type-only | lexigram-admin/src/lexigram/admin/middleware/tenant.py:11 |
| `starlette` | declared | type-only | lexigram-admin/src/lexigram/admin/models/provider_models.py:7 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/openapi/controller.py:5 |
| `starlette` | declared | type-only | lexigram-admin/src/lexigram/admin/openapi/controller.py:10 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/rbac/middleware.py:8 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/rbac/middleware.py:9 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/rbac/middleware.py:10 |
| `starlette` | declared | type-only | lexigram-admin/src/lexigram/admin/relations/belongs_to_many.py:15 |
| `starlette` | declared | type-only | lexigram-admin/src/lexigram/admin/relations/belongs_to_many.py:16 |
| `starlette` | declared | type-only | lexigram-admin/src/lexigram/admin/relations/morph_to.py:10 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/relations/routes.py:7 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/relations/routes.py:8 |
| `starlette` | declared | type-only | lexigram-admin/src/lexigram/admin/relations/routes.py:11 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/resources/detail_renderer.py:7 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/resources/field_renderer.py:7 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/resources/form_renderer.py:7 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/resources/handler.py:11 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/resources/handler.py:12 |
| `starlette` | declared | module | lexigram-admin/src/lexigram/admin/resources/list_renderer.py:7 |
| `openpyxl` | guarded | guard | lexigram-admin/src/lexigram/admin/services/export/adapters/excel.py:13 |
| `openpyxl` | guarded | guard | lexigram-admin/src/lexigram/admin/services/export/adapters/excel.py:14 |
| `reportlab` | guarded | guard | lexigram-admin/src/lexigram/admin/services/export/adapters/pdf.py:13 |
| `reportlab` | guarded | guard | lexigram-admin/src/lexigram/admin/services/export/adapters/pdf.py:14 |
| `reportlab` | guarded | guard | lexigram-admin/src/lexigram/admin/services/export/adapters/pdf.py:15 |
| `reportlab` | guarded | guard | lexigram-admin/src/lexigram/admin/services/export/adapters/pdf.py:19 |
| `aiofiles` | declared | module | lexigram-admin/src/lexigram/admin/settings/loader.py:21 |
| `yaml` | declared | module | lexigram-admin/src/lexigram/admin/settings/loader.py:22 |
| `starlette` | declared | type-only | lexigram-admin/src/lexigram/admin/state/context.py:19 |
| `starlette` | declared | type-only | lexigram-admin/src/lexigram/admin/state/url.py:14 |
| `markupsafe` | declared | module | lexigram-admin/src/lexigram/admin/ui/layouts/admin_layout.py:21 |
| `markupsafe` | declared | module | lexigram-admin/src/lexigram/admin/ui/layouts/components/header.py:11 |
| `markupsafe` | declared | module | lexigram-admin/src/lexigram/admin/ui/layouts/components/sidebar.py:11 |
| `markupsafe` | declared | module | lexigram-admin/src/lexigram/admin/ui/layouts/standalone_layout.py:12 |
| `htpy` | declared | module | lexigram-admin/src/lexigram/admin/ui/organisms/bulk_edit_modal.py:12 |
| `htpy` | declared | module | lexigram-admin/src/lexigram/admin/ui/organisms/dynamic_form.py:10 |
| `htpy` | declared | type-only | lexigram-admin/src/lexigram/admin/ui/views.py:16 |

Optional extras not imported by package sources: `authlib`, `ldap3`, `pysaml2`, `xmlsec`

## lexigram-ai

| module | status | guard | location |
|---|---|---|---|
| `starlette` | declared | module | lexigram-ai/src/lexigram/ai/admin/pages/overview.py:5 |
| `typer` | declared | module | lexigram-ai/src/lexigram/ai/cli/commands.py:5 |

Optional extras not imported by package sources: `anthropic`, `beautifulsoup4`, `chromadb`, `jinja2`, `joblib`, `jsonschema`, `markdown`, `milvus`, `numpy`, `ollama`, `openai`, `opencv-python-headless`, `openrouter`, `pgvector`, `pillow`, `pinecone-client`, `psycopg`, `pypdf`, `pyyaml`, `qdrant-client`, `redis`, `scikit-learn`, `scipy`, `sentence-transformers`, `tiktoken`, `types-beautifulsoup4`, `types-pillow`, `types-pyyaml`, `types-requests`, `weaviate-client`, `xgboost`

## lexigram-ai-agents

No third-party module-level imports.

## lexigram-ai-evaluation

No third-party module-level imports.

## lexigram-ai-feedback

No third-party module-level imports.

## lexigram-ai-governance

| module | status | guard | location |
|---|---|---|---|
| `starlette` | declared | module | lexigram-ai-governance/src/lexigram/ai/governance/admin/ledger_pages.py:14 |
| `starlette` | declared | module | lexigram-ai-governance/src/lexigram/ai/governance/admin/logs_pages.py:14 |
| `starlette` | declared | module | lexigram-ai-governance/src/lexigram/ai/governance/admin/pages.py:14 |

## lexigram-ai-guard

| module | status | guard | location |
|---|---|---|---|
| `starlette` | declared | module | lexigram-ai-guard/src/lexigram/ai/guard/admin/pages/overview.py:5 |

## lexigram-ai-llm

| module | status | guard | location |
|---|---|---|---|
| `starlette` | declared | module | lexigram-ai-llm/src/lexigram/ai/llm/admin/pages/overview.py:5 |
| `starlette` | declared | module | lexigram-ai-llm/src/lexigram/ai/llm/admin/pages/providers.py:5 |
| `starlette` | declared | module | lexigram-ai-llm/src/lexigram/ai/llm/admin/pages/usage.py:5 |
| `aiohttp` | declared | module | lexigram-ai-llm/src/lexigram/ai/llm/clients/cohere.py:55 |
| `aiohttp` | declared | module | lexigram-ai-llm/src/lexigram/ai/llm/clients/groq.py:40 |
| `aiohttp` | declared | module | lexigram-ai-llm/src/lexigram/ai/llm/clients/mistral.py:40 |
| `aiohttp` | declared | module | lexigram-ai-llm/src/lexigram/ai/llm/clients/openrouter.py:14 |
| `pydantic` | declared | module | lexigram-ai-llm/src/lexigram/ai/llm/extraction/extractor.py:13 |
| `pydantic` | declared | type-only | lexigram-ai-llm/src/lexigram/ai/llm/extraction/extractor.py:33 |
| `aiohttp` | declared | module | lexigram-ai-llm/src/lexigram/ai/llm/http/client.py:13 |
| `ollama` | guarded | guard | lexigram-ai-llm/src/lexigram/ai/llm/model_manager/providers/ollama.py:10 |
| `aiohttp` | declared | guard | lexigram-ai-llm/src/lexigram/ai/llm/model_manager/providers/openapi_compatible.py:12 |
| `httpx` | declared | module | lexigram-ai-llm/src/lexigram/ai/llm/multimodal/fetcher.py:7 |
| `pydantic` | declared | type-only | lexigram-ai-llm/src/lexigram/ai/llm/parsers/pydantic.py:17 |
| `aiohttp` | declared | module | lexigram-ai-llm/src/lexigram/ai/llm/pricing/sources.py:21 |
| `pydantic` | declared | module | lexigram-ai-llm/src/lexigram/ai/llm/pricing/types.py:14 |

Optional extras not imported by package sources: `anthropic`, `cohere`, `groq`, `instructor`, `jinja2`, `mistralai`, `openai`, `redis`, `tiktoken`, `transformers`

## lexigram-ai-mcp

| module | status | guard | location |
|---|---|---|---|
| `typer` | declared | module | lexigram-ai-mcp/src/lexigram/ai/mcp/cli/commands.py:11 |

## lexigram-ai-memory

No third-party module-level imports.

## lexigram-ai-observability

No third-party module-level imports.

## lexigram-ai-prompt

No third-party module-level imports.

## lexigram-ai-rag

| module | status | guard | location |
|---|---|---|---|
| `aiofiles` | declared | guard | lexigram-ai-rag/src/lexigram/ai/rag/loaders/_io_utils.py:9 |
| `aiofiles` | declared | guard | lexigram-ai-rag/src/lexigram/ai/rag/loaders/core.py:20 |
| `PIL` | guarded | type-only | lexigram-ai-rag/src/lexigram/ai/rag/multimodal/embeddings/clip.py:18 |
| `numpy` | declared | module | lexigram-ai-rag/src/lexigram/ai/rag/multimodal/embeddings/multimodal.py:12 |
| `librosa` | guarded | guard | lexigram-ai-rag/src/lexigram/ai/rag/multimodal/loaders/audio.py:23 |
| `mutagen` | guarded | guard | lexigram-ai-rag/src/lexigram/ai/rag/multimodal/loaders/audio.py:32 |
| `PIL` | guarded | type-only | lexigram-ai-rag/src/lexigram/ai/rag/multimodal/loaders/image.py:38 |
| `cv2` | guarded | guard | lexigram-ai-rag/src/lexigram/ai/rag/multimodal/loaders/video.py:25 |
| `numpy` | declared | guard | lexigram-ai-rag/src/lexigram/ai/rag/multimodal/loaders/video.py:26 |
| `yaml` | declared | module | lexigram-ai-rag/src/lexigram/ai/rag/pipeline/builder.py:6 |
| `numpy` | declared | module | lexigram-ai-rag/src/lexigram/ai/rag/routing/strategies/semantic.py:8 |

Optional extras not imported by package sources: `aiohttp`, `beautifulsoup4`, `flashrank`, `llmlingua`, `pypdf2`, `torch`, `transformers`

## lexigram-ai-relay

No third-party module-level imports.

## lexigram-ai-relay-gateway

| module | status | guard | location |
|---|---|---|---|
| `starlette` | declared | module | lexigram-ai-relay-gateway/src/lexigram/ai/relay/gateway/admin/pages.py:15 |
| `redis` | guarded | type-only | lexigram-ai-relay-gateway/src/lexigram/ai/relay/gateway/ratelimit_redis.py:19 |
| `starlette` | declared | module | lexigram-ai-relay-gateway/src/lexigram/ai/relay/gateway/web/audio_endpoints.py:25 |
| `starlette` | declared | module | lexigram-ai-relay-gateway/src/lexigram/ai/relay/gateway/web/audio_endpoints.py:26 |
| `starlette` | declared | module | lexigram-ai-relay-gateway/src/lexigram/ai/relay/gateway/web/image_endpoints.py:20 |
| `starlette` | declared | module | lexigram-ai-relay-gateway/src/lexigram/ai/relay/gateway/web/image_endpoints.py:21 |
| `starlette` | declared | module | lexigram-ai-relay-gateway/src/lexigram/ai/relay/gateway/web/image_endpoints.py:22 |
| `starlette` | declared | module | lexigram-ai-relay-gateway/src/lexigram/ai/relay/gateway/web/routes.py:27 |
| `starlette` | declared | module | lexigram-ai-relay-gateway/src/lexigram/ai/relay/gateway/web/routes.py:28 |
| `starlette` | declared | module | lexigram-ai-relay-gateway/src/lexigram/ai/relay/gateway/web/routes.py:29 |
| `starlette` | declared | module | lexigram-ai-relay-gateway/src/lexigram/ai/relay/gateway/web/shared.py:14 |
| `starlette` | declared | module | lexigram-ai-relay-gateway/src/lexigram/ai/relay/gateway/web/shared.py:15 |

## lexigram-ai-session

No third-party module-level imports.

## lexigram-ai-skills

| module | status | guard | location |
|---|---|---|---|
| `yaml` | declared | module | lexigram-ai-skills/src/lexigram/ai/skills/discovery/skill_source_scanner.py:9 |

## lexigram-ai-workers

No third-party module-level imports.

## lexigram-audit

| module | status | guard | location |
|---|---|---|---|
| `starlette` | declared | module | lexigram-audit/src/lexigram/audit/admin/pages/audit_log.py:5 |
| `starlette` | declared | module | lexigram-audit/src/lexigram/audit/admin/pages/verification.py:5 |
| `typer` | declared | module | lexigram-audit/src/lexigram/audit/cli/commands.py:5 |

## lexigram-auth

| module | status | guard | location |
|---|---|---|---|
| `starlette` | declared | module | lexigram-auth/src/lexigram/auth/admin/pages/overview.py:8 |
| `starlette` | declared | module | lexigram-auth/src/lexigram/auth/admin/pages/sessions.py:8 |
| `starlette` | declared | module | lexigram-auth/src/lexigram/auth/admin/pages/tokens.py:7 |
| `starlette` | declared | module | lexigram-auth/src/lexigram/auth/admin/pages/users.py:7 |
| `jwt` | declared | module | lexigram-auth/src/lexigram/auth/authn/_jwt_creation.py:13 |
| `jwt` | declared | module | lexigram-auth/src/lexigram/auth/authn/_jwt_lifecycle.py:13 |
| `jwt` | declared | module | lexigram-auth/src/lexigram/auth/authn/blacklist.py:16 |
| `jwt` | declared | module | lexigram-auth/src/lexigram/auth/authn/google_oauth.py:9 |
| `ldap3` | guarded | guard | lexigram-auth/src/lexigram/auth/authn/ldap.py:11 |
| `ldap3` | guarded | guard | lexigram-auth/src/lexigram/auth/authn/ldap.py:12 |
| `ldap3` | guarded | guard | lexigram-auth/src/lexigram/auth/authn/ldap.py:13 |
| `authlib` | guarded | guard | lexigram-auth/src/lexigram/auth/authn/oauth2.py:38 |
| `authlib` | guarded | guard | lexigram-auth/src/lexigram/auth/authn/oauth2.py:41 |
| `cryptography` | declared | module | lexigram-auth/src/lexigram/auth/authn/passkeys.py:60 |
| `cryptography` | declared | module | lexigram-auth/src/lexigram/auth/authn/passkeys.py:61 |
| `argon2` | guarded | guard | lexigram-auth/src/lexigram/auth/authn/password_hasher.py:23 |
| `argon2` | guarded | guard | lexigram-auth/src/lexigram/auth/authn/password_hasher.py:24 |
| `saml2` | guarded | guard | lexigram-auth/src/lexigram/auth/authn/saml.py:11 |
| `saml2` | guarded | guard | lexigram-auth/src/lexigram/auth/authn/saml.py:14 |
| `saml2` | guarded | guard | lexigram-auth/src/lexigram/auth/authn/saml.py:15 |
| `saml2` | guarded | guard | lexigram-auth/src/lexigram/auth/authn/saml.py:16 |
| `saml2` | guarded | guard | lexigram-auth/src/lexigram/auth/authn/saml.py:17 |
| `saml2` | guarded | guard | lexigram-auth/src/lexigram/auth/authn/saml.py:20 |
| `saml2` | guarded | guard | lexigram-auth/src/lexigram/auth/authn/saml.py:21 |
| `xmlsec` | guarded | guard | lexigram-auth/src/lexigram/auth/authn/saml.py:22 |
| `starlette` | declared | module | lexigram-auth/src/lexigram/auth/authz/guards.py:30 |
| `typer` | declared | module | lexigram-auth/src/lexigram/auth/cli/commands.py:5 |
| `jinja2` | declared | module | lexigram-auth/src/lexigram/auth/cli/generators/guard.py:5 |
| `pydantic` | declared | module | lexigram-auth/src/lexigram/auth/di/sub_providers/authentication_provider.py:8 |

## lexigram-cache

| module | status | guard | location |
|---|---|---|---|
| `starlette` | declared | module | lexigram-cache/src/lexigram/cache/admin/pages/keys.py:5 |
| `starlette` | declared | module | lexigram-cache/src/lexigram/cache/admin/pages/overview.py:5 |
| `starlette` | declared | module | lexigram-cache/src/lexigram/cache/admin/pages/stats.py:5 |
| `pymemcache` | guarded | guard | lexigram-cache/src/lexigram/cache/backends/memcached/backend.py:14 |
| `pymemcache` | guarded | guard | lexigram-cache/src/lexigram/cache/backends/memcached/backend.py:15 |
| `pymemcache` | guarded | guard | lexigram-cache/src/lexigram/cache/backends/memcached/backend.py:16 |
| `typer` | declared | module | lexigram-cache/src/lexigram/cache/cli/commands.py:5 |
| `redis` | guarded | guard | lexigram-cache/src/lexigram/cache/stores/redis_lock.py:23 |
| `redis` | guarded | guard | lexigram-cache/src/lexigram/cache/stores/redis_lock.py:24 |
| `redis` | guarded | guard | lexigram-cache/src/lexigram/cache/stores/redis_secrets.py:32 |
| `redis` | guarded | guard | lexigram-cache/src/lexigram/cache/stores/redis_secrets.py:33 |
| `redis` | guarded | guard | lexigram-cache/src/lexigram/cache/stores/redis_state.py:28 |
| `redis` | guarded | guard | lexigram-cache/src/lexigram/cache/stores/redis_state.py:29 |

Optional extras not imported by package sources: `faiss-cpu`, `numpy`, `types-redis`

## lexigram-cli

| module | status | guard | location |
|---|---|---|---|
| `typer` | declared | module | lexigram-cli/src/lexigram/cli/assembly/assembler.py:8 |
| `typer` | declared | module | lexigram-cli/src/lexigram/cli/commands/add.py:7 |
| `yaml` | declared | module | lexigram-cli/src/lexigram/cli/commands/add.py:8 |
| `aiofiles` | declared | module | lexigram-cli/src/lexigram/cli/commands/config.py:11 |
| `typer` | declared | module | lexigram-cli/src/lexigram/cli/commands/config.py:12 |
| `yaml` | declared | module | lexigram-cli/src/lexigram/cli/commands/config.py:13 |
| `typer` | declared | module | lexigram-cli/src/lexigram/cli/commands/contrib.py:16 |
| `typer` | declared | module | lexigram-cli/src/lexigram/cli/commands/db.py:11 |
| `typer` | declared | module | lexigram-cli/src/lexigram/cli/commands/dev.py:8 |
| `typer` | declared | module | lexigram-cli/src/lexigram/cli/commands/events.py:13 |
| `typer` | declared | module | lexigram-cli/src/lexigram/cli/commands/gen.py:5 |
| `typer` | declared | module | lexigram-cli/src/lexigram/cli/commands/init.py:8 |
| `typer` | declared | module | lexigram-cli/src/lexigram/cli/commands/inspect.py:10 |
| `typer` | declared | module | lexigram-cli/src/lexigram/cli/commands/meta.py:5 |
| `jinja2` | declared | module | lexigram-cli/src/lexigram/cli/commands/new.py:9 |
| `typer` | declared | module | lexigram-cli/src/lexigram/cli/commands/new.py:10 |
| `typer` | declared | module | lexigram-cli/src/lexigram/cli/commands/project.py:7 |
| `typer` | declared | module | lexigram-cli/src/lexigram/cli/commands/run.py:10 |
| `typer` | declared | module | lexigram-cli/src/lexigram/cli/commands/shell.py:10 |
| `typer` | declared | module | lexigram-cli/src/lexigram/cli/commands/system.py:7 |
| `yaml` | declared | module | lexigram-cli/src/lexigram/cli/commands/system.py:8 |
| `tomli` | declared | guard | lexigram-cli/src/lexigram/cli/config.py:9 |
| `pydantic` | declared | type-only | lexigram-cli/src/lexigram/cli/lib/config_gen.py:23 |
| `aiofiles` | declared | module | lexigram-cli/src/lexigram/cli/lib/config_loader.py:16 |
| `yaml` | declared | module | lexigram-cli/src/lexigram/cli/lib/config_loader.py:17 |
| `rich` | declared | module | lexigram-cli/src/lexigram/cli/lib/console.py:3 |
| `rich` | declared | module | lexigram-cli/src/lexigram/cli/lib/console.py:4 |
| `jinja2` | declared | module | lexigram-cli/src/lexigram/cli/lib/templates.py:5 |
| `rich` | declared | module | lexigram-cli/src/lexigram/cli/output/manager.py:13 |
| `rich` | declared | module | lexigram-cli/src/lexigram/cli/output/manager.py:14 |
| `rich` | declared | module | lexigram-cli/src/lexigram/cli/output/manager.py:15 |
| `jinja2` | declared | module | lexigram-cli/src/lexigram/cli/registry/generator.py:14 |
| `typer` | declared | module | lexigram-cli/src/lexigram/cli/runtime/error_handler.py:9 |
| `typer` | declared | module | lexigram-cli/src/lexigram/cli/runtime/main.py:8 |

## lexigram-contracts

| module | status | guard | location |
|---|---|---|---|
| `typing_extensions` | declared | module | lexigram-contracts/src/lexigram/contracts/ai/memory.py:8 |
| `typing_extensions` | declared | module | lexigram-contracts/src/lexigram/contracts/ai/providers.py:10 |
| `typing_extensions` | declared | module | lexigram-contracts/src/lexigram/contracts/ai/session.py:11 |
| `typing_extensions` | declared | module | lexigram-contracts/src/lexigram/contracts/ai/skills.py:8 |

## lexigram-events

| module | status | guard | location |
|---|---|---|---|
| `starlette` | declared | module | lexigram-events/src/lexigram/events/admin/pages/dead_letter.py:5 |
| `starlette` | declared | module | lexigram-events/src/lexigram/events/admin/pages/history.py:5 |
| `starlette` | declared | module | lexigram-events/src/lexigram/events/admin/pages/overview.py:5 |
| `typer` | declared | module | lexigram-events/src/lexigram/events/cli/commands.py:5 |
| `jinja2` | declared | module | lexigram-events/src/lexigram/events/cli/generators/command_handler.py:5 |
| `jinja2` | declared | module | lexigram-events/src/lexigram/events/cli/generators/query_handler.py:5 |
| `motor` | guarded | type-only | lexigram-events/src/lexigram/events/stores/mongodb/snapshot_store.py:16 |

Optional extras not imported by package sources: `aio-pika`, `aiokafka`, `aiosqlite`, `asyncpg`, `azure-servicebus`

## lexigram-features

| module | status | guard | location |
|---|---|---|---|
| `typer` | declared | module | lexigram-features/src/lexigram/features/cli/commands.py:5 |

Optional extras not imported by package sources: `pyyaml`

## lexigram-graph

| module | status | guard | location |
|---|---|---|---|
| `neo4j` | guarded | type-only | lexigram-graph/src/lexigram/graph/backends/neo4j/backend.py:16 |
| `neo4j` | guarded | type-only | lexigram-graph/src/lexigram/graph/backends/neo4j/graph.py:18 |

## lexigram-graphql

| module | status | guard | location |
|---|---|---|---|
| `jinja2` | declared | module | lexigram-graphql/src/lexigram/graphql/cli/generators/dataloader.py:11 |
| `starlette` | declared | module | lexigram-graphql/src/lexigram/graphql/controllers/graphql.py:11 |
| `strawberry` | declared | module | lexigram-graphql/src/lexigram/graphql/core/__init__.py:9 |
| `strawberry` | declared | type-only | lexigram-graphql/src/lexigram/graphql/core/execution.py:37 |
| `strawberry` | declared | type-only | lexigram-graphql/src/lexigram/graphql/core/introspection.py:12 |
| `graphql` | guarded | type-only | lexigram-graphql/src/lexigram/graphql/core/validation.py:16 |
| `strawberry` | declared | module | lexigram-graphql/src/lexigram/graphql/monitoring/metrics.py:15 |
| `strawberry` | declared | module | lexigram-graphql/src/lexigram/graphql/monitoring/tracing.py:16 |
| `strawberry` | declared | module | lexigram-graphql/src/lexigram/graphql/protocols.py:21 |
| `strawberry` | declared | module | lexigram-graphql/src/lexigram/graphql/schema/builder.py:11 |
| `strawberry` | declared | module | lexigram-graphql/src/lexigram/graphql/schema/builder.py:12 |
| `strawberry` | declared | module | lexigram-graphql/src/lexigram/graphql/schema/decorators.py:19 |
| `strawberry` | declared | module | lexigram-graphql/src/lexigram/graphql/schema/decorators.py:20 |
| `strawberry` | declared | module | lexigram-graphql/src/lexigram/graphql/schema/types.py:11 |
| `strawberry` | declared | module | lexigram-graphql/src/lexigram/graphql/security/alias.py:11 |
| `graphql` | guarded | type-only | lexigram-graphql/src/lexigram/graphql/security/alias.py:19 |
| `graphql` | guarded | type-only | lexigram-graphql/src/lexigram/graphql/security/complexity.py:18 |
| `graphql` | guarded | type-only | lexigram-graphql/src/lexigram/graphql/security/complexity.py:19 |
| `strawberry` | declared | module | lexigram-graphql/src/lexigram/graphql/security/depth.py:11 |
| `graphql` | guarded | type-only | lexigram-graphql/src/lexigram/graphql/security/depth.py:19 |
| `strawberry` | declared | module | lexigram-graphql/src/lexigram/graphql/security/extensions.py:12 |
| `strawberry` | declared | type-only | lexigram-graphql/src/lexigram/graphql/security/permissions.py:15 |

Optional extras not imported by package sources: `websockets`

## lexigram-http

| module | status | guard | location |
|---|---|---|---|
| `jinja2` | declared | module | lexigram-http/src/lexigram/http/cli/generators/api_client.py:9 |
| `aiohttp` | declared | type-only | lexigram-http/src/lexigram/http/client/base_url_client.py:28 |
| `aiohttp` | declared | module | lexigram-http/src/lexigram/http/pool/connection_pool.py:11 |

Optional extras not imported by package sources: `pytest-aiohttp`

## lexigram-monitor

| module | status | guard | location |
|---|---|---|---|
| `prometheus_client` | guarded | guard | lexigram-monitor/src/lexigram/monitor/backends/exporters/prometheus.py:24 |
| `prometheus_client` | guarded | guard | lexigram-monitor/src/lexigram/monitor/backends/exporters/prometheus.py:25 |
| `prometheus_client` | guarded | guard | lexigram-monitor/src/lexigram/monitor/backends/exporters/prometheus.py:26 |
| `prometheus_client` | guarded | guard | lexigram-monitor/src/lexigram/monitor/backends/exporters/prometheus.py:27 |
| `opentelemetry` | guarded | guard | lexigram-monitor/src/lexigram/monitor/backends/opentelemetry.py:29 |
| `opentelemetry` | guarded | guard | lexigram-monitor/src/lexigram/monitor/backends/opentelemetry.py:30 |
| `opentelemetry` | guarded | guard | lexigram-monitor/src/lexigram/monitor/backends/opentelemetry.py:31 |
| `prometheus_client` | guarded | guard | lexigram-monitor/src/lexigram/monitor/backends/prometheus.py:36 |
| `prometheus_client` | guarded | guard | lexigram-monitor/src/lexigram/monitor/backends/prometheus.py:37 |
| `prometheus_client` | guarded | guard | lexigram-monitor/src/lexigram/monitor/backends/prometheus.py:38 |
| `prometheus_client` | guarded | guard | lexigram-monitor/src/lexigram/monitor/backends/prometheus.py:39 |
| `typer` | declared | module | lexigram-monitor/src/lexigram/monitor/cli/commands.py:5 |
| `opentelemetry` | guarded | guard | lexigram-monitor/src/lexigram/monitor/instrumentation/database.py:23 |
| `opentelemetry` | guarded | guard | lexigram-monitor/src/lexigram/monitor/instrumentation/database.py:24 |
| `starlette` | declared | module | lexigram-monitor/src/lexigram/monitor/instrumentation/http.py:24 |
| `opentelemetry` | guarded | guard | lexigram-monitor/src/lexigram/monitor/instrumentation/http.py:28 |
| `opentelemetry` | guarded | guard | lexigram-monitor/src/lexigram/monitor/instrumentation/http.py:29 |
| `opentelemetry` | guarded | guard | lexigram-monitor/src/lexigram/monitor/instrumentation/http.py:30 |
| `opentelemetry` | guarded | guard | lexigram-monitor/src/lexigram/monitor/instrumentation/messaging.py:16 |
| `opentelemetry` | guarded | guard | lexigram-monitor/src/lexigram/monitor/instrumentation/messaging.py:17 |
| `opentelemetry` | guarded | guard | lexigram-monitor/src/lexigram/monitor/instrumentation/messaging.py:18 |
| `prometheus_client` | guarded | guard | lexigram-monitor/src/lexigram/monitor/metrics/prometheus.py:21 |

Optional extras not imported by package sources: `opentelemetry-distro`, `opentelemetry-instrumentation`, `psutil`

## lexigram-multimedia

No third-party module-level imports.

## lexigram-multimedia-beat

| module | status | guard | location |
|---|---|---|---|
| `aiohttp` | declared | module | lexigram-multimedia-beat/src/lexigram/multimedia/beat/providers/librosa.py:16 |
| `aiohttp` | declared | module | lexigram-multimedia-beat/src/lexigram/multimedia/beat/providers/madmom.py:8 |
| `aiohttp` | declared | module | lexigram-multimedia-beat/src/lexigram/multimedia/beat/servers/madmom_server.py:19 |

Optional extras not imported by package sources: `librosa`, `madmom`, `numpy`, `soundfile`

## lexigram-multimedia-image

| module | status | guard | location |
|---|---|---|---|
| `aiohttp` | declared | module | lexigram-multimedia-image/src/lexigram/multimedia/image/providers/comfyui.py:16 |
| `aiohttp` | declared | module | lexigram-multimedia-image/src/lexigram/multimedia/image/providers/local_http.py:7 |
| `aiohttp` | declared | module | lexigram-multimedia-image/src/lexigram/multimedia/image/providers/openai.py:10 |
| `aiohttp` | declared | module | lexigram-multimedia-image/src/lexigram/multimedia/image/providers/stability.py:10 |

## lexigram-multimedia-interpolate

| module | status | guard | location |
|---|---|---|---|
| `aiohttp` | declared | module | lexigram-multimedia-interpolate/src/lexigram/multimedia/interpolate/providers/rife.py:8 |
| `aiohttp` | declared | module | lexigram-multimedia-interpolate/src/lexigram/multimedia/interpolate/servers/rife_server.py:22 |

Optional extras not imported by package sources: `torch`

## lexigram-multimedia-music

| module | status | guard | location |
|---|---|---|---|
| `aiohttp` | declared | module | lexigram-multimedia-music/src/lexigram/multimedia/music/providers/ace_step.py:16 |
| `aiohttp` | declared | module | lexigram-multimedia-music/src/lexigram/multimedia/music/providers/local_http.py:7 |
| `aiohttp` | declared | module | lexigram-multimedia-music/src/lexigram/multimedia/music/providers/stable_audio_open.py:14 |
| `aiohttp` | declared | module | lexigram-multimedia-music/src/lexigram/multimedia/music/servers/ace_step_server.py:21 |
| `aiohttp` | declared | module | lexigram-multimedia-music/src/lexigram/multimedia/music/servers/stable_audio_open_server.py:20 |

Optional extras not imported by package sources: `ace-step`, `stable-audio-tools`, `torch`

## lexigram-multimedia-tts

| module | status | guard | location |
|---|---|---|---|
| `aiohttp` | declared | module | lexigram-multimedia-tts/src/lexigram/multimedia/tts/providers/chatterbox.py:13 |
| `aiohttp` | declared | module | lexigram-multimedia-tts/src/lexigram/multimedia/tts/providers/elevenlabs.py:7 |
| `aiohttp` | declared | module | lexigram-multimedia-tts/src/lexigram/multimedia/tts/providers/f5_tts.py:15 |
| `aiohttp` | declared | module | lexigram-multimedia-tts/src/lexigram/multimedia/tts/providers/kokoro.py:11 |
| `aiohttp` | declared | module | lexigram-multimedia-tts/src/lexigram/multimedia/tts/providers/local_http.py:7 |
| `aiohttp` | declared | module | lexigram-multimedia-tts/src/lexigram/multimedia/tts/providers/openai.py:15 |
| `aiohttp` | declared | module | lexigram-multimedia-tts/src/lexigram/multimedia/tts/providers/piper.py:12 |
| `aiohttp` | declared | module | lexigram-multimedia-tts/src/lexigram/multimedia/tts/servers/chatterbox_server.py:18 |
| `aiohttp` | declared | module | lexigram-multimedia-tts/src/lexigram/multimedia/tts/servers/f5_tts_server.py:20 |
| `aiohttp` | declared | module | lexigram-multimedia-tts/src/lexigram/multimedia/tts/servers/kokoro_server.py:16 |
| `aiohttp` | declared | module | lexigram-multimedia-tts/src/lexigram/multimedia/tts/servers/piper_server.py:18 |

Optional extras not imported by package sources: `chatterbox-tts`, `f5-tts`, `kokoro`, `piper-tts`, `soundfile`, `torch`, `torchaudio`

## lexigram-multimedia-upscale

| module | status | guard | location |
|---|---|---|---|
| `aiohttp` | declared | module | lexigram-multimedia-upscale/src/lexigram/multimedia/upscale/providers/_asset_io.py:5 |
| `aiohttp` | declared | module | lexigram-multimedia-upscale/src/lexigram/multimedia/upscale/providers/hat.py:8 |
| `aiohttp` | declared | module | lexigram-multimedia-upscale/src/lexigram/multimedia/upscale/providers/real_esrgan.py:8 |
| `aiohttp` | declared | module | lexigram-multimedia-upscale/src/lexigram/multimedia/upscale/servers/hat_server.py:25 |
| `aiohttp` | declared | module | lexigram-multimedia-upscale/src/lexigram/multimedia/upscale/servers/real_esrgan_server.py:24 |

## lexigram-multimedia-video

| module | status | guard | location |
|---|---|---|---|
| `aiohttp` | declared | module | lexigram-multimedia-video/src/lexigram/multimedia/video/processing/media_io.py:11 |
| `aiohttp` | declared | module | lexigram-multimedia-video/src/lexigram/multimedia/video/providers/cogvideox.py:13 |
| `aiohttp` | declared | module | lexigram-multimedia-video/src/lexigram/multimedia/video/providers/comfyui.py:19 |
| `aiohttp` | declared | module | lexigram-multimedia-video/src/lexigram/multimedia/video/providers/local_http.py:7 |
| `aiohttp` | declared | module | lexigram-multimedia-video/src/lexigram/multimedia/video/providers/openai.py:27 |
| `aiohttp` | declared | module | lexigram-multimedia-video/src/lexigram/multimedia/video/providers/runway.py:8 |
| `aiohttp` | declared | module | lexigram-multimedia-video/src/lexigram/multimedia/video/providers/svd.py:15 |
| `aiohttp` | declared | module | lexigram-multimedia-video/src/lexigram/multimedia/video/providers/wan22.py:14 |
| `aiohttp` | declared | module | lexigram-multimedia-video/src/lexigram/multimedia/video/servers/cogvideox_server.py:16 |
| `aiohttp` | declared | module | lexigram-multimedia-video/src/lexigram/multimedia/video/servers/svd_server.py:20 |
| `aiohttp` | declared | module | lexigram-multimedia-video/src/lexigram/multimedia/video/servers/wan22_server.py:19 |

Optional extras not imported by package sources: `diffusers`, `torch`, `transformers`, `wan`

## lexigram-nosql

| module | status | guard | location |
|---|---|---|---|
| `pymongo` | guarded | guard | lexigram-nosql/src/lexigram/nosql/backends/mongodb/backend.py:10 |
| `pymongo` | guarded | guard | lexigram-nosql/src/lexigram/nosql/backends/mongodb/collection.py:9 |
| `jinja2` | declared | module | lexigram-nosql/src/lexigram/nosql/cli/generators/document_repository.py:9 |

Optional extras not imported by package sources: `aioboto3`, `google-cloud-firestore`, `motor`

## lexigram-notification

| module | status | guard | location |
|---|---|---|---|
| `starlette` | declared | module | lexigram-notification/src/lexigram/notification/admin/handlers/inbox.py:13 |
| `starlette` | declared | module | lexigram-notification/src/lexigram/notification/admin/pages/inbox.py:7 |
| `pywebpush` | declared | guard | lexigram-notification/src/lexigram/notification/backends/push/web_push.py:22 |
| `typer` | declared | module | lexigram-notification/src/lexigram/notification/cli/commands.py:5 |

Optional extras not imported by package sources: `cryptography`, `pyjwt`, `sendgrid`, `slack-sdk`, `twilio`

## lexigram-queue

| module | status | guard | location |
|---|---|---|---|
| `starlette` | declared | module | lexigram-queue/src/lexigram/queue/admin/pages/consumers.py:5 |
| `starlette` | declared | module | lexigram-queue/src/lexigram/queue/admin/pages/jobs.py:5 |
| `starlette` | declared | module | lexigram-queue/src/lexigram/queue/admin/pages/overview.py:5 |
| `jinja2` | declared | module | lexigram-queue/src/lexigram/queue/cli/generators/message_consumer.py:8 |

Optional extras not imported by package sources: `aio-pika`, `aiobotocore`, `aiokafka`, `azure-servicebus`, `google-cloud-pubsub`, `redis`

## lexigram-resilience

No third-party module-level imports.

## lexigram-search

| module | status | guard | location |
|---|---|---|---|
| `jinja2` | declared | module | lexigram-search/src/lexigram/search/cli/generators/search_index.py:8 |

Optional extras not imported by package sources: `aiomysql`, `aiosqlite`, `algoliasearch`, `asyncpg`, `elasticsearch`, `meilisearch`, `motor`

## lexigram-secrets

No third-party module-level imports.

## lexigram-sql

| module | status | guard | location |
|---|---|---|---|
| `sqlalchemy` | declared | module | lexigram-sql/src/lexigram/sql/admin/audit_store.py:13 |
| `sqlalchemy` | declared | module | lexigram-sql/src/lexigram/sql/admin/audit_store.py:14 |
| `starlette` | declared | module | lexigram-sql/src/lexigram/sql/admin/pages/migrations.py:5 |
| `starlette` | declared | module | lexigram-sql/src/lexigram/sql/admin/pages/overview.py:5 |
| `starlette` | declared | module | lexigram-sql/src/lexigram/sql/admin/pages/queries.py:5 |
| `asyncpg` | guarded | guard | lexigram-sql/src/lexigram/sql/backends/_postgres_connection.py:23 |
| `asyncpg` | guarded | guard | lexigram-sql/src/lexigram/sql/backends/postgres.py:39 |
| `aiosqlite` | declared | guard | lexigram-sql/src/lexigram/sql/backends/sqlite.py:23 |
| `typer` | declared | module | lexigram-sql/src/lexigram/sql/cli/commands.py:13 |
| `alembic` | declared | guard | lexigram-sql/src/lexigram/sql/migrations/engine.py:13 |
| `alembic` | declared | guard | lexigram-sql/src/lexigram/sql/migrations/engine.py:14 |
| `alembic` | declared | guard | lexigram-sql/src/lexigram/sql/migrations/introspector.py:12 |
| `alembic` | declared | guard | lexigram-sql/src/lexigram/sql/migrations/manager.py:55 |
| `aiomysql` | guarded | guard | lexigram-sql/src/lexigram/sql/providers/mysql_provider.py:11 |
| `asyncpg` | guarded | guard | lexigram-sql/src/lexigram/sql/providers/postgres_provider.py:13 |
| `aiosqlite` | declared | guard | lexigram-sql/src/lexigram/sql/providers/sqlite_provider.py:14 |
| `sqlalchemy` | declared | module | lexigram-sql/src/lexigram/sql/query/admin_builder.py:13 |
| `anyio` | declared | module | lexigram-sql/src/lexigram/sql/seeds/manager.py:10 |
| `sqlalchemy` | declared | module | lexigram-sql/src/lexigram/sql/seeds/manager.py:11 |
| `sqlalchemy` | declared | module | lexigram-sql/src/lexigram/sql/seeds/manager.py:12 |

## lexigram-storage

| module | status | guard | location |
|---|---|---|---|
| `botocore` | guarded | guard | lexigram-storage/src/lexigram/storage/backends/_s3_upload_mixin.py:13 |
| `azure` | guarded | guard | lexigram-storage/src/lexigram/storage/backends/azure.py:14 |
| `azure` | guarded | guard | lexigram-storage/src/lexigram/storage/backends/azure.py:17 |
| `gcloud` | guarded | guard | lexigram-storage/src/lexigram/storage/backends/gcs.py:13 |
| `aiofiles` | declared | module | lexigram-storage/src/lexigram/storage/backends/local.py:16 |
| `aiobotocore` | guarded | guard | lexigram-storage/src/lexigram/storage/backends/s3.py:21 |
| `aiobotocore` | guarded | guard | lexigram-storage/src/lexigram/storage/backends/s3.py:22 |
| `botocore` | guarded | guard | lexigram-storage/src/lexigram/storage/backends/s3.py:23 |
| `aiofiles` | declared | module | lexigram-storage/src/lexigram/storage/kv/local.py:10 |

Optional extras not imported by package sources: `azure-storage-blob`, `gcloud-aio-storage`, `types-aiobotocore`

## lexigram-tasks

| module | status | guard | location |
|---|---|---|---|
| `starlette` | declared | module | lexigram-tasks/src/lexigram/tasks/admin/pages/active.py:7 |
| `starlette` | declared | module | lexigram-tasks/src/lexigram/tasks/admin/pages/failed.py:7 |
| `starlette` | declared | module | lexigram-tasks/src/lexigram/tasks/admin/pages/history.py:7 |
| `starlette` | declared | module | lexigram-tasks/src/lexigram/tasks/admin/pages/overview.py:7 |
| `aio_pika` | guarded | guard | lexigram-tasks/src/lexigram/tasks/backends/rabbitmq.py:18 |
| `redis` | guarded | guard | lexigram-tasks/src/lexigram/tasks/backends/redis.py:39 |
| `typer` | declared | module | lexigram-tasks/src/lexigram/tasks/cli/commands.py:5 |
| `psutil` | declared | guard | lexigram-tasks/src/lexigram/tasks/concurrency/compute.py:24 |
| `redis` | guarded | type-only | lexigram-tasks/src/lexigram/tasks/dlq/redis_dlq.py:12 |
| `psutil` | declared | guard | lexigram-tasks/src/lexigram/tasks/execution/pool.py:13 |
| `croniter` | declared | guard | lexigram-tasks/src/lexigram/tasks/scheduling/cron.py:30 |

Optional extras not imported by package sources: `pika`, `rq`, `types-croniter`

## lexigram-tenancy

| module | status | guard | location |
|---|---|---|---|
| `typer` | declared | module | lexigram-tenancy/src/lexigram/tenancy/cli/commands.py:5 |

## lexigram-testing

| module | status | guard | location |
|---|---|---|---|
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/clients/auth/fixtures.py:11 |
| `pytest_asyncio` | declared | guard | lexigram-testing/src/lexigram/testing/clients/auth/fixtures.py:19 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/clients/cache/fixtures.py:14 |
| `pytest_asyncio` | declared | guard | lexigram-testing/src/lexigram/testing/clients/cache/fixtures.py:27 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/clients/events/fixtures.py:16 |
| `pytest_asyncio` | declared | guard | lexigram-testing/src/lexigram/testing/clients/events/fixtures.py:163 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/clients/search/fixtures.py:12 |
| `pytest_asyncio` | declared | guard | lexigram-testing/src/lexigram/testing/clients/search/fixtures.py:15 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/clients/storage/fixtures.py:8 |
| `pytest_asyncio` | declared | guard | lexigram-testing/src/lexigram/testing/clients/storage/fixtures.py:16 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/clients/tasks/fixtures.py:13 |
| `pytest_asyncio` | declared | guard | lexigram-testing/src/lexigram/testing/clients/tasks/fixtures.py:25 |
| `starlette` | guarded | guard | lexigram-testing/src/lexigram/testing/clients/web/client.py:6 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/compliance/audit.py:10 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/compliance/blob_store.py:19 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/compliance/cache.py:20 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/compliance/database.py:19 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/compliance/distributed_lock.py:8 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/compliance/event_bus.py:21 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/compliance/flags.py:20 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/compliance/middleware.py:19 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/compliance/notification.py:23 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/compliance/queue_backend.py:13 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/compliance/repository.py:21 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/compliance/search.py:19 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/compliance/secrets.py:28 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/compliance/task_queue.py:21 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/compliance/vector_store.py:9 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/compliance/webhook.py:24 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/fixtures/ai.py:8 |
| `pytest_asyncio` | declared | guard | lexigram-testing/src/lexigram/testing/fixtures/ai.py:18 |
| `pytest` | declared | guard | lexigram-testing/src/lexigram/testing/fixtures/bed.py:72 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/fixtures/core.py:13 |
| `pytest_asyncio` | declared | guard | lexigram-testing/src/lexigram/testing/fixtures/core.py:17 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/fixtures/db.py:9 |
| `pytest_asyncio` | declared | guard | lexigram-testing/src/lexigram/testing/fixtures/db.py:13 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/fixtures/tasks.py:8 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/fixtures/web.py:8 |
| `pytest_asyncio` | declared | guard | lexigram-testing/src/lexigram/testing/fixtures/web.py:15 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/integration/fixtures.py:32 |
| `pytest_asyncio` | declared | module | lexigram-testing/src/lexigram/testing/integration/fixtures.py:33 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/integration/markers.py:24 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/lib/snapshots.py:32 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/plugin.py:5 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/plugins/pytest/_hooks_impl.py:5 |
| `pytest` | declared | module | lexigram-testing/src/lexigram/testing/testkit/fixtures.py:23 |
| `pytest_asyncio` | declared | module | lexigram-testing/src/lexigram/testing/testkit/fixtures.py:24 |

Optional extras not imported by package sources: `aiokafka`, `aiosqlite`, `asyncpg`, `elasticsearch`, `httpx2`, `motor`, `neo4j`, `qdrant-client`, `redis`

## lexigram-ui

| module | status | guard | location |
|---|---|---|---|
| `typer` | declared | module | lexigram-ui/src/lexigram/ui/cli/add.py:8 |
| `htpy` | declared | type-only | lexigram-ui/src/lexigram/ui/htmx/helpers.py:12 |
| `starlette` | declared | module | lexigram-ui/src/lexigram/ui/htmx/sse.py:15 |
| `markupsafe` | declared | module | lexigram-ui/src/lexigram/ui/layouts/base_layout.py:11 |
| `markupsafe` | declared | module | lexigram-ui/src/lexigram/ui/layouts/footer.py:11 |
| `markupsafe` | declared | module | lexigram-ui/src/lexigram/ui/layouts/head.py:8 |
| `markupsafe` | declared | module | lexigram-ui/src/lexigram/ui/layouts/html_document.py:12 |
| `markupsafe` | declared | module | lexigram-ui/src/lexigram/ui/layouts/mixins.py:8 |
| `markupsafe` | declared | module | lexigram-ui/src/lexigram/ui/layouts/server_toasts.py:12 |
| `htpy` | declared | module | lexigram-ui/src/lexigram/ui/molecules/stack.py:11 |
| `htpy` | declared | module | lexigram-ui/src/lexigram/ui/state.py:7 |

Optional extras not imported by package sources: `playwright`, `pytest-playwright`

## lexigram-vector

| module | status | guard | location |
|---|---|---|---|
| `chromadb` | guarded | type-only | lexigram-vector/src/lexigram/vector/backends/chroma.py:34 |
| `pinecone` | guarded | type-only | lexigram-vector/src/lexigram/vector/backends/pinecone/backend.py:23 |
| `pinecone` | guarded | type-only | lexigram-vector/src/lexigram/vector/backends/pinecone/collection.py:20 |
| `qdrant_client` | guarded | type-only | lexigram-vector/src/lexigram/vector/backends/qdrant/backend.py:21 |
| `qdrant_client` | guarded | type-only | lexigram-vector/src/lexigram/vector/backends/qdrant/collection.py:19 |
| `typer` | declared | module | lexigram-vector/src/lexigram/vector/cli/commands.py:5 |
| `aiohttp` | declared | type-only | lexigram-vector/src/lexigram/vector/embedding/client.py:13 |

Optional extras not imported by package sources: `asyncpg`, `numpy`, `weaviate-client`

## lexigram-web

| module | status | guard | location |
|---|---|---|---|
| `starlette` | declared | module | lexigram-web/src/lexigram/web/admin/pages/middleware.py:5 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/admin/pages/overview.py:5 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/admin/pages/routes.py:5 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/dependencies/functions.py:5 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/dependencies/functions.py:6 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/dependencies/state.py:5 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/dependencies/state.py:6 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/di/middleware_setup.py:16 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/di/provider.py:8 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/di/provider.py:9 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/di/route_setup.py:11 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/errors/html_error_renderer.py:23 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/integrations/auth.py:8 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/integrations/cache.py:13 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/integrations/debug.py:7 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/integrations/graphql.py:17 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/integrations/rate_limit.py:7 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/integrations/setup.py:14 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/integrations/sql.py:14 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/integrations/starlette.py:7 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/integrations/starlette.py:8 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/middleware/access_log.py:27 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/middleware/adapter.py:7 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/middleware/adapter.py:8 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/middleware/adapter.py:11 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/middleware/adapter.py:14 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/middleware/auth.py:13 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/middleware/auth.py:14 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/middleware/base.py:31 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/middleware/compression.py:8 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/middleware/di_scope.py:17 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/middleware/di_scope.py:24 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/middleware/hooks.py:12 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/middleware/manager.py:8 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/middleware/metrics.py:32 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/middleware/metrics.py:39 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/middleware/rate_limit.py:17 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/middleware/rate_limit.py:18 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/middleware/registry.py:11 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/middleware/request_context.py:16 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/middleware/request_id.py:11 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/middleware/request_id.py:12 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/middleware/role_guard.py:23 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/middleware/role_guard.py:24 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/middleware/security.py:26 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/middleware/stack.py:27 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/middleware/stack.py:28 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/middleware/static.py:9 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/middleware/static.py:10 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/middleware/static.py:11 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/middleware/static.py:12 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/middleware/timing.py:7 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/middleware/unified.py:10 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/responses/adapter.py:5 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/routing/caching.py:31 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/routing/caching.py:32 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/routing/debug.py:6 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/routing/health.py:7 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/routing/health.py:15 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/routing/openapi.py:7 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/routing/result_bridge.py:38 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/routing/router.py:45 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/routing/versioning.py:19 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/routing/versioning.py:20 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/security/context.py:9 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/security/guards.py:15 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/security/guards.py:16 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/serialization/negotiator.py:16 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/serialization/negotiator.py:17 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/serialization/serializers.py:8 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/serialization/serializers.py:11 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/server/shutdown.py:13 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/sse/backpressure.py:11 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/sse/handler.py:13 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/transport/responses.py:9 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/transport/responses.py:12 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/transport/responses.py:15 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/transport/responses.py:18 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/transport/responses.py:21 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/transport/sse.py:12 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/transport/websocket_guards.py:15 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/transport/websockets.py:7 |
| `aiofiles` | declared | module | lexigram-web/src/lexigram/web/uploads/pipeline.py:13 |
| `aiofiles` | declared | module | lexigram-web/src/lexigram/web/uploads/pipeline.py:14 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/uploads/pipeline.py:19 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/websocket/connection_id.py:17 |
| `starlette` | declared | module | lexigram-web/src/lexigram/web/websocket/handler.py:32 |
| `starlette` | declared | type-only | lexigram-web/src/lexigram/web/websocket/rooms.py:16 |

Optional extras not imported by package sources: `granian`, `httpx2`, `hypercorn`, `itsdangerous`, `jinja2`, `pyyaml`, `types-aiofiles`, `uvicorn`, `websockets`

## lexigram-webhook

| module | status | guard | location |
|---|---|---|---|
| `starlette` | declared | module | lexigram-webhook/src/lexigram/webhook/admin/pages/dead_letter.py:5 |
| `starlette` | declared | module | lexigram-webhook/src/lexigram/webhook/admin/pages/deliveries.py:5 |
| `starlette` | declared | module | lexigram-webhook/src/lexigram/webhook/admin/pages/subscriptions.py:5 |
| `httpx` | declared | module | lexigram-webhook/src/lexigram/webhook/delivery/sender.py:7 |

## lexigram-workflow

| module | status | guard | location |
|---|---|---|---|
| `typer` | declared | module | lexigram-workflow/src/lexigram/workflow/cli/commands.py:5 |
