# Climate Manager

Climate Manager is a Home Assistant custom integration that manages an existing thermostat around a configurable comfort target. It does not replace your thermostat entity. Instead, it watches your thermostat and optional context signals like sleep, away, guest, override lock, windows, and season, then applies the safest HVAC mode and target settings needed for the current situation.

This integration is a good fit if you already have a working `climate` entity in Home Assistant and want smarter target management without building a large automation stack by hand.

## Current Status

Climate Manager currently:

- Controls an existing thermostat entity
- Supports `home`, `sleep`, `guest`, `away`, `manual override`, `override lock`, `windows open`, and `paused` states
- Uses comfort-centered Auto control with a default `70 F` comfort target
- Shapes transition-season Auto ranges around outdoor hot and cold boost conditions
- Preserves profile targets and outdoor curves for explicit Heat/Cool behavior
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
- `Comfort target`
- `Transition heat target`
- `Transition cool target`
- `Outdoor boost state`
- `Active control reason`
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
- Global comfort target fallback
- Home comfort target
- Sleep comfort target
- Guest comfort target
- Transition comfort band
- Minimum Auto heat/cool gap
- Outdoor hot boost temperature
- Outdoor cold boost temperature
- Outdoor boost deadband
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
- If HVAC preference is `Auto`, Climate Manager uses comfort-centered control and the season entity guides mode selection:
  - `winter` -> `heat`
  - `summer` -> `cool`
  - `spring`, `fall`, and `autumn` -> `heat_cool`
  - anything else -> `heat_cool`
- During manual override, override lock, or paused mode, Climate Manager stops applying changes.

## Profile Comfort Target Behavior

In `Auto`, Climate Manager centers control around the active profile comfort target.

- Home comfort defaults to `70 F`.
- Sleep comfort defaults to `68 F`.
- Guest comfort defaults to `70 F`.
- Away uses the configured away heat/cool targets as a safety range instead of a comfort target.
- Heating season normally uses `heat` at the active comfort target.
- Cooling season normally uses `cool` at the active comfort target.
- Transition season uses `heat_cool` around the active comfort target.
- Explicit `Heat`, `Cool`, and `Off` preferences do not use the comfort-centered Auto calculation.

With the home defaults:

- `Home comfort target`: `70 F`
- `Transition comfort band`: `6 F`
- `Minimum Auto heat/cool gap`: `6 F`

Normal transition Auto is:

- Heat target: `67 F`
- Cool target: `73 F`

## Transition Auto Behavior

Spring, fall, autumn, missing season, and unknown season use transition Auto. Climate Manager keeps the thermostat in `heat_cool` and adjusts the range around the comfort target.

The active comfort side moves toward the comfort target while the opposite side moves enough to preserve the required Auto gap.

| Situation | Heat target | Cool target |
| --- | --- | --- |
| Normal transition | `67 F` | `73 F` |
| Hot boost | `64 F` | `70 F` |
| Cold boost | `70 F` | `76 F` |

The `Current set temp` sensor reports the active side during hot or cold boost. During normal transition it reports the heat side of the range.

Sleep uses the same math around its default `68 F` comfort target, so normal sleep transition is `65 / 71` before any curve adjustment.

## Comfort Curve Behavior

In comfort-centered `Auto`, Climate Manager applies a linear outdoor curve around the active profile comfort target:

- If outdoor temperature is below the active comfort target, the heat side rises by `0.5 F` for every `3 F` of difference.
- If outdoor temperature is above the active comfort target, the cool side lowers by `0.5 F` for every `3 F` of difference.
- Existing per-profile heat and cool curve weights still scale the result.
- Away mode does not use the comfort curve; it uses the configured away heat/cool safety range.

Example: with home comfort `70 F` and outdoor temperature `64 F`, the heat curve adds `1.0 F` before final min/max and Auto-gap normalization.

## Outdoor Boost Behavior

Outdoor boost uses the outdoor temperature sensor only when HVAC preference is `Auto`.

Defaults:

- Hot boost starts at `80 F`
- Cold boost starts at `55 F`
- Boost deadband is `2 F`

Hot boost remains active until outdoor temperature drops below `78 F`. Cold boost remains active until outdoor temperature rises above `57 F`.

Outdoor boost does not override explicit `Heat`, `Cool`, or `Off`. In transition season, it primarily shapes the `heat_cool` range instead of forcing a single mode. In summer and winter, Climate Manager may already be using single-mode `cool` or `heat`, and the active target remains centered on the comfort target by default.

## Ecobee Heat/Cool Minimum Gap Handling

Some thermostats, including Ecobee, require a minimum spread between `target_temp_low` and `target_temp_high` in Auto/`heat_cool`.

