# AUDIT_TESTS.md — Lexigram Framework Targeted Test Execution Audit

> **Source**: Live pytest execution evidence for targeted scopes, with `tests/` directory scanning as supporting context.

---

## Summary

- Total passed tests: 28016
- Total failed tests: 0
- Total skipped tests: 268
- Total warnings: 274
- Aggregate code coverage: 73.00%

- Representative commands run: 54
- Commands passing: 43
- Commands failing: 11
- Packages with tests: 54
- Test files: 2715
- Test functions: 28498

### Exit Codes Reference

- **`0`**: Success — All tests passed and code coverage met the configured threshold.
- **`1`**: Failure — Functional tests failed OR code coverage fell below the package's `--cov-fail-under` threshold.
- **`timeout`**: The test command exceeded the execution time limit (120s) and was automatically terminated.

## Execution Evidence

| Label | Code Coverage | Pass/Total | Failed | Skipped | Warnings | Exit Code | Duration |
|-------|---------------|------------|---------|----------|------|-----------|----------|
| Lexigram framework core tests | 57.0% | 2884/2889 | 0 | 5 | 1 | 1 | 27699 ms |
| Package tests: lexigram-contracts | 33.0% | 1679/1679 | 0 | 0 | 5 | 1 | 11214 ms |
| Package tests: lexigram-admin | 67.0% | 3552/3594 | 0 | 42 | 14 | 0 | 62569 ms |
| Package tests: lexigram-ai-agents | 84.0% | 379/379 | 0 | 0 | 4 | 0 | 6351 ms |
| Package tests: lexigram-ai-evaluation | 99.0% | 136/136 | 0 | 0 | 4 | 0 | 2096 ms |
| Package tests: lexigram-ai-feedback | 94.0% | 237/237 | 0 | 0 | 4 | 0 | 2447 ms |
| Package tests: lexigram-ai-governance | 86.0% | 457/457 | 0 | 0 | 16 | 0 | 4221 ms |
| Package tests: lexigram-ai-guard | 78.0% | 224/224 | 0 | 0 | 7 | 0 | 2433 ms |
| Package tests: lexigram-ai-llm | 71.0% | 925/945 | 0 | 20 | 4 | 0 | 33521 ms |
| Package tests: lexigram-ai-mcp | 48.0% | 359/359 | 0 | 0 | 4 | 0 | 3827 ms |
| Package tests: lexigram-ai-memory | 76.0% | 222/222 | 0 | 0 | 4 | 0 | 2721 ms |
| Package tests: lexigram-ai-observability | 86.0% | 232/232 | 0 | 0 | 4 | 0 | 2886 ms |
| Package tests: lexigram-ai-prompt | 87.0% | 297/297 | 0 | 0 | 4 | 0 | 2849 ms |
| Package tests: lexigram-ai-rag | 62.0% | 521/528 | 0 | 7 | 4 | 0 | 7967 ms |
| Package tests: lexigram-ai-relay-gateway | 95.0% | 414/414 | 0 | 0 | 4 | 0 | 3897 ms |
| Package tests: lexigram-ai-relay | 91.0% | 539/539 | 0 | 0 | 4 | 0 | 6778 ms |
| Package tests: lexigram-ai-session | 90.0% | 207/207 | 0 | 0 | 4 | 0 | 2697 ms |
| Package tests: lexigram-ai-skills | 78.0% | 263/263 | 0 | 0 | 6 | 0 | 2926 ms |
| Package tests: lexigram-ai-workers | 87.0% | 318/318 | 0 | 0 | 4 | 0 | 4262 ms |
| Package tests: lexigram-ai | 42.0% | 442/453 | 0 | 11 | 4 | 1 | 19408 ms |
| Package tests: lexigram-audit | 72.0% | 242/242 | 0 | 0 | 4 | 1 | 2630 ms |
| Package tests: lexigram-auth | 64.0% | 553/557 | 0 | 4 | 6 | 1 | 21632 ms |
| Package tests: lexigram-cache | 69.0% | 741/754 | 0 | 13 | 6 | 1 | 10958 ms |
| Package tests: lexigram-cli | 80.0% | 846/847 | 0 | 1 | 6 | 0 | 11777 ms |
| Package tests: lexigram-events | 61.0% | 913/928 | 0 | 15 | 5 | 1 | 12452 ms |
| Package tests: lexigram-features | 80.0% | 245/245 | 0 | 0 | 17 | 0 | 3761 ms |
| Package tests: lexigram-graph | 73.0% | 252/253 | 0 | 1 | 4 | 0 | 2538 ms |
| Package tests: lexigram-graphql | 72.0% | 502/506 | 0 | 4 | 4 | 0 | 5833 ms |
| Package tests: lexigram-http | 73.0% | 433/433 | 0 | 0 | 4 | 0 | 2890 ms |
| Package tests: lexigram-monitor | 80.0% | 303/308 | 0 | 5 | 4 | 0 | 8938 ms |
| Package tests: lexigram-multimedia-beat | 69.0% | 12/12 | 0 | 0 | 4 | 0 | 2284 ms |
| Package tests: lexigram-multimedia-image | 92.0% | 53/53 | 0 | 0 | 4 | 0 | 2493 ms |
| Package tests: lexigram-multimedia-interpolate | 84.0% | 23/23 | 0 | 0 | 4 | 0 | 2153 ms |
| Package tests: lexigram-multimedia-music | 79.0% | 37/37 | 0 | 0 | 4 | 0 | 2244 ms |
| Package tests: lexigram-multimedia-tts | 70.0% | 53/53 | 0 | 0 | 4 | 0 | 2388 ms |
| Package tests: lexigram-multimedia-upscale | 78.0% | 26/26 | 0 | 0 | 4 | 0 | 2205 ms |
| Package tests: lexigram-multimedia-video | 84.0% | 139/139 | 0 | 0 | 4 | 0 | 5428 ms |
| Package tests: lexigram-multimedia | 56.0% | 81/81 | 0 | 0 | 5 | 0 | 5289 ms |
| Package tests: lexigram-nosql | 91.0% | 414/414 | 0 | 0 | 4 | 0 | 3437 ms |
| Package tests: lexigram-notification | 83.0% | 239/239 | 0 | 0 | 4 | 0 | 4531 ms |
| Package tests: lexigram-queue | 82.0% | 201/201 | 0 | 0 | 4 | 0 | 4154 ms |
| Package tests: lexigram-resilience | 71.0% | 297/297 | 0 | 0 | 4 | 0 | 21390 ms |
| Package tests: lexigram-search | 60.0% | 640/644 | 0 | 4 | 4 | 0 | 4266 ms |
| Package tests: lexigram-secrets | 39.0% | 85/85 | 0 | 0 | 4 | 1 | 1874 ms |
| Package tests: lexigram-sql (unit only, no external DB) | 55.0% | 1086/1176 | 0 | 90 | 6 | 1 | 11348 ms |
| Package tests: lexigram-storage | 62.0% | 440/443 | 0 | 3 | 4 | 0 | 7028 ms |
| Package tests: lexigram-tasks | 65.0% | 410/431 | 0 | 21 | 4 | 1 | 9272 ms |
| Package tests: lexigram-tenancy | 83.0% | 345/345 | 0 | 0 | 4 | 0 | 3324 ms |
| Package tests: lexigram-testing | 17.0% | 436/451 | 0 | 15 | 4 | 1 | 7705 ms |
| Package tests: lexigram-ui | 74.0% | 960/960 | 0 | 0 | 12 | 0 | 5804 ms |
| Package tests: lexigram-vector | 76.0% | 498/498 | 0 | 0 | 4 | 0 | 4783 ms |
| Package tests: lexigram-web | 80.0% | 1344/1351 | 0 | 7 | 6 | 0 | 12906 ms |
| Package tests: lexigram-webhook | 86.0% | 327/327 | 0 | 0 | 4 | 0 | 2764 ms |
| Package tests: lexigram-workflow | 71.0% | 553/553 | 0 | 0 | 4 | 0 | 14267 ms |

