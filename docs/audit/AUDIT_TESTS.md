# AUDIT_TESTS.md — Lexigram Framework Targeted Test Execution Audit

> **Source**: Live pytest execution evidence for targeted scopes, with `tests/` directory scanning as supporting context.

---

## Summary

- Total passed tests: 31567
- Total failed tests: 0
- Total skipped tests: 335
- Total warnings: 334
- Aggregate code coverage: 75.65%

- Representative commands run: 54
- Commands passing: 52
- Commands failing: 2
- Packages with tests: 54
- Test files: 3367
- Test functions: 31770

### Exit Codes Reference

- **`0`**: Success — All tests passed and code coverage met the configured threshold.
- **`1`**: Failure — Functional tests failed OR code coverage fell below the package's `--cov-fail-under` threshold.
- **`timeout`**: The test command exceeded the execution time limit (120s) and was automatically terminated.

## Execution Evidence

| Label | Code Coverage | Pass/Total | Failed | Skipped | Warnings | Exit Code | Duration |
|-------|---------------|------------|---------|----------|------|-----------|----------|
| Package tests: core/lexigram-contracts | 34.0% | 1812/1812 | 0 | 0 | 4 | 0 | 10380 ms |
| Package tests: core/lexigram | 39.0% | 3026/3031 | 0 | 5 | 2 | 0 | 51111 ms |
| Package tests: experimental/ai/lexigram-ai-agents | 85.0% | 402/402 | 0 | 0 | 4 | 0 | 5808 ms |
| Package tests: experimental/ai/lexigram-ai-evaluation | 97.0% | 167/167 | 0 | 0 | 4 | 0 | 1837 ms |
| Package tests: experimental/ai/lexigram-ai-feedback | 96.0% | 260/260 | 0 | 0 | 4 | 0 | 2100 ms |
| Package tests: experimental/ai/lexigram-ai-governance | 88.0% | 544/544 | 0 | 0 | 46 | 0 | 4585 ms |
| Package tests: experimental/ai/lexigram-ai-guard | 87.0% | 242/242 | 0 | 0 | 7 | 0 | 2107 ms |
| Package tests: experimental/ai/lexigram-ai-llm | 70.0% | 946/967 | 0 | 21 | 4 | 0 | 31086 ms |
| Package tests: experimental/ai/lexigram-ai-mcp | 51.0% | 384/384 | 0 | 0 | 4 | 0 | 3398 ms |
| Package tests: experimental/ai/lexigram-ai-memory | 83.0% | 240/240 | 0 | 0 | 4 | 0 | 2355 ms |
| Package tests: experimental/ai/lexigram-ai-observability | 87.0% | 260/260 | 0 | 0 | 4 | 0 | 2562 ms |
| Package tests: experimental/ai/lexigram-ai-prompt | 87.0% | 307/307 | 0 | 0 | 4 | 0 | 2385 ms |
| Package tests: experimental/ai/lexigram-ai-rag | 62.0% | 528/535 | 0 | 7 | 4 | 0 | 6787 ms |
| Package tests: experimental/ai/lexigram-ai-relay-gateway | 94.0% | 579/579 | 0 | 0 | 4 | 0 | 4142 ms |
| Package tests: experimental/ai/lexigram-ai-relay | 91.0% | 534/534 | 0 | 0 | 4 | 0 | 5627 ms |
| Package tests: experimental/ai/lexigram-ai-session | 88.0% | 210/210 | 0 | 0 | 4 | 0 | 2364 ms |
| Package tests: experimental/ai/lexigram-ai-skills | 78.0% | 268/268 | 0 | 0 | 6 | 0 | 2530 ms |
| Package tests: experimental/ai/lexigram-ai-workers | 87.0% | 328/328 | 0 | 0 | 4 | 0 | 3795 ms |
| Package tests: experimental/ai/lexigram-ai | 42.0% | 470/489 | 0 | 19 | 4 | 1 | 15183 ms |
| Package tests: experimental/apps/lexigram-admin | 77.0% | 4669/4685 | 0 | 16 | 18 | 0 | 53527 ms |
| Package tests: experimental/apps/lexigram-cli | 81.0% | 860/861 | 0 | 1 | 6 | 0 | 11484 ms |
| Package tests: experimental/apps/lexigram-ui | 73.0% | 1251/1329 | 0 | 78 | 12 | 0 | 6436 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-beat | 71.0% | 18/18 | 0 | 0 | 4 | 0 | 2576 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-image | 92.0% | 54/54 | 0 | 0 | 4 | 0 | 2057 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-interpolate | 88.0% | 23/23 | 0 | 0 | 4 | 0 | 1830 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-music | 86.0% | 47/47 | 0 | 0 | 4 | 0 | 1973 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-tts | 78.0% | 63/63 | 0 | 0 | 4 | 0 | 2201 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-upscale | 93.0% | 42/42 | 0 | 0 | 4 | 0 | 2047 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-video | 87.0% | 182/182 | 0 | 0 | 4 | 0 | 5486 ms |
| Package tests: experimental/multimedia/lexigram-multimedia | 55.0% | 86/86 | 0 | 0 | 5 | 0 | 4532 ms |
| Package tests: packages/lexigram-audit | 85.0% | 287/287 | 0 | 0 | 4 | 0 | 2323 ms |
| Package tests: packages/lexigram-auth | 68.0% | 621/625 | 0 | 4 | 6 | 0 | 27720 ms |
| Package tests: packages/lexigram-cache | 80.0% | 870/883 | 0 | 13 | 6 | 0 | 10678 ms |
| Package tests: packages/lexigram-events | 64.0% | 970/985 | 0 | 15 | 6 | 0 | 11730 ms |
| Package tests: packages/lexigram-features | 83.0% | 249/249 | 0 | 0 | 17 | 0 | 3512 ms |
| Package tests: packages/lexigram-graph | 79.0% | 257/258 | 0 | 1 | 4 | 0 | 2182 ms |
| Package tests: packages/lexigram-graphql | 76.0% | 520/522 | 0 | 2 | 23 | 0 | 5842 ms |
| Package tests: packages/lexigram-http | 85.0% | 457/457 | 0 | 0 | 8 | 0 | 2886 ms |
| Package tests: packages/lexigram-monitor | 81.0% | 342/358 | 0 | 16 | 4 | 0 | 8504 ms |
| Package tests: packages/lexigram-nosql | 91.0% | 537/537 | 0 | 0 | 4 | 0 | 3381 ms |
| Package tests: packages/lexigram-notification | 83.0% | 294/294 | 0 | 0 | 4 | 0 | 5483 ms |
| Package tests: packages/lexigram-queue | 84.0% | 232/232 | 0 | 0 | 4 | 0 | 4303 ms |
| Package tests: packages/lexigram-resilience | 75.0% | 311/311 | 0 | 0 | 4 | 0 | 21504 ms |
| Package tests: packages/lexigram-search | 65.0% | 810/815 | 0 | 5 | 4 | 0 | 4258 ms |
| Package tests: packages/lexigram-secrets | 58.0% | 127/127 | 0 | 0 | 4 | 0 | 1636 ms |
| Package tests: packages/lexigram-sql | 41.0% | 1301/1392 | 0 | 91 | 10 | 1 | 84743 ms |
| Package tests: packages/lexigram-storage | 64.0% | 454/457 | 0 | 3 | 4 | 0 | 6673 ms |
| Package tests: packages/lexigram-tasks | 74.0% | 525/541 | 0 | 16 | 4 | 0 | 11015 ms |
| Package tests: packages/lexigram-tenancy | 84.0% | 361/361 | 0 | 0 | 4 | 0 | 2935 ms |
| Package tests: packages/lexigram-testing | 17.0% | 442/457 | 0 | 15 | 2 | 0 | 7997 ms |
| Package tests: packages/lexigram-vector | 78.0% | 526/526 | 0 | 0 | 4 | 0 | 4080 ms |
| Package tests: packages/lexigram-web | 81.0% | 1379/1386 | 0 | 7 | 6 | 0 | 12602 ms |
| Package tests: packages/lexigram-webhook | 90.0% | 336/336 | 0 | 0 | 4 | 0 | 2744 ms |
| Package tests: packages/lexigram-workflow | 72.0% | 557/557 | 0 | 0 | 4 | 0 | 13707 ms |

