# AUDIT_TESTS.md — Lexigram Framework Targeted Test Execution Audit

> **Source**: Live pytest execution evidence for targeted scopes, with `tests/` directory scanning as supporting context.

---

## Summary

- Total passed tests: 31498
- Total failed tests: 20
- Total skipped tests: 233
- Total warnings: 314
- Aggregate code coverage: 76.15%

- Representative commands run: 54
- Commands passing: 44
- Commands failing: 10
- Packages with tests: 54
- Test files: 3066
- Test functions: 31605

### Exit Codes Reference

- **`0`**: Success — All tests passed and code coverage met the configured threshold.
- **`1`**: Failure — Functional tests failed OR code coverage fell below the package's `--cov-fail-under` threshold.
- **`timeout`**: The test command exceeded the execution time limit (120s) and was automatically terminated.

## Execution Evidence

| Label | Code Coverage | Pass/Total | Failed | Skipped | Warnings | Exit Code | Duration |
|-------|---------------|------------|---------|----------|------|-----------|----------|
| Package tests: core/lexigram-contracts | 34.0% | 1791/1792 | 1 | 0 | 4 | 1 | 11080 ms |
| Package tests: core/lexigram | 38.0% | 2988/2996 | 2 | 6 | 2 | 1 | 52350 ms |
| Package tests: experimental/ai/lexigram-ai-agents | 85.0% | 402/402 | 0 | 0 | 4 | 0 | 6073 ms |
| Package tests: experimental/ai/lexigram-ai-evaluation | 97.0% | 166/166 | 0 | 0 | 4 | 0 | 1940 ms |
| Package tests: experimental/ai/lexigram-ai-feedback | 96.0% | 260/260 | 0 | 0 | 4 | 0 | 2256 ms |
| Package tests: experimental/ai/lexigram-ai-governance | 88.0% | 544/544 | 0 | 0 | 29 | 0 | 4747 ms |
| Package tests: experimental/ai/lexigram-ai-guard | 87.0% | 242/242 | 0 | 0 | 7 | 0 | 2293 ms |
| Package tests: experimental/ai/lexigram-ai-llm | 71.0% | 949/969 | 0 | 20 | 4 | 0 | 33206 ms |
| Package tests: experimental/ai/lexigram-ai-mcp | 51.0% | 384/384 | 0 | 0 | 4 | 0 | 3702 ms |
| Package tests: experimental/ai/lexigram-ai-memory | 83.0% | 240/240 | 0 | 0 | 4 | 0 | 2512 ms |
| Package tests: experimental/ai/lexigram-ai-observability | 87.0% | 260/260 | 0 | 0 | 4 | 0 | 2756 ms |
| Package tests: experimental/ai/lexigram-ai-prompt | 87.0% | 307/307 | 0 | 0 | 4 | 0 | 2547 ms |
| Package tests: experimental/ai/lexigram-ai-rag | 62.0% | 528/535 | 0 | 7 | 4 | 0 | 7126 ms |
| Package tests: experimental/ai/lexigram-ai-relay-gateway | 94.0% | 551/551 | 0 | 0 | 4 | 0 | 4267 ms |
| Package tests: experimental/ai/lexigram-ai-relay | 91.0% | 539/539 | 0 | 0 | 4 | 0 | 6014 ms |
| Package tests: experimental/ai/lexigram-ai-session | 88.0% | 210/210 | 0 | 0 | 4 | 0 | 2518 ms |
| Package tests: experimental/ai/lexigram-ai-skills | 78.0% | 268/268 | 0 | 0 | 6 | 0 | 2662 ms |
| Package tests: experimental/ai/lexigram-ai-workers | 87.0% | 328/328 | 0 | 0 | 4 | 0 | 3966 ms |
| Package tests: experimental/ai/lexigram-ai | 0.0% | 450/469 | 0 | 19 | 4 | 1 | 5368 ms |
| Package tests: experimental/apps/lexigram-admin | 76.0% | 4596/4615 | 8 | 11 | 18 | 1 | 61752 ms |
| Package tests: experimental/apps/lexigram-cli | 78.0% | 845/852 | 6 | 1 | 6 | 1 | 13534 ms |
| Package tests: experimental/apps/lexigram-ui | 73.0% | 1257/1335 | 0 | 78 | 12 | 0 | 6948 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-beat | 71.0% | 18/18 | 0 | 0 | 4 | 0 | 2691 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-image | 92.0% | 54/54 | 0 | 0 | 4 | 0 | 2162 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-interpolate | 87.0% | 23/23 | 0 | 0 | 4 | 0 | 1900 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-music | 86.0% | 43/46 | 3 | 0 | 4 | 1 | 2391 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-tts | 78.0% | 63/63 | 0 | 0 | 4 | 0 | 2388 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-upscale | 93.0% | 42/42 | 0 | 0 | 4 | 0 | 2177 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-video | 86.0% | 182/182 | 0 | 0 | 4 | 0 | 5530 ms |
| Package tests: experimental/multimedia/lexigram-multimedia | 55.0% | 86/86 | 0 | 0 | 5 | 0 | 4883 ms |
| Package tests: packages/lexigram-audit | 85.0% | 287/287 | 0 | 0 | 4 | 0 | 2600 ms |
| Package tests: packages/lexigram-auth | 68.0% | 614/618 | 0 | 4 | 5 | 1 | 28158 ms |
| Package tests: packages/lexigram-cache | 80.0% | 867/880 | 0 | 13 | 6 | 0 | 11267 ms |
| Package tests: packages/lexigram-events | 63.0% | 969/984 | 0 | 15 | 6 | 1 | 12400 ms |
| Package tests: packages/lexigram-features | 80.0% | 248/248 | 0 | 0 | 17 | 0 | 3533 ms |
| Package tests: packages/lexigram-graph | 79.0% | 257/258 | 0 | 1 | 4 | 0 | 2386 ms |
| Package tests: packages/lexigram-graphql | 76.0% | 519/521 | 0 | 2 | 23 | 0 | 6088 ms |
| Package tests: packages/lexigram-http | 77.0% | 450/450 | 0 | 0 | 4 | 0 | 2917 ms |
| Package tests: packages/lexigram-monitor | 82.0% | 349/354 | 0 | 5 | 4 | 0 | 8744 ms |
| Package tests: packages/lexigram-nosql | 91.0% | 536/536 | 0 | 0 | 4 | 0 | 3737 ms |
| Package tests: packages/lexigram-notification | 83.0% | 289/289 | 0 | 0 | 4 | 0 | 4964 ms |
| Package tests: packages/lexigram-queue | 84.0% | 228/228 | 0 | 0 | 4 | 0 | 4395 ms |
| Package tests: packages/lexigram-resilience | 74.0% | 310/310 | 0 | 0 | 4 | 0 | 19709 ms |
| Package tests: packages/lexigram-search | 65.0% | 813/817 | 0 | 4 | 4 | 0 | 4679 ms |
| Package tests: packages/lexigram-secrets | 58.0% | 127/127 | 0 | 0 | 4 | 0 | 1762 ms |
| Package tests: packages/lexigram-sql | 63.0% | 1387/1394 | 0 | 7 | 10 | 0 | 15616 ms |
| Package tests: packages/lexigram-storage | 62.0% | 453/456 | 0 | 3 | 4 | 0 | 6906 ms |
| Package tests: packages/lexigram-tasks | 73.0% | 525/540 | 0 | 15 | 4 | 1 | 11759 ms |
| Package tests: packages/lexigram-tenancy | 83.0% | 360/360 | 0 | 0 | 4 | 0 | 3030 ms |
| Package tests: packages/lexigram-testing | 17.0% | 436/451 | 0 | 15 | 4 | 1 | 8415 ms |
| Package tests: packages/lexigram-vector | 77.0% | 546/546 | 0 | 0 | 4 | 0 | 4620 ms |
| Package tests: packages/lexigram-web | 81.0% | 1422/1429 | 0 | 7 | 6 | 0 | 13431 ms |
| Package tests: packages/lexigram-webhook | 86.0% | 334/334 | 0 | 0 | 4 | 0 | 2880 ms |
| Package tests: packages/lexigram-workflow | 70.0% | 556/556 | 0 | 0 | 4 | 0 | 13787 ms |

