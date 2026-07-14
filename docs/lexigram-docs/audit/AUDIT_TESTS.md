# AUDIT_TESTS.md — Lexigram Framework Targeted Test Execution Audit

> **Source**: Live pytest execution evidence for targeted scopes, with `tests/` directory scanning as supporting context.

---

## Summary

- Total passed tests: 31287
- Total failed tests: 0
- Total skipped tests: 263
- Total warnings: 305
- Aggregate code coverage: 75.87%

- Representative commands run: 54
- Commands passing: 47
- Commands failing: 7
- Packages with tests: 54
- Test files: 3034
- Test functions: 31462

### Exit Codes Reference

- **`0`**: Success — All tests passed and code coverage met the configured threshold.
- **`1`**: Failure — Functional tests failed OR code coverage fell below the package's `--cov-fail-under` threshold.
- **`timeout`**: The test command exceeded the execution time limit (120s) and was automatically terminated.

## Execution Evidence

| Label | Code Coverage | Pass/Total | Failed | Skipped | Warnings | Exit Code | Duration |
|-------|---------------|------------|---------|----------|------|-----------|----------|
| Lexigram framework core tests | 59.0% | 2987/2992 | 0 | 5 | 1 | 1 | 27206 ms |
| Package tests: lexigram-contracts | 35.0% | 1783/1783 | 0 | 0 | 4 | 1 | 11327 ms |
| Package tests: lexigram-admin | 76.0% | 4562/4573 | 0 | 11 | 18 | 0 | 61720 ms |
| Package tests: lexigram-ai-agents | 85.0% | 402/402 | 0 | 0 | 4 | 0 | 6145 ms |
| Package tests: lexigram-ai-evaluation | 99.0% | 142/142 | 0 | 0 | 4 | 0 | 1906 ms |
| Package tests: lexigram-ai-feedback | 96.0% | 260/260 | 0 | 0 | 4 | 0 | 2267 ms |
| Package tests: lexigram-ai-governance | 88.0% | 544/544 | 0 | 0 | 24 | 0 | 5014 ms |
| Package tests: lexigram-ai-guard | 87.0% | 242/242 | 0 | 0 | 7 | 0 | 2353 ms |
| Package tests: lexigram-ai-llm | 71.0% | 949/969 | 0 | 20 | 4 | 0 | 33350 ms |
| Package tests: lexigram-ai-mcp | 51.0% | 384/384 | 0 | 0 | 4 | 0 | 3810 ms |
| Package tests: lexigram-ai-memory | 83.0% | 240/240 | 0 | 0 | 4 | 0 | 2588 ms |
| Package tests: lexigram-ai-observability | 87.0% | 260/260 | 0 | 0 | 4 | 0 | 2799 ms |
| Package tests: lexigram-ai-prompt | 87.0% | 307/307 | 0 | 0 | 4 | 0 | 2666 ms |
| Package tests: lexigram-ai-rag | 62.0% | 528/535 | 0 | 7 | 4 | 0 | 7879 ms |
| Package tests: lexigram-ai-relay-gateway | 94.0% | 536/536 | 0 | 0 | 4 | 0 | 4176 ms |
| Package tests: lexigram-ai-relay | 91.0% | 539/539 | 0 | 0 | 4 | 0 | 5917 ms |
| Package tests: lexigram-ai-session | 88.0% | 210/210 | 0 | 0 | 4 | 0 | 2665 ms |
| Package tests: lexigram-ai-skills | 78.0% | 268/268 | 0 | 0 | 6 | 0 | 2803 ms |
| Package tests: lexigram-ai-workers | 87.0% | 328/328 | 0 | 0 | 4 | 0 | 4106 ms |
| Package tests: lexigram-ai | 42.0% | 450/461 | 0 | 11 | 4 | 1 | 18725 ms |
| Package tests: lexigram-audit | 85.0% | 287/287 | 0 | 0 | 4 | 0 | 2559 ms |
| Package tests: lexigram-auth | 68.0% | 616/620 | 0 | 4 | 6 | 1 | 28584 ms |
| Package tests: lexigram-cache | 80.0% | 842/855 | 0 | 13 | 6 | 0 | 11268 ms |
| Package tests: lexigram-cli | 80.0% | 852/853 | 0 | 1 | 6 | 0 | 12548 ms |
| Package tests: lexigram-events | 63.0% | 969/984 | 0 | 15 | 6 | 1 | 12918 ms |
| Package tests: lexigram-features | 80.0% | 248/248 | 0 | 0 | 17 | 0 | 3587 ms |
| Package tests: lexigram-graph | 79.0% | 257/258 | 0 | 1 | 4 | 0 | 2459 ms |
| Package tests: lexigram-graphql | 76.0% | 519/521 | 0 | 2 | 23 | 0 | 6398 ms |
| Package tests: lexigram-http | 77.0% | 450/450 | 0 | 0 | 4 | 0 | 2887 ms |
| Package tests: lexigram-monitor | 82.0% | 333/338 | 0 | 5 | 4 | 0 | 8839 ms |
| Package tests: lexigram-multimedia-beat | 71.0% | 18/18 | 0 | 0 | 4 | 0 | 2761 ms |
| Package tests: lexigram-multimedia-image | 92.0% | 54/54 | 0 | 0 | 4 | 0 | 2274 ms |
| Package tests: lexigram-multimedia-interpolate | 87.0% | 23/23 | 0 | 0 | 4 | 0 | 2037 ms |
| Package tests: lexigram-multimedia-music | 84.0% | 38/38 | 0 | 0 | 4 | 0 | 2100 ms |
| Package tests: lexigram-multimedia-tts | 78.0% | 63/63 | 0 | 0 | 4 | 0 | 2417 ms |
| Package tests: lexigram-multimedia-upscale | 93.0% | 42/42 | 0 | 0 | 4 | 0 | 2271 ms |
| Package tests: lexigram-multimedia-video | 86.0% | 182/182 | 0 | 0 | 4 | 0 | 5748 ms |
| Package tests: lexigram-multimedia | 55.0% | 86/86 | 0 | 0 | 5 | 0 | 5224 ms |
| Package tests: lexigram-nosql | 91.0% | 536/536 | 0 | 0 | 4 | 0 | 3599 ms |
| Package tests: lexigram-notification | 83.0% | 289/289 | 0 | 0 | 4 | 0 | 5586 ms |
| Package tests: lexigram-queue | 84.0% | 228/228 | 0 | 0 | 4 | 0 | 4708 ms |
| Package tests: lexigram-resilience | 74.0% | 310/310 | 0 | 0 | 4 | 0 | 20510 ms |
| Package tests: lexigram-search | 65.0% | 813/817 | 0 | 4 | 4 | 0 | 4611 ms |
| Package tests: lexigram-secrets | 58.0% | 127/127 | 0 | 0 | 4 | 0 | 1807 ms |
| Package tests: lexigram-sql (unit only, no external DB) | 61.0% | 1301/1347 | 0 | 46 | 6 | 0 | 22861 ms |
| Package tests: lexigram-storage | 62.0% | 453/456 | 0 | 3 | 4 | 0 | 7025 ms |
| Package tests: lexigram-tasks | 73.0% | 525/540 | 0 | 15 | 4 | 1 | 11852 ms |
| Package tests: lexigram-tenancy | 83.0% | 360/360 | 0 | 0 | 4 | 0 | 3167 ms |
| Package tests: lexigram-testing | 17.0% | 436/451 | 0 | 15 | 4 | 1 | 8710 ms |
| Package tests: lexigram-ui | 70.0% | 1251/1329 | 0 | 78 | 12 | 0 | 7315 ms |
| Package tests: lexigram-vector | 77.0% | 546/546 | 0 | 0 | 4 | 0 | 4709 ms |
| Package tests: lexigram-web | 81.0% | 1422/1429 | 0 | 7 | 6 | 0 | 13353 ms |
| Package tests: lexigram-webhook | 86.0% | 334/334 | 0 | 0 | 4 | 0 | 2852 ms |
| Package tests: lexigram-workflow | 70.0% | 556/556 | 0 | 0 | 4 | 0 | 14117 ms |

