# Quickstart

Get up and running in minutes.

---

## Install

```bash
uv add lexigram-ai-evaluation
```

---

## Basic Usage

```python
from lexigram import Application
from lexigram.di.module import Module, module

from lexigram.ai.evaluation import EvaluationModule

@module(imports=[EvaluationModule.configure()])
class AppModule(Module):
    pass

app = Application(modules=[AppModule])
```

---

## What Just Happened

- `EvaluationModule.configure()` creates and registers the evaluation subsystem
- `EvaluationProvider` boots the evaluator services into the DI container
- You can now resolve `EvaluatorProtocol` and `EvaluationHarnessProtocol`

---

## Next Steps

- [Guide](./GUIDE.md)
- [How-Tos](./HOWTOS.md)