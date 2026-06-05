## Climate Manager Control Philosophy

Climate Manager must be comfort-centered, not season-centered.

The primary goal is:
- User sets a desired comfort target, default `70°F`.
- Climate Manager chooses the safest HVAC mode and target settings needed to keep the home near that comfort target.
- Outdoor temperature, weather/forecast data, occupancy/home mode, window/door states, and manual controls adjust behavior around the comfort target.
- Seasons only guide whether the home is in heating season, cooling season, or transition season.
- Seasons must not become the main source of comfort math.

## Required Behavior Model

Use this control hierarchy:

### 1. Safety and blocking states

These always come first:

- Master disabled
- Pause
- Manual override
- Override lock
- Window/door backoff
- Unavailable required entities
- Unavailable thermostat

Normal smart control must not bypass these states.

### 2. Explicit user HVAC preference

Explicit user choices remain authoritative.

- `Off`, `Heat`, and `Cool` must not be overridden by season logic.
- Outdoor boost must not override explicit HVAC choices.
- Existing profile targets and legacy outdoor curve behavior should remain available where still supported.
- Comfort-centered Auto logic applies only to Auto/smart control behavior unless intentionally expanded later.

### 3. Comfort-centered Auto behavior

Default comfort target:

```text
comfort_target = 70°F