# AUDIT_TESTS.md — Lexigram Framework Targeted Test Execution Audit

> **Source**: Live pytest execution evidence for targeted scopes, with `tests/` directory scanning as supporting context.

---

## Summary

- Total passed tests: 29606
- Total failed tests: 16
- Total skipped tests: 270
- Total warnings: 277
- Aggregate code coverage: 72.67%

- Representative commands run: 55
- Commands passing: 39
- Commands failing: 16
- Packages with tests: 54
- Test files: 2895
- Test functions: 29969

### Exit Codes Reference

- **`0`**: Success — All tests passed and code coverage met the configured threshold.
- **`1`**: Failure — Functional tests failed OR code coverage fell below the package's `--cov-fail-under` threshold.
- **`timeout`**: The test command exceeded the execution time limit (120s) and was automatically terminated.

## Execution Evidence

| Label | Code Coverage | Pass/Total | Failed | Skipped | Warnings | Exit Code | Duration |
|-------|---------------|------------|---------|----------|------|-----------|----------|
| Lexigram framework core tests | 58.0% | 2936/2941 | 0 | 5 | 1 | 1 | 28333 ms |
| Package tests: lexigram-contracts | 34.0% | 1732/1732 | 0 | 0 | 4 | 1 | 11866 ms |
| Package tests: lexigram-admin | 75.0% | 4282/4304 | 12 | 10 | 19 | 1 | 71525 ms |
| Package tests: lexigram-ai-agents | 84.0% | 379/379 | 0 | 0 | 4 | 0 | 6411 ms |
| Package tests: lexigram-ai-evaluation | 99.0% | 136/136 | 0 | 0 | 4 | 0 | 2142 ms |
| Package tests: lexigram-ai-feedback | 94.0% | 237/237 | 0 | 0 | 4 | 0 | 2448 ms |
| Package tests: lexigram-ai-governance | 86.0% | 506/506 | 0 | 0 | 15 | 0 | 4726 ms |
| Package tests: lexigram-ai-guard | 78.0% | 224/224 | 0 | 0 | 7 | 0 | 2675 ms |
| Package tests: lexigram-ai-llm | 71.0% | 945/965 | 0 | 20 | 4 | 0 | 33834 ms |
| Package tests: lexigram-ai-mcp | 50.0% | 368/368 | 0 | 0 | 4 | 0 | 4015 ms |
| Package tests: lexigram-ai-memory | 77.0% | 224/224 | 0 | 0 | 4 | 0 | 2795 ms |
| Package tests: lexigram-ai-observability | 86.0% | 232/232 | 0 | 0 | 4 | 0 | 2996 ms |
| Package tests: lexigram-ai-prompt | 87.0% | 297/297 | 0 | 0 | 4 | 0 | 3017 ms |
| Package tests: lexigram-ai-rag | 62.0% | 528/535 | 0 | 7 | 4 | 0 | 8015 ms |
| Package tests: lexigram-ai-relay-gateway | 94.0% | 526/526 | 0 | 0 | 4 | 0 | 4438 ms |
| Package tests: lexigram-ai-relay | 91.0% | 539/539 | 0 | 0 | 4 | 0 | 6945 ms |
| Package tests: lexigram-ai-session | 88.0% | 210/210 | 0 | 0 | 4 | 0 | 2925 ms |
| Package tests: lexigram-ai-skills | 78.0% | 263/263 | 0 | 0 | 6 | 0 | 2944 ms |
| Package tests: lexigram-ai-workers | 87.0% | 318/318 | 0 | 0 | 4 | 0 | 4365 ms |
| Package tests: lexigram-ai | 42.0% | 451/462 | 0 | 11 | 4 | 1 | 19722 ms |
| Package tests: lexigram-audit | 70.0% | 242/242 | 0 | 0 | 4 | 1 | 2736 ms |
| Package tests: lexigram-auth | 66.0% | 578/582 | 0 | 4 | 6 | 1 | 26758 ms |
| Package tests: lexigram-cache | 70.0% | 752/765 | 0 | 13 | 6 | 1 | 11262 ms |
| Package tests: lexigram-cli | 80.0% | 851/852 | 0 | 1 | 6 | 0 | 19898 ms |
| Package tests: lexigram-events | 61.0% | 916/931 | 0 | 15 | 5 | 1 | 13431 ms |
| Package tests: lexigram-features | 80.0% | 245/245 | 0 | 0 | 17 | 0 | 3845 ms |
| Package tests: lexigram-graph | 79.0% | 257/258 | 0 | 1 | 4 | 0 | 2636 ms |
| Package tests: lexigram-graphql | 72.0% | 502/506 | 0 | 4 | 4 | 0 | 5995 ms |
| Package tests: lexigram-http | 73.0% | 433/433 | 0 | 0 | 4 | 0 | 2891 ms |
| Package tests: lexigram-monitor | 81.0% | 310/315 | 0 | 5 | 4 | 0 | 9093 ms |
| Package tests: lexigram-multimedia-beat | 69.0% | 12/13 | 0 | 1 | 4 | 0 | 2296 ms |
| Package tests: lexigram-multimedia-image | 92.0% | 54/54 | 0 | 0 | 4 | 0 | 2601 ms |
| Package tests: lexigram-multimedia-interpolate | 83.0% | 22/22 | 0 | 0 | 4 | 0 | 2225 ms |
| Package tests: lexigram-multimedia-music | 78.0% | 36/36 | 0 | 0 | 4 | 0 | 2200 ms |
| Package tests: lexigram-multimedia-tts | 70.0% | 53/53 | 0 | 0 | 4 | 0 | 2482 ms |
| Package tests: lexigram-multimedia-upscale | 77.0% | 25/25 | 0 | 0 | 4 | 0 | 2246 ms |
| Package tests: lexigram-multimedia-video | 84.0% | 142/142 | 0 | 0 | 4 | 0 | 5669 ms |
| Package tests: lexigram-multimedia | 56.0% | 86/86 | 0 | 0 | 5 | 0 | 5519 ms |
| Package tests: lexigram-nosql | 91.0% | 416/416 | 0 | 0 | 4 | 0 | 3573 ms |
| Package tests: lexigram-notification | 83.0% | 278/279 | 1 | 0 | 4 | 1 | 6218 ms |
| Package tests: lexigram-queue | 82.0% | 205/206 | 1 | 0 | 4 | 1 | 4600 ms |
| Package tests: lexigram-resilience | 72.0% | 299/299 | 0 | 0 | 4 | 0 | 20595 ms |
| Package tests: lexigram-search | 65.0% | 771/774 | 0 | 3 | 4 | 0 | 4709 ms |
| Package tests: lexigram-secrets | 41.0% | 85/85 | 0 | 0 | 4 | 1 | 1837 ms |
| Package tests: lexigram-sql (unit only, no external DB) | 58.0% | 1197/1243 | 0 | 46 | 6 | 1 | 23282 ms |
| Package tests: lexigram-storage | 62.0% | 440/443 | 0 | 3 | 4 | 0 | 7128 ms |
| Package tests: lexigram-tasks | 68.0% | 433/454 | 0 | 21 | 4 | 1 | 9798 ms |
| Package tests: lexigram-tenancy | 82.0% | 345/345 | 0 | 0 | 4 | 0 | 3512 ms |
| Package tests: lexigram-testing | 17.0% | 436/451 | 0 | 15 | 4 | 1 | 8946 ms |
| Package tests: lexigram-ui | 59.0% | 1061/1140 | 1 | 78 | 12 | 1 | 7461 ms |
| Package tests: lexigram-vector | 76.0% | 498/498 | 0 | 0 | 4 | 0 | 4967 ms |
| Package tests: lexigram-web | 80.0% | 1370/1377 | 0 | 7 | 6 | 0 | 13737 ms |
| Package tests: lexigram-webhook | 83.0% | 334/334 | 0 | 0 | 4 | 0 | 3064 ms |
| Package tests: lexigram-workflow | 70.0% | 553/553 | 0 | 0 | 4 | 0 | 14196 ms |
| Scripts audit smoke | 46.0% | 36/37 | 1 | 0 | 0 | 1 | 2300 ms |