### Execution Scope Notes

- `framework-core`: real test execution for `lexigram/tests`.
- `package`: real test execution for `<package>/tests` across every discovered Lexigram package with tests.
### Package tests: core/lexigram-contracts

- Scope: `core/lexigram-contracts/tests`
- Command: `uv run pytest core/lexigram-contracts/tests -q -m not integration --cov=core/lexigram.contracts`
- Status: **FAIL**
- Exit code: `1`
- Duration: `11080 ms`
- Parsed summary: `1 failed, 1791 passed, 4 warnings in 9.65s`
- Counters: passed=1791, total=1792, failed=1, skipped=0, warnings=4, coverage=34.0%
- Example failures: `core/lexigram-contracts/tests/unit/test_tasks_protocols.py::TestTaskProviderProtocol::test_is_runtime_checkable`
- Output snippet:

```text
2026-08-21 00:13:19 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `52350 ms`
- Parsed summary: `2 failed, 2988 passed, 6 skipped, 19 deselected, 2 warnings in 49.67s`
- Counters: passed=2988, total=2996, failed=2, skipped=6, warnings=2, coverage=38.0%
- Example failures: `core/lexigram/tests/unit/concurrency/test_task_utils.py::TestCreateTrackedTask::test_exception_in_task_is_logged`, `core/lexigram/tests/unit/test_config_lexigram.py::TestConfigSystem::test_base_config_load_default`
- Output snippet:

```text
2026-08-21 00:13:30 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  2%]
........................................................................ [  4%]
........................................................................ [  7%]
..........................F............................................. [  9%]
........................................................................ [ 12%]
........................................................................ [ 14%]
........................................................................ [ 16%]
....................................................
```

### Package tests: experimental/ai/lexigram-ai-agents

- Scope: `experimental/ai/lexigram-ai-agents/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-agents/tests -q -m not integration --cov=experimental/ai/lexigram.ai.agents`
- Status: **PASS**
- Exit code: `0`
- Duration: `6073 ms`
- Parsed summary: `402 passed, 10 deselected, 4 warnings in 4.71s`
- Counters: passed=402, total=402, failed=0, skipped=0, warnings=4, coverage=85.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:14:22 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `1940 ms`
- Parsed summary: `166 passed, 4 warnings in 0.73s`
- Counters: passed=166, total=166, failed=0, skipped=0, warnings=4, coverage=97.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:14:28 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 43%]
........................................................................ [ 86%]
......................                                                   [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.cor
```

