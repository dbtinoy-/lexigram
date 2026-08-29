# AUDIT_TESTS.md — Lexigram Framework Targeted Test Execution Audit

> **Source**: Live pytest execution evidence for targeted scopes, with `tests/` directory scanning as supporting context.

---

## Summary

- Total passed tests: 31818
- Total failed tests: 0
- Total skipped tests: 340
- Total warnings: 345
- Aggregate code coverage: 76.46%

- Representative commands run: 54
- Commands passing: 52
- Commands failing: 2
- Packages with tests: 54
- Test files: 3401
- Test functions: 32019

### Exit Codes Reference

- **`0`**: Success — All tests passed and code coverage met the configured threshold.
- **`1`**: Failure — Functional tests failed OR code coverage fell below the package's `--cov-fail-under` threshold.
- **`timeout`**: The test command exceeded the execution time limit (120s) and was automatically terminated.

## Execution Evidence

| Label | Code Coverage | Pass/Total | Failed | Skipped | Warnings | Exit Code | Duration |
|-------|---------------|------------|---------|----------|------|-----------|----------|
| Package tests: core/lexigram-contracts | 34.0% | 1814/1814 | 0 | 0 | 4 | 0 | 10398 ms |
| Package tests: core/lexigram | 39.0% | 3077/3082 | 0 | 5 | 2 | 0 | 52480 ms |
| Package tests: experimental/ai/lexigram-ai-agents | 85.0% | 402/402 | 0 | 0 | 4 | 0 | 5811 ms |
| Package tests: experimental/ai/lexigram-ai-evaluation | 97.0% | 167/167 | 0 | 0 | 4 | 0 | 1849 ms |
| Package tests: experimental/ai/lexigram-ai-feedback | 96.0% | 260/260 | 0 | 0 | 4 | 0 | 2111 ms |
| Package tests: experimental/ai/lexigram-ai-governance | 88.0% | 544/544 | 0 | 0 | 47 | 0 | 4622 ms |
| Package tests: experimental/ai/lexigram-ai-guard | 87.0% | 242/242 | 0 | 0 | 7 | 0 | 2129 ms |
| Package tests: experimental/ai/lexigram-ai-llm | 71.0% | 953/974 | 0 | 21 | 4 | 0 | 31148 ms |
| Package tests: experimental/ai/lexigram-ai-mcp | 54.0% | 400/400 | 0 | 0 | 4 | 0 | 3541 ms |
| Package tests: experimental/ai/lexigram-ai-memory | 83.0% | 240/240 | 0 | 0 | 4 | 0 | 2339 ms |
| Package tests: experimental/ai/lexigram-ai-observability | 87.0% | 260/260 | 0 | 0 | 4 | 0 | 2597 ms |
| Package tests: experimental/ai/lexigram-ai-prompt | 87.0% | 307/307 | 0 | 0 | 4 | 0 | 2373 ms |
| Package tests: experimental/ai/lexigram-ai-rag | 62.0% | 528/535 | 0 | 7 | 4 | 0 | 6820 ms |
| Package tests: experimental/ai/lexigram-ai-relay-gateway | 94.0% | 581/581 | 0 | 0 | 4 | 0 | 4225 ms |
| Package tests: experimental/ai/lexigram-ai-relay | 91.0% | 534/534 | 0 | 0 | 4 | 0 | 5608 ms |
| Package tests: experimental/ai/lexigram-ai-session | 89.0% | 219/219 | 0 | 0 | 4 | 0 | 2391 ms |
| Package tests: experimental/ai/lexigram-ai-skills | 80.0% | 286/286 | 0 | 0 | 6 | 0 | 5311 ms |
| Package tests: experimental/ai/lexigram-ai-workers | 87.0% | 328/328 | 0 | 0 | 4 | 0 | 3790 ms |
| Package tests: experimental/ai/lexigram-ai | 42.0% | 470/489 | 0 | 19 | 4 | 1 | 15160 ms |
| Package tests: experimental/apps/lexigram-admin | 77.0% | 4676/4692 | 0 | 16 | 18 | 0 | 54279 ms |
| Package tests: experimental/apps/lexigram-cli | 81.0% | 902/903 | 0 | 1 | 6 | 0 | 15845 ms |
| Package tests: experimental/apps/lexigram-ui | 73.0% | 1251/1329 | 0 | 78 | 12 | 0 | 6529 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-beat | 74.0% | 21/21 | 0 | 0 | 4 | 0 | 2651 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-image | 92.0% | 54/54 | 0 | 0 | 4 | 0 | 2123 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-interpolate | 88.0% | 23/23 | 0 | 0 | 4 | 0 | 1857 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-music | 87.0% | 47/47 | 0 | 0 | 4 | 0 | 1992 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-tts | 79.0% | 63/63 | 0 | 0 | 4 | 0 | 2232 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-upscale | 92.0% | 42/42 | 0 | 0 | 4 | 0 | 2052 ms |
| Package tests: experimental/multimedia/lexigram-multimedia-video | 87.0% | 182/182 | 0 | 0 | 4 | 0 | 5502 ms |
| Package tests: experimental/multimedia/lexigram-multimedia | 58.0% | 89/89 | 0 | 0 | 5 | 0 | 4616 ms |
| Package tests: packages/lexigram-audit | 87.0% | 293/293 | 0 | 0 | 4 | 0 | 2417 ms |
| Package tests: packages/lexigram-auth | 69.0% | 632/636 | 0 | 4 | 15 | 0 | 30081 ms |
| Package tests: packages/lexigram-cache | 81.0% | 874/887 | 0 | 13 | 6 | 0 | 10739 ms |
| Package tests: packages/lexigram-events | 64.0% | 999/1014 | 0 | 15 | 4 | 0 | 11957 ms |
| Package tests: packages/lexigram-features | 84.0% | 253/253 | 0 | 0 | 17 | 0 | 3478 ms |
| Package tests: packages/lexigram-graph | 80.0% | 263/264 | 0 | 1 | 4 | 0 | 2225 ms |
| Package tests: packages/lexigram-graphql | 76.0% | 520/522 | 0 | 2 | 23 | 0 | 5852 ms |
| Package tests: packages/lexigram-http | 85.0% | 457/457 | 0 | 0 | 8 | 0 | 2833 ms |
| Package tests: packages/lexigram-monitor | 78.0% | 317/338 | 0 | 21 | 4 | 1 | 8408 ms |
| Package tests: packages/lexigram-nosql | 91.0% | 537/537 | 0 | 0 | 4 | 0 | 3443 ms |
| Package tests: packages/lexigram-notification | 85.0% | 296/296 | 0 | 0 | 7 | 0 | 4976 ms |
| Package tests: packages/lexigram-queue | 85.0% | 235/235 | 0 | 0 | 4 | 0 | 4375 ms |
| Package tests: packages/lexigram-resilience | 75.0% | 311/311 | 0 | 0 | 4 | 0 | 19952 ms |
| Package tests: packages/lexigram-search | 66.0% | 813/818 | 0 | 5 | 4 | 0 | 4187 ms |
| Package tests: packages/lexigram-secrets | 59.0% | 134/134 | 0 | 0 | 4 | 0 | 1652 ms |
| Package tests: packages/lexigram-sql | 61.0% | 1309/1400 | 0 | 91 | 10 | 0 | 11741 ms |
| Package tests: packages/lexigram-storage | 64.0% | 463/466 | 0 | 3 | 4 | 0 | 6731 ms |
| Package tests: packages/lexigram-tasks | 74.0% | 525/541 | 0 | 16 | 4 | 0 | 11090 ms |
| Package tests: packages/lexigram-tenancy | 85.0% | 362/362 | 0 | 0 | 4 | 0 | 2942 ms |
| Package tests: packages/lexigram-testing | 17.0% | 443/458 | 0 | 15 | 2 | 0 | 7938 ms |
| Package tests: packages/lexigram-vector | 78.0% | 533/533 | 0 | 0 | 4 | 0 | 4059 ms |
| Package tests: packages/lexigram-web | 81.0% | 1392/1399 | 0 | 7 | 6 | 0 | 14425 ms |
| Package tests: packages/lexigram-webhook | 90.0% | 336/336 | 0 | 0 | 4 | 0 | 2713 ms |
| Package tests: packages/lexigram-workflow | 73.0% | 559/559 | 0 | 0 | 4 | 0 | 13676 ms |

