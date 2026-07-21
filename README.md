# Climate Manager

Climate Manager is a Home Assistant custom integration that manages an existing thermostat around a configurable comfort target. It does not replace your thermostat entity. Instead, it watches your thermostat and optional context signals like sleep, away, guest, override lock, windows, and season, then applies the safest HVAC mode and target settings needed for the current situation.

This integration is a good fit if you already have a working `climate` entity in Home Assistant and want smarter target management without building a large automation stack by hand.

## Current Status

Climate Manager currently:

- Controls an existing thermostat entity
- Supports `home`, `sleep`, `guest`, `away`, `heading home`, `manual override`, `override lock`, `windows open`, and `paused` states
- Uses comfort-centered Auto control with a default `70 F` comfort target
- Supports Fahrenheit, Celsius, or Home Assistant system-unit temperature display/input
- Shapes transition-season Auto ranges around outdoor hot and cold boost conditions
- Preserves profile targets and outdoor curves for explicit Heat/Cool behavior
- Detects manual thermostat setpoint and HVAC mode changes
- Can ignore manual changes, treat them as a temporary override, or hold them until cleared
- Exposes status sensors, control buttons, a master enable switch, and services
- Persists runtime state across reloads and Home Assistant restarts

Current integration version: `2.0.0-beta.2`

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
- `Window safety state`
- `Window safety activation reason`
- `Window safety activated at`
- `Window safety cleared at`
- `Window safety clear reason`
- `Window safety deadline`
- `Window safety minimum indoor temperature`
- `Window safety maximum indoor temperature`
- `Window safety hysteresis`
- `Last reason`
- `Last action`

### Binary Sensors

- `Smart control active`
- `Manual override active`
- `Windows backoff active`
- `Window temperature safety override enabled`
- `Window temperature safety override active`
- `Window temperature safety override blocked`
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
- `Temperature unit`: use Home Assistant system unit, Fahrenheit, or Celsius

### Optional During Setup

- `Sleep schedule`: a `schedule` entity
- `Away mode boolean`: an `input_boolean`
- `Guest mode boolean`: an `input_boolean`
- `Manual climate lock boolean`: an `input_boolean`
- `Window or door open sensor`: a `binary_sensor`
- `Season source`: an `input_text`, `sensor`, or `select`
- `Heading home request`: a `binary_sensor` or `input_boolean` produced by an external Home Assistant automation

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

The options flow is grouped so normal comfort settings are not mixed with legacy tuning.

### Simple Comfort

Use this first for normal comfort-centered Auto control:

- Smart control enabled
- HVAC preference: `Auto`, `Heat`, `Cool`, or `Off`
- Default comfort target
- Custom Home, Sleep, and Guest comfort target toggles and values

### Transition Auto And Outdoor Boost

- Transition comfort band
- Minimum Auto heat/cool gap
- Outdoor hot boost temperature
- Outdoor cold boost temperature
- Outdoor boost deadband

### Safety, Away, And Limits

- Away heat target
- Away cool target
- Min and max heat targets
- Min and max cool targets

### Manual Override And Windows

- Manual temperature change behavior
- Manual HVAC mode change behavior
- Temporary override duration
- Manual change grace period
- Whether overrides are canceled by away, sleep, or windows backoff
- Windows action: `Turn HVAC off`, `Heat setback`, or `Cool setback`
- Window-open delay
- Window-close restore delay

### Window Temperature Safety Override

- Opt-in enable switch, disabled by default
- Maximum active window-backoff duration, default `240` minutes
- Minimum safe indoor temperature, default `50 F`
- Maximum safe indoor temperature, default `80 F`
- Recovery hysteresis, default `2 F`

### Advanced Comfort Curve

- Home, sleep, and guest heat curve weights
- Home, sleep, and guest cool curve weights

These weights scale the comfort-centered outdoor curve used in `Auto`.

### Legacy Explicit Heat/Cool Tuning

These settings are preserved for existing installs and explicit/profile-style behavior:

- Home, sleep, and guest heat targets
- Home, sleep, and guest cool targets
- Legacy heat curve bands and offsets
- Legacy cool curve bands and offsets
- Away heat and cool curve weights

Comfort-centered `Auto` uses the comfort target settings first. Explicit `Heat`, explicit `Cool`, away safety, and window/door setback behavior can still use legacy profile targets and curves.

### Diagnostics And Temperature Units