### Package tests: experimental/ai/lexigram-ai-feedback

- Scope: `experimental/ai/lexigram-ai-feedback/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-feedback/tests -q -m not integration --cov=experimental/ai/lexigram.ai.feedback`
- Status: **PASS**
- Exit code: `0`
- Duration: `2256 ms`
- Parsed summary: `260 passed, 4 warnings in 1.03s`
- Counters: passed=260, total=260, failed=0, skipped=0, warnings=4, coverage=96.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:14:30 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4747 ms`
- Parsed summary: `544 passed, 7 deselected, 29 warnings in 3.47s`
- Counters: passed=544, total=544, failed=0, skipped=0, warnings=29, coverage=88.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:14:32 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2293 ms`
- Parsed summary: `242 passed, 17 deselected, 7 warnings in 1.07s`
- Counters: passed=242, total=242, failed=0, skipped=0, warnings=7, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:14:37 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `33206 ms`
- Parsed summary: `949 passed, 20 skipped, 19 deselected, 4 warnings in 31.43s`
- Counters: passed=949, total=969, failed=0, skipped=20, warnings=4, coverage=71.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:14:39 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `3702 ms`
- Parsed summary: `384 passed, 13 deselected, 4 warnings in 2.40s`
- Counters: passed=384, total=384, failed=0, skipped=0, warnings=4, coverage=51.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:15:13 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2512 ms`
- Parsed summary: `240 passed, 16 deselected, 4 warnings in 1.26s`
- Counters: passed=240, total=240, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:15:16 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2756 ms`
- Parsed summary: `260 passed, 10 deselected, 4 warnings in 1.48s`
- Counters: passed=260, total=260, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:15:19 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2547 ms`
- Parsed summary: `307 passed, 4 warnings in 1.30s`
- Counters: passed=307, total=307, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:15:22 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `7126 ms`
- Parsed summary: `528 passed, 7 skipped, 8 deselected, 4 warnings in 5.75s`
- Counters: passed=528, total=535, failed=0, skipped=7, warnings=4, coverage=62.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:15:24 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4267 ms`
- Parsed summary: `551 passed, 4 warnings in 2.89s`
- Counters: passed=551, total=551, failed=0, skipped=0, warnings=4, coverage=94.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:15:31 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 39%]
........................................................................ [ 52%]
........................................................................ [ 65%]
........................................................................ [ 78%]
........................................................................ [ 91%]
...............................................     
```

### Package tests: experimental/ai/lexigram-ai-relay

- Scope: `experimental/ai/lexigram-ai-relay/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-relay/tests -q -m not integration --cov=experimental/ai/lexigram.ai.relay`
- Status: **PASS**
- Exit code: `0`
- Duration: `6014 ms`
- Parsed summary: `539 passed, 4 warnings in 4.69s`
- Counters: passed=539, total=539, failed=0, skipped=0, warnings=4, coverage=91.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:15:35 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
2026-08-21 00:15:36 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=RelayModule providers=0
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 40%]
........................................................................ [ 53%]
........................................................................ [ 66%]
..........................
```

