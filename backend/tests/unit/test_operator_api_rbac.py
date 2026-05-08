from __future__ import annotations

import pytest

from app.api.v1.accounting import _authorize_accounting_read as assert_accounting_read
from app.api.v1.billing_dashboard import _assert_operator_role as assert_billing_dashboard_operator
from app.api.v1.brokers import _assert_staff_dashboard_role as assert_broker_dashboard_role
from app.api.v1.customer_accounts import _assert_staff_dashboard_role as assert_customer_dashboard_role
from app.api.v1.dashboard import _assert_operator_role as assert_dashboard_operator
from app.api.v1.drivers import _assert_staff_dashboard_role as assert_driver_dashboard_role
from app.api.v1.loads import _assert_staff_load_management_role
from app.core.exceptions import ForbiddenError, UnauthorizedError


def test_driver_blocked_from_operator_dashboard_apis() -> None:
    with pytest.raises(UnauthorizedError):
        assert_dashboard_operator({"role": "driver"})
    with pytest.raises(UnauthorizedError):
        assert_billing_dashboard_operator({"role": "driver"})


def test_driver_blocked_from_dashboard_management_apis() -> None:
    token_payload = {"role": "driver"}

    for guard in (
        assert_broker_dashboard_role,
        assert_customer_dashboard_role,
        assert_driver_dashboard_role,
        _assert_staff_load_management_role,
        assert_accounting_read,
    ):
        with pytest.raises(ForbiddenError):
            guard(token_payload)