### Execution Scope Notes

- `framework-core`: real test execution for `lexigram/tests`.
- `package`: real test execution for `<package>/tests` across every discovered Lexigram package with tests.
### Lexigram framework core tests

- Scope: `lexigram/tests`
- Command: `uv run pytest lexigram/tests -q -m not integration --cov=lexigram`
- Status: **FAIL**
- Exit code: `1`
- Duration: `27699 ms`
- Parsed summary: `2884 passed, 5 skipped, 19 deselected, 1 warning in 24.55s`
- Counters: passed=2884, total=2889, failed=0, skipped=5, warnings=1, coverage=57.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:42:59 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `11214 ms`
- Parsed summary: `1679 passed, 5 warnings in 9.49s`
- Counters: passed=1679, total=1679, failed=0, skipped=0, warnings=5, coverage=33.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:43:27 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  4%]
........................................................................ [  8%]
........................................................................ [ 12%]
........................................................................ [ 17%]
........................................................................ [ 21%]
........................................................................ [ 25%]
........................................................................ [ 30%]
....................................................
```

### Package tests: lexigram-admin

- Scope: `lexigram-admin/tests`
- Command: `uv run pytest lexigram-admin/tests -q -m not integration --cov=lexigram.admin`
- Status: **PASS**
- Exit code: `0`
- Duration: `62569 ms`
- Parsed summary: `3552 passed, 42 skipped, 25 deselected, 14 warnings in 59.85s`
- Counters: passed=3552, total=3594, failed=0, skipped=42, warnings=14, coverage=67.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:43:38 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
ss....ss................................................................ [  2%]
............................s...............................ss.......... [  4%]
........................................................................ [  6%]
........................................................................ [  8%]
........................................................................ [ 10%]
........................................................................ [ 12%]
........................................................................ [ 14%]
....................................................
```

