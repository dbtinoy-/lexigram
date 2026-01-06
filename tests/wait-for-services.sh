#!/usr/bin/env bash
# Wait for Docker Compose services to be ready before running integration tests.
set -euo pipefail

TIMEOUT="${WAIT_TIMEOUT:-30}"

wait_for_port() {
    local name="$1"
    local port="$2"
    echo -n "Waiting for $name on port $port..."
    timeout "$TIMEOUT" bash -c "until nc -z localhost $port 2>/dev/null; do sleep 1; done"
    echo " ready."
}

# Core services
wait_for_port "PostgreSQL" 15432
wait_for_port "Redis" 16379

# Optional services — only wait if running
if nc -z localhost 19092 2>/dev/null; then
    wait_for_port "Kafka" 19092
fi
if nc -z localhost 19200 2>/dev/null; then
    wait_for_port "Elasticsearch" 19200
fi
if nc -z localhost 17017 2>/dev/null; then
    wait_for_port "MongoDB" 17017
fi
if nc -z localhost 16333 2>/dev/null; then
    wait_for_port "Qdrant" 16333
fi
if nc -z localhost 17687 2>/dev/null; then
    wait_for_port "Neo4j Bolt" 17687
fi

echo "All requested services are ready."
