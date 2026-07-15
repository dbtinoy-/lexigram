# AUDIT_TESTS.md — Lexigram Framework Targeted Test Execution Audit

> **Source**: Live pytest execution evidence for targeted scopes, with `tests/` directory scanning as supporting context.

---

## Summary

- Total passed tests: 30918
- Total failed tests: 0
- Total skipped tests: 263
- Total warnings: 276
- Aggregate code coverage: 75.39%

- Representative commands run: 54
- Commands passing: 47
- Commands failing: 7
- Packages with tests: 54
- Test files: 2992
- Test functions: 31112

### Exit Codes Reference

- **`0`**: Success — All tests passed and code coverage met the configured threshold.
- **`1`**: Failure — Functional tests failed OR code coverage fell below the package's `--cov-fail-under` threshold.
- **`timeout`**: The test command exceeded the execution time limit (120s) and was automatically terminated.

## Execution Evidence

| Label | Code Coverage | Pass/Total | Failed | Skipped | Warnings | Exit Code | Duration |
|-------|---------------|------------|---------|----------|------|-----------|----------|
| Lexigram framework core tests | 58.0% | 2959/2964 | 0 | 5 | 1 | 1 | 27356 ms |
| Package tests: lexigram-contracts | 34.0% | 1766/1766 | 0 | 0 | 4 | 1 | 11282 ms |
| Package tests: lexigram-admin | 76.0% | 4542/4553 | 0 | 11 | 18 | 0 | 60136 ms |
| Package tests: lexigram-ai-agents | 85.0% | 402/402 | 0 | 0 | 4 | 0 | 6345 ms |
| Package tests: lexigram-ai-evaluation | 99.0% | 136/136 | 0 | 0 | 4 | 0 | 1887 ms |
| Package tests: lexigram-ai-feedback | 94.0% | 237/237 | 0 | 0 | 4 | 0 | 2239 ms |
| Package tests: lexigram-ai-governance | 86.0% | 506/506 | 0 | 0 | 15 | 0 | 4301 ms |
| Package tests: lexigram-ai-guard | 82.0% | 239/239 | 0 | 0 | 7 | 0 | 2407 ms |
| Package tests: lexigram-ai-llm | 71.0% | 949/969 | 0 | 20 | 4 | 0 | 33320 ms |
| Package tests: lexigram-ai-mcp | 51.0% | 384/384 | 0 | 0 | 4 | 0 | 3852 ms |
| Package tests: lexigram-ai-memory | 83.0% | 240/240 | 0 | 0 | 4 | 0 | 2663 ms |
| Package tests: lexigram-ai-observability | 86.0% | 232/232 | 0 | 0 | 4 | 0 | 2771 ms |
| Package tests: lexigram-ai-prompt | 87.0% | 297/297 | 0 | 0 | 4 | 0 | 2672 ms |
| Package tests: lexigram-ai-rag | 62.0% | 528/535 | 0 | 7 | 4 | 0 | 7896 ms |
| Package tests: lexigram-ai-relay-gateway | 94.0% | 535/535 | 0 | 0 | 4 | 0 | 4256 ms |
| Package tests: lexigram-ai-relay | 91.0% | 539/539 | 0 | 0 | 4 | 0 | 6093 ms |
| Package tests: lexigram-ai-session | 88.0% | 210/210 | 0 | 0 | 4 | 0 | 2732 ms |
| Package tests: lexigram-ai-skills | 78.0% | 268/268 | 0 | 0 | 6 | 0 | 2817 ms |
| Package tests: lexigram-ai-workers | 87.0% | 318/318 | 0 | 0 | 4 | 0 | 4037 ms |
| Package tests: lexigram-ai | 42.0% | 451/462 | 0 | 11 | 4 | 1 | 18830 ms |
| Package tests: lexigram-audit | 82.0% | 265/265 | 0 | 0 | 4 | 0 | 2620 ms |
| Package tests: lexigram-auth | 67.0% | 607/611 | 0 | 4 | 6 | 1 | 28468 ms |
| Package tests: lexigram-cache | 80.0% | 837/850 | 0 | 13 | 6 | 0 | 11350 ms |
| Package tests: lexigram-cli | 80.0% | 852/853 | 0 | 1 | 6 | 0 | 17580 ms |
| Package tests: lexigram-events | 61.0% | 916/931 | 0 | 15 | 5 | 1 | 12804 ms |
| Package tests: lexigram-features | 80.0% | 245/245 | 0 | 0 | 17 | 0 | 3545 ms |
| Package tests: lexigram-graph | 79.0% | 257/258 | 0 | 1 | 4 | 0 | 2440 ms |
| Package tests: lexigram-graphql | 76.0% | 519/521 | 0 | 2 | 4 | 0 | 6337 ms |
| Package tests: lexigram-http | 77.0% | 450/450 | 0 | 0 | 4 | 0 | 2933 ms |
| Package tests: lexigram-monitor | 81.0% | 310/315 | 0 | 5 | 4 | 0 | 8836 ms |
| Package tests: lexigram-multimedia-beat | 71.0% | 18/18 | 0 | 0 | 4 | 0 | 2732 ms |
| Package tests: lexigram-multimedia-image | 92.0% | 54/54 | 0 | 0 | 4 | 0 | 2269 ms |
| Package tests: lexigram-multimedia-interpolate | 87.0% | 23/23 | 0 | 0 | 4 | 0 | 2006 ms |
| Package tests: lexigram-multimedia-music | 84.0% | 38/38 | 0 | 0 | 4 | 0 | 2076 ms |
| Package tests: lexigram-multimedia-tts | 78.0% | 63/63 | 0 | 0 | 4 | 0 | 2429 ms |
| Package tests: lexigram-multimedia-upscale | 93.0% | 42/42 | 0 | 0 | 4 | 0 | 2291 ms |
| Package tests: lexigram-multimedia-video | 86.0% | 182/182 | 0 | 0 | 4 | 0 | 5720 ms |
| Package tests: lexigram-multimedia | 55.0% | 86/86 | 0 | 0 | 5 | 0 | 5227 ms |
| Package tests: lexigram-nosql | 91.0% | 536/536 | 0 | 0 | 4 | 0 | 3611 ms |
| Package tests: lexigram-notification | 83.0% | 291/291 | 0 | 0 | 4 | 0 | 5823 ms |
| Package tests: lexigram-queue | 82.0% | 206/206 | 0 | 0 | 4 | 0 | 3926 ms |
| Package tests: lexigram-resilience | 72.0% | 299/299 | 0 | 0 | 4 | 0 | 20531 ms |
| Package tests: lexigram-search | 65.0% | 809/813 | 0 | 4 | 4 | 0 | 4540 ms |
| Package tests: lexigram-secrets | 58.0% | 127/127 | 0 | 0 | 4 | 0 | 1800 ms |
| Package tests: lexigram-sql (unit only, no external DB) | 61.0% | 1296/1342 | 0 | 46 | 6 | 0 | 22926 ms |
| Package tests: lexigram-storage | 62.0% | 453/456 | 0 | 3 | 4 | 0 | 7036 ms |
| Package tests: lexigram-tasks | 73.0% | 509/524 | 0 | 15 | 4 | 1 | 11093 ms |
| Package tests: lexigram-tenancy | 83.0% | 360/360 | 0 | 0 | 4 | 0 | 3276 ms |
| Package tests: lexigram-testing | 17.0% | 436/451 | 0 | 15 | 4 | 1 | 8568 ms |
| Package tests: lexigram-ui | 70.0% | 1251/1329 | 0 | 78 | 12 | 0 | 7314 ms |
| Package tests: lexigram-vector | 77.0% | 541/541 | 0 | 0 | 4 | 0 | 4882 ms |
| Package tests: lexigram-web | 81.0% | 1415/1422 | 0 | 7 | 6 | 0 | 13164 ms |
| Package tests: lexigram-webhook | 83.0% | 334/334 | 0 | 0 | 4 | 0 | 2850 ms |
| Package tests: lexigram-workflow | 70.0% | 553/553 | 0 | 0 | 4 | 0 | 13988 ms |