### Package tests: lexigram-ai-agents

- Scope: `lexigram-ai-agents/tests`
- Command: `uv run pytest lexigram-ai-agents/tests -q -m not integration --cov=lexigram.ai.agents`
- Status: **PASS**
- Exit code: `0`
- Duration: `6351 ms`
- Parsed summary: `379 passed, 10 deselected, 4 warnings in 4.72s`
- Counters: passed=379, total=379, failed=0, skipped=0, warnings=4, coverage=84.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:44:41 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 18%]
........................................................................ [ 37%]
........................................................................ [ 56%]
........................................................................ [ 75%]
........................................................................ [ 94%]
...................                                                      [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/_
```

### Package tests: lexigram-ai-evaluation

- Scope: `lexigram-ai-evaluation/tests`
- Command: `uv run pytest lexigram-ai-evaluation/tests -q -m not integration --cov=lexigram.ai.evaluation`
- Status: **PASS**
- Exit code: `0`
- Duration: `2096 ms`
- Parsed summary: `136 passed, 4 warnings in 0.60s`
- Counters: passed=136, total=136, failed=0, skipped=0, warnings=4, coverage=99.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:44:47 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2447 ms`
- Parsed summary: `237 passed, 4 warnings in 0.89s`
- Counters: passed=237, total=237, failed=0, skipped=0, warnings=4, coverage=94.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:44:49 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4221 ms`
- Parsed summary: `457 passed, 7 deselected, 16 warnings in 2.61s`
- Counters: passed=457, total=457, failed=0, skipped=0, warnings=16, coverage=86.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:44:52 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 15%]
........................................................................ [ 31%]
........................................................................ [ 47%]
........................................................................ [ 63%]
........................................................................ [ 78%]
........................................................................ [ 94%]
.........................                                                [100%]
=============================== warnings summary ===
```

### Package tests: lexigram-ai-guard

- Scope: `lexigram-ai-guard/tests`
- Command: `uv run pytest lexigram-ai-guard/tests -q -m not integration --cov=lexigram.ai.guard`
- Status: **PASS**
- Exit code: `0`
- Duration: `2433 ms`
- Parsed summary: `224 passed, 17 deselected, 7 warnings in 0.96s`
- Counters: passed=224, total=224, failed=0, skipped=0, warnings=7, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:44:56 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 32%]
........................................................................ [ 64%]
........................................................................ [ 96%]
........                                                                 [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-ai-llm

- Scope: `lexigram-ai-llm/tests`
- Command: `uv run pytest lexigram-ai-llm/tests -q -m not integration --cov=lexigram.ai.llm`
- Status: **PASS**
- Exit code: `0`
- Duration: `33521 ms`
- Parsed summary: `925 passed, 20 skipped, 19 deselected, 4 warnings in 31.37s`
- Counters: passed=925, total=945, failed=0, skipped=20, warnings=4, coverage=71.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:44:58 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
ssssssssssssssss........................................................ [  7%]
........................................................................ [ 15%]
........................................................................ [ 22%]
..........................................ssss.......................... [ 30%]
........................................................................ [ 38%]
........................................................................ [ 45%]
........................................................................ [ 53%]
....................................................
```

### Package tests: lexigram-ai-mcp

- Scope: `lexigram-ai-mcp/tests`
- Command: `uv run pytest lexigram-ai-mcp/tests -q -m not integration --cov=lexigram.ai.mcp`
- Status: **PASS**
- Exit code: `0`
- Duration: `3827 ms`
- Parsed summary: `359 passed, 13 deselected, 4 warnings in 2.29s`
- Counters: passed=359, total=359, failed=0, skipped=0, warnings=4, coverage=48.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:45:32 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 20%]
........................................................................ [ 40%]
........................................................................ [ 60%]
........................................................................ [ 80%]
.......................................................................  [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/
```

### Package tests: lexigram-ai-memory

- Scope: `lexigram-ai-memory/tests`
- Command: `uv run pytest lexigram-ai-memory/tests -q -m not integration --cov=lexigram.ai.memory`
- Status: **PASS**
- Exit code: `0`
- Duration: `2721 ms`
- Parsed summary: `222 passed, 16 deselected, 4 warnings in 1.24s`
- Counters: passed=222, total=222, failed=0, skipped=0, warnings=4, coverage=76.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:45:36 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 32%]
........................................................................ [ 64%]
........................................................................ [ 97%]
......                                                                   [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-ai-observability

- Scope: `lexigram-ai-observability/tests`
- Command: `uv run pytest lexigram-ai-observability/tests -q -m not integration --cov=lexigram.ai.observability`
- Status: **PASS**
- Exit code: `0`
- Duration: `2886 ms`
- Parsed summary: `232 passed, 10 deselected, 4 warnings in 1.38s`
- Counters: passed=232, total=232, failed=0, skipped=0, warnings=4, coverage=86.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:45:38 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2849 ms`
- Parsed summary: `297 passed, 4 warnings in 1.34s`
- Counters: passed=297, total=297, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:45:41 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `7967 ms`
- Parsed summary: `521 passed, 7 skipped, 8 deselected, 4 warnings in 6.24s`
- Counters: passed=521, total=528, failed=0, skipped=7, warnings=4, coverage=62.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:45:44 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
...........................................................sss.......... [ 13%]
.s..............ss...................................................... [ 27%]
.........................................................s.............. [ 40%]
........................................................................ [ 54%]
........................................................................ [ 68%]
........................................................................ [ 81%]
........................................................................ [ 95%]
........................                            
```

### Package tests: lexigram-ai-relay-gateway

- Scope: `lexigram-ai-relay-gateway/tests`
- Command: `uv run pytest lexigram-ai-relay-gateway/tests -q -m not integration --cov=lexigram.ai.relay.gateway`
- Status: **PASS**
- Exit code: `0`
- Duration: `3897 ms`
- Parsed summary: `414 passed, 4 warnings in 2.32s`
- Counters: passed=414, total=414, failed=0, skipped=0, warnings=4, coverage=95.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:45:52 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 17%]
........................................................................ [ 34%]
........................................................................ [ 52%]
........................................................................ [ 69%]
........................................................................ [ 86%]
......................................................                   [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/_
```

### Package tests: lexigram-ai-relay

- Scope: `lexigram-ai-relay/tests`
- Command: `uv run pytest lexigram-ai-relay/tests -q -m not integration --cov=lexigram.ai.relay`
- Status: **PASS**
- Exit code: `0`
- Duration: `6778 ms`
- Parsed summary: `539 passed, 4 warnings in 5.19s`
- Counters: passed=539, total=539, failed=0, skipped=0, warnings=4, coverage=91.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:45:56 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
2026-08-09 13:45:56 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=RelayModule providers=0
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
- Duration: `2697 ms`
- Parsed summary: `207 passed, 4 warnings in 1.18s`
- Counters: passed=207, total=207, failed=0, skipped=0, warnings=4, coverage=90.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:46:03 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 34%]
........................................................................ [ 69%]
...............................................................          [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtur
```

### Package tests: lexigram-ai-skills

- Scope: `lexigram-ai-skills/tests`
- Command: `uv run pytest lexigram-ai-skills/tests -q -m not integration --cov=lexigram.ai.skills`
- Status: **PASS**
- Exit code: `0`
- Duration: `2926 ms`
- Parsed summary: `263 passed, 6 warnings in 1.43s`
- Counters: passed=263, total=263, failed=0, skipped=0, warnings=6, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:46:05 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 27%]
........................................................................ [ 54%]
........................................................................ [ 82%]
...............................................                          [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-ai-workers

- Scope: `lexigram-ai-workers/tests`
- Command: `uv run pytest lexigram-ai-workers/tests -q -m not integration --cov=lexigram.ai.workers`
- Status: **PASS**
- Exit code: `0`
- Duration: `4262 ms`
- Parsed summary: `318 passed, 7 deselected, 4 warnings in 2.69s`
- Counters: passed=318, total=318, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:46:08 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `19408 ms`
- Parsed summary: `442 passed, 11 skipped, 15 deselected, 4 warnings in 17.48s`
- Counters: passed=442, total=453, failed=0, skipped=11, warnings=4, coverage=42.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:46:13 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
...ss..s................................................................ [ 16%]
........................................................................ [ 32%]
...s.s.................................................................. [ 48%]
........................................................................ [ 64%]
........................................................................ [ 80%]
........................................................................ [ 96%]
...............
ERROR: Coverage failure: total of 42 is less than fail-under=60
                                                    
```

### Package tests: lexigram-audit

- Scope: `lexigram-audit/tests`
- Command: `uv run pytest lexigram-audit/tests -q -m not integration --cov=lexigram.audit`
- Status: **FAIL**
- Exit code: `1`
- Duration: `2630 ms`
- Parsed summary: `242 passed, 17 deselected, 4 warnings in 1.11s`
- Counters: passed=242, total=242, failed=0, skipped=0, warnings=4, coverage=72.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:46:32 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 29%]
........................................................................ [ 59%]
........................................................................ [ 89%]
..........................
ERROR: Coverage failure: total of 72 is less than fail-under=80
                                                                         [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexi
```

### Package tests: lexigram-auth

- Scope: `lexigram-auth/tests`
- Command: `uv run pytest lexigram-auth/tests -q -m not integration --cov=lexigram.auth`
- Status: **FAIL**
- Exit code: `1`
- Duration: `21632 ms`
- Parsed summary: `553 passed, 4 skipped, 2 deselected, 6 warnings in 19.94s`
- Counters: passed=553, total=557, failed=0, skipped=4, warnings=6, coverage=64.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:46:35 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 12%]
.......................ssss............................................. [ 25%]
........................................................................ [ 38%]
........................................................................ [ 51%]
........................................................................ [ 64%]
........................................................................ [ 77%]
........................................................................ [ 90%]
....................................................
```

### Package tests: lexigram-cache

- Scope: `lexigram-cache/tests`
- Command: `uv run pytest lexigram-cache/tests -q -m not integration --cov=lexigram.cache`
- Status: **FAIL**
- Exit code: `1`
- Duration: `10958 ms`
- Parsed summary: `741 passed, 13 skipped, 22 deselected, 6 warnings in 9.15s`
- Counters: passed=741, total=754, failed=0, skipped=13, warnings=6, coverage=69.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:46:56 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  9%]
.................ss..................................................... [ 19%]
........................................................................ [ 28%]
...ssssssssss........................................................... [ 38%]
........................................................................ [ 47%]
........................................................................ [ 57%]
........................................................................ [ 66%]
....................................................
```

