"""Unit tests for event adapters."""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from lexigram.events.exceptions import AdapterConnectionError

from lexigram.events.adapters.base import (
    AdapterConfig,
    DefaultMessageSerializer,
    MessageAdapter,
    MessageHeaders,
    MessageSerializer,
)
from lexigram.events.messages.event import Event


class _TestEvent(Event):
    """Test event for adapter testing."""

    data: str


class _TestMessageAdapter(MessageAdapter[_TestEvent]):
    """Test implementation of MessageAdapter."""

    def __init__(
        self, config: AdapterConfig, serializer: MessageSerializer | None = None,
    ):
        super().__init__(config, serializer)
        self.published_events: list[_TestEvent] = []
        self.subscriptions: dict[str, tuple[list[str], Callable]] = {}

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def publish(self, event: _TestEvent) -> None:
        if not self._connected:
            raise ConnectionError("Not connected")
        self.published_events.append(event)

    async def subscribe(
        self,
        event_types: list[str],
        handler: Callable[[_TestEvent], Any],
    ) -> str:
        subscription_id = str(len(self.subscriptions))
        self.subscriptions[subscription_id] = (event_types, handler)
        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> None:
        self.subscriptions.pop(subscription_id, None)


class TestAdapterConfig:
    """Test AdapterConfig functionality."""

    def test_default_config(self):
        """Test default configuration values."""
        config = AdapterConfig()
        assert config.connection_string == ""
        assert config.timeout == 30.0
        assert config.reconnect_attempts == 3
        assert config.reconnect_delay == 1.0
        assert config.enable_logging is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = AdapterConfig(
            connection_string="test://",
            timeout=60.0,
            reconnect_attempts=5,
            reconnect_delay=2.0,
            enable_logging=False,
        )
        assert config.connection_string == "test://"
        assert config.timeout == 60.0
        assert config.reconnect_attempts == 5
        assert config.reconnect_delay == 2.0
        assert config.enable_logging is False


class TestMessageHeaders:
    """Test MessageHeaders functionality."""

    def test_default_headers(self):
        """Test default header creation."""
        headers = MessageHeaders(event_type="TestEvent")
        assert headers.event_type == "TestEvent"
        assert headers.aggregate_id is None
        assert headers.aggregate_type is None
        assert headers.correlation_id is None
        assert headers.causation_id is None
        assert headers.metadata == {}
        assert isinstance(headers.timestamp, datetime)

    def test_full_headers(self):
        """Test headers with all fields."""
        timestamp = datetime.now(UTC)
        headers = MessageHeaders(
            event_type="OrderCreated",
            aggregate_id="order-123",
            aggregate_type="Order",
            timestamp=timestamp,
            correlation_id="corr-456",
            causation_id="cause-789",
            metadata={"key": "value"},
        )
        assert headers.event_type == "OrderCreated"
        assert headers.aggregate_id == "order-123"
        assert headers.aggregate_type == "Order"
        assert headers.timestamp == timestamp
        assert headers.correlation_id == "corr-456"
        assert headers.causation_id == "cause-789"
        assert headers.metadata == {"key": "value"}

    def test_to_dict(self):
        """Test converting headers to dictionary."""
        timestamp = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        headers = MessageHeaders(
            event_type="TestEvent",
            aggregate_id="agg-123",
            aggregate_type="TestAggregate",
            timestamp=timestamp,
            correlation_id="corr-456",
            causation_id="cause-789",
            metadata={"env": "test"},
        )
        result = headers.to_dict()
        expected = {
            "event_type": "TestEvent",
            "aggregate_id": "agg-123",
            "aggregate_type": "TestAggregate",
            "timestamp": "2023-01-01T12:00:00+00:00",
            "correlation_id": "corr-456",
            "causation_id": "cause-789",
            "env": "test",
        }
        assert result == expected

    def test_from_dict(self):
        """Test creating headers from dictionary."""
        data = {
            "event_type": "TestEvent",
            "aggregate_id": "agg-123",
            "aggregate_type": "TestAggregate",
            "timestamp": "2023-01-01T12:00:00+00:00",
            "correlation_id": "corr-456",
            "causation_id": "cause-789",
            "custom": "value",
        }
        headers = MessageHeaders.from_dict(data)
        assert headers.event_type == "TestEvent"
        assert headers.aggregate_id == "agg-123"
        assert headers.aggregate_type == "TestAggregate"
        assert headers.correlation_id == "corr-456"
        assert headers.causation_id == "cause-789"
        assert headers.metadata == {"custom": "value"}

    def test_from_dict_minimal(self):
        """Test creating headers from minimal dictionary."""
        data = {"event_type": "TestEvent"}
        headers = MessageHeaders.from_dict(data)
        assert headers.event_type == "TestEvent"
        assert headers.aggregate_id is None
        assert headers.metadata == {}