### Execution Scope Notes

- `framework-core`: real test execution for `lexigram/tests`.
- `package`: real test execution for `<package>/tests` across every discovered Lexigram package with tests.
### Lexigram framework core tests

- Scope: `lexigram/tests`
- Command: `uv run pytest lexigram/tests -q -m not integration --cov=lexigram`
- Status: **FAIL**
- Exit code: `1`
- Duration: `27356 ms`
- Parsed summary: `2959 passed, 5 skipped, 19 deselected, 1 warning in 24.27s`
- Counters: passed=2959, total=2964, failed=0, skipped=5, warnings=1, coverage=58.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:33:22 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  2%]
........................................................................ [  4%]
........................................................................ [  7%]
........................................................................ [  9%]
........................................................................ [ 12%]
........................................................................ [ 14%]
........................................................................ [ 17%]
....................................................
```

### Package tests: lexigram-contracts

- Scope: `lexigram-contracts/tests`
- Command: `uv run pytest lexigram-contracts/tests -q -m not integration --cov=lexigram.contracts`
- Status: **FAIL**
- Exit code: `1`
- Duration: `11282 ms`
- Parsed summary: `1766 passed, 4 warnings in 9.68s`
- Counters: passed=1766, total=1766, failed=0, skipped=0, warnings=4, coverage=34.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:33:49 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  4%]
........................................................................ [  8%]
........................................................................ [ 12%]
........................................................................ [ 16%]
........................................................................ [ 20%]
........................................................................ [ 24%]
........................................................................ [ 28%]
....................................................
```

### Package tests: lexigram-admin

- Scope: `lexigram-admin/tests`
- Command: `uv run pytest lexigram-admin/tests -q -m not integration --cov=lexigram.admin`
- Status: **PASS**
- Exit code: `0`
- Duration: `60136 ms`
- Parsed summary: `4542 passed, 11 skipped, 27 deselected, 18 warnings in 57.42s`
- Counters: passed=4542, total=4553, failed=0, skipped=11, warnings=18, coverage=76.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:34:00 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
ss....................................................ss................ [  1%]
........................................................................ [  3%]
...............s..................ss.................................... [  4%]
........................................................................ [  6%]
........................................................................ [  7%]
........................................................................ [  9%]
........................................................................ [ 11%]
....................................................
```

### Package tests: lexigram-ai-agents

- Scope: `lexigram-ai-agents/tests`
- Command: `uv run pytest lexigram-ai-agents/tests -q -m not integration --cov=lexigram.ai.agents`
- Status: **PASS**
- Exit code: `0`
- Duration: `6345 ms`
- Parsed summary: `402 passed, 10 deselected, 4 warnings in 4.83s`
- Counters: passed=402, total=402, failed=0, skipped=0, warnings=4, coverage=85.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:35:01 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 17%]
........................................................................ [ 35%]
........................................................................ [ 53%]
........................................................................ [ 71%]
........................................................................ [ 89%]
..........................................                               [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/_
```