### Package tests: lexigram-cli

- Scope: `lexigram-cli/tests`
- Command: `uv run pytest lexigram-cli/tests -q -m not integration --cov=lexigram.cli`
- Status: **PASS**
- Exit code: `0`
- Duration: `11777 ms`
- Parsed summary: `846 passed, 1 skipped, 7 deselected, 6 warnings in 9.73s`
- Counters: passed=846, total=847, failed=0, skipped=1, warnings=6, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:47:07 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  8%]
........................................................................ [ 17%]
........................................................................ [ 25%]
........................................................................ [ 34%]
........................................................................ [ 42%]
........................................................................ [ 51%]
........................................................................ [ 59%]
....................................................
```

### Package tests: lexigram-events

- Scope: `lexigram-events/tests`
- Command: `uv run pytest lexigram-events/tests -q -m not integration --cov=lexigram.events`
- Status: **FAIL**
- Exit code: `1`
- Duration: `12452 ms`
- Parsed summary: `913 passed, 15 skipped, 11 deselected, 5 warnings in 10.74s`
- Counters: passed=913, total=928, failed=0, skipped=15, warnings=5, coverage=61.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:47:19 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
...s.................................................................... [  7%]
........................................................................ [ 15%]
........................................................................ [ 23%]
........................................................................ [ 31%]
........................................................................ [ 39%]
........................................................................ [ 46%]
........................................................................ [ 54%]
....................................................
```