### Execution Scope Notes

- `framework-core`: real test execution for `lexigram/tests`.
- `package`: real test execution for `<package>/tests` across every discovered Lexigram package with tests.
### Package tests: core/lexigram-contracts

- Scope: `core/lexigram-contracts/tests`
- Command: `uv run pytest core/lexigram-contracts/tests -q -m not integration --cov=core/lexigram.contracts`
- Status: **PASS**
- Exit code: `0`
- Duration: `10398 ms`
- Parsed summary: `1814 passed, 4 warnings in 9.04s`
- Counters: passed=1814, total=1814, failed=0, skipped=0, warnings=4, coverage=34.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:11:42 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `52480 ms`
- Parsed summary: `3077 passed, 5 skipped, 19 deselected, 2 warnings in 49.93s`
- Counters: passed=3077, total=3082, failed=0, skipped=5, warnings=2, coverage=39.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:11:52 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
2026-08-29 19:11:52 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=1 imports=0 is_global=False module=CoreModule providers=1
2026-08-29 19:11:52 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=1 imports=1 is_global=False module=CacheModule providers=1
2026-08-29 19:11:52 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=1 imports=2 is_global=False module=WebModule providers=1
.........................................................
```

### Package tests: experimental/ai/lexigram-ai-agents

- Scope: `experimental/ai/lexigram-ai-agents/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-agents/tests -q -m not integration --cov=experimental/ai/lexigram.ai.agents`
- Status: **PASS**
- Exit code: `0`
- Duration: `5811 ms`
- Parsed summary: `402 passed, 10 deselected, 4 warnings in 4.55s`
- Counters: passed=402, total=402, failed=0, skipped=0, warnings=4, coverage=85.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:12:45 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `1849 ms`
- Parsed summary: `167 passed, 4 warnings in 0.71s`
- Counters: passed=167, total=167, failed=0, skipped=0, warnings=4, coverage=97.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:12:51 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2111 ms`
- Parsed summary: `260 passed, 4 warnings in 0.94s`
- Counters: passed=260, total=260, failed=0, skipped=0, warnings=4, coverage=96.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:12:52 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4622 ms`
- Parsed summary: `544 passed, 7 deselected, 47 warnings in 3.39s`
- Counters: passed=544, total=544, failed=0, skipped=0, warnings=47, coverage=88.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:12:54 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2129 ms`
- Parsed summary: `242 passed, 17 deselected, 7 warnings in 0.97s`
- Counters: passed=242, total=242, failed=0, skipped=0, warnings=7, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:12:59 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `31148 ms`
- Parsed summary: `953 passed, 21 skipped, 19 deselected, 4 warnings in 29.65s`
- Counters: passed=953, total=974, failed=0, skipped=21, warnings=4, coverage=71.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:13:01 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
ssssssssssssssss........................................................ [  7%]
........................................................................ [ 14%]
........................................................................ [ 22%]
.....................................................................sss [ 29%]
s....................................................................... [ 36%]
........................................................................ [ 44%]
........................................................................ [ 51%]
....................................................
```

### Package tests: experimental/ai/lexigram-ai-mcp

- Scope: `experimental/ai/lexigram-ai-mcp/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-mcp/tests -q -m not integration --cov=experimental/ai/lexigram.ai.mcp`
- Status: **PASS**
- Exit code: `0`
- Duration: `3541 ms`
- Parsed summary: `400 passed, 13 deselected, 4 warnings in 2.31s`
- Counters: passed=400, total=400, failed=0, skipped=0, warnings=4, coverage=54.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:13:32 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 18%]
........................................................................ [ 36%]
........................................................................ [ 54%]
........................................................................ [ 72%]
........................................................................ [ 90%]
........................................                                 [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/_
```

