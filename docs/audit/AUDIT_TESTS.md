# AUDIT_TESTS.md — Lexigram Framework Targeted Test Execution Audit

> **Source**: Live pytest execution evidence for targeted scopes, with `tests/` directory scanning as supporting context.

---

## Summary

- Total passed tests: 28584
- Total failed tests: 15
- Total skipped tests: 268
- Total warnings: 331
- Aggregate code coverage: 76.32%

- Representative commands run: 54
- Commands passing: 51
- Commands failing: 3
- Packages with tests: 54
- Test files: 3309
- Test functions: 31715

### Exit Codes Reference

- **`0`**: Success — All tests passed and code coverage met the configured threshold.
- **`1`**: Failure — Functional tests failed OR code coverage fell below the package's `--cov-fail-under` threshold.
- **`timeout`**: The test command exceeded the execution time limit (120s) and was automatically terminated.

## Execution Evidence

| Label | Code Coverage | Pass/Total | Failed | Skipped | Warnings | Exit Code | Duration |
|-------|---------------|------------|---------|----------|------|-----------|----------|
| Package tests: core/lexigram-contracts | 32.0% | 1792/1792 | 0 | 0 | 4 | 0 | 10657 ms |
| Package tests: core/lexigram | 0.0% | 0/13 | 12 | 1 | 0 | 2 | 3731 ms |
| Package tests: experimental/ai/lexigram-ai-agents | 85.0% | 402/402 | 0 | 0 | 4 | 0 | 5835 ms |
| Package tests: experimental/ai/lexigram-ai-evaluation | 97.0% | 167/167 | 0 | 0 | 4 | 0 | 1853 ms |
| Package tests: experimental/ai/lexigram-ai-feedback | 96.0% | 260/260 | 0 | 0 | 4 | 0 | 2124 ms |
| Package tests: experimental/ai/lexigram-ai-governance | 88.0% | 544/544 | 0 | 0 | 46 | 0 | 4545 ms |
| Package tests: experimental/ai/lexigram-ai-guard | 87.0% | 242/242 | 0 | 0 | 7 | 0 | 2150 ms |
| Package tests: experimental/ai/lexigram-ai-llm | 71.0% | 949/969 | 0 | 20 | 4 | 0 | 32958 ms |
| Package tests: experimental/ai/lexigram-ai-mcp | 51.0% | 384/384 | 0 | 0 | 4 | 0 | 3474 ms |
| Package tests: experimental/ai/lexigram-ai-memory | 83.0% | 240/240 | 0 | 0 | 4 | 0 | 2397 ms |
| Package tests: experimental/ai/lexigram-ai-observability | 87.0% | 260/260 | 0 | 0 | 4 | 0 | 2589 ms |
| Package tests: experimental/ai/lexigram-ai-prompt | 87.0% | 307/307 | 0 | 0 | 4 | 0 | 2477 ms |
| Package tests: experimental/ai/lexigram-ai-rag | 62.0% | 528/535 | 0 | 7 | 4 | 0 | 6862 ms |
| Package tests: experimental/ai/lexigram-ai-relay-gateway | 94.0% | 579/579 | 0 | 0 | 4 | 0 | 4162 ms |
| Package tests: experimental/ai/lexigram-ai-relay | 91.0% | 534/534 | 0 | 0 | 4 | 0 | 5922 ms |
| Package tests: experimental/ai/lexigram-ai-session | 88.0% | 210/210 | 0 | 0 | 4 | 0 | 2417 ms |
| Package tests: experimental/ai/lexigram-ai-skills | 78.0% | 268/268 | 0 | 0 | 6 | 0 | 2569 ms |
| Package tests: experimental/ai/lexigram-ai-workers | 87.0% | 328/328 | 0 | 0 | 4 | 0 | 3804 ms |
| Package tests: experimental/ai/lexigram-ai | 43.0% | 470/489 | 0 | 19 | 4 | 0 | 17639 ms |
| Package tests: experimental/apps/lexigram-admin | 77.0% | 4721/4733 | 1 | 11 | 18 | 1 | 56505 ms |
| Package tests: experimental/apps/lexigram-cli | 80.0% | 851/852 | 0 | 1 | 6 | 0 | 12575 ms |
| Package tests: experimental/apps/lexigram-ui | 73.0% | 1251/1329 | 0 | 78 | 12 | 0 | 6562 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-beat | 71.0% | 18/18 | 0 | 0 | 4 | 0 | 2529 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-image | 92.0% | 54/54 | 0 | 0 | 4 | 0 | 2066 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-interpolate | 87.0% | 23/23 | 0 | 0 | 4 | 0 | 1854 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-music | 86.0% | 47/47 | 0 | 0 | 4 | 0 | 2033 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-tts | 78.0% | 63/63 | 0 | 0 | 4 | 0 | 2190 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-upscale | 93.0% | 42/42 | 0 | 0 | 4 | 0 | 2089 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-video | 86.0% | 182/182 | 0 | 0 | 4 | 0 | 5477 ms |
| Package tests: experimental/multimedia/lexigram-multimedia | 55.0% | 86/86 | 0 | 0 | 5 | 0 | 4868 ms |
| Package tests: packages/lexigram-audit | 85.0% | 287/287 | 0 | 0 | 4 | 0 | 2410 ms |
| Package tests: packages/lexigram-auth | 68.0% | 614/618 | 0 | 4 | 5 | 0 | 27738 ms |
| Package tests: packages/lexigram-cache | 80.0% | 867/880 | 0 | 13 | 6 | 0 | 10893 ms |
| Package tests: packages/lexigram-events | 63.0% | 969/984 | 0 | 15 | 6 | 0 | 12060 ms |
| Package tests: packages/lexigram-features | 80.0% | 248/248 | 0 | 0 | 17 | 0 | 3378 ms |
| Package tests: packages/lexigram-graph | 79.0% | 257/258 | 0 | 1 | 4 | 0 | 2223 ms |
| Package tests: packages/lexigram-graphql | 76.0% | 519/521 | 0 | 2 | 23 | 0 | 5909 ms |
| Package tests: packages/lexigram-http | 78.0% | 456/456 | 0 | 0 | 8 | 0 | 2791 ms |
| Package tests: packages/lexigram-monitor | 82.0% | 349/356 | 2 | 5 | 4 | 1 | 8762 ms |
| Package tests: packages/lexigram-nosql | 91.0% | 536/536 | 0 | 0 | 4 | 0 | 3547 ms |
| Package tests: packages/lexigram-notification | 84.0% | 289/289 | 0 | 0 | 4 | 0 | 4337 ms |
| Package tests: packages/lexigram-queue | 84.0% | 231/231 | 0 | 0 | 4 | 0 | 4334 ms |
| Package tests: packages/lexigram-resilience | 74.0% | 310/310 | 0 | 0 | 4 | 0 | 20385 ms |
| Package tests: packages/lexigram-search | 66.0% | 813/817 | 0 | 4 | 4 | 0 | 4337 ms |
| Package tests: packages/lexigram-secrets | 58.0% | 127/127 | 0 | 0 | 4 | 0 | 1665 ms |
| Package tests: packages/lexigram-sql | 62.0% | 1347/1394 | 0 | 47 | 10 | 0 | 11602 ms |
| Package tests: packages/lexigram-storage | 62.0% | 453/456 | 0 | 3 | 4 | 0 | 6690 ms |
| Package tests: packages/lexigram-tasks | 74.0% | 525/540 | 0 | 15 | 4 | 0 | 11276 ms |
| Package tests: packages/lexigram-tenancy | 83.0% | 360/360 | 0 | 0 | 4 | 0 | 2912 ms |
| Package tests: packages/lexigram-testing | 17.0% | 438/453 | 0 | 15 | 2 | 0 | 7892 ms |
| Package tests: packages/lexigram-vector | 77.0% | 525/525 | 0 | 0 | 4 | 0 | 3992 ms |
| Package tests: packages/lexigram-web | 81.0% | 1372/1379 | 0 | 7 | 6 | 0 | 12833 ms |
| Package tests: packages/lexigram-webhook | 86.0% | 334/334 | 0 | 0 | 4 | 0 | 2763 ms |
| Package tests: packages/lexigram-workflow | 70.0% | 556/556 | 0 | 0 | 4 | 0 | 13656 ms |

