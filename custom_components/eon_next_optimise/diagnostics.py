"""Explicitly allow-list diagnostics; never return config-entry credentials."""

from homeassistant.util import dt as dt_util

from .rates import coverage


async def async_get_config_entry_diagnostics(hass, entry):
    """Return coverage and counts, excluding tokens, login and private site data."""
    coordinator = entry.runtime_data
    return {
        "last_update_success": coordinator.last_update_success,
        "last_success": coordinator.last_success.isoformat() if coordinator.last_success else None,
        "channels": {
            direction: {"periods": len(rows), "covered_until": coverage(rows, dt_util.utcnow())[1]}
            for direction, rows in (coordinator.data or {}).items()
        },
    }
