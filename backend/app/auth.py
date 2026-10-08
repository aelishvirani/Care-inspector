from __future__ import annotations

import os
from datetime import (
    datetime,
    timedelta,
    timezone,
)

import bcrypt
import jwt

from fastapi import (
    Header,
    HTTPException,
    status,
)

from .database import SessionLocal
from .models import User


JWT_ALGORITHM = "HS256"

JWT_SECRET = os.getenv(
    "CARE_INSPECTOR_JWT_SECRET",
    "care-inspector-development-secret",
)

ACCESS_TOKEN_HOURS = 12


def hash_password(
    password: str,
) -> str:
    hashed = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    )

    return hashed.decode("utf-8")


def verify_password(
    password: str,
    password_hash: str,
) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )

    except Exception:
        return False


def create_access_token(
    user: User,
) -> str:
    now = datetime.now(
        timezone.utc
    )

    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "customer_id": (
            user.customer_id
        ),
        "iat": now,
        "exp": (
            now
            + timedelta(
                hours=ACCESS_TOKEN_HOURS
            )
        ),
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(
    token: str,
) -> dict:
    try:
        return jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[
                JWT_ALGORITHM
            ],
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Token expired",
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        )


def get_current_user(
    authorization: str | None = Header(
        default=None
    ),
) -> User:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Authorization header "
                "required"
            ),
        )

    parts = authorization.split(
        " ",
        1,
    )

    if (
        len(parts) != 2
        or parts[0].lower()
        != "bearer"
    ):
        raise HTTPException(
            status_code=401,
            detail=(
                "Expected Bearer token"
            ),
        )

    payload = decode_access_token(
        parts[1]
    )

    try:
        user_id = int(
            payload["sub"]
        )

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid token user",
        )

    with SessionLocal() as db:
        user = db.get(
            User,
            user_id,
        )

        if (
            user is None
            or not user.active
        ):
            raise HTTPException(
                status_code=401,
                detail=(
                    "User unavailable"
                ),
            )

        # Detach simple fields before
        # session closes.
        db.expunge(user)

        return user


def require_technician(
    user: User,
) -> None:
    if user.role not in {
        "TECHNICIAN",
        "ADMIN",
    }:
        raise HTTPException(
            status_code=403,
            detail=(
                "Technician or admin access "
                "required"
            ),
        )
