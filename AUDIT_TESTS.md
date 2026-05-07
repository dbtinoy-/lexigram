# AUDIT_TESTS.md — Lexigram Framework Targeted Test Execution Audit

> **Source**: Live pytest execution evidence for targeted scopes, with `tests/` directory scanning as supporting context.

---

## Summary

- Total passed tests: 0
- Total failed tests: 0
- Total skipped tests: 0
- Total warnings: 0
- Aggregate code coverage: 0.00%

- Representative commands run: 55
- Commands passing: 0
- Commands failing: 55
- Packages with tests: 54
- Test files: 2876
- Test functions: 29837

### Exit Codes Reference

- **`0`**: Success — All tests passed and code coverage met the configured threshold.
- **`1`**: Failure — Functional tests failed OR code coverage fell below the package's `--cov-fail-under` threshold.
- **`timeout`**: The test command exceeded the execution time limit (120s) and was automatically terminated.

## Execution Evidence

| Label | Code Coverage | Pass/Total | Failed | Skipped | Warnings | Exit Code | Duration |
|-------|---------------|------------|---------|----------|------|-----------|----------|
| Lexigram framework core tests | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 709 ms |
| Package tests: lexigram-contracts | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 762 ms |
| Package tests: lexigram-admin | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 1073 ms |
| Package tests: lexigram-ai-agents | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 676 ms |
| Package tests: lexigram-ai-evaluation | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 786 ms |
| Package tests: lexigram-ai-feedback | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 677 ms |
| Package tests: lexigram-ai-governance | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 725 ms |
| Package tests: lexigram-ai-guard | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 705 ms |
| Package tests: lexigram-ai-llm | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 828 ms |
| Package tests: lexigram-ai-mcp | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 842 ms |
| Package tests: lexigram-ai-memory | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 803 ms |
| Package tests: lexigram-ai-observability | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 801 ms |
| Package tests: lexigram-ai-prompt | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 763 ms |
| Package tests: lexigram-ai-rag | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 691 ms |
| Package tests: lexigram-ai-relay-gateway | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 677 ms |
| Package tests: lexigram-ai-relay | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 842 ms |
| Package tests: lexigram-ai-session | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 831 ms |
| Package tests: lexigram-ai-skills | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 830 ms |
| Package tests: lexigram-ai-workers | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 786 ms |
| Package tests: lexigram-ai | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 796 ms |
| Package tests: lexigram-audit | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 785 ms |
| Package tests: lexigram-auth | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 783 ms |
| Package tests: lexigram-cache | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 844 ms |
| Package tests: lexigram-cli | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 772 ms |
| Package tests: lexigram-events | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 777 ms |
| Package tests: lexigram-features | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 843 ms |
| Package tests: lexigram-graph | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 831 ms |
| Package tests: lexigram-graphql | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 780 ms |
| Package tests: lexigram-http | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 834 ms |
| Package tests: lexigram-monitor | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 853 ms |
| Package tests: lexigram-multimedia-beat | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 800 ms |
| Package tests: lexigram-multimedia-image | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 740 ms |
| Package tests: lexigram-multimedia-interpolate | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 822 ms |
| Package tests: lexigram-multimedia-music | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 780 ms |
| Package tests: lexigram-multimedia-tts | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 776 ms |
| Package tests: lexigram-multimedia-upscale | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 814 ms |
| Package tests: lexigram-multimedia-video | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 713 ms |
| Package tests: lexigram-multimedia | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 743 ms |
| Package tests: lexigram-nosql | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 682 ms |
| Package tests: lexigram-notification | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 716 ms |
| Package tests: lexigram-queue | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 655 ms |
| Package tests: lexigram-resilience | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 654 ms |
| Package tests: lexigram-search | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 508 ms |
| Package tests: lexigram-secrets | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 595 ms |
| Package tests: lexigram-sql (unit only, no external DB) | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 695 ms |
| Package tests: lexigram-storage | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 617 ms |
| Package tests: lexigram-tasks | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 840 ms |
| Package tests: lexigram-tenancy | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 640 ms |
| Package tests: lexigram-testing | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 817 ms |
| Package tests: lexigram-ui | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 834 ms |
| Package tests: lexigram-vector | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 717 ms |
| Package tests: lexigram-web | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 897 ms |
| Package tests: lexigram-webhook | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 735 ms |
| Package tests: lexigram-workflow | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 821 ms |
| Scripts audit smoke | 0.0% | 0/0 | 0 | 0 | 0 | 1 | 598 ms |

