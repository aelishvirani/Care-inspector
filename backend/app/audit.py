from datetime import datetime, timezone

from .models import AuditLog


def log_audit(
    db,
    *,
    user,
    action: str,
    object_type: str | None = None,
    object_id: str | int | None = None,
    details: str | None = None,
):
    row = AuditLog(
        actor_user_id=getattr(
            user,
            "id",
            None,
        ),
        actor_email=getattr(
            user,
            "email",
            "system",
        ),
        actor_role=getattr(
            user,
            "role",
            "SYSTEM",
        ),
        action=action,
        object_type=object_type,
        object_id=(
            str(object_id)
            if object_id is not None
            else None
        ),
        details=details,
        created_at=datetime.now(
            timezone.utc
        ),
    )

    db.add(row)

    return row