### Package tests: experimental/ai/lexigram-ai-session

- Scope: `experimental/ai/lexigram-ai-session/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-session/tests -q -m not integration --cov=experimental/ai/lexigram.ai.session`
- Status: **PASS**
- Exit code: `0`
- Duration: `2518 ms`
- Parsed summary: `210 passed, 4 warnings in 1.24s`
- Counters: passed=210, total=210, failed=0, skipped=0, warnings=4, coverage=88.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:15:42 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2662 ms`
- Parsed summary: `268 passed, 6 warnings in 1.41s`
- Counters: passed=268, total=268, failed=0, skipped=0, warnings=6, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:15:44 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `3966 ms`
- Parsed summary: `328 passed, 7 deselected, 4 warnings in 2.71s`
- Counters: passed=328, total=328, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:15:47 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `5368 ms`
- Parsed summary: `450 passed, 19 skipped, 15 deselected, 4 warnings in 3.62s`
- Counters: passed=450, total=469, failed=0, skipped=19, warnings=4, coverage=0.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:15:51 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Status: **FAIL**
- Exit code: `1`
- Duration: `61752 ms`
- Parsed summary: `8 failed, 4596 passed, 11 skipped, 29 deselected, 18 warnings in 59.47s`
- Counters: passed=4596, total=4615, failed=8, skipped=11, warnings=18, coverage=76.0%
- Example failures: `experimental/apps/lexigram-admin/tests/e2e/test_admin_email_verify_http_e2e.py::test_profile_shows_verified_status`, `experimental/apps/lexigram-admin/tests/e2e/test_admin_email_verify_http_e2e.py::test_profile_shows_unverified_status`, `experimental/apps/lexigram-admin/tests/e2e/test_admin_mfa_http_e2e.py::test_mfa_profile_shows_setup_qr_when_disabled`, `experimental/apps/lexigram-admin/tests/e2e/test_admin_mfa_http_e2e.py::test_mfa_profile_shows_disable_form_when_enabled`, `experimental/apps/lexigram-admin/tests/e2e/test_admin_mfa_http_e2e.py::test_mfa_setup_confirm_redirects_notice`
- Output snippet:

```text
2026-08-21 00:15:56 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
ss..............................FFFFFF................ss................ [  1%]
.............FF......................................................... [  3%]
...............s..................ss.................................... [  4%]
........................................................................ [  6%]
........................................................................ [  7%]
........................................................................ [  9%]
........................................................................ [ 10%]
....................................................
```

### Package tests: experimental/apps/lexigram-cli

- Scope: `experimental/apps/lexigram-cli/tests`
- Command: `uv run pytest experimental/apps/lexigram-cli/tests -q -m not integration --cov=experimental/apps/lexigram.cli`
- Status: **FAIL**
- Exit code: `1`
- Duration: `13534 ms`
- Parsed summary: `6 failed, 845 passed, 1 skipped, 7 deselected, 6 warnings in 11.88s`
- Counters: passed=845, total=852, failed=6, skipped=1, warnings=6, coverage=78.0%
- Example failures: `experimental/apps/lexigram-cli/tests/unit/test_cli_contribution_system.py::TestCommandAssembler::test_definition_command_executes_registry_loaded_adapter`, `experimental/apps/lexigram-cli/tests/unit/test_cli_contribution_system.py::TestCommandAssemblerPackageLayout::test_definition_command_preserves_src_suffix_for_package_layout`, `experimental/apps/lexigram-cli/tests/unit/test_config_validate.py::TestConfigValidate::test_config_validate_success`, `experimental/apps/lexigram-cli/tests/unit/test_config_validate.py::TestConfigValidate::test_config_validate_failure`, `experimental/apps/lexigram-cli/tests/unit/test_db.py::TestDbCommand::test_db_init`
- Output snippet:

```text
2026-08-21 00:16:58 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `6948 ms`
- Parsed summary: `1257 passed, 78 skipped, 8 deselected, 12 warnings in 5.57s`
- Counters: passed=1257, total=1335, failed=0, skipped=78, warnings=12, coverage=73.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:17:11 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2691 ms`
- Parsed summary: `18 passed, 12 deselected, 4 warnings in 1.25s`
- Counters: passed=18, total=18, failed=0, skipped=0, warnings=4, coverage=71.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:17:18 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2162 ms`
- Parsed summary: `54 passed, 4 warnings in 0.77s`
- Counters: passed=54, total=54, failed=0, skipped=0, warnings=4, coverage=92.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:17:21 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `1900 ms`
- Parsed summary: `23 passed, 4 warnings in 0.48s`
- Counters: passed=23, total=23, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:17:23 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Status: **FAIL**
- Exit code: `1`
- Duration: `2391 ms`
- Parsed summary: `3 failed, 43 passed, 4 warnings in 0.98s`
- Counters: passed=43, total=46, failed=3, skipped=0, warnings=4, coverage=86.0%
- Example failures: `experimental/multimedia/lexigram-multimedia-music/tests/unit/providers/test_stability_audio.py::test_generate_sends_bearer_and_multipart_payload`, `experimental/multimedia/lexigram-multimedia-music/tests/unit/providers/test_stability_audio.py::test_generate_omits_extra_fields_when_absent`, `experimental/multimedia/lexigram-multimedia-music/tests/unit/test_config.py::test_music_config_has_no_stability_fields`
- Output snippet:

```text
2026-08-21 00:17:25 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.........................FF............F......                           [100%]
=================================== FAILURES ===================================
_______________ test_generate_sends_bearer_and_multipart_payload _______________

    @pytest.mark.asyncio
    async def test_generate_sends_bearer_and_multipart_payload() -> None:
        provider = StabilityAudioMusicProvider(api_key="sk-test")
    
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read = AsyncMock(return_value=b"audio-bytes")
...
```

### Package tests: experimental/multimedia/lexigram-multimedia-tts

- Scope: `experimental/multimedia/lexigram-multimedia-tts/tests`
- Command: `uv run pytest experimental/multimedia/lexigram-multimedia-tts/tests -q -m not integration --cov=experimental/multimedia/lexigram.multimedia.tts`
- Status: **PASS**
- Exit code: `0`
- Duration: `2388 ms`
- Parsed summary: `63 passed, 4 warnings in 0.89s`
- Counters: passed=63, total=63, failed=0, skipped=0, warnings=4, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:17:27 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2177 ms`
- Parsed summary: `42 passed, 4 warnings in 0.75s`
- Counters: passed=42, total=42, failed=0, skipped=0, warnings=4, coverage=93.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:17:30 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `5530 ms`
- Parsed summary: `182 passed, 4 warnings in 4.13s`
- Counters: passed=182, total=182, failed=0, skipped=0, warnings=4, coverage=86.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:17:32 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4883 ms`
- Parsed summary: `86 passed, 5 warnings in 3.52s`
- Counters: passed=86, total=86, failed=0, skipped=0, warnings=5, coverage=55.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:17:38 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2600 ms`
- Parsed summary: `287 passed, 17 deselected, 4 warnings in 1.26s`
- Counters: passed=287, total=287, failed=0, skipped=0, warnings=4, coverage=85.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:17:42 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `28158 ms`
- Parsed summary: `614 passed, 4 skipped, 2 deselected, 5 warnings in 26.73s`
- Counters: passed=614, total=618, failed=0, skipped=4, warnings=5, coverage=68.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:17:45 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 11%]
...................................................ssss................. [ 23%]
........................................................................ [ 34%]
........................................................................ [ 46%]
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
- Duration: `11267 ms`
- Parsed summary: `867 passed, 13 skipped, 13 deselected, 6 warnings in 9.78s`
- Counters: passed=867, total=880, failed=0, skipped=13, warnings=6, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:18:13 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `12400 ms`
- Parsed summary: `969 passed, 15 skipped, 11 deselected, 6 warnings in 10.80s`
- Counters: passed=969, total=984, failed=0, skipped=15, warnings=6, coverage=63.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:18:24 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `3533 ms`
- Parsed summary: `248 passed, 14 deselected, 17 warnings in 2.27s`
- Counters: passed=248, total=248, failed=0, skipped=0, warnings=17, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:18:37 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2386 ms`
- Parsed summary: `257 passed, 1 skipped, 7 deselected, 4 warnings in 1.14s`
- Counters: passed=257, total=258, failed=0, skipped=1, warnings=4, coverage=79.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:18:40 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `6088 ms`
- Parsed summary: `519 passed, 2 skipped, 11 deselected, 23 warnings in 4.47s`
- Counters: passed=519, total=521, failed=0, skipped=2, warnings=23, coverage=76.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:18:43 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2917 ms`
- Parsed summary: `450 passed, 9 deselected, 4 warnings in 1.63s`
- Counters: passed=450, total=450, failed=0, skipped=0, warnings=4, coverage=77.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:18:49 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 16%]
........................................................................ [ 32%]
........................................................................ [ 48%]
........................................................................ [ 64%]
........................................................................ [ 80%]
........................................................................ [ 96%]
..................                                                       [100%]
=============================== warnings summary ===
```

