from backend.app.auth import (
    hash_password,
)
from backend.app.database import (
    SessionLocal,
)
from backend.app.models import (
    Customer,
    User,
)


TECH_EMAIL = (
    "technik@care-inspector.local"
)

TECH_PASSWORD = (
    "TechnikDemo2026!"
)

CUSTOMER_EMAIL = (
    "customer@demo.local"
)

CUSTOMER_PASSWORD = (
    "CustomerDemo2026!"
)


def ensure_user(
    db,
    *,
    email,
    password,
    role,
    customer_id,
):
    existing = (
        db.query(User)
        .filter(
            User.email == email
        )
        .first()
    )

    if existing:
        print(
            f"Exists: {email}"
        )
        return

    user = User(
        email=email,
        password_hash=(
            hash_password(
                password
            )
        ),
        role=role,
        customer_id=customer_id,
        active=True,
    )

    db.add(user)

    print(
        f"Created: {email}"
    )


def main():
    with SessionLocal() as db:

        customer = db.get(
            Customer,
            1,
        )

        if customer is None:
            raise RuntimeError(
                "Customer ID 1 "
                "does not exist."
            )

        ensure_user(
            db,
            email=TECH_EMAIL,
            password=TECH_PASSWORD,
            role="TECHNICIAN",
            customer_id=None,
        )

        ensure_user(
            db,
            email=CUSTOMER_EMAIL,
            password=CUSTOMER_PASSWORD,
            role="CUSTOMER",
            customer_id=1,
        )

        db.commit()

    print()
    print(
        "Demo users ready."
    )


if __name__ == "__main__":
    main()
