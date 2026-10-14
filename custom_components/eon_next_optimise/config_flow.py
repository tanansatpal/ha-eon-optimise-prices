"""Validate the user's own Optimise app login before creating an entry."""

import hashlib

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AuthenticationError, OptimiseClient, PriceFeedError
from .const import CONF_REFRESH_TOKEN, DOMAIN, NAME


def account_id(username):
    return hashlib.sha256(username.strip().casefold().encode()).hexdigest()


def login_schema():
    return vol.Schema(
        {
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
        }
    )


class OptimiseConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _validate(self, user_input):
        client = OptimiseClient(
            async_get_clientsession(self.hass), user_input[CONF_USERNAME], user_input[CONF_PASSWORD]
        )
        try:
            await client.fetch(self.hass.async_add_executor_job)
        except AuthenticationError:
            return None, {"base": "invalid_auth"}
        except PriceFeedError:
            return None, {"base": "cannot_connect"}
        return {**user_input, CONF_REFRESH_TOKEN: client.refresh_token}, {}

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            user_input = {**user_input, CONF_USERNAME: user_input[CONF_USERNAME].strip()}
            await self.async_set_unique_id(account_id(user_input[CONF_USERNAME]))
            self._abort_if_unique_id_configured()
            data, errors = await self._validate(user_input)
            if data is not None:
                return self.async_create_entry(title=NAME, data=data)
        return self.async_show_form(step_id="user", data_schema=login_schema(), errors=errors)

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        errors = {}
        if user_input is not None:
            entry = self._get_reauth_entry()
            if account_id(user_input[CONF_USERNAME]) != entry.unique_id:
                return self.async_abort(reason="wrong_account")
            user_input = {**user_input, CONF_USERNAME: user_input[CONF_USERNAME].strip()}
            data, errors = await self._validate(user_input)
            if data is not None:
                return self.async_update_reload_and_abort(entry, data_updates=data)
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=login_schema(), errors=errors
        )
