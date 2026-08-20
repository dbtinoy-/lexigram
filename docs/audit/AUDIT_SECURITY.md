# AUDIT_SECURITY.md — Lexigram Framework Security Audit

> **Source**: Live command evidence (pip-audit, ruff bandit rules), framework security rules, and the audit tracker (`docs/AUDIT_TRACKER.md`).

---

## Summary

- Verdict: **WARN** — static analysis findings remain (low-signal noise only)
- Dependency scan: clean (0 vulnerable package(s))
- SAST (ruff `S` rules): 3239 finding(s) (103 unverified, 175 verified low-risk, 2961 low-signal noise)
- Framework security rules: 0 finding(s)
- Tracker areas: 0 total, 0 done

## Dependency Scan

- Command: `uv run pip-audit --timeout 60`
- Exit code: `0`
- Duration: `38561 ms`
- Vulnerable packages: 0
- Summary: `No known vulnerabilities found`

```text
Name            Skip Reason
--------------- ---------------------------------------------------------------------------------
lexigram-ai-mcp Dependency not found on PyPI and could not be audited: lexigram-ai-mcp (0.1.3008)
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
No known vulnerabilities found
```

## Static Analysis (ruff bandit rules)

- Exit code: `1`

### Findings (unverified)

| File | Line | Rule | Message |
|------|------|------|---------|
| `demos/fullstack-demo/src/shorts_creator/controllers/api/render_api/controller.py` | 246 | `S103` | `os.chmod` setting a permissive mask `0o755` on file or directory |
| `demos/fullstack-demo/src/shorts_creator/pipeline/reel_core.py` | 91 | `S103` | `os.chmod` setting a permissive mask `0o755` on file or directory |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 43 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 45 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/outro.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 68 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 70 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/outro.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 72 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/music.wav" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 122 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 125 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/outro.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 137 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 139 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/outro.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 175 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 177 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/td" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 179 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/outro.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 226 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 228 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/td" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 231 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/outro.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 254 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 256 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/td" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 258 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/outro.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 267 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 269 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/td" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 272 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/outro.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 310 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 312 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/outro.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 343 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 378 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 380 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/outro.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 425 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 427 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/outro.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 434 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 436 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/outro.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 449 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 451 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/td" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 452 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/music.mp3" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 465 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 467 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/td" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 468 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/wm.png" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 478 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 492 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 546 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 557 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 585 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/seg0.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 586 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/seg1.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 587 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/seg2.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 592 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 595 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/outro.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 651 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 653 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/td" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 656 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/outro.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 704 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 706 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/outro.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 723 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 725 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/outro.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 727 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/wm.png" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 743 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 745 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/outro.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 747 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/wm.png" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 770 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 772 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/outro.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 774 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/outro_text.mov" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 797 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 799 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/outro.mp4" |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 286 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/x.mp4" |
| `demos/fullstack-demo/tests/test_music_beat.py` | 92 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/m.wav" |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 297 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/line.wav" |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 297 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/padded.wav" |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 303 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/padded.wav" |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 329 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/a.wav" |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 329 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/b.wav" |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 350 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/a.wav" |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 67 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/custom.ttf" |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 69 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/custom.ttf" |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 144 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/m.wav" |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 127 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/l0.wav" |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 128 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/l1.wav" |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 129 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/l2.wav" |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 136 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 147 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_pipeline_field_contracts.py` | 38 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_pipeline_field_contracts.py` | 40 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/outro.mp4" |
| `demos/fullstack-demo/tests/test_pipeline_field_contracts.py` | 46 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_pipeline_field_contracts.py` | 48 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/outro.mp4" |
| `demos/fullstack-demo/tests/test_pipeline_field_contracts.py` | 57 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/contract.mp4" |
| `demos/fullstack-demo/tests/test_pipeline_stage_accents.py` | 143 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_progress_api.py` | 21 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/video.mp4" |
| `demos/fullstack-demo/tests/test_progress_api.py` | 24 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/video.mp4" |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 266 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/v.mp4" |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 287 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/v.mp4" |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 309 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/v.mp4" |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 368 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/v.mp4" |
| `demos/fullstack-demo/tests/test_render_progress.py` | 25 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/video.mp4" |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 117 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 194 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 260 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/" |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 270 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 378 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 714 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/bg.mp4" |
| `demos/fullstack-demo/tests/test_stock_video.py` | 48 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/out.mp4" |
| `demos/fullstack-demo/tests/test_stock_video.py` | 60 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/out.mp4" |
| `demos/fullstack-demo/tests/test_stock_video.py` | 76 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/out.mp4" |
| `demos/fullstack-demo/tests/test_stock_video.py` | 96 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/out.mp4" |
| `demos/fullstack-demo/tests/test_stock_video.py` | 119 | `S108` | Probable insecure usage of temporary file or directory: "/tmp/out.mp4" |

### Verified Low-Risk Families (reviewed 2026-08-20; all closed — see notes below)

- Count: 175