### Package tests: experimental/ai/lexigram-ai-memory

- Scope: `experimental/ai/lexigram-ai-memory/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-memory/tests -q -m not integration --cov=experimental/ai/lexigram.ai.memory`
- Status: **PASS**
- Exit code: `0`
- Duration: `2339 ms`
- Parsed summary: `240 passed, 16 deselected, 4 warnings in 1.17s`
- Counters: passed=240, total=240, failed=0, skipped=0, warnings=4, coverage=83.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:13:36 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2597 ms`
- Parsed summary: `260 passed, 10 deselected, 4 warnings in 1.39s`
- Counters: passed=260, total=260, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:13:38 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2373 ms`
- Parsed summary: `307 passed, 4 warnings in 1.20s`
- Counters: passed=307, total=307, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:13:41 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `6820 ms`
- Parsed summary: `528 passed, 7 skipped, 8 deselected, 4 warnings in 5.52s`
- Counters: passed=528, total=535, failed=0, skipped=7, warnings=4, coverage=62.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:13:43 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4225 ms`
- Parsed summary: `581 passed, 4 warnings in 2.94s`
- Counters: passed=581, total=581, failed=0, skipped=0, warnings=4, coverage=94.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:13:50 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
2026-08-29 19:13:50 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=RelayModule providers=0
........................................................................ [ 12%]
........................................................................ [ 24%]
........................................................................ [ 37%]
........................................................................ [ 49%]
........................................................................ [ 61%]
..........................
```

