# Hot Water Model

This is a custom integration for [Home Assistant](https://www.home-assistant.io/) that provides a thermodynamic model for simulating hot water tank behavior.

## Installation

1. Add the integration to HACS.
2. Follow the on-screen instructions to complete setup.

## Features

- Simulates hot water tank behavior based on real-time sensor data.
- Calculates hot and cold water volumes, temperatures, and percentages.
- Provides insights into hot water usage and recovery.

## Configuration

To use this integration, add the following to your `configuration.yaml` file:

```yaml
hot_water_model:
  outlet_temp_sensor: sensor.outlet_temperature
  inlet_temp_sensor: sensor.inlet_temperature
  flow_rate_sensor: sensor.flow_rate
  tank_capacity_litres: 50.0
  target_temperature: 60.0
  heating_element_kw: 3.6
```

## Support

For support, issues, or feature requests, please visit the [GitHub repository](https://github.com/davidlang42/ha-hot-water-model).

## License

This integration is licensed under the [MIT License](https://opensource.org/licenses/MIT).