### Package tests: lexigram-features

- Scope: `lexigram-features/tests`
- Command: `uv run pytest lexigram-features/tests -q -m not integration --cov=lexigram.features`
- Status: **PASS**
- Exit code: `0`
- Duration: `3761 ms`
- Parsed summary: `245 passed, 14 deselected, 17 warnings in 2.25s`
- Counters: passed=245, total=245, failed=0, skipped=0, warnings=17, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:47:32 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2538 ms`
- Parsed summary: `252 passed, 1 skipped, 7 deselected, 4 warnings in 1.08s`
- Counters: passed=252, total=253, failed=0, skipped=1, warnings=4, coverage=73.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:47:35 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 28%]
..................s..................................................... [ 56%]
........................................................................ [ 85%]
.....................................                                    [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-graphql

- Scope: `lexigram-graphql/tests`
- Command: `uv run pytest lexigram-graphql/tests -q -m not integration --cov=lexigram.graphql`
- Status: **PASS**
- Exit code: `0`
- Duration: `5833 ms`
- Parsed summary: `502 passed, 4 skipped, 11 deselected, 4 warnings in 3.95s`
- Counters: passed=502, total=506, failed=0, skipped=4, warnings=4, coverage=72.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:47:38 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
s....................................................................... [ 14%]
........................................................................ [ 28%]
................s....................................................... [ 42%]
.......s.....s.......................................................... [ 56%]
........................................................................ [ 71%]
........................................................................ [ 85%]
........................................................................ [ 99%]
..                                                  
```