### Package tests: lexigram-ai-evaluation

- Scope: `lexigram-ai-evaluation/tests`
- Command: `uv run pytest lexigram-ai-evaluation/tests -q -m not integration --cov=lexigram.ai.evaluation`
- Status: **PASS**
- Exit code: `0`
- Duration: `1887 ms`
- Parsed summary: `136 passed, 4 warnings in 0.60s`
- Counters: passed=136, total=136, failed=0, skipped=0, warnings=4, coverage=99.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:35:07 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 52%]
................................................................         [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/
```

### Package tests: lexigram-ai-feedback

- Scope: `lexigram-ai-feedback/tests`
- Command: `uv run pytest lexigram-ai-feedback/tests -q -m not integration --cov=lexigram.ai.feedback`
- Status: **PASS**
- Exit code: `0`
- Duration: `2239 ms`
- Parsed summary: `237 passed, 4 warnings in 0.90s`
- Counters: passed=237, total=237, failed=0, skipped=0, warnings=4, coverage=94.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:35:09 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 30%]
........................................................................ [ 60%]
........................................................................ [ 91%]
.....................                                                    [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-ai-governance

- Scope: `lexigram-ai-governance/tests`
- Command: `uv run pytest lexigram-ai-governance/tests -q -m not integration --cov=lexigram.ai.governance`
- Status: **PASS**
- Exit code: `0`
- Duration: `4301 ms`
- Parsed summary: `506 passed, 7 deselected, 15 warnings in 2.92s`
- Counters: passed=506, total=506, failed=0, skipped=0, warnings=15, coverage=86.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:35:11 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 14%]
........................................................................ [ 28%]
........................................................................ [ 42%]
........................................................................ [ 56%]
........................................................................ [ 71%]
........................................................................ [ 85%]
........................................................................ [ 99%]
..                                                  
```

### Package tests: lexigram-ai-guard

- Scope: `lexigram-ai-guard/tests`
- Command: `uv run pytest lexigram-ai-guard/tests -q -m not integration --cov=lexigram.ai.guard`
- Status: **PASS**
- Exit code: `0`
- Duration: `2407 ms`
- Parsed summary: `239 passed, 17 deselected, 7 warnings in 1.07s`
- Counters: passed=239, total=239, failed=0, skipped=0, warnings=7, coverage=82.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:35:15 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 30%]
........................................................................ [ 60%]
........................................................................ [ 90%]
.......................                                                  [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-ai-llm

- Scope: `lexigram-ai-llm/tests`
- Command: `uv run pytest lexigram-ai-llm/tests -q -m not integration --cov=lexigram.ai.llm`
- Status: **PASS**
- Exit code: `0`
- Duration: `33320 ms`
- Parsed summary: `949 passed, 20 skipped, 19 deselected, 4 warnings in 31.41s`
- Counters: passed=949, total=969, failed=0, skipped=20, warnings=4, coverage=71.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:35:18 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
ssssssssssssssss........................................................ [  7%]
........................................................................ [ 14%]
........................................................................ [ 22%]
..............................................................ssss...... [ 29%]
........................................................................ [ 37%]
........................................................................ [ 44%]
........................................................................ [ 52%]
....................................................
```

### Package tests: lexigram-ai-mcp

- Scope: `lexigram-ai-mcp/tests`
- Command: `uv run pytest lexigram-ai-mcp/tests -q -m not integration --cov=lexigram.ai.mcp`
- Status: **PASS**
- Exit code: `0`
- Duration: `3852 ms`
- Parsed summary: `384 passed, 13 deselected, 4 warnings in 2.42s`
- Counters: passed=384, total=384, failed=0, skipped=0, warnings=4, coverage=51.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:35:51 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 18%]
........................................................................ [ 37%]
........................................................................ [ 56%]
........................................................................ [ 75%]
........................................................................ [ 93%]
........................                                                 [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/_
```

### Package tests: lexigram-ai-memory

- Scope: `lexigram-ai-memory/tests`
- Command: `uv run pytest lexigram-ai-memory/tests -q -m not integration --cov=lexigram.ai.memory`
- Status: **PASS**
- Exit code: `0`
- Duration: `2663 ms`
- Parsed summary: `240 passed, 16 deselected, 4 warnings in 1.32s`
- Counters: passed=240, total=240, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:35:55 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 30%]
........................................................................ [ 60%]
........................................................................ [ 90%]
........................                                                 [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-ai-observability

- Scope: `lexigram-ai-observability/tests`
- Command: `uv run pytest lexigram-ai-observability/tests -q -m not integration --cov=lexigram.ai.observability`
- Status: **PASS**
- Exit code: `0`
- Duration: `2771 ms`
- Parsed summary: `232 passed, 10 deselected, 4 warnings in 1.40s`
- Counters: passed=232, total=232, failed=0, skipped=0, warnings=4, coverage=86.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:35:58 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 31%]
........................................................................ [ 62%]
........................................................................ [ 93%]
................                                                         [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-ai-prompt

- Scope: `lexigram-ai-prompt/tests`
- Command: `uv run pytest lexigram-ai-prompt/tests -q -m not integration --cov=lexigram.ai.prompt`
- Status: **PASS**
- Exit code: `0`
- Duration: `2672 ms`
- Parsed summary: `297 passed, 4 warnings in 1.32s`
- Counters: passed=297, total=297, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:36:00 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 24%]
........................................................................ [ 48%]
........................................................................ [ 72%]
........................................................................ [ 96%]
.........                                                                [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/
```

### Package tests: lexigram-ai-rag

- Scope: `lexigram-ai-rag/tests`
- Command: `uv run pytest lexigram-ai-rag/tests -q -m not integration --cov=lexigram.ai.rag`
- Status: **PASS**
- Exit code: `0`
- Duration: `7896 ms`
- Parsed summary: `528 passed, 7 skipped, 8 deselected, 4 warnings in 6.36s`
- Counters: passed=528, total=535, failed=0, skipped=7, warnings=4, coverage=62.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:36:03 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
...........................................................sss.......... [ 13%]
.s..............ss...................................................... [ 26%]
.........................................................s.............. [ 40%]
........................................................................ [ 53%]
........................................................................ [ 67%]
........................................................................ [ 80%]
........................................................................ [ 94%]
...............................                     
```

### Package tests: lexigram-ai-relay-gateway

- Scope: `lexigram-ai-relay-gateway/tests`
- Command: `uv run pytest lexigram-ai-relay-gateway/tests -q -m not integration --cov=lexigram.ai.relay.gateway`
- Status: **PASS**
- Exit code: `0`
- Duration: `4256 ms`
- Parsed summary: `535 passed, 4 warnings in 2.86s`
- Counters: passed=535, total=535, failed=0, skipped=0, warnings=4, coverage=94.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:36:11 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 40%]
........................................................................ [ 53%]
........................................................................ [ 67%]
........................................................................ [ 80%]
........................................................................ [ 94%]
...............................                     
```

### Package tests: lexigram-ai-relay

- Scope: `lexigram-ai-relay/tests`
- Command: `uv run pytest lexigram-ai-relay/tests -q -m not integration --cov=lexigram.ai.relay`
- Status: **PASS**
- Exit code: `0`
- Duration: `6093 ms`
- Parsed summary: `539 passed, 4 warnings in 4.64s`
- Counters: passed=539, total=539, failed=0, skipped=0, warnings=4, coverage=91.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:36:15 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
2026-08-18 12:36:15 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=RelayModule providers=0
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 40%]
........................................................................ [ 53%]
........................................................................ [ 66%]
..........................
```