| File | Line | Rule | Message |
|------|------|------|---------|
| `demos/fullstack-demo/migrations/primary/versions/schema_012_project_profiles.py` | 156 | `S608` | Possible SQL injection vector through string-based query construction |
| `demos/fullstack-demo/scripts/compare_renderers.py` | 44 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/scripts/compare_renderers.py` | 118 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/scripts/compare_renderers.py` | 119 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/scripts/compare_renderers.py` | 151 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/scripts/compare_renderers.py` | 152 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/scripts/compare_renderers.py` | 243 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/scripts/compare_renderers.py` | 244 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/scripts/e2e_compositions.py` | 155 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/scripts/e2e_compositions.py` | 171 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/scripts/e2e_compositions.py` | 172 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/src/shorts_creator/controllers/api/preview_api.py` | 24 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |
| `demos/fullstack-demo/src/shorts_creator/controllers/api/render_api/media.py` | 104 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/src/shorts_creator/controllers/api/render_api/media.py` | 105 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/src/shorts_creator/controllers/api/render_api/media.py` | 127 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/src/shorts_creator/controllers/api/render_api/media.py` | 128 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/src/shorts_creator/controllers/api/render_api/media.py` | 181 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/src/shorts_creator/controllers/api/render_api/media.py` | 182 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/src/shorts_creator/controllers/assets.py` | 39 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/assets.py` | 190 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/assets.py` | 503 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/assets.py` | 632 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/project_runs.py` | 132 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/project_runs.py` | 326 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/project_runs.py` | 395 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/project_runs.py` | 458 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/project_runs.py` | 502 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/project_runs.py` | 565 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/project_runs.py` | 587 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/project_runs.py` | 594 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/projects/cards.py` | 10 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/projects/cards.py` | 45 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/projects/cards.py` | 120 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/projects/cards.py` | 132 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/projects/dashboard.py` | 60 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/projects/dashboard.py` | 100 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/projects/dashboard.py` | 133 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/projects/dashboard.py` | 189 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/projects/ideas.py` | 33 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/projects/profile.py` | 90 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/projects/profile.py` | 114 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/projects/runs.py` | 16 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/projects/runs.py` | 100 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/projects/runs.py` | 147 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/projects/scripts.py` | 49 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/projects/stats.py` | 6 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/render.py` | 161 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/render.py` | 170 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/render.py` | 203 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/render.py` | 214 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/render.py` | 328 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/scripts.py` | 136 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/scripts.py` | 163 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/scripts.py` | 305 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/scripts.py` | 368 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/scripts.py` | 390 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/scripts.py` | 489 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/settings.py` | 286 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/settings.py` | 292 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/videos.py` | 140 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/controllers/videos.py` | 326 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/pipeline/background.py` | 20 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/src/shorts_creator/pipeline/background.py` | 21 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/src/shorts_creator/pipeline/background.py` | 41 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/src/shorts_creator/pipeline/background.py` | 42 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/src/shorts_creator/pipeline/background.py` | 77 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/src/shorts_creator/pipeline/background.py` | 78 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/src/shorts_creator/pipeline/background.py` | 131 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/src/shorts_creator/pipeline/background.py` | 132 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/src/shorts_creator/pipeline/background.py` | 164 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/src/shorts_creator/pipeline/background.py` | 165 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/src/shorts_creator/pipeline/bake.py` | 75 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/src/shorts_creator/pipeline/bake.py` | 84 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/src/shorts_creator/pipeline/bake.py` | 85 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/src/shorts_creator/pipeline/bake.py` | 119 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/src/shorts_creator/pipeline/bake.py` | 120 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/src/shorts_creator/pipeline/caption_text.py` | 203 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/src/shorts_creator/pipeline/caption_text.py` | 236 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/src/shorts_creator/pipeline/caption_text.py` | 630 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/src/shorts_creator/pipeline/music_beat.py` | 136 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/src/shorts_creator/pipeline/music_beat.py` | 137 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/src/shorts_creator/pipeline/outro.py` | 43 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/src/shorts_creator/pipeline/outro.py` | 44 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/src/shorts_creator/pipeline/outro.py` | 145 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/src/shorts_creator/pipeline/outro.py` | 146 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/src/shorts_creator/pipeline/prompts.py` | 256 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |
| `demos/fullstack-demo/src/shorts_creator/pipeline/reel_finalize.py` | 29 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/src/shorts_creator/pipeline/reel_finalize.py` | 30 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/src/shorts_creator/pipeline/reel_finalize.py` | 128 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/src/shorts_creator/pipeline/reel_finalize.py` | 140 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/src/shorts_creator/pipeline/reel_finalize.py` | 141 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/src/shorts_creator/pipeline/reel_finalize.py` | 159 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/src/shorts_creator/pipeline/reel_finalize.py` | 160 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/src/shorts_creator/pipeline/stock_video.py` | 71 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |
| `demos/fullstack-demo/src/shorts_creator/pipeline/stock_video.py` | 77 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/src/shorts_creator/pipeline/stock_video.py` | 78 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/src/shorts_creator/pipeline/stock_video.py` | 136 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |
| `demos/fullstack-demo/src/shorts_creator/pipeline/stock_video.py` | 161 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |
| `demos/fullstack-demo/src/shorts_creator/pipeline/stock_video.py` | 165 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |
| `demos/fullstack-demo/src/shorts_creator/pipeline/subprocess_guard.py` | 25 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/src/shorts_creator/ui/button.py` | 83 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/components/concept_list_item.py` | 88 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/components/concept_list_item.py` | 158 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/components/idea_editor.py` | 149 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/components/pipeline_tracker.py` | 124 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/components/project_tabs.py` | 58 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/components/project_tabs.py` | 76 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/components/project_tabs.py` | 171 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/components/provider_card.py` | 33 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/components/run_history.py` | 25 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/components/run_history.py` | 225 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/components/script_viewer.py` | 37 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/components/script_viewer.py` | 54 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/components/script_viewer.py` | 87 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/components/script_viewer.py` | 225 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/components/script_viewer.py` | 242 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/components/script_viewer.py` | 266 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/components/settings_profile.py` | 148 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/icons.py` | 8 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/icons.py` | 70 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/pages/new_project_main.py` | 109 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/pages/new_project_main.py` | 348 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/pages/new_project_main.py` | 349 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/pages/new_project_main.py` | 361 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/pages/new_project_main.py` | 420 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/pages/new_project_panels/core.py` | 40 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/pages/new_project_preview.py` | 25 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |
| `demos/fullstack-demo/src/shorts_creator/ui/pages/new_project_preview.py` | 95 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/pages/new_project_preview.py` | 205 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/pages/new_project_profile.py` | 146 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/pages/new_project_profile.py` | 158 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/pages/new_project_settings.py` | 132 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/pages/new_project_settings.py` | 133 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/pages/new_project_settings.py` | 147 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/pages/new_project_wizard.py` | 32 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/pages/new_project_wizard.py` | 248 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/shell.py` | 142 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/shell.py` | 149 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/shell.py` | 152 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/shell.py` | 155 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/src/shorts_creator/ui/shell.py` | 201 | `S704` | Unsafe use of `markupsafe.Markup` detected |
| `demos/fullstack-demo/tests/test_app_settings_migration.py` | 22 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/tests/test_app_settings_migration.py` | 51 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/tests/test_app_settings_migration.py` | 67 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/tests/test_app_settings_migration.py` | 68 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 41 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 73 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 74 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 126 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 127 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 154 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 155 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/tests/test_hardening.py` | 137 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/tests/test_hardening.py` | 138 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/tests/test_hardening.py` | 156 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/tests/test_hardening.py` | 157 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/tests/test_hardening.py` | 176 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/tests/test_hardening.py` | 177 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/tests/test_migration_schema_012.py` | 37 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/tests/test_migration_schema_012.py` | 75 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/tests/test_migration_schema_012.py` | 172 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/tests/test_migration_schema_012.py` | 214 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/tests/test_override_reset.py` | 39 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/tests/test_preview_fields_harness.py` | 20 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/tests/test_preview_fields_harness.py` | 21 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 76 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/tests/test_project_repository.py` | 25 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 35 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/tests/test_render_duration.py` | 20 | `S603` | `subprocess` call: check for execution of untrusted input |
| `demos/fullstack-demo/tests/test_render_duration.py` | 21 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/tests/test_settings_api.py` | 34 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/tests/test_settings_store.py` | 21 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/tests/test_topic_profile_service.py` | 30 | `S607` | Starting a process with a partial executable path |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 39 | `S607` | Starting a process with a partial executable path |
| `demos/llm-experiment/harness.py` | 272 | `S311` | Standard pseudo-random generators are not suitable for cryptographic purposes |

### Low-Signal Rules (S101 asserts, S105/S106 hardcoded strings)

- Count: 2961

| File | Line | Rule | Message |
|------|------|------|---------|
| `demos/fullstack-demo/tests/integration/test_ffmpeg_render_progress.py` | 94 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/integration/test_ffmpeg_render_progress.py` | 99 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/integration/test_ffmpeg_render_progress.py` | 100 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/integration/test_ffmpeg_render_progress.py` | 103 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 7 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 8 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 9 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 13 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 14 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 18 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 19 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 23 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 24 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 25 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 32 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 33 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 34 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 35 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 36 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 37 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 50 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 51 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 52 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 58 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 62 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 63 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 68 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 69 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 74 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_action_button.py` | 75 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_active_context.py` | 42 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_active_context.py` | 43 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_active_context.py` | 44 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_active_context.py` | 51 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_active_context.py` | 59 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_app_config.py` | 13 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_app_config.py` | 20 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_app_config.py` | 21 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_app_config.py` | 22 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_app_config.py` | 28 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_app_config.py` | 29 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_app_config.py` | 30 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_app_settings_migration.py` | 41 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_app_settings_migration.py` | 61 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_app_settings_migration.py` | 62 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_app_settings_migration.py` | 63 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_app_settings_migration.py` | 89 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_app_settings_migration.py` | 101 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_app_settings_migration.py` | 102 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_app_settings_migration.py` | 182 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_app_settings_migration.py` | 183 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_app_settings_migration.py` | 184 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_app_settings_migration.py` | 191 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_app_settings_migration.py` | 192 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_repository.py` | 45 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_repository.py` | 46 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_repository.py` | 47 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_repository.py` | 48 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_repository.py` | 57 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_repository.py` | 59 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_repository.py` | 65 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_repository.py` | 69 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_repository.py` | 70 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_resolver.py` | 24 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_resolver.py` | 30 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_resolver.py` | 36 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_resolver.py` | 41 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_resolver.py` | 42 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_resolver.py` | 51 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_resolver.py` | 52 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_resolver.py` | 60 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_resolver.py` | 66 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_resolver.py` | 73 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_resolver.py` | 85 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_selectors.py` | 85 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_selectors.py` | 101 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_selectors.py` | 102 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_selectors.py` | 103 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_selectors.py` | 104 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_selectors.py` | 105 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_selectors.py` | 119 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_selectors.py` | 120 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_selectors.py` | 137 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_selectors.py` | 152 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_selectors.py` | 153 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_selectors.py` | 154 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_selectors.py` | 155 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_selectors.py` | 156 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_selectors.py` | 172 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_selectors.py` | 173 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_selectors.py` | 174 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_selectors.py` | 175 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_selectors.py` | 188 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_selectors.py` | 189 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_service.py` | 61 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_service.py` | 62 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_service.py` | 64 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_service.py` | 65 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_service.py` | 66 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_service.py` | 82 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_service.py` | 84 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_service.py` | 92 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_service.py` | 93 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_service.py` | 94 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_service.py` | 101 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_service.py` | 107 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_service.py` | 108 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_service.py` | 113 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_service.py` | 114 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_service.py` | 115 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_service.py` | 116 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_asset_service.py` | 117 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_api.py` | 65 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_api.py` | 67 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_api.py` | 68 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_api.py` | 81 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_api.py` | 89 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_api.py` | 92 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_api.py` | 101 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_api.py` | 102 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_api.py` | 109 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_api.py` | 114 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_api.py` | 128 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_api.py` | 133 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_api.py` | 141 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_api.py` | 142 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_api.py` | 149 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_api.py` | 154 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_api.py` | 158 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_api.py` | 162 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 43 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 44 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 45 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 46 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 54 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 55 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 63 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 64 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 72 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 79 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 80 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 91 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 92 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 99 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 104 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 123 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 129 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 130 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 142 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 143 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 155 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 157 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 193 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 194 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 221 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 222 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 223 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 224 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 225 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 226 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 237 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 243 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_assets_pages.py` | 246 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 168 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 169 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 174 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 175 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 176 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 177 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 178 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 184 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 185 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 186 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 187 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 188 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 192 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 193 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 207 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 210 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 211 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 242 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 272 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 273 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 301 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 302 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 328 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 329 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 367 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 368 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 369 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 370 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 405 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 406 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 426 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 427 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 428 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 429 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 461 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 462 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 481 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 482 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 483 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_async_feedback.py` | 495 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_auth_middleware.py` | 48 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_auth_middleware.py` | 57 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_auth_middleware.py` | 58 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_auth_middleware.py` | 67 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_auth_middleware.py` | 68 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_auth_middleware.py` | 79 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_auth_middleware.py` | 80 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_auth_middleware.py` | 89 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_auth_middleware.py` | 90 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_background_op_feedback.py` | 144 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_background_op_feedback.py` | 145 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_background_op_feedback.py` | 146 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_background_op_feedback.py` | 147 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_background_op_feedback.py` | 148 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_background_op_feedback.py` | 149 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_background_op_feedback.py` | 150 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_background_op_feedback.py` | 187 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_background_op_feedback.py` | 188 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_background_op_feedback.py` | 189 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_background_op_feedback.py` | 190 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_background_op_feedback.py` | 191 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_background_op_feedback.py` | 192 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_background_op_feedback.py` | 193 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_background_op_feedback.py` | 232 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_background_op_feedback.py` | 266 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 24 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 25 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 26 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 27 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 31 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 35 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 54 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 70 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 72 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 73 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 84 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 101 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 106 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 107 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 113 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 124 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 137 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 144 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 154 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 155 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 156 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 167 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 178 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 195 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 199 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 202 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 206 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 210 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 223 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 225 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_caption_styles.py` | 237 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 56 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 57 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 58 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 59 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 60 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 61 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 67 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 68 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 105 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 106 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 107 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 119 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 120 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 121 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 148 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 149 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 176 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 177 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 178 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 183 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 188 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 195 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 221 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 222 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 227 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 228 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 233 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 238 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 243 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 248 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 252 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 254 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 260 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 261 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compare_renderers_metrics.py` | 309 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 49 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 50 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 51 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 52 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 53 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 54 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 55 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 56 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 76 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 77 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 101 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 131 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 132 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 142 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 184 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 185 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 186 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 189 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 192 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 193 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 236 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 237 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 238 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 241 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 243 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 262 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 276 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 277 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 285 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 287 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 317 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 318 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 319 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 321 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 322 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 324 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 326 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 327 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 328 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 329 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 330 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 331 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 333 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 334 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 335 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 345 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 346 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 347 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 348 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 386 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 387 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 388 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 389 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 398 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 439 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 440 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 441 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 455 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 456 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 457 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 472 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 473 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 480 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 481 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 482 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 483 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 484 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 495 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 496 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 497 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 498 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 505 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 506 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 507 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 516 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 523 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 552 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 561 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 575 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 599 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 600 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 605 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 606 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 617 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 618 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 619 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 620 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 647 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 661 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 662 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 663 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 665 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 675 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 677 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 692 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 693 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 710 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 711 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 731 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 732 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 733 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 734 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 735 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 750 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 751 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 757 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 782 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 788 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 789 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_plan.py` | 802 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 180 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 183 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 184 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 185 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 186 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 187 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 188 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 189 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 195 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 215 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 218 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 238 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 244 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 252 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 253 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 255 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 260 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 269 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 275 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 286 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 295 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 301 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 303 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 305 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 313 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 319 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 326 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 333 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 374 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 375 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 376 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 377 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 378 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 379 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 380 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 381 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 382 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 383 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 384 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 385 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 386 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 387 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 388 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 389 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 390 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 391 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 392 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 396 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 397 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 398 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 404 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 405 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 406 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 407 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 411 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 460 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 461 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 475 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 483 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 484 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 485 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 486 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 487 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 499 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 500 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 506 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 507 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 508 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 524 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 527 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 528 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 529 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 530 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 531 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 541 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 560 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 563 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 564 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 565 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 566 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 567 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 568 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 585 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 587 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 601 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 603 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 618 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 621 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 622 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 623 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 624 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 641 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 642 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 646 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 647 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 651 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 652 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 656 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 657 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 661 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 662 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 663 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 664 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 666 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 667 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 668 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 669 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 670 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 676 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 677 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 681 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 685 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 689 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 692 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 696 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 697 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 698 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 704 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 705 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 706 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 714 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 715 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 716 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 717 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 718 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 724 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_compose_settings.py` | 725 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 38 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 39 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 40 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 52 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 54 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 55 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 64 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 65 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 67 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 79 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 81 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 86 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 87 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 89 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 94 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 95 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 97 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 106 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 109 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 110 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 115 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 116 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 118 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 123 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_composer_presets_api.py` | 131 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_capabilities.py` | 11 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_capabilities.py` | 14 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_capabilities.py` | 18 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_capabilities.py` | 23 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_capabilities.py` | 24 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_capabilities.py` | 25 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_capabilities.py` | 28 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_capabilities.py` | 35 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_capabilities.py` | 38 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_capabilities.py` | 39 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_capabilities.py` | 50 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_matcher.py` | 28 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_matcher.py` | 29 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_matcher.py` | 44 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_matcher.py` | 45 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_matcher.py` | 57 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_matcher.py` | 69 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_matcher.py` | 70 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_matcher.py` | 84 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_matcher.py` | 85 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_matcher.py` | 101 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_matcher.py` | 115 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_matcher.py` | 116 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_contract_matcher.py` | 119 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_core_config.py` | 17 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_core_config.py` | 18 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_core_config.py` | 21 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_critique_tools.py` | 29 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_critique_tools.py` | 30 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_critique_tools.py` | 31 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_critique_tools.py` | 50 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_critique_tools.py` | 51 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_critique_tools.py` | 52 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_critique_tools.py` | 70 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_critique_tools.py` | 71 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_critique_tools.py` | 72 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_critique_tools.py` | 80 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_critique_tools.py` | 81 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_critique_tools.py` | 82 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_critique_tools.py` | 89 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_critique_tools.py` | 90 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_critique_tools.py` | 91 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_critique_tools.py` | 92 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_e2e_matrix_yaml.py` | 17 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_e2e_matrix_yaml.py` | 18 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_e2e_matrix_yaml.py` | 19 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_e2e_matrix_yaml.py` | 20 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_e2e_matrix_yaml.py` | 26 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_e2e_matrix_yaml.py` | 27 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_e2e_matrix_yaml.py` | 28 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_e2e_matrix_yaml.py` | 29 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_e2e_matrix_yaml.py` | 35 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_e2e_matrix_yaml.py` | 36 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 85 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 91 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 95 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 99 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 106 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 107 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 108 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 114 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 120 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 130 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 139 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 148 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 155 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 164 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 171 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 182 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 191 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 204 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 211 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 218 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 222 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 227 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 232 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 237 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 244 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 248 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 258 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 259 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 270 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 275 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 280 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 287 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 298 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 310 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 315 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 329 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 330 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 331 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 332 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 333 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 334 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 352 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 353 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 372 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 373 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 374 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 375 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 386 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 387 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 392 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 393 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 398 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 402 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 420 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 425 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 435 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 455 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 456 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 467 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 468 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 475 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 476 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 485 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 486 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 487 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_form_provenance.py` | 488 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 68 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 73 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 74 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 81 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 82 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 83 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 90 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 91 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 92 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 100 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 108 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 124 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 125 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 127 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 129 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 142 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 152 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 153 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 154 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 164 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 166 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 167 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 168 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_format_requires.py` | 179 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 32 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 36 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 37 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 38 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 42 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 43 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 44 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 48 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 50 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 53 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 61 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 62 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 63 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 71 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 72 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 81 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 82 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 108 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 109 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 124 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 125 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 130 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 134 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 135 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 136 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 137 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 138 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 139 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 143 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 145 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 146 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 147 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 148 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 174 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 175 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 180 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 184 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 185 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 186 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 187 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 188 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 189 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 190 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 194 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 196 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 197 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 198 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 221 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 227 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 277 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 311 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 331 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 357 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 358 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 363 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 368 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 369 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_formats.py` | 374 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_framework_compose_imports.py` | 15 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_framework_compose_imports.py` | 21 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_framework_compose_imports.py` | 26 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_framework_compose_imports.py` | 27 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_framework_compose_imports.py` | 28 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_framework_compose_imports.py` | 36 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_framework_compose_imports.py` | 127 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_framework_compose_imports.py` | 142 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_framework_compose_imports.py` | 143 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_framework_compose_imports.py` | 145 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_framework_compose_imports.py` | 156 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_framework_compose_imports.py` | 157 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_generate_seo_persists.py` | 90 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_generate_seo_persists.py` | 92 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_generate_seo_persists.py` | 93 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_generate_seo_persists.py` | 100 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_generate_seo_persists.py` | 123 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_generate_seo_persists.py` | 124 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_generate_seo_persists.py` | 125 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_generate_seo_persists.py` | 126 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_generate_seo_persists.py` | 133 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_generate_seo_persists.py` | 134 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_hardening.py` | 42 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_hardening.py` | 43 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_hardening.py` | 50 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_hardening.py` | 56 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_hardening.py` | 57 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_hardening.py` | 61 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_hardening.py` | 64 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_hardening.py` | 67 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_hardening.py` | 68 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_hardening.py` | 81 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_hardening.py` | 82 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_hardening.py` | 91 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_hardening.py` | 101 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_hardening.py` | 111 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_hardening.py` | 122 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_hardening.py` | 123 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_hardening.py` | 125 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_hardening.py` | 126 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_hardening.py` | 127 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_hardening.py` | 175 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_hardening.py` | 195 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_hardening.py` | 196 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_history_project_link.py` | 94 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_history_project_link.py` | 95 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_history_project_link.py` | 96 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_history_project_link.py` | 108 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_history_project_link.py` | 109 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_history_project_link.py` | 141 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_history_project_link.py` | 142 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_history_project_link.py` | 143 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_history_project_link.py` | 152 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_history_project_link.py` | 153 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_history_project_link.py` | 161 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_history_project_link.py` | 170 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_history_project_link.py` | 171 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_homepage_root_redirect.py` | 8 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_homepage_root_redirect.py` | 9 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 112 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 113 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 148 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 149 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 150 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 156 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 162 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 189 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 190 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 214 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 256 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 276 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 296 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 297 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 330 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 331 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 349 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 350 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 402 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 403 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 416 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 417 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 444 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_html_escaping_regression.py` | 457 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_ideas_clear_fields.py` | 91 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_ideas_clear_fields.py` | 107 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_ideas_clear_fields.py` | 121 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_ideas_clear_fields.py` | 122 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_ideas_clear_fields.py` | 138 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_ideas_clear_fields.py` | 155 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_ideas_clear_fields.py` | 156 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_ideas_clear_fields.py` | 157 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_ideas_clear_fields.py` | 179 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_log_store.py` | 9 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_log_store.py` | 10 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_log_store.py` | 11 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_log_store.py` | 17 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_log_store.py` | 18 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_log_store.py` | 19 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_log_store.py` | 25 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_log_store.py` | 37 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_log_store.py` | 38 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_logs_api.py` | 16 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_logs_api.py` | 17 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_logs_api.py` | 18 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_logs_api.py` | 26 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_migration_schema_012.py` | 94 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_migration_schema_012.py` | 105 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_migration_schema_012.py` | 107 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_migration_schema_012.py` | 114 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_migration_schema_012.py` | 124 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_migration_schema_012.py` | 125 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_migration_schema_012.py` | 130 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_migration_schema_012.py` | 156 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_migration_schema_012.py` | 162 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_migration_schema_012.py` | 235 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_migration_schema_012.py` | 236 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_migration_schema_012.py` | 237 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_migration_schema_012.py` | 246 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_migration_schema_012.py` | 247 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_migration_schema_012.py` | 251 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_migration_schema_012.py` | 252 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_migration_schema_012.py` | 253 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_migration_schema_012.py` | 260 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_migration_schema_012.py` | 261 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_music_beat.py` | 17 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_music_beat.py` | 18 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_music_beat.py` | 23 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_music_beat.py` | 26 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_music_beat.py` | 33 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_music_beat.py` | 38 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_music_beat.py` | 43 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_music_beat.py` | 49 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_music_beat.py` | 53 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_music_beat.py` | 61 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_music_beat.py` | 75 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_music_beat.py` | 76 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_music_beat.py` | 82 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_music_beat.py` | 102 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_music_beat.py` | 103 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_myth_format.py` | 23 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_myth_format.py` | 24 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_myth_format.py` | 25 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_myth_format.py` | 26 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_myth_format.py` | 31 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_myth_format.py` | 32 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_myth_format.py` | 33 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_myth_format.py` | 34 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_myth_format.py` | 35 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_myth_format.py` | 37 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_myth_format.py` | 42 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_myth_format.py` | 54 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_myth_format.py` | 87 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_myth_format.py` | 88 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_myth_format.py` | 89 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_myth_format.py` | 90 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 32 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 33 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 34 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 54 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 56 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 57 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 60 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 61 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 63 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 83 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 85 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 86 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 87 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 103 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 105 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 106 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 119 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 120 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 121 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 144 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 145 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 147 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 148 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 155 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 156 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 157 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 158 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 159 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 160 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 161 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 162 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 178 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 179 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 180 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 182 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 184 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 189 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 190 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 191 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 195 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 196 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 211 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 213 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 214 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 221 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 222 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 223 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 261 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 262 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 263 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 264 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 283 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 299 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 300 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 301 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 302 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 303 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 304 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 305 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 309 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 312 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 313 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 314 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 315 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 334 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 336 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 337 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 338 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 352 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 353 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 354 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 379 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 380 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 381 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_narration_alignment.py` | 382 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_new_project_preview.py` | 98 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_new_project_preview.py` | 104 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_new_project_preview.py` | 116 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_new_project_preview.py` | 122 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_new_project_preview.py` | 123 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_new_project_preview.py` | 134 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_new_project_preview.py` | 135 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_new_project_preview.py` | 141 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_new_project_preview.py` | 145 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_new_project_preview.py` | 146 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_new_project_preview.py` | 157 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_new_project_preview.py` | 159 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_new_project_preview.py` | 168 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_new_project_preview.py` | 169 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_new_project_preview.py` | 170 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_new_project_preview.py` | 171 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_new_project_preview.py` | 172 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_new_project_preview.py` | 176 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_new_project_preview.py` | 177 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_new_project_preview.py` | 178 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_new_project_preview.py` | 179 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_no_static_colors.py` | 47 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_no_static_colors.py` | 59 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 83 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 97 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 99 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 100 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 108 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 115 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 123 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 132 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 133 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 140 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 151 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 152 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 158 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 169 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 171 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 172 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 185 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 186 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 194 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 214 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 216 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 217 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 223 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 224 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_override_reset.py` | 230 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 77 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 78 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 85 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 86 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 103 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 104 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 121 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 129 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 130 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 136 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 139 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 143 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 156 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 161 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 164 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 165 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 166 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 171 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 172 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 223 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 224 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 233 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 242 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_creation_gate.py` | 243 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_drift.py` | 58 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_drift.py` | 67 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_drift.py` | 68 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_drift.py` | 76 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_drift.py` | 95 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_drift.py` | 114 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_drift.py` | 122 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_drift.py` | 126 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_drift.py` | 210 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_drift.py` | 211 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_drift.py` | 218 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_drift.py` | 227 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_drift.py` | 242 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pair_drift.py` | 252 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 38 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 39 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 40 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 41 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 52 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 68 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 69 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 73 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 83 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 136 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 137 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 138 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 147 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 148 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 172 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 217 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 247 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 248 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 286 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 287 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 288 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 308 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 309 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 310 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 336 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 337 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 338 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 356 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 357 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 358 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 381 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 382 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 432 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 433 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 434 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_assets.py` | 435 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 47 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 51 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 65 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 71 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 75 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 79 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 85 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 87 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 91 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 97 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 99 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 107 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 108 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 111 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 117 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 121 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 122 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 144 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 148 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 154 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 173 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_dimensions.py` | 188 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_field_contracts.py` | 51 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_field_contracts.py` | 58 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_field_contracts.py` | 71 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_field_contracts.py` | 72 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_field_contracts.py` | 81 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_field_contracts.py` | 82 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_field_contracts.py` | 83 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_field_contracts.py` | 91 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_field_contracts.py` | 98 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_map.py` | 10 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_map.py` | 21 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_map.py` | 22 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_map.py` | 23 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_map.py` | 24 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_map.py` | 25 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_map.py` | 26 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_map.py` | 27 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_map.py` | 30 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_map.py` | 33 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_map.py` | 36 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_map.py` | 37 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_no_kdenlive.py` | 19 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_no_kdenlive.py` | 20 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_no_kdenlive.py` | 21 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_no_kdenlive.py` | 31 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_no_kdenlive.py` | 42 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_no_kdenlive.py` | 48 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_no_kdenlive.py` | 50 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_outro.py` | 19 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_outro.py` | 20 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_outro.py` | 29 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_outro.py` | 30 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_outro.py` | 33 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_outro.py` | 38 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_outro.py` | 39 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_outro.py` | 44 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_outro.py` | 45 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_outro.py` | 68 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_outro.py` | 69 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_stage_accents.py` | 197 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_stage_accents.py` | 210 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_stage_accents.py` | 224 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_stage_accents.py` | 238 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_stage_accents.py` | 248 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_stage_accents.py` | 262 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_pipeline_stage_accents.py` | 276 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_preview_fields_harness.py` | 27 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_preview_fields_harness.py` | 28 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_preview_form_wiring.py` | 163 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_preview_form_wiring.py` | 169 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_preview_form_wiring.py` | 174 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_preview_form_wiring.py` | 178 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_preview_form_wiring.py` | 185 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_preview_form_wiring.py` | 190 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_preview_form_wiring.py` | 195 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_preview_form_wiring.py` | 199 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 41 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 44 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 47 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 52 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 55 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 58 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 61 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 67 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 68 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 69 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 70 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 71 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 75 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 76 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 80 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 92 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 93 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 117 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 125 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 129 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 130 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 144 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 145 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 146 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 147 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 152 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 153 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 158 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 159 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 175 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 176 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 177 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 178 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 179 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 180 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 186 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 187 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 191 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 211 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 212 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 216 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 220 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_cards.py` | 224 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 110 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 111 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 112 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 113 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 123 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 124 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 125 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 134 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 145 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 146 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 153 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 154 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 161 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 163 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 164 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 165 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 171 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 173 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 180 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 181 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 182 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 183 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 189 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 190 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 191 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 192 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 199 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 200 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 201 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 208 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 210 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 211 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 225 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 227 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_flow_contract.py` | 228 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 47 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 48 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 49 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 50 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 51 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 52 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 53 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 58 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 74 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 75 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 90 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 91 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 92 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 93 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 94 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 95 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 106 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 107 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 108 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 109 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 110 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 119 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 120 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 121 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 126 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 127 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 128 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 129 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 130 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 131 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 132 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 133 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 139 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 148 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 165 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 179 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 180 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 181 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 182 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 183 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_profile_resolve_composer.py` | 184 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_progress_api.py` | 16 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_progress_api.py` | 25 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_progress_api.py` | 31 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_progress_store.py` | 42 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_progress_store.py` | 43 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_progress_store.py` | 44 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_progress_store.py` | 45 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_progress_store.py` | 46 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_progress_store.py` | 47 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_progress_store.py` | 72 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_progress_store.py` | 73 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 109 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 110 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 111 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 112 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 113 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 118 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 122 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 124 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 125 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 126 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 127 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 128 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 129 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 133 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 136 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 140 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 145 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 146 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 147 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 154 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 155 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 156 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 157 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 158 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 159 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 160 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 167 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 168 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 172 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 173 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 174 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 180 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 181 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 182 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 183 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 184 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 185 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 186 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 190 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 194 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 195 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 196 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 197 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 204 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 205 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 206 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 207 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 210 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 211 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 216 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 217 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 218 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 221 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 222 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 227 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 228 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 232 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 233 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 234 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 235 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 253 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 254 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 273 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 274 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 288 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 289 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 290 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 302 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 315 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 316 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 317 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 323 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 324 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 325 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 326 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 332 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 333 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 334 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 335 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 336 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 337 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 338 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 339 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 340 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 344 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 345 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 346 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 350 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 353 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 354 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 355 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 356 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 357 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 358 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 362 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 363 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 364 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 365 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 369 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 371 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 375 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 376 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 377 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 378 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 380 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 384 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 388 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 389 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 393 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 394 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 395 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 396 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 410 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 411 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 412 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 421 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 422 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 423 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 432 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 433 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 434 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 443 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 444 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 445 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 449 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 450 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 451 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 452 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 453 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 457 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 458 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 460 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 461 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 464 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 468 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 469 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 473 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 475 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 476 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 477 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 481 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 482 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 486 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 488 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 489 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 490 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 491 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 492 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 504 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 505 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 510 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 514 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 515 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 524 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 525 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 529 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 531 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 532 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 533 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 534 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 543 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 547 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 548 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 552 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 554 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 555 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 556 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 572 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 580 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 586 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 587 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 590 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 591 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 593 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 600 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 601 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 603 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 604 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 616 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 621 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 622 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 624 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 625 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 629 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 630 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 633 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 634 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 635 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 639 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 640 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 642 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 643 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 645 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 646 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 647 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 653 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 654 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 655 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 656 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 657 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 658 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 662 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 663 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 668 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 669 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 673 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 674 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 675 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 676 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 687 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 688 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 689 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 690 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 691 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 692 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 693 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 694 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 698 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 708 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 709 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 711 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 712 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 713 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 714 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 719 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 720 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 724 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 726 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 727 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 728 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 729 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 730 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 734 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 735 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 736 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 737 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 761 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 762 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 763 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 764 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 765 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 766 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 767 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 773 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 774 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 775 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 776 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 780 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 781 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 782 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 786 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 787 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 788 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 789 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 790 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 796 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 797 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 798 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 799 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 803 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 804 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 805 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 815 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 816 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 817 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 818 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 819 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 828 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 829 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 834 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 835 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 836 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 840 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 841 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 843 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_creation_flow.py` | 847 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_model.py` | 8 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_model.py` | 9 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_model.py` | 10 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_model.py` | 16 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_model.py` | 17 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_model.py` | 18 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_model.py` | 19 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_model.py` | 20 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_model.py` | 23 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_model.py` | 24 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 12 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 13 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 23 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 24 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 32 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 33 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 34 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 43 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 44 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 45 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 50 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 55 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 56 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 57 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 58 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 63 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 64 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 69 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 70 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 71 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 72 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 73 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 77 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 78 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 79 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 81 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 86 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 87 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 88 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 93 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 94 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 95 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 100 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 101 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 102 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 107 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 111 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 124 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 129 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 153 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 158 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 174 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 175 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 180 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 181 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 182 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 187 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 189 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 190 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 191 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 193 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 194 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 198 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 199 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 201 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 215 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 216 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 217 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 229 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 230 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 231 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 232 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile.py` | 242 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_save.py` | 42 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_save.py` | 43 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_save.py` | 56 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_save.py` | 57 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_save.py` | 72 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_save.py` | 94 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_save.py` | 103 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_save.py` | 112 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 41 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 42 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 49 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 50 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 60 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 61 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 68 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 69 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 79 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 84 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 92 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 104 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 105 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 112 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 113 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 145 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 146 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 156 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 163 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 172 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 182 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 189 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 196 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 206 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 207 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 217 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 218 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 228 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 229 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 236 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 237 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 244 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 245 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 246 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 247 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 248 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 249 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 258 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 259 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 269 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 270 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 277 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 284 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 285 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 286 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 287 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 299 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 305 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 306 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 314 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 315 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 325 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 332 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 355 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_profile_service.py` | 356 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_repository.py` | 42 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_repository.py` | 44 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_repository.py` | 45 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_repository.py` | 46 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_repository.py` | 54 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_repository.py` | 57 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_runs_api.py` | 80 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_runs_api.py` | 93 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_runs_api.py` | 115 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_runs_api.py` | 116 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_runs_api.py` | 117 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_runs_api.py` | 118 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_runs_api.py` | 119 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_runs_api.py` | 120 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_runs_api.py` | 121 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_runs_api.py` | 129 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_runs_api.py` | 136 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_runs_api.py` | 140 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_runs_api.py` | 146 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_service.py` | 68 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_service.py` | 69 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_service.py` | 77 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_service.py` | 79 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_service.py` | 80 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_service.py` | 92 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_service.py` | 93 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_service.py` | 110 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_service.py` | 118 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_service.py` | 125 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_service.py` | 126 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_service.py` | 131 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_service.py` | 140 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_service.py` | 141 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_service.py` | 146 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_service.py` | 155 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_service.py` | 161 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_service.py` | 162 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_service.py` | 169 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_service.py` | 170 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_service.py` | 171 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_service.py` | 178 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_service.py` | 179 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 88 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 90 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 110 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 122 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 123 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 124 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 125 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 126 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 144 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 145 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 150 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 167 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 170 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 171 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 172 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 192 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 193 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 213 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 214 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 232 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 233 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 252 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 254 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 255 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 275 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 277 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 278 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 298 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 300 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 301 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 302 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 303 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 323 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 325 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 326 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 327 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 328 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 347 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 349 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 350 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 368 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 369 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 395 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 397 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 398 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 409 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 410 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 411 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 412 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 413 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 414 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 415 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 424 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 425 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 426 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 427 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 428 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 437 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 438 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 447 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 448 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 449 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 450 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 451 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 452 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 453 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 454 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 455 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 466 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 467 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_settings_api.py` | 468 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 39 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 40 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 43 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 46 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 52 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 53 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 54 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 55 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 56 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 57 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 58 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 59 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 60 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 67 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 68 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 69 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 70 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 71 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 72 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 77 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 78 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 79 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 80 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 81 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 91 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 92 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 93 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 94 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 95 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 101 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 102 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 112 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 113 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 114 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 122 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 123 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 124 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 129 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 130 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 136 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state.py` | 137 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state_service.py` | 41 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state_service.py` | 42 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state_service.py` | 43 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state_service.py` | 44 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state_service.py` | 48 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state_service.py` | 54 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state_service.py` | 55 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state_service.py` | 68 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state_service.py` | 69 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_project_state_service.py` | 73 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_create_api.py` | 73 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_create_api.py` | 74 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_create_api.py` | 76 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_create_api.py` | 77 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_create_api.py` | 94 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_create_api.py` | 95 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_create_api.py` | 108 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_create_api.py` | 109 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_create_api.py` | 110 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_create_api.py` | 116 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_create_api.py` | 117 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_create_api.py` | 118 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_create_api.py` | 119 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_create_api.py` | 136 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_create_api.py` | 137 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 54 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 55 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 60 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 61 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 62 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 68 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 69 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 70 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 71 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 78 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 85 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 86 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 91 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 103 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 104 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 105 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 117 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 125 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 126 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 129 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 140 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 144 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 151 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 156 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 185 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 186 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 194 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 195 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 202 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 203 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 204 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 205 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 206 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 207 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 208 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 209 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 210 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 215 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 216 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 221 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 222 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 223 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 224 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 225 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 230 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 231 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 232 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 233 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 238 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 254 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 255 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 256 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 257 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 271 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 272 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 293 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 294 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 295 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 296 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 299 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 300 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 315 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 316 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 319 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 325 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 332 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 333 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 334 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 335 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 336 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 341 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 355 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 356 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 357 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 358 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 372 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 373 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 380 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 381 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 382 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 383 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 384 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 385 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 386 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 387 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 415 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 421 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 432 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 433 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_dashboard.py` | 440 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_empty_state.py` | 13 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_empty_state.py` | 18 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_empty_state.py` | 19 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_empty_state.py` | 20 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_subtitle.py` | 14 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_projects_subtitle.py` | 15 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_provider_card.py` | 10 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_provider_card.py` | 11 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_provider_card.py` | 12 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_provider_card.py` | 17 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_provider_card.py` | 18 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_provider_card.py` | 19 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_provider_card.py` | 22 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_provider_card.py` | 28 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_provider_card.py` | 29 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_registry.py` | 8 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_registry.py` | 12 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_registry.py` | 13 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_registry.py` | 14 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_registry.py` | 17 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_registry.py` | 21 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_registry.py` | 23 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_registry.py` | 25 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_registry.py` | 29 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_registry.py` | 31 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_registry.py` | 32 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_registry.py` | 36 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_registry.py` | 37 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_registry.py` | 40 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_registry.py` | 41 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_registry.py` | 44 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 31 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 32 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 33 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 34 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 35 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 39 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 77 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 78 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 79 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 81 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 82 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 87 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 260 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 261 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 262 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 279 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 280 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 281 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 283 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 284 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 300 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 301 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 339 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 340 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 341 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 342 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 343 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 359 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 361 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 362 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 367 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 368 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 389 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 391 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 392 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 409 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 426 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 427 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 440 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 451 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 452 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 471 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 487 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 489 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 506 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 507 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 508 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 519 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 520 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 533 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 551 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 553 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 554 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 555 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 556 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 558 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 576 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 577 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 579 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 580 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 599 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 600 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 602 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 651 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 652 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 653 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 668 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_api_assets.py` | 669 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 11 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 12 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 13 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 14 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 15 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 16 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 17 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 18 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 19 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 20 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 21 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 22 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 23 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 24 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 25 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 26 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 27 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 28 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 29 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 30 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 31 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 32 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 33 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 34 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 47 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 48 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 49 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 67 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 68 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 69 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 70 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 71 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 76 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 95 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 96 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 97 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 98 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 99 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 100 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 101 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 102 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 103 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 121 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 122 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 123 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 124 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 125 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 126 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 127 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 142 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 159 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 160 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 161 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 162 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 163 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 164 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 178 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 179 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 180 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 181 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 182 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 192 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 201 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_config.py` | 217 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_duration.py` | 53 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_duration.py` | 58 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_duration.py` | 203 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_duration.py` | 204 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_duration.py` | 205 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_duration.py` | 206 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_duration.py` | 207 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_duration.py` | 228 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_duration.py` | 229 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_duration.py` | 230 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_duration.py` | 231 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_duration.py` | 233 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_duration.py` | 259 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_duration.py` | 260 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_duration.py` | 261 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_progress.py` | 30 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_progress.py` | 31 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_progress.py` | 32 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 53 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 54 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 55 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 56 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 57 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 58 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 59 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 60 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 61 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 62 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 63 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 64 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 65 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 86 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 87 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 88 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 89 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 90 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 94 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 95 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 96 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 97 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 98 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 99 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 123 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 124 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 125 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 126 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 127 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 128 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 163 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 164 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 165 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 166 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 167 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 189 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 190 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 197 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_script_conversion.py` | 198 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_state.py` | 66 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_state.py` | 67 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_state.py` | 85 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_state.py` | 86 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_state.py` | 87 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_state.py` | 103 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_render_state.py` | 117 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 54 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 55 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 56 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 57 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 58 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 59 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 60 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 61 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 62 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 105 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 166 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 168 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 169 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 170 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 171 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 174 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 175 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 176 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 177 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 178 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 179 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 180 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 181 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 182 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 183 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 184 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 185 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 255 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 256 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 258 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 259 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 260 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 261 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 363 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 364 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 369 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 472 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 473 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 474 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 541 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 542 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 543 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 544 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 545 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 547 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 548 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 549 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 626 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 627 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 700 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 701 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 702 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 704 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 705 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 785 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 786 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 787 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 788 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 789 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 791 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 792 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 793 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 794 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 800 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_ffmpeg.py` | 820 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_history.py` | 16 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_history.py` | 17 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_history.py` | 22 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_history.py` | 27 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_history.py` | 28 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_history.py` | 29 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_history.py` | 30 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_history.py` | 35 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_history.py` | 36 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_history.py` | 43 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_history.py` | 44 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_history.py` | 45 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_history.py` | 52 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_history.py` | 57 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_panel_shared_state.py` | 11 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_panel_shared_state.py` | 12 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_profile_snapshot.py` | 42 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_profile_snapshot.py` | 49 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_profile_snapshot.py` | 53 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_profile_snapshot.py` | 86 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_profile_snapshot.py` | 87 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_service.py` | 10 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_service.py` | 13 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_service.py` | 21 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_service.py` | 39 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_service.py` | 40 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_service.py` | 53 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_service.py` | 54 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_service.py` | 73 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_service.py` | 74 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_service.py` | 80 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_service.py` | 81 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_service.py` | 82 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_service.py` | 83 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_run_service.py` | 113 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_critique_agent.py` | 18 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_critique_agent.py` | 19 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_critique_agent.py` | 20 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_critique_agent.py` | 46 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_critique_agent.py` | 47 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_critique_agent.py` | 48 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_critique_agent.py` | 49 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_critique_agent.py` | 58 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_critique_agent.py` | 59 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 18 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 19 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 31 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 43 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 44 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 45 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 58 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 59 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 69 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 70 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 78 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 94 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 95 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 96 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 97 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 98 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 119 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 120 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 121 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 122 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 123 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 124 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 135 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 151 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 152 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 153 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 171 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 172 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 173 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 174 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 175 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 194 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 195 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 196 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 197 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 198 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 210 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 211 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 231 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 232 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 233 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 234 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 256 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_parser_conversion.py` | 257 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_service_critique.py` | 39 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_service_critique.py` | 40 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_service_critique.py` | 41 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_service_critique.py` | 50 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_service_critique.py` | 51 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_service_retry.py` | 48 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_service_retry.py` | 49 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_service_retry.py` | 51 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_service_retry.py` | 52 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_service_retry.py` | 60 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_service_retry.py` | 67 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_service_retry.py` | 68 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_service_retry.py` | 75 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_service_retry.py` | 76 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_service_retry.py` | 84 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_service_retry.py` | 85 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_script_service_retry.py` | 92 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_scripts_active_fallback.py` | 50 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_scripts_active_fallback.py` | 61 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_scripts_active_fallback.py` | 62 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_scripts_active_fallback.py` | 98 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_scripts_active_fallback.py` | 99 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_scripts_active_fallback.py` | 100 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_scripts_state.py` | 56 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_scripts_state.py` | 57 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 74 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 79 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 86 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 88 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 89 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 94 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 95 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 100 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 101 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 103 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 108 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 110 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 122 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 123 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 124 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 125 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 127 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 128 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 133 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 134 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 135 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 136 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 143 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 144 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 145 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 146 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 157 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 158 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 165 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 166 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 167 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 175 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 181 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 186 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_api.py` | 194 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 82 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 83 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 84 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 85 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 86 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 87 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 96 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 97 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 107 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 118 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 119 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 128 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 129 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 134 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 135 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 136 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 137 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 141 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 147 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 148 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 149 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 150 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 151 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 155 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 156 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 157 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 161 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 162 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 163 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 164 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 168 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 169 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 170 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 171 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 172 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 173 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 174 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 175 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 179 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 180 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 184 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 185 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 189 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 193 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 204 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 205 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 209 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 210 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_profile_ui.py` | 211 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 38 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 43 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 49 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 52 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 57 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 62 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 65 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 80 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 93 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 95 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 96 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 100 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 109 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 110 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 111 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 115 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 116 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 120 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 121 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 130 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 131 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 132 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 141 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 142 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 146 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 150 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 152 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 156 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 160 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 165 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 170 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 177 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 182 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 188 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 189 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 194 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 195 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 201 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 207 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 208 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 212 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 213 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 217 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 221 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 222 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 226 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 227 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 237 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 238 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 242 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 254 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 264 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 265 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 270 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 271 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 281 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_store.py` | 282 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 23 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 24 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 25 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 29 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 30 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 34 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 36 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 37 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 48 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 49 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 64 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 65 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 66 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 93 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 94 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 103 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 104 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 112 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 113 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 114 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 129 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 131 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 132 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 138 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 139 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_settings_ux.py` | 140 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 12 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 13 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 15 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 16 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 17 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 21 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 22 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 24 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 25 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 26 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 28 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 34 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 35 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 36 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 37 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 38 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 42 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 43 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 44 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 45 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 46 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 58 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 63 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 65 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 66 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 67 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 68 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_shell_wiring.py` | 69 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 7 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 8 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 9 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 10 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 11 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 12 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 13 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 14 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 15 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 16 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 17 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 18 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 19 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 20 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 21 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 28 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 29 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 31 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 32 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 38 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 39 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 40 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 41 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 42 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 46 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 47 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 48 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 56 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 57 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 58 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 59 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 60 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 70 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_active_group.py` | 71 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_recent_projects_api.py` | 53 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_recent_projects_api.py` | 54 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_recent_projects_api.py` | 55 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_recent_projects_api.py` | 63 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_recent_projects_api.py` | 64 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_recent_projects_api.py` | 65 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_recent_projects_api.py` | 70 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_recent_projects_api.py` | 82 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_recent_projects_api.py` | 83 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_recent_projects_api.py` | 84 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_recent_projects_api.py` | 91 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_recent_projects_api.py` | 92 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_recent_projects_api.py` | 93 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_recent_projects_api.py` | 94 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_recent_projects_api.py` | 99 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_recent_projects_api.py` | 104 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_recent_projects_api.py` | 113 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_recent_projects_api.py` | 114 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_sidebar_recent_projects_api.py` | 119 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_status_badge.py` | 8 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_status_badge.py` | 9 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_status_badge.py` | 10 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_status_badge.py` | 13 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_status_badge.py` | 14 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_status_badge.py` | 17 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_status_badge.py` | 18 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_stock_video.py` | 7 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_stock_video.py` | 11 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_stock_video.py` | 15 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_stock_video.py` | 20 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_stock_video.py` | 21 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_stock_video.py` | 24 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_stock_video.py` | 27 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_stock_video.py` | 35 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_stock_video.py` | 48 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_stock_video.py` | 62 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_stock_video.py` | 63 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_stock_video.py` | 78 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_stock_video.py` | 79 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_stock_video.py` | 101 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_stock_video.py` | 102 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_stock_video.py` | 124 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_stock_video.py` | 125 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 93 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 94 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 95 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 96 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 97 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 107 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 108 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 109 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 110 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 119 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 120 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 121 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 126 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 127 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 128 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 136 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 145 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 146 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 147 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 148 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 149 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 154 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 155 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 156 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 161 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 171 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 176 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_parsers_topn.py` | 177 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_profile_service.py` | 46 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_profile_service.py` | 47 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_profile_service.py` | 48 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_profile_service.py` | 53 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_profile_service.py` | 59 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_profile_service.py` | 65 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_profile_service.py` | 86 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_profile_service.py` | 91 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_profile_service.py` | 92 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_profile_service.py` | 101 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_profile_service.py` | 102 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_profile_service.py` | 111 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_profile_service.py` | 129 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 30 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 31 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 32 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 37 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 38 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 43 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 44 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 45 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 49 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 50 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 57 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 58 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 59 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 64 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 65 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 66 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 67 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 72 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 73 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 74 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 80 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 81 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 93 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 94 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 95 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 96 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 97 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 102 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 108 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 109 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 110 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 115 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 116 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 117 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 118 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 122 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 129 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 133 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 140 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 141 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 148 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 149 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 151 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_prompt_selection.py` | 152 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_provides_and_defaults.py` | 81 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_provides_and_defaults.py` | 82 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_provides_and_defaults.py` | 83 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_provides_and_defaults.py` | 84 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_provides_and_defaults.py` | 89 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_provides_and_defaults.py` | 90 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_provides_and_defaults.py` | 91 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_provides_and_defaults.py` | 92 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_provides_and_defaults.py` | 97 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_provides_and_defaults.py` | 98 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_provides_and_defaults.py` | 99 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_provides_and_defaults.py` | 100 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_provides_and_defaults.py` | 105 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_provides_and_defaults.py` | 113 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_provides_and_defaults.py` | 124 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_provides_and_defaults.py` | 125 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_provides_and_defaults.py` | 133 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topic_provides_and_defaults.py` | 137 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 9 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 10 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 14 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 15 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 18 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 19 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 22 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 25 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 29 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 31 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 41 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 43 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 44 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 45 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 46 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 51 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 52 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 53 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 54 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 55 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 61 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 62 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 63 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 64 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 74 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 76 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 77 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 78 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 83 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 84 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 85 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 86 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 87 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 93 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 94 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 95 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 96 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 102 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 108 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 114 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 123 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 132 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 142 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 143 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 149 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 150 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics.py` | 157 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_frontmatter.py` | 12 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_frontmatter.py` | 14 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_frontmatter.py` | 15 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_frontmatter.py` | 16 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_frontmatter.py` | 21 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_frontmatter.py` | 22 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_frontmatter.py` | 23 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_frontmatter.py` | 24 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_frontmatter.py` | 25 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_frontmatter.py` | 26 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_frontmatter.py` | 27 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_frontmatter.py` | 32 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_frontmatter.py` | 45 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_frontmatter.py` | 50 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_frontmatter.py` | 55 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_frontmatter.py` | 57 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_frontmatter.py` | 58 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_frontmatter.py` | 59 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_frontmatter.py` | 64 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_frontmatter.py` | 77 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_frontmatter.py` | 89 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 83 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 84 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 88 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 89 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 93 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 94 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 95 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 101 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 102 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 107 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 111 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 112 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 113 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 114 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 118 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 119 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 120 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 128 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 136 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 144 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 152 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 153 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 159 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 160 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 166 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 167 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 173 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 174 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 194 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 195 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 201 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 202 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 203 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 209 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 210 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topics_pages.py` | 218 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topn_contracts.py` | 10 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topn_contracts.py` | 17 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topn_contracts.py` | 23 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topn_contracts.py` | 24 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topn_contracts.py` | 25 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_topn_contracts.py` | 28 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_card_links.py` | 7 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_card_links.py` | 11 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_card_links.py` | 15 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_card_links.py` | 19 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_card_links.py` | 23 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_card_links.py` | 29 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_card_links.py` | 43 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_card_links.py` | 44 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_card_links.py` | 45 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_card_links.py` | 53 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_card_links.py` | 59 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_card_links.py` | 112 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_card_links.py` | 124 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_card_links.py` | 139 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_card_links.py` | 140 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_card_links.py` | 141 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_card_links.py` | 142 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_card_links.py` | 143 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_card_links.py` | 155 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_card_links.py` | 156 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_endpoints.py` | 43 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_endpoints.py` | 48 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_endpoints.py` | 54 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_endpoints.py` | 59 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_endpoints.py` | 65 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_endpoints.py` | 73 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_video_endpoints.py` | 83 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 95 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 96 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 105 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 106 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 115 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 116 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 125 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 126 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 127 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 128 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 129 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 130 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 139 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 144 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 145 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 156 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 157 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 158 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 172 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 173 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 174 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 183 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 207 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 208 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 209 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 210 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 211 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 212 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 234 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 235 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 244 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 256 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 257 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 258 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 283 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 285 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 290 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 292 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 297 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 298 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 307 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 308 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 309 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 318 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 319 | `S101` | Use of `assert` detected |
| `demos/fullstack-demo/tests/test_videos_seo_scope.py` | 328 | `S101` | Use of `assert` detected |