### Execution Scope Notes

- `framework-core`: real test execution for `lexigram/tests`.
- `package`: real test execution for `<package>/tests` across every discovered Lexigram package with tests.
- `scripts-audit`: real test execution for `tests/scripts`.

### Lexigram framework core tests

- Scope: `lexigram/tests`
- Command: `uv run pytest lexigram/tests -q -m not integration --cov=lexigram`
- Status: **FAIL**
- Exit code: `1`
- Duration: `28333 ms`
- Parsed summary: `2936 passed, 5 skipped, 19 deselected, 1 warning in 25.10s`
- Counters: passed=2936, total=2941, failed=0, skipped=5, warnings=1, coverage=58.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:48:13 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `11866 ms`
- Parsed summary: `1732 passed, 4 warnings in 10.05s`
- Counters: passed=1732, total=1732, failed=0, skipped=0, warnings=4, coverage=34.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:48:42 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  4%]
........................................................................ [  8%]
........................................................................ [ 12%]
........................................................................ [ 16%]
........................................................................ [ 20%]
........................................................................ [ 24%]
........................................................................ [ 29%]
....................................................
```

### Package tests: lexigram-admin

- Scope: `lexigram-admin/tests`
- Command: `uv run pytest lexigram-admin/tests -q -m not integration --cov=lexigram.admin`
- Status: **FAIL**
- Exit code: `1`
- Duration: `71525 ms`
- Parsed summary: `12 failed, 4282 passed, 10 skipped, 27 deselected, 19 warnings in 68.62s (0:01:08)`
- Counters: passed=4282, total=4304, failed=12, skipped=10, warnings=19, coverage=75.0%
- Example failures: `lexigram-admin/tests/e2e/test_admin_email_verify_http_e2e.py::test_login_email_factor_redirects_to_challenge_and_sends_otp`, `lexigram-admin/tests/e2e/test_admin_email_verify_http_e2e.py::test_email_factor_challenge_page_shows_resend_form`, `lexigram-admin/tests/e2e/test_admin_email_verify_http_e2e.py::test_email_factor_challenge_submit_completes_login`, `lexigram-admin/tests/e2e/test_admin_email_verify_http_e2e.py::test_email_factor_challenge_submit_invalid_code_errors`, `lexigram-admin/tests/e2e/test_admin_email_verify_http_e2e.py::test_email_factor_resend_redirects_notice`
- Output snippet:

```text
2026-08-16 21:48:53 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
ss...................FFFFFF......................ss..................... [  1%]
........................................................................ [  3%]
..........s..................ss......................................... [  5%]
........................................................................ [  6%]
........................................................................ [  8%]
........................................................................ [ 10%]
..................................FF.F........FF........................ [ 11%]
....................................................
```

### Package tests: lexigram-ai-agents

- Scope: `lexigram-ai-agents/tests`
- Command: `uv run pytest lexigram-ai-agents/tests -q -m not integration --cov=lexigram.ai.agents`
- Status: **PASS**
- Exit code: `0`
- Duration: `6411 ms`
- Parsed summary: `379 passed, 10 deselected, 4 warnings in 4.70s`
- Counters: passed=379, total=379, failed=0, skipped=0, warnings=4, coverage=84.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:50:05 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2142 ms`
- Parsed summary: `136 passed, 4 warnings in 0.62s`
- Counters: passed=136, total=136, failed=0, skipped=0, warnings=4, coverage=99.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:50:11 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2448 ms`
- Parsed summary: `237 passed, 4 warnings in 0.91s`
- Counters: passed=237, total=237, failed=0, skipped=0, warnings=4, coverage=94.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:50:14 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4726 ms`
- Parsed summary: `506 passed, 7 deselected, 15 warnings in 3.13s`
- Counters: passed=506, total=506, failed=0, skipped=0, warnings=15, coverage=86.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:50:16 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2675 ms`
- Parsed summary: `224 passed, 17 deselected, 7 warnings in 1.01s`
- Counters: passed=224, total=224, failed=0, skipped=0, warnings=7, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:50:21 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `33834 ms`
- Parsed summary: `945 passed, 20 skipped, 19 deselected, 4 warnings in 31.60s`
- Counters: passed=945, total=965, failed=0, skipped=20, warnings=4, coverage=71.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:50:23 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4015 ms`
- Parsed summary: `368 passed, 13 deselected, 4 warnings in 2.40s`
- Counters: passed=368, total=368, failed=0, skipped=0, warnings=4, coverage=50.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:50:57 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Command: `uv run pytest lexigram-ai-memory/tests -q -m not integration --cov=lexigram.ai.memory`
- Status: **PASS**
- Exit code: `0`
- Duration: `2795 ms`
- Parsed summary: `224 passed, 16 deselected, 4 warnings in 1.26s`
- Counters: passed=224, total=224, failed=0, skipped=0, warnings=4, coverage=77.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:51:01 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 32%]
........................................................................ [ 64%]
........................................................................ [ 96%]
........                                                                 [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858
  /home/admin/Documents/AI/applications/framework/lexigram/.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:858: PytestAssertRewrite
```

### Package tests: lexigram-ai-observability

- Scope: `lexigram-ai-observability/tests`
- Command: `uv run pytest lexigram-ai-observability/tests -q -m not integration --cov=lexigram.ai.observability`
- Status: **PASS**
- Exit code: `0`
- Duration: `2996 ms`
- Parsed summary: `232 passed, 10 deselected, 4 warnings in 1.42s`
- Counters: passed=232, total=232, failed=0, skipped=0, warnings=4, coverage=86.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:51:04 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `3017 ms`
- Parsed summary: `297 passed, 4 warnings in 1.42s`
- Counters: passed=297, total=297, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:51:07 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `8015 ms`
- Parsed summary: `528 passed, 7 skipped, 8 deselected, 4 warnings in 6.32s`
- Counters: passed=528, total=535, failed=0, skipped=7, warnings=4, coverage=62.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:51:10 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4438 ms`
- Parsed summary: `526 passed, 4 warnings in 2.85s`
- Counters: passed=526, total=526, failed=0, skipped=0, warnings=4, coverage=94.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:51:18 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 27%]
........................................................................ [ 41%]
........................................................................ [ 54%]
........................................................................ [ 68%]
........................................................................ [ 82%]
........................................................................ [ 95%]
......................                              
```

### Package tests: lexigram-ai-relay

- Scope: `lexigram-ai-relay/tests`
- Command: `uv run pytest lexigram-ai-relay/tests -q -m not integration --cov=lexigram.ai.relay`
- Status: **PASS**
- Exit code: `0`
- Duration: `6945 ms`
- Parsed summary: `539 passed, 4 warnings in 5.31s`
- Counters: passed=539, total=539, failed=0, skipped=0, warnings=4, coverage=91.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:51:22 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
2026-08-16 21:51:23 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=RelayModule providers=0
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
- Duration: `2925 ms`
- Parsed summary: `210 passed, 4 warnings in 1.29s`
- Counters: passed=210, total=210, failed=0, skipped=0, warnings=4, coverage=88.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:51:29 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2944 ms`
- Parsed summary: `263 passed, 6 warnings in 1.41s`
- Counters: passed=263, total=263, failed=0, skipped=0, warnings=6, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:51:32 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4365 ms`
- Parsed summary: `318 passed, 7 deselected, 4 warnings in 2.78s`
- Counters: passed=318, total=318, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:51:35 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `19722 ms`
- Parsed summary: `451 passed, 11 skipped, 15 deselected, 4 warnings in 17.65s`
- Counters: passed=451, total=462, failed=0, skipped=11, warnings=4, coverage=42.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:51:40 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Status: **FAIL**
- Exit code: `1`
- Duration: `2736 ms`
- Parsed summary: `242 passed, 17 deselected, 4 warnings in 1.14s`
- Counters: passed=242, total=242, failed=0, skipped=0, warnings=4, coverage=70.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:51:59 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 29%]
........................................................................ [ 59%]
........................................................................ [ 89%]
..........................
ERROR: Coverage failure: total of 70 is less than fail-under=80
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
- Duration: `26758 ms`
- Parsed summary: `578 passed, 4 skipped, 2 deselected, 6 warnings in 25.00s`
- Counters: passed=578, total=582, failed=0, skipped=4, warnings=6, coverage=66.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:52:02 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 12%]
....................................ssss................................ [ 24%]
........................................................................ [ 37%]
........................................................................ [ 49%]
........................................................................ [ 61%]
........................................................................ [ 74%]
........................................................................ [ 86%]
....................................................
```