class TestDefaultMessageSerializer:
    """Test DefaultMessageSerializer functionality."""

    def test_initialization(self):
        """Test serializer initialization."""
        serializer = DefaultMessageSerializer()
        assert serializer._event_types == {}

    def test_register_event_type(self):
        """Test registering a single event type."""
        serializer = DefaultMessageSerializer()
        serializer.register_event_type(_TestEvent)
        assert serializer._event_types == {"_TestEvent": _TestEvent}

    def test_register_event_types(self):
        """Test registering multiple event types."""
        serializer = DefaultMessageSerializer()
        serializer.register_event_types(_TestEvent)
        assert serializer._event_types == {"_TestEvent": _TestEvent}

    def test_serialize_pydantic_event(self):
        """Test serializing a Pydantic event."""
        serializer = DefaultMessageSerializer()
        event = _TestEvent(aggregate_id=uuid4(), data="test data")
        data = serializer.serialize(event)
        assert isinstance(data, bytes)
        # Should contain JSON data
        json_str = data.decode()
        assert "test data" in json_str

    def test_deserialize_registered_event(self):
        """Test deserializing a registered event."""
        serializer = DefaultMessageSerializer()
        serializer.register_event_type(_TestEvent)

        event = _TestEvent(aggregate_id=uuid4(), data="test data")
        data = serializer.serialize(event)
        deserialized = serializer.deserialize(data, "_TestEvent")

        assert isinstance(deserialized, _TestEvent)
        assert deserialized.data == "test data"

    def test_deserialize_unregistered_event(self):
        """Test deserializing an unregistered event raises error."""
        serializer = DefaultMessageSerializer()
        data = b'{"event_type": "UnknownEvent"}'

        with pytest.raises(ValueError, match="Unknown event type: UnknownEvent"):
            serializer.deserialize(data, "UnknownEvent")


