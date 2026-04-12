# AGENTS.md

## Purpose

Climate Manager is a Home Assistant custom integration that manages an existing thermostat using profile-based targets and helper entities. It does not replace the thermostat entity. It observes the thermostat and optional context such as sleep, away, guest, override lock, windows, and season, then applies the desired HVAC mode and target temperatures for the current situation.

Use this file as the default operating guide for coding agents working in this repository.

## Repository Scope

This repository ships a Home Assistant custom integration for the `climate_manager` domain.

Important package roots:
- `custom_components/climate_manager`: integration source
- `.github/workflows`: repository validation and release workflows
- `assets` and `brand`: distribution and branding assets
- `README.md`: user-facing behavior, installation, and option documentation
- `hacs.json`: HACS metadata

## Primary Code Map

Core integration files:
- `custom_components/climate_manager/__init__.py`: integration setup and unload entrypoints
- `custom_components/climate_manager/config_flow.py`: config flow and options flow
- `custom_components/climate_manager/coordinator.py`: orchestration between Home Assistant state and manager logic
- `custom_components/climate_manager/manager.py`: primary control logic and decision-making
- `custom_components/climate_manager/models.py`: internal state models and typed structures
- `custom_components/climate_manager/helpers.py`: shared utility helpers
- `custom_components/climate_manager/restore.py`: restored runtime state
- `custom_components/climate_manager/entity.py`: shared entity base behavior
- `custom_components/climate_manager/sensor.py`: sensors exposed by the integration
- `custom_components/climate_manager/binary_sensor.py`: binary sensors exposed by the integration
- `custom_components/climate_manager/button.py`: control buttons such as recalculate or clear override
- `custom_components/climate_manager/switch.py`: master enable switch
- `custom_components/climate_manager/const.py`: constants and option keys
- `custom_components/climate_manager/services.yaml`: service definitions
- `custom_components/climate_manager/strings.json` and `translations/`: UI strings and localization
- `custom_components/climate_manager/manifest.json`: Home Assistant manifest metadata

## Working Rules

When making changes in this repository:
- Preserve Home Assistant custom integration conventions and keep the domain as `climate_manager`.
- Prefer small, behavior-focused changes over broad refactors.
- Keep user-visible behavior aligned with `README.md`, `services.yaml`, `strings.json`, and translations.
- Update docs when configuration, entities, services, or runtime behavior changes.
- Avoid introducing machine-specific absolute paths, editor-specific assumptions, or private environment details into committed files.
- Treat runtime persistence and manual override behavior as sensitive areas; changes there should be deliberate and easy to reason about.

## Change Strategy

Before editing:
- Identify whether the change belongs in config flow, runtime coordination, manager logic, entity exposure, or docs.
- Check whether new behavior also requires updates to manifest metadata, services, strings, or README examples.

While editing:
- Keep logic centralized rather than duplicating profile or HVAC decision rules across files.
- Reuse helper and model layers when possible.
- Keep naming consistent with existing Home Assistant entity concepts and Climate Manager vocabulary.

After editing:
- Re-read the affected user-facing surfaces for consistency.
- Verify that added or renamed options are reflected anywhere they are surfaced.
- Verify that integration metadata still matches repository structure.

## Validation

This repository includes a GitHub validation workflow in `.github/workflows/validate.yml`.

At minimum, changes should preserve:
- `custom_components/climate_manager/manifest.json`
- `custom_components/climate_manager/__init__.py`
- `custom_components/climate_manager/config_flow.py`
- `hacs.json`

The workflow also validates that:
- manifest domain remains `climate_manager`
- `config_flow` remains `true`
- manifest includes a `version`

If local testing is limited, at least sanity-check the changed files for import correctness, Home Assistant integration structure, and README or metadata drift.

## Documentation Expectations

If a change affects any of the following, update documentation in the same pass when practical:
- created entities
- service behavior
- config flow fields or option flow settings
- manual override behavior
- HVAC mode selection behavior
- seasonal or outdoor-temperature target logic

## Path Continuity For Local Threads

Repository copies may move between local folders over time. When continuing work from an older Codex thread or note:
- treat an old local workspace path as historical context, not a different project
- use the currently opened repository as the source of truth
- translate stale local paths to the current workspace before running commands or editing files
- avoid creating duplicate assumptions or duplicate project summaries solely because the local folder changed

## Good Agent First Step

When starting a fresh thread in this repo:
1. Confirm the active workspace path.
2. Read `README.md` and the relevant integration files for the requested change.
3. Check whether the task touches runtime logic, config flow, entities, or docs.
4. Make the change in the smallest coherent set of files.
5. Validate that user-facing docs and metadata still match the implementation.
