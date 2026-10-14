"""One shared five-minute price request per configured account."""

import logging

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import AuthenticationError, OptimiseClient, PriceFeedError
from .const import CONF_REFRESH_TOKEN, NAME, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class OptimiseCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(
            hass, _LOGGER, name=NAME, config_entry=entry, update_interval=UPDATE_INTERVAL
        )
        self.entry = entry
        self.client = OptimiseClient(
            async_get_clientsession(hass),
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            entry.data.get(CONF_REFRESH_TOKEN),
        )
        self.last_success = None

    async def _async_update_data(self):
        try:
            schedule = await self.client.fetch(self.hass.async_add_executor_job)
        except AuthenticationError:
            raise ConfigEntryAuthFailed("Optimise login needs attention") from None
        except PriceFeedError:
            raise UpdateFailed("Optimise prices are temporarily unavailable") from None
        if self.client.refresh_token != self.entry.data.get(CONF_REFRESH_TOKEN):
            self.hass.config_entries.async_update_entry(
                self.entry, data={**self.entry.data, CONF_REFRESH_TOKEN: self.client.refresh_token}
            )
        self.last_success = dt_util.utcnow()
        return schedule
