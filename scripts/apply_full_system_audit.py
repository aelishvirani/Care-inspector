from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text()


def write(path, text):
    target = ROOT / path
    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    target.write_text(text)


# =========================================================
# 1. EXTEND AUDIT LOG MODEL
# =========================================================

path = "backend/app/models.py"
text = read(path)

start = text.index(
    "class AuditLog(Base):"
)

end = text.index(
    "class Alert(Base):",
    start,
)

audit_model = '''class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    actor_user_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    actor_email: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )

    actor_role: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )

    category: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )

    action: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
    )

    outcome: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )

    object_type: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    object_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    method: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    path: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True,
    )

    status_code: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    details: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    old_value: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    new_value: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )


'''

text = (
    text[:start]
    + audit_model
    + text[end:]
)

write(path, text)

print("✓ Extended AuditLog model")


# =========================================================
# 2. AUDIT SERVICE
# =========================================================

write(
    "backend/app/audit.py",
    '''from datetime import datetime, timezone

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
'''
)

print("✓ Created central audit service")


# =========================================================
# 3. HTTP AUDIT MIDDLEWARE
# =========================================================

write(
    "backend/app/audit_middleware.py",
    '''from time import perf_counter

from starlette.middleware.base import (
    BaseHTTPMiddleware,
)

from .audit import write_audit_event
from .auth import decode_access_token


class AuditMiddleware(
    BaseHTTPMiddleware
):
    async def dispatch(
        self,
        request,
        call_next,
    ):
        started = perf_counter()

        actor_email = "ANONYMOUS"
        actor_role = "ANONYMOUS"

        authorization = (
            request.headers.get(
                "authorization"
            )
        )

        if (
            authorization
            and authorization.lower()
            .startswith("bearer ")
        ):
            token = (
                authorization
                .split(" ", 1)[1]
            )

            try:
                payload = (
                    decode_access_token(
                        token
                    )
                )

                actor_email = (
                    payload.get("email")
                    or "UNKNOWN"
                )

                actor_role = (
                    payload.get("role")
                    or "UNKNOWN"
                )

            except Exception:
                actor_email = (
                    "INVALID_TOKEN"
                )

                actor_role = (
                    "ANONYMOUS"
                )

        try:
            response = await call_next(
                request
            )

        except Exception as exc:
            duration_ms = (
                perf_counter()
                - started
            ) * 1000

            write_audit_event(
                actor_email=actor_email,
                actor_role=actor_role,
                category="HTTP",
                action="API_REQUEST",
                outcome="FAILURE",
                request=request,
                status_code=500,
                details=(
                    f"{duration_ms:.1f} ms"
                ),
                error_message=str(exc),
            )

            raise

        duration_ms = (
            perf_counter()
            - started
        ) * 1000

        write_audit_event(
            actor_email=actor_email,
            actor_role=actor_role,
            category=(
                "SECURITY"
                if response.status_code
                in {401, 403}
                else "HTTP"
            ),
            action=(
                "ACCESS_DENIED"
                if response.status_code
                in {401, 403}
                else "API_REQUEST"
            ),
            outcome=(
                "SUCCESS"
                if response.status_code < 400
                else "FAILURE"
            ),
            request=request,
            status_code=(
                response.status_code
            ),
            details=(
                f"{duration_ms:.1f} ms"
            ),
        )

        return response
'''
)

print("✓ Created HTTP audit middleware")


# =========================================================
# 4. SQLITE ADDITIVE MIGRATION
# =========================================================

write(
    "scripts/upgrade_audit_log.py",
    '''import sqlite3

from backend.app.database import (
    DATA_DIR,
)


DATABASE = (
    DATA_DIR
    / "care_inspector.db"
)


COLUMNS = {
    "category":
        "VARCHAR",
    "outcome":
        "VARCHAR",
    "method":
        "VARCHAR",
    "path":
        "VARCHAR",
    "status_code":
        "INTEGER",
    "ip_address":
        "VARCHAR",
    "old_value":
        "VARCHAR",
    "new_value":
        "VARCHAR",
    "error_message":
        "VARCHAR",
}


with sqlite3.connect(
    DATABASE
) as conn:

    existing = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(audit_logs)"
        )
    }

    for name, sql_type in (
        COLUMNS.items()
    ):
        if name in existing:
            continue

        conn.execute(
            f"""
            ALTER TABLE audit_logs
            ADD COLUMN {name} {sql_type}
            """
        )

        print(
            f"Added audit_logs.{name}"
        )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        ix_audit_logs_category
        ON audit_logs(category)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        ix_audit_logs_outcome
        ON audit_logs(outcome)
        """
    )

    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS
        ix_audit_logs_path
        ON audit_logs(path)
        """
    )

    conn.commit()


print(
    "✓ Audit database upgrade complete"
)
'''
)

