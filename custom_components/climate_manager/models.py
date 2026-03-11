"""Models for Climate Manager."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ManagerConfig:
    thermostat_entity: str
    outdoor_temp_entity: str | None = None
    sleep_schedule_entity: str | None = None
    away_entity: str | None = None
    guest_entity: str | None = None
    override_entity: str | None = None
    windows_entity: str | None = None
    season_entity: str | None = None
    smart_control_enabled: bool = True
    hvac_preference: str = "auto"
    heat_home: float = 69.0
    heat_sleep: float = 67.0
    heat_guest: float = 70.0
    heat_away: float = 62.0
    cool_home: float = 73.0
    cool_sleep: float = 72.0
    cool_guest: float = 73.0
    cool_away: float = 78.0
    curve_band_1_max: float = 35.0
    curve_band_1_offset: float = 3.0
    curve_band_2_max: float = 45.0
    curve_band_2_offset: float = 2.0
    curve_band_3_max: float = 55.0
    curve_band_3_offset: float = 1.5
    curve_band_4_max: float = 62.0
    curve_band_4_offset: float = 0.5
    curve_weight_home: float = 1.0
    curve_weight_sleep: float = 0.5
    curve_weight_guest: float = 1.0
    curve_weight_away: float = 0.0
    manual_temp_behavior: str = "temporary_override"
    manual_mode_behavior: str = "temporary_override"
    override_duration_minutes: int = 120
    manual_grace_seconds: int = 20
    windows_open_delay_minutes: int = 15
    windows_restore_delay_minutes: int = 15
    windows_action: str = "off"
    min_heat_target: float = 60.0
    max_heat_target: float = 75.0
    min_cool_target: float = 68.0
    max_cool_target: float = 82.0
    temp_change_threshold: float = 0.5
    cancel_override_on_away: bool = True
    cancel_override_on_windows: bool = True
    cancel_override_on_sleep: bool = False


@dataclass(slots=True)
class RuntimeState:
    active_profile: str | None = None
    desired_hvac_mode: str | None = None
    target_heat: float | None = None
    target_cool: float | None = None
    comfort_offset: float = 0.0
    manual_override_active: bool = False
    manual_override_until: datetime | None = None
    manual_hold: bool = False
    windows_backoff_active: bool = False
    windows_backoff_until: datetime | None = None
    paused: bool = False
    status: str = "idle"
    last_commanded_hvac_mode: str | None = None
    last_commanded_temp: float | None = None
    last_commanded_low: float | None = None
    last_commanded_high: float | None = None
    last_command_time: datetime | None = None
    windows_open_since: datetime | None = None
    windows_closed_since: datetime | None = None


@dataclass(slots=True)
class ThermostatSnapshot:
    hvac_mode: str | None
    target_temp: float | None
    target_temp_low: float | None
    target_temp_high: float | None
    current_temperature: float | None
    available: bool


