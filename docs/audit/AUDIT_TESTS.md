# AUDIT_TESTS.md — Lexigram Framework Targeted Test Execution Audit

> **Source**: Live pytest execution evidence for targeted scopes, with `tests/` directory scanning as supporting context.

---

## Summary

- Total passed tests: 31626
- Total failed tests: 0
- Total skipped tests: 272
- Total warnings: 335
- Aggregate code coverage: 76.26%

- Representative commands run: 54
- Commands passing: 47
- Commands failing: 7
- Packages with tests: 54
- Test files: 3215
- Test functions: 31739

### Exit Codes Reference

- **`0`**: Success — All tests passed and code coverage met the configured threshold.
- **`1`**: Failure — Functional tests failed OR code coverage fell below the package's `--cov-fail-under` threshold.
- **`timeout`**: The test command exceeded the execution time limit (120s) and was automatically terminated.

## Execution Evidence

| Label | Code Coverage | Pass/Total | Failed | Skipped | Warnings | Exit Code | Duration |
|-------|---------------|------------|---------|----------|------|-----------|----------|
| Package tests: core/lexigram-contracts | 34.0% | 1792/1792 | 0 | 0 | 4 | 1 | 10323 ms |
| Package tests: core/lexigram | 39.0% | 3028/3033 | 0 | 5 | 2 | 1 | 50520 ms |
| Package tests: experimental/ai/lexigram-ai-agents | 85.0% | 402/402 | 0 | 0 | 4 | 0 | 5803 ms |
| Package tests: experimental/ai/lexigram-ai-evaluation | 97.0% | 167/167 | 0 | 0 | 4 | 0 | 1894 ms |
| Package tests: experimental/ai/lexigram-ai-feedback | 96.0% | 260/260 | 0 | 0 | 4 | 0 | 2141 ms |
| Package tests: experimental/ai/lexigram-ai-governance | 88.0% | 544/544 | 0 | 0 | 46 | 0 | 4601 ms |
| Package tests: experimental/ai/lexigram-ai-guard | 87.0% | 242/242 | 0 | 0 | 7 | 0 | 2126 ms |
| Package tests: experimental/ai/lexigram-ai-llm | 71.0% | 949/969 | 0 | 20 | 4 | 0 | 32731 ms |
| Package tests: experimental/ai/lexigram-ai-mcp | 51.0% | 384/384 | 0 | 0 | 4 | 0 | 3378 ms |
| Package tests: experimental/ai/lexigram-ai-memory | 83.0% | 240/240 | 0 | 0 | 4 | 0 | 2364 ms |
| Package tests: experimental/ai/lexigram-ai-observability | 87.0% | 260/260 | 0 | 0 | 4 | 0 | 2601 ms |
| Package tests: experimental/ai/lexigram-ai-prompt | 87.0% | 307/307 | 0 | 0 | 4 | 0 | 2375 ms |
| Package tests: experimental/ai/lexigram-ai-rag | 62.0% | 528/535 | 0 | 7 | 4 | 0 | 6839 ms |
| Package tests: experimental/ai/lexigram-ai-relay-gateway | 94.0% | 579/579 | 0 | 0 | 4 | 0 | 4114 ms |
| Package tests: experimental/ai/lexigram-ai-relay | 91.0% | 534/534 | 0 | 0 | 4 | 0 | 5792 ms |
| Package tests: experimental/ai/lexigram-ai-session | 88.0% | 210/210 | 0 | 0 | 4 | 0 | 2332 ms |
| Package tests: experimental/ai/lexigram-ai-skills | 78.0% | 268/268 | 0 | 0 | 6 | 0 | 2519 ms |
| Package tests: experimental/ai/lexigram-ai-workers | 87.0% | 328/328 | 0 | 0 | 4 | 0 | 3799 ms |
| Package tests: experimental/ai/lexigram-ai | 0.0% | 450/469 | 0 | 19 | 4 | 1 | 5165 ms |
| Package tests: experimental/apps/lexigram-admin | 77.0% | 4694/4705 | 0 | 11 | 18 | 0 | 55528 ms |
| Package tests: experimental/apps/lexigram-cli | 80.0% | 851/852 | 0 | 1 | 6 | 0 | 13649 ms |
| Package tests: experimental/apps/lexigram-ui | 73.0% | 1257/1335 | 0 | 78 | 12 | 0 | 6483 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-beat | 71.0% | 18/18 | 0 | 0 | 4 | 0 | 2528 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-image | 92.0% | 54/54 | 0 | 0 | 4 | 0 | 2057 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-interpolate | 87.0% | 23/23 | 0 | 0 | 4 | 0 | 1803 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-music | 86.0% | 47/47 | 0 | 0 | 4 | 0 | 1990 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-tts | 78.0% | 63/63 | 0 | 0 | 4 | 0 | 2149 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-upscale | 93.0% | 42/42 | 0 | 0 | 4 | 0 | 2047 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-video | 86.0% | 182/182 | 0 | 0 | 4 | 0 | 5409 ms |
| Package tests: experimental/multimedia/lexigram-multimedia | 55.0% | 86/86 | 0 | 0 | 5 | 0 | 4698 ms |
| Package tests: packages/lexigram-audit | 85.0% | 287/287 | 0 | 0 | 4 | 0 | 2281 ms |
| Package tests: packages/lexigram-auth | 68.0% | 614/618 | 0 | 4 | 5 | 1 | 27744 ms |
| Package tests: packages/lexigram-cache | 80.0% | 867/880 | 0 | 13 | 6 | 0 | 10870 ms |
| Package tests: packages/lexigram-events | 63.0% | 969/984 | 0 | 15 | 6 | 1 | 12012 ms |
| Package tests: packages/lexigram-features | 80.0% | 248/248 | 0 | 0 | 17 | 0 | 3361 ms |
| Package tests: packages/lexigram-graph | 79.0% | 257/258 | 0 | 1 | 4 | 0 | 2211 ms |
| Package tests: packages/lexigram-graphql | 76.0% | 519/521 | 0 | 2 | 23 | 0 | 5881 ms |
| Package tests: packages/lexigram-http | 78.0% | 456/456 | 0 | 0 | 8 | 0 | 2760 ms |
| Package tests: packages/lexigram-monitor | 82.0% | 351/356 | 0 | 5 | 4 | 0 | 8467 ms |
| Package tests: packages/lexigram-nosql | 91.0% | 536/536 | 0 | 0 | 4 | 0 | 3373 ms |
| Package tests: packages/lexigram-notification | 83.0% | 289/289 | 0 | 0 | 4 | 0 | 4313 ms |
| Package tests: packages/lexigram-queue | 84.0% | 231/231 | 0 | 0 | 4 | 0 | 4357 ms |
| Package tests: packages/lexigram-resilience | 74.0% | 310/310 | 0 | 0 | 4 | 0 | 20965 ms |
| Package tests: packages/lexigram-search | 66.0% | 813/817 | 0 | 4 | 4 | 0 | 4298 ms |
| Package tests: packages/lexigram-secrets | 58.0% | 127/127 | 0 | 0 | 4 | 0 | 1633 ms |
| Package tests: packages/lexigram-sql | 62.0% | 1347/1394 | 0 | 47 | 10 | 0 | 11557 ms |
| Package tests: packages/lexigram-storage | 62.0% | 453/456 | 0 | 3 | 4 | 0 | 6617 ms |
| Package tests: packages/lexigram-tasks | 74.0% | 525/540 | 0 | 15 | 4 | 1 | 11649 ms |
| Package tests: packages/lexigram-tenancy | 83.0% | 360/360 | 0 | 0 | 4 | 0 | 2865 ms |
| Package tests: packages/lexigram-testing | 17.0% | 438/453 | 0 | 15 | 4 | 1 | 7806 ms |
| Package tests: packages/lexigram-vector | 77.0% | 525/525 | 0 | 0 | 4 | 0 | 4012 ms |
| Package tests: packages/lexigram-web | 81.0% | 1425/1432 | 0 | 7 | 6 | 0 | 12672 ms |
| Package tests: packages/lexigram-webhook | 86.0% | 334/334 | 0 | 0 | 4 | 0 | 2733 ms |
| Package tests: packages/lexigram-workflow | 70.0% | 556/556 | 0 | 0 | 4 | 0 | 13587 ms |

