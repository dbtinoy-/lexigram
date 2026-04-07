# AUDIT_TESTS.md — Lexigram Framework Targeted Test Execution Audit

> **Source**: Live pytest execution evidence for targeted scopes, with `tests/` directory scanning as supporting context.

---

## Summary

- Total passed tests: 24374
- Total failed tests: 0
- Total skipped tests: 346
- Total warnings: 288
- Aggregate code coverage: 69.70%

- Representative commands run: 44
- Commands passing: 34
- Commands failing: 10
- Packages with tests: 43
- Test files: 2308
- Test functions: 24688

### Exit Codes Reference

- **`0`**: Success — All tests passed and code coverage met the configured threshold.
- **`1`**: Failure — Functional tests failed OR code coverage fell below the package's `--cov-fail-under` threshold.
- **`timeout`**: The test command exceeded the execution time limit (120s) and was automatically terminated.

## Execution Evidence

| Label | Code Coverage | Pass/Total | Failed | Skipped | Warnings | Exit Code | Duration |
|-------|---------------|------------|---------|----------|------|-----------|----------|
| Lexigram framework core tests | 60.0% | 2889/2899 | 0 | 10 | 9 | 1 | 27500 ms |
| Package tests: lexigram-contracts | 46.0% | 1363/1363 | 0 | 0 | 5 | 1 | 8242 ms |
| Package tests: lexigram-admin | 68.0% | 3528/3570 | 0 | 42 | 69 | 0 | 51000 ms |
| Package tests: lexigram-ai-agents | 81.0% | 322/322 | 0 | 0 | 4 | 0 | 5832 ms |
| Package tests: lexigram-ai-evaluation | 95.0% | 98/98 | 0 | 0 | 4 | 0 | 1727 ms |
| Package tests: lexigram-ai-feedback | 92.0% | 180/180 | 0 | 0 | 4 | 0 | 2017 ms |
| Package tests: lexigram-ai-governance | 84.0% | 244/244 | 0 | 0 | 4 | 0 | 2574 ms |
| Package tests: lexigram-ai-guard | 81.0% | 237/237 | 0 | 0 | 7 | 0 | 2185 ms |
| Package tests: lexigram-ai-llm | 68.0% | 849/872 | 0 | 23 | 4 | 0 | 31514 ms |
| Package tests: lexigram-ai-mcp | 48.0% | 368/368 | 0 | 0 | 4 | 0 | 3708 ms |
| Package tests: lexigram-ai-memory | 76.0% | 234/234 | 0 | 0 | 4 | 0 | 2551 ms |
| Package tests: lexigram-ai-observability | 79.0% | 234/234 | 0 | 0 | 4 | 0 | 2685 ms |
| Package tests: lexigram-ai-prompt | 86.0% | 272/272 | 0 | 0 | 4 | 0 | 2537 ms |
| Package tests: lexigram-ai-rag | 62.0% | 512/519 | 0 | 7 | 4 | 0 | 7497 ms |
| Package tests: lexigram-ai-session | 90.0% | 203/203 | 0 | 0 | 4 | 0 | 2497 ms |
| Package tests: lexigram-ai-skills | 78.0% | 257/257 | 0 | 0 | 6 | 0 | 2693 ms |
| Package tests: lexigram-ai-workers | 87.0% | 321/321 | 0 | 0 | 4 | 0 | 4002 ms |
| Package tests: lexigram-ai | 45.0% | 457/468 | 0 | 11 | 4 | 1 | 15210 ms |
| Package tests: lexigram-audit | 82.0% | 233/244 | 0 | 11 | 4 | 0 | 2195 ms |
| Package tests: lexigram-auth | 66.0% | 554/559 | 0 | 5 | 6 | 1 | 22002 ms |
| Package tests: lexigram-cache | 70.0% | 757/782 | 0 | 25 | 12 | 1 | 10893 ms |
| Package tests: lexigram-cli | 51.0% | 337/338 | 0 | 1 | 4 | 0 | 13537 ms |
| Package tests: lexigram-events | 61.0% | 897/917 | 0 | 20 | 5 | 1 | 12004 ms |
| Package tests: lexigram-features | 76.0% | 232/238 | 0 | 6 | 17 | 0 | 3670 ms |
| Package tests: lexigram-graph | 68.0% | 202/203 | 0 | 1 | 4 | 0 | 1948 ms |
| Package tests: lexigram-graphql | 55.0% | 311/315 | 0 | 4 | 4 | 1 | 4261 ms |
| Package tests: lexigram-http | 71.0% | 388/388 | 0 | 0 | 4 | 0 | 2441 ms |
| Package tests: lexigram-monitor | 81.0% | 275/281 | 0 | 6 | 5 | 0 | 8191 ms |
| Package tests: lexigram-nosql | 59.0% | 261/262 | 0 | 1 | 4 | 0 | 2622 ms |
| Package tests: lexigram-notification | 83.0% | 242/242 | 0 | 0 | 4 | 0 | 4164 ms |
| Package tests: lexigram-queue | 87.0% | 208/216 | 0 | 8 | 5 | 0 | 3898 ms |
| Package tests: lexigram-resilience | 72.0% | 320/320 | 0 | 0 | 4 | 0 | 20654 ms |
| Package tests: lexigram-search | 42.0% | 425/435 | 0 | 10 | 4 | 0 | 3027 ms |
| Package tests: lexigram-sql (unit only, no external DB) | 55.0% | 1042/1132 | 0 | 90 | 6 | 1 | 18876 ms |
| Package tests: lexigram-storage | 63.0% | 455/465 | 0 | 10 | 4 | 0 | 6801 ms |
| Package tests: lexigram-tasks | 67.0% | 418/439 | 0 | 21 | 4 | 1 | 8886 ms |
| Package tests: lexigram-tenancy | 72.0% | 250/250 | 0 | 0 | 4 | 0 | 2436 ms |
| Package tests: lexigram-testing | 18.0% | 448/464 | 0 | 16 | 4 | 1 | 7913 ms |
| Package tests: lexigram-ui | 71.0% | 863/863 | 0 | 0 | 14 | 0 | 4973 ms |
| Package tests: lexigram-vector | 75.0% | 477/488 | 0 | 11 | 4 | 0 | 4477 ms |
| Package tests: lexigram-web | 80.0% | 1340/1347 | 0 | 7 | 6 | 0 | 13088 ms |
| Package tests: lexigram-webhook | 96.0% | 327/327 | 0 | 0 | 4 | 0 | 2483 ms |
| Package tests: lexigram-workflow | 71.0% | 515/515 | 0 | 0 | 4 | 0 | 13660 ms |
| Scripts audit smoke | 49.0% | 29/29 | 0 | 0 | 0 | 0 | 1891 ms |