### Execution Scope Notes

- `framework-core`: real test execution for `lexigram/tests`.
- `package`: real test execution for `<package>/tests` across every discovered Lexigram package with tests.
- `scripts-audit`: real test execution for `tests/scripts`.

### Lexigram framework core tests

- Scope: `lexigram/tests`
- Command: `uv run pytest lexigram/tests -q -m not integration --cov=lexigram`
- Status: **FAIL**
- Exit code: `1`
- Duration: `709 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-contracts

- Scope: `lexigram-contracts/tests`
- Command: `uv run pytest lexigram-contracts/tests -q -m not integration --cov=lexigram.contracts`
- Status: **FAIL**
- Exit code: `1`
- Duration: `762 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-admin

- Scope: `lexigram-admin/tests`
- Command: `uv run pytest lexigram-admin/tests -q -m not integration --cov=lexigram.admin`
- Status: **FAIL**
- Exit code: `1`
- Duration: `1073 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-ai-agents

- Scope: `lexigram-ai-agents/tests`
- Command: `uv run pytest lexigram-ai-agents/tests -q -m not integration --cov=lexigram.ai.agents`
- Status: **FAIL**
- Exit code: `1`
- Duration: `676 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-ai-evaluation

- Scope: `lexigram-ai-evaluation/tests`
- Command: `uv run pytest lexigram-ai-evaluation/tests -q -m not integration --cov=lexigram.ai.evaluation`
- Status: **FAIL**
- Exit code: `1`
- Duration: `786 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-ai-feedback

- Scope: `lexigram-ai-feedback/tests`
- Command: `uv run pytest lexigram-ai-feedback/tests -q -m not integration --cov=lexigram.ai.feedback`
- Status: **FAIL**
- Exit code: `1`
- Duration: `677 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-ai-governance

- Scope: `lexigram-ai-governance/tests`
- Command: `uv run pytest lexigram-ai-governance/tests -q -m not integration --cov=lexigram.ai.governance`
- Status: **FAIL**
- Exit code: `1`
- Duration: `725 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-ai-guard

- Scope: `lexigram-ai-guard/tests`
- Command: `uv run pytest lexigram-ai-guard/tests -q -m not integration --cov=lexigram.ai.guard`
- Status: **FAIL**
- Exit code: `1`
- Duration: `705 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-ai-llm

- Scope: `lexigram-ai-llm/tests`
- Command: `uv run pytest lexigram-ai-llm/tests -q -m not integration --cov=lexigram.ai.llm`
- Status: **FAIL**
- Exit code: `1`
- Duration: `828 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-ai-mcp

- Scope: `lexigram-ai-mcp/tests`
- Command: `uv run pytest lexigram-ai-mcp/tests -q -m not integration --cov=lexigram.ai.mcp`
- Status: **FAIL**
- Exit code: `1`
- Duration: `842 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-ai-memory

- Scope: `lexigram-ai-memory/tests`
- Command: `uv run pytest lexigram-ai-memory/tests -q -m not integration --cov=lexigram.ai.memory`
- Status: **FAIL**
- Exit code: `1`
- Duration: `803 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-ai-observability

- Scope: `lexigram-ai-observability/tests`
- Command: `uv run pytest lexigram-ai-observability/tests -q -m not integration --cov=lexigram.ai.observability`
- Status: **FAIL**
- Exit code: `1`
- Duration: `801 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-ai-prompt

