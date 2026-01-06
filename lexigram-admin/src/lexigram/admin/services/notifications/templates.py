"""Email templates and rendering for admin notifications."""

from __future__ import annotations

import re
from typing import Any

from lexigram.admin.services.notifications.models import NotificationType
from lexigram.di.decorators import inject

# Base template with admin branding
ADMIN_EMAIL_BASE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #1a56db; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
        .content {{ background: #fff; padding: 30px; border: 1px solid #e5e7eb; }}
        .footer {{ background: #f9fafb; padding: 20px; text-align: center; font-size: 12px; color: #6b7280; border-radius: 0 0 8px 8px; }}
        .btn {{ display: inline-block; padding: 12px 24px; background: #1a56db; color: white; text-decoration: none; border-radius: 6px; margin: 16px 0; }}
        .alert {{ padding: 16px; border-radius: 6px; margin: 16px 0; }}
        .alert-success {{ background: #d1fae5; border: 1px solid #34d399; }}
        .alert-warning {{ background: #fef3c7; border: 1px solid #f59e0b; }}
        .alert-error {{ background: #fee2e2; border: 1px solid #ef4444; }}
        .progress {{ background: #e5e7eb; border-radius: 9999px; height: 8px; overflow: hidden; }}
        .progress-bar {{ background: #1a56db; height: 100%; transition: width 0.3s; }}
        table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
        th {{ background: #f9fafb; font-weight: 600; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{app_name} Admin</h1>
        </div>
        <div class="content">
            {content}
        </div>
        <div class="footer">
            <p>This is an automated notification from {app_name} Admin Panel.</p>
            <p>You received this email because you are an administrator.</p>
        </div>
    </div>
</body>
</html>
"""

# Specific templates
EMAIL_TEMPLATES: dict[NotificationType, tuple[str, str]] = {
    # (subject_template, body_template)
    NotificationType.USER_CREATED: (
        "New user created: {user_name}",
        """
        <h2>New User Created</h2>
        <p>A new user account has been created:</p>
        <table>
            <tr><th>Name</th><td>{user_name}</td></tr>
            <tr><th>Email</th><td>{user_email}</td></tr>
            <tr><th>Role</th><td>{user_role}</td></tr>
            <tr><th>Created By</th><td>{created_by}</td></tr>
            <tr><th>Created At</th><td>{created_at}</td></tr>
        </table>
        <a href="{user_url}" class="btn">View User</a>
        """,
    ),
    NotificationType.USER_INVITED: (
        "You've been invited to {app_name} Admin",
        """
        <h2>Welcome to {app_name} Admin</h2>
        <p>Hello {user_name},</p>
        <p>You've been invited to join {app_name} as an administrator.</p>
        <p>Click the button below to set up your account:</p>
        <a href="{invite_url}" class="btn">Accept Invitation</a>
        <p><small>This invitation expires in {expires_in}.</small></p>
        """,
    ),
    NotificationType.PASSWORD_RESET: (
        "Password Reset Request",
        """
        <h2>Password Reset</h2>
        <p>Hello {user_name},</p>
        <p>We received a request to reset your password. Click the button below to create a new password:</p>
        <a href="{reset_url}" class="btn">Reset Password</a>
        <p><small>This link expires in {expires_in}. If you didn't request this, you can safely ignore this email.</small></p>
        """,
    ),
    NotificationType.BULK_STARTED: (
        "Bulk operation started: {operation_name}",
        """
        <h2>Bulk Operation Started</h2>
        <p>A bulk operation has been started:</p>
        <table>
            <tr><th>Operation</th><td>{operation_name}</td></tr>
            <tr><th>Resource</th><td>{resource}</td></tr>
            <tr><th>Total Items</th><td>{total_items}</td></tr>
            <tr><th>Started By</th><td>{started_by}</td></tr>
            <tr><th>Started At</th><td>{started_at}</td></tr>
        </table>
        <p>You will receive another notification when the operation completes.</p>
        """,
    ),
    NotificationType.BULK_PROGRESS: (
        "Bulk operation progress: {progress}%",
        """
        <h2>Bulk Operation Progress</h2>
        <p>Operation: {operation_name}</p>
        <div class="progress">
            <div class="progress-bar" style="width: {progress}%"></div>
        </div>
        <p>{processed} of {total_items} items processed ({progress}%)</p>
        <table>
            <tr><th>Successful</th><td>{successful}</td></tr>
            <tr><th>Failed</th><td>{failed}</td></tr>
            <tr><th>Remaining</th><td>{remaining}</td></tr>
        </table>
        """,
    ),
    NotificationType.BULK_COMPLETED: (
        "Bulk operation completed: {operation_name}",
        """
        <h2>Bulk Operation Completed</h2>
        <div class="alert alert-success">
            <strong>Success!</strong> The bulk operation has completed.
        </div>
        <table>
            <tr><th>Operation</th><td>{operation_name}</td></tr>
            <tr><th>Resource</th><td>{resource}</td></tr>
            <tr><th>Total Items</th><td>{total_items}</td></tr>
            <tr><th>Successful</th><td>{successful}</td></tr>
            <tr><th>Failed</th><td>{failed}</td></tr>
            <tr><th>Duration</th><td>{duration}</td></tr>
        </table>
        <a href="{results_url}" class="btn">View Results</a>
        """,
    ),
    NotificationType.BULK_FAILED: (
        "Bulk operation failed: {operation_name}",
        """
        <h2>Bulk Operation Failed</h2>
        <div class="alert alert-error">
            <strong>Error!</strong> The bulk operation failed.
        </div>
        <table>
            <tr><th>Operation</th><td>{operation_name}</td></tr>
            <tr><th>Error</th><td>{error_message}</td></tr>
            <tr><th>Processed Before Failure</th><td>{processed}</td></tr>
        </table>
        <p>Please check the logs for more details.</p>
        """,
    ),
    NotificationType.EXPORT_READY: (
        "Your export is ready: {export_name}",
        """
        <h2>Export Ready</h2>
        <div class="alert alert-success">
            <strong>Success!</strong> Your data export is ready for download.
        </div>
        <table>
            <tr><th>Export</th><td>{export_name}</td></tr>
            <tr><th>Format</th><td>{format}</td></tr>
            <tr><th>Records</th><td>{record_count}</td></tr>
            <tr><th>File Size</th><td>{file_size}</td></tr>
        </table>
        <a href="{download_url}" class="btn">Download Export</a>
        <p><small>This link expires in {expires_in}.</small></p>
        """,
    ),
    NotificationType.SYSTEM_ALERT: (
        "[{severity}] System Alert: {alert_title}",
        """
        <h2>System Alert</h2>
        <div class="alert alert-{severity_class}">
            <strong>{severity}:</strong> {alert_title}
        </div>
        <p>{alert_message}</p>
        <table>
            <tr><th>Time</th><td>{occurred_at}</td></tr>
            <tr><th>Component</th><td>{component}</td></tr>
        </table>
        """,
    ),
}


@inject
class TemplateRenderer:
    """Handles rendering of email templates."""

    def __init__(self, app_name: str = "Admin"):
        """Initialize with app name for templates."""
        self.app_name = app_name

    def render_template(
        self,
        notification_type: NotificationType,
        data: dict[str, Any],
    ) -> tuple[str, str, str]:
        """Render email template.

        Args:
            notification_type: Type of notification
            data: Template data

        Returns:
            Tuple of (subject, text_body, html_body)
        """
        templates = EMAIL_TEMPLATES.get(notification_type)
        if not templates:
            return (
                data.get("subject", "Admin Notification"),
                data.get("body", ""),
                "",
            )

        subject_tpl, body_tpl = templates

        # Add app name to data
        full_data = {
            "app_name": self.app_name,
            **data,
        }

        # Render
        try:
            subject = subject_tpl.format(**full_data)
            body_content = body_tpl.format(**full_data)
            html_body = ADMIN_EMAIL_BASE.format(
                app_name=self.app_name,
                content=body_content,
            )

            # Simple text conversion
            text_body = re.sub(r"<[^>]+>", "", body_content)
            text_body = re.sub(r"\s+", " ", text_body).strip()

            return subject, text_body, html_body
        except KeyError as e:
            return (
                f"Admin Notification: {notification_type.value}",
                f"Missing template data: {e}",
                "",
            )


__all__ = [
    "ADMIN_EMAIL_BASE",
    "EMAIL_TEMPLATES",
    "TemplateRenderer",
]