### Package tests: packages/lexigram-monitor

- Scope: `packages/lexigram-monitor/tests`
- Command: `uv run pytest packages/lexigram-monitor/tests -q -m not integration --cov=packages/lexigram.monitor`
- Status: **PASS**
- Exit code: `0`
- Duration: `8744 ms`
- Parsed summary: `349 passed, 5 skipped, 4 deselected, 4 warnings in 7.38s`
- Counters: passed=349, total=354, failed=0, skipped=5, warnings=4, coverage=82.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:18:52 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 20%]
........................................................................ [ 40%]
....sss.s............................................................... [ 61%]
........................................................................ [ 81%]
..........s.......................................................       [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/py
```

### Package tests: packages/lexigram-nosql

- Scope: `packages/lexigram-nosql/tests`
- Command: `uv run pytest packages/lexigram-nosql/tests -q -m not integration --cov=packages/lexigram.nosql`
- Status: **PASS**
- Exit code: `0`
- Duration: `3737 ms`
- Parsed summary: `536 passed, 10 deselected, 4 warnings in 2.38s`
- Counters: passed=536, total=536, failed=0, skipped=0, warnings=4, coverage=91.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:19:01 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4964 ms`
- Parsed summary: `289 passed, 8 deselected, 4 warnings in 3.55s`
- Counters: passed=289, total=289, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:19:04 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4395 ms`
- Parsed summary: `228 passed, 20 deselected, 4 warnings in 3.13s`
- Counters: passed=228, total=228, failed=0, skipped=0, warnings=4, coverage=84.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:19:09 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 31%]
........................................................................ [ 63%]
........................................................................ [ 94%]
............                                                             [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewriteWarnin
```

### Package tests: packages/lexigram-resilience

- Scope: `packages/lexigram-resilience/tests`
- Command: `uv run pytest packages/lexigram-resilience/tests -q -m not integration --cov=packages/lexigram.resilience`
- Status: **PASS**
- Exit code: `0`
- Duration: `19709 ms`
- Parsed summary: `310 passed, 23 deselected, 4 warnings in 18.46s`
- Counters: passed=310, total=310, failed=0, skipped=0, warnings=4, coverage=74.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:19:14 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4679 ms`
- Parsed summary: `813 passed, 4 skipped, 15 deselected, 4 warnings in 3.25s`
- Counters: passed=813, total=817, failed=0, skipped=4, warnings=4, coverage=65.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:19:33 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `1762 ms`
- Parsed summary: `127 passed, 4 warnings in 0.52s`
- Counters: passed=127, total=127, failed=0, skipped=0, warnings=4, coverage=58.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:19:38 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `15616 ms`
- Parsed summary: `1387 passed, 7 skipped, 9 deselected, 10 warnings in 13.90s`
- Counters: passed=1387, total=1394, failed=0, skipped=7, warnings=10, coverage=63.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:19:40 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................s............................... [  5%]
........................................................................ [ 10%]
........................................................................ [ 15%]
......................................................ss................ [ 20%]
........................................................................ [ 25%]
........................................................................ [ 30%]
........................................................................ [ 36%]
..................................s.................
```

### Package tests: packages/lexigram-storage

- Scope: `packages/lexigram-storage/tests`
- Command: `uv run pytest packages/lexigram-storage/tests -q -m not integration --cov=packages/lexigram.storage`
- Status: **PASS**
- Exit code: `0`
- Duration: `6906 ms`
- Parsed summary: `453 passed, 3 skipped, 22 deselected, 4 warnings in 5.59s`
- Counters: passed=453, total=456, failed=0, skipped=3, warnings=4, coverage=62.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:19:55 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `11759 ms`
- Parsed summary: `525 passed, 15 skipped, 9 deselected, 4 warnings in 10.27s`
- Counters: passed=525, total=540, failed=0, skipped=15, warnings=4, coverage=73.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:20:02 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `3030 ms`
- Parsed summary: `360 passed, 4 deselected, 4 warnings in 1.76s`
- Counters: passed=360, total=360, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:20:14 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `8415 ms`
- Parsed summary: `436 passed, 15 skipped, 13 deselected, 4 warnings in 7.06s`
- Counters: passed=436, total=451, failed=0, skipped=15, warnings=4, coverage=17.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:20:17 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.................s...................................................... [ 15%]
........................................................................ [ 31%]
........................................................................ [ 47%]
........................................................................ [ 63%]
............ssssssssssssss.............................................. [ 79%]
........................................................................ [ 95%]
...................
ERROR: Coverage failure: total of 17 is less than fail-under=80
                                                
```

### Package tests: packages/lexigram-vector

- Scope: `packages/lexigram-vector/tests`
- Command: `uv run pytest packages/lexigram-vector/tests -q -m not integration --cov=packages/lexigram.vector`
- Status: **PASS**
- Exit code: `0`
- Duration: `4620 ms`
- Parsed summary: `546 passed, 20 deselected, 4 warnings in 3.29s`
- Counters: passed=546, total=546, failed=0, skipped=0, warnings=4, coverage=77.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:20:25 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 39%]
........................................................................ [ 52%]
........................................................................ [ 65%]
........................................................................ [ 79%]
........................................................................ [ 92%]
..........................................          
```

### Package tests: packages/lexigram-web

- Scope: `packages/lexigram-web/tests`
- Command: `uv run pytest packages/lexigram-web/tests -q -m not integration --cov=packages/lexigram.web`
- Status: **PASS**
- Exit code: `0`
- Duration: `13431 ms`
- Parsed summary: `1422 passed, 7 skipped, 7 deselected, 6 warnings in 11.86s`
- Counters: passed=1422, total=1429, failed=0, skipped=7, warnings=6, coverage=81.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:20:30 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2880 ms`
- Parsed summary: `334 passed, 4 warnings in 1.57s`
- Counters: passed=334, total=334, failed=0, skipped=0, warnings=4, coverage=86.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:20:44 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `13787 ms`
- Parsed summary: `556 passed, 23 deselected, 4 warnings in 12.52s`
- Counters: passed=556, total=556, failed=0, skipped=0, warnings=4, coverage=70.0%
- Example failures: none
- Output snippet:

```text
2026-08-21 00:20:46 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 12%]
........................................................................ [ 25%]
........................................................................ [ 38%]
........................................................................ [ 51%]
........................................................................ [ 64%]
........................................................................ [ 77%]
........................................................................ [ 90%]
....................................................
```