### Package tests: lexigram-cache

- Scope: `lexigram-cache/tests`
- Command: `uv run pytest lexigram-cache/tests -q -m not integration --cov=lexigram.cache`
- Status: **FAIL**
- Exit code: `1`
- Duration: `11262 ms`
- Parsed summary: `752 passed, 13 skipped, 22 deselected, 6 warnings in 9.43s`
- Counters: passed=752, total=765, failed=0, skipped=13, warnings=6, coverage=70.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:52:29 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  9%]
.........................ss............................................. [ 18%]
........................................................................ [ 28%]
...........ssssssssss................................................... [ 37%]
........................................................................ [ 47%]
........................................................................ [ 56%]
........................................................................ [ 65%]
....................................................
```

### Package tests: lexigram-cli

- Scope: `lexigram-cli/tests`
- Command: `uv run pytest lexigram-cli/tests -q -m not integration --cov=lexigram.cli`
- Status: **PASS**
- Exit code: `0`
- Duration: `19898 ms`
- Parsed summary: `851 passed, 1 skipped, 7 deselected, 6 warnings in 17.82s`
- Counters: passed=851, total=852, failed=0, skipped=1, warnings=6, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:52:40 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `13431 ms`
- Parsed summary: `916 passed, 15 skipped, 11 deselected, 5 warnings in 11.09s`
- Counters: passed=916, total=931, failed=0, skipped=15, warnings=5, coverage=61.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:53:00 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `3845 ms`
- Parsed summary: `245 passed, 14 deselected, 17 warnings in 2.28s`
- Counters: passed=245, total=245, failed=0, skipped=0, warnings=17, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:53:14 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2636 ms`
- Parsed summary: `257 passed, 1 skipped, 7 deselected, 4 warnings in 1.10s`
- Counters: passed=257, total=258, failed=0, skipped=1, warnings=4, coverage=79.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:53:17 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `5995 ms`
- Parsed summary: `502 passed, 4 skipped, 11 deselected, 4 warnings in 4.04s`
- Counters: passed=502, total=506, failed=0, skipped=4, warnings=4, coverage=72.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:53:20 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2891 ms`
- Parsed summary: `433 passed, 9 deselected, 4 warnings in 1.34s`
- Counters: passed=433, total=433, failed=0, skipped=0, warnings=4, coverage=73.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:53:26 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `9093 ms`
- Parsed summary: `310 passed, 5 skipped, 4 deselected, 4 warnings in 7.46s`
- Counters: passed=310, total=315, failed=0, skipped=5, warnings=4, coverage=81.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:53:29 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2296 ms`
- Parsed summary: `12 passed, 1 skipped, 4 warnings in 0.56s`
- Counters: passed=12, total=13, failed=0, skipped=1, warnings=4, coverage=69.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:53:38 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2601 ms`
- Parsed summary: `54 passed, 4 warnings in 0.84s`
- Counters: passed=54, total=54, failed=0, skipped=0, warnings=4, coverage=92.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:53:40 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2225 ms`
- Parsed summary: `22 passed, 4 warnings in 0.50s`
- Counters: passed=22, total=22, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:53:43 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
......................                                                   [100%]
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
- Duration: `2200 ms`
- Parsed summary: `36 passed, 4 warnings in 0.55s`
- Counters: passed=36, total=36, failed=0, skipped=0, warnings=4, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:53:45 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
....................................                                     [100%]
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
- Duration: `2482 ms`
- Parsed summary: `53 passed, 4 warnings in 0.75s`
- Counters: passed=53, total=53, failed=0, skipped=0, warnings=4, coverage=70.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:53:47 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2246 ms`
- Parsed summary: `25 passed, 4 warnings in 0.54s`
- Counters: passed=25, total=25, failed=0, skipped=0, warnings=4, coverage=77.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:53:50 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.........................                                                [100%]
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
- Duration: `5669 ms`
- Parsed summary: `142 passed, 4 warnings in 3.95s`
- Counters: passed=142, total=142, failed=0, skipped=0, warnings=4, coverage=84.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:53:52 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 50%]
......................................................................   [100%]
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
- Duration: `5519 ms`
- Parsed summary: `86 passed, 5 warnings in 3.85s`
- Counters: passed=86, total=86, failed=0, skipped=0, warnings=5, coverage=56.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:53:58 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `3573 ms`
- Parsed summary: `416 passed, 10 deselected, 4 warnings in 1.99s`
- Counters: passed=416, total=416, failed=0, skipped=0, warnings=4, coverage=91.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:54:03 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 17%]
........................................................................ [ 34%]
........................................................................ [ 51%]
........................................................................ [ 69%]
........................................................................ [ 86%]
........................................................                 [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/_
```

