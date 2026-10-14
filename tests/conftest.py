"""Home Assistant lifecycle tests with synthetic prices and no provider requests."""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.util import dt as dt_util


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def prices():
    now = dt_util.utcnow()
    start = now.replace(minute=0 if now.minute < 30 else 30, second=0, microsecond=0)
    return {
        direction: [
            {
                "valid_from": (start + timedelta(minutes=30 * i)).isoformat(),
                "valid_to": (start + timedelta(minutes=30 * (i + 1))).isoformat(),
                "value_inc_vat": value + i,
                "source_quality": "current" if i == 0 else "forecast",
                "provider_estimate": i != 0,
            }
            for i in range(3)
        ]
        for direction, value in (("import", 12.5), ("export", 7.0))
    }


@pytest.fixture
def fetch(prices):
    with patch(
        "custom_components.eon_next_optimise.api.OptimiseClient.fetch",
        new=AsyncMock(return_value=prices),
    ) as mock:
        yield mock
