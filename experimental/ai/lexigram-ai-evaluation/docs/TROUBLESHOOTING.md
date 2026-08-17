# Troubleshooting

Common issues and how to fix them.

---

## Problem: Evaluator not found

**Cause:**
You haven't registered an evaluator or misspelled its name.

**Solution:**
```python
from lexigram.ai.evaluation import EvaluationProvider
# Ensure it's registered in the module
```

---

## Problem: Embedding model fails

**Cause:**
Embedding provider not configured or API key missing.

**Solution:**
```bash
# Configure embedding model
export LEX_AI_EVALUATION__EMBEDDING_MODEL="text-embedding-3-small"
```

---

## Problem: Threshold too strict

**Cause:**
Score never passes the threshold (default 0.8).

**Solution:**
```python
from lexigram.ai.evaluation.config import EvaluationConfig

config = EvaluationConfig(default_threshold=0.5)
EvaluationModule.configure(config)
```

---

## Problem: Timeout during batch run

**Cause:**
Too many samples or evaluator taking too long.

**Solution:**
```python
config = EvaluationConfig(timeout_seconds=120)
# Or limit max_samples
config = EvaluationConfig(max_samples=50)
```

---

## Debug Tips

- enable verbose logging for the evaluation package
- check `EvaluationRunContext` for detailed error info
- verify evaluator type matches your metric needs

---

## Still Stuck?

- check the evaluation docs
- open an issue on GitHub
- review example tests in `tests/`