- Scope: `lexigram-ai-prompt/tests`
- Command: `uv run pytest lexigram-ai-prompt/tests -q -m not integration --cov=lexigram.ai.prompt`
- Status: **FAIL**
- Exit code: `1`
- Duration: `763 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-ai-rag

- Scope: `lexigram-ai-rag/tests`
- Command: `uv run pytest lexigram-ai-rag/tests -q -m not integration --cov=lexigram.ai.rag`
- Status: **FAIL**
- Exit code: `1`
- Duration: `691 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-ai-relay-gateway

- Scope: `lexigram-ai-relay-gateway/tests`
- Command: `uv run pytest lexigram-ai-relay-gateway/tests -q -m not integration --cov=lexigram.ai.relay.gateway`
- Status: **FAIL**
- Exit code: `1`
- Duration: `677 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-ai-relay

- Scope: `lexigram-ai-relay/tests`
- Command: `uv run pytest lexigram-ai-relay/tests -q -m not integration --cov=lexigram.ai.relay`
- Status: **FAIL**
- Exit code: `1`
- Duration: `842 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-ai-session

- Scope: `lexigram-ai-session/tests`
- Command: `uv run pytest lexigram-ai-session/tests -q -m not integration --cov=lexigram.ai.session`
- Status: **FAIL**
- Exit code: `1`
- Duration: `831 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-ai-skills

- Scope: `lexigram-ai-skills/tests`
- Command: `uv run pytest lexigram-ai-skills/tests -q -m not integration --cov=lexigram.ai.skills`
- Status: **FAIL**
- Exit code: `1`
- Duration: `830 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-ai-workers

- Scope: `lexigram-ai-workers/tests`
- Command: `uv run pytest lexigram-ai-workers/tests -q -m not integration --cov=lexigram.ai.workers`
- Status: **FAIL**
- Exit code: `1`
- Duration: `786 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-ai

- Scope: `lexigram-ai/tests`
- Command: `uv run pytest lexigram-ai/tests -q -m not integration --cov=lexigram.ai`
- Status: **FAIL**
- Exit code: `1`
- Duration: `796 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-audit

- Scope: `lexigram-audit/tests`
- Command: `uv run pytest lexigram-audit/tests -q -m not integration --cov=lexigram.audit`
- Status: **FAIL**
- Exit code: `1`
- Duration: `785 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-auth

- Scope: `lexigram-auth/tests`
- Command: `uv run pytest lexigram-auth/tests -q -m not integration --cov=lexigram.auth`
- Status: **FAIL**
- Exit code: `1`
- Duration: `783 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-cache

- Scope: `lexigram-cache/tests`
- Command: `uv run pytest lexigram-cache/tests -q -m not integration --cov=lexigram.cache`
- Status: **FAIL**
- Exit code: `1`
- Duration: `844 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-cli

- Scope: `lexigram-cli/tests`
- Command: `uv run pytest lexigram-cli/tests -q -m not integration --cov=lexigram.cli`
- Status: **FAIL**
- Exit code: `1`
- Duration: `772 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-events

- Scope: `lexigram-events/tests`
- Command: `uv run pytest lexigram-events/tests -q -m not integration --cov=lexigram.events`
- Status: **FAIL**
- Exit code: `1`
- Duration: `777 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-features

- Scope: `lexigram-features/tests`
- Command: `uv run pytest lexigram-features/tests -q -m not integration --cov=lexigram.features`
- Status: **FAIL**
- Exit code: `1`
- Duration: `843 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-graph

- Scope: `lexigram-graph/tests`
- Command: `uv run pytest lexigram-graph/tests -q -m not integration --cov=lexigram.graph`
- Status: **FAIL**
- Exit code: `1`
- Duration: `831 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-graphql

- Scope: `lexigram-graphql/tests`
- Command: `uv run pytest lexigram-graphql/tests -q -m not integration --cov=lexigram.graphql`
- Status: **FAIL**
- Exit code: `1`
- Duration: `780 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-http