### Package tests: lexigram-notification

- Scope: `lexigram-notification/tests`
- Command: `uv run pytest lexigram-notification/tests -q -m not integration --cov=lexigram.notification`
- Status: **FAIL**
- Exit code: `1`
- Duration: `6218 ms`
- Parsed summary: `1 failed, 278 passed, 8 deselected, 4 warnings in 4.46s`
- Counters: passed=278, total=279, failed=1, skipped=0, warnings=4, coverage=83.0%
- Example failures: `lexigram-notification/tests/e2e/test_inbox_admin_http_e2e.py::TestInboxAdminPageContainerIntegration::test_page_resolved_from_container_and_wrapped_in_shell`
- Output snippet:

```text
2026-08-16 21:54:07 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
............F........................................................... [ 25%]
........................................................................ [ 51%]
........................................................................ [ 77%]
...............................................................          [100%]
=================================== FAILURES ===================================
_ TestInboxAdminPageContainerIntegration.test_page_resolved_from_container_and_wrapped_in_shell _

self = <test_inbox_admin_http_e2e.TestInboxAdminPageContainerIntegration object at 0x7029e6491810>

    @pytest.
```

### Package tests: lexigram-queue

- Scope: `lexigram-queue/tests`
- Command: `uv run pytest lexigram-queue/tests -q -m not integration --cov=lexigram.queue`
- Status: **FAIL**
- Exit code: `1`
- Duration: `4600 ms`
- Parsed summary: `1 failed, 205 passed, 19 deselected, 4 warnings in 2.93s`
- Counters: passed=205, total=206, failed=1, skipped=0, warnings=4, coverage=82.0%
- Example failures: `lexigram-queue/tests/unit/test_azure_servicebus.py::TestAzureServiceBusQueue::test_connect_raises_import_error_without_sdk`
- Output snippet:

```text
2026-08-16 21:54:13 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
...................F.................................................... [ 34%]
........................................................................ [ 69%]
..............................................................           [100%]
=================================== FAILURES ===================================
____ TestAzureServiceBusQueue.test_connect_raises_import_error_without_sdk _____

self = <test_azure_servicebus.TestAzureServiceBusQueue object at 0x7491a8e42710>

    @pytest.mark.asyncio
    async def test_connect_raises_import_error_without_sdk(self) -> None:
        """connect() raises 
```

### Package tests: lexigram-resilience

- Scope: `lexigram-resilience/tests`
- Command: `uv run pytest lexigram-resilience/tests -q -m not integration --cov=lexigram.resilience`
- Status: **PASS**
- Exit code: `0`
- Duration: `20595 ms`
- Parsed summary: `299 passed, 23 deselected, 4 warnings in 19.04s`
- Counters: passed=299, total=299, failed=0, skipped=0, warnings=4, coverage=72.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:54:18 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4709 ms`
- Parsed summary: `771 passed, 3 skipped, 15 deselected, 4 warnings in 2.97s`
- Counters: passed=771, total=774, failed=0, skipped=3, warnings=4, coverage=65.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:54:38 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  9%]
........................................................................ [ 18%]
........................................................................ [ 28%]
........................................................................ [ 37%]
........................................................................ [ 46%]
........................................................................ [ 56%]
........................................................................ [ 65%]
....................................................
```

