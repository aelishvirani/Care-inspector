from datetime import datetime, timezone

from .database import SessionLocal
from .models import AuditLog


def get_client_ip(
    request,
):
    if request is None:
        return None

    forwarded = request.headers.get(
        "x-forwarded-for"
    )

    if forwarded:
        return (
            forwarded
            .split(",")[0]
            .strip()
        )

    if request.client:
        return request.client.host

    return None


def log_audit(
    db,
    *,
    user=None,
    actor_email: str | None = None,
    actor_role: str | None = None,
    action: str,
    category: str = "GENERAL",
    outcome: str = "SUCCESS",
    object_type: str | None = None,
    object_id: str | int | None = None,
    details: str | None = None,
    request=None,
    method: str | None = None,
    path: str | None = None,
    status_code: int | None = None,
    ip_address: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    error_message: str | None = None,
):
    resolved_email = (
        actor_email
        or getattr(
            user,
            "email",
            None,
        )
        or "SYSTEM"
    )

    resolved_role = (
        actor_role
        or getattr(
            user,
            "role",
            None,
        )
        or "SYSTEM"
    )

    if request is not None:
        method = (
            method
            or request.method
        )

        path = (
            path
            or request.url.path
        )

        ip_address = (
            ip_address
            or get_client_ip(
                request
            )
        )

    row = AuditLog(
        actor_user_id=getattr(
            user,
            "id",
            None,
        ),
        actor_email=resolved_email,
        actor_role=resolved_role,
        category=category,
        action=action,
        outcome=outcome,
        object_type=object_type,
        object_id=(
            str(object_id)
            if object_id is not None
            else None
        ),
        method=method,
        path=path,
        status_code=status_code,
        ip_address=ip_address,
        details=details,
        old_value=old_value,
        new_value=new_value,
        error_message=error_message,
        created_at=datetime.now(
            timezone.utc
        ),
    )

    db.add(row)

    return row


def write_audit_event(
    **kwargs,
):
    try:
        with SessionLocal() as db:
            row = log_audit(
                db,
                **kwargs,
            )

            db.commit()

            return row

    except Exception as exc:
        print(
            "Audit logging error:",
            exc,
        )

        return None