### Execution Scope Notes

- `framework-core`: real test execution for `lexigram/tests`.
- `package`: real test execution for `<package>/tests` across every discovered Lexigram package with tests.
### Lexigram framework core tests

- Scope: `lexigram/tests`
- Command: `uv run pytest lexigram/tests -q -m not integration --cov=lexigram`
- Status: **FAIL**
- Exit code: `1`
- Duration: `27206 ms`
- Parsed summary: `2987 passed, 5 skipped, 19 deselected, 1 warning in 24.11s`
- Counters: passed=2987, total=2992, failed=0, skipped=5, warnings=1, coverage=59.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:01:32 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  2%]
........................................................................ [  4%]
........................................................................ [  7%]
........................................................................ [  9%]
........................................................................ [ 12%]
........................................................................ [ 14%]
........................................................................ [ 16%]
....................................................
```

### Package tests: lexigram-contracts

- Scope: `lexigram-contracts/tests`
- Command: `uv run pytest lexigram-contracts/tests -q -m not integration --cov=lexigram.contracts`
- Status: **FAIL**
- Exit code: `1`
- Duration: `11327 ms`
- Parsed summary: `1783 passed, 4 warnings in 9.76s`
- Counters: passed=1783, total=1783, failed=0, skipped=0, warnings=4, coverage=35.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:01:59 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `61720 ms`
- Parsed summary: `4562 passed, 11 skipped, 27 deselected, 18 warnings in 58.97s`
- Counters: passed=4562, total=4573, failed=0, skipped=11, warnings=18, coverage=76.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:02:10 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `6145 ms`
- Parsed summary: `402 passed, 10 deselected, 4 warnings in 4.69s`
- Counters: passed=402, total=402, failed=0, skipped=0, warnings=4, coverage=85.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:03:12 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `1906 ms`
- Parsed summary: `142 passed, 4 warnings in 0.61s`
- Counters: passed=142, total=142, failed=0, skipped=0, warnings=4, coverage=99.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:03:18 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 50%]
......................................................................   [100%]
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
- Duration: `2267 ms`
- Parsed summary: `260 passed, 4 warnings in 0.95s`
- Counters: passed=260, total=260, failed=0, skipped=0, warnings=4, coverage=96.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:03:20 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 27%]
........................................................................ [ 55%]
........................................................................ [ 83%]
............................................                             [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-ai-governance

- Scope: `lexigram-ai-governance/tests`
- Command: `uv run pytest lexigram-ai-governance/tests -q -m not integration --cov=lexigram.ai.governance`
- Status: **PASS**
- Exit code: `0`
- Duration: `5014 ms`
- Parsed summary: `544 passed, 7 deselected, 24 warnings in 3.55s`
- Counters: passed=544, total=544, failed=0, skipped=0, warnings=24, coverage=88.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:03:22 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 39%]
........................................................................ [ 52%]
........................................................................ [ 66%]
........................................................................ [ 79%]
........................................................................ [ 92%]
........................................            
```

