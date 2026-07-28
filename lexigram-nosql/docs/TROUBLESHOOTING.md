---
title: lexigram-nosql Troubleshooting
description: Common errors, their causes, and fixes.
---

## Connection Refused

**Error:** `NoSQLConnectionError` or `ServerSelectionTimeoutError`

**Cause:** The MongoDB/Firestore/DynamoDB host is unreachable — wrong URI, wrong port, or the service isn't running.

**Fix:**
- Verify the URI in config: `nosql.mongodb.uri` or `LEX_NOSQL__MONGODB__URI`.
- For MongoDB, confirm the server is running: `mongosh --eval "db.runCommand({ ping: 1 })"`.
- For Firestore, check `project_id` and `credentials_json` are correct.
- For DynamoDB Local, confirm `endpoint_url` points to the local instance.

## Authentication Failure

**Error:** `NoSQLConnectionError` with "Authentication failed" message

**Cause:** Wrong credentials or missing `auth_source`.

**Fix:**
```yaml
nosql:
  mongodb:
    uri: mongodb://user:password@host:27017
    auth_source: admin  # default is "admin"
```

## Document Not Found

**Error:** `DocumentNotFoundError`

**Cause:** `CollectionProtocol.find_one` or `DocumentRepository.get` returned `None` — no document matches the given ID or filter.

**Fix:**
- Check the document ID exists: `await collection.find_one({"_id": doc_id})`.
- Verify the collection name is correct.
- If soft-delete is enabled, the document may have been soft-deleted.

## Duplicate Key on Insert

**Error:** `DuplicateKeyError`

**Cause:** An insert or upsert violated a unique index.

**Fix:**
- Use `update_one` with `upsert=True` instead of `insert_one` for upsert semantics.
- Check the unique index definition: `await collection.list_indexes()`.

## Unsupported Driver

**Error:** `ValueError("Unsupported NoSQL driver: ...")`

**Cause:** `config.driver` is set to a value other than `"mongodb"` or `"firestore"`.

**Fix:**
```yaml
nosql:
  driver: mongodb  # or "firestore"
```

DynamoDB uses `DynamoDBConfig` directly and is configurable through `backends`.

## Transaction Failed

**Error:** `TransactionError`

**Cause:** Multi-document transaction could not be committed — usually a conflict or timeout in MongoDB replica sets.

**Fix:**
- Ensure the MongoDB deployment is a replica set (transactions require replication).
- Retry the transaction with exponential backoff.
- Check `max_transaction_retry_time` in your driver config.

## Multi-Backend: Store Not Found

**Error:** Container resolution fails for `Annotated[DocumentStoreProtocol, Named("...")]`

**Cause:** The named backend isn't registered — either `backends` is empty or the name doesn't match.

**Fix:**
- Verify the name in `Named(...)` matches a `name` field in `nosql.backends`.
- Ensure `backends` is non-empty in your config.
- Check the application.yaml section — missing indentation is a common cause.

## Health Check Fails After Boot

**Error:** Provider health check returns `DEGRADED` or `UNHEALTHY`

**Cause:** The store connected on boot but lost connectivity.

**Fix:**
- Check the database server logs.
- Verify network/firewall rules.
- Set `nosql.health_check_timeout` higher (default 5s) for slow networks.

## DynamoDB provisioned throughput exceeded

**Symptom:** `ProvisionedThroughputExceededException` wrapped as `NoSQLError`

**Cause:** The DynamoDB table's read/write capacity is insufficient for the current request volume.

**Fix:** Increase provisioned throughput or switch to on-demand billing. Implement retry with exponential backoff in your application.

```python
from lexigram.nosql.config import DynamoDBConfig

config = DynamoDBConfig(
    table_name="my-table",
    region="us-east-1",
)
```

Consider enabling DynamoDB auto-scaling or on-demand capacity mode in the AWS console.

## Firestore project not found or credentials invalid

**Error:** `NoSQLConnectionError: 404 Project 'my-project' not found` or `403 The caller does not have permission`

**Cause:** The `project_id` in `FirestoreConfig` is wrong, or the service account credentials are invalid or missing required roles.

**Fix:** Verify the GCP project ID. Ensure the service account has the `Cloud Datastore User` role. Check the `credentials_json` path.

```yaml
nosql:
  driver: firestore
  firestore:
    project_id: my-gcp-project
    credentials_json: "/path/to/service-account-key.json"
```

Test locally with `gcloud auth application-default login` if using ADC.

## MongoDB write concern timeout

**Error:** `TransactionError` or `NoSQLConnectionError` with "Write Concern timeout"

**Cause:** `write_concern_w` is set to `"majority"` but not enough replica set members are available.

**Fix:** Lower the write concern, or check replica set health. For standalone MongoDB use `w: 1`.

```yaml
nosql:
  mongodb:
    write_concern_w: 1              # Primary only
    socket_timeout_ms: 30000        # Increase timeout
```

## DocumentValidationError — Schema violation

**Error:** `DocumentValidationError: Document failed validation: field 'email' is required`

**Cause:** The document does not satisfy the collection's schema validator rules.

**Fix:** Ensure all required fields are present. If no validation is intended, remove the validator on the collection.

```python
await collection.insert_one({
    "_id": "user-1",
    "email": "user@example.com",
    "name": "Alice",
})
```

## DynamoDB table not found

**Error:** `ResourceNotFoundException` wrapped as `NoSQLError`

**Cause:** The DynamoDB table specified in `DynamoDBConfig.table_name` does not exist in the configured region.

**Fix:** Create the table first, or verify the `region` and `table_name` match an existing table.

```bash
aws dynamodb create-table \
    --table-name lexigram \
    --attribute-definitions AttributeName=_id,AttributeType=S \
    --key-schema AttributeName=_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

For DynamoDB Local, ensure `endpoint_url` points to the running local instance.
