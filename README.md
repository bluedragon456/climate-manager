# Climate Manager

Climate Manager is a Home Assistant custom integration that adds a comfort-focused control layer on top of an existing thermostat. Instead of building and maintaining a pile of helpers and automations, you configure one integration that reacts to occupancy, sleep, guest mode, open windows, outdoor temperature, and manual thermostat changes.

It is designed for people who already have a working thermostat in Home Assistant and want smarter target management without replacing the thermostat entity itself.

## What it does

- Wraps an existing `climate` entity with profile-based temperature control
- Supports `home`, `sleep`, `guest`, `away`, `manual override`, `windows open`, and `paused` states
- Applies a weather-aware heating comfort curve using an outdoor temperature sensor
- Detects manual temperature or HVAC mode changes at the thermostat
- Can treat manual changes as ignore, temporary override, or hold-until-cleared
- Exposes status sensors, control buttons, a master enable switch, and services
- Persists runtime state so temporary overrides and pause state survive reloads and restarts

## Best fit

Climate Manager works best if you already have:

- A thermostat entity in Home Assistant
- An outdoor temperature sensor
- Optional helper entities for sleep, away, guest, season, and open windows or doors

It is especially useful if you want the thermostat to feel more adaptive without building separate automations for every condition.

## Installation

### HACS

Repository URL: `https://github.com/bluedragon456/climate-manager`

1. Open HACS.
2. Go to the menu and select **Custom repositories**.
3. Add this repository URL and choose **Integration**.
4. Install **Climate Manager**.
5. Restart Home Assistant.
6. Go to **Settings > Devices & Services**.
7. Select **Add Integration** and search for **Climate Manager**.

### Manual

Copy `custom_components/climate_manager` into:

```text
/config/custom_components/climate_manager
```

Restart Home Assistant, then add the integration from **Settings > Devices & Services**.

## Configuration

Climate Manager is configured through the UI. There is no YAML setup.

### Required during setup

- `Thermostat`: the `climate` entity Climate Manager should control
- `Outdoor temperature sensor`: used for the heating comfort curve

### Optional during setup

- `Sleep schedule`: a `schedule` entity for sleep mode
- `Away mode boolean`: an `input_boolean` for away mode
- `Guest mode boolean`: an `input_boolean` for guest mode
- `Manual climate lock boolean`: an `input_boolean` that forces Climate Manager into override-lock mode
- `Window or door open sensor`: a `binary_sensor` used for HVAC backoff
- `Season source`: an `input_text`, `sensor`, or `select` used when HVAC preference is `Auto`

### Recommended example entities

- `climate.living_room_thermostat`
- `sensor.outdoor_temperature`
- `schedule.climate_sleep`
- `input_boolean.away_mode`
- `input_boolean.guest_mode`
- `input_boolean.climate_override_lock`
- `binary_sensor.window_or_door_open`
- `input_text.season_mode`

## Options you can tune

After setup, the options flow lets you tune the integration without editing YAML:

- Heat targets for home, sleep, guest, and away
- Cool targets for home, sleep, guest, and away
- HVAC preference: `Auto`, `Heat`, `Cool`, or `Off`
- Four outdoor temperature curve bands with configurable offsets
- Per-profile curve weights
- Manual temperature change behavior
- Manual HVAC mode change behavior
- Temporary override duration
- Manual change grace period
- Window-open delay before backoff activates
- Window-close restore buffer
- Minimum and maximum heat or cool limits
- Temperature change threshold for manual-change detection
- Whether overrides are canceled by away, sleep, or window backoff

## How profile selection works

Climate Manager evaluates conditions in this priority order:

1. Paused or smart control disabled
2. Override-lock boolean is on
3. Manual override is active
4. Window or door backoff is active
5. Away mode
6. Guest mode
7. Sleep schedule
8. Home

That makes behavior predictable and easier to debug from the exposed status sensors.

## Manual override behavior

When somebody changes the thermostat directly, Climate Manager compares that change to the last command it sent.

You can choose how it responds:

- `Ignore`: keep controlling normally
- `Temporary override`: stop controlling until the override expires
- `Hold until cleared`: stop controlling until you clear the override

You can also create a temporary override explicitly with the built-in service.

## Window and door handling

If a configured window or door sensor stays open past the configured delay, Climate Manager can:

- Turn HVAC off
- Apply a heat setback
- Apply a cool setback

When the sensor closes, Climate Manager waits for the restore buffer before resuming normal control.

## Entities created

### Sensors

- `Active profile`
- `Desired HVAC mode`
- `Current set temp`
- `Target heat`
- `Target cool`
- `Comfort offset`
- `Status`
- `Override until`
- `Windows backoff until`
- `Last reason`
- `Last action`

### Binary sensors

- `Smart control active`
- `Manual override active`
- `Windows backoff active`
- `Fail-safe active`

### Buttons

- `Recalculate now`
- `Clear override`
- `Pause`
- `Resume`

### Switch

- `Enabled`

Turning the `Enabled` switch off pauses Climate Manager. Turning it back on resumes smart control.

## Services

Climate Manager registers these services:

- `climate_manager.recalculate`
- `climate_manager.clear_override`
- `climate_manager.pause`
- `climate_manager.resume`
- `climate_manager.set_temporary_override`

If you only have one Climate Manager instance loaded, `entry_id` is optional. If you have multiple instances, include the `entry_id`.

### Example: temporary override

```yaml
service: climate_manager.set_temporary_override
data:
  duration_minutes: 120
  target_temp: 71
  hvac_mode: heat
```

## Fail-safe behavior

If the thermostat becomes unavailable, Climate Manager stops applying changes and exposes that state through the `Fail-safe active` binary sensor and `Status` sensor. Once the thermostat becomes available again, normal recalculation resumes.

## Notes

- Climate Manager controls your existing thermostat; it does not create a replacement climate entity
- Outdoor temperature currently affects the heating comfort curve
- In `Auto` HVAC preference, the season source is used to prefer `heat` for `winter`, `cool` for `summer`, and `heat_cool` otherwise
- Runtime state such as temporary override timers and pause state is restored after restart

## Troubleshooting

### It is not changing my thermostat

Check these first:

- The configured thermostat entity is available
- The integration is not paused
- A manual override is not active
- The override-lock boolean is not on
- A windows-open backoff is not active
- The thermostat supports the HVAC mode and temperature fields Climate Manager is trying to set

### It keeps going into manual override

Review:

- `Manual temperature change behavior`
- `Manual HVAC mode change behavior`
- `Manual change grace seconds`
- `Meaningful temperature change threshold`

The `Last reason`, `Last action`, `Status`, and `Override until` sensors are the quickest way to understand what happened.

### Auto mode is not choosing the right HVAC mode

If HVAC preference is `Auto`, verify the configured season entity returns a state like `winter` or `summer`. Any other value falls back to `heat_cool`.

## Version

Current integration version: `1.1.8`