### Package tests: lexigram-ai-guard

- Scope: `lexigram-ai-guard/tests`
- Command: `uv run pytest lexigram-ai-guard/tests -q -m not integration --cov=lexigram.ai.guard`
- Status: **PASS**
- Exit code: `0`
- Duration: `2353 ms`
- Parsed summary: `242 passed, 17 deselected, 7 warnings in 1.05s`
- Counters: passed=242, total=242, failed=0, skipped=0, warnings=7, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:03:27 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 29%]
........................................................................ [ 59%]
........................................................................ [ 89%]
..........................                                               [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-ai-llm

- Scope: `lexigram-ai-llm/tests`
- Command: `uv run pytest lexigram-ai-llm/tests -q -m not integration --cov=lexigram.ai.llm`
- Status: **PASS**
- Exit code: `0`
- Duration: `33350 ms`
- Parsed summary: `949 passed, 20 skipped, 19 deselected, 4 warnings in 31.43s`
- Counters: passed=949, total=969, failed=0, skipped=20, warnings=4, coverage=71.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:03:30 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `3810 ms`
- Parsed summary: `384 passed, 13 deselected, 4 warnings in 2.43s`
- Counters: passed=384, total=384, failed=0, skipped=0, warnings=4, coverage=51.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:04:03 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2588 ms`
- Parsed summary: `240 passed, 16 deselected, 4 warnings in 1.27s`
- Counters: passed=240, total=240, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:04:07 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2799 ms`
- Parsed summary: `260 passed, 10 deselected, 4 warnings in 1.48s`
- Counters: passed=260, total=260, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:04:10 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 27%]
........................................................................ [ 55%]
........................................................................ [ 83%]
............................................                             [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-ai-prompt

- Scope: `lexigram-ai-prompt/tests`
- Command: `uv run pytest lexigram-ai-prompt/tests -q -m not integration --cov=lexigram.ai.prompt`
- Status: **PASS**
- Exit code: `0`
- Duration: `2666 ms`
- Parsed summary: `307 passed, 4 warnings in 1.33s`
- Counters: passed=307, total=307, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:04:12 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 23%]
........................................................................ [ 46%]
........................................................................ [ 70%]
........................................................................ [ 93%]
...................                                                      [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/
```

### Package tests: lexigram-ai-rag

- Scope: `lexigram-ai-rag/tests`
- Command: `uv run pytest lexigram-ai-rag/tests -q -m not integration --cov=lexigram.ai.rag`
- Status: **PASS**
- Exit code: `0`
- Duration: `7879 ms`
- Parsed summary: `528 passed, 7 skipped, 8 deselected, 4 warnings in 6.35s`
- Counters: passed=528, total=535, failed=0, skipped=7, warnings=4, coverage=62.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:04:15 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4176 ms`
- Parsed summary: `536 passed, 4 warnings in 2.78s`
- Counters: passed=536, total=536, failed=0, skipped=0, warnings=4, coverage=94.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:04:23 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 40%]
........................................................................ [ 53%]
........................................................................ [ 67%]
........................................................................ [ 80%]
........................................................................ [ 94%]
................................                    
```

### Package tests: lexigram-ai-relay

- Scope: `lexigram-ai-relay/tests`
- Command: `uv run pytest lexigram-ai-relay/tests -q -m not integration --cov=lexigram.ai.relay`
- Status: **PASS**
- Exit code: `0`
- Duration: `5917 ms`
- Parsed summary: `539 passed, 4 warnings in 4.51s`
- Counters: passed=539, total=539, failed=0, skipped=0, warnings=4, coverage=91.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:04:27 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
2026-08-19 03:04:27 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=RelayModule providers=0
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
- Duration: `2665 ms`
- Parsed summary: `210 passed, 4 warnings in 1.31s`
- Counters: passed=210, total=210, failed=0, skipped=0, warnings=4, coverage=88.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:04:33 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2803 ms`
- Parsed summary: `268 passed, 6 warnings in 1.48s`
- Counters: passed=268, total=268, failed=0, skipped=0, warnings=6, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:04:36 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4106 ms`
- Parsed summary: `328 passed, 7 deselected, 4 warnings in 2.73s`
- Counters: passed=328, total=328, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:04:38 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 21%]
........................................................................ [ 43%]
........................................................................ [ 65%]
........................................................................ [ 87%]
........................................                                 [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/
```