print("✓ Created additive DB migration")


# =========================================================
# 5. MAIN.PY
# =========================================================

path = "backend/app/main.py"
text = read(path)

if "    Request,\n" not in text:
    text = text.replace(
        "    HTTPException,\n",
        "    HTTPException,\n"
        "    Request,\n",
        1,
    )


audit_import = '''from .audit import (
    log_audit,
    write_audit_event,
)
from .audit_middleware import (
    AuditMiddleware,
)

'''

if (
    "from .audit_middleware import"
    not in text
):
    anchor = (
        "from .alerts import "
        "evaluate_measurement, "
        "set_alert\n"
    )

    text = text.replace(
        anchor,
        audit_import + anchor,
        1,
    )


# Register middleware.
if (
    "app.add_middleware("
    "AuditMiddleware"
    not in text
):
    marker = '''app = FastAPI(
    title="Care-Inspector API",
    version="0.3.0",
    lifespan=lifespan,
)
'''

    replacement = marker + '''

app.add_middleware(
    AuditMiddleware
)
'''

    if marker not in text:
        raise SystemExit(
            "FastAPI app marker not found"
        )

    text = text.replace(
        marker,
        replacement,
        1,
    )


# Replace login with fully audited login.
login_start = text.index(
    '@app.post("/api/auth/login")'
)

login_end = text.index(
    '@app.get("/api/auth/me")',
    login_start,
)

login_block = '''@app.post("/api/auth/login")
async def login(
    request: LoginRequest,
    http_request: Request,
):
    with SessionLocal() as db:

        user = db.scalar(
            select(User).where(
                User.email
                == request.email
            )
        )

        if (
            user is None
            or not user.active
            or not verify_password(
                request.password,
                user.password_hash,
            )
        ):
            log_audit(
                db,
                user=user,
                actor_email=(
                    request.email
                    .strip()
                    .lower()
                ),
                actor_role=(
                    user.role
                    if user
                    else "ANONYMOUS"
                ),
                category="AUTH",
                action="LOGIN_FAILED",
                outcome="FAILURE",
                object_type="user",
                object_id=(
                    user.id
                    if user
                    else None
                ),
                request=http_request,
                status_code=401,
                details=(
                    "Invalid credentials "
                    "or inactive account"
                ),
            )

            db.commit()

            raise HTTPException(
                status_code=401,
                detail=(
                    "Invalid email or password"
                ),
            )

        token = create_access_token(
            user
        )

        log_audit(
            db,
            user=user,
            category="AUTH",
            action="LOGIN_SUCCESS",
            outcome="SUCCESS",
            object_type="user",
            object_id=user.id,
            request=http_request,
            status_code=200,
        )

        db.commit()

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "customer_id": (
                    user.customer_id
                ),
            },
        }


'''

text = (
    text[:login_start]
    + login_block
    + text[login_end:]
)


# Add logout.
if (
    '@app.post("/api/auth/logout")'
    not in text
):
    marker = '''
# =========================================================
# Secure device access
# =========================================================
'''

    logout = '''
@app.post("/api/auth/logout")
async def logout(
    http_request: Request,
    user: User = Depends(
        get_current_user
    ),
):
    with SessionLocal() as db:
        log_audit(
            db,
            user=user,
            category="AUTH",
            action="LOGOUT",
            outcome="SUCCESS",
            object_type="user",
            object_id=user.id,
            request=http_request,
            status_code=200,
        )

        db.commit()

    return {
        "status": "ok",
    }


'''

    text = text.replace(
        marker,
        logout + marker,
        1,
    )