### Execution Scope Notes

- `framework-core`: real test execution for `lexigram/tests`.
- `package`: real test execution for `<package>/tests` across every discovered Lexigram package with tests.
### Package tests: core/lexigram-contracts

- Scope: `core/lexigram-contracts/tests`
- Command: `uv run pytest core/lexigram-contracts/tests -q -m not integration --cov=core/lexigram.contracts`
- Status: **PASS**
- Exit code: `0`
- Duration: `10380 ms`
- Parsed summary: `1812 passed, 4 warnings in 9.04s`
- Counters: passed=1812, total=1812, failed=0, skipped=0, warnings=4, coverage=34.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:43:20 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  3%]
........................................................................ [  7%]
........................................................................ [ 11%]
........................................................................ [ 15%]
........................................................................ [ 19%]
........................................................................ [ 23%]
........................................................................ [ 27%]
....................................................
```

### Package tests: core/lexigram

- Scope: `core/lexigram/tests`
- Command: `uv run pytest core/lexigram/tests -q -m not integration --cov=core/lexigram`
- Status: **PASS**
- Exit code: `0`
- Duration: `51111 ms`
- Parsed summary: `3026 passed, 5 skipped, 19 deselected, 2 warnings in 48.68s`
- Counters: passed=3026, total=3031, failed=0, skipped=5, warnings=2, coverage=39.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:43:30 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
2026-08-27 08:43:30 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=1 imports=0 is_global=False module=CoreModule providers=1
2026-08-27 08:43:30 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=1 imports=1 is_global=False module=CacheModule providers=1
2026-08-27 08:43:30 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=1 imports=2 is_global=False module=WebModule providers=1
.........................................................
```

### Package tests: experimental/ai/lexigram-ai-agents

