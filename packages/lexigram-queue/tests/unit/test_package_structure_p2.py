from __future__ import annotations

from pathlib import Path

from lexigram.queue.backends.kafka import KafkaQueue
from lexigram.queue.backends.memory import InMemoryQueue
from lexigram.queue.backends.rabbitmq import RabbitMQQueue
from lexigram.queue.backends.redis import RedisQueue
from lexigram.queue.backends.sqs import SQSQueue

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PACKAGE_ROOT / "src/lexigram/queue"


def test_queue_backends_directory_is_canonical() -> None:
    assert (SRC_ROOT / "backends").is_dir()
    assert (SRC_ROOT / "backends/memory.py").is_file()
    assert (SRC_ROOT / "backends/redis.py").is_file()
    assert (SRC_ROOT / "backends/rabbitmq.py").is_file()
    assert (SRC_ROOT / "backends/kafka.py").is_file()
    assert (SRC_ROOT / "backends/sqs.py").is_file()
    assert not (SRC_ROOT / "memory.py").exists()
    assert not (SRC_ROOT / "redis.py").exists()
    assert not (SRC_ROOT / "rabbitmq.py").exists()
    assert not (SRC_ROOT / "kafka.py").exists()
    assert not (SRC_ROOT / "sqs.py").exists()


def test_queue_backend_classes_remain_in_backend_modules() -> None:
    assert InMemoryQueue.__module__ == "lexigram.queue.backends.memory"
    assert RedisQueue.__module__ == "lexigram.queue.backends.redis"
    assert RabbitMQQueue.__module__ == "lexigram.queue.backends.rabbitmq"
    assert KafkaQueue.__module__ == "lexigram.queue.backends.kafka"
    assert SQSQueue.__module__ == "lexigram.queue.backends.sqs"