# Collector connected.
if (
    'action="COLLECTOR_CONNECTED"'
    not in text
):
    marker = '''    await websocket.accept()

    print(
'''

    replacement = '''    await websocket.accept()

    write_audit_event(
        actor_email="SYSTEM",
        actor_role="SYSTEM",
        category="COLLECTOR",
        action="COLLECTOR_CONNECTED",
        outcome="SUCCESS",
        object_type="device",
        object_id=device_id,
        ip_address=(
            websocket.client.host
            if websocket.client
            else None
        ),
    )

    print(
'''

    text = text.replace(
        marker,
        replacement,
        1,
    )


# Collector disconnected.
if (
    'action="COLLECTOR_DISCONNECTED"'
    not in text
):
    marker = '''    except WebSocketDisconnect:
        print(
'''

    replacement = '''    except WebSocketDisconnect:
        write_audit_event(
            actor_email="SYSTEM",
            actor_role="SYSTEM",
            category="COLLECTOR",
            action="COLLECTOR_DISCONNECTED",
            outcome="SUCCESS",
            object_type="device",
            object_id=device_id,
        )

        print(
'''

    text = text.replace(
        marker,
        replacement,
        1,
    )


# Collector error.
if (
    'action="COLLECTOR_ERROR"'
    not in text
):
    marker = '''    except Exception as exc:
        print(
'''

    replacement = '''    except Exception as exc:
        write_audit_event(
            actor_email="SYSTEM",
            actor_role="SYSTEM",
            category="COLLECTOR",
            action="COLLECTOR_ERROR",
            outcome="FAILURE",
            object_type="device",
            object_id=device_id,
            error_message=str(exc),
        )

        print(
'''

    text = text.replace(
        marker,
        replacement,
        1,
    )


# System start.
if (
    'action="SYSTEM_START"'
    not in text
):
    marker = '''    with SessionLocal() as db:
        get_configuration(db)

    monitor_task = asyncio.create_task(
'''

    replacement = '''    with SessionLocal() as db:
        get_configuration(db)

    write_audit_event(
        actor_email="SYSTEM",
        actor_role="SYSTEM",
        category="SYSTEM",
        action="SYSTEM_START",
        outcome="SUCCESS",
        object_type="backend",
        object_id="care-inspector-api",
    )

    monitor_task = asyncio.create_task(
'''

    text = text.replace(
        marker,
        replacement,
        1,
    )


# System stop.
if (
    'action="SYSTEM_STOP"'
    not in text
):
    marker = '''    try:
        await monitor_task
    except asyncio.CancelledError:
        pass
'''

    replacement = marker + '''

    write_audit_event(
        actor_email="SYSTEM",
        actor_role="SYSTEM",
        category="SYSTEM",
        action="SYSTEM_STOP",
        outcome="SUCCESS",
        object_type="backend",
        object_id="care-inspector-api",
    )
'''

    text = text.replace(
        marker,
        replacement,
        1,
    )


write(path, text)

print("✓ main.py authentication/system/collector audit added")


# =========================================================
# 6. ALERT LIFECYCLE
# =========================================================

path = "backend/app/alerts.py"
text = read(path)

if "from .audit import log_audit" not in text:
    text = text.replace(
        "from .models import Alert\n",
        "from .audit import log_audit\n"
        "from .models import Alert\n",
        1,
    )


old = '''        if existing is None:
            db.add(
                Alert(
                    device_id=device_id,
                    alert_type=alert_type,
                    severity=severity,
                    message=message,
                    active=True,
                    created_at=utc_now(),
                    resolved_at=None,
                )
            )
'''

new = '''        if existing is None:
            alert = Alert(
                device_id=device_id,
                alert_type=alert_type,
                severity=severity,
                message=message,
                active=True,
                created_at=utc_now(),
                resolved_at=None,
            )

            db.add(alert)
            db.flush()

            log_audit(
                db,
                actor_email="SYSTEM",
                actor_role="SYSTEM",
                category="ALERT",
                action="ALERT_CREATED",
                outcome="SUCCESS",
                object_type="alert",
                object_id=alert.id,
                details=(
                    f"{alert_type} for "
                    f"{device_id}: "
                    f"{message}"
                ),
            )
'''