### Package tests: lexigram-secrets

- Scope: `lexigram-secrets/tests`
- Command: `uv run pytest lexigram-secrets/tests -q -m not integration --cov=lexigram.secrets`
- Status: **FAIL**
- Exit code: `1`
- Duration: `1837 ms`
- Parsed summary: `85 passed, 4 warnings in 0.37s`
- Counters: passed=85, total=85, failed=0, skipped=0, warnings=4, coverage=41.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:54:43 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 84%]
.............
ERROR: Coverage failure: total of 41 is less than fail-under=55
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
- Duration: `23282 ms`
- Parsed summary: `1197 passed, 46 skipped, 6 warnings in 21.08s`
- Counters: passed=1197, total=1243, failed=0, skipped=46, warnings=6, coverage=58.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:54:45 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  5%]
........................................................................ [ 11%]
........................................................................ [ 17%]
.....ss................................................................. [ 23%]
........................................................................ [ 28%]
........................................................................ [ 34%]
.....................................................s.................. [ 40%]
..ss......s.........................................
```

### Package tests: lexigram-storage

- Scope: `lexigram-storage/tests`
- Command: `uv run pytest lexigram-storage/tests -q -m not integration --cov=lexigram.storage`
- Status: **PASS**
- Exit code: `0`
- Duration: `7128 ms`
- Parsed summary: `440 passed, 3 skipped, 22 deselected, 4 warnings in 5.53s`
- Counters: passed=440, total=443, failed=0, skipped=3, warnings=4, coverage=62.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:55:08 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `9798 ms`
- Parsed summary: `433 passed, 21 skipped, 9 deselected, 4 warnings in 7.96s`
- Counters: passed=433, total=454, failed=0, skipped=21, warnings=4, coverage=68.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:55:15 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
......................................................................ss [ 15%]
ssss.................................................................... [ 31%]
..........................sssss......................................... [ 47%]
.................................................................sssssss [ 63%]
ss...................................................................... [ 79%]
.................................................s...................... [ 95%]
......................
ERROR: Coverage failure: total of 68 is less than fail-under=80
                                             
```