### Execution Scope Notes

- `framework-core`: real test execution for `lexigram/tests`.
- `package`: real test execution for `<package>/tests` across every discovered Lexigram package with tests.
### Package tests: core/lexigram-contracts

- Scope: `core/lexigram-contracts/tests`
- Command: `uv run pytest core/lexigram-contracts/tests -q -m not integration --cov=core/lexigram.contracts`
- Status: **PASS**
- Exit code: `0`
- Duration: `10657 ms`
- Parsed summary: `1792 passed, 4 warnings in 9.31s`
- Counters: passed=1792, total=1792, failed=0, skipped=0, warnings=4, coverage=32.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:19:52 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Exit code: `2`
- Duration: `3731 ms`
- Parsed summary: `1 skipped, 19 deselected, 6 errors in 2.32s`
- Counters: passed=0, total=13, failed=12, skipped=1, warnings=0, coverage=0.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:20:02 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0

==================================== ERRORS ====================================
_______ ERROR collecting tests/integration/di/module/test_boot_level.py ________
ImportError while importing test module 'core/lexigram/tests/integration/di/module/test_boot_level.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/home/admin/.local/share/uv/python/cpython-3.13.7-linux-x86_64-gnu/lib/python3.13/importlib/__init__.py:88: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^
```

### Package tests: experimental/ai/lexigram-ai-agents

- Scope: `experimental/ai/lexigram-ai-agents/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-agents/tests -q -m not integration --cov=experimental/ai/lexigram.ai.agents`
- Status: **PASS**
- Exit code: `0`
- Duration: `5835 ms`
- Parsed summary: `402 passed, 10 deselected, 4 warnings in 4.57s`
- Counters: passed=402, total=402, failed=0, skipped=0, warnings=4, coverage=85.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:20:06 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `1853 ms`
- Parsed summary: `167 passed, 4 warnings in 0.70s`
- Counters: passed=167, total=167, failed=0, skipped=0, warnings=4, coverage=97.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:20:12 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2124 ms`
- Parsed summary: `260 passed, 4 warnings in 0.96s`
- Counters: passed=260, total=260, failed=0, skipped=0, warnings=4, coverage=96.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:20:14 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4545 ms`
- Parsed summary: `544 passed, 7 deselected, 46 warnings in 3.32s`
- Counters: passed=544, total=544, failed=0, skipped=0, warnings=46, coverage=88.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:20:16 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2150 ms`
- Parsed summary: `242 passed, 17 deselected, 7 warnings in 0.98s`
- Counters: passed=242, total=242, failed=0, skipped=0, warnings=7, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:20:20 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `32958 ms`
- Parsed summary: `949 passed, 20 skipped, 19 deselected, 4 warnings in 31.21s`
- Counters: passed=949, total=969, failed=0, skipped=20, warnings=4, coverage=71.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:20:23 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `3474 ms`
- Parsed summary: `384 passed, 13 deselected, 4 warnings in 2.21s`
- Counters: passed=384, total=384, failed=0, skipped=0, warnings=4, coverage=51.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:20:56 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2397 ms`
- Parsed summary: `240 passed, 16 deselected, 4 warnings in 1.20s`
- Counters: passed=240, total=240, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:20:59 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2589 ms`
- Parsed summary: `260 passed, 10 deselected, 4 warnings in 1.39s`
- Counters: passed=260, total=260, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:21:01 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2477 ms`
- Parsed summary: `307 passed, 4 warnings in 1.24s`
- Counters: passed=307, total=307, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:21:04 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `6862 ms`
- Parsed summary: `528 passed, 7 skipped, 8 deselected, 4 warnings in 5.56s`
- Counters: passed=528, total=535, failed=0, skipped=7, warnings=4, coverage=62.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:21:07 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4162 ms`
- Parsed summary: `579 passed, 4 warnings in 2.88s`
- Counters: passed=579, total=579, failed=0, skipped=0, warnings=4, coverage=94.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:21:13 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `5922 ms`
- Parsed summary: `534 passed, 4 warnings in 4.68s`
- Counters: passed=534, total=534, failed=0, skipped=0, warnings=4, coverage=91.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:21:18 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
2026-08-25 07:21:18 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=RelayModule providers=0
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
- Duration: `2417 ms`
- Parsed summary: `210 passed, 4 warnings in 1.21s`
- Counters: passed=210, total=210, failed=0, skipped=0, warnings=4, coverage=88.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:21:24 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2569 ms`
- Parsed summary: `268 passed, 6 warnings in 1.36s`
- Counters: passed=268, total=268, failed=0, skipped=0, warnings=6, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:21:26 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `3804 ms`
- Parsed summary: `328 passed, 7 deselected, 4 warnings in 2.61s`
- Counters: passed=328, total=328, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:21:28 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Status: **PASS**
- Exit code: `0`
- Duration: `17639 ms`
- Parsed summary: `470 passed, 19 skipped, 15 deselected, 4 warnings in 16.06s`
- Counters: passed=470, total=489, failed=0, skipped=19, warnings=4, coverage=43.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:21:32 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 15%]
........................................................................ [ 30%]
..................................................................ss.... [ 45%]
................................s....................................... [ 60%]
..........................................................s.s........... [ 75%]
........................................................................ [ 90%]
...........................................                              [100%]
=============================== warnings summary ===
```

