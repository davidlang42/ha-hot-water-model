"""The Thermodynamic Hot Water Tank Model integration."""
from datetime import timedelta
import logging
import time
import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import discovery
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

DOMAIN = "hot_water_model"
UPDATE_INTERVAL = timedelta(seconds=5)

# Configuration Keys
CONF_INLET_TEMP = "inlet_temp_sensor"
CONF_FLOW_RATE = "flow_rate_sensor"
CONF_TANK_CAPACITY = "tank_capacity_litres"
CONF_TARGET_TEMP = "target_temperature"
CONF_ELEMENT_KW = "heating_element_kw"
CONF_INLET_TEMP_FALLBACK = "inlet_temp_fallback"

# Schema validation with your exact existing values as defaults
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_INLET_TEMP): cv.entity_id,
                vol.Required(CONF_FLOW_RATE): cv.entity_id,
                vol.Optional(CONF_TANK_CAPACITY, default=50.0): vol.Coerce(float),
                vol.Optional(CONF_TARGET_TEMP, default=60.0): vol.Coerce(float),
                vol.Optional(CONF_ELEMENT_KW, default=3.6): vol.Coerce(float),
                vol.Optional(CONF_INLET_TEMP_FALLBACK, default=18.0): vol.Coerce(float),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the hot water model platform from configuration.yaml."""
    conf = config[DOMAIN]

    # Read tracking variables from configuration
    inlet_sensor = conf[CONF_INLET_TEMP]
    flow_sensor = conf[CONF_FLOW_RATE]
    
    tank_capacity = conf[CONF_TANK_CAPACITY]
    t_hot_target = conf[CONF_TARGET_TEMP]
    element_kw = conf[CONF_ELEMENT_KW]

    # Calculate dynamic heating factor: (kW * 60 seconds) / 4.184 (specific heat capacity)
    heating_factor = (element_kw * 60.0) / 4.184

    # Share configuration parameters with downstream sensors via hass.data
    hass.data[DOMAIN] = {
        "tank_capacity": tank_capacity
    }

    # Internal runtime state management dictionary
    runtime_data = {
        "v_hot": tank_capacity,
        "v_cold": 0.0,
        "t_cold": conf[CONF_INLET_TEMP_FALLBACK], # Initial fallback, will adjust immediately to sensor state
        "last_run_time": time.time()
    }

    async def async_update_data():
        """Calculate the thermodynamic state-space transition."""
        current_time = time.time()
        dt = (current_time - runtime_data["last_run_time"]) / 60.0  # Time step in minutes
        runtime_data["last_run_time"] = current_time

        if dt <= 0 or dt > 1.0:
            return runtime_data

        # 1. Dynamically read configurations and sensor values
        try:
            flow_rate_state = hass.states.get(flow_sensor)
            flow_rate = float(flow_rate_state.state) if flow_rate_state else 0.0
        except (ValueError, TypeError):
            flow_rate = 0.0

        try:
            inlet_temp_state = hass.states.get(inlet_sensor)
            t_inlet = float(inlet_temp_state.state) if inlet_temp_state else conf[CONF_INLET_TEMP_FALLBACK]
        except (ValueError, TypeError):
            t_inlet = conf[CONF_INLET_TEMP_FALLBACK]

        v_hot = runtime_data["v_hot"]
        v_cold = runtime_data["v_cold"]
        t_cold = runtime_data["t_cold"]

        # 2. State Operations
        if flow_rate > 0:
            # --- MODE 1: FLOW MODE (Shower is Active) ---
            v_hot -= flow_rate * dt
            v_cold += flow_rate * dt

            if v_hot < 0:
                v_hot = 0.0
                v_cold = tank_capacity

            if v_cold > 0:
                # Energy Balance: Element energy minus cold replacement water cooling effect
                net_heat_effect = (flow_rate * (t_inlet - t_cold)) + heating_factor
                dt_cold = (net_heat_effect / v_cold) * dt
                t_cold += dt_cold
                t_cold = min(max(t_cold, t_inlet), t_hot_target)
        else:
            # --- MODE 2: RECOVERY MODE (Idle/Heating) ---
            if v_hot < tank_capacity:
                temp_gap = t_hot_target - t_cold
                if temp_gap <= 0.5:
                    v_hot = tank_capacity
                    v_cold = 0.0
                    t_cold = t_inlet
                else:
                    v_hot_recovery_rate = heating_factor / temp_gap
                    v_hot += v_hot_recovery_rate * dt
                    v_cold -= v_hot_recovery_rate * dt

                    if v_hot >= tank_capacity:
                        v_hot = tank_capacity
                        v_cold = 0.0
                        t_cold = t_inlet
            else:
                v_hot = tank_capacity
                v_cold = 0.0
                t_cold = t_inlet

        # Save math conclusions back into runtime data package
        runtime_data["v_hot"] = round(v_hot, 2)
        runtime_data["v_cold"] = round(v_cold, 2)
        runtime_data["t_cold"] = round(t_cold, 1)
        runtime_data["percentage"] = round((v_hot / tank_capacity) * 100.0, 0)

        return runtime_data

    # Setup the interval loop runner
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="hot_water_model",
        update_method=async_update_data,
        update_interval=UPDATE_INTERVAL,
    )

    await coordinator.async_refresh()
    
    # Store reference to coordinator alongside configuration properties
    hass.data[DOMAIN]["coordinator"] = coordinator

    hass.async_create_task(
        discovery.async_load_platform(hass, "sensor", DOMAIN, {}, config)
    )

    return True