- Scope: `experimental/ai/lexigram-ai-agents/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-agents/tests -q -m not integration --cov=experimental/ai/lexigram.ai.agents`
- Status: **PASS**
- Exit code: `0`
- Duration: `5808 ms`
- Parsed summary: `402 passed, 10 deselected, 4 warnings in 4.55s`
- Counters: passed=402, total=402, failed=0, skipped=0, warnings=4, coverage=85.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:44:21 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `1837 ms`
- Parsed summary: `167 passed, 4 warnings in 0.69s`
- Counters: passed=167, total=167, failed=0, skipped=0, warnings=4, coverage=97.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:44:27 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 43%]
........................................................................ [ 86%]
.......................                                                  [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fix
```

### Package tests: experimental/ai/lexigram-ai-feedback

- Scope: `experimental/ai/lexigram-ai-feedback/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-feedback/tests -q -m not integration --cov=experimental/ai/lexigram.ai.feedback`
- Status: **PASS**
- Exit code: `0`
- Duration: `2100 ms`
- Parsed summary: `260 passed, 4 warnings in 0.95s`
- Counters: passed=260, total=260, failed=0, skipped=0, warnings=4, coverage=96.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:44:29 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 27%]
........................................................................ [ 55%]
........................................................................ [ 83%]
............................................                             [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewr
```

### Package tests: experimental/ai/lexigram-ai-governance

- Scope: `experimental/ai/lexigram-ai-governance/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-governance/tests -q -m not integration --cov=experimental/ai/lexigram.ai.governance`
- Status: **PASS**
- Exit code: `0`
- Duration: `4585 ms`
- Parsed summary: `544 passed, 7 deselected, 46 warnings in 3.36s`
- Counters: passed=544, total=544, failed=0, skipped=0, warnings=46, coverage=88.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:44:31 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2107 ms`
- Parsed summary: `242 passed, 17 deselected, 7 warnings in 0.95s`
- Counters: passed=242, total=242, failed=0, skipped=0, warnings=7, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:44:35 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 29%]
........................................................................ [ 59%]
........................................................................ [ 89%]
..........................                                               [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewr
```

### Package tests: experimental/ai/lexigram-ai-llm

- Scope: `experimental/ai/lexigram-ai-llm/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-llm/tests -q -m not integration --cov=experimental/ai/lexigram.ai.llm`
- Status: **PASS**
- Exit code: `0`
- Duration: `31086 ms`
- Parsed summary: `946 passed, 21 skipped, 19 deselected, 4 warnings in 29.58s`
- Counters: passed=946, total=967, failed=0, skipped=21, warnings=4, coverage=70.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:44:38 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `3398 ms`
- Parsed summary: `384 passed, 13 deselected, 4 warnings in 2.17s`
- Counters: passed=384, total=384, failed=0, skipped=0, warnings=4, coverage=51.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:45:09 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2355 ms`
- Parsed summary: `240 passed, 16 deselected, 4 warnings in 1.17s`
- Counters: passed=240, total=240, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:45:12 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 30%]
........................................................................ [ 60%]
........................................................................ [ 90%]
........................                                                 [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewr
```

### Package tests: experimental/ai/lexigram-ai-observability

- Scope: `experimental/ai/lexigram-ai-observability/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-observability/tests -q -m not integration --cov=experimental/ai/lexigram.ai.observability`
- Status: **PASS**
- Exit code: `0`
- Duration: `2562 ms`
- Parsed summary: `260 passed, 10 deselected, 4 warnings in 1.38s`
- Counters: passed=260, total=260, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:45:14 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 27%]
........................................................................ [ 55%]
........................................................................ [ 83%]
............................................                             [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewr
```

### Package tests: experimental/ai/lexigram-ai-prompt

- Scope: `experimental/ai/lexigram-ai-prompt/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-prompt/tests -q -m not integration --cov=experimental/ai/lexigram.ai.prompt`
- Status: **PASS**
- Exit code: `0`
- Duration: `2385 ms`
- Parsed summary: `307 passed, 4 warnings in 1.20s`
- Counters: passed=307, total=307, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:45:17 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 23%]
........................................................................ [ 46%]
........................................................................ [ 70%]
........................................................................ [ 93%]
...................                                                      [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .ve
```

### Package tests: experimental/ai/lexigram-ai-rag

- Scope: `experimental/ai/lexigram-ai-rag/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-rag/tests -q -m not integration --cov=experimental/ai/lexigram.ai.rag`
- Status: **PASS**
- Exit code: `0`
- Duration: `6787 ms`
- Parsed summary: `528 passed, 7 skipped, 8 deselected, 4 warnings in 5.49s`
- Counters: passed=528, total=535, failed=0, skipped=7, warnings=4, coverage=62.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:45:19 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
..........................................................s............. [ 13%]
...sss..........ss...................................................... [ 26%]
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
- Duration: `4142 ms`
- Parsed summary: `579 passed, 4 warnings in 2.88s`
- Counters: passed=579, total=579, failed=0, skipped=0, warnings=4, coverage=94.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:45:26 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
2026-08-27 08:45:26 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=RelayModule providers=0
........................................................................ [ 12%]
........................................................................ [ 24%]
........................................................................ [ 37%]
........................................................................ [ 49%]
........................................................................ [ 62%]
..........................
```

### Package tests: experimental/ai/lexigram-ai-relay

- Scope: `experimental/ai/lexigram-ai-relay/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-relay/tests -q -m not integration --cov=experimental/ai/lexigram.ai.relay`
- Status: **PASS**
- Exit code: `0`
- Duration: `5627 ms`
- Parsed summary: `534 passed, 4 warnings in 4.40s`
- Counters: passed=534, total=534, failed=0, skipped=0, warnings=4, coverage=91.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:45:30 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
2026-08-27 08:45:30 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=RelayModule providers=0
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
- Duration: `2364 ms`
- Parsed summary: `210 passed, 4 warnings in 1.17s`
- Counters: passed=210, total=210, failed=0, skipped=0, warnings=4, coverage=88.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:45:36 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 34%]
........................................................................ [ 68%]
..................................................................       [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fix
```

### Package tests: experimental/ai/lexigram-ai-skills

- Scope: `experimental/ai/lexigram-ai-skills/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-skills/tests -q -m not integration --cov=experimental/ai/lexigram.ai.skills`
- Status: **PASS**
- Exit code: `0`
- Duration: `2530 ms`
- Parsed summary: `268 passed, 6 warnings in 1.35s`
- Counters: passed=268, total=268, failed=0, skipped=0, warnings=6, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:45:38 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 26%]
........................................................................ [ 53%]
........................................................................ [ 80%]
....................................................                     [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewr
```

### Package tests: experimental/ai/lexigram-ai-workers

- Scope: `experimental/ai/lexigram-ai-workers/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-workers/tests -q -m not integration --cov=experimental/ai/lexigram.ai.workers`
- Status: **PASS**
- Exit code: `0`
- Duration: `3795 ms`
- Parsed summary: `328 passed, 7 deselected, 4 warnings in 2.61s`
- Counters: passed=328, total=328, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:45:41 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 21%]
........................................................................ [ 43%]
........................................................................ [ 65%]
........................................................................ [ 87%]
........................................                                 [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .ve
```

### Package tests: experimental/ai/lexigram-ai

- Scope: `experimental/ai/lexigram-ai/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai/tests -q -m not integration --cov=experimental/ai/lexigram.ai`
- Status: **FAIL**
- Exit code: `1`
- Duration: `15183 ms`
- Parsed summary: `470 passed, 19 skipped, 15 deselected, 4 warnings in 13.81s`
- Counters: passed=470, total=489, failed=0, skipped=19, warnings=4, coverage=42.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:45:45 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 15%]
........................................................................ [ 30%]
..................................................................ss.... [ 45%]
................................s....................................... [ 60%]
..........................................................s.s........... [ 75%]
........................................................................ [ 90%]
...........................................
ERROR: Coverage failure: total of 42 is less than fail-under=43
                        
