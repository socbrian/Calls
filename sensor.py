"""Platform for Broadcastify Calls sensor."""
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN, BroadcastifyApiClient # Import DOMAIN and BroadcastifyApiClient from __init__.py

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType = None,
):
    """Set up the Broadcastify Calls sensor platform."""
    # The coordinator is stored in hass.data by __init__.py
    coordinator = hass.data[DOMAIN]["coordinator"]
    client = hass.data[DOMAIN]["client"] # Access the client if needed by the sensor

    # Add the BroadcastifyCallSensor entity
    async_add_entities([BroadcastifyCallSensor(coordinator, client)], True)
    _LOGGER.debug("Broadcastify Calls Sensor platform set up.")

class BroadcastifyCallSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Broadcastify Call sensor."""

    def __init__(self, coordinator, client: BroadcastifyApiClient):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._client = client # Store the client instance
        self._state = None
        self._attributes = {}
        self._name = "Latest Broadcastify Call"
        self._unique_id = f"{DOMAIN}_latest_call"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID to use for this sensor."""
        return self._unique_id

    @property
    def state(self):
        """Return the state of the sensor."""
        # The state could be the call_id or a simplified description
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:radio-tower" # You can choose a more appropriate icon

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        await super().async_added_to_hass()
        # Listen for updates from the coordinator
        self.async_on_remove(self.coordinator.async_add_listener(self._handle_coordinator_update))
        # Perform initial update
        self._handle_coordinator_update()

    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        # The coordinator.data contains the list of new calls from the last fetch
        if self.coordinator.data:
            latest_call = self.coordinator.data[-1] # Get the very latest call from the batch
            _LOGGER.debug(f"Sensor updating with latest call: {latest_call.get('call_id')}")

            self._state = latest_call.get("call_id") # Set the state to the call ID
            self._attributes = {
                "timestamp": latest_call.get("timestamp"),
                "talkgroup": latest_call.get("talkgroup"),
                "description": latest_call.get("description"),
                "audio_url": latest_call.get("audio_url"),
                "feed_id": latest_call.get("feed_id") # Assuming feed_id is part of the call data
            }
            self.async_write_ha_state()
        else:
            _LOGGER.debug("No new calls in coordinator data for sensor update.")
            # Optionally, you might want to clear state or set a default if no calls are active
            # self._state = None
            # self._attributes = {}
            # self.async_write_ha_state()

