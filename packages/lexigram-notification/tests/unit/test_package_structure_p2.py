from __future__ import annotations

from pathlib import Path

from lexigram.notification.di.mailer_provider import MailerProvider
from lexigram.notification.mailer.module import MailerModule
from lexigram.notification.mailer.sendgrid_mailer import SendGridMailer
from lexigram.notification.mailer.smtp_mailer import SMTPMailer

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
NOTIF_ROOT = PACKAGE_ROOT / "src/lexigram/notification"


def test_mailer_submodule_files_exist() -> None:
    assert (NOTIF_ROOT / "mailer/module.py").is_file()
    assert (NOTIF_ROOT / "di/mailer_provider.py").is_file()
    assert (NOTIF_ROOT / "mailer/sendgrid_mailer.py").is_file()
    assert (NOTIF_ROOT / "mailer/smtp_mailer.py").is_file()
    assert not (NOTIF_ROOT / "mail_module.py").exists(), "flat mail_module.py should be removed"
    assert not (NOTIF_ROOT / "sendgrid_mailer.py").exists(), "flat sendgrid_mailer.py should be removed"
    assert not (NOTIF_ROOT / "smtp_mailer.py").exists(), "flat smtp_mailer.py should be removed"


def test_inbox_submodule_files_exist() -> None:
    assert (NOTIF_ROOT / "inbox/database.py").is_file()
    assert (NOTIF_ROOT / "inbox/memory.py").is_file()
    assert (NOTIF_ROOT / "inbox/service.py").is_file()
    assert (NOTIF_ROOT / "di/inbox_provider.py").is_file()
    assert not (NOTIF_ROOT / "inbox_database.py").exists(), "flat inbox_database.py should be removed"
    assert not (NOTIF_ROOT / "inbox_memory.py").exists(), "flat inbox_memory.py should be removed"
    assert not (NOTIF_ROOT / "inbox_service.py").exists(), "flat inbox_service.py should be removed"


def test_mailer_types_live_in_mailer_submodule() -> None:
    assert MailerModule.__module__ == "lexigram.notification.mailer.module"
    assert MailerProvider.__module__ == "lexigram.notification.di.mailer_provider"
    assert SMTPMailer.__module__ == "lexigram.notification.mailer.smtp_mailer"
    assert SendGridMailer.__module__ == "lexigram.notification.mailer.sendgrid_mailer"