### Package tests: lexigram-http

- Scope: `lexigram-http/tests`
- Command: `uv run pytest lexigram-http/tests -q -m not integration --cov=lexigram.http`
- Status: **PASS**
- Exit code: `0`
- Duration: `2890 ms`
- Parsed summary: `433 passed, 9 deselected, 4 warnings in 1.35s`
- Counters: passed=433, total=433, failed=0, skipped=0, warnings=4, coverage=73.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:47:44 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 16%]
........................................................................ [ 33%]
........................................................................ [ 49%]
........................................................................ [ 66%]
........................................................................ [ 83%]
........................................................................ [ 99%]
.                                                                        [100%]
=============================== warnings summary ===
```

### Package tests: lexigram-monitor

- Scope: `lexigram-monitor/tests`
- Command: `uv run pytest lexigram-monitor/tests -q -m not integration --cov=lexigram.monitor`
- Status: **PASS**
- Exit code: `0`
- Duration: `8938 ms`
- Parsed summary: `303 passed, 5 skipped, 4 deselected, 4 warnings in 7.35s`
- Counters: passed=303, total=308, failed=0, skipped=5, warnings=4, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:47:47 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 23%]
.............................................sss.s...................... [ 46%]
........................................................................ [ 70%]
.................................................s...................... [ 93%]
....................                                                     [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/
```

### Package tests: lexigram-multimedia-beat

- Scope: `lexigram-multimedia-beat/tests`
- Command: `uv run pytest lexigram-multimedia-beat/tests -q -m not integration --cov=lexigram.multimedia.beat`
- Status: **PASS**
- Exit code: `0`
- Duration: `2284 ms`
- Parsed summary: `12 passed, 2 deselected, 4 warnings in 0.58s`
- Counters: passed=12, total=12, failed=0, skipped=0, warnings=4, coverage=69.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:47:55 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
............                                                             [100%]
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
- Duration: `2493 ms`
- Parsed summary: `53 passed, 4 warnings in 0.81s`
- Counters: passed=53, total=53, failed=0, skipped=0, warnings=4, coverage=92.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:47:58 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.....................................................                    [100%]
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
- Duration: `2153 ms`
- Parsed summary: `23 passed, 4 warnings in 0.49s`
- Counters: passed=23, total=23, failed=0, skipped=0, warnings=4, coverage=84.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:48:00 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2244 ms`
- Parsed summary: `37 passed, 4 warnings in 0.58s`
- Counters: passed=37, total=37, failed=0, skipped=0, warnings=4, coverage=79.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:48:02 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.....................................                                    [100%]
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
- Duration: `2388 ms`
- Parsed summary: `53 passed, 4 warnings in 0.72s`
- Counters: passed=53, total=53, failed=0, skipped=0, warnings=4, coverage=70.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:48:05 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.....................................................                    [100%]
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
- Duration: `2205 ms`
- Parsed summary: `26 passed, 4 warnings in 0.53s`
- Counters: passed=26, total=26, failed=0, skipped=0, warnings=4, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:48:07 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
..........................                                               [100%]
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
- Duration: `5428 ms`
- Parsed summary: `139 passed, 4 warnings in 3.74s`
- Counters: passed=139, total=139, failed=0, skipped=0, warnings=4, coverage=84.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:48:09 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 51%]
...................................................................      [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/
```

### Package tests: lexigram-multimedia

