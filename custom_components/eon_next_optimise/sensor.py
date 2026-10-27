"""Current prices and API periods, grouped under a single device."""

from datetime import timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, MAX_AGE, NAME
from .rates import coverage


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        [OptimisePriceSensor(entry.runtime_data, direction) for direction in ("import", "export")]
        + [OptimiseLastUpdateSensor(entry.runtime_data)]
    )


class OptimiseEntity(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, key):
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.entry.entry_id + "_" + key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=NAME,
            manufacturer="E.ON Next / Amber",
            model="Read-only Optimise price feed",
        )


class OptimisePriceSensor(OptimiseEntity):
    _attr_native_unit_of_measurement = "p/kWh"
    _attr_icon = "mdi:currency-gbp"
    # The full schedule is ~16 KB; keep it live but out of recorder history.
    _unrecorded_attributes = frozenset({"rates"})

    def __init__(self, coordinator, direction):
        super().__init__(coordinator, direction)
        self.direction = direction
        self._attr_name = direction.title() + " price"

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_interval(self.hass, self._advance_current, timedelta(minutes=1))
        )

    @callback
    def _advance_current(self, now):
        self.async_write_ha_state()

    @property
    def available(self):
        now = dt_util.utcnow()
        return bool(
            super().available
            and self.coordinator.last_success
            and now - self.coordinator.last_success < MAX_AGE
            and coverage((self.coordinator.data or {}).get(self.direction, []), now)[0]
        )

    @property
    def native_value(self):
        current, _ = coverage(
            (self.coordinator.data or {}).get(self.direction, []), dt_util.utcnow()
        )
        return current["value_inc_vat"] if current else None

    @property
    def extra_state_attributes(self):
        rows = (self.coordinator.data or {}).get(self.direction, []) if self.available else []
        current, until = coverage(rows, dt_util.utcnow())
        return {
            "rates": rows,
            "source": "optimise_app_api",
            "last_success": self.coordinator.last_success.isoformat()
            if self.coordinator.last_success
            else None,
            "current_rate_available": bool(current),
            "coverage_status": "current" if self.available else "stale_or_missing",
            "coverage_start": rows[0]["valid_from"] if rows else None,
            "coverage_end": rows[-1]["valid_to"] if rows else None,
            "covered_until": until,
            "forecast_is_settlement": False,
            "notice": "Upcoming periods are supplied by the API and may change.",
        }


class OptimiseLastUpdateSensor(OptimiseEntity):
    _attr_name = "Last successful update"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        super().__init__(coordinator, "last_update")

    @property
    def available(self):
        return self.coordinator.last_success is not None

    @property
    def native_value(self):
        return self.coordinator.last_success
