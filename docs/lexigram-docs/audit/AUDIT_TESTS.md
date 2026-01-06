# AUDIT_TESTS.md — Lexigram Framework Targeted Test Execution Audit

> **Source**: Live pytest execution evidence for targeted scopes, with `tests/` directory scanning as supporting context.

---

## Summary

- Total passed tests: 19104
- Total failed tests: 0
- Total skipped tests: 304
- Total warnings: 186
- Aggregate code coverage: 68.51%

- Representative commands run: 37
- Commands passing: 27
- Commands failing: 10
- Packages with tests: 37
- Test files: 1862
- Test functions: 19568

### Exit Codes Reference

- **`0`**: Success — All tests passed and code coverage met the configured threshold.
- **`1`**: Failure — Functional tests failed OR code coverage fell below the package's `--cov-fail-under` threshold.
- **`timeout`**: The test command exceeded the execution time limit (120s) and was automatically terminated.

## Execution Evidence

| Label | Code Coverage | Pass/Total | Failed | Skipped | Warnings | Exit Code | Duration |
|-------|---------------|------------|---------|----------|------|-----------|----------|
| Lexigram framework core tests | 60.0% | 2889/2899 | 0 | 10 | 9 | 1 | 27471 ms |
| Package tests: lexigram-contracts | 47.0% | 1361/1361 | 0 | 0 | 5 | 1 | 8356 ms |
| Package tests: lexigram-ai-agents | 81.0% | 322/322 | 0 | 0 | 4 | 0 | 5879 ms |
| Package tests: lexigram-ai-feedback | 92.0% | 180/180 | 0 | 0 | 4 | 0 | 2047 ms |
| Package tests: lexigram-ai-llm | 68.0% | 849/872 | 0 | 23 | 4 | 0 | 31600 ms |
| Package tests: lexigram-ai-mcp | 48.0% | 368/368 | 0 | 0 | 4 | 0 | 3714 ms |
| Package tests: lexigram-ai-memory | 76.0% | 234/234 | 0 | 0 | 4 | 0 | 2587 ms |
| Package tests: lexigram-ai-observability | 79.0% | 234/234 | 0 | 0 | 4 | 0 | 2712 ms |
| Package tests: lexigram-ai-rag | 62.0% | 512/519 | 0 | 7 | 4 | 0 | 7539 ms |
| Package tests: lexigram-ai-session | 90.0% | 203/203 | 0 | 0 | 4 | 0 | 2575 ms |
| Package tests: lexigram-ai-skills | 78.0% | 257/257 | 0 | 0 | 6 | 0 | 2728 ms |
| Package tests: lexigram-ai-workers | 87.0% | 321/321 | 0 | 0 | 4 | 0 | 4068 ms |
| Package tests: lexigram-ai | 45.0% | 457/468 | 0 | 11 | 4 | 1 | 15367 ms |
| Package tests: lexigram-audit | 82.0% | 233/244 | 0 | 11 | 4 | 0 | 2247 ms |
| Package tests: lexigram-auth | 66.0% | 554/559 | 0 | 5 | 6 | 1 | 22038 ms |
| Package tests: lexigram-cache | 71.0% | 760/785 | 0 | 25 | 12 | 1 | 10909 ms |
| Package tests: lexigram-cli | 51.0% | 337/338 | 0 | 1 | 4 | 0 | 11209 ms |
| Package tests: lexigram-events | 61.0% | 897/917 | 0 | 20 | 5 | 1 | 12070 ms |
| Package tests: lexigram-features | 76.0% | 232/238 | 0 | 6 | 17 | 0 | 3731 ms |
| Package tests: lexigram-graph | 68.0% | 202/203 | 0 | 1 | 4 | 0 | 1975 ms |
| Package tests: lexigram-graphql | 55.0% | 311/315 | 0 | 4 | 4 | 1 | 4288 ms |
| Package tests: lexigram-http | 71.0% | 388/388 | 0 | 0 | 4 | 0 | 2453 ms |
| Package tests: lexigram-monitor | 81.0% | 275/281 | 0 | 6 | 5 | 0 | 8244 ms |
| Package tests: lexigram-nosql | 59.0% | 261/262 | 0 | 1 | 4 | 0 | 2705 ms |
| Package tests: lexigram-notification | 83.0% | 242/242 | 0 | 0 | 4 | 0 | 3986 ms |
| Package tests: lexigram-queue | 87.0% | 208/216 | 0 | 8 | 5 | 0 | 3939 ms |
| Package tests: lexigram-resilience | 72.0% | 320/320 | 0 | 0 | 4 | 0 | 20921 ms |
| Package tests: lexigram-search | 42.0% | 425/435 | 0 | 10 | 4 | 0 | 3110 ms |
| Package tests: lexigram-sql (unit only, no external DB) | 55.0% | 1042/1132 | 0 | 90 | 6 | 1 | 19033 ms |
| Package tests: lexigram-storage | 63.0% | 455/465 | 0 | 10 | 4 | 0 | 6858 ms |
| Package tests: lexigram-tasks | 67.0% | 418/439 | 0 | 21 | 4 | 1 | 8904 ms |
| Package tests: lexigram-tenancy | 72.0% | 250/250 | 0 | 0 | 4 | 0 | 2495 ms |
| Package tests: lexigram-testing | 18.0% | 448/464 | 0 | 16 | 4 | 1 | 8010 ms |
| Package tests: lexigram-vector | 75.0% | 477/488 | 0 | 11 | 4 | 0 | 4583 ms |
| Package tests: lexigram-web | 80.0% | 1340/1347 | 0 | 7 | 6 | 0 | 13372 ms |
| Package tests: lexigram-webhook | 96.0% | 327/327 | 0 | 0 | 4 | 0 | 2567 ms |
| Package tests: lexigram-workflow | 71.0% | 515/515 | 0 | 0 | 4 | 0 | 13738 ms |