class TestMessageAdapter:
    """Test MessageAdapter base functionality."""

    def test_initialization(self):
        """Test adapter initialization."""
        config = AdapterConfig()
        adapter = _TestMessageAdapter(config)

        assert adapter.config == config
        assert isinstance(adapter.serializer, DefaultMessageSerializer)
        assert not adapter.is_connected

    def test_initialization_with_serializer(self):
        """Test adapter initialization with custom serializer."""
        config = AdapterConfig()
        serializer = DefaultMessageSerializer()
        adapter = _TestMessageAdapter(config, serializer)

        assert adapter.serializer == serializer

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Test connecting and disconnecting."""
        adapter = _TestMessageAdapter(AdapterConfig())

        await adapter.connect()
        assert adapter.is_connected

        await adapter.disconnect()
        assert not adapter.is_connected

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        adapter = _TestMessageAdapter(AdapterConfig())

        async with adapter:
            assert adapter.is_connected

        assert not adapter.is_connected

    @pytest.mark.asyncio
    async def test_publish_when_connected(self):
        """Test publishing when connected."""
        adapter = _TestMessageAdapter(AdapterConfig())
        await adapter.connect()

        event = _TestEvent(aggregate_id=uuid4(), data="test")
        await adapter.publish(event)

        assert len(adapter.published_events) == 1
        assert adapter.published_events[0] == event

    @pytest.mark.asyncio
    async def test_publish_when_disconnected(self):
        """Test publishing when disconnected raises error."""
        adapter = _TestMessageAdapter(AdapterConfig())
        event = _TestEvent(aggregate_id=uuid4(), data="test")

        with pytest.raises(ConnectionError, match="Not connected"):
            await adapter.publish(event)

    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe(self):
        """Test subscribing and unsubscribing."""
        adapter = _TestMessageAdapter(AdapterConfig())
        handler = MagicMock()

        # Subscribe
        subscription_id = await adapter.subscribe(["TestEvent"], handler)
        assert subscription_id in adapter.subscriptions
        assert adapter.subscriptions[subscription_id] == (["TestEvent"], handler)

        # Unsubscribe
        await adapter.unsubscribe(subscription_id)
        assert subscription_id not in adapter.subscriptions

    def test_create_headers(self):
        """Test creating headers from event."""
        adapter = _TestMessageAdapter(AdapterConfig())
        event = _TestEvent(aggregate_id=uuid4(), data="test")

        headers = adapter._create_headers(event)
        assert headers.event_type == "_TestEvent"


class TestAzureServiceBusAdapter:
    """Test Azure Service Bus adapter."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        from lexigram.events.adapters.azure_servicebus import AzureServiceBusAdapterConfig

        return AzureServiceBusAdapterConfig(
            connection_string="test-connection-string",
            topic_name="test-topic",
            subscription_name="test-subscription",
        )

    @pytest.fixture
    def adapter(self, config):
        """Create test adapter."""
        from lexigram.events.adapters.azure_servicebus import AzureServiceBusAdapter

        return AzureServiceBusAdapter(config)

    @pytest.mark.asyncio
    async def test_connect_success(self, adapter, config):
        """Test successful connection."""
        mock_client = AsyncMock()
        mock_sender = AsyncMock()

        with patch(
            "azure.servicebus.aio.ServiceBusClient.from_connection_string",
        ) as mock_from_conn:
            mock_from_conn.return_value = mock_client
            mock_client.get_topic_sender = AsyncMock(return_value=mock_sender)

            await adapter.connect()

            assert adapter.is_connected
            assert adapter._client == mock_client
            assert adapter._sender == mock_sender
            mock_from_conn.assert_called_once_with(config.connection_string.get_secret_value())
            mock_client.get_topic_sender.assert_called_once_with(
                topic_name=config.topic_name,
            )

    @pytest.mark.asyncio
    async def test_connect_failure(self, adapter):
        """Test connection failure."""
        with patch(
            "azure.servicebus.aio.ServiceBusClient.from_connection_string",
            side_effect=Exception("Connection failed"),
        ):
            with pytest.raises(
                AdapterConnectionError, match="Azure Service Bus",
            ):
                await adapter.connect()

    @pytest.mark.asyncio
    async def test_disconnect(self, adapter):
        """Test disconnecting."""
        mock_client = AsyncMock()
        mock_sender = AsyncMock()
        adapter._client = mock_client
        adapter._sender = mock_sender
        adapter._connected = True

        await adapter.disconnect()

        assert not adapter.is_connected
        mock_sender.close.assert_called_once()
        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_success(self, adapter):
        """Test successful publishing."""
        adapter._connected = True
        mock_sender = AsyncMock()
        adapter._sender = mock_sender

        event = _TestEvent(aggregate_id=uuid4(), data="test")

        with patch("azure.servicebus.ServiceBusMessage") as mock_message:
            mock_message_instance = MagicMock()
            mock_message.return_value = mock_message_instance

            await adapter.publish(event)

            mock_message.assert_called_once()
            mock_sender.send_messages.assert_called_once_with(mock_message_instance)

    @pytest.mark.asyncio
    async def test_publish_not_connected(self, adapter):
        """Test publishing when not connected."""
        event = _TestEvent(aggregate_id=uuid4(), data="test")

        with pytest.raises(RuntimeError, match="Not connected to Azure Service Bus"):
            await adapter.publish(event)

    @pytest.mark.asyncio
    async def test_subscribe_success(self, adapter, config):
        """Test successful subscription."""
        adapter._connected = True
        mock_client = AsyncMock()
        mock_receiver = AsyncMock()
        adapter._client = mock_client
        mock_client.get_subscription_receiver = AsyncMock(return_value=mock_receiver)

        handler = MagicMock()

        with patch("asyncio.create_task") as mock_create_task:
            mock_task = AsyncMock()
            # Ensure add_done_callback is a regular callable in tests so it doesn't return an un-awaited coroutine
            mock_task.add_done_callback = MagicMock()
            coro_holder: dict[str, object] = {}

            def _fake_create_task(coro, **kwargs):
                coro_holder["coro"] = coro
                return mock_task

            mock_create_task.side_effect = _fake_create_task
            subscription_id = await adapter.subscribe(["TestEvent"], handler)

            # Close the created coroutine to avoid 'coroutine was never awaited' warnings from test harness
            if "coro" in coro_holder:
                try:
                    coro_holder["coro"].close()
                except RuntimeError:
                    pass

            assert subscription_id in adapter._receivers
            assert subscription_id in adapter._receiver_tasks
            assert adapter._receivers[subscription_id] == mock_receiver
            assert adapter._receiver_tasks[subscription_id] == mock_task
            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_not_connected(self, adapter):
        """Test subscribing when not connected."""
        handler = MagicMock()

        with pytest.raises(RuntimeError, match="Not connected to Azure Service Bus"):
            await adapter.subscribe(["TestEvent"], handler)

    @pytest.mark.asyncio
    async def test_unsubscribe(self, adapter):
        """Test unsubscribing."""
        mock_receiver = AsyncMock()

        # Create a real task that can be cancelled
        task = asyncio.create_task(asyncio.sleep(0))

        subscription_id = "test-sub"

        adapter._receivers[subscription_id] = mock_receiver
        adapter._receiver_tasks[subscription_id] = task

        await adapter.unsubscribe(subscription_id)

        assert subscription_id not in adapter._receivers
        assert subscription_id not in adapter._receiver_tasks
        assert task.cancelled()
        mock_receiver.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_batch(self, adapter):
        """Test publishing batch of events."""
        adapter._connected = True
        mock_sender = AsyncMock()
        adapter._sender = mock_sender

        events = [
            _TestEvent(aggregate_id=uuid4(), data="test1"),
            _TestEvent(aggregate_id=uuid4(), data="test2"),
        ]

        with patch("azure.servicebus.ServiceBusMessage") as mock_message:
            mock_message_instances = [MagicMock(), MagicMock()]
            mock_message.side_effect = mock_message_instances

            await adapter.publish_batch(events)

            assert mock_message.call_count == 2
            mock_sender.send_messages.assert_called_once_with(mock_message_instances)

    @pytest.mark.asyncio
    async def test_schedule_message(self, adapter):
        """Test scheduling a message."""
        adapter._connected = True
        mock_sender = AsyncMock()
        adapter._sender = mock_sender
        mock_sender.schedule_messages.return_value = [12345]

        event = _TestEvent(aggregate_id=uuid4(), data="test")
        scheduled_time = datetime.now(UTC)

        with patch("azure.servicebus.ServiceBusMessage") as mock_message:
            mock_message_instance = MagicMock()
            mock_message.return_value = mock_message_instance

            result = await adapter.schedule_message(event, scheduled_time)

            assert result == 12345
            mock_sender.schedule_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_scheduled_message(self, adapter):
        """Test canceling a scheduled message."""
        adapter._connected = True
        mock_sender = AsyncMock()
        adapter._sender = mock_sender

        await adapter.cancel_scheduled_message(12345)

        mock_sender.cancel_scheduled_messages.assert_called_once_with(12345)