### Execution Scope Notes

- `framework-core`: real test execution for `lexigram/tests`.
- `package`: real test execution for `<package>/tests` across every discovered Lexigram package with tests.
- `scripts-audit`: real test execution for `tests/scripts`.

### Lexigram framework core tests

- Scope: `lexigram/tests`
- Command: `uv run pytest lexigram/tests -q --cov=lexigram`
- Status: **FAIL**
- Exit code: `1`
- Duration: `27500 ms`
- Parsed summary: `2889 passed, 10 skipped, 9 warnings in 24.54s`
- Counters: passed=2889, total=2899, failed=0, skipped=10, warnings=9, coverage=60.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:02:52 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `8242 ms`
- Parsed summary: `1363 passed, 5 warnings in 6.80s`
- Counters: passed=1363, total=1363, failed=0, skipped=0, warnings=5, coverage=46.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:03:19 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  5%]
........................................................................ [ 10%]
........................................................................ [ 15%]
........................................................................ [ 21%]
........................................................................ [ 26%]
........................................................................ [ 31%]
........................................................................ [ 36%]
....................................................
```

### Package tests: lexigram-admin

- Scope: `lexigram-admin/tests`
- Command: `uv run pytest lexigram-admin/tests -q --cov=lexigram.admin`
- Status: **PASS**
- Exit code: `0`
- Duration: `51000 ms`
- Parsed summary: `3528 passed, 42 skipped, 69 warnings in 48.74s`
- Counters: passed=3528, total=3570, failed=0, skipped=42, warnings=69, coverage=68.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:03:28 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
ss....ss................................................................ [  2%]
.................................................s...................... [  4%]
.........ss............................................................. [  6%]
........................................................................ [  8%]
........................................................................ [ 10%]
........................................................................ [ 12%]
........................................................................ [ 14%]
....................................................
```

### Package tests: lexigram-ai-agents