### Package tests: lexigram-ai-session

- Scope: `lexigram-ai-session/tests`
- Command: `uv run pytest lexigram-ai-session/tests -q -m not integration --cov=lexigram.ai.session`
- Status: **PASS**
- Exit code: `0`
- Duration: `2732 ms`
- Parsed summary: `210 passed, 4 warnings in 1.35s`
- Counters: passed=210, total=210, failed=0, skipped=0, warnings=4, coverage=88.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:36:21 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 34%]
........................................................................ [ 68%]
..................................................................       [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtur
```

### Package tests: lexigram-ai-skills

- Scope: `lexigram-ai-skills/tests`
- Command: `uv run pytest lexigram-ai-skills/tests -q -m not integration --cov=lexigram.ai.skills`
- Status: **PASS**
- Exit code: `0`
- Duration: `2817 ms`
- Parsed summary: `268 passed, 6 warnings in 1.49s`
- Counters: passed=268, total=268, failed=0, skipped=0, warnings=6, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:36:24 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 26%]
........................................................................ [ 53%]
........................................................................ [ 80%]
....................................................                     [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-ai-workers

- Scope: `lexigram-ai-workers/tests`
- Command: `uv run pytest lexigram-ai-workers/tests -q -m not integration --cov=lexigram.ai.workers`
- Status: **PASS**
- Exit code: `0`
- Duration: `4037 ms`
- Parsed summary: `318 passed, 7 deselected, 4 warnings in 2.70s`
- Counters: passed=318, total=318, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:36:27 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 22%]
........................................................................ [ 45%]
........................................................................ [ 67%]
........................................................................ [ 90%]
..............................                                           [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/
```

### Package tests: lexigram-ai

- Scope: `lexigram-ai/tests`
- Command: `uv run pytest lexigram-ai/tests -q -m not integration --cov=lexigram.ai`
- Status: **FAIL**
- Exit code: `1`
- Duration: `18830 ms`
- Parsed summary: `451 passed, 11 skipped, 15 deselected, 4 warnings in 17.05s`
- Counters: passed=451, total=462, failed=0, skipped=11, warnings=4, coverage=42.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:36:31 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
...ss..s................................................................ [ 15%]
........................................................................ [ 31%]
............s.s......................................................... [ 47%]
........................................................................ [ 63%]
........................................................................ [ 78%]
........................................................................ [ 94%]
........................
ERROR: Coverage failure: total of 42 is less than fail-under=60
                                           
```

### Package tests: lexigram-audit

- Scope: `lexigram-audit/tests`
- Command: `uv run pytest lexigram-audit/tests -q -m not integration --cov=lexigram.audit`
- Status: **PASS**
- Exit code: `0`
- Duration: `2620 ms`
- Parsed summary: `265 passed, 17 deselected, 4 warnings in 1.23s`
- Counters: passed=265, total=265, failed=0, skipped=0, warnings=4, coverage=82.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:36:50 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 27%]
........................................................................ [ 54%]
........................................................................ [ 81%]
.................................................                        [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-auth

- Scope: `lexigram-auth/tests`
- Command: `uv run pytest lexigram-auth/tests -q -m not integration --cov=lexigram.auth`
- Status: **FAIL**
- Exit code: `1`
- Duration: `28468 ms`
- Parsed summary: `607 passed, 4 skipped, 2 deselected, 6 warnings in 26.97s`
- Counters: passed=607, total=611, failed=0, skipped=4, warnings=6, coverage=67.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:36:52 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 11%]
..........................................ssss.......................... [ 23%]
........................................................................ [ 35%]
........................................................................ [ 47%]
........................................................................ [ 58%]
........................................................................ [ 70%]
........................................................................ [ 82%]
....................................................
```

### Package tests: lexigram-cache

- Scope: `lexigram-cache/tests`
- Command: `uv run pytest lexigram-cache/tests -q -m not integration --cov=lexigram.cache`
- Status: **PASS**
- Exit code: `0`
- Duration: `11350 ms`
- Parsed summary: `837 passed, 13 skipped, 22 deselected, 6 warnings in 9.66s`
- Counters: passed=837, total=850, failed=0, skipped=13, warnings=6, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:37:21 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  8%]
.....................................ss................................. [ 16%]
........................................................................ [ 25%]
...........................................ssssssssss................... [ 33%]
........................................................................ [ 42%]
........................................................................ [ 50%]
........................................................................ [ 59%]
....................................................
```

### Package tests: lexigram-cli

- Scope: `lexigram-cli/tests`
- Command: `uv run pytest lexigram-cli/tests -q -m not integration --cov=lexigram.cli`
- Status: **PASS**
- Exit code: `0`
- Duration: `17580 ms`
- Parsed summary: `852 passed, 1 skipped, 7 deselected, 6 warnings in 15.68s`
- Counters: passed=852, total=853, failed=0, skipped=1, warnings=6, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:37:32 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  8%]
........................................................................ [ 16%]
........................................................................ [ 25%]
........................................................................ [ 33%]
........................................................................ [ 42%]
........................................................................ [ 50%]
........................................................................ [ 59%]
....................................................
```

