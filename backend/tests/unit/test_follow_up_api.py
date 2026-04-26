from __future__ import annotations

import pytest

from app.api.v1.follow_ups import _authorize
from app.core.exceptions import ForbiddenError


def test_driver_cannot_generate_or_update_followups() -> None:
    with pytest.raises(ForbiddenError):
        _authorize({"role": "driver"}, write=True)


def test_viewer_can_read_but_not_write() -> None:
    _authorize({"role": "viewer"}, write=False)
    with pytest.raises(ForbiddenError):
        _authorize({"role": "viewer"}, write=True)
