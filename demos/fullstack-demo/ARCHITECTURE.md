# shorts-creator — Architecture

Short-form (Reels/Shorts) video creation app built on the **Lexigram** framework:
an htmx server-rendered web UI drives an async render pipeline that turns an
LLM-generated *idea* + *script* into a narrated, captioned 1080×1920 MP4 using
local TTS (Chatterbox), word-level timing (Whisper), stock footage (Pixabay /
Pexels), and ffmpeg composition.

> Everything here is grounded in the current code. File paths are relative to
> this repo root (`shorts-creator/`).

---

## 1. High-Level View

```mermaid
flowchart LR
    U[("User / Browser")] -->|"htmx + SSE"| W["Web app<br/>uvicorn :8080<br/>Lexigram WebModule"]

    W --> LLM["LLM layer<br/>httpx client<br/>OpenAI-compatible / Anthropic / Ollama<br/>multi-provider failover"]
    LLM -->|"prompts + parse"| P["Pipeline<br/>ideas → script → render"]

    P -->|"synthesize_batch"| TTS["Chatterbox TTS<br/>chatterbox-venv<br/>local model"]
    P -->|"word timings"| WH["Whisper tiny.en<br/>CPU-only"]
    P -->|"stock search"| SV["Pixabay / Pexels<br/>REST APIs"]
    P -->|"compose + encode"| FF["ffmpeg + qtrle overlays<br/>NVENC 720p transcode"]

    W --> DB[("SQLite<br/>data/shorts.db")]
    P --> DB
    P --> FS[("data/renders<br/>data/runs")]
    P --> SK["data/skills/*/SKILL.md<br/>topics registry"]
    P --> FM["data/formats/*/FORMAT.md<br/>format registry"]
```

**Key facts**

| Aspect | Value |
|---|---|
| Framework | Lexigram (`lexigram.app`, DI, web, sql, tasks) |
| Frontend | Server-rendered HTML fragments + **htmx 2** + Tailwind CDN; no SPA framework |
| Database | SQLite via lexigram-sql + Alembic migrations (version table `alembic_primary`) |
| HTTP port | 8080 in container, mapped to `DSM_PORT` (default `18080`) on host |
| Rendering | ffmpeg timeline (`lexigram.multimedia`), 1080×1920 @ 30 fps, HEVC master + H.264 720p companion |
| TTS | Chatterbox, own venv (`dsm/chatterbox-venv`), one process per run for all lines |
| Speech timing | Whisper `tiny.en` (`--word_timestamps`, `--device cpu`), timings only — text never used for captions |
| Backgrounds | Stock video (Pixabay / Pexels, randomized provider order), gradient fallback |
| Content model | `topic` (idea source) + `format` (presentation container with `caption_style`) |

---

## 2. Logical Layers

```mermaid
flowchart TB
    subgraph WEB["Web layer — src/shorts_creator/controllers"]
        WC["Page controllers<br/>projects, scripts, render, videos,<br/>topics, history, settings, assets,<br/>project settings, project runs, homepage"]
        API["API controllers<br/>ideas, scripts, render, settings,<br/>progress, logs, sidebar, assets, health"]
        UI["UI kit — ui/ (shell, icons,<br/>ActionButton, components)"]
    end

    subgraph SVC["Service layer — src/shorts_creator/services"]
        IS["IdeaService"] --> TS["topics registry"]
        SS["ScriptService"] --> TS
        SS --> CA["ScriptCritiqueAgent + critique_tools"]
        PS["ProjectService"] --> PR["ProjectRepository"]
        RS["RunService"] --> RR["RunRepository"]
        PPS["ProjectProfileService<br/>+ TopicProfileService"] --> DB[("SQLite")]
        AS["AssetService"] --> AR["AssetRepository"]
        ST["SettingsStore"] --> DB[("SQLite")]
        PGS["ProgressStore / RenderProgressStore"]
        RTR["RenderTaskRegistry"]
        LS["LogStore"] ; HS["HistoryService"] ; ACT["ActiveContext"]
    end

    subgraph PIPE["Pipeline — src/shorts_creator/pipeline"]
        RP["ReelPipeline"]
        CP["compose.py — ComposePlan"]
        CAP["captions.py — thought grouping"]
        NAR["narration.py — TTS + Whisper"]
        PAR["script_parser.py / topics parsers"]
        SEO["seo.py — keywords + angles + metadata"]
        STK["stock_video.py"]
        SG["subprocess_guard.py"]
    end

    subgraph DATA["Data — models / migrations / repos"]
        M["models: Project, Run, Idea, ParsedScript"]
        MG["migrations/primary/versions<br/>schema_001 … schema_013"]
    end

    WC --> SVC
    API --> SVC
    SVC --> PIPE
    PIPE --> DATA
    PIPE --> FF["ffmpeg / chatterbox / whisper"]
    PS -.-> DB
    RS -.-> DB
    ST -.-> DB
```

