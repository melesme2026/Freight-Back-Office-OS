from __future__ import annotations

import pytest

from app.api.v1.billing_dashboard import _assert_operator_role as assert_billing_dashboard_operator
from app.api.v1.dashboard import _assert_operator_role as assert_dashboard_operator
from app.core.exceptions import UnauthorizedError


def test_driver_blocked_from_operator_dashboard_apis() -> None:
    with pytest.raises(UnauthorizedError):
        assert_dashboard_operator({"role": "driver"})
    with pytest.raises(UnauthorizedError):
        assert_billing_dashboard_operator({"role": "driver"})
