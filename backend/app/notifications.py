import os
import smtplib
import threading

from email.message import EmailMessage

from .models import (
    Customer,
    Device,
)


def _enabled(
    name: str,
) -> bool:
    return (
        os.getenv(
            name,
            "",
        )
        .strip()
        .lower()
        in {
            "1",
            "true",
            "yes",
            "on",
        }
    )


def _resolve_recipient(
    db,
    device_id: str,
) -> str | None:
    device = db.get(
        Device,
        device_id,
    )

    if (
        device is not None
        and device.customer_id
        is not None
    ):
        customer = db.get(
            Customer,
            device.customer_id,
        )

        if (
            customer is not None
            and customer.contact_email
        ):
            return (
                customer.contact_email
                .strip()
            )

    fallback = os.getenv(
        "ALERT_EMAIL_TO"
    )

    if fallback:
        return fallback.strip()

    return None


def _send_email(
    *,
    recipient: str,
    subject: str,
    body: str,
):
    host = os.getenv(
        "SMTP_HOST"
    )

    port = int(
        os.getenv(
            "SMTP_PORT",
            "587",
        )
    )

    username = os.getenv(
        "SMTP_USERNAME"
    )

    password = os.getenv(
        "SMTP_PASSWORD"
    )

    sender = (
        os.getenv(
            "SMTP_FROM"
        )
        or username
    )

    if not host or not sender:
        print(
            "Alert email skipped: "
            "SMTP configuration missing"
        )
        return

    message = EmailMessage()

    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject

    message.set_content(
        body
    )

    use_ssl = _enabled(
        "SMTP_SSL"
    )

    if use_ssl:
        with smtplib.SMTP_SSL(
            host,
            port,
            timeout=10,
        ) as smtp:

            if username:
                smtp.login(
                    username,
                    password or "",
                )

            smtp.send_message(
                message
            )

    else:
        with smtplib.SMTP(
            host,
            port,
            timeout=10,
        ) as smtp:

            smtp.ehlo()

            if _enabled(
                "SMTP_STARTTLS"
            ):
                smtp.starttls()
                smtp.ehlo()

            if username:
                smtp.login(
                    username,
                    password or "",
                )

            smtp.send_message(
                message
            )

    print(
        "Alert email sent | "
        f"recipient={recipient}"
    )


def notify_new_alert(
    db,
    *,
    device_id: str,
    alert_type: str,
    severity: str,
    message: str,
):
    # Frank's current requirement:
    # email notification for temperature
    # threshold alerts.
    if alert_type not in {
        "temperature_low",
        "temperature_high",
        "offline",
        "printer_warning",
        "printer_fault",
        "ink_low",
        "makeup_low",
    }:
        return

    if not _enabled(
        "ALERT_EMAIL_ENABLED"
    ):
        return

    recipient = _resolve_recipient(
        db,
        device_id,
    )

    if not recipient:
        print(
            "Alert email skipped: "
            "no recipient configured"
        )
        return

    subject = (
        "[Care-Inspector] "
        f"{alert_type.replace('_', ' ').title()} "
        f"- {device_id}"
    )

    body = (
        "Care-Inspector alert\n\n"
        f"Printer: {device_id}\n"
        f"Severity: {severity}\n"
        f"Alert: {alert_type}\n"
        f"Details: {message}\n"
    )

    # Never block the collector/WebSocket loop
    # while the SMTP server is contacted.
    thread = threading.Thread(
        target=_send_email,
        kwargs={
            "recipient": recipient,
            "subject": subject,
            "body": body,
        },
        daemon=True,
    )

    thread.start()