- Scope: `lexigram-ai-agents/tests`
- Command: `uv run pytest lexigram-ai-agents/tests -q --cov=lexigram.ai.agents`
- Status: **PASS**
- Exit code: `0`
- Duration: `5832 ms`
- Parsed summary: `322 passed, 4 warnings in 4.44s`
- Counters: passed=322, total=322, failed=0, skipped=0, warnings=4, coverage=81.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:04:19 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 22%]
........................................................................ [ 44%]
........................................................................ [ 67%]
........................................................................ [ 89%]
..................................                                       [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/
```

### Package tests: lexigram-ai-evaluation

- Scope: `lexigram-ai-evaluation/tests`
- Command: `uv run pytest lexigram-ai-evaluation/tests -q --cov=lexigram.ai.evaluation`
- Status: **PASS**
- Exit code: `0`
- Duration: `1727 ms`
- Parsed summary: `98 passed, 4 warnings in 0.52s`
- Counters: passed=98, total=98, failed=0, skipped=0, warnings=4, coverage=95.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:04:24 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 73%]
..........................                                               [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtures.core
    self.import_plugin(import_spec)

.venv/lib/python3.13/site-packages/
```

### Package tests: lexigram-ai-feedback

- Scope: `lexigram-ai-feedback/tests`
- Command: `uv run pytest lexigram-ai-feedback/tests -q --cov=lexigram.ai.feedback`
- Status: **PASS**
- Exit code: `0`
- Duration: `2017 ms`
- Parsed summary: `180 passed, 4 warnings in 0.79s`
- Counters: passed=180, total=180, failed=0, skipped=0, warnings=4, coverage=92.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:04:26 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 40%]
........................................................................ [ 80%]
....................................                                     [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewriteWarning: Module already imported so cannot be rewritten; lexigram.testing.fixtur
```

### Package tests: lexigram-ai-governance

- Scope: `lexigram-ai-governance/tests`
- Command: `uv run pytest lexigram-ai-governance/tests -q --cov=lexigram.ai.governance`
- Status: **PASS**
- Exit code: `0`
- Duration: `2574 ms`
- Parsed summary: `244 passed, 4 warnings in 1.34s`
- Counters: passed=244, total=244, failed=0, skipped=0, warnings=4, coverage=84.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:04:28 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 29%]
........................................................................ [ 59%]
........................................................................ [ 88%]
............................                                             [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-ai-guard

- Scope: `lexigram-ai-guard/tests`
- Command: `uv run pytest lexigram-ai-guard/tests -q --cov=lexigram.ai.guard`
- Status: **PASS**
- Exit code: `0`
- Duration: `2185 ms`
- Parsed summary: `237 passed, 7 warnings in 0.97s`
- Counters: passed=237, total=237, failed=0, skipped=0, warnings=7, coverage=81.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:04:31 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 30%]
........................................................................ [ 60%]
........................................................................ [ 91%]
.....................                                                    [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-ai-llm

- Scope: `lexigram-ai-llm/tests`
- Command: `uv run pytest lexigram-ai-llm/tests -q --cov=lexigram.ai.llm`
- Status: **PASS**
- Exit code: `0`
- Duration: `31514 ms`
- Parsed summary: `849 passed, 23 skipped, 4 warnings in 29.77s`
- Counters: passed=849, total=872, failed=0, skipped=23, warnings=4, coverage=68.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:04:33 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `3708 ms`
- Parsed summary: `368 passed, 4 warnings in 2.39s`
- Counters: passed=368, total=368, failed=0, skipped=0, warnings=4, coverage=48.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:05:04 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2551 ms`
- Parsed summary: `234 passed, 4 warnings in 1.29s`
- Counters: passed=234, total=234, failed=0, skipped=0, warnings=4, coverage=76.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:05:08 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2685 ms`
- Parsed summary: `234 passed, 4 warnings in 1.43s`
- Counters: passed=234, total=234, failed=0, skipped=0, warnings=4, coverage=79.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:05:11 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 30%]
........................................................................ [ 61%]
........................................................................ [ 92%]
..................                                                       [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-ai-prompt

- Scope: `lexigram-ai-prompt/tests`
- Command: `uv run pytest lexigram-ai-prompt/tests -q --cov=lexigram.ai.prompt`
- Status: **PASS**
- Exit code: `0`
- Duration: `2537 ms`
- Parsed summary: `272 passed, 4 warnings in 1.27s`
- Counters: passed=272, total=272, failed=0, skipped=0, warnings=4, coverage=86.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:05:13 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 26%]
........................................................................ [ 52%]
........................................................................ [ 79%]
........................................................                 [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-ai-rag

- Scope: `lexigram-ai-rag/tests`
- Command: `uv run pytest lexigram-ai-rag/tests -q --cov=lexigram.ai.rag`
- Status: **PASS**
- Exit code: `0`
- Duration: `7497 ms`
- Parsed summary: `512 passed, 7 skipped, 4 warnings in 6.04s`
- Counters: passed=512, total=519, failed=0, skipped=7, warnings=4, coverage=62.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:05:16 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2497 ms`
- Parsed summary: `203 passed, 4 warnings in 1.16s`
- Counters: passed=203, total=203, failed=0, skipped=0, warnings=4, coverage=90.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:05:23 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2693 ms`
- Parsed summary: `257 passed, 6 warnings in 1.45s`
- Counters: passed=257, total=257, failed=0, skipped=0, warnings=6, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:05:26 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4002 ms`
- Parsed summary: `321 passed, 4 warnings in 2.74s`
- Counters: passed=321, total=321, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:05:29 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `15210 ms`
- Parsed summary: `457 passed, 11 skipped, 4 warnings in 13.70s`
- Counters: passed=457, total=468, failed=0, skipped=11, warnings=4, coverage=45.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:05:33 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2195 ms`
- Parsed summary: `233 passed, 11 skipped, 4 warnings in 0.96s`
- Counters: passed=233, total=244, failed=0, skipped=11, warnings=4, coverage=82.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:05:48 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `22002 ms`
- Parsed summary: `554 passed, 5 skipped, 6 warnings in 20.49s`
- Counters: passed=554, total=559, failed=0, skipped=5, warnings=6, coverage=66.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:05:50 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `10893 ms`
- Parsed summary: `757 passed, 25 skipped, 12 warnings in 9.23s`
- Counters: passed=757, total=782, failed=0, skipped=25, warnings=12, coverage=70.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:06:12 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.........ssssssssssss................................................... [  9%]
......................................ss................................ [ 18%]
........................................................................ [ 27%]
..........................ssssssssss.................................... [ 36%]
........................................................................ [ 46%]
........................................................................ [ 55%]
........................................................................ [ 64%]
....................................................
```

### Package tests: lexigram-cli

- Scope: `lexigram-cli/tests`
- Command: `uv run pytest lexigram-cli/tests -q --cov=lexigram.cli`
- Status: **PASS**
- Exit code: `0`
- Duration: `13537 ms`
- Parsed summary: `337 passed, 1 skipped, 4 warnings in 11.89s`
- Counters: passed=337, total=338, failed=0, skipped=1, warnings=4, coverage=51.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:06:23 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `12004 ms`
- Parsed summary: `897 passed, 20 skipped, 5 warnings in 10.57s`
- Counters: passed=897, total=917, failed=0, skipped=20, warnings=5, coverage=61.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:06:36 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `3670 ms`
- Parsed summary: `232 passed, 6 skipped, 17 warnings in 2.36s`
- Counters: passed=232, total=238, failed=0, skipped=6, warnings=17, coverage=76.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:06:48 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `1948 ms`
- Parsed summary: `202 passed, 1 skipped, 4 warnings in 0.74s`
- Counters: passed=202, total=203, failed=0, skipped=1, warnings=4, coverage=68.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:06:52 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4261 ms`
- Parsed summary: `311 passed, 4 skipped, 4 warnings in 2.69s`
- Counters: passed=311, total=315, failed=0, skipped=4, warnings=4, coverage=55.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:06:54 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2441 ms`
- Parsed summary: `388 passed, 4 warnings in 1.16s`
- Counters: passed=388, total=388, failed=0, skipped=0, warnings=4, coverage=71.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:06:58 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `8191 ms`
- Parsed summary: `275 passed, 6 skipped, 5 warnings in 6.87s`
- Counters: passed=275, total=281, failed=0, skipped=6, warnings=5, coverage=81.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:07:01 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2622 ms`
- Parsed summary: `261 passed, 1 skipped, 4 warnings in 1.39s`
- Counters: passed=261, total=262, failed=0, skipped=1, warnings=4, coverage=59.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:07:09 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4164 ms`
- Parsed summary: `242 passed, 4 warnings in 2.82s`
- Counters: passed=242, total=242, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:07:12 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `3898 ms`
- Parsed summary: `208 passed, 8 skipped, 5 warnings in 2.60s`
- Counters: passed=208, total=216, failed=0, skipped=8, warnings=5, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:07:16 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `20654 ms`
- Parsed summary: `320 passed, 4 warnings in 19.40s`
- Counters: passed=320, total=320, failed=0, skipped=0, warnings=4, coverage=72.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:07:20 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `3027 ms`
- Parsed summary: `425 passed, 10 skipped, 4 warnings in 1.74s`
- Counters: passed=425, total=435, failed=0, skipped=10, warnings=4, coverage=42.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:07:40 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `18876 ms`
- Parsed summary: `1042 passed, 90 skipped, 6 warnings in 17.14s`
- Counters: passed=1042, total=1132, failed=0, skipped=90, warnings=6, coverage=55.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:07:43 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `6801 ms`
- Parsed summary: `455 passed, 10 skipped, 4 warnings in 5.49s`
- Counters: passed=455, total=465, failed=0, skipped=10, warnings=4, coverage=63.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:08:02 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `8886 ms`
- Parsed summary: `418 passed, 21 skipped, 4 warnings in 7.38s`
- Counters: passed=418, total=439, failed=0, skipped=21, warnings=4, coverage=67.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:08:09 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2436 ms`
- Parsed summary: `250 passed, 4 warnings in 1.19s`
- Counters: passed=250, total=250, failed=0, skipped=0, warnings=4, coverage=72.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:08:18 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `7913 ms`
- Parsed summary: `448 passed, 16 skipped, 4 warnings in 6.51s`
- Counters: passed=448, total=464, failed=0, skipped=16, warnings=4, coverage=18.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:08:20 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
...........s..................s......................................... [ 15%]
........................................................................ [ 31%]
........................................................................ [ 46%]
........................................................................ [ 62%]
.........................ssssssssssssss................................. [ 77%]
........................................................................ [ 93%]
................................
ERROR: Coverage failure: total of 18 is less than fail-under=80
                                   
```

### Package tests: lexigram-ui

- Scope: `lexigram-ui/tests`
- Command: `uv run pytest lexigram-ui/tests -q --cov=lexigram.ui`
- Status: **PASS**
- Exit code: `0`
- Duration: `4973 ms`
- Parsed summary: `863 passed, 14 warnings in 3.63s`
- Counters: passed=863, total=863, failed=0, skipped=0, warnings=14, coverage=71.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:08:28 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  8%]
........................................................................ [ 16%]
........................................................................ [ 25%]
........................................................................ [ 33%]
........................................................................ [ 41%]
........................................................................ [ 50%]
........................................................................ [ 58%]
....................................................
```

### Package tests: lexigram-vector

- Scope: `lexigram-vector/tests`
- Command: `uv run pytest lexigram-vector/tests -q --cov=lexigram.vector`
- Status: **PASS**
- Exit code: `0`
- Duration: `4477 ms`
- Parsed summary: `477 passed, 11 skipped, 4 warnings in 3.11s`
- Counters: passed=477, total=488, failed=0, skipped=11, warnings=4, coverage=75.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:08:33 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `13088 ms`
- Parsed summary: `1340 passed, 7 skipped, 6 warnings in 11.39s`
- Counters: passed=1340, total=1347, failed=0, skipped=7, warnings=6, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:08:38 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2483 ms`
- Parsed summary: `327 passed, 4 warnings in 1.20s`
- Counters: passed=327, total=327, failed=0, skipped=0, warnings=4, coverage=96.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:08:51 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `13660 ms`
- Parsed summary: `515 passed, 4 warnings in 12.39s`
- Counters: passed=515, total=515, failed=0, skipped=0, warnings=4, coverage=71.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:08:53 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 27%]
........................................................................ [ 41%]
........................................................................ [ 55%]
........................................................................ [ 69%]
........................................................................ [ 83%]
........................................................................ [ 97%]
...........                                         
```

### Scripts audit smoke

- Scope: `tests/scripts`
- Command: `uv run pytest tests/scripts -q --cov=scripts`
- Status: **PASS**
- Exit code: `0`
- Duration: `1891 ms`
- Parsed summary: `29 passed in 0.59s`
- Counters: passed=29, total=29, failed=0, skipped=0, warnings=0, coverage=49.0%
- Example failures: none
- Output snippet:

```text
2026-05-30 00:09:07 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.............................                                            [100%]
================================ tests coverage ================================
_______________ coverage: platform linux, python 3.13.7-final-0 ________________

Name                                                 Stmts   Miss  Cover
------------------------------------------------------------------------
scripts/__init__.py                                      3      0   100%
scripts/audit/__init__.py                                4      0   100%
scripts/audit/base.py                                   89     89     0%
scri
```