- Meaningful temperature change threshold
- Manual detection diagnostics logging
- Temperature unit mode

## Temperature Units

Climate Manager stores and computes temperatures internally in Fahrenheit, then converts at Home Assistant boundaries.

Temperature unit modes:

- `Use Home Assistant system unit`: new installs default to this.
- `Fahrenheit`: always show options, diagnostics, service inputs, and thermostat commands in Fahrenheit.
- `Celsius`: show options, diagnostics, service inputs, and thermostat commands in Celsius.

Existing installs that do not have a stored temperature unit mode continue using Fahrenheit until changed.

Absolute temperatures and temperature differences are converted differently:

- Absolute temperatures include comfort targets, thermostat setpoints, outdoor thresholds, curve band thresholds, and min/max limits.
- Temperature differences include offsets, transition comfort band, minimum Auto gap, boost deadband, and manual change threshold.

The outdoor temperature sensor and thermostat attributes are read in the resolved Home Assistant-facing unit and converted to internal Fahrenheit before control calculations run. Thermostat service calls are converted back to the resolved unit.

## Profile Priority

Climate Manager resolves the active profile in this order:

1. Smart control disabled or paused
2. Override lock
3. Manual override
4. Windows backoff
5. Heading home, only when Away is active
6. Away
7. Guest
8. Sleep
9. Home

## HVAC Mode Selection

- If HVAC preference is `Heat`, `Cool`, or `Off`, that mode is used directly.
- If HVAC preference is `Auto`, Climate Manager uses comfort-centered control and the season entity guides mode selection:
  - `winter` -> `heat`
  - `summer` -> `cool`
  - `spring`, `fall`, and `autumn` -> `heat_cool`
  - anything else -> `heat_cool`
- During manual override, override lock, or paused mode, Climate Manager stops applying changes.

## Profile Comfort Target Behavior

In `Auto`, Climate Manager centers control around the default comfort target unless a profile-specific comfort target is enabled.

- Default comfort target defaults to `70 F`.
- Home, Sleep, and Guest can each use a custom comfort target when their custom target option is enabled.
- If a profile-specific comfort target is missing, unset, or still at its migration default, Climate Manager uses the default comfort target.
- The `Comfort target` sensor reports the active effective comfort target after the active comfort offset is applied.
- The `Comfort offset` sensor reports the capped total automatic comfort adjustment from the outdoor curve plus any active outdoor boost.
- Changing only `Default comfort target` changes Home, Sleep, and Guest Auto control unless a custom target is enabled for that profile.
- Away uses the configured away heat/cool targets as a safety range instead of a comfort target.
- Heating season normally uses `heat` at the active comfort target.
- Cooling season normally uses `cool` at the active comfort target.
- Transition season uses `heat_cool` around the active comfort target.
- Explicit `Heat`, `Cool`, and `Off` preferences do not use the comfort-centered Auto calculation.

With the home defaults:

- `Default comfort target`: `70 F`
- `Comfort offset`: `0 F`
- `Transition comfort band`: `6 F`
- `Minimum Auto heat/cool gap`: `6 F`

Normal transition Auto is:

- Heat target: `67 F`
- Cool target: `73 F`

## Transition Auto Behavior

Spring, fall, autumn, missing season, and unknown season use transition Auto. Climate Manager keeps the thermostat in `heat_cool` and adjusts the range around the comfort target.

When a comfort offset is active, Climate Manager first calculates the effective comfort target, then builds the transition range around that effective target. The active comfort side moves toward the effective comfort target while the opposite side moves enough to preserve the required Auto gap.

| Situation | Heat target | Cool target |
| --- | --- | --- |
| Normal transition | `67 F` | `73 F` |
| Hot boost at `95 F` outdoor | `65 F` | `71 F` |
| Cold boost at `55 F` outdoor | `69.5 F` | `75.5 F` |

The `Current set temp` sensor reports the active side during hot or cold boost. During normal transition it reports the heat side of the range.

Sleep and Guest use the same math around the default comfort target unless their custom comfort target options are enabled.

### Comfort Target Pipeline

In comfort-centered `Auto`, Climate Manager uses one comfort-target pipeline before it decides what to send to the thermostat:

1. Resolve the base comfort target from the active profile.
2. Calculate the outdoor comfort curve adjustment.
3. Add the active outdoor boost adjustment, if any.
4. Calculate the effective comfort target.
5. Cap the effective comfort target between the configured minimum cool target and maximum heat target.
6. Generate the transition heat/cool range from the capped effective comfort target.
7. Run final thermostat safety normalization on the generated range.
8. Send the final thermostat command if it differs meaningfully from the current thermostat state.

The comfort target cap applies only to the effective comfort target. It does not directly clamp the transition heat or cool target. After the range is generated, final thermostat safety normalization may still adjust one or both sides so the command respects the configured heat/cool limits and the minimum required Auto spread.

Example with a capped cold adjustment:

- Base comfort target: `70 F`
- Outdoor comfort curve adjustment: `+7 F`
- Cold boost adjustment: `+1 F`
- Raw effective comfort target: `78 F`
- Capped effective comfort target: `75 F`
- Transition comfort band: `6 F`
- Generated transition heat/cool range before final safety normalization: `72 / 78`

## Comfort Curve Behavior

In comfort-centered `Auto`, Climate Manager applies a linear outdoor curve around the active profile comfort target:

- If outdoor temperature is below the active profile comfort target, the comfort offset increases by `0.5 F` for every `5 F` of difference.
- If outdoor temperature is above the active profile comfort target, the comfort offset decreases by `0.5 F` for every `5 F` of difference.
- Cold outdoor boost adds `1.0 F` to the outdoor curve adjustment.
- Hot outdoor boost subtracts `1.0 F` from the outdoor curve adjustment.
- The effective comfort target is the active profile comfort target plus the active comfort offset, capped between the configured minimum cool target and maximum heat target.
- Existing per-profile heat and cool curve weights still scale the result.
- Curve and effective target results are rounded to the nearest `0.5 F` before final min/max and Auto-gap normalization.
- Away mode does not use the comfort curve; it uses the configured away heat/cool safety range.

Example: with home comfort `70 F` and outdoor temperature `60 F`, the heat curve adds `1.0 F` before final min/max and Auto-gap normalization.

Numeric temperature, curve, and threshold options use `0.5` degree steps in the resolved unit. Fahrenheit-mode values are rounded to the nearest `0.5 F` when loaded or saved; Celsius-mode values are converted at the UI boundary so they reopen in Celsius-friendly increments.

## Outdoor Boost Behavior

Outdoor boost uses the outdoor temperature sensor only when HVAC preference is `Auto`. Comfort-centered `Auto` treats the outdoor temperature sensor as required; if the configured sensor is missing, `unknown`, `unavailable`, or non-numeric, Climate Manager stops comfort Auto writes and reports `outdoor_temperature_unavailable` through `Active control reason`.

Defaults:

- Hot boost starts at `95 F`
- Cold boost starts at `55 F`
- Boost deadband is `2 F`

Hot boost remains active until outdoor temperature drops below `93 F`. Cold boost remains active until outdoor temperature rises above `57 F`.

Outdoor boost does not override explicit `Heat`, `Cool`, or `Off`. In `Auto`, it stacks with the outdoor comfort curve before the effective comfort target is capped. Cold boost makes the effective target `1.0 F` warmer than the curve alone; hot boost makes it `1.0 F` cooler than the curve alone. In transition season, Climate Manager then builds the `heat_cool` range around that capped effective comfort target. In summer and winter, Climate Manager may already be using single-mode `cool` or `heat`, and the active target remains centered on the capped effective comfort target by default.

The displayed `Outdoor boost state` values remain `hot`, `cold`, or `none` for compatibility. The internal option name for hot outdoor boost is legacy-compatible, but the user-facing setting is `Outdoor hot boost temperature`.

The `95 F` hot boost default applies to new installs and installs that do not already have a saved hot boost option. Existing installs keep their saved option value until changed in the integration options.

## Ecobee Heat/Cool Minimum Gap Handling

Some thermostats, including Ecobee, require a minimum spread between `target_temp_low` and `target_temp_high` in Auto/`heat_cool`.

Climate Manager uses `Minimum Auto heat/cool gap`, default `6 F`, and will normalize outgoing Auto ranges so Home Assistant and the thermostat accept them. The built-in minimum is never lower than `5 F`.

Final Auto ranges are normalized in one pass so they respect both the configured heat/cool min/max limits and the minimum Auto gap whenever that is possible. If the configured allowed range is narrower than the minimum Auto gap, Climate Manager falls back to the widest range allowed by the configured limits and adds `range_gap_limited` to `Active control reason`. If a configured min target is higher than its matching max target, `Active control reason` includes `range_limits_invalid`.

