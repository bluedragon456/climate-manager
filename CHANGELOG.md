# Changelog

## 2.0.9 - 2026-10-19

### Occupied Auto cooling ceiling

Cool outdoor weather can raise the effective comfort target and Auto cooling
threshold even while sunlight warms the home. This release adds an optional
occupied cooling ceiling so Home, Guest, and Heading Home can cool sooner.

- Added **Limit occupied Auto cooling target** and **Occupied Auto cooling ceiling**
  under **Simple comfort**. The ceiling value defaults to `72 F`; the feature is
  disabled until explicitly enabled, preserving existing installations.
- Applied the ceiling after outdoor curve, boost, and transition calculations,
  including summer Auto cooling. A `70 / 75 F` range becomes `67 / 72 F` with a
  `72 F` ceiling and a `5 F` Auto gap. Lower cooling targets stay lower.
- Preserved Sleep, Away, explicit Heat/Cool/Off, manual overrides, pause, override
  lock, window protection, and disabled smart control. No entity IDs changed.
- Preserved configured minimum temperature limits and Auto heat/cool separation.
  The active control reason reports when these prevent the requested ceiling.
- Added Fahrenheit/Celsius option handling, diagnostic reasons, setup instructions,
  troubleshooting, migration notes, and rollback instructions.

### Installation and activation

Update Climate Manager through HACS and restart Home Assistant. Open
**Settings > Devices & Services > Climate Manager > Configure > Simple comfort**,
enable **Limit occupied Auto cooling target**, set the ceiling, and save.
This does not clear manual overrides or bypass window protection.

Check the final cooling target and thermostat-reported target once Auto is active.
The ceiling limits the setpoint; actual room temperature also depends on thermostat
hysteresis and HVAC capacity. It does not add solar forecasting.

### Validation

139 standalone regression tests passed, including the cold-weather daytime
thermostat command, profile exclusions, safety limits, settings persistence, and
Celsius conversion. Python syntax, JSON, translation parity, and diff checks passed.