### Package tests: experimental/apps/lexigram-admin

- Scope: `experimental/apps/lexigram-admin/tests`
- Command: `uv run pytest experimental/apps/lexigram-admin/tests -q -m not integration --cov=experimental/apps/lexigram.admin`
- Status: **FAIL**
- Exit code: `1`
- Duration: `56505 ms`
- Parsed summary: `1 failed, 4721 passed, 11 skipped, 29 deselected, 18 warnings in 54.29s`
- Counters: passed=4721, total=4733, failed=1, skipped=11, warnings=18, coverage=77.0%
- Example failures: `experimental/apps/lexigram-admin/tests/e2e/test_admin_auth_open_redirect_e2e.py::test_open_redirect_mfa_sink_keeps_legitimate_pending_next`
- Output snippet:

```text
2026-08-25 07:21:50 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
ss...............F....................................ss................ [  1%]
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
- Duration: `12575 ms`
- Parsed summary: `851 passed, 1 skipped, 7 deselected, 6 warnings in 10.98s`
- Counters: passed=851, total=852, failed=0, skipped=1, warnings=6, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:22:46 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `6562 ms`
- Parsed summary: `1251 passed, 78 skipped, 8 deselected, 12 warnings in 5.26s`
- Counters: passed=1251, total=1329, failed=0, skipped=78, warnings=12, coverage=73.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:22:59 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2529 ms`
- Parsed summary: `18 passed, 12 deselected, 4 warnings in 1.15s`
- Counters: passed=18, total=18, failed=0, skipped=0, warnings=4, coverage=71.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:23:06 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2066 ms`
- Parsed summary: `54 passed, 4 warnings in 0.75s`
- Counters: passed=54, total=54, failed=0, skipped=0, warnings=4, coverage=92.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:23:08 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `1854 ms`
- Parsed summary: `23 passed, 4 warnings in 0.49s`
- Counters: passed=23, total=23, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:23:10 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2033 ms`
- Parsed summary: `47 passed, 4 warnings in 0.68s`
- Counters: passed=47, total=47, failed=0, skipped=0, warnings=4, coverage=86.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:23:12 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2190 ms`
- Parsed summary: `63 passed, 4 warnings in 0.84s`
- Counters: passed=63, total=63, failed=0, skipped=0, warnings=4, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:23:14 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2089 ms`
- Parsed summary: `42 passed, 4 warnings in 0.70s`
- Counters: passed=42, total=42, failed=0, skipped=0, warnings=4, coverage=93.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:23:16 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `5477 ms`
- Parsed summary: `182 passed, 4 warnings in 4.09s`
- Counters: passed=182, total=182, failed=0, skipped=0, warnings=4, coverage=86.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:23:18 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4868 ms`
- Parsed summary: `86 passed, 5 warnings in 3.52s`
- Counters: passed=86, total=86, failed=0, skipped=0, warnings=5, coverage=55.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:23:24 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2410 ms`
- Parsed summary: `287 passed, 17 deselected, 4 warnings in 1.18s`
- Counters: passed=287, total=287, failed=0, skipped=0, warnings=4, coverage=85.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:23:29 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `27738 ms`
- Parsed summary: `614 passed, 4 skipped, 2 deselected, 5 warnings in 26.44s`
- Counters: passed=614, total=618, failed=0, skipped=4, warnings=5, coverage=68.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:23:31 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `10893 ms`
- Parsed summary: `867 passed, 13 skipped, 13 deselected, 6 warnings in 9.48s`
- Counters: passed=867, total=880, failed=0, skipped=13, warnings=6, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:23:59 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Status: **PASS**
- Exit code: `0`
- Duration: `12060 ms`
- Parsed summary: `969 passed, 15 skipped, 11 deselected, 6 warnings in 10.48s`
- Counters: passed=969, total=984, failed=0, skipped=15, warnings=6, coverage=63.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:24:10 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `3378 ms`
- Parsed summary: `248 passed, 14 deselected, 17 warnings in 2.20s`
- Counters: passed=248, total=248, failed=0, skipped=0, warnings=17, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:24:22 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 29%]
........................................................................ [ 58%]
........................................................................ [ 87%]
................................                                         [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewr
```

### Package tests: packages/lexigram-graph

- Scope: `packages/lexigram-graph/tests`
- Command: `uv run pytest packages/lexigram-graph/tests -q -m not integration --cov=packages/lexigram.graph`
- Status: **PASS**
- Exit code: `0`
- Duration: `2223 ms`
- Parsed summary: `257 passed, 1 skipped, 7 deselected, 4 warnings in 1.06s`
- Counters: passed=257, total=258, failed=0, skipped=1, warnings=4, coverage=79.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:24:25 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `5909 ms`
- Parsed summary: `519 passed, 2 skipped, 11 deselected, 23 warnings in 4.39s`
- Counters: passed=519, total=521, failed=0, skipped=2, warnings=23, coverage=76.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:24:27 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2791 ms`
- Parsed summary: `456 passed, 9 deselected, 8 warnings in 1.53s`
- Counters: passed=456, total=456, failed=0, skipped=0, warnings=8, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:24:33 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Status: **FAIL**
- Exit code: `1`
- Duration: `8762 ms`
- Parsed summary: `2 failed, 349 passed, 5 skipped, 4 deselected, 4 warnings in 7.46s`
- Counters: passed=349, total=356, failed=2, skipped=5, warnings=4, coverage=82.0%
- Example failures: `packages/lexigram-monitor/tests/unit/test_channel_dispatchers.py::TestSlackBusinessHoursDispatcher::test_queues_outside_business_hours`, `packages/lexigram-monitor/tests/unit/test_channel_dispatchers.py::TestSlackBusinessHoursDispatcher::test_flush_queue_sends_queued`
- Output snippet:

```text
2026-08-25 07:24:36 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.......................FF............................................... [ 20%]
........................................................................ [ 40%]
......sss.s............................................................. [ 60%]
........................................................................ [ 80%]
............s.......................................................     [100%]
=================================== FAILURES ===================================
_____ TestSlackBusinessHoursDispatcher.test_queues_outside_business_hours ______

self = <AsyncMock name='mock.request' id='1247018
```

### Package tests: packages/lexigram-nosql

- Scope: `packages/lexigram-nosql/tests`
- Command: `uv run pytest packages/lexigram-nosql/tests -q -m not integration --cov=packages/lexigram.nosql`
- Status: **PASS**
- Exit code: `0`
- Duration: `3547 ms`
- Parsed summary: `536 passed, 10 deselected, 4 warnings in 2.27s`
- Counters: passed=536, total=536, failed=0, skipped=0, warnings=4, coverage=91.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:24:45 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4337 ms`
- Parsed summary: `289 passed, 8 deselected, 4 warnings in 3.01s`
- Counters: passed=289, total=289, failed=0, skipped=0, warnings=4, coverage=84.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:24:48 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 24%]
........................................................................ [ 49%]
........................................................................ [ 74%]
........................................................................ [ 99%]
.                                                                        [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .ve
```

### Package tests: packages/lexigram-queue

- Scope: `packages/lexigram-queue/tests`
- Command: `uv run pytest packages/lexigram-queue/tests -q -m not integration --cov=packages/lexigram.queue`
- Status: **PASS**
- Exit code: `0`
- Duration: `4334 ms`
- Parsed summary: `231 passed, 20 deselected, 4 warnings in 3.12s`
- Counters: passed=231, total=231, failed=0, skipped=0, warnings=4, coverage=84.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:24:53 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 31%]
........................................................................ [ 62%]
........................................................................ [ 93%]
...............                                                          [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewr
```

### Package tests: packages/lexigram-resilience

- Scope: `packages/lexigram-resilience/tests`
- Command: `uv run pytest packages/lexigram-resilience/tests -q -m not integration --cov=packages/lexigram.resilience`
- Status: **PASS**
- Exit code: `0`
- Duration: `20385 ms`
- Parsed summary: `310 passed, 23 deselected, 4 warnings in 19.20s`
- Counters: passed=310, total=310, failed=0, skipped=0, warnings=4, coverage=74.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:24:57 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 23%]
........................................................................ [ 46%]
........................................................................ [ 69%]
........................................................................ [ 92%]
......................                                                   [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .ve
```

### Package tests: packages/lexigram-search

- Scope: `packages/lexigram-search/tests`
- Command: `uv run pytest packages/lexigram-search/tests -q -m not integration --cov=packages/lexigram.search`
- Status: **PASS**
- Exit code: `0`
- Duration: `4337 ms`
- Parsed summary: `813 passed, 4 skipped, 15 deselected, 4 warnings in 3.03s`
- Counters: passed=813, total=817, failed=0, skipped=4, warnings=4, coverage=66.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:25:17 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `1665 ms`
- Parsed summary: `127 passed, 4 warnings in 0.48s`
- Counters: passed=127, total=127, failed=0, skipped=0, warnings=4, coverage=58.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:25:22 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Status: **PASS**
- Exit code: `0`
- Duration: `11602 ms`
- Parsed summary: `1347 passed, 47 skipped, 9 deselected, 10 warnings in 9.97s`
- Counters: passed=1347, total=1394, failed=0, skipped=47, warnings=10, coverage=62.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:25:23 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `6690 ms`
- Parsed summary: `453 passed, 3 skipped, 22 deselected, 4 warnings in 5.45s`
- Counters: passed=453, total=456, failed=0, skipped=3, warnings=4, coverage=62.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:25:35 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Status: **PASS**
- Exit code: `0`
- Duration: `11276 ms`
- Parsed summary: `525 passed, 15 skipped, 9 deselected, 4 warnings in 9.92s`
- Counters: passed=525, total=540, failed=0, skipped=15, warnings=4, coverage=74.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:25:42 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 40%]
...sssss................................................................ [ 53%]
..........................................sssssssss..................... [ 66%]
........................................................................ [ 80%]
...............................s........................................ [ 93%]
....................................                
```

### Package tests: packages/lexigram-tenancy

- Scope: `packages/lexigram-tenancy/tests`
- Command: `uv run pytest packages/lexigram-tenancy/tests -q -m not integration --cov=packages/lexigram.tenancy`
- Status: **PASS**
- Exit code: `0`
- Duration: `2912 ms`
- Parsed summary: `360 passed, 4 deselected, 4 warnings in 1.67s`
- Counters: passed=360, total=360, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:25:53 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 20%]
........................................................................ [ 40%]
........................................................................ [ 60%]
........................................................................ [ 80%]
........................................................................ [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .ve
```