### Execution Scope Notes

- `framework-core`: real test execution for `lexigram/tests`.
- `package`: real test execution for `<package>/tests` across every discovered Lexigram package with tests.
### Lexigram framework core tests

- Scope: `lexigram/tests`
- Command: `uv run pytest lexigram/tests -q --cov=lexigram`
- Status: **FAIL**
- Exit code: `1`
- Duration: `27471 ms`
- Parsed summary: `2889 passed, 10 skipped, 9 warnings in 24.68s`
- Counters: passed=2889, total=2899, failed=0, skipped=10, warnings=9, coverage=60.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:35:26 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  2%]
..................ssss....s............................................. [  4%]
........................................................................ [  7%]
........................................................................ [  9%]
........................................................................ [ 12%]
........................................................................ [ 14%]
........................................................................ [ 17%]
....................................................
```

### Package tests: lexigram-contracts

- Scope: `lexigram-contracts/tests`
- Command: `uv run pytest lexigram-contracts/tests -q --cov=lexigram.contracts`
- Status: **FAIL**
- Exit code: `1`
- Duration: `8356 ms`
- Parsed summary: `1361 passed, 5 warnings in 6.86s`
- Counters: passed=1361, total=1361, failed=0, skipped=0, warnings=5, coverage=47.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:35:53 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  5%]
........................................................................ [ 10%]
........................................................................ [ 15%]
........................................................................ [ 21%]
........................................................................ [ 26%]
........................................................................ [ 31%]
........................................................................ [ 37%]
....................................................
```

### Package tests: lexigram-ai-agents

