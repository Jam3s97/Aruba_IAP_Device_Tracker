"""Switch platform — Track New Devices toggle for Aruba Device Tracker."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo

from .const import CONF_TRACK_NEW, DEFAULT_TRACK_NEW, DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the track-new-devices switch entity."""
    async_add_entities([ArubaTrackNewSwitch(entry)])


class ArubaTrackNewSwitch(SwitchEntity):
    """
    Toggle whether newly discovered devices are tracked by default.

    When turned ON it also enables all previously disabled tracker entities
    belonging to this integration entry, so devices discovered while the
    switch was off are not left permanently hidden.
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:radar"

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialise the track-new-devices switch."""
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_track_new_devices"
        self._attr_name = "Track New Devices"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Aruba IAP ({entry.data.get('host', '')})",
            manufacturer="Aruba Networks (HPE)",
            model="Instant AP",
        )

    @property
    def is_on(self) -> bool:
        """Return current tracking state."""
        return self._entry.options.get(
            CONF_TRACK_NEW,
            self._entry.data.get(CONF_TRACK_NEW, DEFAULT_TRACK_NEW),
        )

    async def async_turn_on(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Enable tracking and enable all previously disabled tracker entities."""
        await self._set(value=True)
        await self._enable_all_tracker_entities()

    async def async_turn_off(self, **kwargs: Any) -> None:  # noqa: ARG002
        """Disable tracking for future new devices (does not disable existing ones)."""
        await self._set(value=False)

    async def _set(self, *, value: bool) -> None:
        """Persist the new tracking preference to options."""
        new_options = {**self._entry.options, CONF_TRACK_NEW: value}
        self.hass.config_entries.async_update_entry(self._entry, options=new_options)
        self.async_write_ha_state()

    async def _enable_all_tracker_entities(self) -> None:
        """Enable every device_tracker entity registered under this config entry."""
        registry = er.async_get(self.hass)
        enabled_count = 0

        for entity in er.async_entries_for_config_entry(registry, self._entry.entry_id):
            if entity.domain != "device_tracker":
                continue
            if entity.disabled_by is not None:
                registry.async_update_entity(
                    entity.entity_id,
                    disabled_by=None,
                )
                enabled_count += 1

        if enabled_count:
            LOGGER.info(
                "Aruba Device Tracker: enabled %d previously disabled tracker(s)",
                enabled_count,
            )
        else:
            LOGGER.debug(
                "Aruba Device Tracker: track_new turned on"
                " — no disabled tracker entities found"
            )