Climate Manager uses `Minimum Auto heat/cool gap`, default `6 F`, and will normalize outgoing Auto ranges so Home Assistant and the thermostat accept them. The built-in minimum is never lower than `5 F`.

Final Auto ranges are normalized in one pass so they respect both the configured heat/cool min/max limits and the minimum Auto gap whenever that is possible. If the configured allowed range is narrower than the minimum Auto gap, Climate Manager falls back to the widest range allowed by the configured limits and adds `range_gap_limited` to `Active control reason`. If a configured min target is higher than its matching max target, `Active control reason` includes `range_limits_invalid`.

## Legacy Profile And Curve Behavior

The existing profile targets and outdoor curve band options are not removed. They remain available for explicit/profile-style behavior, including explicit `Heat`, explicit `Cool`, and window/door setback behavior.

In comfort-centered `Auto`, the profile comfort targets and comfort-relative outdoor curve supersede the old season baseline/profile target math. Existing installs keep their old options, but Auto calculations now use the comfort-centered model.

### Existing Outdoor Curve Options

### Default Heat Curve Behavior

The legacy heat curve provides a positive comfort bump below `65 F`, then tapers down to neutral through `75 F`:

| Outdoor temperature | Default heat offset | Effect on heat target |
| --- | --- | --- |
| `< 50 F` | `+3.0 F` | Raise the profile heat target by `3.0 F` |
| `50-54.9 F` | `+2.0 F` | Raise the profile heat target by `2.0 F` |
| `55-64.9 F` | `+1.0 F` | Raise the profile heat target by `1.0 F` |
| `65-75 F` | `0.0 F` | Keep the profile heat target unchanged |
| `> 75 F` | `0.0 F` | Keep the profile heat target unchanged |

### Default Cooling Curve Behavior

The legacy cooling curve includes four outdoor-temperature cooling bands:

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
- Outdoor temperature can activate hot or cold boost in `Auto`.
- Season values currently recognize `winter`, `spring`, `summer`, `fall`, and `autumn`.
- Heating and cooling targets are clamped by your configured min and max values whenever those limits can also satisfy the minimum Auto gap.
- Auto mode works best when the season entity reports values like `winter`, `spring`, `summer`, or `fall`.
- Home, sleep, and guest use profile-specific comfort targets in `Auto`; away uses the away heat/cool safety range.
- Outdoor boost state is persisted as normal runtime state. If the stored runtime state is cleared, boost state is recalculated from the current outdoor temperature on the next update.
- If heat/cool min/max limits are too narrow to satisfy `Minimum Auto heat/cool gap`, `Active control reason` includes `range_gap_limited` and the thermostat may still reject the Auto range.
- If a configured min target is higher than its matching max target, `Active control reason` includes `range_limits_invalid`; fix the option values before relying on Auto control.
- Profile target and curve options are preserved, but comfort-centered `Auto` supersedes the old season baseline/profile target math.
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

- `Outdoor boost state`
- `Active control reason`
- `Comfort target`
- `Transition cool target`
- `Target cool`
- `Current set temp`
- Your outdoor temperature sensor reading against a local weather source for the same time period

With the defaults, spring/fall transition Auto should move from `67 / 73` to `64 / 70` when hot boost activates at `80 F`. If `Outdoor boost state` stays `none`, check the outdoor temperature sensor and the configured hot boost threshold.

### Heating Is Not Responding To Colder Outdoor Temperatures

Check:

- `Outdoor boost state`
- `Active control reason`
- `Comfort target`
- `Transition heat target`
- `Target heat`
- `Current set temp`
- Your outdoor temperature sensor reading against a local weather source for the same time period

With the defaults, spring/fall transition Auto should move from `67 / 73` to `70 / 76` when cold boost activates at `55 F`.

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

If HVAC preference is `Auto`, check the season entity state and `Active control reason`. `winter` maps to `heat`, `summer` maps to `cool`, and `spring`, `fall`, `autumn`, or any other value uses transition `heat_cool`.

## Migration Notes

Existing installs keep their current option values. New comfort-centered options are added with defaults:

- `Comfort target`: `70 F` fallback
- `Home comfort target`: `70 F`
- `Sleep comfort target`: `68 F`
- `Guest comfort target`: `70 F`
- `Transition comfort band`: `6 F`
- `Minimum Auto heat/cool gap`: `6 F`
- `Outdoor hot boost temperature`: `80 F`
- `Outdoor cold boost temperature`: `55 F`
- `Outdoor boost deadband`: `2 F`

No old options are removed. In `Auto`, the new comfort-centered model supersedes old profile target and seasonal baseline behavior. Explicit `Heat`, explicit `Cool`, away safety range, and window/door setback behavior continue to use the existing profile target and curve options.