### Package tests: lexigram-tenancy

- Scope: `lexigram-tenancy/tests`
- Command: `uv run pytest lexigram-tenancy/tests -q -m not integration --cov=lexigram.tenancy`
- Status: **PASS**
- Exit code: `0`
- Duration: `3512 ms`
- Parsed summary: `345 passed, 4 deselected, 4 warnings in 1.84s`
- Counters: passed=345, total=345, failed=0, skipped=0, warnings=4, coverage=82.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:55:25 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `8946 ms`
- Parsed summary: `436 passed, 15 skipped, 13 deselected, 4 warnings in 7.23s`
- Counters: passed=436, total=451, failed=0, skipped=15, warnings=4, coverage=17.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:55:28 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Status: **FAIL**
- Exit code: `1`
- Duration: `7461 ms`
- Parsed summary: `1 failed, 1061 passed, 78 skipped, 8 deselected, 12 warnings in 5.74s`
- Counters: passed=1061, total=1140, failed=1, skipped=78, warnings=12, coverage=59.0%
- Example failures: `lexigram-ui/tests/unit/test_theme.py::test_shadcn_css_has_no_static_utility_classes`
- Output snippet:

```text
2026-08-16 21:55:37 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
ssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssss [  6%]
........................................................................ [ 12%]
........................................................................ [ 18%]
........................................................................ [ 25%]
........................................................................ [ 31%]
........................................................................ [ 37%]
........................................................................ [ 44%]
....................................................
```