---

## 3. Boot & Dependency Injection

Two modules in `src/shorts_creator/main.py` + `services/module.py`:

```mermaid
flowchart TD
    APP["Application.boot('shorts-creator')<br/>asgi_app.py / main.py"] --> ROOT["RootModule"]
    ROOT --> WM["WebModule<br/>20 controllers, port DSM_PORT, CSP"]
    ROOT --> PM["PipelineModule"]
    PM --> DM["DatabaseModule<br/>application.yaml → sqlite,<br/>migrations/primary auto-upgrade"]
    PM --> CP["CoreProvider<br/>AppConfig from application.yaml (LEX_PROFILE)"]
    PM --> LP["LLMProvider<br/>LLMConfig + LLMClientProtocol singletons"]
    PM --> PP["PipelineProvider<br/>registers + wires services"]

    PP -->|"register"| S1["IdeaService, ScriptService, HistoryService<br/>LogStore, RenderTaskRegistry, BackgroundTaskManager"]
    PP -->|"register None → boot binds"| S2["ProjectService, RunService, SettingsStore, ProgressStore"]
    PP -->|"boot"| W1["IdeaService.config/.llm ; ScriptService.config/.llm"]
    PP -->|"boot"| W2["critique tools → ScriptCritiqueAgent → ScriptService"]
    PP -->|"boot"| W3["ProgressStore(LogStore) bound as ProgressStore AND RenderProgressStore"]
    PP -->|"boot"| W4["ProjectRepository(db) → ProjectService ; RunRepository(db) → RunService ; SettingsStore(db)"]
    PP -->|"boot"| W5["_fail_stale_rendering_runs: mark RENDERING runs failed on restart"]
```

---

## 4. Web Layer — Pages & API Routes

### 4.1 The htmx shell

`AppLayout` (`ui/shell.py`) renders a top navbar + 240 px sidebar; **every** page
navigation is `hx_get` + `hx_target="#main-content"` + `hx_push_url` — no full
page loads. A small inline script auto-injects `project_id` into htmx requests.
Secondary swap targets: `#script-output`, `#concept-list`, `#render-output`,
`#videos-content`, `#save-msg`, `#provider-list`, `#sidebar-active`,
`#card-{key}`, and `this` (dashboard auto-poll every 20 s during an active
run).

### 4.2 Routes

```mermaid
flowchart TD
    subgraph PAGES["Page controllers (HTML fragments)"]
        H["GET / → /projects (redirect)"]
        P1["GET /projects ; GET /projects/new ; POST /api/projects/create ; GET /projects/{id}"]
        P2["GET /scripts (ideas + script preview)"]
        P3["GET /render (render studio)"]
        P4["GET /videos ; GET /videos/version/{run_id}"]
        P5["GET /topics ; GET /topics/{name} ; POST /topics/{name}/save"]
        P6["GET /history ; GET /history/{run_id}"]
        P7["GET /settings ; GET /projects/{id}/settings ; POST /api/projects/{id}/settings ; POST /api/projects/{id}/settings/reset ; POST /api/projects/{id}/settings/reset-all"]
        P8["GET /projects/{pid}/runs/{rid} (run dashboard + profile snapshot)"]
        P9["GET /assets ; GET /assets/new ; GET /assets/{id}/edit"]
    end

    subgraph APIS["API controllers"]
        A1["ideas: generate / delete / update / edit-form / cancel-edit"]
        A2["scripts: generate / section update"]
        A3["render: start / progress-SSE / status / cancel / generate-seo / download / preview"]
        A4["settings: get / save (global)"]
        A5["progress: SSE /api/progress/{op_id}"]
        A6["logs: /api/logs"]
        A7["sidebar: active / projects / project-dropdown"]
        A8["assets: upload / update / delete / select-options / file"]
        A9["health: providers / providers/html / header"]
    end

    H --> P1
```

---

## 5. Service Layer & Key Flows

