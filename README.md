# Climate Manager

Climate Manager is a Home Assistant custom integration that manages an existing thermostat using profile-based targets and a small set of helper entities. It does not replace your thermostat entity. Instead, it watches your thermostat and optional context signals like sleep, away, guest, override lock, windows, and season, then applies the temperature or HVAC mode you want for the current situation.

This integration is a good fit if you already have a working `climate` entity in Home Assistant and want smarter target management without building a large automation stack by hand.

## Current Status

Climate Manager currently:

- Controls an existing thermostat entity
- Supports `home`, `sleep`, `guest`, `away`, `manual override`, `override lock`, `windows open`, and `paused` states
- Applies heating and cooling comfort offsets based on outdoor temperature
- Applies season-aware baseline shifts for `winter`, `spring`, `summer`, and `fall`
- Detects manual thermostat setpoint and HVAC mode changes
- Can ignore manual changes, treat them as a temporary override, or hold them until cleared
- Exposes status sensors, control buttons, a master enable switch, and services
- Persists runtime state across reloads and Home Assistant restarts

Current integration version: `1.1.14`

## What It Creates

For each config entry, Climate Manager creates:

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

### Binary Sensors

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

Turning `Enabled` off pauses Climate Manager. Turning it back on resumes control.

## Installation

### HACS

Repository URL: `https://github.com/bluedragon456/climate-manager`

1. Open HACS.
2. Go to **Custom repositories**.
3. Add this repository as an **Integration**.
4. Install **Climate Manager**.
5. Restart Home Assistant.
6. Go to **Settings > Devices & Services**.
7. Add the **Climate Manager** integration.

### Manual

Copy `custom_components/climate_manager` to:

```text
/config/custom_components/climate_manager
```

Restart Home Assistant, then add the integration from **Settings > Devices & Services**.

## Configuration

Climate Manager is configured through the UI only. There is no YAML setup.

### Required During Setup

- `Thermostat`: a `climate` entity
- `Outdoor temperature sensor`: a `sensor` entity

### Optional During Setup

- `Sleep schedule`: a `schedule` entity
- `Away mode boolean`: an `input_boolean`
- `Guest mode boolean`: an `input_boolean`
- `Manual climate lock boolean`: an `input_boolean`
- `Window or door open sensor`: a `binary_sensor`
- `Season source`: an `input_text`, `sensor`, or `select`

### Example Helpers

- `climate.living_room`
- `sensor.outdoor_temperature`
- `schedule.climate_sleep`
- `input_boolean.away_mode`
- `input_boolean.guest_mode`
- `input_boolean.climate_override_lock`
- `binary_sensor.window_open`
- `input_text.season_mode`

## Options

The options flow lets you tune:

- Home, sleep, guest, and away heat targets
- Home, sleep, guest, and away cool targets
- HVAC preference: `Auto`, `Heat`, `Cool`, or `Off`
- Four outdoor-temperature heating curve bands and offsets
- Four outdoor-temperature cooling curve bands and offsets
- Per-profile heat and cool curve weights
- Manual temperature change behavior
- Manual HVAC mode change behavior
- Temporary override duration
- Manual change grace period
- Window-open delay
- Window-close restore delay
- Windows action: `Turn HVAC off`, `Heat setback`, or `Cool setback`
- Min and max heat targets
- Min and max cool targets
- Meaningful temperature change threshold
- Whether overrides are canceled by away, sleep, or windows backoff
- Manual detection diagnostics logging

## Profile Priority

Climate Manager resolves the active profile in this order:

1. Smart control disabled or paused
2. Override lock
3. Manual override
4. Windows backoff
5. Away
6. Guest
7. Sleep
8. Home

## HVAC Mode Selection

- If HVAC preference is `Heat`, `Cool`, or `Off`, that mode is used directly.
- If HVAC preference is `Auto`, the season entity is used when available:
  - `winter` -> `heat`
  - `summer` -> `cool`
  - `spring`, `fall`, and `autumn` -> `heat_cool`
  - anything else -> `heat_cool`
