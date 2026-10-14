"""Verify actual HA config flow, device grouping, reauth and stale feed handling."""

from datetime import timedelta

import pytest
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eon_next_optimise.api import AuthenticationError, PriceFeedError
from custom_components.eon_next_optimise.config_flow import account_id
from custom_components.eon_next_optimise.const import DOMAIN, MAX_AGE, NAME

LOGIN = {CONF_USERNAME: "synthetic@example.test", CONF_PASSWORD: "synthetic-test-only"}


async def setup(hass, fetch):
    entry = MockConfigEntry(
        domain=DOMAIN, title=NAME, unique_id=account_id(LOGIN[CONF_USERNAME]), data=LOGIN.copy()
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_user_flow_validates_login(hass, fetch):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] == "form"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], LOGIN)
    assert result["type"] == "create_entry"
    assert result["title"] == NAME
    await hass.async_block_till_done()
    fetch.assert_awaited()


@pytest.mark.parametrize(
    "error,key",
    [
        (AuthenticationError("private-password"), "invalid_auth"),
        (PriceFeedError("private-token"), "cannot_connect"),
    ],
)
async def test_flow_errors_are_generic(hass, fetch, error, key):
    fetch.side_effect = error
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], LOGIN)
    assert result["type"] == "form"
    assert result["errors"] == {"base": key}
    assert "private" not in str(result)


async def test_duplicate_login_is_blocked(hass, fetch):
    await setup(hass, fetch)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], LOGIN)
    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"


async def test_one_device_three_entities_and_no_controls(hass, fetch):
    entry = await setup(hass, fetch)
    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert len(entities) == 3
    assert {e.domain for e in entities} == {"sensor"}
    assert len({e.device_id for e in entities}) == 1
    device = dr.async_get(hass).async_get(entities[0].device_id)
    assert device.name == NAME
    assert device.identifiers == {(DOMAIN, entry.entry_id)}
    assert "example.test" not in str(device.identifiers)
    states = [hass.states.get(e.entity_id) for e in entities]
    assert sorted(
        s.state for s in states if s.attributes.get("unit_of_measurement") == "p/kWh"
    ) == ["12.5", "7.0"]
    assert "synthetic-test-only" not in str(states)


async def test_current_price_moves_at_boundary_without_new_api_call(hass, fetch, prices):
    entry = await setup(hass, fetch)
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, entry.entry_id + "_import")
    coordinator = entry.runtime_data
    from unittest.mock import patch

    boundary = dt_util.parse_datetime(prices["import"][1]["valid_from"])
    coordinator.last_success = boundary - timedelta(minutes=1)
    with patch("custom_components.eon_next_optimise.sensor.dt_util.utcnow", return_value=boundary):
        coordinator.async_update_listeners()
        await hass.async_block_till_done()
        assert hass.states.get(entity_id).state == "13.5"


async def test_feed_expires_and_hides_old_rates(hass, fetch):
    entry = await setup(hass, fetch)
    entry.runtime_data.last_success = dt_util.utcnow() - MAX_AGE - timedelta(seconds=1)
    entry.runtime_data.async_update_listeners()
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, entry.entry_id + "_import")
    assert hass.states.get(entity_id).state == "unavailable"
    assert not hass.states.get(entity_id).attributes.get("rates")


async def test_outage_does_not_leave_a_live_price(hass, fetch):
    entry = await setup(hass, fetch)
    fetch.side_effect = PriceFeedError("private-provider-body")
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, entry.entry_id + "_import")
    assert hass.states.get(entity_id).state == "unavailable"


async def test_reauth_preserves_entities(hass, fetch):
    entry = await setup(hass, fetch)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "reauth", "entry_id": entry.entry_id}, data=entry.data
    )
    assert result["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], LOGIN)
    assert result["type"] == "abort"
    assert result["reason"] == "reauth_successful"
    await hass.async_block_till_done()
    assert len(er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)) == 3


async def test_reauth_rejects_switching_accounts(hass, fetch):
    entry = await setup(hass, fetch)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "reauth", "entry_id": entry.entry_id}, data=entry.data
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**LOGIN, CONF_USERNAME: "another@example.test"}
    )
    assert result["reason"] == "wrong_account"


async def test_auth_failure_requests_reauth(hass, fetch):
    entry = await setup(hass, fetch)
    fetch.side_effect = AuthenticationError("private")
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.config_entries.flow.async_progress_by_handler(DOMAIN)


async def test_unload_removes_states(hass, fetch):
    entry = await setup(hass, fetch)
    entity_ids = [
        e.entity_id for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    ]
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert all(
        hass.states.get(eid) is None or hass.states.get(eid).state == "unavailable"
        for eid in entity_ids
    )


async def test_diagnostics_exclude_credentials_and_prices(hass, fetch):
    from custom_components.eon_next_optimise.diagnostics import async_get_config_entry_diagnostics

    entry = await setup(hass, fetch)
    diagnostic = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostic["last_update_success"] is True
    assert diagnostic["channels"]["import"]["periods"] == 3
    assert diagnostic["channels"]["export"]["periods"] == 3
    for secret in (*LOGIN.values(), "value_inc_vat", "refresh_token", "rates"):
        assert secret not in str(diagnostic)


async def test_two_accounts_have_separate_devices(hass, fetch):
    first = await setup(hass, fetch)
    second = MockConfigEntry(
        domain=DOMAIN,
        title=NAME,
        unique_id=account_id("another@example.test"),
        data={**LOGIN, CONF_USERNAME: "another@example.test"},
    )
    second.add_to_hass(hass)
    assert await hass.config_entries.async_setup(second.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    first_entities = er.async_entries_for_config_entry(registry, first.entry_id)
    second_entities = er.async_entries_for_config_entry(registry, second.entry_id)
    assert len(first_entities) == len(second_entities) == 3
    assert {e.device_id for e in first_entities}.isdisjoint(e.device_id for e in second_entities)