### Package tests: packages/lexigram-testing

- Scope: `packages/lexigram-testing/tests`
- Command: `uv run pytest packages/lexigram-testing/tests -q -m not integration --cov=packages/lexigram.testing`
- Status: **PASS**
- Exit code: `0`
- Duration: `7892 ms`
- Parsed summary: `438 passed, 15 skipped, 13 deselected, 2 warnings in 6.59s`
- Counters: passed=438, total=453, failed=0, skipped=15, warnings=2, coverage=17.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:25:56 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.................s...................................................... [ 15%]
........................................................................ [ 31%]
........................................................................ [ 47%]
........................................................................ [ 63%]
............ssssssssssssss.............................................. [ 79%]
........................................................................ [ 95%]
.....................                                                    [100%]
=============================== warnings summary ===
```

### Package tests: packages/lexigram-vector

- Scope: `packages/lexigram-vector/tests`
- Command: `uv run pytest packages/lexigram-vector/tests -q -m not integration --cov=packages/lexigram.vector`
- Status: **PASS**
- Exit code: `0`
- Duration: `3992 ms`
- Parsed summary: `525 passed, 20 deselected, 4 warnings in 2.73s`
- Counters: passed=525, total=525, failed=0, skipped=0, warnings=4, coverage=77.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:26:04 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `12833 ms`
- Parsed summary: `1372 passed, 7 skipped, 7 deselected, 6 warnings in 11.33s`
- Counters: passed=1372, total=1379, failed=0, skipped=7, warnings=6, coverage=81.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:26:08 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
sss..................................................................... [  5%]
........................................................................ [ 10%]
........................................................................ [ 15%]
....................................................s................... [ 20%]
........................................................................ [ 26%]
........................................................................ [ 31%]
.................s...................................................... [ 36%]
....................................................
```