- During manual override, override lock, or paused mode, Climate Manager stops applying changes.

## Seasonal Baselines

When a season entity is configured, Climate Manager shifts the configured profile targets before applying the outdoor curve. This keeps profile differences intact while nudging the whole house slightly warmer or cooler through the year.

The seasonal home-equivalent baselines are:

- `winter`: `69 / 74`
- `spring`: `66 / 71`
- `summer`: `66 / 71`
- `fall` and `autumn`: `67 / 72`

These seasonal baselines are applied as offsets relative to the neutral home baseline of `69 / 73`, then the usual profile targets, min/max clamps, and outdoor curve weights still apply.

## Outdoor Temperature Response

Climate Manager resolves a base target from the active profile, then applies an outdoor-temperature offset for the active mode:

- Heating uses the configured heat curve bands and heat curve weights.
- Cooling uses the configured cool curve bands and cool curve weights.
- The final target is clamped to your configured min and max target limits.

### Default Neutral Targets

- `Home`: `73 F`
- `Sleep`: `72 F`
- `Guest`: `73 F`
- `Away`: `78 F`

### Default Heat Curve Behavior

The default heat curve provides a positive comfort bump below `65 F`, then tapers down to neutral through `75 F`:

| Outdoor temperature | Default heat offset | Effect on heat target |
| --- | --- | --- |
| `< 50 F` | `+3.0 F` | Raise the profile heat target by `3.0 F` |
| `50-54.9 F` | `+2.0 F` | Raise the profile heat target by `2.0 F` |
| `55-64.9 F` | `+1.0 F` | Raise the profile heat target by `1.0 F` |
| `65-75 F` | `0.0 F` | Keep the profile heat target unchanged |
| `> 75 F` | `0.0 F` | Keep the profile heat target unchanged |

### Default Cooling Curve Behavior

The integration includes four outdoor-temperature cooling bands:

- `65 F` to `75 F`
- `75.1 F` to `84.9 F`
- `85 F` to `94.9 F`
- `95 F` and above

| Outdoor temperature | Default cool offset | Effect on cool target |
| --- | --- | --- |
| `<= 75 F` | `0.0 F` | Keep the profile cool target unchanged |
| `75.1-84.9 F` | `-1.0 F` | Lower the profile cool target by `1.0 F` |
| `85-94.9 F` | `-2.0 F` | Lower the profile cool target by `2.0 F` |
| `>= 95 F` | `-3.0 F` | Lower the profile cool target by `3.0 F` |

The default cool curve weights are:

- `Home`: `1.0`
- `Sleep`: `0.5`
- `Guest`: `1.0`
- `Away`: `0.0`

The default heat curve weights use the same profile multipliers:

- `Home`: `1.0`
- `Sleep`: `0.5`
- `Guest`: `1.0`
- `Away`: `0.0`

These weights scale the matching band offset before it is added to the profile target.

## Manual Change Handling

When the thermostat changes, Climate Manager compares the new thermostat state to the last command it sent. You can configure both temperature changes and HVAC mode changes to be handled as:

- `Ignore`
- `Temporary override`
- `Hold until cleared`

Temporary overrides expire automatically. Hold overrides remain active until cleared from the button or service.

### Manual Detection Diagnostics

Climate Manager includes a built-in support logging mode for false manual override reports.

Enable `Manual detection diagnostics` in the integration options when you want users to capture troubleshooting logs without turning on broad Home Assistant debug logging.

When enabled, Climate Manager writes support-focused log entries to the normal Home Assistant log for:

- Every stored command snapshot from `set_hvac_mode`
- Every stored command snapshot from `set_temperature`
- Every thermostat-triggered manual detection evaluation

Each manual detection event includes:

- `reason`
- `thermostat_snapshot`
- `last_commanded_snapshot`
- `command_time`
- `grace_until`
- `settle_until`
- `in_grace_window`
- `in_settle_window`
- `mode_changed`
- `temp_changed`
- `field_changes`
- `override_activated`
- `outcome`