- Scope: `lexigram-multimedia/tests`
- Command: `uv run pytest lexigram-multimedia/tests -q -m not integration --cov=lexigram.multimedia`
- Status: **PASS**
- Exit code: `0`
- Duration: `5289 ms`
- Parsed summary: `81 passed, 5 warnings in 3.67s`
- Counters: passed=81, total=81, failed=0, skipped=0, warnings=5, coverage=56.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:48:15 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 88%]
.........                                                                [100%]
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
- Duration: `3437 ms`
- Parsed summary: `414 passed, 10 deselected, 4 warnings in 1.92s`
- Counters: passed=414, total=414, failed=0, skipped=0, warnings=4, coverage=91.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:48:20 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 17%]
........................................................................ [ 34%]
........................................................................ [ 52%]
........................................................................ [ 69%]
........................................................................ [ 86%]
......................................................                   [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/_
```

### Package tests: lexigram-notification

- Scope: `lexigram-notification/tests`
- Command: `uv run pytest lexigram-notification/tests -q -m not integration --cov=lexigram.notification`
- Status: **PASS**
- Exit code: `0`
- Duration: `4531 ms`
- Parsed summary: `239 passed, 8 deselected, 4 warnings in 2.98s`
- Counters: passed=239, total=239, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:48:23 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 30%]
........................................................................ [ 60%]
........................................................................ [ 90%]
.......................                                                  [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-queue

- Scope: `lexigram-queue/tests`
- Command: `uv run pytest lexigram-queue/tests -q -m not integration --cov=lexigram.queue`
- Status: **PASS**
- Exit code: `0`
- Duration: `4154 ms`
- Parsed summary: `201 passed, 19 deselected, 4 warnings in 2.64s`
- Counters: passed=201, total=201, failed=0, skipped=0, warnings=4, coverage=82.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:48:28 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 35%]
........................................................................ [ 71%]
.........................................................                [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtur
```

### Package tests: lexigram-resilience

- Scope: `lexigram-resilience/tests`
- Command: `uv run pytest lexigram-resilience/tests -q -m not integration --cov=lexigram.resilience`
- Status: **PASS**
- Exit code: `0`
- Duration: `21390 ms`
- Parsed summary: `297 passed, 23 deselected, 4 warnings in 19.89s`
- Counters: passed=297, total=297, failed=0, skipped=0, warnings=4, coverage=71.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:48:32 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 24%]
........................................................................ [ 48%]
........................................................................ [ 72%]
........................................................................ [ 96%]
.........                                                                [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/
```

### Package tests: lexigram-search

- Scope: `lexigram-search/tests`
- Command: `uv run pytest lexigram-search/tests -q -m not integration --cov=lexigram.search`
- Status: **PASS**
- Exit code: `0`
- Duration: `4266 ms`
- Parsed summary: `640 passed, 4 skipped, 15 deselected, 4 warnings in 2.58s`
- Counters: passed=640, total=644, failed=0, skipped=4, warnings=4, coverage=60.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:48:53 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 11%]
........................................................................ [ 22%]
........................................................................ [ 33%]
........................................................................ [ 45%]
........................................................................ [ 56%]
........................................................................ [ 67%]
........................................................................ [ 78%]
....................................................
```

### Package tests: lexigram-secrets

- Scope: `lexigram-secrets/tests`
- Command: `uv run pytest lexigram-secrets/tests -q -m not integration --cov=lexigram.secrets`
- Status: **FAIL**
- Exit code: `1`
- Duration: `1874 ms`
- Parsed summary: `85 passed, 4 warnings in 0.37s`
- Counters: passed=85, total=85, failed=0, skipped=0, warnings=4, coverage=39.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:48:58 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 84%]
.............
ERROR: Coverage failure: total of 39 is less than fail-under=55
                                                                         [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures
```

### Package tests: lexigram-sql (unit only, no external DB)

- Scope: `lexigram-sql/tests`
- Command: `uv run pytest lexigram-sql/tests/unit -q -m not integration --cov=lexigram.sql`
- Status: **FAIL**
- Exit code: `1`
- Duration: `11348 ms`
- Parsed summary: `1086 passed, 90 skipped, 6 warnings in 9.34s`
- Counters: passed=1086, total=1176, failed=0, skipped=90, warnings=6, coverage=55.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:49:00 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  6%]
........................................................................ [ 12%]
..............................ss........................................ [ 18%]
........................................................................ [ 24%]
........................................................................ [ 30%]
........................................................................ [ 36%]
......s...............sssssss.....ss.................................... [ 42%]
....................................................
```

### Package tests: lexigram-storage

- Scope: `lexigram-storage/tests`
- Command: `uv run pytest lexigram-storage/tests -q -m not integration --cov=lexigram.storage`
- Status: **PASS**
- Exit code: `0`
- Duration: `7028 ms`
- Parsed summary: `440 passed, 3 skipped, 22 deselected, 4 warnings in 5.48s`
- Counters: passed=440, total=443, failed=0, skipped=3, warnings=4, coverage=62.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:49:11 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 16%]
........................................................................ [ 32%]
............................s........................................... [ 48%]
........................................................................ [ 65%]
........................................................................ [ 81%]
........................................................................ [ 97%]
.........s                                                               [100%]
=============================== warnings summary ===
```

### Package tests: lexigram-tasks

- Scope: `lexigram-tasks/tests`
- Command: `uv run pytest lexigram-tasks/tests -q -m not integration --cov=lexigram.tasks`
- Status: **FAIL**
- Exit code: `1`
- Duration: `9272 ms`
- Parsed summary: `410 passed, 21 skipped, 9 deselected, 4 warnings in 7.54s`
- Counters: passed=410, total=431, failed=0, skipped=21, warnings=4, coverage=65.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:49:18 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.......................................................ssssss........... [ 16%]
........................................................................ [ 33%]
...........sssss........................................................ [ 50%]
..........................................sssssssss..................... [ 66%]
........................................................................ [ 83%]
..........................s............................................
ERROR: Coverage failure: total of 65 is less than fail-under=80
                                                                         [10
```

