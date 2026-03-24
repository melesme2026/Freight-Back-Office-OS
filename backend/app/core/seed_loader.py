from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.domain.models.broker import Broker
from app.domain.models.customer_account import CustomerAccount
from app.domain.models.driver import Driver
from app.domain.models.organization import Organization
from app.domain.models.service_plan import ServicePlan
from app.domain.models.staff_user import StaffUser

SEED_DIR = Path(__file__).resolve().parents[3] / "data" / "seeds"


def _load_json(filename: str) -> list[dict[str, Any]]:
    path = SEED_DIR / filename
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def seed_organizations(db: Session) -> None:
    for item in _load_json("organizations.json"):
        if not db.query(Organization).filter(Organization.id == item["id"]).first():
            db.add(Organization(**item))
    db.commit()


def seed_customer_accounts(db: Session) -> None:
    for item in _load_json("customer_accounts.json"):
        if not db.query(CustomerAccount).filter(CustomerAccount.id == item["id"]).first():
            db.add(CustomerAccount(**item))
    db.commit()


def seed_drivers(db: Session) -> None:
    for item in _load_json("drivers.json"):
        if not db.query(Driver).filter(Driver.id == item["id"]).first():
            db.add(Driver(**item))
    db.commit()


def seed_brokers(db: Session) -> None:
    for item in _load_json("brokers.json"):
        if not db.query(Broker).filter(Broker.id == item["id"]).first():
            db.add(Broker(**item))
    db.commit()


def seed_service_plans(db: Session) -> None:
    for item in _load_json("service_plans.json"):
        if not db.query(ServicePlan).filter(ServicePlan.id == item["id"]).first():
            db.add(ServicePlan(**item))
    db.commit()


def seed_staff_users(db: Session) -> None:
    for item in _load_json("staff_users.json"):
        if not db.query(StaffUser).filter(StaffUser.id == item["id"]).first():
            db.add(StaffUser(**item))
    db.commit()


def run_all_seeds(db: Session) -> None:
    seed_organizations(db)
    seed_customer_accounts(db)
    seed_drivers(db)
    seed_brokers(db)
    seed_service_plans(db)
    seed_staff_users(db)