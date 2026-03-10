# Climate Manager

Climate Manager is a Home Assistant custom integration that manages an existing thermostat with comfort-focused logic instead of preset-heavy automation.

## Features

- Weather-based heating comfort curve
- Home, sleep, guest, away, and windows-open profiles
- Temporary manual override when someone changes the thermostat
- One integration options page instead of helper sprawl
- Status sensors, buttons, and services for visibility and control
- Works with your existing thermostat entity

## Install with HACS

Repository URL: `https://github.com/bluedragon456/climate-manager`


1. In HACS, open the menu and choose **Custom repositories**.
2. Add this repository URL.
3. Choose **Integration** as the category.
4. Install **Climate Manager**.
5. Restart Home Assistant.
6. Go to **Settings → Devices & Services → Add Integration**.
7. Search for **Climate Manager**.

## Manual install

Copy `custom_components/climate_manager` into your Home Assistant config directory at:

```text
/config/custom_components/climate_manager
```

Then restart Home Assistant and add the integration from **Settings → Devices & Services**.

## Recommended entities

- Thermostat: `climate.living_room_thermostat`
- Outdoor temp: `sensor.astroweather_2m_temperature`
- Sleep schedule: `schedule.climate_sleep`
- Away mode: `input_boolean.away_mode`
- Guest mode: `input_boolean.guest_mode`
- Override boolean: `input_boolean.climate_override`
- Window/door sensor: `binary_sensor.window_door_open`
- Season source: `input_text.season_mode_state`