### Execution Scope Notes

- `framework-core`: real test execution for `lexigram/tests`.
- `package`: real test execution for `<package>/tests` across every discovered Lexigram package with tests.
### Package tests: core/lexigram-contracts

- Scope: `core/lexigram-contracts/tests`
- Command: `uv run pytest core/lexigram-contracts/tests -q -m not integration --cov=core/lexigram.contracts`
- Status: **FAIL**
- Exit code: `1`
- Duration: `10323 ms`
- Parsed summary: `1792 passed, 4 warnings in 8.98s`
- Counters: passed=1792, total=1792, failed=0, skipped=0, warnings=4, coverage=34.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:36:31 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  4%]
........................................................................ [  8%]
........................................................................ [ 12%]
........................................................................ [ 16%]
........................................................................ [ 20%]
........................................................................ [ 24%]
........................................................................ [ 28%]
....................................................
```

### Package tests: core/lexigram

- Scope: `core/lexigram/tests`
- Command: `uv run pytest core/lexigram/tests -q -m not integration --cov=core/lexigram`
- Status: **FAIL**
- Exit code: `1`
- Duration: `50520 ms`
- Parsed summary: `3028 passed, 5 skipped, 19 deselected, 2 warnings in 47.95s`
- Counters: passed=3028, total=3033, failed=0, skipped=5, warnings=2, coverage=39.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:36:41 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  2%]
........................................................................ [  4%]
........................................................................ [  7%]
........................................................................ [  9%]
........................................................................ [ 11%]
........................................................................ [ 14%]
........................................................................ [ 16%]
....................................................
```

### Package tests: experimental/ai/lexigram-ai-agents