### Package tests: lexigram-ai

- Scope: `lexigram-ai/tests`
- Command: `uv run pytest lexigram-ai/tests -q -m not integration --cov=lexigram.ai`
- Status: **FAIL**
- Exit code: `1`
- Duration: `18725 ms`
- Parsed summary: `450 passed, 11 skipped, 15 deselected, 4 warnings in 16.94s`
- Counters: passed=450, total=461, failed=0, skipped=11, warnings=4, coverage=42.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:04:43 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
...ss..s................................................................ [ 15%]
........................................................................ [ 31%]
...........s.s.......................................................... [ 47%]
........................................................................ [ 63%]
........................................................................ [ 79%]
........................................................................ [ 94%]
.......................
ERROR: Coverage failure: total of 42 is less than fail-under=60
                                            
```

### Package tests: lexigram-audit

- Scope: `lexigram-audit/tests`
- Command: `uv run pytest lexigram-audit/tests -q -m not integration --cov=lexigram.audit`
- Status: **PASS**
- Exit code: `0`
- Duration: `2559 ms`
- Parsed summary: `287 passed, 17 deselected, 4 warnings in 1.20s`
- Counters: passed=287, total=287, failed=0, skipped=0, warnings=4, coverage=85.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:05:01 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 25%]
........................................................................ [ 50%]
........................................................................ [ 75%]
.......................................................................  [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-auth

- Scope: `lexigram-auth/tests`
- Command: `uv run pytest lexigram-auth/tests -q -m not integration --cov=lexigram.auth`
- Status: **FAIL**
- Exit code: `1`
- Duration: `28584 ms`
- Parsed summary: `616 passed, 4 skipped, 2 deselected, 6 warnings in 27.10s`
- Counters: passed=616, total=620, failed=0, skipped=4, warnings=6, coverage=68.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:05:04 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 11%]
...................................................ssss................. [ 23%]
........................................................................ [ 34%]
........................................................................ [ 46%]
........................................................................ [ 58%]
........................................................................ [ 69%]
........................................................................ [ 81%]
....................................................
```