- Scope: `lexigram-http/tests`
- Command: `uv run pytest lexigram-http/tests -q -m not integration --cov=lexigram.http`
- Status: **FAIL**
- Exit code: `1`
- Duration: `834 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-monitor

- Scope: `lexigram-monitor/tests`
- Command: `uv run pytest lexigram-monitor/tests -q -m not integration --cov=lexigram.monitor`
- Status: **FAIL**
- Exit code: `1`
- Duration: `853 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-multimedia-beat

- Scope: `lexigram-multimedia-beat/tests`
- Command: `uv run pytest lexigram-multimedia-beat/tests -q -m not integration --cov=lexigram.multimedia.beat`
- Status: **FAIL**
- Exit code: `1`
- Duration: `800 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-multimedia-image

- Scope: `lexigram-multimedia-image/tests`
- Command: `uv run pytest lexigram-multimedia-image/tests -q -m not integration --cov=lexigram.multimedia.image`
- Status: **FAIL**
- Exit code: `1`
- Duration: `740 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-multimedia-interpolate

- Scope: `lexigram-multimedia-interpolate/tests`
- Command: `uv run pytest lexigram-multimedia-interpolate/tests -q -m not integration --cov=lexigram.multimedia.interpolate`
- Status: **FAIL**
- Exit code: `1`
- Duration: `822 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-multimedia-music

- Scope: `lexigram-multimedia-music/tests`
- Command: `uv run pytest lexigram-multimedia-music/tests -q -m not integration --cov=lexigram.multimedia.music`
- Status: **FAIL**
- Exit code: `1`
- Duration: `780 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-multimedia-tts

- Scope: `lexigram-multimedia-tts/tests`
- Command: `uv run pytest lexigram-multimedia-tts/tests -q -m not integration --cov=lexigram.multimedia.tts`
- Status: **FAIL**
- Exit code: `1`
- Duration: `776 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-multimedia-upscale

- Scope: `lexigram-multimedia-upscale/tests`
- Command: `uv run pytest lexigram-multimedia-upscale/tests -q -m not integration --cov=lexigram.multimedia.upscale`
- Status: **FAIL**
- Exit code: `1`
- Duration: `814 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-multimedia-video

- Scope: `lexigram-multimedia-video/tests`
- Command: `uv run pytest lexigram-multimedia-video/tests -q -m not integration --cov=lexigram.multimedia.video`
- Status: **FAIL**
- Exit code: `1`
- Duration: `713 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-multimedia

- Scope: `lexigram-multimedia/tests`
- Command: `uv run pytest lexigram-multimedia/tests -q -m not integration --cov=lexigram.multimedia`
- Status: **FAIL**
- Exit code: `1`
- Duration: `743 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-nosql

- Scope: `lexigram-nosql/tests`
- Command: `uv run pytest lexigram-nosql/tests -q -m not integration --cov=lexigram.nosql`
- Status: **FAIL**
- Exit code: `1`
- Duration: `682 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-notification

- Scope: `lexigram-notification/tests`
- Command: `uv run pytest lexigram-notification/tests -q -m not integration --cov=lexigram.notification`
- Status: **FAIL**
- Exit code: `1`
- Duration: `716 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-queue

- Scope: `lexigram-queue/tests`
- Command: `uv run pytest lexigram-queue/tests -q -m not integration --cov=lexigram.queue`
- Status: **FAIL**
- Exit code: `1`
- Duration: `655 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-resilience

- Scope: `lexigram-resilience/tests`
- Command: `uv run pytest lexigram-resilience/tests -q -m not integration --cov=lexigram.resilience`
- Status: **FAIL**
- Exit code: `1`
- Duration: `654 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-search