- Scope: `experimental/ai/lexigram-ai-agents/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-agents/tests -q -m not integration --cov=experimental/ai/lexigram.ai.agents`
- Status: **PASS**
- Exit code: `0`
- Duration: `5803 ms`
- Parsed summary: `402 passed, 10 deselected, 4 warnings in 4.54s`
- Counters: passed=402, total=402, failed=0, skipped=0, warnings=4, coverage=85.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:37:32 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 17%]
........................................................................ [ 35%]
........................................................................ [ 53%]
........................................................................ [ 71%]
........................................................................ [ 89%]
..........................................                               [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/_
```

### Package tests: experimental/ai/lexigram-ai-evaluation

- Scope: `experimental/ai/lexigram-ai-evaluation/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-evaluation/tests -q -m not integration --cov=experimental/ai/lexigram.ai.evaluation`
- Status: **PASS**
- Exit code: `0`
- Duration: `1894 ms`
- Parsed summary: `167 passed, 4 warnings in 0.71s`
- Counters: passed=167, total=167, failed=0, skipped=0, warnings=4, coverage=97.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:37:38 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 43%]
........................................................................ [ 86%]
.......................                                                  [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.cor
```

### Package tests: experimental/ai/lexigram-ai-feedback

- Scope: `experimental/ai/lexigram-ai-feedback/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-feedback/tests -q -m not integration --cov=experimental/ai/lexigram.ai.feedback`
- Status: **PASS**
- Exit code: `0`
- Duration: `2141 ms`
- Parsed summary: `260 passed, 4 warnings in 0.96s`
- Counters: passed=260, total=260, failed=0, skipped=0, warnings=4, coverage=96.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:37:40 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 27%]
........................................................................ [ 55%]
........................................................................ [ 83%]
............................................                             [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarnin
```

### Package tests: experimental/ai/lexigram-ai-governance

- Scope: `experimental/ai/lexigram-ai-governance/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-governance/tests -q -m not integration --cov=experimental/ai/lexigram.ai.governance`
- Status: **PASS**
- Exit code: `0`
- Duration: `4601 ms`
- Parsed summary: `544 passed, 7 deselected, 46 warnings in 3.35s`
- Counters: passed=544, total=544, failed=0, skipped=0, warnings=46, coverage=88.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:37:42 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 39%]
........................................................................ [ 52%]
........................................................................ [ 66%]
........................................................................ [ 79%]
........................................................................ [ 92%]
........................................            
```

### Package tests: experimental/ai/lexigram-ai-guard

- Scope: `experimental/ai/lexigram-ai-guard/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-guard/tests -q -m not integration --cov=experimental/ai/lexigram.ai.guard`
- Status: **PASS**
- Exit code: `0`
- Duration: `2126 ms`
- Parsed summary: `242 passed, 17 deselected, 7 warnings in 0.96s`
- Counters: passed=242, total=242, failed=0, skipped=0, warnings=7, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:37:46 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 29%]
........................................................................ [ 59%]
........................................................................ [ 89%]
..........................                                               [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarnin
```

### Package tests: experimental/ai/lexigram-ai-llm

- Scope: `experimental/ai/lexigram-ai-llm/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-llm/tests -q -m not integration --cov=experimental/ai/lexigram.ai.llm`
- Status: **PASS**
- Exit code: `0`
- Duration: `32731 ms`
- Parsed summary: `949 passed, 20 skipped, 19 deselected, 4 warnings in 30.96s`
- Counters: passed=949, total=969, failed=0, skipped=20, warnings=4, coverage=71.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:37:48 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
ssssssssssssssss........................................................ [  7%]
........................................................................ [ 14%]
........................................................................ [ 22%]
..............................................................ssss...... [ 29%]
........................................................................ [ 37%]
........................................................................ [ 44%]
........................................................................ [ 52%]
....................................................
```

### Package tests: experimental/ai/lexigram-ai-mcp

- Scope: `experimental/ai/lexigram-ai-mcp/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-mcp/tests -q -m not integration --cov=experimental/ai/lexigram.ai.mcp`
- Status: **PASS**
- Exit code: `0`
- Duration: `3378 ms`
- Parsed summary: `384 passed, 13 deselected, 4 warnings in 2.16s`
- Counters: passed=384, total=384, failed=0, skipped=0, warnings=4, coverage=51.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:38:21 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 18%]
........................................................................ [ 37%]
........................................................................ [ 56%]
........................................................................ [ 75%]
........................................................................ [ 93%]
........................                                                 [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/_
```

### Package tests: experimental/ai/lexigram-ai-memory

- Scope: `experimental/ai/lexigram-ai-memory/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-memory/tests -q -m not integration --cov=experimental/ai/lexigram.ai.memory`
- Status: **PASS**
- Exit code: `0`
- Duration: `2364 ms`
- Parsed summary: `240 passed, 16 deselected, 4 warnings in 1.18s`
- Counters: passed=240, total=240, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:38:24 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 30%]
........................................................................ [ 60%]
........................................................................ [ 90%]
........................                                                 [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarnin
```

### Package tests: experimental/ai/lexigram-ai-observability

- Scope: `experimental/ai/lexigram-ai-observability/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-observability/tests -q -m not integration --cov=experimental/ai/lexigram.ai.observability`
- Status: **PASS**
- Exit code: `0`
- Duration: `2601 ms`
- Parsed summary: `260 passed, 10 deselected, 4 warnings in 1.43s`
- Counters: passed=260, total=260, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:38:27 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 27%]
........................................................................ [ 55%]
........................................................................ [ 83%]
............................................                             [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarnin
```

### Package tests: experimental/ai/lexigram-ai-prompt

- Scope: `experimental/ai/lexigram-ai-prompt/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-prompt/tests -q -m not integration --cov=experimental/ai/lexigram.ai.prompt`
- Status: **PASS**
- Exit code: `0`
- Duration: `2375 ms`
- Parsed summary: `307 passed, 4 warnings in 1.20s`
- Counters: passed=307, total=307, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:38:29 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 23%]
........................................................................ [ 46%]
........................................................................ [ 70%]
........................................................................ [ 93%]
...................                                                      [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/py
```

### Package tests: experimental/ai/lexigram-ai-rag

- Scope: `experimental/ai/lexigram-ai-rag/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-rag/tests -q -m not integration --cov=experimental/ai/lexigram.ai.rag`
- Status: **PASS**
- Exit code: `0`
- Duration: `6839 ms`
- Parsed summary: `528 passed, 7 skipped, 8 deselected, 4 warnings in 5.53s`
- Counters: passed=528, total=535, failed=0, skipped=7, warnings=4, coverage=62.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:38:32 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
...........................................................sss.......... [ 13%]
.s..............ss...................................................... [ 26%]
.........................................................s.............. [ 40%]
........................................................................ [ 53%]
........................................................................ [ 67%]
........................................................................ [ 80%]
........................................................................ [ 94%]
...............................                     
```

### Package tests: experimental/ai/lexigram-ai-relay-gateway

- Scope: `experimental/ai/lexigram-ai-relay-gateway/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-relay-gateway/tests -q -m not integration --cov=experimental/ai/lexigram.ai.relay.gateway`
- Status: **PASS**
- Exit code: `0`
- Duration: `4114 ms`
- Parsed summary: `579 passed, 4 warnings in 2.84s`
- Counters: passed=579, total=579, failed=0, skipped=0, warnings=4, coverage=94.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:38:39 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 12%]
........................................................................ [ 24%]
........................................................................ [ 37%]
........................................................................ [ 49%]
........................................................................ [ 62%]
........................................................................ [ 74%]
........................................................................ [ 87%]
....................................................
```

### Package tests: experimental/ai/lexigram-ai-relay

- Scope: `experimental/ai/lexigram-ai-relay/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-relay/tests -q -m not integration --cov=experimental/ai/lexigram.ai.relay`
- Status: **PASS**
- Exit code: `0`
- Duration: `5792 ms`
- Parsed summary: `534 passed, 4 warnings in 4.56s`
- Counters: passed=534, total=534, failed=0, skipped=0, warnings=4, coverage=91.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:38:43 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
2026-08-23 11:38:43 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=RelayModule providers=0
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 40%]
........................................................................ [ 53%]
........................................................................ [ 67%]
..........................
```

### Package tests: experimental/ai/lexigram-ai-session

- Scope: `experimental/ai/lexigram-ai-session/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-session/tests -q -m not integration --cov=experimental/ai/lexigram.ai.session`
- Status: **PASS**
- Exit code: `0`
- Duration: `2332 ms`
- Parsed summary: `210 passed, 4 warnings in 1.16s`
- Counters: passed=210, total=210, failed=0, skipped=0, warnings=4, coverage=88.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:38:49 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 34%]
........................................................................ [ 68%]
..................................................................       [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.cor
```