### Package tests: lexigram-cache

- Scope: `lexigram-cache/tests`
- Command: `uv run pytest lexigram-cache/tests -q -m not integration --cov=lexigram.cache`
- Status: **PASS**
- Exit code: `0`
- Duration: `11268 ms`
- Parsed summary: `842 passed, 13 skipped, 22 deselected, 6 warnings in 9.61s`
- Counters: passed=842, total=855, failed=0, skipped=13, warnings=6, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:05:32 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  8%]
........................................ss.............................. [ 16%]
........................................................................ [ 25%]
................................................ssssssssss.............. [ 33%]
........................................................................ [ 42%]
........................................................................ [ 50%]
........................................................................ [ 58%]
....................................................
```

### Package tests: lexigram-cli

- Scope: `lexigram-cli/tests`
- Command: `uv run pytest lexigram-cli/tests -q -m not integration --cov=lexigram.cli`
- Status: **PASS**
- Exit code: `0`
- Duration: `12548 ms`
- Parsed summary: `852 passed, 1 skipped, 7 deselected, 6 warnings in 10.60s`
- Counters: passed=852, total=853, failed=0, skipped=1, warnings=6, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:05:44 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `12918 ms`
- Parsed summary: `969 passed, 15 skipped, 11 deselected, 6 warnings in 11.04s`
- Counters: passed=969, total=984, failed=0, skipped=15, warnings=6, coverage=63.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:05:56 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
...s.................................................................... [  7%]
........................................................................ [ 14%]
........................................................................ [ 22%]
........................................................................ [ 29%]
........................................................................ [ 36%]
........................................................................ [ 44%]
........................................................................ [ 51%]
....................................................
```

### Package tests: lexigram-features