### Verification Notes

All 305 verified low-risk findings were closed on 2026-08-19 by deep re-verification of every site:

- **S608** (SQL injection, 221 sites): every site re-verified individually. Nine genuine issues fixed: `index_many` index sanitization on the Postgres/MySQL backends, identifier validation at construction for `PostgresFTSQuery`/`MySQLFTSQuery` (table and columns), `Column()` quoting for `batch_processor` record keys, and a collection-name allowlist in `BaseVectorCollection` (prevents quoted-identifier breakout in pgvector SQL). All remaining sites are `# noqa: S608`-annotated with per-site justification: config-only identifiers, allowlisted sanitizers (`_sanitize_index_name`, `_quote_identifier`, `_FIELD_NAME_RE`, `_safe_filter_key`), fixed condition strings, or parameterized values.
- **S110** (except-pass, 41 sites): intentional non-fatal fallbacks; every site annotated with its justification.
- **S311** (pseudo-random, 16 sites): retry/TTL jitter, backoff, sampling, and mock vectors — no security context; annotated.
- **S603** (subprocess, 10 sites): nine operator CLI tooling sites annotated (argv lists, no shell); one genuine fix — `lexigram-cli` MCP self-invocation switched from `sys.argv[0]` to `sys.executable -m lexigram.cli.runtime.main` (argv[0] independence).
- **S607/S104/S704/S701** (17 sites): static PATH tools invoked by the operator, `0.0.0.0` dev-server config defaults, trusted framework HTML composition, and trusted CLI scaffold templates — all annotated with per-site justification.

## Framework Security Rules

| File | Line | Rule ID | Severity | Message |
|------|------|---------|----------|---------|
| `(none)` | 0 | `-` | `-` | No framework security-rule findings. |

## Audit Tracker Status

`docs/AUDIT_TRACKER.md` not found; tracker status unavailable.

## Verified-Clean Surfaces

_(none recorded in the tracker)_

## Open Risk Table

| # | Area | Severity mix |
|---|------|--------------|
| - | (none) | - |