### Package tests: packages/lexigram-webhook

- Scope: `packages/lexigram-webhook/tests`
- Command: `uv run pytest packages/lexigram-webhook/tests -q -m not integration --cov=packages/lexigram.webhook`
- Status: **PASS**
- Exit code: `0`
- Duration: `2763 ms`
- Parsed summary: `334 passed, 4 warnings in 1.50s`
- Counters: passed=334, total=334, failed=0, skipped=0, warnings=4, coverage=86.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:26:21 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 21%]
........................................................................ [ 43%]
........................................................................ [ 64%]
........................................................................ [ 86%]
..............................................                           [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .ve
```

### Package tests: packages/lexigram-workflow

- Scope: `packages/lexigram-workflow/tests`
- Command: `uv run pytest packages/lexigram-workflow/tests -q -m not integration --cov=packages/lexigram.workflow`
- Status: **PASS**
- Exit code: `0`
- Duration: `13656 ms`
- Parsed summary: `556 passed, 23 deselected, 4 warnings in 12.43s`
- Counters: passed=556, total=556, failed=0, skipped=0, warnings=4, coverage=70.0%
- Example failures: none
- Output snippet:

```text
2026-08-25 07:26:23 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 12%]
........................................................................ [ 25%]
........................................................................ [ 38%]
........................................................................ [ 51%]
........................................................................ [ 64%]
........................................................................ [ 77%]
........................................................................ [ 90%]
....................................................
```

