# ✍️ prompt-lab — prompt authoring & deterministic A/B

> Iterate on a support-reply prompt like a scientist: render any revision,
> inspect history, roll back, and score variants through the real
> evaluation harness — zero LLM, byte-stable every run.

## What it proves

- **Declared-variable templates** — `ChatPromptTemplate` with
  `PromptVariable` declarations; undeclared `{vars}` fail `validate()`
- **Real versioning** — `VersionedPromptStore` push/history/rollback with
  an active-revision pointer (v2 has two revisions to roll between)
- **Duck-typed harness contract** — local `ScoredSample` adds the `output`
  field contracts' `EvaluationSample` lacks; the runner picks it up
  (`runner.py:49`)
- **Deterministic A/B** — v1 (terse) scores 0.0 on the seeded cases,
  v2 (empathetic few-shot) scores 1.0; winner declared per run

## Layout

House flat structure with auth-web's co-located `ui/`.

## Run

```bash
PYTHONPATH=demos/prompt-lab/src uv run python -m prompt_lab
# → http://127.0.0.1:8085  (override: --port / PROMPT_LAB_PORT)
```

Render previews at any revision, run **A/B**, then **Rollback** v2 and see
its score drop back to v1's baseline.

## Tests

```bash
uv run pytest demos/prompt-lab/tests -q
```

Spec & plan: `.superpowers/specs/2026-08-22-prompt-lab-design.md`,
`.superpowers/plans/2026-08-22-prompt-lab.md`.
