---
title: lexigram-sql Quickstart
description: Install, configure, and run SQL database access in under 5 minutes.
---

:::note
Lexigram is **alpha (0.1.x)** — public APIs may change before 1.0.
:::

## Install

```bash
uv add lexigram-sql
```

`lexigram` (core) and `lexigram-contracts` are pulled in automatically. For Postgres or MySQL, add the driver extra:

```bash
uv add "lexigram-sql[postgres]"    # asyncpg
uv add "lexigram-sql[mysql]"       # aiomysql
```

---

## Minimal Setup

Configure a database and boot it with `DatabaseModule`:

```python
import asyncio
from lexigram import Application
from lexigram.sql import DatabaseModule


async def main():
    async with Application.boot(
        name="my-app",
        modules=[DatabaseModule.configure("sqlite+aiosqlite:///example.db")],
    ) as app:
        print("Database connected")


asyncio.run(main())
```

---

## Define a Repository

```python
from dataclasses import dataclass
from lexigram.domain import DomainModel
from lexigram.sql import GenericRepository


@dataclass
class User(DomainModel):
    id: int | None = None
    name: str = ""
    email: str = ""


repo = GenericRepository[User, int](
    provider=db_provider,  # resolved from container
    table_name="users",
    entity_class=User,
    key_field="id",
)
```

---

## Next Steps

- [Guide](./GUIDE.md) — mental model, repositories, queries, migrations
- [How-Tos](./HOWTOS.md) — task-oriented recipes
- [Configuration](./CONFIGURATION.md) — every config key
