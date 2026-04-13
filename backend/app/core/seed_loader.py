from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.core.security import hash_password
from app.domain.models.broker import Broker
from app.domain.models.customer_account import CustomerAccount
from app.domain.models.driver import Driver
from app.domain.models.organization import Organization
from app.domain.models.service_plan import ServicePlan
from app.domain.models.staff_user import StaffUser


SEED_DIR = Path(__file__).resolve().parents[3] / "data" / "seeds"

SeedModel = type[Any]
SeedNormalizer = Callable[[dict[str, Any]], dict[str, Any]]

_RUNTIME_STAFF_USER_PASSWORDS: dict[str, str] = {
    "admin@adwafreight.com": "Admin123!",
    "reviewer@adwafreight.com": "Reviewer123!",
    "john.doe@example.com": "Driver123!",
}

SEED_SPECS: tuple[tuple[str, SeedModel, SeedNormalizer], ...] = (
    ("organizations.json", Organization, lambda item: _normalize_seed_item(item)),
    ("customer_accounts.json", CustomerAccount, lambda item: _normalize_seed_item(item)),
    ("drivers.json", Driver, lambda item: _normalize_seed_item(item)),
    ("brokers.json", Broker, lambda item: _normalize_seed_item(item)),
    ("service_plans.json", ServicePlan, lambda item: _normalize_seed_item(item)),
    ("staff_users.json", StaffUser, lambda item: _normalize_staff_user_seed_item(item)),
)


def _load_json(filename: str) -> list[dict[str, Any]]:
    path = SEED_DIR / filename

    if not path.exists():
        raise ValidationError(
            "Seed file not found",
            details={"filename": filename, "path": str(path)},
        )

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise ValidationError(
            "Invalid seed JSON",
            details={"filename": filename, "path": str(path)},
        ) from exc

    if not isinstance(data, list):
        raise ValidationError(
            "Seed file must contain a JSON array",
            details={"filename": filename, "path": str(path)},
        )

    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValidationError(
                "Each seed item must be a JSON object",
                details={
                    "filename": filename,
                    "path": str(path),
                    "index": index,
                    "item_type": type(item).__name__,
                },
            )

    return data


def _normalize_seed_item(item: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(item)

    for key, value in normalized.items():
        if value is None:
            continue

        if key == "id" or key.endswith("_id"):
            if isinstance(value, str):
                try:
                    normalized[key] = uuid.UUID(value)
                except ValueError as exc:
                    raise ValidationError(
                        "Invalid UUID value in seed data",
                        details={"field": key, "value": value},
                    ) from exc

    return normalized


def _normalize_staff_user_seed_item(item: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_seed_item(item)

    email = normalized.get("email")
    password_hash = normalized.get("password_hash")

    if not isinstance(email, str) or not email.strip():
        raise ValidationError(
            "Staff user seed item must include a valid email",
            details={"item": item},
        )

    if password_hash == "__SET_VIA_SEED_RUNTIME__":
        plain_password = _RUNTIME_STAFF_USER_PASSWORDS.get(email.lower())
        if not plain_password:
            raise ValidationError(
                "No runtime seed password configured for staff user",
                details={"email": email},
            )
        normalized["password_hash"] = hash_password(plain_password)

    return normalized


def _existing_ids(
    db: Session,
    model: SeedModel,
    ids: Iterable[uuid.UUID],
) -> set[uuid.UUID]:
    ids_list = list(ids)
    if not ids_list:
        return set()

    stmt = select(model.id).where(model.id.in_(ids_list))
    return set(db.execute(stmt).scalars().all())


def _seed_model(
    db: Session,
    *,
    filename: str,
    model: SeedModel,
    normalizer: SeedNormalizer = _normalize_seed_item,
) -> int:
    raw_items = _load_json(filename)
    normalized_items = [normalizer(item) for item in raw_items]

    missing_id_indexes = [
        index for index, item in enumerate(normalized_items) if "id" not in item
    ]
    if missing_id_indexes:
        raise ValidationError(
            "Seed items must include an id field",
            details={"filename": filename, "indexes": missing_id_indexes},
        )

    ids = [item["id"] for item in normalized_items]
    existing = _existing_ids(db, model, ids)

    created_count = 0
    for item in normalized_items:
        if item["id"] in existing:
            continue
        db.add(model(**item))
        created_count += 1

    return created_count


def seed_organizations(db: Session) -> int:
    return _seed_model(
        db,
        filename="organizations.json",
        model=Organization,
    )


def seed_customer_accounts(db: Session) -> int:
    return _seed_model(
        db,
        filename="customer_accounts.json",
        model=CustomerAccount,
    )


def seed_drivers(db: Session) -> int:
    return _seed_model(
        db,
        filename="drivers.json",
        model=Driver,
    )


def seed_brokers(db: Session) -> int:
    return _seed_model(
        db,
        filename="brokers.json",
        model=Broker,
    )


def seed_service_plans(db: Session) -> int:
    return _seed_model(
        db,
        filename="service_plans.json",
        model=ServicePlan,
    )


def seed_staff_users(db: Session) -> int:
    return _seed_model(
        db,
        filename="staff_users.json",
        model=StaffUser,
        normalizer=_normalize_staff_user_seed_item,
    )


def run_all_seeds(db: Session) -> dict[str, int]:
    results: dict[str, int] = {}

    try:
        for filename, model, normalizer in SEED_SPECS:
            created_count = _seed_model(
                db,
                filename=filename,
                model=model,
                normalizer=normalizer,
            )
            results[model.__name__] = created_count

        db.commit()
        return results
    except Exception:
        db.rollback()
        raise