### Package tests: lexigram-events

- Scope: `lexigram-events/tests`
- Command: `uv run pytest lexigram-events/tests -q -m not integration --cov=lexigram.events`
- Status: **FAIL**
- Exit code: `1`
- Duration: `12804 ms`
- Parsed summary: `916 passed, 15 skipped, 11 deselected, 5 warnings in 10.88s`
- Counters: passed=916, total=931, failed=0, skipped=15, warnings=5, coverage=61.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:37:50 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
...s.................................................................... [  7%]
........................................................................ [ 15%]
........................................................................ [ 23%]
........................................................................ [ 31%]
........................................................................ [ 38%]
........................................................................ [ 46%]
........................................................................ [ 54%]
....................................................
```

### Package tests: lexigram-features

- Scope: `lexigram-features/tests`
- Command: `uv run pytest lexigram-features/tests -q -m not integration --cov=lexigram.features`
- Status: **PASS**
- Exit code: `0`
- Duration: `3545 ms`
- Parsed summary: `245 passed, 14 deselected, 17 warnings in 2.22s`
- Counters: passed=245, total=245, failed=0, skipped=0, warnings=17, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:38:02 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 29%]
........................................................................ [ 58%]
........................................................................ [ 88%]
.............................                                            [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-graph

- Scope: `lexigram-graph/tests`
- Command: `uv run pytest lexigram-graph/tests -q -m not integration --cov=lexigram.graph`
- Status: **PASS**
- Exit code: `0`
- Duration: `2440 ms`
- Parsed summary: `257 passed, 1 skipped, 7 deselected, 4 warnings in 1.12s`
- Counters: passed=257, total=258, failed=0, skipped=1, warnings=4, coverage=79.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:38:06 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 27%]
..................s..................................................... [ 55%]
........................................................................ [ 83%]
..........................................                               [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-graphql

- Scope: `lexigram-graphql/tests`
- Command: `uv run pytest lexigram-graphql/tests -q -m not integration --cov=lexigram.graphql`
- Status: **PASS**
- Exit code: `0`
- Duration: `6337 ms`
- Parsed summary: `519 passed, 2 skipped, 11 deselected, 4 warnings in 4.58s`
- Counters: passed=519, total=521, failed=0, skipped=2, warnings=4, coverage=76.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:38:08 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
s....................................................................... [ 13%]
........................................................................ [ 27%]
................s....................................................... [ 41%]
........................................................................ [ 55%]
........................................................................ [ 69%]
........................................................................ [ 82%]
........................................................................ [ 96%]
.................                                   
```

### Package tests: lexigram-http

