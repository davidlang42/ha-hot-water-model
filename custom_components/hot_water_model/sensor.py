"""Sensor platform for the Hot Water Tank Model."""
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

DOMAIN = "hot_water_model"

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities,
    discovery_info: DiscoveryInfoType = None,
):
    """Set up the calculated hot water sensors configuration."""
    domain_data = hass.data[DOMAIN]
    coordinator = domain_data["coordinator"]
    tank_capacity = domain_data["tank_capacity"]

    entities = [
        HotWaterModelSensor(coordinator, "v_hot", "Hot Volume Available", UnitOfVolume.LITERS, "mdi:water-thermometer", tank_capacity),
        HotWaterModelSensor(coordinator, "v_cold", "Cold Volume Area", UnitOfVolume.LITERS, "mdi:water-outline", tank_capacity),
        HotWaterModelSensor(coordinator, "t_cold", "Cold Zone Temperature", UnitOfTemperature.CELSIUS, "mdi:thermometer", tank_capacity),
        HotWaterModelSensor(coordinator, "percentage", "Hot Water Capacity", PERCENTAGE, "mdi:water-boiler", tank_capacity),
    ]

    async_add_entities(entities)


class HotWaterModelSensor(RestoreEntity, SensorEntity):
    """Representation of an internal calculated thermodynamic tank metric."""

    def __init__(self, coordinator, data_key, name, unit, icon, tank_capacity):
        """Initialize the custom virtual sensor."""
        self.coordinator = coordinator
        self._data_key = data_key
        self._attr_name = name
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._tank_capacity = tank_capacity
        self._attr_unique_id = f"hot_water_tank_model_{data_key}"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def should_poll(self) -> bool:
        """Let Home Assistant core handle updates via the coordinator ticker."""
        return False

    @property
    def available(self) -> bool:
        """Check if coordinator data has resolved cleanly."""
        return self.coordinator.last_update_success

    @property
    def native_value(self):
        """Return the current numerical state calculated from the model."""
        return self.coordinator.data.get(self._data_key)

    async def async_added_to_hass(self):
        """Handle restoring historical value states across system restarts."""
        await super().async_added_to_hass()
        
        old_state = await self.async_get_last_state()
        if old_state is not None and old_state.state not in (None, "unknown", "unavailable"):
            try:
                # Handle recovery limits checking if full capacity values mismatched old data entries
                val = float(old_state.state)
                if self._data_key == "v_hot" and val > self._tank_capacity:
                    val = self._tank_capacity
                self.coordinator.data[self._data_key] = val
            except ValueError:
                pass

        self.async_on_remove(
            self.coordinator.async_add_listener(self.async_write_ha_state)
        )