This final normalization is separate from the comfort target cap. The cap limits the effective comfort target before transition range generation; normalization protects the final thermostat command after the heat/cool range has been generated.

## Legacy Profile And Curve Behavior

The existing profile targets and outdoor curve band options are not removed. They remain available for explicit/profile-style behavior, including explicit `Heat`, explicit `Cool`, and window/door setback behavior.

In comfort-centered `Auto`, the profile comfort targets and comfort-relative outdoor curve supersede the old season baseline/profile target math. Existing installs keep their old options, but Auto calculations now use the comfort-centered model.

### Existing Outdoor Curve Options

### Default Heat Curve Behavior

The legacy heat curve provides a positive comfort bump below `65 F`, then tapers down to neutral through `75 F`:

| Outdoor temperature | Default heat offset | Effect on heat target |
| --- | --- | --- |
| `<= 49.5 F` | `+3.0 F` | Raise the profile heat target by `3.0 F` |
| `<= 54.5 F` | `+2.0 F` | Raise the profile heat target by `2.0 F` |
| `<= 64.5 F` | `+1.0 F` | Raise the profile heat target by `1.0 F` |
| `<= 75 F` | `0.0 F` | Keep the profile heat target unchanged |
| `> 75 F` | `0.0 F` | Keep the profile heat target unchanged |

### Default Cooling Curve Behavior

The legacy cooling curve includes four outdoor-temperature cooling bands:

- `65 F` to `75 F`
- `75.5 F` to `84.5 F`
- `85 F` to `94.5 F`
- `95 F` and above

| Outdoor temperature | Default cool offset | Effect on cool target |
| --- | --- | --- |
| `<= 75 F` | `0.0 F` | Keep the profile cool target unchanged |
| `75.5-84.5 F` | `-1.0 F` | Lower the profile cool target by `1.0 F` |
| `85-94.5 F` | `-2.0 F` | Lower the profile cool target by `2.0 F` |
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

The open delay is stored and interpreted in minutes. The restore setting retains the legacy internal key `windows_restore_delay_minutes` for backward compatibility, but its value is displayed and interpreted as seconds. Existing stored numeric values are not silently converted.

Only an explicit `off` state from the configured aggregate sensor counts as a trustworthy close. `unknown`, `unavailable`, or a missing entity freezes the last trustworthy pending/active state and cannot restore HVAC control. Closing before the open deadline cancels pending protection immediately; closing after protection activates starts the restore delay. Reloads and restarts retain the original open, close, and deadline timestamps. While protection is active, a one-minute state recheck also recovers if Home Assistant's state changed but the expected close event was missed.

With the `Turn HVAC off` action, an open sensor can still keep the HVAC off indefinitely by design when the optional Window Temperature Safety Override is disabled. Existing installations keep that behavior unless the feature is explicitly enabled.

### Window Temperature Safety Override

The opt-in safety layer preserves the configured window action initially, then independently watches the thermostat's `current_temperature` while backoff is active; no additional indoor sensor is required. It activates when the indoor temperature reaches the configured minimum or maximum, or when the maximum backoff duration expires. A low-temperature trigger temporarily selects Heat, a high-temperature trigger temporarily selects Cool, and the duration trigger selects a wide Heat/Cool safety envelope. The protective heat target is the minimum plus hysteresis; the protective cool target is the maximum minus hysteresis.

When a thermostat advertises no `heat_cool` mode, maximum-duration protection selects its supported Heat or Cool mode according to which safety boundary is closer and re-evaluates on every control pass. Heat-only and Cool-only thermostats protect the capability they actually expose. If the mode required by the current unsafe temperature is unsupported, Climate Manager does not send an invalid command and reports the capability block in diagnostics.

Safety remains latched while the window is open, unavailable, or in the close restore delay. It ends only after a trustworthy `off` window state completes the existing restore delay, at which point Climate Manager recalculates Home, Away, Guest, Sleep, Pre-arrival, or any retained manual override. It never changes the stored HVAC preference, `windows_action`, `min_heat_target`, or `max_cool_target`.

Precedence is: disabled/paused, unavailable thermostat, override lock, window temperature safety, manual override, ordinary window backoff, pre-arrival, away, guest, sleep, then home. If override lock or another higher-priority block prevents an active safety command, the safety entities and diagnostics report that blocked state.

