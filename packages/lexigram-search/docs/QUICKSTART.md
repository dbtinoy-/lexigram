---
title: lexigram-search Quickstart
description: Install, connect a search backend, index documents, and run your first query.
---

:::note[Maturity]
`lexigram-search` is **alpha (0.1.x)** and MIT-licensed. Public APIs may change before 1.0.
:::

## Install

```bash
uv add lexigram-search
```

For a specific backend, install with extras:

```bash
# MeiliSearch (default)
uv add "lexigram-search[meilisearch]"
# Elasticsearch
uv add "lexigram-search[elasticsearch]"
# PostgreSQL full-text
uv add "lexigram-search[postgres]"
# All backends
uv add "lexigram-search[search-all]"
```

## Minimal Example

```python
import asyncio

from lexigram import Application, LexigramConfig
from lexigram.search import SearchProvider, SearchConfig
from lexigram.search.config import BackendType


async def main():
    config = LexigramConfig.from_yaml("application.yaml")
    app = Application(name="my-app", config=config)
    app.add_provider(SearchProvider.with_memory())

    async with app.boot():
        # Resolve the search engine
        from lexigram.contracts.search import SearchEngineProtocol

        engine = await app.container.resolve(SearchEngineProtocol)

        # Index a document
        await engine.index_document("doc-1", {"title": "Hello world", "content": "Lexigram search works"})

        # Search
        result = await engine.search("hello")
        print(f"Found {result.total} result(s)")
        for hit in result.results:
            print(f"  - {hit.data['title']} (score: {hit.score})")


asyncio.run(main())
```

## Wiring

Add `SearchProvider` to your `Application`. The provider auto-discovers `SearchConfig` from the `search:` section of your YAML config:

```python
from lexigram.search import SearchProvider

app.add_provider(SearchProvider.configure(SearchConfig(
    backend_type=BackendType.MEILISEARCH,
)))
```

Or use the declarative `SearchModule`:

```python
from lexigram.search import SearchModule
from lexigram.search.config import SearchConfig

app.add_module(SearchModule.configure(SearchConfig(backend_type="meilisearch")))
```

## Next Steps

- [Guide](./GUIDE.md) — mental model, core concepts, best practices
- [Configuration](./CONFIGURATION.md) — every config key with defaults and env vars
- [How-Tos](./HOWTOS.md) — common recipes