- Scope: `lexigram-features/tests`
- Command: `uv run pytest lexigram-features/tests -q -m not integration --cov=lexigram.features`
- Status: **PASS**
- Exit code: `0`
- Duration: `3587 ms`
- Parsed summary: `248 passed, 14 deselected, 17 warnings in 2.24s`
- Counters: passed=248, total=248, failed=0, skipped=0, warnings=17, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:06:09 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 29%]
........................................................................ [ 58%]
........................................................................ [ 87%]
................................                                         [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-graph

- Scope: `lexigram-graph/tests`
- Command: `uv run pytest lexigram-graph/tests -q -m not integration --cov=lexigram.graph`
- Status: **PASS**
- Exit code: `0`
- Duration: `2459 ms`
- Parsed summary: `257 passed, 1 skipped, 7 deselected, 4 warnings in 1.14s`
- Counters: passed=257, total=258, failed=0, skipped=1, warnings=4, coverage=79.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:06:13 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `6398 ms`
- Parsed summary: `519 passed, 2 skipped, 11 deselected, 23 warnings in 4.63s`
- Counters: passed=519, total=521, failed=0, skipped=2, warnings=23, coverage=76.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:06:15 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2887 ms`
- Parsed summary: `450 passed, 9 deselected, 4 warnings in 1.51s`
- Counters: passed=450, total=450, failed=0, skipped=0, warnings=4, coverage=77.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:06:22 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `8839 ms`
- Parsed summary: `333 passed, 5 skipped, 4 deselected, 4 warnings in 7.41s`
- Counters: passed=333, total=338, failed=0, skipped=5, warnings=4, coverage=82.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:06:25 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 21%]
......................................................................ss [ 42%]
s.s..................................................................... [ 63%]
........................................................................ [ 85%]
....s.............................................                       [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/
```

### Package tests: lexigram-multimedia-beat

- Scope: `lexigram-multimedia-beat/tests`
- Command: `uv run pytest lexigram-multimedia-beat/tests -q -m not integration --cov=lexigram.multimedia.beat`
- Status: **PASS**
- Exit code: `0`
- Duration: `2761 ms`
- Parsed summary: `18 passed, 12 deselected, 4 warnings in 1.21s`
- Counters: passed=18, total=18, failed=0, skipped=0, warnings=4, coverage=71.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:06:33 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2274 ms`
- Parsed summary: `54 passed, 4 warnings in 0.78s`
- Counters: passed=54, total=54, failed=0, skipped=0, warnings=4, coverage=92.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:06:36 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2037 ms`
- Parsed summary: `23 passed, 4 warnings in 0.52s`
- Counters: passed=23, total=23, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:06:38 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2100 ms`
- Parsed summary: `38 passed, 4 warnings in 0.60s`
- Counters: passed=38, total=38, failed=0, skipped=0, warnings=4, coverage=84.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:06:40 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2417 ms`
- Parsed summary: `63 passed, 4 warnings in 0.91s`
- Counters: passed=63, total=63, failed=0, skipped=0, warnings=4, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:06:43 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2271 ms`
- Parsed summary: `42 passed, 4 warnings in 0.71s`
- Counters: passed=42, total=42, failed=0, skipped=0, warnings=4, coverage=93.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:06:45 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `5748 ms`
- Parsed summary: `182 passed, 4 warnings in 4.20s`
- Counters: passed=182, total=182, failed=0, skipped=0, warnings=4, coverage=86.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:06:47 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `5224 ms`
- Parsed summary: `86 passed, 5 warnings in 3.70s`
- Counters: passed=86, total=86, failed=0, skipped=0, warnings=5, coverage=55.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:06:53 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `3599 ms`
- Parsed summary: `536 passed, 10 deselected, 4 warnings in 2.22s`
- Counters: passed=536, total=536, failed=0, skipped=0, warnings=4, coverage=91.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:06:58 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `5586 ms`
- Parsed summary: `289 passed, 8 deselected, 4 warnings in 3.94s`
- Counters: passed=289, total=289, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:07:02 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 24%]
........................................................................ [ 49%]
........................................................................ [ 74%]
........................................................................ [ 99%]
.                                                                        [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/
```

### Package tests: lexigram-queue

- Scope: `lexigram-queue/tests`
- Command: `uv run pytest lexigram-queue/tests -q -m not integration --cov=lexigram.queue`
- Status: **PASS**
- Exit code: `0`
- Duration: `4708 ms`
- Parsed summary: `228 passed, 20 deselected, 4 warnings in 3.32s`
- Counters: passed=228, total=228, failed=0, skipped=0, warnings=4, coverage=84.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:07:07 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 31%]
........................................................................ [ 63%]
........................................................................ [ 94%]
............                                                             [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-resilience

- Scope: `lexigram-resilience/tests`
- Command: `uv run pytest lexigram-resilience/tests -q -m not integration --cov=lexigram.resilience`
- Status: **PASS**
- Exit code: `0`
- Duration: `20510 ms`
- Parsed summary: `310 passed, 23 deselected, 4 warnings in 19.19s`
- Counters: passed=310, total=310, failed=0, skipped=0, warnings=4, coverage=74.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:07:12 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 23%]
........................................................................ [ 46%]
........................................................................ [ 69%]
........................................................................ [ 92%]
......................                                                   [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/
```

### Package tests: lexigram-search

- Scope: `lexigram-search/tests`
- Command: `uv run pytest lexigram-search/tests -q -m not integration --cov=lexigram.search`
- Status: **PASS**
- Exit code: `0`
- Duration: `4611 ms`
- Parsed summary: `813 passed, 4 skipped, 15 deselected, 4 warnings in 3.08s`
- Counters: passed=813, total=817, failed=0, skipped=4, warnings=4, coverage=65.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:07:33 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  8%]
........................................................................ [ 17%]
........................................................................ [ 26%]
........................................................................ [ 35%]
........................................................................ [ 44%]
........................................................................ [ 53%]
........................................................................ [ 61%]
....................................................
```

### Package tests: lexigram-secrets

- Scope: `lexigram-secrets/tests`
- Command: `uv run pytest lexigram-secrets/tests -q -m not integration --cov=lexigram.secrets`
- Status: **PASS**
- Exit code: `0`
- Duration: `1807 ms`
- Parsed summary: `127 passed, 4 warnings in 0.48s`
- Counters: passed=127, total=127, failed=0, skipped=0, warnings=4, coverage=58.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:07:37 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `22861 ms`
- Parsed summary: `1301 passed, 46 skipped, 6 warnings in 20.92s`
- Counters: passed=1301, total=1347, failed=0, skipped=46, warnings=6, coverage=61.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:07:39 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  5%]
........................................................................ [ 10%]
........................................................................ [ 16%]
...........ss........................................................... [ 21%]
........................................................................ [ 26%]
........................................................................ [ 32%]
...............................................................s........ [ 37%]
............ss......s...............................
```

### Package tests: lexigram-storage

- Scope: `lexigram-storage/tests`
- Command: `uv run pytest lexigram-storage/tests -q -m not integration --cov=lexigram.storage`
- Status: **PASS**
- Exit code: `0`
- Duration: `7025 ms`
- Parsed summary: `453 passed, 3 skipped, 22 deselected, 4 warnings in 5.62s`
- Counters: passed=453, total=456, failed=0, skipped=3, warnings=4, coverage=62.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:08:02 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `11852 ms`
- Parsed summary: `525 passed, 15 skipped, 9 deselected, 4 warnings in 10.28s`
- Counters: passed=525, total=540, failed=0, skipped=15, warnings=4, coverage=73.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:08:09 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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

### Package tests: lexigram-tenancy

- Scope: `lexigram-tenancy/tests`
- Command: `uv run pytest lexigram-tenancy/tests -q -m not integration --cov=lexigram.tenancy`
- Status: **PASS**
- Exit code: `0`
- Duration: `3167 ms`
- Parsed summary: `360 passed, 4 deselected, 4 warnings in 1.81s`
- Counters: passed=360, total=360, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:08:21 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `8710 ms`
- Parsed summary: `436 passed, 15 skipped, 13 deselected, 4 warnings in 7.22s`
- Counters: passed=436, total=451, failed=0, skipped=15, warnings=4, coverage=17.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:08:24 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `7315 ms`
- Parsed summary: `1251 passed, 78 skipped, 8 deselected, 12 warnings in 5.83s`
- Counters: passed=1251, total=1329, failed=0, skipped=78, warnings=12, coverage=70.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:08:33 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4709 ms`
- Parsed summary: `546 passed, 20 deselected, 4 warnings in 3.27s`
- Counters: passed=546, total=546, failed=0, skipped=0, warnings=4, coverage=77.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:08:40 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 39%]
........................................................................ [ 52%]
........................................................................ [ 65%]
........................................................................ [ 79%]
........................................................................ [ 92%]
..........................................          
```

### Package tests: lexigram-web

- Scope: `lexigram-web/tests`
- Command: `uv run pytest lexigram-web/tests -q -m not integration --cov=lexigram.web`
- Status: **PASS**
- Exit code: `0`
- Duration: `13353 ms`
- Parsed summary: `1422 passed, 7 skipped, 7 deselected, 6 warnings in 11.49s`
- Counters: passed=1422, total=1429, failed=0, skipped=7, warnings=6, coverage=81.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:08:45 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
sss..................................................................... [  5%]
........................................................................ [ 10%]
........................................................................ [ 15%]
........................................................................ [ 20%]
.................................s...................................... [ 25%]
........................................................................ [ 30%]
......................................................................s. [ 35%]
....................................................
```

### Package tests: lexigram-webhook

- Scope: `lexigram-webhook/tests`
- Command: `uv run pytest lexigram-webhook/tests -q -m not integration --cov=lexigram.webhook`
- Status: **PASS**
- Exit code: `0`
- Duration: `2852 ms`
- Parsed summary: `334 passed, 4 warnings in 1.44s`
- Counters: passed=334, total=334, failed=0, skipped=0, warnings=4, coverage=86.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:08:58 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `14117 ms`
- Parsed summary: `556 passed, 23 deselected, 4 warnings in 12.69s`
- Counters: passed=556, total=556, failed=0, skipped=0, warnings=4, coverage=70.0%
- Example failures: none
- Output snippet:

```text
2026-08-19 03:09:01 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 12%]
........................................................................ [ 25%]
........................................................................ [ 38%]
........................................................................ [ 51%]
........................................................................ [ 64%]
........................................................................ [ 77%]
........................................................................ [ 90%]
....................................................
```