### Package tests: experimental/ai/lexigram-ai-relay

- Scope: `experimental/ai/lexigram-ai-relay/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-relay/tests -q -m not integration --cov=experimental/ai/lexigram.ai.relay`
- Status: **PASS**
- Exit code: `0`
- Duration: `5608 ms`
- Parsed summary: `534 passed, 4 warnings in 4.39s`
- Counters: passed=534, total=534, failed=0, skipped=0, warnings=4, coverage=91.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:13:54 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
2026-08-29 19:13:54 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=RelayModule providers=0
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
- Duration: `2391 ms`
- Parsed summary: `219 passed, 4 warnings in 1.19s`
- Counters: passed=219, total=219, failed=0, skipped=0, warnings=4, coverage=89.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:14:00 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 32%]
........................................................................ [ 65%]
........................................................................ [ 98%]
...                                                                      [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewr
```

### Package tests: experimental/ai/lexigram-ai-skills

- Scope: `experimental/ai/lexigram-ai-skills/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-skills/tests -q -m not integration --cov=experimental/ai/lexigram.ai.skills`
- Status: **PASS**
- Exit code: `0`
- Duration: `5311 ms`
- Parsed summary: `286 passed, 6 warnings in 4.14s`
- Counters: passed=286, total=286, failed=0, skipped=0, warnings=6, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:14:02 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 25%]
........................................................................ [ 50%]
........................................................................ [ 75%]
......................................................................   [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewr
```

### Package tests: experimental/ai/lexigram-ai-workers

- Scope: `experimental/ai/lexigram-ai-workers/tests`
- Command: `uv run pytest experimental/ai/lexigram-ai-workers/tests -q -m not integration --cov=experimental/ai/lexigram.ai.workers`
- Status: **PASS**
- Exit code: `0`
- Duration: `3790 ms`
- Parsed summary: `328 passed, 7 deselected, 4 warnings in 2.59s`
- Counters: passed=328, total=328, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:14:08 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `15160 ms`
- Parsed summary: `470 passed, 19 skipped, 15 deselected, 4 warnings in 13.79s`
- Counters: passed=470, total=489, failed=0, skipped=19, warnings=4, coverage=42.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:14:11 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `54279 ms`
- Parsed summary: `4676 passed, 16 skipped, 29 deselected, 18 warnings in 52.08s`
- Counters: passed=4676, total=4692, failed=0, skipped=16, warnings=18, coverage=77.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:14:27 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `15845 ms`
- Parsed summary: `902 passed, 1 skipped, 7 deselected, 6 warnings in 14.25s`
- Counters: passed=902, total=903, failed=0, skipped=1, warnings=6, coverage=81.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:15:21 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  7%]
........................................................................ [ 15%]
........................................................................ [ 23%]
........................................................................ [ 31%]
........................................................................ [ 39%]
........................................................................ [ 47%]
........................................................................ [ 55%]
....................................................
```

### Package tests: experimental/apps/lexigram-ui

- Scope: `experimental/apps/lexigram-ui/tests`
- Command: `uv run pytest experimental/apps/lexigram-ui/tests -q -m not integration --cov=experimental/apps/lexigram.ui`
- Status: **PASS**
- Exit code: `0`
- Duration: `6529 ms`
- Parsed summary: `1251 passed, 78 skipped, 8 deselected, 12 warnings in 5.20s`
- Counters: passed=1251, total=1329, failed=0, skipped=78, warnings=12, coverage=73.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:15:37 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2651 ms`
- Parsed summary: `21 passed, 12 deselected, 4 warnings in 1.28s`
- Counters: passed=21, total=21, failed=0, skipped=0, warnings=4, coverage=74.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:15:43 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.....................                                                    [100%]
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
- Duration: `2123 ms`
- Parsed summary: `54 passed, 4 warnings in 0.78s`
- Counters: passed=54, total=54, failed=0, skipped=0, warnings=4, coverage=92.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:15:46 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `1857 ms`
- Parsed summary: `23 passed, 4 warnings in 0.51s`
- Counters: passed=23, total=23, failed=0, skipped=0, warnings=4, coverage=88.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:15:48 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `1992 ms`
- Parsed summary: `47 passed, 4 warnings in 0.68s`
- Counters: passed=47, total=47, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:15:50 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2232 ms`
- Parsed summary: `63 passed, 4 warnings in 0.89s`
- Counters: passed=63, total=63, failed=0, skipped=0, warnings=4, coverage=79.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:15:52 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2052 ms`
- Parsed summary: `42 passed, 4 warnings in 0.70s`
- Counters: passed=42, total=42, failed=0, skipped=0, warnings=4, coverage=92.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:15:54 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `5502 ms`
- Parsed summary: `182 passed, 4 warnings in 4.15s`
- Counters: passed=182, total=182, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:15:56 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4616 ms`
- Parsed summary: `89 passed, 5 warnings in 3.41s`
- Counters: passed=89, total=89, failed=0, skipped=0, warnings=5, coverage=58.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:16:02 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 80%]
.................                                                        [100%]
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
- Duration: `2417 ms`
- Parsed summary: `293 passed, 17 deselected, 4 warnings in 1.21s`
- Counters: passed=293, total=293, failed=0, skipped=0, warnings=4, coverage=87.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:16:06 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 24%]
........................................................................ [ 49%]
........................................................................ [ 73%]
........................................................................ [ 98%]
.....                                                                    [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .ve
```