This is especially useful for diagnosing thermostats like Ecobee that may echo delayed setpoint changes or apply schedule-driven changes after Climate Manager sends a command.

## Window and Door Backoff

If a configured window or door sensor remains open long enough to pass the configured delay, Climate Manager can:

- Turn HVAC off
- Apply a heat setback
- Apply a cool setback

If windows action is `off`, there is still a freeze-protection behavior: when the season entity reports `winter` and outdoor temperature is `50 F` or below, Climate Manager will hold heat at `50 F` instead of fully shutting off.

When the sensor closes, Climate Manager waits for the configured restore delay before returning to normal control.

## Services

Climate Manager registers these services:

- `climate_manager.recalculate`
- `climate_manager.clear_override`
- `climate_manager.pause`
- `climate_manager.resume`
- `climate_manager.set_temporary_override`

`entry_id` can be omitted if exactly one Climate Manager instance is loaded. If multiple instances are loaded, include `entry_id`.

### Example Service Call

```yaml
service: climate_manager.set_temporary_override
data:
  duration_minutes: 120
  target_temp: 71
  hvac_mode: heat
```

## Notes and Limitations

- Climate Manager controls your existing thermostat; it does not create a replacement `climate` entity.
- Outdoor temperature can affect both heating and cooling targets.
- Seasonal baselines currently recognize `winter`, `spring`, `summer`, `fall`, and `autumn`.
- Cooling targets are clamped by your configured min and max values.
- Auto mode works best when the season entity reports values like `winter`, `spring`, `summer`, or `fall`.
- If the thermostat is unavailable, Climate Manager stops applying changes and exposes that through `Fail-safe active` and `Status`.

## Troubleshooting

### Thermostat Is Not Changing

Check:

- The thermostat entity is available
- Climate Manager is not paused
- A manual override is not active
- Override lock is not active
- Windows backoff is not active
- The thermostat supports the requested HVAC mode and temperature fields

### Cooling Is Not Responding To Hotter Outdoor Temperatures

Check:

- `Desired HVAC mode` is actually `Cool` or `Auto` with the season entity reporting `summer`
- `Target cool`, `Current set temp`, and `Comfort offset`
- Your configured cool curve band offsets in the integration options
- Your outdoor temperature sensor reading against a local weather source for the same time period

If `Comfort offset` stays at `0.0`, Climate Manager is in the neutral zone for the current mode or profile. With the repo defaults, that is expected whenever outdoor temperature stays between `65 F` and `75 F`.

### It Keeps Entering Manual Override

Review:

- `Manual temperature change behavior`
- `Manual HVAC mode change behavior`
- `Manual change grace seconds`
- `Meaningful temperature change threshold`
- `Manual detection diagnostics`

The fastest sensors to inspect are `Last reason`, `Last action`, `Status`, and `Override until`.

If you are collecting a support report:

1. Open the Climate Manager integration options.
2. Turn on `Manual detection diagnostics`.
3. Restart Home Assistant or reload the integration.
4. Reproduce the false manual override.
5. Collect the log lines containing `Stored command snapshot for` and `Manual detection event for`.
6. Share the block around the false trigger, including a few lines before and after it.

The most useful log block includes:

- The `Stored command snapshot for ...` line immediately before the thermostat change
- The `Manual detection event for ...` line with `override_activated=True` or `outcome=manual_override`
- The timestamps on both lines

If you prefer broader integration logs, you can still enable Home Assistant logger overrides:

```yaml
logger:
  default: info
  logs:
    custom_components.climate_manager: debug
```

### Auto Mode Picks the Wrong HVAC Mode

If HVAC preference is `Auto`, check the season entity state. `winter` maps to `heat`, `summer` maps to `cool`, and `spring`, `fall`, `autumn`, or any other value falls back to `heat_cool`.