class TestKafkaAdapter:
    """Test Kafka adapter."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        from lexigram.events.adapters.kafka import KafkaAdapterConfig

        return KafkaAdapterConfig(
            connection_string="localhost:9092",
            topic_prefix="test.",
            group_id="test-group",
        )

    @pytest.fixture
    def adapter(self, config):
        """Create test adapter."""
        from lexigram.events.adapters.kafka import KafkaAdapter

        return KafkaAdapter(config)

    @pytest.mark.asyncio
    async def test_connect_success(self, adapter, config):
        """Test successful connection."""
        mock_producer = AsyncMock()

        mock_aiokafka = MagicMock()
        mock_aiokafka.AIOKafkaProducer = mock_producer_class = MagicMock(return_value=mock_producer)

        with patch.dict("sys.modules", {"aiokafka": mock_aiokafka}):
            await adapter.connect()

            assert adapter.is_connected
            assert adapter._producer == mock_producer
            mock_producer_class.assert_called_once()
            mock_producer.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self, adapter):
        """Test connection failure."""
        from lexigram.events.exceptions import AdapterConnectionError
        mock_aiokafka = MagicMock()
        mock_aiokafka.AIOKafkaProducer = MagicMock(side_effect=Exception("Connection failed"))
        with patch.dict("sys.modules", {"aiokafka": mock_aiokafka}):
            with pytest.raises(AdapterConnectionError, match="Kafka"):
                await adapter.connect()

    @pytest.mark.asyncio
    async def test_disconnect(self, adapter):
        """Test disconnecting."""
        mock_producer = AsyncMock()
        adapter._producer = mock_producer
        adapter._connected = True

        await adapter.disconnect()

        assert not adapter.is_connected
        mock_producer.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_success(self, adapter):
        """Test successful publishing."""
        adapter._connected = True
        mock_producer = AsyncMock()
        adapter._producer = mock_producer

        event = _TestEvent(aggregate_id=uuid4(), data="test")

        await adapter.publish(event)

        mock_producer.send_and_wait.assert_called_once()
        call_args = mock_producer.send_and_wait.call_args
        assert call_args[1]["topic"] == "test._TestEvent"
        assert call_args[1]["key"] == str(event.aggregate_id).encode()

    @pytest.mark.asyncio
    async def test_publish_not_connected(self, adapter):
        """Test publishing when not connected."""
        event = _TestEvent(aggregate_id=uuid4(), data="test")

        with pytest.raises(RuntimeError, match="Not connected to Kafka"):
            await adapter.publish(event)

    @pytest.mark.asyncio
    async def test_subscribe_success(self, adapter, config):
        """Test successful subscription."""
        adapter._connected = True
        mock_consumer = AsyncMock()

        mock_aiokafka = MagicMock()
        mock_aiokafka.AIOKafkaConsumer = mock_consumer_class = MagicMock(return_value=mock_consumer)

        with patch.dict("sys.modules", {"aiokafka": mock_aiokafka}):
            with patch("asyncio.create_task") as mock_create_task:
                mock_task = AsyncMock()
                # Ensure add_done_callback is a regular callable in tests so it doesn't return an un-awaited coroutine
                mock_task.add_done_callback = MagicMock()
                coro_holder: dict[str, object] = {}

                def _fake_create_task(coro, **kwargs):
                    coro_holder["coro"] = coro
                    return mock_task

                mock_create_task.side_effect = _fake_create_task

                subscription_id = await adapter.subscribe(["TestEvent"], MagicMock())

                # Close the created coroutine to avoid 'coroutine was never awaited' warnings from test harness
                if "coro" in coro_holder:
                    try:
                        coro_holder["coro"].close()
                    except RuntimeError:
                        pass

                assert subscription_id in adapter._consumers
                assert subscription_id in adapter._consumer_tasks
                assert adapter._consumers[subscription_id] == mock_consumer
                assert adapter._consumer_tasks[subscription_id] == mock_task
                mock_consumer.start.assert_called_once()
                mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_not_connected(self, adapter):
        """Test subscribing when not connected."""
        with pytest.raises(RuntimeError, match="Not connected to Kafka"):
            await adapter.subscribe(["TestEvent"], MagicMock())

    @pytest.mark.asyncio
    async def test_unsubscribe(self, adapter):
        """Test unsubscribing."""
        mock_consumer = AsyncMock()

        task = asyncio.create_task(asyncio.sleep(0))

        subscription_id = "test-sub"

        adapter._consumers[subscription_id] = mock_consumer
        adapter._consumer_tasks[subscription_id] = task

        await adapter.unsubscribe(subscription_id)

        assert subscription_id not in adapter._consumers
        assert subscription_id not in adapter._consumer_tasks
        mock_consumer.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_batch(self, adapter):
        """Test publishing batch of events."""
        adapter._connected = True
        mock_producer = AsyncMock()
        adapter._producer = mock_producer

        events = [
            _TestEvent(aggregate_id=uuid4(), data="test1"),
            _TestEvent(aggregate_id=uuid4(), data="test2"),
        ]

        await adapter.publish_batch(events)

        assert mock_producer.send_and_wait.call_count == 2

    @pytest.mark.asyncio
    async def test_get_topic_partitions(self, adapter):
        """Test getting topic partitions."""
        adapter._connected = True
        mock_producer = AsyncMock()
        mock_producer.partitions_for.return_value = {0, 1, 2}
        adapter._producer = mock_producer

        partitions = await adapter.get_topic_partitions("test-topic")

        assert partitions == [0, 1, 2]
        mock_producer.partitions_for.assert_called_once_with("test-topic")


class TestRabbitMQAdapter:
    """Test RabbitMQ adapter."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        from lexigram.events.adapters.rabbitmq import RabbitMQAdapterConfig

        return RabbitMQAdapterConfig(
            connection_string="amqp://localhost/",
            exchange_name="test-events", # Changed from "test-exchange" to "test-events"
            routing_key_prefix="test.",
            timeout=10, # Added timeout
        )

    @pytest.fixture
    def adapter(self, config):
        """Create test adapter."""
        from lexigram.events.adapters.rabbitmq import RabbitMQAdapter

        return RabbitMQAdapter(config)

    @pytest.mark.asyncio
    async def test_connect_success(self, adapter, config):
        """Test successful connection."""
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()

        mock_aio_pika = MagicMock()
        mock_aio_pika.connect_robust = mock_connect = AsyncMock(return_value=mock_connection)
        mock_aio_pika.ExchangeType.TOPIC = "topic"
        mock_connection.channel.return_value = mock_channel
        mock_channel.declare_exchange.return_value = mock_exchange

        with patch.dict("sys.modules", {"aio_pika": mock_aio_pika}):
            await adapter.connect()

            assert adapter.is_connected
            assert adapter._connection == mock_connection
            assert adapter._channel == mock_channel
            assert adapter._exchange == mock_exchange

    @pytest.mark.asyncio
    async def test_connect_failure(self, adapter):
        """Test connection failure."""
        mock_aio_pika = MagicMock()
        mock_aio_pika.connect_robust = AsyncMock(side_effect=Exception("Connection failed"))
        with patch.dict("sys.modules", {"aio_pika": mock_aio_pika}):
            with pytest.raises(AdapterConnectionError, match="RabbitMQ"):
                await adapter.connect()

    @pytest.mark.asyncio
    async def test_disconnect(self, adapter):
        """Test disconnecting."""
        mock_connection = AsyncMock()
        adapter._connection = mock_connection
        adapter._connected = True

        await adapter.disconnect()

        assert not adapter.is_connected
        mock_connection.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_success(self, adapter):
        """Test successful publishing."""
        adapter._connected = True
        mock_exchange = AsyncMock()
        adapter._exchange = mock_exchange

        event = _TestEvent(aggregate_id=uuid4(), data="test")

        mock_message_instance = MagicMock()
        mock_aio_pika = MagicMock()
        mock_aio_pika.Message = mock_message = MagicMock(return_value=mock_message_instance)
        mock_aio_pika.DeliveryMode.PERSISTENT = "persistent"

        with patch.dict("sys.modules", {"aio_pika": mock_aio_pika}):
            await adapter.publish(event)

            mock_message.assert_called_once()
            mock_exchange.publish.assert_called_once_with(
                mock_message_instance, routing_key="test._TestEvent",
            )

    @pytest.mark.asyncio
    async def test_publish_not_connected(self, adapter):
        """Test publishing when not connected."""
        event = _TestEvent(aggregate_id=uuid4(), data="test")

        with pytest.raises(RuntimeError, match="Not connected to RabbitMQ"):
            await adapter.publish(event)

    @pytest.mark.asyncio
    async def test_subscribe_success(self, adapter, config):
        """Test successful subscription."""
        adapter._connected = True
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_queue = AsyncMock()
        adapter._channel = mock_channel
        adapter._exchange = mock_exchange
        mock_channel.declare_queue.return_value = mock_queue

        subscription_id = await adapter.subscribe(["TestEvent"], MagicMock())

        assert subscription_id in adapter._subscriptions
        sub = adapter._subscriptions[subscription_id]
        assert sub["queue"] == mock_queue
        assert sub["event_types"] == ["TestEvent"]
        mock_channel.declare_queue.assert_called_once()
        mock_queue.bind.assert_called_once_with(
            mock_exchange, routing_key="test.TestEvent",
        )
        mock_queue.consume.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_not_connected(self, adapter):
        """Test subscribing when not connected."""
        with pytest.raises(RuntimeError, match="Not connected to RabbitMQ"):
            await adapter.subscribe(["TestEvent"], MagicMock())

    @pytest.mark.asyncio
    async def test_unsubscribe(self, adapter):
        """Test unsubscribing."""
        mock_queue = AsyncMock()
        subscription_id = "test-sub"
        adapter._subscriptions[subscription_id] = {
            "queue": mock_queue,
            "consumer_tag": "tag123",
            "event_types": ["TestEvent"],
        }

        await adapter.unsubscribe(subscription_id)

        assert subscription_id not in adapter._subscriptions
        mock_queue.cancel.assert_called_once_with("tag123")

    @pytest.mark.asyncio
    async def test_publish_batch(self, adapter):
        """Test publishing batch of events."""
        adapter._connected = True
        mock_exchange = AsyncMock()
        adapter._exchange = mock_exchange

        events = [
            _TestEvent(aggregate_id=uuid4(), data="test1"),
            _TestEvent(aggregate_id=uuid4(), data="test2"),
        ]

        mock_message_instances = [MagicMock(), MagicMock()]
        mock_aio_pika = MagicMock()
        mock_aio_pika.Message = mock_message = MagicMock(side_effect=mock_message_instances)
        mock_aio_pika.DeliveryMode.PERSISTENT = "persistent"

        with patch.dict("sys.modules", {"aio_pika": mock_aio_pika}):
            await adapter.publish_batch(events)

            assert mock_message.call_count == 2
            assert mock_exchange.publish.call_count == 2