### 5.1 Content generation flow (topic → ideas → script)

```mermaid
sequenceDiagram
    participant U as Browser
    participant IA as IdeasApiController
    participant IS as IdeaService
    participant SEO as seo.research_keywords
    participant TR as topics registry (SkillTopic)
    participant LLM as LLMClient (failover)
    participant SA as ScriptsApiController
    participant SS as ScriptService
    participant PS as ProjectService
    participant CA as ScriptCritiqueAgent

    U->>IA: POST /api/ideas/generate (count, focus, topic)
    IA->>IS: generate_ideas()
    IS->>SEO: research_keywords(focus)
    IS->>TR: topic.build_idea_prompt(count, focus, seo_context)
    IS->>LLM: complete(prompt)
    IS->>TR: topic.parse_ideas(text) → list[Idea]
    IS->>PS: save_ideas / prepend_ideas (project.idea_json JSON blob)
    IA-->>U: fragment into #concept-list

    U->>SA: POST /api/scripts/generate (idea)
    SA->>SS: generate_script(idea)
    SS->>SEO: research_content_angles(title, core_message)
    SS->>TR: topic.build_script_prompt(idea, angle_context)
    SS->>LLM: complete(prompt)
    SS->>TR: topic.parse_script(text) → ParsedScript (sections, durations)
    SS->>PS: save_script (script_json on the idea)
    SA->>SS: critique_script(script_text) [pacing + duration tools]
    SA-->>U: script viewer fragment
```

- **Topics** are loaded from `data/skills/*/SKILL.md` (frontmatter: label,
  structure sections, topic categories, banned phrases + `## IDEA_PROMPT` /
  `## SCRIPT_PROMPT` bodies; pacing/duration ranges are substituted from the
  selected format) plus a per-skill `data/skills/*/scripts/main.py` with
  `parse_ideas / parse_script / mock_*`. Registered once in
  `topics/__init__.py: registry`. Current skills: `stoic`,
  `self_improvement`, `psychology`.
- **Formats** are loaded from `data/formats/*/FORMAT.md`; currently only
  `narration` exists: `caption_styles: [highlight, plain]`, default
  `highlight`, `duration_range: [38, 50]`, `pacing_wps_range: [2.5, 3.0]`.
  Only the caption style is threaded into the renderer today.

### 5.2 Settings resolution (tiered cascade)

```mermaid
flowchart LR
    C["application.yaml<br/>(AppConfig built-ins)"] --> S["ProjectProfileService.resolve(project)<br/>built-in → format → global → project"]
    V["topic_profiles table<br/>(TopicProfileService)"] --> S
    G["app_settings table<br/>(SettingsStore global values)"] --> S
    P["project.profile_overrides_json<br/>(typed profile overrides)"] --> S
    S --> E["EffectiveProjectProfile<br/>(value + ProfileSource per field)"]
    E --> UI["UI badges: Built-in / Format /<br/>Global Default / Project"]
    E --> SNAP["run.settings_snapshot_json<br/>(frozen at render start)"]
```

The guided create form, the per-project profile editor, and the render entry
point all resolve through the same `ProjectProfileService`; renders snapshot
the resolved profile at start so later settings edits never change a running
job's inputs.

---

## 6. Render Pipeline (zoom level)

### 6.1 End-to-end