- Scope: `lexigram-http/tests`
- Command: `uv run pytest lexigram-http/tests -q -m not integration --cov=lexigram.http`
- Status: **PASS**
- Exit code: `0`
- Duration: `2933 ms`
- Parsed summary: `450 passed, 9 deselected, 4 warnings in 1.53s`
- Counters: passed=450, total=450, failed=0, skipped=0, warnings=4, coverage=77.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:38:15 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 16%]
........................................................................ [ 32%]
........................................................................ [ 48%]
........................................................................ [ 64%]
........................................................................ [ 80%]
........................................................................ [ 96%]
..................                                                       [100%]
=============================== warnings summary ===
```

### Package tests: lexigram-monitor

- Scope: `lexigram-monitor/tests`
- Command: `uv run pytest lexigram-monitor/tests -q -m not integration --cov=lexigram.monitor`
- Status: **PASS**
- Exit code: `0`
- Duration: `8836 ms`
- Parsed summary: `310 passed, 5 skipped, 4 deselected, 4 warnings in 7.40s`
- Counters: passed=310, total=315, failed=0, skipped=5, warnings=4, coverage=81.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:38:18 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 22%]
....................................................sss.s............... [ 45%]
........................................................................ [ 68%]
........................................................s............... [ 91%]
...........................                                              [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/
```

### Package tests: lexigram-multimedia-beat

