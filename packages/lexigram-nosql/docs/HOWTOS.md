---
title: lexigram-nosql How-Tos
description: Task-oriented recipes for common NoSQL operations.
---

## Wire a Document Store in Your App

```python
from lexigram import Application
from lexigram.nosql import NoSQLModule, NoSQLConfig

app = Application(name="myapp")
app.add_module(
    NoSQLModule.configure(NoSQLConfig(driver="mongodb"))
)
await app.start()
```

## Store and Query Documents

```python
from lexigram.contracts.data.nosql import DocumentStoreProtocol


class ProfileService:
    def __init__(self, store: DocumentStoreProtocol) -> None:
        self._collection = store.collection("profiles")

    async def create_profile(self, user_id: str, name: str) -> None:
        await self._collection.insert_one({
            "_id": user_id,
            "name": name,
            "created_at": clock.now(),
        })

    async def get_profile(self, user_id: str) -> dict | None:
        return await self._collection.find_one({"_id": user_id})

    async def search_by_name(self, name: str) -> list[dict]:
        results = []
        async for doc in self._collection.find(
            {"name": {"$regex": name, "$options": "i"}},
            limit=20,
        ):
            results.append(doc)
        return results
```

## Use a Repository with Entity Mapping

```python
from dataclasses import dataclass
from lexigram.nosql.repository.base import DocumentRepository


@dataclass
class Product:
    sku: str
    name: str
    price: float
    in_stock: bool = True


class ProductRepository(DocumentRepository[Product, str]):
    collection_name = "products"
    id_field = "sku"

    async def _document_to_entity(self, doc: dict) -> Product:
        return Product(**doc)

    async def _entity_to_document(self, entity: Product) -> dict:
        return {
            "sku": entity.sku,
            "name": entity.name,
            "price": entity.price,
            "in_stock": entity.in_stock,
        }


# Usage
repo = ProductRepository(store)
product = await repo.save(Product(sku="ABC-123", name="Widget", price=9.99))
found = await repo.get("ABC-123")
deleted = await repo.delete("ABC-123")
```

## Run an Aggregation Pipeline

```python
from lexigram.nosql import AggregationPipeline


async def top_sellers(
    store: DocumentStoreProtocol, days: int = 30
) -> list[dict]:
    pipeline = (
        AggregationPipeline()
        .match({"created_at": {"$gte": clock.now() - timedelta(days=days)}})
        .group("product_id", {"total_sold": {"$sum": "$quantity"}})
        .sort([("total_sold", -1)])
        .limit(10)
    )
    results = []
    async for doc in store.collection("orders").aggregate(pipeline.build()):
        results.append(doc)
    return results
```

## Apply Schema Migrations

```python
from lexigram.nosql import MigrationManager, CreateIndex, AddField

manager = MigrationManager(db_name="myapp")

# Create an index
manager.add(CreateIndex("users", [("email", 1)], unique=True))

# Add a field with default value
manager.add(AddField("users", "phone", default=""))

await manager.apply()

# Track applied migrations
pending = manager.pending()
```

## Connect with DynamoDB Local for Development

```python
from lexigram.nosql import NoSQLConfig

config = NoSQLConfig(
    driver="mongodb",  # DynamoDB support requires installing lexigram-nosql[dynamodb]
)
```

For DynamoDB Local:

```python
from lexigram.nosql.config import DynamoDBConfig

dynamo_config = DynamoDBConfig(
    table_name="myapp",
    region="us-east-1",
    endpoint_url="http://localhost:8000",
    pk_field="pk",
)
```

## Configure Named Multi-Backend Stores

```yaml
nosql:
  backends:
    - name: primary
      driver: mongodb
      primary: true
      mongodb:
        uri: mongodb://localhost:27017
        database: app
    - name: audit
      driver: mongodb
      mongodb:
        uri: mongodb://localhost:27017
        database: audit_logs
```

```python
from typing import Annotated
from lexigram.di.markers import Named


class AuditService:
    def __init__(
        self,
        primary: DocumentStoreProtocol,
        audit_store: Annotated[DocumentStoreProtocol, Named("audit")],
    ) -> None:
        self.primary = primary
        self.audit_store = audit_store
```

## Test with an In-Memory Backend

```python
from lexigram.nosql import NoSQLModule


# In tests, NoSQLModule.stub() uses in-memory defaults
app = Application(name="test-app", testing=True)
app.add_module(NoSQLModule.stub())
await app.start()
```