```mermaid
sequenceDiagram
    participant U as Browser
    participant RA as RenderApiController
    participant RS as RunService
    participant RP as ReelPipeline
    participant NAR as narration.py
    participant STK as stock_video.py
    participant CAP as captions.py
    participant CP as compose.py
    participant FF as FFmpegVideoProcessor
    participant PGS as ProgressStore

    U->>RA: POST /api/render/start (project_id, idea_index)
    RA->>RA: load idea + script_json from project.idea_json
    RA->>RS: create/link Run (DRAFT → RENDERING)
    RA->>RA: ReelPipeline(topic, output, caption_style=project.caption_style)
    RA->>RA: task = task_manager.track_named('render:'+run_id, _run())
    RA->>RA: watchdog task (15 min stall → kill subprocesses + fail run)
    RA-->>U: "Render Pipeline Active…" fragment

    Note over RP: _run_ffmpeg() — stage "outputs"
    RP->>RP: _save_outputs() → run_dir/{idea,script,seo_metadata}.json + caption.txt
    Note over RP: stage "project"
    Note over RP: stage "timeline"
    RP->>NAR: _synthesize_narration(all_lines) [executor thread]
    RP->>STK: _fetch_background_clip(frames, fps) [parallel gather]
    NAR-->>RP: per line (wav_path, duration_s, aligned words)
    STK-->>RP: bg stock mp4 (or gradient fallback)

    loop each body line (idx ≥ 1)
        RP->>CAP: group_by_thought(line, words, llm) → chunks
        RP->>RP: split chunks at CAPTION_MAX_WORDS=3
        RP->>RP: caption_chunk_windows + chunk_word_frames (per-word frames)
        RP->>RP: _render_caption_clip(chunk, frames, fps, font, out, trim_tail=True, style=caption_style)
    end
    Note over RP: hook line → _render_hook_clip (full-line display, no karaoke)

    RP->>CP: build_compose_plan(script, line_data, bg, fps, caption groups)
    RP->>FF: _make_black_base (full-length black clip)
    RP->>FF: Timeline(base + overlays + audio layers).render(progress_callback)
    FF-->>RP: bytes → render_output.mp4 → copied to data/renders/{slug}.mp4
    Note over RP: stage "render"
    RP->>PGS: push({event: complete}) → SSE

    Note over RP: stage "finalize"
    RP->>RP: _extract_screenshots (3 JPEGs)
    RP->>RP: _transcode_720p (h264_nvenc 720×1280 + AAC + faststart)
    RA->>RS: mark_completed(run, output_path, duration)
    RA->>PGS: SSE complete event (run_id, output, duration_s)
```

### 6.2 Narration & caption sync (the hard part)

```mermaid
flowchart TD
    L["script line text"] -->|"synthesize_batch<br/>chatterbox-venv python<br/>one process per run"| W["line_*.wav"]
    W -->|"get_duration (RIFF walk)"| D["duration_s"]
    W -->|"whisper tiny.en --word_timestamps<br/>--device cpu"| T["Whisper JSON (word start/end)"]
    T -->|"align_words<br/>DP alignment (fuse 1–3 tokens,<br/>interpolate unheard words)"| A["script's own words + timings<br/>[{'word', start, end}]"]

    A -->|"group_by_thought<br/>LLM phrase grouping (3–5 words)<br/>fallback: clause-aware chunks"| G["chunks"]
    G -->|"≤3 words per clip"| K["karaoke clips (qtrle transparent)<br/>style=highlight: moving pill<br/>style=plain: static line, no pill"]
    A -->|"hook line → whole-line text"| H["hook.mov"]
```

**Caption style** — the resolved `caption_style` (`highlight` | `plain`,
default `highlight`) comes from the run's `settings_snapshot_json`
(`render_api.start_render`, render_api.py) and is passed into
`ReelPipeline(caption_style=…)`. `_render_caption_frame(words,
highlighted_idx, font_size)` draws each frame; `highlighted_idx=None`
(plain) skips the pill. The pill colour is `0x7C5CFAFF`.

### 6.3 Compose plan

`compose.py: build_compose_plan(...) → ComposePlan` is a **pure function**
(no I/O) so timing math cannot drift from the bake loop. Produces:

- `base_asset` — the full-length black base (`_make_black_base`), background
  and hook/caption clips become overlays
- `overlays` — background mp4, hook.mov, caption chunk clips, outro clip
  (generated default `templates/outro_default.mp4` or the project's
  `asset_outro_clip_id` asset)
- `audio_layers` — one per narration WAV at its line offset
- `fade_in`, `encode`, `total_frames`, `narration_end_frames`

---

## 7. Data Layer

### 7.1 Models & schema

```mermaid
erDiagram
    PROJECTS {
        string id PK
        datetime created_at
        datetime updated_at
        string topic
        string focus
        string title
        text idea_json
        text profile_overrides_json
    }
    RUNS {
        string id PK
        string project_id FK
        string title
        string status
        string selected_idea_id
        json stage_progress
        text settings_snapshot_json
        string output_path
        float duration_s
        string error
        datetime created_at
        datetime updated_at
    }
    APP_SETTINGS {
        string key PK
        string value
        datetime updated_at
    }
    PROJECTS ||--o{ RUNS : "project_id"
```

**Embedding, not tables:** ideas + scripts live inside `projects.idea_json`
(a JSON array of idea dicts, each with an optional `script_json`); `runs`
only link to the selected idea by `selected_idea_id`. `ProjectService`
(`save_ideas / prepend_ideas / update_idea / delete_idea / save_script /
get_script`) performs JSON-blob CRUD. All project-level settings (`format`,
`caption_style`, duration, asset references) live in
`projects.profile_overrides_json` (typed overrides, resolved through
`ProjectProfileService`).