if old in text:
    text = text.replace(
        old,
        new,
        1,
    )


old = '''        if existing is not None:
            existing.active = False
            existing.resolved_at = utc_now()
'''

new = '''        if existing is not None:
            existing.active = False
            existing.resolved_at = utc_now()

            log_audit(
                db,
                actor_email="SYSTEM",
                actor_role="SYSTEM",
                category="ALERT",
                action="ALERT_RESOLVED",
                outcome="SUCCESS",
                object_type="alert",
                object_id=existing.id,
                details=(
                    f"{alert_type} for "
                    f"{device_id}"
                ),
            )
'''

if old in text:
    text = text.replace(
        old,
        new,
        1,
    )


write(path, text)

print("✓ Alert create/resolve auditing added")


# =========================================================
# 7. FIX MANAGEMENT DEVICE AUDIT BUG
# =========================================================

path = "backend/app/management.py"
text = read(path)

register_start = text.index(
    "async def register_device("
)

register_end = text.index(
    "@router.patch(\n"
    '    "/devices/{device_id}"',
    register_start,
)

register_section = text[
    register_start:
    register_end
]

bad_start = register_section.find(
    "        new_customer_id = ("
)

if bad_start != -1:
    commit_pos = register_section.find(
        "        db.commit()",
        bad_start,
    )

    if commit_pos == -1:
        raise SystemExit(
            "register_device commit "
            "not found"
        )

    register_section = (
        register_section[:bad_start]
        + register_section[commit_pos:]
    )

    text = (
        text[:register_start]
        + register_section
        + text[register_end:]
    )

    print(
        "✓ Removed invalid old_customer_id "
        "block from register_device"
    )


# Add proper audit to update_device.
update_start = text.index(
    "async def update_device("
)

update_section = text[
    update_start:
]

if (
    'action="DEVICE_ASSIGNED"'
    not in update_section
):
    marker = '''        db.commit()
        db.refresh(device)

        return device_payload(
            device
        )
'''

    replacement = '''        new_customer_id = (
            device.customer_id
        )

        if (
            old_customer_id is None
            and new_customer_id
            is not None
        ):
            action = "DEVICE_ASSIGNED"

        elif (
            old_customer_id
            is not None
            and new_customer_id
            is None
        ):
            action = "DEVICE_UNASSIGNED"

        else:
            action = "DEVICE_UPDATED"

        log_audit(
            db,
            user=user,
            category="DEVICE",
            action=action,
            outcome="SUCCESS",
            object_type="device",
            object_id=device.device_id,
            details=(
                "Printer management change"
            ),
            old_value=(
                f"customer_id="
                f"{old_customer_id}"
            ),
            new_value=(
                f"customer_id="
                f"{new_customer_id}"
            ),
        )

        db.commit()
        db.refresh(device)

        return device_payload(
            device
        )
'''

    relative = update_section.find(
        marker
    )

    if relative == -1:
        raise SystemExit(
            "update_device commit "
            "block not found"
        )

    absolute = (
        update_start
        + relative
    )

    text = (
        text[:absolute]
        + replacement
        + text[
            absolute
            + len(marker):
        ]
    )

write(path, text)

print("✓ Device management auditing repaired")


# =========================================================
# 8. ADMIN AUDIT ENDPOINT
# =========================================================

path = "backend/app/admin.py"
text = read(path)

start = text.index(
    '@router.get("/audit-log")'
)

end = text.index(
    '@router.get("/system-health")',
    start,
)