- Scope: `lexigram-multimedia-beat/tests`
- Command: `uv run pytest lexigram-multimedia-beat/tests -q -m not integration --cov=lexigram.multimedia.beat`
- Status: **PASS**
- Exit code: `0`
- Duration: `2732 ms`
- Parsed summary: `18 passed, 12 deselected, 4 warnings in 1.19s`
- Counters: passed=18, total=18, failed=0, skipped=0, warnings=4, coverage=71.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:38:27 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
..................                                                       [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework
```

### Package tests: lexigram-multimedia-image

- Scope: `lexigram-multimedia-image/tests`
- Command: `uv run pytest lexigram-multimedia-image/tests -q -m not integration --cov=lexigram.multimedia.image`
- Status: **PASS**
- Exit code: `0`
- Duration: `2269 ms`
- Parsed summary: `54 passed, 4 warnings in 0.80s`
- Counters: passed=54, total=54, failed=0, skipped=0, warnings=4, coverage=92.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:38:29 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
......................................................                   [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework
```

### Package tests: lexigram-multimedia-interpolate

- Scope: `lexigram-multimedia-interpolate/tests`
- Command: `uv run pytest lexigram-multimedia-interpolate/tests -q -m not integration --cov=lexigram.multimedia.interpolate`
- Status: **PASS**
- Exit code: `0`
- Duration: `2006 ms`
- Parsed summary: `23 passed, 4 warnings in 0.52s`
- Counters: passed=23, total=23, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:38:32 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.......................                                                  [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework
```

### Package tests: lexigram-multimedia-music

- Scope: `lexigram-multimedia-music/tests`
- Command: `uv run pytest lexigram-multimedia-music/tests -q -m not integration --cov=lexigram.multimedia.music`
- Status: **PASS**
- Exit code: `0`
- Duration: `2076 ms`
- Parsed summary: `38 passed, 4 warnings in 0.59s`
- Counters: passed=38, total=38, failed=0, skipped=0, warnings=4, coverage=84.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:38:34 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
......................................                                   [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework
```

### Package tests: lexigram-multimedia-tts

- Scope: `lexigram-multimedia-tts/tests`
- Command: `uv run pytest lexigram-multimedia-tts/tests -q -m not integration --cov=lexigram.multimedia.tts`
- Status: **PASS**
- Exit code: `0`
- Duration: `2429 ms`
- Parsed summary: `63 passed, 4 warnings in 0.91s`
- Counters: passed=63, total=63, failed=0, skipped=0, warnings=4, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:38:36 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
...............................................................          [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework
```

### Package tests: lexigram-multimedia-upscale

- Scope: `lexigram-multimedia-upscale/tests`
- Command: `uv run pytest lexigram-multimedia-upscale/tests -q -m not integration --cov=lexigram.multimedia.upscale`
- Status: **PASS**
- Exit code: `0`
- Duration: `2291 ms`
- Parsed summary: `42 passed, 4 warnings in 0.73s`
- Counters: passed=42, total=42, failed=0, skipped=0, warnings=4, coverage=93.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:38:38 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
..........................................                               [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework
```

### Package tests: lexigram-multimedia-video

- Scope: `lexigram-multimedia-video/tests`
- Command: `uv run pytest lexigram-multimedia-video/tests -q -m not integration --cov=lexigram.multimedia.video`
- Status: **PASS**
- Exit code: `0`
- Duration: `5720 ms`
- Parsed summary: `182 passed, 4 warnings in 4.19s`
- Counters: passed=182, total=182, failed=0, skipped=0, warnings=4, coverage=86.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:38:40 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 39%]
........................................................................ [ 79%]
......................................                                   [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtur
```

### Package tests: lexigram-multimedia

- Scope: `lexigram-multimedia/tests`
- Command: `uv run pytest lexigram-multimedia/tests -q -m not integration --cov=lexigram.multimedia`
- Status: **PASS**
- Exit code: `0`
- Duration: `5227 ms`
- Parsed summary: `86 passed, 5 warnings in 3.76s`
- Counters: passed=86, total=86, failed=0, skipped=0, warnings=5, coverage=55.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:38:46 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 83%]
..............                                                           [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/
```

### Package tests: lexigram-nosql

- Scope: `lexigram-nosql/tests`
- Command: `uv run pytest lexigram-nosql/tests -q -m not integration --cov=lexigram.nosql`
- Status: **PASS**
- Exit code: `0`
- Duration: `3611 ms`
- Parsed summary: `536 passed, 10 deselected, 4 warnings in 2.23s`
- Counters: passed=536, total=536, failed=0, skipped=0, warnings=4, coverage=91.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:38:51 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 40%]
........................................................................ [ 53%]
........................................................................ [ 67%]
........................................................................ [ 80%]
........................................................................ [ 94%]
................................                    
```

### Package tests: lexigram-notification

- Scope: `lexigram-notification/tests`
- Command: `uv run pytest lexigram-notification/tests -q -m not integration --cov=lexigram.notification`
- Status: **PASS**
- Exit code: `0`
- Duration: `5823 ms`
- Parsed summary: `291 passed, 8 deselected, 4 warnings in 4.29s`
- Counters: passed=291, total=291, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:38:55 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 24%]
........................................................................ [ 49%]
........................................................................ [ 74%]
........................................................................ [ 98%]
...                                                                      [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/
```

### Package tests: lexigram-queue

- Scope: `lexigram-queue/tests`
- Command: `uv run pytest lexigram-queue/tests -q -m not integration --cov=lexigram.queue`
- Status: **PASS**
- Exit code: `0`
- Duration: `3926 ms`
- Parsed summary: `206 passed, 19 deselected, 4 warnings in 2.57s`
- Counters: passed=206, total=206, failed=0, skipped=0, warnings=4, coverage=82.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:39:01 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 34%]
........................................................................ [ 69%]
..............................................................           [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtur
```

### Package tests: lexigram-resilience

- Scope: `lexigram-resilience/tests`
- Command: `uv run pytest lexigram-resilience/tests -q -m not integration --cov=lexigram.resilience`
- Status: **PASS**
- Exit code: `0`
- Duration: `20531 ms`
- Parsed summary: `299 passed, 23 deselected, 4 warnings in 19.14s`
- Counters: passed=299, total=299, failed=0, skipped=0, warnings=4, coverage=72.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:39:05 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 24%]
........................................................................ [ 48%]
........................................................................ [ 72%]
........................................................................ [ 96%]
...........                                                              [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/
```

### Package tests: lexigram-search

- Scope: `lexigram-search/tests`
- Command: `uv run pytest lexigram-search/tests -q -m not integration --cov=lexigram.search`
- Status: **PASS**
- Exit code: `0`
- Duration: `4540 ms`
- Parsed summary: `809 passed, 4 skipped, 15 deselected, 4 warnings in 3.00s`
- Counters: passed=809, total=813, failed=0, skipped=4, warnings=4, coverage=65.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:39:25 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  8%]
........................................................................ [ 17%]
........................................................................ [ 26%]
........................................................................ [ 35%]
........................................................................ [ 44%]
........................................................................ [ 53%]
........................................................................ [ 62%]
....................................................
```

### Package tests: lexigram-secrets

- Scope: `lexigram-secrets/tests`
- Command: `uv run pytest lexigram-secrets/tests -q -m not integration --cov=lexigram.secrets`
- Status: **PASS**
- Exit code: `0`
- Duration: `1800 ms`
- Parsed summary: `127 passed, 4 warnings in 0.49s`
- Counters: passed=127, total=127, failed=0, skipped=0, warnings=4, coverage=58.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:39:30 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 56%]
.......................................................                  [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/
```

### Package tests: lexigram-sql (unit only, no external DB)

- Scope: `lexigram-sql/tests`
- Command: `uv run pytest lexigram-sql/tests/unit -q -m not integration --cov=lexigram.sql`
- Status: **PASS**
- Exit code: `0`
- Duration: `22926 ms`
- Parsed summary: `1296 passed, 46 skipped, 6 warnings in 21.00s`
- Counters: passed=1296, total=1342, failed=0, skipped=46, warnings=6, coverage=61.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:39:32 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  5%]
........................................................................ [ 10%]
........................................................................ [ 16%]
............ss.......................................................... [ 21%]
........................................................................ [ 26%]
........................................................................ [ 32%]
............................................................s........... [ 37%]
.........ss......s..................................
```

### Package tests: lexigram-storage

- Scope: `lexigram-storage/tests`
- Command: `uv run pytest lexigram-storage/tests -q -m not integration --cov=lexigram.storage`
- Status: **PASS**
- Exit code: `0`
- Duration: `7036 ms`
- Parsed summary: `453 passed, 3 skipped, 22 deselected, 4 warnings in 5.58s`
- Counters: passed=453, total=456, failed=0, skipped=3, warnings=4, coverage=62.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:39:54 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 15%]
........................................................................ [ 31%]
.........................................s.............................. [ 47%]
........................................................................ [ 63%]
........................................................................ [ 79%]
........................................................................ [ 94%]
......................s                                                  [100%]
=============================== warnings summary ===
```

### Package tests: lexigram-tasks

