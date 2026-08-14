"""Tests for admin notification models."""


from lexigram.admin.services.notifications.models import (
    Notification,
    NotificationChannel,
    NotificationRecipient,
    NotificationResult,
    NotificationType,
)


class TestNotificationType:
    """Tests for NotificationType enum."""

    def test_notification_type_user_events(self) -> None:
        """Test NotificationType user event values."""
        assert NotificationType.USER_CREATED.value == "user_created"
        assert NotificationType.USER_INVITED.value == "user_invited"
        assert NotificationType.USER_ACTIVATED.value == "user_activated"
        assert NotificationType.USER_DEACTIVATED.value == "user_deactivated"
        assert NotificationType.PASSWORD_RESET.value == "password_reset"
        assert NotificationType.PASSWORD_CHANGED.value == "password_changed"

    def test_notification_type_bulk_operations(self) -> None:
        """Test NotificationType bulk operation values."""
        assert NotificationType.BULK_STARTED.value == "bulk_started"
        assert NotificationType.BULK_PROGRESS.value == "bulk_progress"
        assert NotificationType.BULK_COMPLETED.value == "bulk_completed"
        assert NotificationType.BULK_FAILED.value == "bulk_failed"

    def test_notification_type_system_events(self) -> None:
        """Test NotificationType system event values."""
        assert NotificationType.SYSTEM_ALERT.value == "system_alert"
        assert NotificationType.SYSTEM_WARNING.value == "system_warning"
        assert NotificationType.SYSTEM_ERROR.value == "system_error"

    def test_notification_type_export_import(self) -> None:
        """Test NotificationType export/import values."""
        assert NotificationType.EXPORT_READY.value == "export_ready"
        assert NotificationType.IMPORT_COMPLETED.value == "import_completed"
        assert NotificationType.IMPORT_FAILED.value == "import_failed"

    def test_notification_type_members(self) -> None:
        """Test NotificationType has expected members."""
        members = list(NotificationType)
        assert len(members) == 18

    def test_notification_type_email_security(self) -> None:
        """Test NotificationType email security values."""
        assert NotificationType.EMAIL_VERIFICATION.value == "email_verification"
        assert NotificationType.EMAIL_OTP.value == "email_otp"

    def test_notification_type_from_string(self) -> None:
        """Test creating NotificationType from string."""
        assert NotificationType("user_created") == NotificationType.USER_CREATED
        assert NotificationType("bulk_completed") == NotificationType.BULK_COMPLETED


class TestNotificationChannel:
    """Tests for NotificationChannel enum."""

    def test_notification_channel_values(self) -> None:
        """Test NotificationChannel enum values."""
        assert NotificationChannel.EMAIL.value == "email"
        assert NotificationChannel.IN_APP.value == "in_app"
        assert NotificationChannel.PUSH.value == "push"

    def test_notification_channel_members(self) -> None:
        """Test NotificationChannel has expected members."""
        members = list(NotificationChannel)
        assert len(members) == 3


class TestNotificationRecipient:
    """Tests for NotificationRecipient dataclass."""

    def test_notification_recipient_creation(self) -> None:
        """Test creating NotificationRecipient."""
        recipient = NotificationRecipient(
            email="test@example.com",
            name="Test User",
            user_id="user-123",
        )
        assert recipient.email == "test@example.com"
        assert recipient.name == "Test User"
        assert recipient.user_id == "user-123"
        assert recipient.preferences == {}

    def test_notification_recipient_with_preferences(self) -> None:
        """Test NotificationRecipient with preferences."""
        recipient = NotificationRecipient(
            email="test@example.com",
            preferences={
                "notify_user_created": True,
                "notify_system_alert": False,
            },
        )
        assert recipient.can_receive(NotificationType.USER_CREATED) is True
        assert recipient.can_receive(NotificationType.SYSTEM_ALERT) is False

    def test_notification_recipient_default_preference(self) -> None:
        """Test NotificationRecipient default preference is True."""
        recipient = NotificationRecipient(email="test@example.com")
        assert recipient.can_receive(NotificationType.USER_CREATED) is True
        assert recipient.can_receive(NotificationType.SYSTEM_ERROR) is True


class TestNotification:
    """Tests for Notification dataclass."""

    def test_notification_creation(self) -> None:
        """Test creating Notification."""
        recipient = NotificationRecipient(email="test@example.com")
        notification = Notification(
            type=NotificationType.USER_CREATED,
            subject="Welcome",
            body="Your account has been created",
            recipients=[recipient],
        )
        assert notification.type == NotificationType.USER_CREATED
        assert notification.subject == "Welcome"
        assert notification.body == "Your account has been created"
        assert len(notification.recipients) == 1
        assert notification.channels == [NotificationChannel.EMAIL]

    def test_notification_with_channels(self) -> None:
        """Test Notification with custom channels."""
        recipient = NotificationRecipient(email="test@example.com")
        notification = Notification(
            type=NotificationType.SYSTEM_ALERT,
            subject="Alert",
            body="System alert",
            recipients=[recipient],
            channels=[NotificationChannel.EMAIL, NotificationChannel.PUSH],
        )
        assert notification.channels == [
            NotificationChannel.EMAIL,
            NotificationChannel.PUSH,
        ]

    def test_notification_with_data(self) -> None:
        """Test Notification with additional data."""
        recipient = NotificationRecipient(email="test@example.com")
        notification = Notification(
            type=NotificationType.BULK_COMPLETED,
            subject="Bulk Operation Complete",
            body="Your bulk operation has completed",
            recipients=[recipient],
            data={"total": 100, "processed": 100},
            html_body="<p>Your bulk operation has completed</p>",
            priority="high",
        )
        assert notification.data == {"total": 100, "processed": 100}
        assert notification.html_body == "<p>Your bulk operation has completed</p>"
        assert notification.priority == "high"


class TestNotificationResult:
    """Tests for NotificationResult dataclass."""

    def test_notification_result_all_sent(self) -> None:
        """Test NotificationResult when all recipients received the notification."""
        result = NotificationResult(
            notification_id="notif-123",
            recipients_sent=10,
            recipients_failed=0,
        )
        assert result.notification_id == "notif-123"
        assert result.recipients_sent == 10
        assert result.recipients_failed == 0
        assert result.errors == []

    def test_notification_result_partial_failure(self) -> None:
        """Test NotificationResult with per-recipient delivery failures.

        Partial failures are accumulated in ``errors``/``recipients_failed``
        and remain inside an ``Ok`` result — only a total delivery failure
        (all recipients failed) produces an ``Err``.
        """
        result = NotificationResult(
            notification_id=None,
            recipients_sent=8,
            recipients_failed=2,
            errors=["Invalid email", "Rate limited"],
        )
        assert result.recipients_failed == 2
        assert len(result.errors) == 2