audit_endpoint = '''@router.get("/audit-log")
async def audit_log(
    limit: int = 500,
    category: str | None = None,
    outcome: str | None = None,
    action: str | None = None,
    actor_email: str | None = None,
    user: User = Depends(
        get_current_user
    ),
):
    require_admin(user)

    limit = max(
        1,
        min(limit, 2000),
    )

    with SessionLocal() as db:
        query = select(
            AuditLog
        )

        if category:
            query = query.where(
                AuditLog.category
                == category
            )

        if outcome:
            query = query.where(
                AuditLog.outcome
                == outcome
            )

        if action:
            query = query.where(
                AuditLog.action
                == action
            )

        if actor_email:
            query = query.where(
                AuditLog.actor_email
                == actor_email
            )

        rows = db.scalars(
            query
            .order_by(
                AuditLog.created_at.desc()
            )
            .limit(limit)
        ).all()

        return [
            {
                "id":
                    row.id,

                "actor_user_id":
                    row.actor_user_id,

                "actor_email":
                    row.actor_email,

                "actor_role":
                    row.actor_role,

                "category":
                    row.category,

                "action":
                    row.action,

                "outcome":
                    row.outcome,

                "object_type":
                    row.object_type,

                "object_id":
                    row.object_id,

                "method":
                    row.method,

                "path":
                    row.path,

                "status_code":
                    row.status_code,

                "ip_address":
                    row.ip_address,

                "details":
                    row.details,

                "old_value":
                    row.old_value,

                "new_value":
                    row.new_value,

                "error_message":
                    row.error_message,

                "created_at":
                    row.created_at.isoformat(),
            }
            for row in rows
        ]


'''

text = (
    text[:start]
    + audit_endpoint
    + text[end:]
)

write(path, text)

print("✓ Admin audit API expanded")


# =========================================================
# 9. FRONTEND LOGOUT
# =========================================================

path = "frontend/src/auth/AuthContext.jsx"
text = read(path)

start = text.index(
    "  function logout() {"
)

end = text.index(
    "\n\n\n  return (",
    start,
)

logout = '''  async function logout() {
    try {
      await apiPost(
        '/auth/logout',
        {}
      )
    } catch (error) {
      console.error(
        'Logout audit request failed',
        error
      )
    } finally {
      localStorage.removeItem(
        'care_inspector_token'
      )

      localStorage.removeItem(
        'care_inspector_user'
      )

      setUser(null)
    }
  }'''

text = (
    text[:start]
    + logout
    + text[end:]
)

write(path, text)

print("✓ Frontend logout now calls backend")


# =========================================================
# 10. ADMIN API FILTER SUPPORT
# =========================================================

path = "frontend/src/api/adminApi.js"
text = read(path)

old = '''export function getAuditLog() {
  return apiGet(
    '/secure/admin/audit-log'
  )
}
'''

new = '''export function getAuditLog(
  filters = {}
) {
  const params =
    new URLSearchParams()

  Object.entries(
    filters
  ).forEach(
    ([key, value]) => {
      if (
        value !== ''
        && value !== null
        && value !== undefined
      ) {
        params.set(
          key,
          value
        )
      }
    }
  )

  const query =
    params.toString()

  return apiGet(
    `/secure/admin/audit-log${
      query
        ? `?${query}`
        : ''
    }`
  )
}
'''

if old not in text:
    raise SystemExit(
        "getAuditLog function "
        "not found"
    )

text = text.replace(
    old,
    new,
    1,
)

write(path, text)

print("✓ Audit API filters enabled")


# =========================================================
# 11. FULL AUDIT UI
# =========================================================