- Scope: `lexigram-tasks/tests`
- Command: `uv run pytest lexigram-tasks/tests -q -m not integration --cov=lexigram.tasks`
- Status: **FAIL**
- Exit code: `1`
- Duration: `11093 ms`
- Parsed summary: `509 passed, 15 skipped, 9 deselected, 4 warnings in 9.51s`
- Counters: passed=509, total=524, failed=0, skipped=15, warnings=4, coverage=73.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:40:02 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 27%]
................................................................sssss... [ 41%]
........................................................................ [ 54%]
...............................sssssssss................................ [ 68%]
........................................................................ [ 82%]
...............s........................................................ [ 96%]
....................
ERROR: Coverage failure: total 
```

### Package tests: lexigram-tenancy

- Scope: `lexigram-tenancy/tests`
- Command: `uv run pytest lexigram-tenancy/tests -q -m not integration --cov=lexigram.tenancy`
- Status: **PASS**
- Exit code: `0`
- Duration: `3276 ms`
- Parsed summary: `360 passed, 4 deselected, 4 warnings in 1.83s`
- Counters: passed=360, total=360, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:40:13 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 20%]
........................................................................ [ 40%]
........................................................................ [ 60%]
........................................................................ [ 80%]
........................................................................ [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/
```

### Package tests: lexigram-testing

- Scope: `lexigram-testing/tests`
- Command: `uv run pytest lexigram-testing/tests -q -m not integration --cov=lexigram.testing`
- Status: **FAIL**
- Exit code: `1`
- Duration: `8568 ms`
- Parsed summary: `436 passed, 15 skipped, 13 deselected, 4 warnings in 7.09s`
- Counters: passed=436, total=451, failed=0, skipped=15, warnings=4, coverage=17.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:40:16 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.................s...................................................... [ 15%]
........................................................................ [ 31%]
........................................................................ [ 47%]
........................................................................ [ 63%]
............ssssssssssssss.............................................. [ 79%]
........................................................................ [ 95%]
...................
ERROR: Coverage failure: total of 17 is less than fail-under=80
                                                
```

### Package tests: lexigram-ui

- Scope: `lexigram-ui/tests`
- Command: `uv run pytest lexigram-ui/tests -q -m not integration --cov=lexigram.ui`
- Status: **PASS**
- Exit code: `0`
- Duration: `7314 ms`
- Parsed summary: `1251 passed, 78 skipped, 8 deselected, 12 warnings in 5.82s`
- Counters: passed=1251, total=1329, failed=0, skipped=78, warnings=12, coverage=70.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:40:24 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
ssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssss [  5%]
........................................................................ [ 10%]
........................................................................ [ 16%]
........................................................................ [ 21%]
........................................................................ [ 27%]
........................................................................ [ 32%]
........................................................................ [ 37%]
....................................................
```

### Package tests: lexigram-vector

- Scope: `lexigram-vector/tests`
- Command: `uv run pytest lexigram-vector/tests -q -m not integration --cov=lexigram.vector`
- Status: **PASS**
- Exit code: `0`
- Duration: `4882 ms`
- Parsed summary: `541 passed, 20 deselected, 4 warnings in 3.36s`
- Counters: passed=541, total=541, failed=0, skipped=0, warnings=4, coverage=77.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:40:32 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 39%]
........................................................................ [ 53%]
........................................................................ [ 66%]
........................................................................ [ 79%]
........................................................................ [ 93%]
.....................................               
```

### Package tests: lexigram-web

- Scope: `lexigram-web/tests`
- Command: `uv run pytest lexigram-web/tests -q -m not integration --cov=lexigram.web`
- Status: **PASS**
- Exit code: `0`
- Duration: `13164 ms`
- Parsed summary: `1415 passed, 7 skipped, 7 deselected, 6 warnings in 11.34s`
- Counters: passed=1415, total=1422, failed=0, skipped=7, warnings=6, coverage=81.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:40:37 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
sss..................................................................... [  5%]
........................................................................ [ 10%]
........................................................................ [ 15%]
........................................................................ [ 20%]
.............................s.......................................... [ 25%]
........................................................................ [ 30%]
..................................................................s..... [ 35%]
....................................................
```

### Package tests: lexigram-webhook

- Scope: `lexigram-webhook/tests`
- Command: `uv run pytest lexigram-webhook/tests -q -m not integration --cov=lexigram.webhook`
- Status: **PASS**
- Exit code: `0`
- Duration: `2850 ms`
- Parsed summary: `334 passed, 4 warnings in 1.46s`
- Counters: passed=334, total=334, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:40:50 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 21%]
........................................................................ [ 43%]
........................................................................ [ 64%]
........................................................................ [ 86%]
..............................................                           [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/
```

### Package tests: lexigram-workflow

- Scope: `lexigram-workflow/tests`
- Command: `uv run pytest lexigram-workflow/tests -q -m not integration --cov=lexigram.workflow`
- Status: **PASS**
- Exit code: `0`
- Duration: `13988 ms`
- Parsed summary: `553 passed, 23 deselected, 4 warnings in 12.61s`
- Counters: passed=553, total=553, failed=0, skipped=0, warnings=4, coverage=70.0%
- Example failures: none
- Output snippet:

```text
2026-08-18 12:40:53 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 39%]
........................................................................ [ 52%]
........................................................................ [ 65%]
........................................................................ [ 78%]
........................................................................ [ 91%]
.................................................   
```