### 7.2 Run state machine (`RunService`)

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> queued
    draft --> rendering
    queued --> rendering
    rendering --> completed : mark_completed
    rendering --> failed : mark_failed / watchdog / cancel
    completed --> queued : re-render
    completed --> rendering
    failed --> queued : retry
    failed --> rendering
    failed --> failed : retry
    completed --> [*]
    failed --> [*]
```

Transitions outside this map raise `InvalidTransitionError`. The `RunStatus`
enum also declares `idea_selected` / `script_ready` (reserved for future
linking states; no transition uses them today). On **startup**,
`_fail_stale_rendering_runs` marks any leftover `rendering` rows as failed
(crashed previous process).

### 7.3 Migrations (chain `schema_001` → `schema_013`)

| Migration | What it does |
|---|---|
| 001 | create `projects` |
| 002 | create `app_settings` |
| 003 | create `runs` |
| 004 | add `app_settings.updated_at` |
| 005 | project override columns (tri-tier settings) |
| 006 | move ideas/scripts from runs → `projects.idea_json` (+ `runs.selected_idea_id`) |
| 007 | drop legacy columns from `projects`/`runs` |
| 008 | rename `projects.script_type` → `topic` + rewrite stored `idea_json` keys (named-param SQLAlchemy 2.0 `text()`) |
| 009 | add `projects.format` (default `narration`) + `caption_style` (default `highlight`) |
| 010 | drop CTA columns (`cta_enabled` / `cta_lead_in` / `cta_display`) — CTA tail replaced by the outro clip |
| 011 | create `assets` + per-project asset reference columns |
| 012 | add `projects.profile_overrides_json`, `topic_profiles` table, `runs.settings_snapshot_json`; fold legacy columns into the JSON and drop them |
| 013 | rename `topic_profiles` table (previously `video_type_profiles`) |

---

## 8. Runtime State & Observability

```mermaid
flowchart LR
    RA["RenderApiController"] -->|"track_named"| BTM["BackgroundTaskManager"]
    RA -->|"register run_id → task"| RTR["RenderTaskRegistry (singleton,<br/>cross-request task map)"]
    RP["ReelPipeline"] -->|"progress_callback"| PGS["ProgressStore"]
    PGS -->|"push"| LS["LogStore (200-entry ring)"]
    PGS -->|"SSE subscribe<br/>keep-alive 15 s"| PA["ProgressApiController<br/>/api/progress/{op_id}"]
    RA -->|"watchdog<br/>15 min no progress"| SG["subprocess_guard.kill_all()"]
    PGS -->|"stage elapsed metrics"| WD["watchdog decision"]