```

### Package tests: experimental/apps/lexigram-admin

- Scope: `experimental/apps/lexigram-admin/tests`
- Command: `uv run pytest experimental/apps/lexigram-admin/tests -q -m not integration --cov=experimental/apps/lexigram.admin`
- Status: **PASS**
- Exit code: `0`
- Duration: `53527 ms`
- Parsed summary: `4669 passed, 16 skipped, 29 deselected, 18 warnings in 51.27s`
- Counters: passed=4669, total=4685, failed=0, skipped=16, warnings=18, coverage=77.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:46:00 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
ss...................................................................... [  1%]
........................................................................ [  3%]
.....................s..................ss.............................. [  4%]
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
- Duration: `11484 ms`
- Parsed summary: `860 passed, 1 skipped, 7 deselected, 6 warnings in 9.91s`
- Counters: passed=860, total=861, failed=0, skipped=1, warnings=6, coverage=81.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:46:53 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  8%]
........................................................................ [ 16%]
........................................................................ [ 25%]
........................................................................ [ 33%]
........................................................................ [ 41%]
........................................................................ [ 50%]
........................................................................ [ 58%]
....................................................
```

### Package tests: experimental/apps/lexigram-ui

- Scope: `experimental/apps/lexigram-ui/tests`
- Command: `uv run pytest experimental/apps/lexigram-ui/tests -q -m not integration --cov=experimental/apps/lexigram.ui`
- Status: **PASS**
- Exit code: `0`
- Duration: `6436 ms`
- Parsed summary: `1251 passed, 78 skipped, 8 deselected, 12 warnings in 5.15s`
- Counters: passed=1251, total=1329, failed=0, skipped=78, warnings=12, coverage=73.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:47:05 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
ssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssss [  5%]
........................................................................ [ 10%]
........................................................................ [ 16%]
........................................................................ [ 21%]
........................................................................ [ 27%]
........................................................................ [ 32%]
........................................................................ [ 37%]
....................................................
```

### Package tests: experimental/multimedia/lexigram-multimedia-beat

- Scope: `experimental/multimedia/lexigram-multimedia-beat/tests`
- Command: `uv run pytest experimental/multimedia/lexigram-multimedia-beat/tests -q -m not integration --cov=experimental/multimedia/lexigram.multimedia.beat`
- Status: **PASS**
- Exit code: `0`
- Duration: `2576 ms`
- Parsed summary: `18 passed, 12 deselected, 4 warnings in 1.21s`
- Counters: passed=18, total=18, failed=0, skipped=0, warnings=4, coverage=71.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:47:11 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
..................                                                       [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  /home/admin/Documents/AI/applications/lexigr
```

