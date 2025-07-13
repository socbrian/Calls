"""Platform for Broadcastify Calls media player."""
import logging

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaType,
)
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
    """Set up the Broadcastify Calls media player platform."""
    coordinator = hass.data[DOMAIN]["coordinator"]
    client = hass.data[DOMAIN]["client"]

    async_add_entities([BroadcastifyCallMediaPlayer(coordinator, client)], True)
    _LOGGER.debug("Broadcastify Calls Media Player platform set up.")

class BroadcastifyCallMediaPlayer(CoordinatorEntity, MediaPlayerEntity):
    """Representation of a Broadcastify Call media player."""

    def __init__(self, coordinator, client: BroadcastifyApiClient):
        """Initialize the media player."""
        super().__init__(coordinator)
        self._client = client
        self._name = "Broadcastify Audio Player"
        self._unique_id = f"{DOMAIN}_audio_player"
        self._state = None # Current state (e.g., playing, idle)
        self._media_content_id = None # URL of the currently playing media
        self._media_title = None # Title of the currently playing media

    @property
    def name(self):
        """Return the name of the media player."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID to use for this media player."""
        return self._unique_id

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        # This media player primarily supports playing a specific URL
        return (
            MediaPlayerEntityFeature.PLAY_MEDIA
            | MediaPlayerEntityFeature.VOLUME_SET # Can control volume if connected to a speaker
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.VOLUME_MUTE
            | MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.PLAY
        )

    @property
    def state(self):
        """Return the state of the media player."""
        return self._state

    @property
    def media_content_type(self):
        """Return the content type of currently playing media."""
        return MediaType.MUSIC # Assuming audio/mpeg or similar

    @property
    def media_content_id(self):
        """Content ID of currently playing media."""
        return self._media_content_id

    @property
    def media_title(self):
        """Title of currently playing media."""
        return self._media_title

    async def async_play_media(
        self, media_type: MediaType | str, media_id: str, **kwargs
    ) -> None:
        """Play a piece of media."""
        if media_type == MediaType.MUSIC: # Or check for 'audio/mpeg' if more specific
            _LOGGER.info(f"Playing Broadcastify audio: {media_id}")
            self._media_content_id = media_id
            self._media_title = f"Broadcastify Call ({media_id.split('/')[-1]})" # Simple title from URL
            self._state = "playing"
            self.async_write_ha_state()

            # In a real scenario, you would trigger playback on a connected speaker.
            # Home Assistant's core handles the actual streaming to media players
            # configured in your system (e.g., Google Cast, Sonos, VLC).
            # This entity primarily serves as a source for the media_content_id.
            # You would typically call another media player's play_media service
            # from an automation based on this entity's state changes or a new call event.
            # Example:
            # await self.hass.services.async_call(
            #     "media_player",
            #     "play_media",
            #     {
            #         "entity_id": "media_player.your_actual_speaker", # Replace with your speaker entity
            #         "media_content_id": media_id,
            #         "media_content_type": media_type
            #     },
            #     blocking=True,
            # )
        else:
            _LOGGER.warning(f"Unsupported media type: {media_type}")

    async def async_media_stop(self) -> None:
        """Stop media player."""
        _LOGGER.info("Stopping Broadcastify audio.")
        self._state = "idle"
        self._media_content_id = None
        self._media_title = None
        self.async_write_ha_state()
        # In a real scenario, you would send a stop command to the actual speaker.

    # Implement other media player features as needed:
    # async_media_play()
    # async_media_pause()
    # async_set_volume(volume: float)
    # async_mute_volume(mute: bool)

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        await super().async_added_to_hass()
        # Listen for updates from the coordinator
        self.async_on_remove(self.coordinator.async_add_listener(self._handle_coordinator_update))
        # Perform initial update
        self._handle_coordinator_update()

    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        # This media player doesn't necessarily change its *state* based on new calls directly,
        # but rather provides the *ability* to play media when a new call is detected by the sensor
        # or an automation.
        # However, if you want the media player to automatically play the latest call,
        # you would add logic here:
        if self.coordinator.data:
            latest_call = self.coordinator.data[-1]
            audio_url = latest_call.get("audio_url")
            if audio_url and audio_url != self._media_content_id: # Play only if it's a new audio URL
                _LOGGER.info(f"New audio URL detected by coordinator: {audio_url}. Triggering playback.")
                # This will call async_play_media on this entity.
                # You'd then need an automation to route this to your actual speaker.
                self.hass.async_create_task(
                    self.async_play_media(MediaType.MUSIC, audio_url)
                )
        self.async_write_ha_state()

