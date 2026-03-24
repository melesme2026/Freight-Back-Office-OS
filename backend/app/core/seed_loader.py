import json
from pathlib import Path
from sqlalchemy.orm import Session

from app.domain.models.organization import Organization
from app.domain.models.customer_account import CustomerAccount
from app.domain.models.driver import Driver
from app.domain.models.broker import Broker
from app.domain.models.service_plan import ServicePlan
from app.domain.models.staff_user import StaffUser

BASE_PATH = Path(__file__).resolve().parents[3] / "data" / "seeds"


def load_json(filename: str):
    with open(BASE_PATH / filename, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_organizations(db: Session):
    data = load_json("organizations.json")
    for item in data:
        if not db.query(Organization).filter_by(id=item["id"]).first():
            db.add(Organization(**item))
    db.commit()


def seed_customer_accounts(db: Session):
    data = load_json("customer_accounts.json")
    for item in data:
        if not db.query(CustomerAccount).filter_by(id=item["id"]).first():
            db.add(CustomerAccount(**item))
    db.commit()


def seed_drivers(db: Session):
    data = load_json("drivers.json")
    for item in data:
        if not db.query(Driver).filter_by(id=item["id"]).first():
            db.add(Driver(**item))
    db.commit()


def seed_brokers(db: Session):
    data = load_json("brokers.json")
    for item in data:
        if not db.query(Broker).filter_by(id=item["id"]).first():
            db.add(Broker(**item))
    db.commit()


def seed_service_plans(db: Session):
    data = load_json("service_plans.json")
    for item in data:
        if not db.query(ServicePlan).filter_by(id=item["id"]).first():
            db.add(ServicePlan(**item))
    db.commit()


def seed_staff_users(db: Session):
    data = load_json("staff_users.json")
    for item in data:
        if not db.query(StaffUser).filter_by(id=item["id"]).first():
            db.add(StaffUser(**item))
    db.commit()


def run_all_seeds(db: Session):
    seed_organizations(db)
    seed_customer_accounts(db)
    seed_drivers(db)
    seed_brokers(db)
    seed_service_plans(db)
    seed_staff_users(db)