### Package tests: lexigram-vector

- Scope: `lexigram-vector/tests`
- Command: `uv run pytest lexigram-vector/tests -q -m not integration --cov=lexigram.vector`
- Status: **PASS**
- Exit code: `0`
- Duration: `4967 ms`
- Parsed summary: `498 passed, 20 deselected, 4 warnings in 3.29s`
- Counters: passed=498, total=498, failed=0, skipped=0, warnings=4, coverage=76.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:55:45 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `13737 ms`
- Parsed summary: `1370 passed, 7 skipped, 7 deselected, 6 warnings in 11.68s`
- Counters: passed=1370, total=1377, failed=0, skipped=7, warnings=6, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:55:50 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
sss..................................................................... [  5%]
........................................................................ [ 10%]
........................................................................ [ 15%]
........................................................................ [ 20%]
.........................s.............................................. [ 26%]
........................................................................ [ 31%]
.................................................s...................... [ 36%]
....................................................
```

### Package tests: lexigram-webhook

- Scope: `lexigram-webhook/tests`
- Command: `uv run pytest lexigram-webhook/tests -q -m not integration --cov=lexigram.webhook`
- Status: **PASS**
- Exit code: `0`
- Duration: `3064 ms`
- Parsed summary: `334 passed, 4 warnings in 1.46s`
- Counters: passed=334, total=334, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:56:04 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `14196 ms`
- Parsed summary: `553 passed, 23 deselected, 4 warnings in 12.64s`
- Counters: passed=553, total=553, failed=0, skipped=0, warnings=4, coverage=70.0%
- Example failures: none
- Output snippet:

```text
2026-08-16 21:56:07 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 26%]
........................................................................ [ 39%]
........................................................................ [ 52%]
........................................................................ [ 65%]
........................................................................ [ 78%]
........................................................................ [ 91%]
.................................................   
```

### Scripts audit smoke

- Scope: `tests/scripts`
- Command: `uv run pytest tests/scripts -q -m not integration --cov=scripts`
- Status: **FAIL**
- Exit code: `1`
- Duration: `2300 ms`
- Parsed summary: `1 failed, 36 passed in 0.76s`
- Counters: passed=36, total=37, failed=1, skipped=0, warnings=0, coverage=46.0%
- Example failures: `tests/scripts/test_registry.py::test_audit_registry_contains_expected_generators`
- Output snippet:

```text
2026-08-16 21:56:21 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.......................F.............                                    [100%]
=================================== FAILURES ===================================
_______________ test_audit_registry_contains_expected_generators _______________
tests/scripts/test_registry.py:75: in test_audit_registry_contains_expected_generators
    assert registry.names() == EXPECTED_GENERATOR_NAMES
E   AssertionError: assert ('docs-claims...rations', ...) == ('docs-links'...verview', ...)
E     
E     At index 0 diff: 'docs-claims' != 'docs-links'
E     Left contains 2 more items, first extra item: 'security'
E     Use -v
```