write(
    "frontend/src/pages/AuditLogPage.jsx",
    '''import {
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  getAuditLog,
} from '../api/adminApi'

import {
  formatDateTime,
} from '../utils/formatters'


export default function AuditLogPage() {
  const [
    rows,
    setRows,
  ] = useState([])

  const [
    error,
    setError,
  ] = useState(null)

  const [
    category,
    setCategory,
  ] = useState('')

  const [
    outcome,
    setOutcome,
  ] = useState('')

  const [
    search,
    setSearch,
  ] = useState('')


  async function load() {
    try {
      setError(null)

      setRows(
        await getAuditLog({
          limit: 1000,
          category,
          outcome,
        })
      )

    } catch (err) {
      setError(err.message)
    }
  }


  useEffect(() => {
    load()
  }, [
    category,
    outcome,
  ])


  const filteredRows =
    useMemo(
      () => {
        const term =
          search
            .trim()
            .toLowerCase()

        if (!term) {
          return rows
        }

        return rows.filter(
          row =>
            [
              row.actor_email,
              row.actor_role,
              row.category,
              row.action,
              row.outcome,
              row.object_type,
              row.object_id,
              row.path,
              row.ip_address,
              row.details,
              row.error_message,
            ]
              .filter(Boolean)
              .some(
                value =>
                  String(value)
                    .toLowerCase()
                    .includes(term)
              )
        )
      },
      [
        rows,
        search,
      ]
    )


  return (
    <div className="page">

      <div className="page-header">

        <div>
          <h1>
            System Activity Log
          </h1>

          <p>
            Authentication, security,
            users, printers, collectors,
            alerts and API activity
          </p>
        </div>

        <button
          className="secondary-button"
          onClick={load}
        >
          Refresh
        </button>

      </div>


      <div className="filter-toolbar">

        <div className="filter-group">
          <label>Category</label>

          <select
            value={category}
            onChange={
              event =>
                setCategory(
                  event.target.value
                )
            }
          >
            <option value="">
              All
            </option>

            <option value="AUTH">
              Authentication
            </option>

            <option value="SECURITY">
              Security
            </option>

            <option value="HTTP">
              API
            </option>

            <option value="USER">
              Users
            </option>

            <option value="CUSTOMER">
              Customers
            </option>

            <option value="DEVICE">
              Devices
            </option>

            <option value="COLLECTOR">
              Collectors
            </option>

            <option value="ALERT">
              Alerts
            </option>

            <option value="SYSTEM">
              System
            </option>

            <option value="GENERAL">
              General
            </option>
          </select>
        </div>


        <div className="filter-group">
          <label>Result</label>

          <select
            value={outcome}
            onChange={
              event =>
                setOutcome(
                  event.target.value
                )
            }
          >
            <option value="">
              All
            </option>

            <option value="SUCCESS">
              Success
            </option>

            <option value="FAILURE">
              Failure
            </option>
          </select>
        </div>


        <div className="filter-group">
          <label>Search</label>

          <input
            value={search}
            placeholder={
              'User, action, printer, IP...'
            }
            onChange={
              event =>
                setSearch(
                  event.target.value
                )
            }
          />
        </div>

      </div>


      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}


      <section className="panel">

        <p>
          {filteredRows.length}
          {' '}
          events
        </p>

        <div className="alert-table-wrapper">

          <table className="alert-table">

            <thead>
              <tr>
                <th>Time</th>
                <th>Actor</th>
                <th>Role</th>
                <th>Category</th>
                <th>Action</th>
                <th>Result</th>
                <th>HTTP</th>
                <th>Object</th>
                <th>IP</th>
                <th>Details</th>
              </tr>
            </thead>

            <tbody>

              {
                filteredRows.map(
                  row => (
                    <tr key={row.id}>

                      <td>
                        {
                          formatDateTime(
                            row.created_at
                          )
                        }
                      </td>

                      <td>
                        {row.actor_email}
                      </td>

                      <td>
                        {row.actor_role}
                      </td>

                      <td>
                        {
                          row.category
                          || '—'
                        }
                      </td>

                      <td>
                        {row.action}
                      </td>

                      <td>
                        {
                          row.outcome
                          || '—'
                        }
                      </td>

                      <td>
                        {
                          row.method
                            ? `${row.method} ${
                                row.status_code
                                ?? ''
                              }`
                            : '—'
                        }

                        {
                          row.path
                            ? (
                              <div>
                                {row.path}
                              </div>
                            )
                            : null
                        }
                      </td>

                      <td>
                        {
                          row.object_type
                          || '—'
                        }

                        {
                          row.object_id
                            ? ` #${row.object_id}`
                            : ''
                        }
                      </td>

                      <td>
                        {
                          row.ip_address
                          || '—'
                        }
                      </td>

                      <td>
                        {
                          row.error_message
                          || row.details
                          || '—'
                        }

                        {
                          row.old_value
                          && (
                            <div>
                              Old:
                              {' '}
                              {row.old_value}
                            </div>
                          )
                        }

                        {
                          row.new_value
                          && (
                            <div>
                              New:
                              {' '}
                              {row.new_value}
                            </div>
                          )
                        }
                      </td>

                    </tr>
                  )
                )
              }

            </tbody>

          </table>

        </div>

      </section>

    </div>
  )
}
'''
)

print("✓ Full system activity UI created")


print()
print(
    "=============================================="
)
print(
    "FULL SYSTEM AUDIT PATCH APPLIED"
)
print(
    "=============================================="
)
