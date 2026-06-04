## Climate Manager Control Philosophy

Climate Manager must be comfort-centered, not season-centered.

The primary goal is:
- User sets a desired comfort target, default 70°F.
- Climate Manager chooses the safest HVAC mode and target settings needed to keep the home near that comfort target.
- Outdoor temperature, forecast/weather, occupancy/home mode, window/door states, and manual controls adjust behavior around the comfort target.
- Seasons are only guidance for whether the home is in heating season, cooling season, or transition season. Seasons must not become the main source of comfort math.

### Required behavior model

Use this hierarchy:

1. Safety and blocking states
   - Master disabled
   - Manual override
   - Override lock
   - Pause
   - Window/door backoff
   - Unavailable required entities

2. Explicit user HVAC preference
   - Off, Heat, Cool, and explicit modes remain authoritative.
   - Do not let outdoor boost or season logic override explicit user choices.

3. Comfort-centered Auto behavior
   - Default comfort target: 70°F.
   - Heating season primarily uses heat mode.
   - Cooling season primarily uses cool mode.
   - Transition season uses heat_cool/Auto with a configurable comfort band.
   - Default transition band: 6°F total.
     - Heat = comfort_target - 3
     - Cool = comfort_target + 3

4. Outdoor boost behavior
   - Outdoor boost should pull the active comfort side closer to the comfort target.
   - Outdoor boost should not push beyond the comfort target by default.
   - In transition Auto mode, preserve the thermostat’s required heat/cool gap.
   - Example with comfort_target = 70 and minimum_auto_gap = 6:
     - Normal transition: heat 67 / cool 73
     - Hot boost: cool 70 / heat 64
     - Cold boost: heat 70 / cool 76
   - The opposite side must move as needed so Ecobee/HA does not reject the setpoint range.

5. Seasonal purpose
   - Winter/heating season: focus on heat and optionally raise heat target slightly during extreme cold.
   - Summer/cooling season: focus on cool and optionally lower cool target slightly during extreme heat.
   - Spring/fall/transition: use Auto range unless outdoor conditions justify narrowing the active side toward comfort.

### Migration safety

Do not break current working behavior in one large rewrite.

Prefer a staged migration:
1. Add comfort-centered calculation helpers while keeping current entities/options working.
2. Preserve existing option names where practical.
3. Add new options with defaults instead of removing old ones immediately.
4. Maintain backwards-compatible fallback behavior for existing installs.
5. Keep explicit user controls, manual override, pause, override lock, and window/door backoff behavior intact.
6. Add diagnostics/entities or attributes that expose:
   - comfort target
   - resolved HVAC mode
   - transition heat target
   - transition cool target
   - outdoor boost state
   - active control reason

### README requirement

Any behavior change must update `README.md`.

`README.md` must reflect the current version’s actual behavior and must include the information a Home Assistant user needs to install, configure, understand, and troubleshoot the integration.

At minimum, README updates must cover:
- Installation method
- Required entities
- Optional entities
- Setup flow/options
- Comfort target behavior
- Heating season behavior
- Cooling season behavior
- Transition Auto behavior
- Ecobee heat/cool minimum gap handling
- Outdoor boost behavior
- Window/door and manual override behavior
- Example settings
- Troubleshooting checklist
- Known limitations
- Migration notes when behavior changes

Do not leave README describing older season-first behavior after comfort-centered code is introduced.