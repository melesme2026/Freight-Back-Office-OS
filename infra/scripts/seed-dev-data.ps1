$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $root

if (Test-Path ".venv\Scripts\Activate.ps1") {
    . .\.venv\Scripts\Activate.ps1
}

$env:PYTHONPATH = "$root\backend"

$pythonCode = @'
from decimal import Decimal

from app.core.database import SessionLocal
from app.domain.enums.billing_cycle import BillingCycle
from app.domain.enums.customer_account_status import CustomerAccountStatus
from app.domain.enums.role import Role
from app.domain.models.customer_account import CustomerAccount
from app.domain.models.driver import Driver
from app.domain.models.organization import Organization
from app.domain.models.service_plan import ServicePlan
from app.domain.models.staff_user import StaffUser
from app.core.security import hash_password

db = SessionLocal()

try:
    org = db.query(Organization).filter(Organization.slug == "adwa-freight").first()
    if org is None:
        org = Organization(
            name="Adwa Freight Demo",
            slug="adwa-freight",
            is_active=True,
        )
        db.add(org)
        db.flush()

    customer = db.query(CustomerAccount).filter(
        CustomerAccount.organization_id == org.id,
        CustomerAccount.account_code == "DEMO-001",
    ).first()
    if customer is None:
        customer = CustomerAccount(
            organization_id=org.id,
            account_name="Demo Customer Account",
            account_code="DEMO-001",
            status=CustomerAccountStatus.ACTIVE,
            primary_contact_name="Demo Dispatcher",
            primary_contact_email="dispatch@demo-freight.com",
            primary_contact_phone="+15865550100",
            billing_email="billing@demo-freight.com",
            notes="Seeded development customer account",
        )
        db.add(customer)
        db.flush()

    driver = db.query(Driver).filter(
        Driver.organization_id == org.id,
        Driver.phone == "+15865550101",
    ).first()
    if driver is None:
        driver = Driver(
            organization_id=org.id,
            customer_account_id=customer.id,
            full_name="Demo Driver",
            phone="+15865550101",
            email="driver@demo-freight.com",
            is_active=True,
        )
        db.add(driver)

    plan = db.query(ServicePlan).filter(
        ServicePlan.organization_id == org.id,
        ServicePlan.code == "starter",
    ).first()
    if plan is None:
        plan = ServicePlan(
            organization_id=org.id,
            name="Starter",
            code="starter",
            description="Starter development plan",
            billing_cycle=BillingCycle.MONTHLY,
            base_price=Decimal("99.00"),
            currency_code="USD",
            per_load_price=Decimal("5.00"),
            per_driver_price=Decimal("2.00"),
            is_active=True,
        )
        db.add(plan)

    staff = db.query(StaffUser).filter(
        StaffUser.organization_id == org.id,
        StaffUser.email == "admin@demo-freight.com",
    ).first()
    if staff is None:
        staff = StaffUser(
            organization_id=org.id,
            email="admin@demo-freight.com",
            full_name="Demo Admin",
            password_hash=hash_password("ChangeMe123!"),
            role=Role.ADMIN,
            is_active=True,
            last_login_at=None,
        )
        db.add(staff)

    db.commit()
    print("Seed data inserted successfully.")
finally:
    db.close()
'@

$pythonCode | python -