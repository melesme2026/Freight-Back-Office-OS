from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import Base, get_engine, get_session_factory
from app.core.seed_loader import run_all_seeds
import app.domain.models  # noqa: F401

REQUIRED_ORG_COLUMNS = {
    "billing_provider",
    "billing_status",
    "plan_code",
    "stripe_customer_id",
    "stripe_subscription_id",
    "billing_notes",
}


def reset_schema() -> None:
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def verify_organization_schema() -> None:
    inspector = inspect(get_engine())
    columns = {column["name"] for column in inspector.get_columns("organizations")}
    missing = REQUIRED_ORG_COLUMNS - columns

    if missing:
        missing_list = ", ".join(sorted(missing))
        raise RuntimeError(f"organizations table missing required columns: {missing_list}")


def seed_data() -> None:
    session_factory = get_session_factory()
    db = session_factory()
    try:
        results = run_all_seeds(db)
        print(f"✅ Seeded models: {results}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    reset_schema()
    verify_organization_schema()
    seed_data()
    print("✅ Database reset + schema verification + seed complete")


if __name__ == "__main__":
    main()