### Package tests: packages/lexigram-auth

- Scope: `packages/lexigram-auth/tests`
- Command: `uv run pytest packages/lexigram-auth/tests -q -m not integration --cov=packages/lexigram.auth`
- Status: **PASS**
- Exit code: `0`
- Duration: `30081 ms`
- Parsed summary: `632 passed, 4 skipped, 2 deselected, 15 warnings in 28.67s`
- Counters: passed=632, total=636, failed=0, skipped=4, warnings=15, coverage=69.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:16:09 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 11%]
........................................................................ [ 22%]
........................................................................ [ 33%]
........................................................................ [ 45%]
.....ssss............................................................... [ 56%]
........................................................................ [ 67%]
........................................................................ [ 79%]
....................................................
```

### Package tests: packages/lexigram-cache

- Scope: `packages/lexigram-cache/tests`
- Command: `uv run pytest packages/lexigram-cache/tests -q -m not integration --cov=packages/lexigram.cache`
- Status: **PASS**
- Exit code: `0`
- Duration: `10739 ms`
- Parsed summary: `874 passed, 13 skipped, 13 deselected, 6 warnings in 9.38s`
- Counters: passed=874, total=887, failed=0, skipped=13, warnings=6, coverage=81.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:16:39 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [  8%]
.................................................ss..................... [ 16%]
........................................................................ [ 24%]
..........................................................ssssssssss.... [ 32%]
........................................................................ [ 40%]
........................................................................ [ 48%]
........................................................................ [ 56%]
....................................................
```