### Package tests: experimental/multimedia/lexigram-multimedia-image

- Scope: `experimental/multimedia/lexigram-multimedia-image/tests`
- Command: `uv run pytest experimental/multimedia/lexigram-multimedia-image/tests -q -m not integration --cov=experimental/multimedia/lexigram.multimedia.image`
- Status: **PASS**
- Exit code: `0`
- Duration: `2057 ms`
- Parsed summary: `54 passed, 4 warnings in 0.75s`
- Counters: passed=54, total=54, failed=0, skipped=0, warnings=4, coverage=92.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:47:14 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
......................................................                   [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  /home/admin/Documents/AI/applications/lexigr
```

### Package tests: experimental/multimedia/lexigram-multimedia-interpolate

- Scope: `experimental/multimedia/lexigram-multimedia-interpolate/tests`
- Command: `uv run pytest experimental/multimedia/lexigram-multimedia-interpolate/tests -q -m not integration --cov=experimental/multimedia/lexigram.multimedia.interpolate`
- Status: **PASS**
- Exit code: `0`
- Duration: `1830 ms`
- Parsed summary: `23 passed, 4 warnings in 0.50s`
- Counters: passed=23, total=23, failed=0, skipped=0, warnings=4, coverage=88.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:47:16 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.......................                                                  [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  /home/admin/Documents/AI/applications/lexigr
```

### Package tests: experimental/multimedia/lexigram-multimedia-music

- Scope: `experimental/multimedia/lexigram-multimedia-music/tests`
- Command: `uv run pytest experimental/multimedia/lexigram-multimedia-music/tests -q -m not integration --cov=experimental/multimedia/lexigram.multimedia.music`
- Status: **PASS**
- Exit code: `0`
- Duration: `1973 ms`
- Parsed summary: `47 passed, 4 warnings in 0.66s`
- Counters: passed=47, total=47, failed=0, skipped=0, warnings=4, coverage=86.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:47:18 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
...............................................                          [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  /home/admin/Documents/AI/applications/lexigr
```

### Package tests: experimental/multimedia/lexigram-multimedia-tts

- Scope: `experimental/multimedia/lexigram-multimedia-tts/tests`
- Command: `uv run pytest experimental/multimedia/lexigram-multimedia-tts/tests -q -m not integration --cov=experimental/multimedia/lexigram.multimedia.tts`
- Status: **PASS**
- Exit code: `0`
- Duration: `2201 ms`
- Parsed summary: `63 passed, 4 warnings in 0.88s`
- Counters: passed=63, total=63, failed=0, skipped=0, warnings=4, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:47:20 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
...............................................................          [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  /home/admin/Documents/AI/applications/lexigr
```

### Package tests: experimental/multimedia/lexigram-multimedia-upscale

- Scope: `experimental/multimedia/lexigram-multimedia-upscale/tests`
- Command: `uv run pytest experimental/multimedia/lexigram-multimedia-upscale/tests -q -m not integration --cov=experimental/multimedia/lexigram.multimedia.upscale`
- Status: **PASS**
- Exit code: `0`
- Duration: `2047 ms`
- Parsed summary: `42 passed, 4 warnings in 0.69s`
- Counters: passed=42, total=42, failed=0, skipped=0, warnings=4, coverage=93.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:47:22 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
..........................................                               [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  /home/admin/Documents/AI/applications/lexigr
```

### Package tests: experimental/multimedia/lexigram-multimedia-video

- Scope: `experimental/multimedia/lexigram-multimedia-video/tests`
- Command: `uv run pytest experimental/multimedia/lexigram-multimedia-video/tests -q -m not integration --cov=experimental/multimedia/lexigram.multimedia.video`
- Status: **PASS**
- Exit code: `0`
- Duration: `5486 ms`
- Parsed summary: `182 passed, 4 warnings in 4.13s`
- Counters: passed=182, total=182, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:47:24 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 39%]
........................................................................ [ 79%]
......................................                                   [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fix
```

### Package tests: experimental/multimedia/lexigram-multimedia

- Scope: `experimental/multimedia/lexigram-multimedia/tests`
- Command: `uv run pytest experimental/multimedia/lexigram-multimedia/tests -q -m not integration --cov=experimental/multimedia/lexigram.multimedia`
- Status: **PASS**
- Exit code: `0`
- Duration: `4532 ms`
- Parsed summary: `86 passed, 5 warnings in 3.33s`
- Counters: passed=86, total=86, failed=0, skipped=0, warnings=5, coverage=55.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:47:29 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 83%]
..............                                                           [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packag
```

### Package tests: packages/lexigram-audit

- Scope: `packages/lexigram-audit/tests`
- Command: `uv run pytest packages/lexigram-audit/tests -q -m not integration --cov=packages/lexigram.audit`
- Status: **PASS**
- Exit code: `0`
- Duration: `2323 ms`
- Parsed summary: `287 passed, 17 deselected, 4 warnings in 1.13s`
- Counters: passed=287, total=287, failed=0, skipped=0, warnings=4, coverage=85.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:47:34 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 25%]
........................................................................ [ 50%]
........................................................................ [ 75%]
.......................................................................  [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewr
```

### Package tests: packages/lexigram-auth

- Scope: `packages/lexigram-auth/tests`
- Command: `uv run pytest packages/lexigram-auth/tests -q -m not integration --cov=packages/lexigram.auth`
- Status: **PASS**
- Exit code: `0`
- Duration: `27720 ms`
- Parsed summary: `621 passed, 4 skipped, 2 deselected, 6 warnings in 26.38s`
- Counters: passed=621, total=625, failed=0, skipped=4, warnings=6, coverage=68.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:47:36 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 11%]
........................................................................ [ 23%]
........................................................................ [ 34%]
...................................................................ssss. [ 46%]
........................................................................ [ 57%]
........................................................................ [ 69%]
........................................................................ [ 80%]
....................................................
```

### Package tests: packages/lexigram-cache

- Scope: `packages/lexigram-cache/tests`
- Command: `uv run pytest packages/lexigram-cache/tests -q -m not integration --cov=packages/lexigram.cache`
- Status: **PASS**
- Exit code: `0`
- Duration: `10678 ms`
- Parsed summary: `870 passed, 13 skipped, 13 deselected, 6 warnings in 9.33s`
- Counters: passed=870, total=883, failed=0, skipped=13, warnings=6, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:48:04 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  8%]
.................................................ss..................... [ 16%]
........................................................................ [ 24%]
..........................................................ssssssssss.... [ 32%]
........................................................................ [ 40%]
........................................................................ [ 48%]
........................................................................ [ 57%]
....................................................
```

### Package tests: packages/lexigram-events

- Scope: `packages/lexigram-events/tests`
- Command: `uv run pytest packages/lexigram-events/tests -q -m not integration --cov=packages/lexigram.events`
- Status: **PASS**
- Exit code: `0`
- Duration: `11730 ms`
- Parsed summary: `970 passed, 15 skipped, 11 deselected, 6 warnings in 10.41s`
- Counters: passed=970, total=985, failed=0, skipped=15, warnings=6, coverage=64.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:48:15 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `3512 ms`
- Parsed summary: `249 passed, 14 deselected, 17 warnings in 2.27s`
- Counters: passed=249, total=249, failed=0, skipped=0, warnings=17, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:48:26 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 28%]
........................................................................ [ 57%]
........................................................................ [ 86%]
.................................                                        [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewr
```

### Package tests: packages/lexigram-graph

- Scope: `packages/lexigram-graph/tests`
- Command: `uv run pytest packages/lexigram-graph/tests -q -m not integration --cov=packages/lexigram.graph`
- Status: **PASS**
- Exit code: `0`
- Duration: `2182 ms`
- Parsed summary: `257 passed, 1 skipped, 7 deselected, 4 warnings in 1.02s`
- Counters: passed=257, total=258, failed=0, skipped=1, warnings=4, coverage=79.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:48:30 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 27%]
..................s..................................................... [ 55%]
........................................................................ [ 83%]
..........................................                               [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewr
```

### Package tests: packages/lexigram-graphql

- Scope: `packages/lexigram-graphql/tests`
- Command: `uv run pytest packages/lexigram-graphql/tests -q -m not integration --cov=packages/lexigram.graphql`
- Status: **PASS**
- Exit code: `0`
- Duration: `5842 ms`
- Parsed summary: `520 passed, 2 skipped, 11 deselected, 23 warnings in 4.32s`
- Counters: passed=520, total=522, failed=0, skipped=2, warnings=23, coverage=76.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:48:32 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
s....................................................................... [ 13%]
........................................................................ [ 27%]
.................s...................................................... [ 41%]
........................................................................ [ 55%]
........................................................................ [ 68%]
........................................................................ [ 82%]
........................................................................ [ 96%]
..................                                  
```

### Package tests: packages/lexigram-http

- Scope: `packages/lexigram-http/tests`
- Command: `uv run pytest packages/lexigram-http/tests -q -m not integration --cov=packages/lexigram.http`
- Status: **PASS**
- Exit code: `0`
- Duration: `2886 ms`
- Parsed summary: `457 passed, 9 deselected, 8 warnings in 1.63s`
- Counters: passed=457, total=457, failed=0, skipped=0, warnings=8, coverage=85.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:48:38 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 15%]
........................................................................ [ 31%]
........................................................................ [ 47%]
........................................................................ [ 63%]
........................................................................ [ 78%]
........................................................................ [ 94%]
.........................                                                [100%]
=============================== warnings summary ===
```

### Package tests: packages/lexigram-monitor

- Scope: `packages/lexigram-monitor/tests`
- Command: `uv run pytest packages/lexigram-monitor/tests -q -m not integration --cov=packages/lexigram.monitor`
- Status: **PASS**
- Exit code: `0`
- Duration: `8504 ms`
- Parsed summary: `342 passed, 16 skipped, 4 deselected, 4 warnings in 7.23s`
- Counters: passed=342, total=358, failed=0, skipped=16, warnings=4, coverage=81.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:48:41 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
...............s..s..................ssssss............................. [ 20%]
........................................................................ [ 40%]
.....sss.s.............................................................. [ 60%]
........................................................................ [ 80%]
...........s.ss......................................................    [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .ve
```

### Package tests: packages/lexigram-nosql

- Scope: `packages/lexigram-nosql/tests`
- Command: `uv run pytest packages/lexigram-nosql/tests -q -m not integration --cov=packages/lexigram.nosql`
- Status: **PASS**
- Exit code: `0`
- Duration: `3381 ms`
- Parsed summary: `537 passed, 10 deselected, 4 warnings in 2.16s`
- Counters: passed=537, total=537, failed=0, skipped=0, warnings=4, coverage=91.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:48:49 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 40%]
........................................................................ [ 53%]
........................................................................ [ 67%]
........................................................................ [ 80%]
........................................................................ [ 93%]
.................................                   
```

### Package tests: packages/lexigram-notification

- Scope: `packages/lexigram-notification/tests`
- Command: `uv run pytest packages/lexigram-notification/tests -q -m not integration --cov=packages/lexigram.notification`
- Status: **PASS**
- Exit code: `0`
- Duration: `5483 ms`
- Parsed summary: `294 passed, 8 deselected, 4 warnings in 4.16s`
- Counters: passed=294, total=294, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:48:53 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 24%]
........................................................................ [ 48%]
........................................................................ [ 73%]
........................................................................ [ 97%]
......                                                                   [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .ve
```

### Package tests: packages/lexigram-queue

- Scope: `packages/lexigram-queue/tests`
- Command: `uv run pytest packages/lexigram-queue/tests -q -m not integration --cov=packages/lexigram.queue`
- Status: **PASS**
- Exit code: `0`
- Duration: `4303 ms`
- Parsed summary: `232 passed, 20 deselected, 4 warnings in 3.10s`
- Counters: passed=232, total=232, failed=0, skipped=0, warnings=4, coverage=84.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:48:58 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 31%]
........................................................................ [ 62%]
........................................................................ [ 93%]
................                                                         [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewr
```

### Package tests: packages/lexigram-resilience

- Scope: `packages/lexigram-resilience/tests`
- Command: `uv run pytest packages/lexigram-resilience/tests -q -m not integration --cov=packages/lexigram.resilience`
- Status: **PASS**
- Exit code: `0`
- Duration: `21504 ms`
- Parsed summary: `311 passed, 23 deselected, 4 warnings in 20.32s`
- Counters: passed=311, total=311, failed=0, skipped=0, warnings=4, coverage=75.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:49:03 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 23%]
........................................................................ [ 46%]
........................................................................ [ 69%]
........................................................................ [ 92%]
.......................                                                  [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .ve
```

### Package tests: packages/lexigram-search

- Scope: `packages/lexigram-search/tests`
- Command: `uv run pytest packages/lexigram-search/tests -q -m not integration --cov=packages/lexigram.search`
- Status: **PASS**
- Exit code: `0`
- Duration: `4258 ms`
- Parsed summary: `810 passed, 5 skipped, 15 deselected, 4 warnings in 2.94s`
- Counters: passed=810, total=815, failed=0, skipped=5, warnings=4, coverage=65.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:49:24 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  8%]
........................................................................ [ 17%]
........................................................................ [ 26%]
........................................................................ [ 35%]
........................................................................ [ 44%]
........................................................................ [ 53%]
........................................................................ [ 62%]
....................................................
```

### Package tests: packages/lexigram-secrets

- Scope: `packages/lexigram-secrets/tests`
- Command: `uv run pytest packages/lexigram-secrets/tests -q -m not integration --cov=packages/lexigram.secrets`
- Status: **PASS**
- Exit code: `0`
- Duration: `1636 ms`
- Parsed summary: `127 passed, 4 warnings in 0.47s`
- Counters: passed=127, total=127, failed=0, skipped=0, warnings=4, coverage=58.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:49:28 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 56%]
.......................................................                  [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packag
```

### Package tests: packages/lexigram-sql

- Scope: `packages/lexigram-sql/tests`
- Command: `uv run pytest packages/lexigram-sql/tests -q -m not integration --cov=packages/lexigram.sql`
- Status: **FAIL**
- Exit code: `1`
- Duration: `84743 ms`
- Parsed summary: `1301 passed, 91 skipped, 9 deselected, 10 warnings in 83.09s (0:01:23)`
- Counters: passed=1301, total=1392, failed=0, skipped=91, warnings=10, coverage=41.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:49:30 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................s............................... [  5%]
........................................................................ [ 10%]
........................................................................ [ 15%]
........ss.............................................................. [ 20%]
........................................................................ [ 25%]
........................................................................ [ 31%]
........................................................................ [ 36%]
......s...............ss.....sssssss................
```

### Package tests: packages/lexigram-storage

- Scope: `packages/lexigram-storage/tests`
- Command: `uv run pytest packages/lexigram-storage/tests -q -m not integration --cov=packages/lexigram.storage`
- Status: **PASS**
- Exit code: `0`
- Duration: `6673 ms`
- Parsed summary: `454 passed, 3 skipped, 22 deselected, 4 warnings in 5.46s`
- Counters: passed=454, total=457, failed=0, skipped=3, warnings=4, coverage=64.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:50:55 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 15%]
........................................................................ [ 31%]
..........................................s............................. [ 47%]
........................................................................ [ 63%]
........................................................................ [ 78%]
........................................................................ [ 94%]
.......................s                                                 [100%]
=============================== warnings summary ===
```

### Package tests: packages/lexigram-tasks

- Scope: `packages/lexigram-tasks/tests`
- Command: `uv run pytest packages/lexigram-tasks/tests -q -m not integration --cov=packages/lexigram.tasks`
- Status: **PASS**
- Exit code: `0`
- Duration: `11015 ms`
- Parsed summary: `525 passed, 16 skipped, 9 deselected, 4 warnings in 9.72s`
- Counters: passed=525, total=541, failed=0, skipped=16, warnings=4, coverage=74.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:51:01 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 39%]
....sssss............................................................... [ 53%]
...........................................sssssssss.................... [ 66%]
........................................................................ [ 79%]
...............................ss....................................... [ 93%]
.....................................               
```

### Package tests: packages/lexigram-tenancy

- Scope: `packages/lexigram-tenancy/tests`
- Command: `uv run pytest packages/lexigram-tenancy/tests -q -m not integration --cov=packages/lexigram.tenancy`
- Status: **PASS**
- Exit code: `0`
- Duration: `2935 ms`
- Parsed summary: `361 passed, 4 deselected, 4 warnings in 1.73s`
- Counters: passed=361, total=361, failed=0, skipped=0, warnings=4, coverage=84.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:51:12 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 19%]
........................................................................ [ 39%]
........................................................................ [ 59%]
........................................................................ [ 79%]
........................................................................ [ 99%]
.                                                                        [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/_
```

### Package tests: packages/lexigram-testing

- Scope: `packages/lexigram-testing/tests`
- Command: `uv run pytest packages/lexigram-testing/tests -q -m not integration --cov=packages/lexigram.testing`
- Status: **PASS**
- Exit code: `0`
- Duration: `7997 ms`
- Parsed summary: `442 passed, 15 skipped, 13 deselected, 2 warnings in 6.76s`
- Counters: passed=442, total=457, failed=0, skipped=15, warnings=2, coverage=17.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:51:15 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.................s...................................................... [ 15%]
........................................................................ [ 31%]
........................................................................ [ 47%]
........................................................................ [ 63%]
................ssssssssssssss.......................................... [ 78%]
........................................................................ [ 94%]
.........................                                                [100%]
=============================== warnings summary ===
```

### Package tests: packages/lexigram-vector

- Scope: `packages/lexigram-vector/tests`
- Command: `uv run pytest packages/lexigram-vector/tests -q -m not integration --cov=packages/lexigram.vector`
- Status: **PASS**
- Exit code: `0`
- Duration: `4080 ms`
- Parsed summary: `526 passed, 20 deselected, 4 warnings in 2.81s`
- Counters: passed=526, total=526, failed=0, skipped=0, warnings=4, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:51:23 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 27%]
........................................................................ [ 41%]
........................................................................ [ 54%]
........................................................................ [ 68%]
........................................................................ [ 82%]
........................................................................ [ 95%]
......................                              
```

### Package tests: packages/lexigram-web

- Scope: `packages/lexigram-web/tests`
- Command: `uv run pytest packages/lexigram-web/tests -q -m not integration --cov=packages/lexigram.web`
- Status: **PASS**
- Exit code: `0`
- Duration: `12602 ms`
- Parsed summary: `1379 passed, 7 skipped, 7 deselected, 6 warnings in 11.13s`
- Counters: passed=1379, total=1386, failed=0, skipped=7, warnings=6, coverage=81.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:51:27 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
sss..................................................................... [  5%]
........................................................................ [ 10%]
........................................................................ [ 15%]
...........................................................s............ [ 20%]
........................................................................ [ 25%]
........................................................................ [ 31%]
........................s............................................... [ 36%]
....................................................
```

### Package tests: packages/lexigram-webhook

- Scope: `packages/lexigram-webhook/tests`
- Command: `uv run pytest packages/lexigram-webhook/tests -q -m not integration --cov=packages/lexigram.webhook`
- Status: **PASS**
- Exit code: `0`
- Duration: `2744 ms`
- Parsed summary: `336 passed, 4 warnings in 1.51s`
- Counters: passed=336, total=336, failed=0, skipped=0, warnings=4, coverage=90.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:51:40 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 21%]
........................................................................ [ 42%]
........................................................................ [ 64%]
........................................................................ [ 85%]
................................................                         [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .ve
```

### Package tests: packages/lexigram-workflow

- Scope: `packages/lexigram-workflow/tests`
- Command: `uv run pytest packages/lexigram-workflow/tests -q -m not integration --cov=packages/lexigram.workflow`
- Status: **PASS**
- Exit code: `0`
- Duration: `13707 ms`
- Parsed summary: `557 passed, 23 deselected, 4 warnings in 12.48s`
- Counters: passed=557, total=557, failed=0, skipped=0, warnings=4, coverage=72.0%
- Example failures: none
- Output snippet:

```text
2026-08-27 08:51:43 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 12%]
........................................................................ [ 25%]
........................................................................ [ 38%]
........................................................................ [ 51%]
........................................................................ [ 64%]
........................................................................ [ 77%]
........................................................................ [ 90%]
....................................................
```