### Package tests: lexigram-tenancy

- Scope: `lexigram-tenancy/tests`
- Command: `uv run pytest lexigram-tenancy/tests -q -m not integration --cov=lexigram.tenancy`
- Status: **PASS**
- Exit code: `0`
- Duration: `3324 ms`
- Parsed summary: `345 passed, 4 deselected, 4 warnings in 1.76s`
- Counters: passed=345, total=345, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:49:27 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 20%]
........................................................................ [ 41%]
........................................................................ [ 62%]
........................................................................ [ 83%]
.........................................................                [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/
```

### Package tests: lexigram-testing

- Scope: `lexigram-testing/tests`
- Command: `uv run pytest lexigram-testing/tests -q -m not integration --cov=lexigram.testing`
- Status: **FAIL**
- Exit code: `1`
- Duration: `7705 ms`
- Parsed summary: `436 passed, 15 skipped, 13 deselected, 4 warnings in 6.07s`
- Counters: passed=436, total=451, failed=0, skipped=15, warnings=4, coverage=17.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:49:31 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `5804 ms`
- Parsed summary: `960 passed, 8 deselected, 12 warnings in 4.17s`
- Counters: passed=960, total=960, failed=0, skipped=0, warnings=12, coverage=74.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:49:38 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  7%]
........................................................................ [ 15%]
........................................................................ [ 22%]
........................................................................ [ 30%]
........................................................................ [ 37%]
........................................................................ [ 45%]
........................................................................ [ 52%]
....................................................
```

### Package tests: lexigram-vector

- Scope: `lexigram-vector/tests`
- Command: `uv run pytest lexigram-vector/tests -q -m not integration --cov=lexigram.vector`
- Status: **PASS**
- Exit code: `0`
- Duration: `4783 ms`
- Parsed summary: `498 passed, 20 deselected, 4 warnings in 3.18s`
- Counters: passed=498, total=498, failed=0, skipped=0, warnings=4, coverage=76.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:49:44 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 14%]
........................................................................ [ 28%]
........................................................................ [ 43%]
........................................................................ [ 57%]
........................................................................ [ 72%]
........................................................................ [ 86%]
..................................................................       [100%]
=============================== warnings summary ===
```

### Package tests: lexigram-web

- Scope: `lexigram-web/tests`
- Command: `uv run pytest lexigram-web/tests -q -m not integration --cov=lexigram.web`
- Status: **PASS**
- Exit code: `0`
- Duration: `12906 ms`
- Parsed summary: `1344 passed, 7 skipped, 7 deselected, 6 warnings in 10.97s`
- Counters: passed=1344, total=1351, failed=0, skipped=7, warnings=6, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:49:49 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
sss..................................................................... [  5%]
........................................................................ [ 10%]
........................................................................ [ 16%]
........................................................................ [ 21%]
.....................s.................................................. [ 26%]
........................................................................ [ 32%]
........................................s............................... [ 37%]
....................................................
```

### Package tests: lexigram-webhook

- Scope: `lexigram-webhook/tests`
- Command: `uv run pytest lexigram-webhook/tests -q -m not integration --cov=lexigram.webhook`
- Status: **PASS**
- Exit code: `0`
- Duration: `2764 ms`
- Parsed summary: `327 passed, 4 warnings in 1.22s`
- Counters: passed=327, total=327, failed=0, skipped=0, warnings=4, coverage=86.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:50:02 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 22%]
........................................................................ [ 44%]
........................................................................ [ 66%]
........................................................................ [ 88%]
.......................................                                  [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/
```

### Package tests: lexigram-workflow

- Scope: `lexigram-workflow/tests`
- Command: `uv run pytest lexigram-workflow/tests -q -m not integration --cov=lexigram.workflow`
- Status: **PASS**
- Exit code: `0`
- Duration: `14267 ms`
- Parsed summary: `553 passed, 23 deselected, 4 warnings in 12.69s`
- Counters: passed=553, total=553, failed=0, skipped=0, warnings=4, coverage=71.0%
- Example failures: none
- Output snippet:

```text
2026-08-09 13:50:05 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 39%]
........................................................................ [ 52%]
........................................................................ [ 65%]
........................................................................ [ 78%]
........................................................................ [ 91%]
.................................................   
```