### Package tests: experimental/ai/lexigram-ai-skills

- Scope: `experimental/ai/lexigram-ai-skills/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-skills/tests -q -m not integration --cov=experimental/ai/lexigram.ai.skills`
- Status: **PASS**
- Exit code: `0`
- Duration: `2519 ms`
- Parsed summary: `268 passed, 6 warnings in 1.35s`
- Counters: passed=268, total=268, failed=0, skipped=0, warnings=6, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:38:51 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 26%]
........................................................................ [ 53%]
........................................................................ [ 80%]
....................................................                     [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarnin
```

### Package tests: experimental/ai/lexigram-ai-workers

- Scope: `experimental/ai/lexigram-ai-workers/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-workers/tests -q -m not integration --cov=experimental/ai/lexigram.ai.workers`
- Status: **PASS**
- Exit code: `0`
- Duration: `3799 ms`
- Parsed summary: `328 passed, 7 deselected, 4 warnings in 2.63s`
- Counters: passed=328, total=328, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:38:53 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 21%]
........................................................................ [ 43%]
........................................................................ [ 65%]
........................................................................ [ 87%]
........................................                                 [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/py
```

### Package tests: experimental/ai/lexigram-ai

- Scope: `experimental/ai/lexigram-ai/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai/tests -q -m not integration --cov=experimental/ai/lexigram.ai`
- Status: **FAIL**
- Exit code: `1`
- Duration: `5165 ms`
- Parsed summary: `450 passed, 19 skipped, 15 deselected, 4 warnings in 3.46s`
- Counters: passed=450, total=469, failed=0, skipped=19, warnings=4, coverage=0.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:38:57 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
...ss..s................................................................ [ 15%]
........................................................................ [ 31%]
...........s.s.......................................................... [ 47%]
........................................................................ [ 63%]
........................................................................ [ 79%]
........................................................................ [ 94%]
.......................
WARNING: Failed to generate report: No data to report.


ERROR: Coverage failure: total of 0 is less than fa
```

### Package tests: experimental/apps/lexigram-admin

- Scope: `experimental/apps/lexigram-admin/tests`
- Command: `uv run pytest experimental/apps/lexigram-admin/tests -q -m not integration --cov=experimental/apps/lexigram.admin`
- Status: **PASS**
- Exit code: `0`
- Duration: `55528 ms`
- Parsed summary: `4694 passed, 11 skipped, 29 deselected, 18 warnings in 53.32s`
- Counters: passed=4694, total=4705, failed=0, skipped=11, warnings=18, coverage=77.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:39:02 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
ss....................................................ss................ [  1%]
........................................................................ [  3%]
.......................s..................ss............................ [  4%]
........................................................................ [  6%]
........................................................................ [  7%]
........................................................................ [  9%]
........................................................................ [ 10%]
....................................................
```

### Package tests: experimental/apps/lexigram-cli

- Scope: `experimental/apps/lexigram-cli/tests`
- Command: `uv run pytest experimental/apps/lexigram-cli/tests -q -m not integration --cov=experimental/apps/lexigram.cli`
- Status: **PASS**
- Exit code: `0`
- Duration: `13649 ms`
- Parsed summary: `851 passed, 1 skipped, 7 deselected, 6 warnings in 11.93s`
- Counters: passed=851, total=852, failed=0, skipped=1, warnings=6, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:39:58 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  8%]
........................................................................ [ 16%]
........................................................................ [ 25%]
........................................................................ [ 33%]
........................................................................ [ 42%]
........................................................................ [ 50%]
........................................................................ [ 59%]
....................................................
```

### Package tests: experimental/apps/lexigram-ui

- Scope: `experimental/apps/lexigram-ui/tests`
- Command: `uv run pytest experimental/apps/lexigram-ui/tests -q -m not integration --cov=experimental/apps/lexigram.ui`
- Status: **PASS**
- Exit code: `0`
- Duration: `6483 ms`
- Parsed summary: `1257 passed, 78 skipped, 8 deselected, 12 warnings in 5.20s`
- Counters: passed=1257, total=1335, failed=0, skipped=78, warnings=12, coverage=73.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:40:12 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
ssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssss [  5%]
........................................................................ [ 10%]
........................................................................ [ 16%]
........................................................................ [ 21%]
........................................................................ [ 26%]
........................................................................ [ 32%]
........................................................................ [ 37%]
....................................................
```