### Package tests: packages/lexigram-events

- Scope: `packages/lexigram-events/tests`
- Command: `uv run pytest packages/lexigram-events/tests -q -m not integration --cov=packages/lexigram.events`
- Status: **PASS**
- Exit code: `0`
- Duration: `11957 ms`
- Parsed summary: `999 passed, 15 skipped, 11 deselected, 4 warnings in 10.64s`
- Counters: passed=999, total=1014, failed=0, skipped=15, warnings=4, coverage=64.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:16:49 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
...s.................................................................... [  7%]
........................................................................ [ 14%]
........................................................................ [ 21%]
........................................................................ [ 28%]
........................................................................ [ 35%]
........................................................................ [ 42%]
........................................................................ [ 49%]
....................................................
```

### Package tests: packages/lexigram-features

- Scope: `packages/lexigram-features/tests`
- Command: `uv run pytest packages/lexigram-features/tests -q -m not integration --cov=packages/lexigram.features`
- Status: **PASS**
- Exit code: `0`
- Duration: `3478 ms`
- Parsed summary: `253 passed, 14 deselected, 17 warnings in 2.28s`
- Counters: passed=253, total=253, failed=0, skipped=0, warnings=17, coverage=84.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:17:01 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 28%]
........................................................................ [ 56%]
........................................................................ [ 85%]
.....................................                                    [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewr
```

### Package tests: packages/lexigram-graph

