# Integration Tests

This directory contains Docker Compose configuration and documentation for running integration tests that require external services.

## Quick Start

```bash
# Start all services
docker compose up -d

# Wait for services to be healthy
docker compose ps

# Run all integration tests
uv run pytest -m integration

# Stop all services
docker compose down -v
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 15432 | Database tests for lexigram-sql |
| Redis | 16379 | Cache tests for lexigram-cache |
| Kafka | 19092 | Message queue tests for lexigram-queue |
| MinIO | 19000 | Object storage tests for lexigram-storage |

### Service Health Checks

All services include health checks. Verify readiness with:

```bash
docker compose ps --format "table {{.Name}}\t{{.Status}}"
```

## Running Tests

### All Integration Tests

```bash
uv run pytest -m integration
```

### Specific Package Tests

```bash
# SQL tests
uv run pytest packages/lexigram-sql/tests -m integration

# Cache tests
uv run pytest packages/lexigram-cache/tests -m integration

# Queue tests
uv run pytest packages/lexigram-queue/tests -m integration

# Storage tests
uv run pytest packages/lexigram-storage/tests -m integration
```

### With Coverage

```bash
uv run pytest -m integration --cov --cov-report=html --cov-fail-under=80
```

## Service Markers

The lexigram-testing package provides pytest markers to selectively run tests based on required infrastructure:

| Marker | Description |
|--------|-------------|
| `@pytest.mark.integration` | Marks tests requiring external services (deselect with `-m "not integration"`) |
| `@pytest.mark.requires_postgres` | Skip unless PostgreSQL is available |
| `@pytest.mark.requires_redis` | Skip unless Redis is available |

### Usage Examples

```bash
# Run only PostgreSQL tests
uv run pytest -m requires_postgres

# Run Redis and cache tests
uv run pytest -m requires_redis

# Run all tests requiring PostgreSQL or Redis
uv run pytest -m "requires_postgres or requires_redis"
```

## CI Integration

Example GitHub Actions workflow for running integration tests on merge to main:

```yaml
name: Integration Tests

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Start services
        run: docker compose up -d
        
      - name: Wait for services
        run: sleep 15
        
      - name: Run integration tests
        run: uv run pytest -m integration --tb=short
        
      - name: Upload coverage
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage
          path: htmlcov/
          
      - name: Stop services
        if: always()
        run: docker compose down -v
```

## Troubleshooting

### Services Not Starting

```bash
# Check service logs
docker compose logs postgres
docker compose logs redis
docker compose logs kafka
docker compose logs minio
```

### Port Conflicts

If ports are already in use, stop conflicting services or modify `docker-compose.yml` to use different ports.

### Database Connection Issues

Ensure PostgreSQL is fully ready before running tests:
```bash
docker compose exec postgres pg_isready -U lexigram
```