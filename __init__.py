"""The Broadcastify Calls integration."""
import asyncio
import logging
from datetime import timedelta
import aiohttp

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import config_validation as cv

_LOGGER = logging.getLogger(__name__)

DOMAIN = "broadcastify_calls"
PLATFORMS = ["sensor", "media_player"]

# Configuration schema for the integration
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required("api_key"): cv.string,
                vol.Required("feed_ids"): vol.All(cv.ensure_list, [cv.string]),
                vol.Optional("scan_interval", default=30): vol.All(
                    vol.Coerce(int), vol.Range(min=10)
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

BROADCASTIFY_API_BASE_URL = "https://api.broadcastify.com/calls/v1"

class BroadcastifyApiClient:
    """Client for interacting with the Broadcastify Calls API."""

    def __init__(self, hass: HomeAssistant, api_key: str, feed_ids: list[str]):
        """Initialize the API client."""
        self.hass = hass
        self._api_key = api_key
        self._feed_ids = feed_ids
        self._last_call_id = None # To prevent processing the same call multiple times

    async def async_get_latest_calls(self) -> list[dict]:
        """Fetch the latest call data from the Broadcastify API."""
        headers = {"Authorization": f"Bearer {self._api_key}"}
        params = {"feed_ids": ",".join(self._feed_ids), "limit": 10} # Get up to 10 latest calls

        url = f"{BROADCASTIFY_API_BASE_URL}/latest"

        _LOGGER.debug(f"Fetching latest calls from {url} with params: {params}")

        try:
            async with aiohttp.ClientSession() as session: # Use a new session for each request or manage a single session
                async with session.get(url, headers=headers, params=params, timeout=15) as response:
                    response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
                    data = await response.json()
                    _LOGGER.debug(f"Received data: {json.dumps(data, indent=2)}")

                    if "calls" in data and isinstance(data["calls"], list):
                        new_calls = []
                        for call in data["calls"]:
                            # Basic validation of call structure
                            if all(k in call for k in ["call_id", "timestamp", "audio_url", "talkgroup", "description"]):
                                new_calls.append(call)
                            else:
                                _LOGGER.warning(f"Skipping malformed call entry: {call}")
                        return new_calls
                    else:
                        _LOGGER.warning(f"Unexpected API response structure: {data}")
                        return []

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching Broadcastify calls: {err}") from err
        except asyncio.TimeoutError:
            raise UpdateFailed("Timeout fetching Broadcastify calls.")
        except json.JSONDecodeError as err:
            raise UpdateFailed(f"Failed to decode JSON response from Broadcastify API: {err}") from err
        except Exception as err:
            _LOGGER.exception("An unexpected error occurred during API fetch.")
            raise UpdateFailed(f"An unexpected error occurred: {err}") from err

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Broadcastify Calls component."""
    if DOMAIN not in config:
        return True

    conf = config[DOMAIN]
    api_key = conf["api_key"]
    feed_ids = conf["feed_ids"]
    scan_interval = conf["scan_interval"]

    client = BroadcastifyApiClient(hass, api_key, feed_ids)

    async def async_update_data():
        """Fetch data from API."""
        calls = await client.async_get_latest_calls()
        if calls:
            # Sort calls by timestamp to process oldest first if needed
            # Assuming 'timestamp' is a sortable string (e.g., ISO format)
            calls.sort(key=lambda x: x.get("timestamp", ""))

            # Filter out already processed calls based on _last_call_id
            # This logic can be more sophisticated if you need to handle out-of-order calls
            if client._last_call_id:
                new_calls = [call for call in calls if call.get("call_id") != client._last_call_id]
            else:
                new_calls = calls

            if new_calls:
                # Update last processed call ID to the latest call in the current batch
                client._last_call_id = new_calls[-1].get("call_id")
                _LOGGER.debug(f"New calls detected. Last processed call ID: {client._last_call_id}")
                return new_calls
            else:
                _LOGGER.debug("No new calls since last update or all calls already processed.")
                return [] # No new calls to return
        return [] # No calls fetched or error occurred

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="Broadcastify Calls",
        update_method=async_update_data,
        update_interval=timedelta(seconds=scan_interval),
    )

    # Fetch initial data so we have something to start with
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN] = {
        "coordinator": coordinator,
        "client": client # Store client if other platforms need to call its methods directly
    }

    # Set up platforms (sensor, media_player)
    await hass.config_entries.async_forward_entry_setups(ConfigEntry(None, DOMAIN, {}, {}, DOMAIN), PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    # This function is for handling config flows, but good to include for completeness
    # For YAML config, this might not be strictly necessary for simple integrations
    # But it's good practice to include it for future-proofing or if you convert to config flow.
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

