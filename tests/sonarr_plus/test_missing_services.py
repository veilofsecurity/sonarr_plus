"""Tests for the Sonarr Plus missing episode and search services."""

from unittest.mock import MagicMock

from aiopyarr import ArrConnectionException
from aiopyarr.models.sonarr import SonarrCommands
import probatio
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.sonarr_plus.const import (
    ATTR_COMMAND,
    ATTR_COUNT,
    ATTR_ENTRY_ID,
    ATTR_EPISODE_IDS,
    ATTR_EPISODES,
    DOMAIN,
    SERVICE_GET_MISSING_EPISODES,
    SERVICE_SEARCH_EPISODES,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

# Fixture episodes aired 2014-01-27 (id 14402) and 1960-10-03 (id 889).
NOW = "2014-02-05T00:00:00Z"


async def _get_missing(hass: HomeAssistant, entry: MockConfigEntry, **data):
    return await hass.services.async_call(
        DOMAIN,
        SERVICE_GET_MISSING_EPISODES,
        {ATTR_ENTRY_ID: entry.entry_id, **data},
        blocking=True,
        return_response=True,
    )


@pytest.mark.freeze_time(NOW)
async def test_get_missing_episodes_default_window(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Only episodes inside the default 30 day window are returned."""
    response = await _get_missing(hass, init_integration)

    assert response[ATTR_COUNT] == 1
    assert response[ATTR_EPISODE_IDS] == [14402]
    assert len(response[ATTR_EPISODES]) == 1
    episode = next(iter(response[ATTR_EPISODES].values()))
    assert episode["id"] == 14402
    assert episode["episode_identifier"] == "S04E11"


@pytest.mark.freeze_time(NOW)
async def test_get_missing_episodes_custom_days(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """The days parameter controls the window."""
    short = await _get_missing(hass, init_integration, days=5)
    assert short[ATTR_EPISODE_IDS] == []

    long = await _get_missing(hass, init_integration, days=3650)
    assert long[ATTR_EPISODE_IDS] == [14402]


@pytest.mark.freeze_time(NOW)
async def test_get_missing_episodes_excludes_future(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Episodes that have not aired yet are never returned."""
    response = await _get_missing(hass, init_integration, days=1)
    assert response[ATTR_COUNT] == 0


@pytest.mark.parametrize("days", [0, -1, "abc"])
async def test_get_missing_episodes_invalid_days(
    hass: HomeAssistant, init_integration: MockConfigEntry, days
) -> None:
    """Invalid day values are rejected."""
    with pytest.raises(probatio.MultipleInvalid):
        await _get_missing(hass, init_integration, days=days)


async def test_search_episodes(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_sonarr: MagicMock
) -> None:
    """Searching sends a de-duplicated EpisodeSearch command."""
    mock_sonarr.async_sonarr_command.return_value = MagicMock(id=42, status="queued")

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_SEARCH_EPISODES,
        {ATTR_ENTRY_ID: init_integration.entry_id, ATTR_EPISODE_IDS: [1, 2, 2, "3"]},
        blocking=True,
        return_response=True,
    )

    mock_sonarr.async_sonarr_command.assert_awaited_once_with(
        SonarrCommands.EPISODE_SEARCH, episodeids=[1, 2, 3]
    )
    assert response == {
        ATTR_COUNT: 3,
        ATTR_COMMAND: {"id": 42, "status": "queued"},
    }


@pytest.mark.parametrize("ids", [[], [0], ["x"], "5"])
async def test_search_episodes_invalid_ids(
    hass: HomeAssistant, init_integration: MockConfigEntry, ids
) -> None:
    """An empty or malformed id list is rejected."""
    with pytest.raises(probatio.MultipleInvalid):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SEARCH_EPISODES,
            {ATTR_ENTRY_ID: init_integration.entry_id, ATTR_EPISODE_IDS: ids},
            blocking=True,
        )


async def test_search_episodes_api_error(
    hass: HomeAssistant, init_integration: MockConfigEntry, mock_sonarr: MagicMock
) -> None:
    """API failures surface as HomeAssistantError."""
    mock_sonarr.async_sonarr_command.side_effect = ArrConnectionException("boom")

    with pytest.raises(HomeAssistantError, match="Failed to connect"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_SEARCH_EPISODES,
            {ATTR_ENTRY_ID: init_integration.entry_id, ATTR_EPISODE_IDS: [1]},
            blocking=True,
        )