- Scope: `packages/lexigram-graph/tests`
- Command: `uv run pytest packages/lexigram-graph/tests -q -m not integration --cov=packages/lexigram.graph`
- Status: **PASS**
- Exit code: `0`
- Duration: `2225 ms`
- Parsed summary: `263 passed, 1 skipped, 7 deselected, 4 warnings in 1.05s`
- Counters: passed=263, total=264, failed=0, skipped=1, warnings=4, coverage=80.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:17:05 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 27%]
..................s..................................................... [ 54%]
........................................................................ [ 81%]
................................................                         [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewr
```

### Package tests: packages/lexigram-graphql

- Scope: `packages/lexigram-graphql/tests`
- Command: `uv run pytest packages/lexigram-graphql/tests -q -m not integration --cov=packages/lexigram.graphql`
- Status: **PASS**
- Exit code: `0`
- Duration: `5852 ms`
- Parsed summary: `520 passed, 2 skipped, 11 deselected, 23 warnings in 4.28s`
- Counters: passed=520, total=522, failed=0, skipped=2, warnings=23, coverage=76.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:17:07 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2833 ms`
- Parsed summary: `457 passed, 9 deselected, 8 warnings in 1.58s`
- Counters: passed=457, total=457, failed=0, skipped=0, warnings=8, coverage=85.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:17:13 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Status: **FAIL**
- Exit code: `1`
- Duration: `8408 ms`
- Parsed summary: `317 passed, 21 skipped, 4 deselected, 4 warnings in 7.16s`
- Counters: passed=317, total=338, failed=0, skipped=21, warnings=4, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:17:16 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.s..........................ssssss...................................... [ 21%]
...s................................................sss.s............... [ 43%]
........................................................................ [ 64%]
...........................................................ssss......... [ 86%]
.............................................
ERROR: Coverage failure: total of 78 is less than fail-under=80
                                                                         [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/
```

### Package tests: packages/lexigram-nosql

- Scope: `packages/lexigram-nosql/tests`
- Command: `uv run pytest packages/lexigram-nosql/tests -q -m not integration --cov=packages/lexigram.nosql`
- Status: **PASS**
- Exit code: `0`
- Duration: `3443 ms`
- Parsed summary: `537 passed, 10 deselected, 4 warnings in 2.19s`
- Counters: passed=537, total=537, failed=0, skipped=0, warnings=4, coverage=91.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:17:24 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4976 ms`
- Parsed summary: `296 passed, 8 deselected, 7 warnings in 3.53s`
- Counters: passed=296, total=296, failed=0, skipped=0, warnings=7, coverage=85.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:17:28 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 24%]
........................................................................ [ 48%]
........................................................................ [ 72%]
........................................................................ [ 97%]
........                                                                 [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .ve
```

### Package tests: packages/lexigram-queue

- Scope: `packages/lexigram-queue/tests`
- Command: `uv run pytest packages/lexigram-queue/tests -q -m not integration --cov=packages/lexigram.queue`
- Status: **PASS**
- Exit code: `0`
- Duration: `4375 ms`
- Parsed summary: `235 passed, 20 deselected, 4 warnings in 3.14s`
- Counters: passed=235, total=235, failed=0, skipped=0, warnings=4, coverage=85.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:17:33 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 30%]
........................................................................ [ 61%]
........................................................................ [ 91%]
...................                                                      [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885
  .venv/lib/python3.13/site-packages/_pytest/config/__init__.py:885: PytestAssertRewr
```

### Package tests: packages/lexigram-resilience

- Scope: `packages/lexigram-resilience/tests`
- Command: `uv run pytest packages/lexigram-resilience/tests -q -m not integration --cov=packages/lexigram.resilience`
- Status: **PASS**
- Exit code: `0`
- Duration: `19952 ms`
- Parsed summary: `311 passed, 23 deselected, 4 warnings in 18.79s`
- Counters: passed=311, total=311, failed=0, skipped=0, warnings=4, coverage=75.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:17:37 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `4187 ms`
- Parsed summary: `813 passed, 5 skipped, 15 deselected, 4 warnings in 2.92s`
- Counters: passed=813, total=818, failed=0, skipped=5, warnings=4, coverage=66.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:17:57 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `1652 ms`
- Parsed summary: `134 passed, 4 warnings in 0.49s`
- Counters: passed=134, total=134, failed=0, skipped=0, warnings=4, coverage=59.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:18:01 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 53%]
..............................................................           [100%]
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
- Duration: `11741 ms`
- Parsed summary: `1309 passed, 91 skipped, 9 deselected, 10 warnings in 10.10s`
- Counters: passed=1309, total=1400, failed=0, skipped=91, warnings=10, coverage=61.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:18:03 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................s............................... [  5%]
........................................................................ [ 10%]
........................................................................ [ 15%]
.............ss......................................................... [ 20%]
........................................................................ [ 25%]
........................................................................ [ 30%]
........................................................................ [ 36%]
..............s...............ss.....sssssss........
```

### Package tests: packages/lexigram-storage

- Scope: `packages/lexigram-storage/tests`
- Command: `uv run pytest packages/lexigram-storage/tests -q -m not integration --cov=packages/lexigram.storage`
- Status: **PASS**
- Exit code: `0`
- Duration: `6731 ms`
- Parsed summary: `463 passed, 3 skipped, 22 deselected, 4 warnings in 5.51s`
- Counters: passed=463, total=466, failed=0, skipped=3, warnings=4, coverage=64.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:18:15 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 15%]
........................................................................ [ 30%]
............................................s........................... [ 46%]
........................................................................ [ 61%]
........................................................................ [ 77%]
........................................................................ [ 92%]
................................s                                        [100%]
=============================== warnings summary ===
```

### Package tests: packages/lexigram-tasks

- Scope: `packages/lexigram-tasks/tests`
- Command: `uv run pytest packages/lexigram-tasks/tests -q -m not integration --cov=packages/lexigram.tasks`
- Status: **PASS**
- Exit code: `0`
- Duration: `11090 ms`
- Parsed summary: `525 passed, 16 skipped, 9 deselected, 4 warnings in 9.79s`
- Counters: passed=525, total=541, failed=0, skipped=16, warnings=4, coverage=74.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:18:21 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `2942 ms`
- Parsed summary: `362 passed, 4 deselected, 4 warnings in 1.72s`
- Counters: passed=362, total=362, failed=0, skipped=0, warnings=4, coverage=85.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:18:32 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 19%]
........................................................................ [ 39%]
........................................................................ [ 59%]
........................................................................ [ 79%]
........................................................................ [ 99%]
..                                                                       [100%]
=============================== warnings summary ===============================
.venv/lib/python3.13/site-packages/_pytest/config/_
```

### Package tests: packages/lexigram-testing

- Scope: `packages/lexigram-testing/tests`
- Command: `uv run pytest packages/lexigram-testing/tests -q -m not integration --cov=packages/lexigram.testing`
- Status: **PASS**
- Exit code: `0`
- Duration: `7938 ms`
- Parsed summary: `443 passed, 15 skipped, 13 deselected, 2 warnings in 6.72s`
- Counters: passed=443, total=458, failed=0, skipped=15, warnings=2, coverage=17.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:18:35 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
.................s...................................................... [ 15%]
........................................................................ [ 31%]
........................................................................ [ 47%]
........................................................................ [ 62%]
................ssssssssssssss.......................................... [ 78%]
........................................................................ [ 94%]
..........................                                               [100%]
=============================== warnings summary ===
```

