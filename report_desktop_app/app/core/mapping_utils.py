"""Convert between UI mapping (canonical -> source) and session storage (file:source -> canonical)."""

from __future__ import annotations


def storage_to_ui_mapping(
    stored: dict[str, str],
    filename: str,
) -> dict[str, str]:
    """Session storage -> MappingDialog (canonical field -> Excel column)."""
    prefix = f"{filename}:"
    ui: dict[str, str] = {}
    for key, canonical in stored.items():
        if key.startswith(prefix):
            source = key[len(prefix) :]
            if source and canonical:
                ui[canonical] = source
    return ui


def ui_to_storage_mapping(
    ui: dict[str, str],
    filename: str,
) -> dict[str, str]:
    """MappingDialog result -> session storage."""
    stored: dict[str, str] = {}
    for canonical, source in ui.items():
        if source and canonical:
            stored[f"{filename}:{source}"] = canonical
    return stored


def remap_preset_for_file(
    preset: dict[str, str],
    filename: str,
    source_columns: list[str],
) -> dict[str, str]:
    """
    Apply a preset to the current workbook.

    Preset keys use ``otherfile:column``; output uses ``filename:column`` when
    the column exists in ``source_columns``.
    """
    column_set = set(source_columns)
    stored: dict[str, str] = {}
    for key, canonical in preset.items():
        if ":" in key:
            _, source_col = key.split(":", 1)
        else:
            source_col = key
        if source_col in column_set:
            stored[f"{filename}:{source_col}"] = canonical
    return stored