### Package tests: experimental/multimedia/lexigram-multimedia-beat

- Scope: `experimental/multimedia/lexigram-multimedia-beat/tests`
- Command: `uv run pytest experimental/multimedia/lexigram-multimedia-beat/tests -q -m not integration --cov=experimental/multimedia/lexigram.multimedia.beat`
- Status: **PASS**
- Exit code: `0`
- Duration: `2528 ms`
- Parsed summary: `18 passed, 12 deselected, 4 warnings in 1.15s`
- Counters: passed=18, total=18, failed=0, skipped=0, warnings=4, coverage=71.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:40:18 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
..................                                                       [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .v
```

### Package tests: experimental/multimedia/lexigram-multimedia-image

- Scope: `experimental/multimedia/lexigram-multimedia-image/tests`
- Command: `uv run pytest experimental/multimedia/lexigram-multimedia-image/tests -q -m not integration --cov=experimental/multimedia/lexigram.multimedia.image`
- Status: **PASS**
- Exit code: `0`
- Duration: `2057 ms`
- Parsed summary: `54 passed, 4 warnings in 0.74s`
- Counters: passed=54, total=54, failed=0, skipped=0, warnings=4, coverage=92.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:40:21 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
......................................................                   [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .v
```

### Package tests: experimental/multimedia/lexigram-multimedia-interpolate

- Scope: `experimental/multimedia/lexigram-multimedia-interpolate/tests`
- Command: `uv run pytest experimental/multimedia/lexigram-multimedia-interpolate/tests -q -m not integration --cov=experimental/multimedia/lexigram.multimedia.interpolate`
- Status: **PASS**
- Exit code: `0`
- Duration: `1803 ms`
- Parsed summary: `23 passed, 4 warnings in 0.47s`
- Counters: passed=23, total=23, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:40:23 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.......................                                                  [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .v
```

### Package tests: experimental/multimedia/lexigram-multimedia-music

- Scope: `experimental/multimedia/lexigram-multimedia-music/tests`
- Command: `uv run pytest experimental/multimedia/lexigram-multimedia-music/tests -q -m not integration --cov=experimental/multimedia/lexigram.multimedia.music`
- Status: **PASS**
- Exit code: `0`
- Duration: `1990 ms`
- Parsed summary: `47 passed, 4 warnings in 0.66s`
- Counters: passed=47, total=47, failed=0, skipped=0, warnings=4, coverage=86.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:40:24 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
...............................................                          [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .v
```

### Package tests: experimental/multimedia/lexigram-multimedia-tts

- Scope: `experimental/multimedia/lexigram-multimedia-tts/tests`
- Command: `uv run pytest experimental/multimedia/lexigram-multimedia-tts/tests -q -m not integration --cov=experimental/multimedia/lexigram.multimedia.tts`
- Status: **PASS**
- Exit code: `0`
- Duration: `2149 ms`
- Parsed summary: `63 passed, 4 warnings in 0.82s`
- Counters: passed=63, total=63, failed=0, skipped=0, warnings=4, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:40:26 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
...............................................................          [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .v
```

### Package tests: experimental/multimedia/lexigram-multimedia-upscale

- Scope: `experimental/multimedia/lexigram-multimedia-upscale/tests`
- Command: `uv run pytest experimental/multimedia/lexigram-multimedia-upscale/tests -q -m not integration --cov=experimental/multimedia/lexigram.multimedia.upscale`
- Status: **PASS**
- Exit code: `0`
- Duration: `2047 ms`
- Parsed summary: `42 passed, 4 warnings in 0.67s`
- Counters: passed=42, total=42, failed=0, skipped=0, warnings=4, coverage=93.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:40:29 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
..........................................                               [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .v
```

### Package tests: experimental/multimedia/lexigram-multimedia-video

- Scope: `experimental/multimedia/lexigram-multimedia-video/tests`
- Command: `uv run pytest experimental/multimedia/lexigram-multimedia-video/tests -q -m not integration --cov=experimental/multimedia/lexigram.multimedia.video`
- Status: **PASS**
- Exit code: `0`
- Duration: `5409 ms`
- Parsed summary: `182 passed, 4 warnings in 4.08s`
- Counters: passed=182, total=182, failed=0, skipped=0, warnings=4, coverage=86.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:40:31 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 39%]
........................................................................ [ 79%]
......................................                                   [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.cor
```

### Package tests: experimental/multimedia/lexigram-multimedia

- Scope: `experimental/multimedia/lexigram-multimedia/tests`
- Command: `uv run pytest experimental/multimedia/lexigram-multimedia/tests -q -m not integration --cov=experimental/multimedia/lexigram.multimedia`
- Status: **PASS**
- Exit code: `0`
- Duration: `4698 ms`
- Parsed summary: `86 passed, 5 warnings in 3.44s`
- Counters: passed=86, total=86, failed=0, skipped=0, warnings=5, coverage=55.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:40:36 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 83%]
..............                                                           [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/_pytes
```

### Package tests: packages/lexigram-audit

- Scope: `packages/lexigram-audit/tests`
- Command: `uv run pytest packages/lexigram-audit/tests -q -m not integration --cov=packages/lexigram.audit`
- Status: **PASS**
- Exit code: `0`
- Duration: `2281 ms`
- Parsed summary: `287 passed, 17 deselected, 4 warnings in 1.11s`
- Counters: passed=287, total=287, failed=0, skipped=0, warnings=4, coverage=85.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:40:41 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 25%]
........................................................................ [ 50%]
........................................................................ [ 75%]
.......................................................................  [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarnin
```

### Package tests: packages/lexigram-auth

- Scope: `packages/lexigram-auth/tests`
- Command: `uv run pytest packages/lexigram-auth/tests -q -m not integration --cov=packages/lexigram.auth`
- Status: **FAIL**
- Exit code: `1`
- Duration: `27744 ms`
- Parsed summary: `614 passed, 4 skipped, 2 deselected, 5 warnings in 26.46s`
- Counters: passed=614, total=618, failed=0, skipped=4, warnings=5, coverage=68.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:40:43 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 11%]
........................................................................ [ 23%]
........................................................................ [ 34%]
..................................................................ssss.. [ 46%]
........................................................................ [ 58%]
........................................................................ [ 69%]
........................................................................ [ 81%]
....................................................
```

### Package tests: packages/lexigram-cache

- Scope: `packages/lexigram-cache/tests`
- Command: `uv run pytest packages/lexigram-cache/tests -q -m not integration --cov=packages/lexigram.cache`
- Status: **PASS**
- Exit code: `0`
- Duration: `10870 ms`
- Parsed summary: `867 passed, 13 skipped, 13 deselected, 6 warnings in 9.48s`
- Counters: passed=867, total=880, failed=0, skipped=13, warnings=6, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:41:11 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  8%]
.................................................ss..................... [ 16%]
........................................................................ [ 24%]
.........................................................ssssssssss..... [ 32%]
........................................................................ [ 40%]
........................................................................ [ 49%]
........................................................................ [ 57%]
....................................................
```

### Package tests: packages/lexigram-events

- Scope: `packages/lexigram-events/tests`
- Command: `uv run pytest packages/lexigram-events/tests -q -m not integration --cov=packages/lexigram.events`
- Status: **FAIL**
- Exit code: `1`
- Duration: `12012 ms`
- Parsed summary: `969 passed, 15 skipped, 11 deselected, 6 warnings in 10.48s`
- Counters: passed=969, total=984, failed=0, skipped=15, warnings=6, coverage=63.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:41:22 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
...s.................................................................... [  7%]
........................................................................ [ 14%]
........................................................................ [ 22%]
........................................................................ [ 29%]
........................................................................ [ 36%]
........................................................................ [ 44%]
........................................................................ [ 51%]
....................................................
```

### Package tests: packages/lexigram-features

- Scope: `packages/lexigram-features/tests`
- Command: `uv run pytest packages/lexigram-features/tests -q -m not integration --cov=packages/lexigram.features`
- Status: **PASS**
- Exit code: `0`
- Duration: `3361 ms`
- Parsed summary: `248 passed, 14 deselected, 17 warnings in 2.19s`
- Counters: passed=248, total=248, failed=0, skipped=0, warnings=17, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:41:34 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 29%]
........................................................................ [ 58%]
........................................................................ [ 87%]
................................                                         [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarnin
```

### Package tests: packages/lexigram-graph

- Scope: `packages/lexigram-graph/tests`
- Command: `uv run pytest packages/lexigram-graph/tests -q -m not integration --cov=packages/lexigram.graph`
- Status: **PASS**
- Exit code: `0`
- Duration: `2211 ms`
- Parsed summary: `257 passed, 1 skipped, 7 deselected, 4 warnings in 1.06s`
- Counters: passed=257, total=258, failed=0, skipped=1, warnings=4, coverage=79.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:41:37 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 27%]
..................s..................................................... [ 55%]
........................................................................ [ 83%]
..........................................                               [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarnin
```

### Package tests: packages/lexigram-graphql

- Scope: `packages/lexigram-graphql/tests`
- Command: `uv run pytest packages/lexigram-graphql/tests -q -m not integration --cov=packages/lexigram.graphql`
- Status: **PASS**
- Exit code: `0`
- Duration: `5881 ms`
- Parsed summary: `519 passed, 2 skipped, 11 deselected, 23 warnings in 4.36s`
- Counters: passed=519, total=521, failed=0, skipped=2, warnings=23, coverage=76.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:41:39 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
s....................................................................... [ 13%]
........................................................................ [ 27%]
................s....................................................... [ 41%]
........................................................................ [ 55%]
........................................................................ [ 69%]
........................................................................ [ 82%]
........................................................................ [ 96%]
.................                                   
```

### Package tests: packages/lexigram-http

- Scope: `packages/lexigram-http/tests`
- Command: `uv run pytest packages/lexigram-http/tests -q -m not integration --cov=packages/lexigram.http`
- Status: **PASS**
- Exit code: `0`
- Duration: `2760 ms`
- Parsed summary: `456 passed, 9 deselected, 8 warnings in 1.53s`
- Counters: passed=456, total=456, failed=0, skipped=0, warnings=8, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:41:45 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 15%]
........................................................................ [ 31%]
........................................................................ [ 47%]
........................................................................ [ 63%]
........................................................................ [ 78%]
........................................................................ [ 94%]
........................                                                 [100%]
=============================== warnings summary ===
```

### Package tests: packages/lexigram-monitor

- Scope: `packages/lexigram-monitor/tests`
- Command: `uv run pytest packages/lexigram-monitor/tests -q -m not integration --cov=packages/lexigram.monitor`
- Status: **PASS**
- Exit code: `0`
- Duration: `8467 ms`
- Parsed summary: `351 passed, 5 skipped, 4 deselected, 4 warnings in 7.22s`
- Counters: passed=351, total=356, failed=0, skipped=5, warnings=4, coverage=82.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:41:48 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 20%]
........................................................................ [ 40%]
......sss.s............................................................. [ 60%]
........................................................................ [ 80%]
............s.......................................................     [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/py
```

### Package tests: packages/lexigram-nosql

- Scope: `packages/lexigram-nosql/tests`
- Command: `uv run pytest packages/lexigram-nosql/tests -q -m not integration --cov=packages/lexigram.nosql`
- Status: **PASS**
- Exit code: `0`
- Duration: `3373 ms`
- Parsed summary: `536 passed, 10 deselected, 4 warnings in 2.15s`
- Counters: passed=536, total=536, failed=0, skipped=0, warnings=4, coverage=91.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:41:56 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 40%]
........................................................................ [ 53%]
........................................................................ [ 67%]
........................................................................ [ 80%]
........................................................................ [ 94%]
................................                    
```

### Package tests: packages/lexigram-notification

- Scope: `packages/lexigram-notification/tests`
- Command: `uv run pytest packages/lexigram-notification/tests -q -m not integration --cov=packages/lexigram.notification`
- Status: **PASS**
- Exit code: `0`
- Duration: `4313 ms`
- Parsed summary: `289 passed, 8 deselected, 4 warnings in 2.94s`
- Counters: passed=289, total=289, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:42:00 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 24%]
........................................................................ [ 49%]
........................................................................ [ 74%]
........................................................................ [ 99%]
.                                                                        [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/py
```

### Package tests: packages/lexigram-queue

- Scope: `packages/lexigram-queue/tests`
- Command: `uv run pytest packages/lexigram-queue/tests -q -m not integration --cov=packages/lexigram.queue`
- Status: **PASS**
- Exit code: `0`
- Duration: `4357 ms`
- Parsed summary: `231 passed, 20 deselected, 4 warnings in 3.16s`
- Counters: passed=231, total=231, failed=0, skipped=0, warnings=4, coverage=84.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:42:04 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 31%]
........................................................................ [ 62%]
........................................................................ [ 93%]
...............                                                          [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarnin
```

### Package tests: packages/lexigram-resilience

- Scope: `packages/lexigram-resilience/tests`
- Command: `uv run pytest packages/lexigram-resilience/tests -q -m not integration --cov=packages/lexigram.resilience`
- Status: **PASS**
- Exit code: `0`
- Duration: `20965 ms`
- Parsed summary: `310 passed, 23 deselected, 4 warnings in 19.79s`
- Counters: passed=310, total=310, failed=0, skipped=0, warnings=4, coverage=74.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:42:08 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 23%]
........................................................................ [ 46%]
........................................................................ [ 69%]
........................................................................ [ 92%]
......................                                                   [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/py
```

### Package tests: packages/lexigram-search

- Scope: `packages/lexigram-search/tests`
- Command: `uv run pytest packages/lexigram-search/tests -q -m not integration --cov=packages/lexigram.search`
- Status: **PASS**
- Exit code: `0`
- Duration: `4298 ms`
- Parsed summary: `813 passed, 4 skipped, 15 deselected, 4 warnings in 3.00s`
- Counters: passed=813, total=817, failed=0, skipped=4, warnings=4, coverage=66.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:42:29 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  8%]
........................................................................ [ 17%]
........................................................................ [ 26%]
........................................................................ [ 35%]
........................................................................ [ 44%]
........................................................................ [ 53%]
........................................................................ [ 61%]
....................................................
```

### Package tests: packages/lexigram-secrets

- Scope: `packages/lexigram-secrets/tests`
- Command: `uv run pytest packages/lexigram-secrets/tests -q -m not integration --cov=packages/lexigram.secrets`
- Status: **PASS**
- Exit code: `0`
- Duration: `1633 ms`
- Parsed summary: `127 passed, 4 warnings in 0.47s`
- Counters: passed=127, total=127, failed=0, skipped=0, warnings=4, coverage=58.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:42:34 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 56%]
.......................................................                  [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/_pytes
```

### Package tests: packages/lexigram-sql

- Scope: `packages/lexigram-sql/tests`
- Command: `uv run pytest packages/lexigram-sql/tests -q -m not integration --cov=packages/lexigram.sql`
- Status: **PASS**
- Exit code: `0`
- Duration: `11557 ms`
- Parsed summary: `1347 passed, 47 skipped, 9 deselected, 10 warnings in 9.93s`
- Counters: passed=1347, total=1394, failed=0, skipped=47, warnings=10, coverage=62.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:42:35 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................s............................... [  5%]
........................................................................ [ 10%]
........................................................................ [ 15%]
...ss................................................................... [ 20%]
........................................................................ [ 25%]
........................................................................ [ 30%]
........................................................................ [ 36%]
.s................s..........ss.....................
```

### Package tests: packages/lexigram-storage

- Scope: `packages/lexigram-storage/tests`
- Command: `uv run pytest packages/lexigram-storage/tests -q -m not integration --cov=packages/lexigram.storage`
- Status: **PASS**
- Exit code: `0`
- Duration: `6617 ms`
- Parsed summary: `453 passed, 3 skipped, 22 deselected, 4 warnings in 5.41s`
- Counters: passed=453, total=456, failed=0, skipped=3, warnings=4, coverage=62.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:42:47 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 15%]
........................................................................ [ 31%]
.........................................s.............................. [ 47%]
........................................................................ [ 63%]
........................................................................ [ 79%]
........................................................................ [ 94%]
......................s                                                  [100%]
=============================== warnings summary ===
```

### Package tests: packages/lexigram-tasks

- Scope: `packages/lexigram-tasks/tests`
- Command: `uv run pytest packages/lexigram-tasks/tests -q -m not integration --cov=packages/lexigram.tasks`
- Status: **FAIL**
- Exit code: `1`
- Duration: `11649 ms`
- Parsed summary: `525 passed, 15 skipped, 9 deselected, 4 warnings in 10.28s`
- Counters: passed=525, total=540, failed=0, skipped=15, warnings=4, coverage=74.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:42:53 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 40%]
...sssss................................................................ [ 53%]
..........................................sssssssss..................... [ 66%]
........................................................................ [ 80%]
...............................s........................................ [ 93%]
....................................
ERROR: Coverage
```

### Package tests: packages/lexigram-tenancy

- Scope: `packages/lexigram-tenancy/tests`
- Command: `uv run pytest packages/lexigram-tenancy/tests -q -m not integration --cov=packages/lexigram.tenancy`
- Status: **PASS**
- Exit code: `0`
- Duration: `2865 ms`
- Parsed summary: `360 passed, 4 deselected, 4 warnings in 1.66s`
- Counters: passed=360, total=360, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:43:05 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 20%]
........................................................................ [ 40%]
........................................................................ [ 60%]
........................................................................ [ 80%]
........................................................................ [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/py
```

### Package tests: packages/lexigram-testing

- Scope: `packages/lexigram-testing/tests`
- Command: `uv run pytest packages/lexigram-testing/tests -q -m not integration --cov=packages/lexigram.testing`
- Status: **FAIL**
- Exit code: `1`
- Duration: `7806 ms`
- Parsed summary: `438 passed, 15 skipped, 13 deselected, 4 warnings in 6.53s`
- Counters: passed=438, total=453, failed=0, skipped=15, warnings=4, coverage=17.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:43:08 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.................s...................................................... [ 15%]
........................................................................ [ 31%]
........................................................................ [ 47%]
........................................................................ [ 63%]
............ssssssssssssss.............................................. [ 79%]
........................................................................ [ 95%]
.....................
ERROR: Coverage failure: total of 17 is less than fail-under=80
                                              
```

### Package tests: packages/lexigram-vector

- Scope: `packages/lexigram-vector/tests`
- Command: `uv run pytest packages/lexigram-vector/tests -q -m not integration --cov=packages/lexigram.vector`
- Status: **PASS**
- Exit code: `0`
- Duration: `4012 ms`
- Parsed summary: `525 passed, 20 deselected, 4 warnings in 2.76s`
- Counters: passed=525, total=525, failed=0, skipped=0, warnings=4, coverage=77.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:43:16 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 27%]
........................................................................ [ 41%]
........................................................................ [ 54%]
........................................................................ [ 68%]
........................................................................ [ 82%]
........................................................................ [ 96%]
.....................                               
```

### Package tests: packages/lexigram-web

- Scope: `packages/lexigram-web/tests`
- Command: `uv run pytest packages/lexigram-web/tests -q -m not integration --cov=packages/lexigram.web`
- Status: **PASS**
- Exit code: `0`
- Duration: `12672 ms`
- Parsed summary: `1425 passed, 7 skipped, 7 deselected, 6 warnings in 11.19s`
- Counters: passed=1425, total=1432, failed=0, skipped=7, warnings=6, coverage=81.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:43:20 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
sss..................................................................... [  5%]
........................................................................ [ 10%]
........................................................................ [ 15%]
........................................................................ [ 20%]
.................................s...................................... [ 25%]
........................................................................ [ 30%]
......................................................................s. [ 35%]
....................................................
```