## Heading Home Preconditioning

Climate Manager can consume an optional `Heading home request` entity. Location, direction, authorization, and stale-data logic remain outside the integration in a Home Assistant automation; Climate Manager only consumes the resulting `on` or `off` state.

When Away is active and the request is `on`, Climate Manager selects the `pre_arrival` profile. It keeps Away physically active, uses the Home comfort target and curve weights, and reuses the existing seasonal mode selection: summer uses cooling, winter uses heating, and spring/fall uses transition Auto. Pause, override lock, manual override, and window backoff remain higher priority. An unavailable or unknown request is treated as inactive.

## Services

Climate Manager registers these services:

- `climate_manager.recalculate`
- `climate_manager.clear_override`
- `climate_manager.pause`
- `climate_manager.resume`
- `climate_manager.set_temporary_override`

`entry_id` can be omitted if exactly one Climate Manager instance is loaded. If multiple instances are loaded, include `entry_id`.

`set_temporary_override` interprets `target_temp` in the integration's resolved temperature unit. Existing installs default to Fahrenheit. New installs default to the Home Assistant system unit unless changed in Temperature units.

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
- If the outdoor temperature sensor is unavailable or non-numeric, comfort-centered `Auto` stops applying thermostat setpoints and reports `outdoor_temperature_unavailable`. Explicit `Heat`, `Cool`, and `Off` preferences remain available.

## Troubleshooting

### Thermostat Is Not Changing

Check:

- The thermostat entity is available
- Climate Manager is not paused
- A manual override is not active
- Override lock is not active
- Windows backoff is not active
- `Active control reason` is not `outdoor_temperature_unavailable`
- The thermostat supports the requested HVAC mode and temperature fields

For window incidents, inspect `Windows raw state`, `Windows protection state`, `Windows open since`, `Windows closed since`, `Windows backoff until`, `Window timer scheduled`, `Window timer expected at`, `Window timer kind`, `Last window timer reason`, `Window safety state`, `Window safety activation reason`, and `Window safety deadline`. These distinguish pending, active, restoring, unavailable-sensor, canceled, safety, blocked, and callback states without requiring log review.

### Cooling Is Not Responding To Hotter Outdoor Temperatures

Check:

- `Outdoor boost state`
- `Active control reason`
- `Comfort target`
- `Transition cool target`
- `Target cool`
- `Current set temp`
- Your outdoor temperature sensor reading against a local weather source for the same time period

With the defaults, spring/fall transition Auto should move from `67 / 73` to `65 / 71` when hot boost activates at `95 F`. If `Outdoor boost state` stays `none`, check the outdoor temperature sensor and the configured hot boost threshold.

### Heating Is Not Responding To Colder Outdoor Temperatures

Check:

- `Outdoor boost state`
- `Active control reason`
- `Comfort target`
- `Transition heat target`
- `Target heat`
- `Current set temp`
- Your outdoor temperature sensor reading against a local weather source for the same time period

With the defaults, spring/fall transition Auto should move from `67 / 73` to `69.5 / 75.5` when cold boost activates at `55 F`.

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
- `Outdoor hot boost temperature`: `95 F`
- `Outdoor cold boost temperature`: `55 F`
- `Outdoor boost deadband`: `2 F`

No old options are removed. In `Auto`, the new comfort-centered model supersedes old profile target and seasonal baseline behavior. Explicit `Heat`, explicit `Cool`, away safety range, and window/door setback behavior continue to use the existing profile target and curve options.

The optional `pre_arrival_entity` is additive and defaults to unconfigured, so existing entries retain their current Away behavior. No config-entry migration is required.

The legacy `windows_restore_delay_minutes` key is retained because released versions have interpreted its numeric value as seconds since v1.1.4. Renaming or multiplying existing stored values would change current behavior; the UI, documentation, and regression tests therefore lock the released seconds interpretation while preserving the old storage key.

Temperature-unit migration behavior:

- Existing installs without a stored unit mode continue using Fahrenheit.
- New installs default to `Use Home Assistant system unit`.
- Changing the unit mode changes how options are displayed and how service inputs/thermostat payloads are interpreted; stored control values remain internally Fahrenheit.
- Old profile and curve options remain available under `Legacy explicit Heat/Cool tuning`.