- Scope: `lexigram-search/tests`
- Command: `uv run pytest lexigram-search/tests -q -m not integration --cov=lexigram.search`
- Status: **FAIL**
- Exit code: `1`
- Duration: `508 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-secrets

- Scope: `lexigram-secrets/tests`
- Command: `uv run pytest lexigram-secrets/tests -q -m not integration --cov=lexigram.secrets`
- Status: **FAIL**
- Exit code: `1`
- Duration: `595 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-sql (unit only, no external DB)

- Scope: `lexigram-sql/tests`
- Command: `uv run pytest lexigram-sql/tests/unit -q -m not integration --cov=lexigram.sql`
- Status: **FAIL**
- Exit code: `1`
- Duration: `695 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-storage

- Scope: `lexigram-storage/tests`
- Command: `uv run pytest lexigram-storage/tests -q -m not integration --cov=lexigram.storage`
- Status: **FAIL**
- Exit code: `1`
- Duration: `617 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-tasks

- Scope: `lexigram-tasks/tests`
- Command: `uv run pytest lexigram-tasks/tests -q -m not integration --cov=lexigram.tasks`
- Status: **FAIL**
- Exit code: `1`
- Duration: `840 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-tenancy

- Scope: `lexigram-tenancy/tests`
- Command: `uv run pytest lexigram-tenancy/tests -q -m not integration --cov=lexigram.tenancy`
- Status: **FAIL**
- Exit code: `1`
- Duration: `640 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-testing

- Scope: `lexigram-testing/tests`
- Command: `uv run pytest lexigram-testing/tests -q -m not integration --cov=lexigram.testing`
- Status: **FAIL**
- Exit code: `1`
- Duration: `817 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-ui

- Scope: `lexigram-ui/tests`
- Command: `uv run pytest lexigram-ui/tests -q -m not integration --cov=lexigram.ui`
- Status: **FAIL**
- Exit code: `1`
- Duration: `834 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-vector

- Scope: `lexigram-vector/tests`
- Command: `uv run pytest lexigram-vector/tests -q -m not integration --cov=lexigram.vector`
- Status: **FAIL**
- Exit code: `1`
- Duration: `717 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-web

- Scope: `lexigram-web/tests`
- Command: `uv run pytest lexigram-web/tests -q -m not integration --cov=lexigram.web`
- Status: **FAIL**
- Exit code: `1`
- Duration: `897 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-webhook

- Scope: `lexigram-webhook/tests`
- Command: `uv run pytest lexigram-webhook/tests -q -m not integration --cov=lexigram.webhook`
- Status: **FAIL**
- Exit code: `1`
- Duration: `735 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Package tests: lexigram-workflow

- Scope: `lexigram-workflow/tests`
- Command: `uv run pytest lexigram-workflow/tests -q -m not integration --cov=lexigram.workflow`
- Status: **FAIL**
- Exit code: `1`
- Duration: `821 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

### Scripts audit smoke

- Scope: `tests/scripts`
- Command: `uv run pytest tests/scripts -q -m not integration --cov=scripts`
- Status: **FAIL**
- Exit code: `1`
- Duration: `598 ms`
- Parsed summary: `summary unavailable`
- Counters: passed=0, total=0, failed=0, skipped=0, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
warning: The `extra-build-dependencies` option is experimental and may change without warning. Pass `--preview-features extra-build-dependencies` to disable this warning.
  × No solution found when resolving dependencies for split (markers:
  │ python_full_version >= '3.15' and sys_platform == 'win32'):
  ╰─▶ Because lexigram-multimedia-music[ace-step-server] depends on ace-step
      and ace-step==0.1.0 depends on gradio==5.23.3, we can conclude that
      lexigram-multimedia-music[ace-step-server] depends on gradio==5.23.3.
      And because gradio==5.23.3 depends on pillow>=8.0,<12.0 and
      lexigram-workspace:dev depends on pillow>=12.1.1, we can conclude that
      lexigram-workspace:dev and lexigram-multimedia-music[ace-step-server]
      are incompatible.
      And because your wo
```