- Scope: `lexigram-ai-agents/tests`
- Command: `uv run pytest lexigram-ai-agents/tests -q --cov=lexigram.ai.agents`
- Status: **PASS**
- Exit code: `0`
- Duration: `5879 ms`
- Parsed summary: `322 passed, 4 warnings in 4.48s`
- Counters: passed=322, total=322, failed=0, skipped=0, warnings=4, coverage=81.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:36:01 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 22%]
........................................................................ [ 44%]
........................................................................ [ 67%]
........................................................................ [ 89%]
..................................                                       [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/
```

### Package tests: lexigram-ai-feedback

- Scope: `lexigram-ai-feedback/tests`
- Command: `uv run pytest lexigram-ai-feedback/tests -q --cov=lexigram.ai.feedback`
- Status: **PASS**
- Exit code: `0`
- Duration: `2047 ms`
- Parsed summary: `180 passed, 4 warnings in 0.81s`
- Counters: passed=180, total=180, failed=0, skipped=0, warnings=4, coverage=92.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:36:07 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 40%]
........................................................................ [ 80%]
....................................                                     [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtur
```

### Package tests: lexigram-ai-llm

- Scope: `lexigram-ai-llm/tests`
- Command: `uv run pytest lexigram-ai-llm/tests -q --cov=lexigram.ai.llm`
- Status: **PASS**
- Exit code: `0`
- Duration: `31600 ms`
- Parsed summary: `849 passed, 23 skipped, 4 warnings in 29.80s`
- Counters: passed=849, total=872, failed=0, skipped=23, warnings=4, coverage=68.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:36:09 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.................ssssssssssssssssss..................................... [  8%]
........................................................................ [ 16%]
........................................................................ [ 24%]
..........................ssss.......................................... [ 33%]
........................................................................ [ 41%]
........................................................................ [ 49%]
........................................................................ [ 57%]
....................................................
```

### Package tests: lexigram-ai-mcp

- Scope: `lexigram-ai-mcp/tests`
- Command: `uv run pytest lexigram-ai-mcp/tests -q --cov=lexigram.ai.mcp`
- Status: **PASS**
- Exit code: `0`
- Duration: `3714 ms`
- Parsed summary: `368 passed, 4 warnings in 2.38s`
- Counters: passed=368, total=368, failed=0, skipped=0, warnings=4, coverage=48.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:36:41 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 19%]
........................................................................ [ 39%]
........................................................................ [ 58%]
........................................................................ [ 78%]
........................................................................ [ 97%]
........                                                                 [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/_
```

### Package tests: lexigram-ai-memory

- Scope: `lexigram-ai-memory/tests`
- Command: `uv run pytest lexigram-ai-memory/tests -q --cov=lexigram.ai.memory`
- Status: **PASS**
- Exit code: `0`
- Duration: `2587 ms`
- Parsed summary: `234 passed, 4 warnings in 1.31s`
- Counters: passed=234, total=234, failed=0, skipped=0, warnings=4, coverage=76.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:36:45 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 30%]
........................................................................ [ 61%]
........................................................................ [ 92%]
..................                                                       [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-ai-observability

- Scope: `lexigram-ai-observability/tests`
- Command: `uv run pytest lexigram-ai-observability/tests -q --cov=lexigram.ai.observability`
- Status: **PASS**
- Exit code: `0`
- Duration: `2712 ms`
- Parsed summary: `234 passed, 4 warnings in 1.44s`
- Counters: passed=234, total=234, failed=0, skipped=0, warnings=4, coverage=79.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:36:47 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 30%]
........................................................................ [ 61%]
........................................................................ [ 92%]
..................                                                       [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-ai-rag

- Scope: `lexigram-ai-rag/tests`
- Command: `uv run pytest lexigram-ai-rag/tests -q --cov=lexigram.ai.rag`
- Status: **PASS**
- Exit code: `0`
- Duration: `7539 ms`
- Parsed summary: `512 passed, 7 skipped, 4 warnings in 6.08s`
- Counters: passed=512, total=519, failed=0, skipped=7, warnings=4, coverage=62.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:36:50 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
............................................................sss......... [ 13%]
..s..............ss..................................................... [ 27%]
..........................................................s............. [ 41%]
........................................................................ [ 55%]
........................................................................ [ 69%]
........................................................................ [ 83%]
........................................................................ [ 97%]
...............                                     
```

### Package tests: lexigram-ai-session

- Scope: `lexigram-ai-session/tests`
- Command: `uv run pytest lexigram-ai-session/tests -q --cov=lexigram.ai.session`
- Status: **PASS**
- Exit code: `0`
- Duration: `2575 ms`
- Parsed summary: `203 passed, 4 warnings in 1.20s`
- Counters: passed=203, total=203, failed=0, skipped=0, warnings=4, coverage=90.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:36:58 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 35%]
........................................................................ [ 70%]
...........................................................              [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtur
```

### Package tests: lexigram-ai-skills

- Scope: `lexigram-ai-skills/tests`
- Command: `uv run pytest lexigram-ai-skills/tests -q --cov=lexigram.ai.skills`
- Status: **PASS**
- Exit code: `0`
- Duration: `2728 ms`
- Parsed summary: `257 passed, 6 warnings in 1.45s`
- Counters: passed=257, total=257, failed=0, skipped=0, warnings=6, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:37:00 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 28%]
........................................................................ [ 56%]
........................................................................ [ 84%]
.........................................                                [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-ai-workers

- Scope: `lexigram-ai-workers/tests`
- Command: `uv run pytest lexigram-ai-workers/tests -q --cov=lexigram.ai.workers`
- Status: **PASS**
- Exit code: `0`
- Duration: `4068 ms`
- Parsed summary: `321 passed, 4 warnings in 2.75s`
- Counters: passed=321, total=321, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:37:03 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 22%]
........................................................................ [ 44%]
........................................................................ [ 67%]
........................................................................ [ 89%]
.................................                                        [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/
```

### Package tests: lexigram-ai

- Scope: `lexigram-ai/tests`
- Command: `uv run pytest lexigram-ai/tests -q --cov=lexigram.ai`
- Status: **FAIL**
- Exit code: `1`
- Duration: `15367 ms`
- Parsed summary: `457 passed, 11 skipped, 4 warnings in 13.84s`
- Counters: passed=457, total=468, failed=0, skipped=11, warnings=4, coverage=45.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:37:07 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
..................ss..s................................................. [ 15%]
........................................................................ [ 31%]
..................s.s................................................... [ 46%]
........................................................................ [ 62%]
........................................................................ [ 77%]
........................................................................ [ 93%]
..............................
ERROR: Coverage failure: total of 45 is less than fail-under=60
                                     
```

### Package tests: lexigram-audit

- Scope: `lexigram-audit/tests`
- Command: `uv run pytest lexigram-audit/tests -q --cov=lexigram.audit`
- Status: **PASS**
- Exit code: `0`
- Duration: `2247 ms`
- Parsed summary: `233 passed, 11 skipped, 4 warnings in 0.99s`
- Counters: passed=233, total=244, failed=0, skipped=11, warnings=4, coverage=82.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:37:22 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
ssssss......sssss....................................................... [ 29%]
........................................................................ [ 59%]
........................................................................ [ 88%]
............................                                             [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-auth

- Scope: `lexigram-auth/tests`
- Command: `uv run pytest lexigram-auth/tests -q --cov=lexigram.auth`
- Status: **FAIL**
- Exit code: `1`
- Duration: `22038 ms`
- Parsed summary: `554 passed, 5 skipped, 6 warnings in 20.45s`
- Counters: passed=554, total=559, failed=0, skipped=5, warnings=6, coverage=66.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:37:24 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
s....................................................................... [ 12%]
.........................ssss........................................... [ 25%]
........................................................................ [ 38%]
........................................................................ [ 51%]
........................................................................ [ 64%]
........................................................................ [ 77%]
........................................................................ [ 90%]
....................................................
```

### Package tests: lexigram-cache

- Scope: `lexigram-cache/tests`
- Command: `uv run pytest lexigram-cache/tests -q --cov=lexigram.cache`
- Status: **FAIL**
- Exit code: `1`
- Duration: `10909 ms`
- Parsed summary: `760 passed, 25 skipped, 12 warnings in 9.30s`
- Counters: passed=760, total=785, failed=0, skipped=25, warnings=12, coverage=71.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:37:47 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.........ssssssssssss................................................... [  9%]
......................................ss................................ [ 18%]
........................................................................ [ 27%]
..........................ssssssssss.................................... [ 36%]
........................................................................ [ 45%]
........................................................................ [ 55%]
........................................................................ [ 64%]
....................................................
```

### Package tests: lexigram-cli

- Scope: `lexigram-cli/tests`
- Command: `uv run pytest lexigram-cli/tests -q --cov=lexigram.cli`
- Status: **PASS**
- Exit code: `0`
- Duration: `11209 ms`
- Parsed summary: `337 passed, 1 skipped, 4 warnings in 9.52s`
- Counters: passed=337, total=338, failed=0, skipped=1, warnings=4, coverage=51.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:37:57 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 21%]
........................................................................ [ 42%]
........................................................................ [ 63%]
..........................s............................................. [ 85%]
..................................................                       [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/
```

### Package tests: lexigram-events

- Scope: `lexigram-events/tests`
- Command: `uv run pytest lexigram-events/tests -q --cov=lexigram.events`
- Status: **FAIL**
- Exit code: `1`
- Duration: `12070 ms`
- Parsed summary: `897 passed, 20 skipped, 5 warnings in 10.61s`
- Counters: passed=897, total=917, failed=0, skipped=20, warnings=5, coverage=61.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:38:09 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
...s......sssss......................................................... [  7%]
........................................................................ [ 15%]
........................................................................ [ 23%]
........................................................................ [ 31%]
........................................................................ [ 39%]
........................................................................ [ 47%]
........................................................................ [ 55%]
....................................................
```

### Package tests: lexigram-features

- Scope: `lexigram-features/tests`
- Command: `uv run pytest lexigram-features/tests -q --cov=lexigram.features`
- Status: **PASS**
- Exit code: `0`
- Duration: `3731 ms`
- Parsed summary: `232 passed, 6 skipped, 17 warnings in 2.37s`
- Counters: passed=232, total=238, failed=0, skipped=6, warnings=17, coverage=76.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:38:21 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........ssssss.......................................................... [ 30%]
........................................................................ [ 60%]
........................................................................ [ 90%]
......................                                                   [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-graph

- Scope: `lexigram-graph/tests`
- Command: `uv run pytest lexigram-graph/tests -q --cov=lexigram.graph`
- Status: **PASS**
- Exit code: `0`
- Duration: `1975 ms`
- Parsed summary: `202 passed, 1 skipped, 4 warnings in 0.75s`
- Counters: passed=202, total=203, failed=0, skipped=1, warnings=4, coverage=68.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:38:24 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 35%]
....................s................................................... [ 70%]
...........................................................              [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtur
```

### Package tests: lexigram-graphql

- Scope: `lexigram-graphql/tests`
- Command: `uv run pytest lexigram-graphql/tests -q --cov=lexigram.graphql`
- Status: **FAIL**
- Exit code: `1`
- Duration: `4288 ms`
- Parsed summary: `311 passed, 4 skipped, 4 warnings in 2.69s`
- Counters: passed=311, total=315, failed=0, skipped=4, warnings=4, coverage=55.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:38:26 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
s.................................................s..................... [ 22%]
.........................................s.....s........................ [ 45%]
........................................................................ [ 68%]
........................................................................ [ 91%]
...........................
ERROR: Coverage failure: total of 55 is less than fail-under=60
                                                                         [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pyt
```

### Package tests: lexigram-http

- Scope: `lexigram-http/tests`
- Command: `uv run pytest lexigram-http/tests -q --cov=lexigram.http`
- Status: **PASS**
- Exit code: `0`
- Duration: `2453 ms`
- Parsed summary: `388 passed, 4 warnings in 1.17s`
- Counters: passed=388, total=388, failed=0, skipped=0, warnings=4, coverage=71.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:38:31 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 18%]
........................................................................ [ 37%]
........................................................................ [ 55%]
........................................................................ [ 74%]
........................................................................ [ 92%]
............................                                             [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/_
```

### Package tests: lexigram-monitor

- Scope: `lexigram-monitor/tests`
- Command: `uv run pytest lexigram-monitor/tests -q --cov=lexigram.monitor`
- Status: **PASS**
- Exit code: `0`
- Duration: `8244 ms`
- Parsed summary: `275 passed, 6 skipped, 5 warnings in 6.90s`
- Counters: passed=275, total=281, failed=0, skipped=6, warnings=5, coverage=81.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:38:33 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.s...................................................................... [ 25%]
........................................sss.s........................... [ 51%]
........................................................................ [ 76%]
....................................s............................        [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-nosql

- Scope: `lexigram-nosql/tests`
- Command: `uv run pytest lexigram-nosql/tests -q --cov=lexigram.nosql`
- Status: **PASS**
- Exit code: `0`
- Duration: `2705 ms`
- Parsed summary: `261 passed, 1 skipped, 4 warnings in 1.41s`
- Counters: passed=261, total=262, failed=0, skipped=1, warnings=4, coverage=59.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:38:41 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
s....................................................................... [ 27%]
........................................................................ [ 54%]
........................................................................ [ 82%]
..............................................                           [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-notification

- Scope: `lexigram-notification/tests`
- Command: `uv run pytest lexigram-notification/tests -q --cov=lexigram.notification`
- Status: **PASS**
- Exit code: `0`
- Duration: `3986 ms`
- Parsed summary: `242 passed, 4 warnings in 2.62s`
- Counters: passed=242, total=242, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:38:44 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 29%]
........................................................................ [ 59%]
........................................................................ [ 89%]
..........................                                               [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-queue

- Scope: `lexigram-queue/tests`
- Command: `uv run pytest lexigram-queue/tests -q --cov=lexigram.queue`
- Status: **PASS**
- Exit code: `0`
- Duration: `3939 ms`
- Parsed summary: `208 passed, 8 skipped, 5 warnings in 2.61s`
- Counters: passed=208, total=216, failed=0, skipped=8, warnings=5, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:38:48 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
..ssssssss.............................................................. [ 33%]
........................................................................ [ 66%]
........................................................................ [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtur
```

### Package tests: lexigram-resilience

- Scope: `lexigram-resilience/tests`
- Command: `uv run pytest lexigram-resilience/tests -q --cov=lexigram.resilience`
- Status: **PASS**
- Exit code: `0`
- Duration: `20921 ms`
- Parsed summary: `320 passed, 4 warnings in 19.66s`
- Counters: passed=320, total=320, failed=0, skipped=0, warnings=4, coverage=72.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:38:52 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 22%]
........................................................................ [ 45%]
........................................................................ [ 67%]
........................................................................ [ 90%]
................................                                         [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/
```

### Package tests: lexigram-search

- Scope: `lexigram-search/tests`
- Command: `uv run pytest lexigram-search/tests -q --cov=lexigram.search`
- Status: **PASS**
- Exit code: `0`
- Duration: `3110 ms`
- Parsed summary: `425 passed, 10 skipped, 4 warnings in 1.77s`
- Counters: passed=425, total=435, failed=0, skipped=10, warnings=4, coverage=42.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:39:13 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
ssssss.................................................................. [ 16%]
........................................................................ [ 33%]
........................................................................ [ 50%]
........................................................................ [ 66%]
........................................................................ [ 83%]
.......................................................................  [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/_
```

### Package tests: lexigram-sql (unit only, no external DB)

- Scope: `lexigram-sql/tests`
- Command: `uv run pytest lexigram-sql/tests/unit -q --cov=lexigram.sql`
- Status: **FAIL**
- Exit code: `1`
- Duration: `19033 ms`
- Parsed summary: `1042 passed, 90 skipped, 6 warnings in 17.26s`
- Counters: passed=1042, total=1132, failed=0, skipped=90, warnings=6, coverage=55.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:39:16 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  6%]
.....................................................................ss. [ 12%]
........................................................................ [ 19%]
........................................................................ [ 25%]
........................................................................ [ 31%]
.............................................s...............sssssss.... [ 38%]
.ss..................................................................... [ 44%]
....................................................
```

### Package tests: lexigram-storage

- Scope: `lexigram-storage/tests`
- Command: `uv run pytest lexigram-storage/tests -q --cov=lexigram.storage`
- Status: **PASS**
- Exit code: `0`
- Duration: `6858 ms`
- Parsed summary: `455 passed, 10 skipped, 4 warnings in 5.51s`
- Counters: passed=455, total=465, failed=0, skipped=10, warnings=4, coverage=63.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:39:35 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
............................sssssss..................................... [ 15%]
........................................................................ [ 31%]
..................................................s..................... [ 46%]
........................................................................ [ 62%]
........................................................................ [ 77%]
........................................................................ [ 93%]
...............................s                                         [100%]
=============================== warnings summary ===
```

### Package tests: lexigram-tasks

- Scope: `lexigram-tasks/tests`
- Command: `uv run pytest lexigram-tasks/tests -q --cov=lexigram.tasks`
- Status: **FAIL**
- Exit code: `1`
- Duration: `8904 ms`
- Parsed summary: `418 passed, 21 skipped, 4 warnings in 7.44s`
- Counters: passed=418, total=439, failed=0, skipped=21, warnings=4, coverage=67.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:39:42 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
................................................................ssssss.. [ 16%]
........................................................................ [ 32%]
....................sssss............................................... [ 49%]
...................................................sssssssss............ [ 65%]
........................................................................ [ 82%]
...................................s.................................... [ 98%]
.......
ERROR: Coverage failure: total of 67 is less than fail-under=80
                                                            
```

### Package tests: lexigram-tenancy

- Scope: `lexigram-tenancy/tests`
- Command: `uv run pytest lexigram-tenancy/tests -q --cov=lexigram.tenancy`
- Status: **PASS**
- Exit code: `0`
- Duration: `2495 ms`
- Parsed summary: `250 passed, 4 warnings in 1.20s`
- Counters: passed=250, total=250, failed=0, skipped=0, warnings=4, coverage=72.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:39:51 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 28%]
........................................................................ [ 57%]
........................................................................ [ 86%]
..................................                                       [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-testing

- Scope: `lexigram-testing/tests`
- Command: `uv run pytest lexigram-testing/tests -q --cov=lexigram.testing`
- Status: **FAIL**
- Exit code: `1`
- Duration: `8010 ms`
- Parsed summary: `448 passed, 16 skipped, 4 warnings in 6.56s`
- Counters: passed=448, total=464, failed=0, skipped=16, warnings=4, coverage=18.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:39:53 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
...........s..................s......................................... [ 15%]
........................................................................ [ 31%]
........................................................................ [ 46%]
........................................................................ [ 62%]
.........................ssssssssssssss................................. [ 77%]
........................................................................ [ 93%]
................................
ERROR: Coverage failure: total of 18 is less than fail-under=80
                                   
```

### Package tests: lexigram-vector

- Scope: `lexigram-vector/tests`
- Command: `uv run pytest lexigram-vector/tests -q --cov=lexigram.vector`
- Status: **PASS**
- Exit code: `0`
- Duration: `4583 ms`
- Parsed summary: `477 passed, 11 skipped, 4 warnings in 3.19s`
- Counters: passed=477, total=488, failed=0, skipped=11, warnings=4, coverage=75.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:40:01 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
ss.sssssssss............................................................ [ 14%]
........................................................................ [ 29%]
........................................................................ [ 44%]
........................................................................ [ 59%]
........................................................................ [ 73%]
........................................................................ [ 88%]
........................................................                 [100%]
=============================== warnings summary ===
```

### Package tests: lexigram-web

- Scope: `lexigram-web/tests`
- Command: `uv run pytest lexigram-web/tests -q --cov=lexigram.web`
- Status: **PASS**
- Exit code: `0`
- Duration: `13372 ms`
- Parsed summary: `1340 passed, 7 skipped, 6 warnings in 11.55s`
- Counters: passed=1340, total=1347, failed=0, skipped=7, warnings=6, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:40:06 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
sss..................................................................... [  5%]
........................................................................ [ 10%]
........................................................................ [ 16%]
........................................................................ [ 21%]
......................s................................................. [ 26%]
........................................................................ [ 32%]
.........................................s.............................. [ 37%]
....................................................
```

### Package tests: lexigram-webhook

- Scope: `lexigram-webhook/tests`
- Command: `uv run pytest lexigram-webhook/tests -q --cov=lexigram.webhook`
- Status: **PASS**
- Exit code: `0`
- Duration: `2567 ms`
- Parsed summary: `327 passed, 4 warnings in 1.25s`
- Counters: passed=327, total=327, failed=0, skipped=0, warnings=4, coverage=96.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:40:19 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Command: `uv run pytest lexigram-workflow/tests -q --cov=lexigram.workflow`
- Status: **PASS**
- Exit code: `0`
- Duration: `13738 ms`
- Parsed summary: `515 passed, 4 warnings in 12.44s`
- Counters: passed=515, total=515, failed=0, skipped=0, warnings=4, coverage=71.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 21:40:22 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 27%]
........................................................................ [ 41%]
........................................................................ [ 55%]
........................................................................ [ 69%]
........................................................................ [ 83%]
........................................................................ [ 97%]
...........                                         
```