### Package tests: packages/lexigram-webhook

- Scope: `packages/lexigram-webhook/tests`
- Command: `uv run pytest packages/lexigram-webhook/tests -q -m not integration --cov=packages/lexigram.webhook`
- Status: **PASS**
- Exit code: `0`
- Duration: `2733 ms`
- Parsed summary: `334 passed, 4 warnings in 1.50s`
- Counters: passed=334, total=334, failed=0, skipped=0, warnings=4, coverage=86.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:43:32 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 21%]
........................................................................ [ 43%]
........................................................................ [ 64%]
........................................................................ [ 86%]
..............................................                           [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/py
```

### Package tests: packages/lexigram-workflow

- Scope: `packages/lexigram-workflow/tests`
- Command: `uv run pytest packages/lexigram-workflow/tests -q -m not integration --cov=packages/lexigram.workflow`
- Status: **PASS**
- Exit code: `0`
- Duration: `13587 ms`
- Parsed summary: `556 passed, 23 deselected, 4 warnings in 12.38s`
- Counters: passed=556, total=556, failed=0, skipped=0, warnings=4, coverage=70.0%
- Example failures: none
- Output snippet:

```text
2026-08-23 11:43:35 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 12%]
........................................................................ [ 25%]
........................................................................ [ 38%]
........................................................................ [ 51%]
........................................................................ [ 64%]
........................................................................ [ 77%]
........................................................................ [ 90%]
....................................................
```