### Package tests: packages/lexigram-vector

- Scope: `packages/lexigram-vector/tests`
- Command: `uv run pytest packages/lexigram-vector/tests -q -m not integration --cov=packages/lexigram.vector`
- Status: **PASS**
- Exit code: `0`
- Duration: `4059 ms`
- Parsed summary: `533 passed, 20 deselected, 4 warnings in 2.79s`
- Counters: passed=533, total=533, failed=0, skipped=0, warnings=4, coverage=78.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:18:43 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 13%]
........................................................................ [ 27%]
........................................................................ [ 40%]
........................................................................ [ 54%]
........................................................................ [ 67%]
........................................................................ [ 81%]
........................................................................ [ 94%]
.............................                       
```

### Package tests: packages/lexigram-web

- Scope: `packages/lexigram-web/tests`
- Command: `uv run pytest packages/lexigram-web/tests -q -m not integration --cov=packages/lexigram.web`
- Status: **PASS**
- Exit code: `0`
- Duration: `14425 ms`
- Parsed summary: `1392 passed, 7 skipped, 7 deselected, 6 warnings in 12.92s`
- Counters: passed=1392, total=1399, failed=0, skipped=7, warnings=6, coverage=81.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:18:47 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
sss..................................................................... [  5%]
........................................................................ [ 10%]
........................................................................ [ 15%]
............................................................s........... [ 20%]
........................................................................ [ 25%]
........................................................................ [ 30%]
.........................s.............................................. [ 36%]
....................................................
```

### Package tests: packages/lexigram-webhook

- Scope: `packages/lexigram-webhook/tests`
- Command: `uv run pytest packages/lexigram-webhook/tests -q -m not integration --cov=packages/lexigram.webhook`
- Status: **PASS**
- Exit code: `0`
- Duration: `2713 ms`
- Parsed summary: `336 passed, 4 warnings in 1.48s`
- Counters: passed=336, total=336, failed=0, skipped=0, warnings=4, coverage=90.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:19:02 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
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
- Duration: `13676 ms`
- Parsed summary: `559 passed, 23 deselected, 4 warnings in 12.45s`
- Counters: passed=559, total=559, failed=0, skipped=0, warnings=4, coverage=73.0%
- Example failures: none
- Output snippet:

```text
2026-08-29 19:19:04 [debug    ] module_decorated               _logger_name=lexigram.di.module.decorator controllers=0 exports=0 imports=0 is_global=False module=TestingModule providers=0
........................................................................ [ 12%]
........................................................................ [ 25%]
........................................................................ [ 38%]
........................................................................ [ 51%]
........................................................................ [ 64%]
........................................................................ [ 77%]
........................................................................ [ 90%]
....................................................
```