```

- **RenderTaskRegistry** exists because controllers are per-request; live task
  bookkeeping must live in a DI singleton.
- Per-run stdout is **teed to `data/runs/{run_id}.log`** (docker logs rotate;
  LogStore ring overwrites).
- `HistoryService` keeps a file-based run ledger in `data/runs/*.json` (planned
  replacement: the SQLite `runs` table).

---

## 9. Deployment Topology

```mermaid
flowchart LR
    HOST["Host (linux)"] --> DC["docker compose<br/>service: shorts-creator<br/>restart: unless-stopped"]
    DC --> CT["container shorts-creator-shorts-creator-1<br/>python:3.12-slim + ffmpeg<br/>runtime: nvidia (GPU 0)"]
    CT -->|"port ${DSM_PORT:-18080} → 8080"| WEB["Browser :18080"]
    CT -->|"bind mounts"| M1["src/ , templates/ , migrations/ ,<br/>application.yaml , asgi_app.py , data/"]
    CT -->|"framework context"| FX["../../framework/lexigram"]
    CT -->|"tools context"| TL["../tools"]
    CT -->|"TTS venv"| VB["../dsm/chatterbox-venv<br/>(Python 3.11 + torch + chatterbox)"]
    CT -->|"HF cache"| HF["chatterbox model weights<br/>/root/.cache/huggingface/hub"]
    CT -->|"whisper cache"| WC["/root/.cache/whisper/tiny.en.pt"]
    CT -->|"OLLAMA_BASE_URL"| OL["host.docker.internal:11434"]
```

**Startup sequence**: container start → `uvicorn asgi_app:app --reload` →
`Application.boot` → `DatabaseModule` runs Alembic to head (env honors
`SHORTS_CREATOR_DATABASE_URL`) → `PipelineProvider.boot` wires services and
fails stale runs.

### Environment variables

| Var | Purpose |
|---|---|
| `DSM_PORT` | app port (container 8080; host mapping `${DSM_PORT:-18080}`) |
| `DSM_RELOAD` | opt-in `uvicorn --reload` for dev hot-restart (off by default so in-flight renders survive) |
| `SHORTS_CREATOR_DATABASE_URL` | sqlite URL for migrations (auto `+aiosqlite`) |
| `LEX_PROFILE` | config profile selector (dev vs prod LLM providers) |
| `OLLAMA_BASE_URL` | local LLM fallback (host.docker.internal:11434/v1) |
| `GROQ_API_KEYS`, `GEMINI_API_KEYS`, `OPENROUTER_API_KEYS`, `ANTHROPIC_API_KEY` | LLM provider keys (interpolated in `application.prod.yaml` only, i.e. `LEX_PROFILE=prod`) |
| `OPENCODE_ZEN_API_KEY` | opencode-zen LLM provider key (base/dev profile) |
| `PIXABAY_API_KEY`, `PEXELS_API_KEY` | stock-video providers |

**Local-media gotchas (container-local, recreated on rebuild):**
- Whisper model `tiny.en.pt` in `/root/.cache/whisper` — a corrupt copy breaks
  every render (SHA256 mismatch); restore from a valid cache.
- `templates/outro_default.mp4` is generated automatically when missing; the
  compose stage fails only if the generated outro cannot be created in the
  container.

---

## 10. Testing

```mermaid
flowchart LR
    T["tests/ (506 tests)"] --> U1["unit: models, repos, services<br/>(fakes for repos/LLM)"]
    T --> U2["registry tests: topics + formats<br/>(SKILL.md/FORMAT.md loading)"]
    T --> U3["pipeline unit: caption frames,<br/>compose plan, alignment, parsers"]
    T --> U4["controller tests: dashboard states,<br/>create API, settings API (temp DB + alembic head)"]
    T --> I["integration: ffmpeg render progress<br/>(skipif no ffmpeg)"]
    T --> S["scripts/compare_renderers.py<br/>(render + metric parity report)"]
```

Run: `set -a; source .env; set +a; uv run pytest tests -q` · lint: `uv run ruff check`.

The ffmpeg integration test
(`tests/integration/test_ffmpeg_render_progress.py`) is skipped when `ffmpeg`
is not on PATH (`shutil.which("ffmpeg")`); the rest of the suite is fully
mocked and offline.

---

## 11. Key Design Decisions (why it works this way)

1. **Topic vs format split** — `topic` is the *idea source* (prompts, pacing,
   structure from `data/skills/*/SKILL.md`); `format` is the *presentation
   container* (`data/formats/*/FORMAT.md`). Formats drive the renderer
   (`caption_style`); presets were removed.
2. **No LLM in the render pipeline** — script/idea JSON is produced by the
   services (LLM available), then handed to `ReelPipeline`; the pipeline's own
   `_generate_script` is a no-op stub ("LLM not available in pipeline").
3. **Whisper supplies timing only** — its transcription garbles the TTS voice
   ("The day" → "W-day"), so captions always use script words; a DP alignment
   maps script words onto fused Whisper tokens and interpolates unheard words.
4. **Baked caption pixels** — each caption chunk becomes a transparent qtrle
   `.mov` with the karaoke pill drawn into pixels, so per-word sync survives
   the compose stage with one clip per chunk.
5. **Backgrounds from stock footage, not AI images** — Pollinations.ai was
   deprecated (429 rate-limiting); Pixabay/Pexels with gradient fallback.
6. **TTS in a separate venv** — Chatterbox (~3.6 GB torch weights) lives in
   `chatterbox-venv`; the worker loads the model once per run and synthesizes
   every line in one process.
7. **Watchdog + stale-run cleanup** — a 15-minute stall watchdog kills tracked
   subprocesses and fails the run; startup sweeps orphaned `rendering` rows so
   the UI never hangs on a dead pipeline.
8. **720p companion** — FB Reels loads smaller H.264 faster than 1080 HEVC, so
   every render gets a `_720p.mp4` (NVENC, faststart).
