"""Color theme definitions — all themes use a bright, light UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

DEFAULT_THEME_ID: Final[str] = "bright_daylight"


@dataclass(frozen=True)
class ColorTheme:
    """Token set used to build the application stylesheet."""

    id: str
    display_name: str
    bg_main: str
    sidebar_bg: str
    card_bg: str
    input_bg: str
    menubar_bg: str
    statusbar_bg: str
    sidebar_title: str
    sidebar_subtitle: str
    sidebar_section: str
    text_primary: str
    text_muted: str
    text_caption: str
    card_title: str
    group_title: str
    border: str
    border_strong: str
    btn_bg: str
    btn_hover: str
    btn_pressed: str
    btn_disabled_bg: str
    btn_disabled_text: str
    secondary_bg: str
    primary_top: str
    primary_bottom: str
    primary_border: str
    primary_hover: str
    primary_text: str
    tool_bg: str
    tool_border: str
    tool_text: str
    tool_hover: str
    list_bg: str
    list_hover: str
    list_selected_bg: str
    list_selected_text: str
    list_selected_border: str
    selection_bg: str
    selection_text: str
    tab_bg: str
    tab_text: str
    tab_hover_bg: str
    tab_hover_text: str
    tab_selected_bg: str
    tab_selected_text: str
    tab_accent: str
    table_alt: str
    table_header_bg: str
    table_grid: str
    workflow_active_bg: str
    workflow_active_text: str
    workflow_done_bg: str
    workflow_done_text: str
    workflow_done_border: str
    workflow_step_bg: str
    workflow_step_text: str
    workflow_step_border: str
    workflow_arrow: str
    workflow_title: str
    scroll_bg: str
    scroll_handle: str
    scroll_handle_hover: str
    splitter: str
    splitter_hover: str
    session_bar_bg: str
    session_bar_border: str
    session_summary: str
    chip_bg: str
    chip_text: str
    chip_border: str
    zoom_label: str
    status_muted: str
    status_info: str
    status_warning: str
    status_error: str
    status_success: str


def _bright_blue() -> ColorTheme:
    return ColorTheme(
        id="bright_daylight",
        display_name="明亮日光（預設）",
        bg_main="#ffffff",
        sidebar_bg="#f0f4ff",
        card_bg="#ffffff",
        input_bg="#ffffff",
        menubar_bg="#ffffff",
        statusbar_bg="#ffffff",
        sidebar_title="#1e3a5f",
        sidebar_subtitle="#64748b",
        sidebar_section="#475569",
        text_primary="#0f172a",
        text_muted="#64748b",
        text_caption="#475569",
        card_title="#1e40af",
        group_title="#334155",
        border="#e2e8f0",
        border_strong="#cbd5e1",
        btn_bg="#ffffff",
        btn_hover="#f1f5f9",
        btn_pressed="#e2e8f0",
        btn_disabled_bg="#f8fafc",
        btn_disabled_text="#94a3b8",
        secondary_bg="#f8fafc",
        primary_top="#60a5fa",
        primary_bottom="#3b82f6",
        primary_border="#2563eb",
        primary_hover="#2563eb",
        primary_text="#ffffff",
        tool_bg="#eff6ff",
        tool_border="#bfdbfe",
        tool_text="#1d4ed8",
        tool_hover="#dbeafe",
        list_bg="#ffffff",
        list_hover="#f1f5f9",
        list_selected_bg="#dbeafe",
        list_selected_text="#1e40af",
        list_selected_border="#93c5fd",
        selection_bg="#dbeafe",
        selection_text="#1e3a8a",
        tab_bg="#f1f5f9",
        tab_text="#64748b",
        tab_hover_bg="#e2e8f0",
        tab_hover_text="#334155",
        tab_selected_bg="#ffffff",
        tab_selected_text="#2563eb",
        tab_accent="#3b82f6",
        table_alt="#f8fafc",
        table_header_bg="#f1f5f9",
        table_grid="#f1f5f9",
        workflow_active_bg="#3b82f6",
        workflow_active_text="#ffffff",
        workflow_done_bg="#ecfdf5",
        workflow_done_text="#047857",
        workflow_done_border="#6ee7b7",
        workflow_step_bg="#ffffff",
        workflow_step_text="#64748b",
        workflow_step_border="#e2e8f0",
        workflow_arrow="#cbd5e1",
        workflow_title="#475569",
        scroll_bg="#f1f5f9",
        scroll_handle="#cbd5e1",
        scroll_handle_hover="#94a3b8",
        splitter="#e2e8f0",
        splitter_hover="#94a3b8",
        session_bar_bg="#ffffff",
        session_bar_border="#e2e8f0",
        session_summary="#334155",
        chip_bg="#f8fafc",
        chip_text="#475569",
        chip_border="#e2e8f0",
        zoom_label="#1e40af",
        status_muted="#64748b",
        status_info="#475569",
        status_warning="#b45309",
        status_error="#dc2626",
        status_success="#059669",
    )


def _bright_sky() -> ColorTheme:
    return ColorTheme(
        id="bright_sky",
        display_name="明亮天藍",
        bg_main="#fafcff",
        sidebar_bg="#e8f4ff",
        card_bg="#ffffff",
        input_bg="#ffffff",
        menubar_bg="#ffffff",
        statusbar_bg="#ffffff",
        sidebar_title="#0c4a6e",
        sidebar_subtitle="#0369a1",
        sidebar_section="#0284c7",
        text_primary="#0c4a6e",
        text_muted="#64748b",
        text_caption="#475569",
        card_title="#0369a1",
        group_title="#0e7490",
        border="#bae6fd",
        border_strong="#7dd3fc",
        btn_bg="#ffffff",
        btn_hover="#f0f9ff",
        btn_pressed="#e0f2fe",
        btn_disabled_bg="#f8fafc",
        btn_disabled_text="#94a3b8",
        secondary_bg="#f0f9ff",
        primary_top="#38bdf8",
        primary_bottom="#0ea5e9",
        primary_border="#0284c7",
        primary_hover="#0284c7",
        primary_text="#ffffff",
        tool_bg="#e0f2fe",
        tool_border="#7dd3fc",
        tool_text="#0369a1",
        tool_hover="#bae6fd",
        list_bg="#ffffff",
        list_hover="#f0f9ff",
        list_selected_bg="#e0f2fe",
        list_selected_text="#075985",
        list_selected_border="#7dd3fc",
        selection_bg="#e0f2fe",
        selection_text="#0c4a6e",
        tab_bg="#e0f2fe",
        tab_text="#64748b",
        tab_hover_bg="#bae6fd",
        tab_hover_text="#0369a1",
        tab_selected_bg="#ffffff",
        tab_selected_text="#0284c7",
        tab_accent="#0ea5e9",
        table_alt="#f0f9ff",
        table_header_bg="#e0f2fe",
        table_grid="#e0f2fe",
        workflow_active_bg="#0ea5e9",
        workflow_active_text="#ffffff",
        workflow_done_bg="#ecfdf5",
        workflow_done_text="#047857",
        workflow_done_border="#6ee7b7",
        workflow_step_bg="#ffffff",
        workflow_step_text="#64748b",
        workflow_step_border="#bae6fd",
        workflow_arrow="#7dd3fc",
        workflow_title="#0369a1",
        scroll_bg="#e0f2fe",
        scroll_handle="#7dd3fc",
        scroll_handle_hover="#38bdf8",
        splitter="#bae6fd",
        splitter_hover="#38bdf8",
        session_bar_bg="#ffffff",
        session_bar_border="#bae6fd",
        session_summary="#334155",
        chip_bg="#f0f9ff",
        chip_text="#0369a1",
        chip_border="#bae6fd",
        zoom_label="#0284c7",
        status_muted="#64748b",
        status_info="#0c4a6e",
        status_warning="#b45309",
        status_error="#dc2626",
        status_success="#059669",
    )


def _bright_pearl() -> ColorTheme:
    return ColorTheme(
        id="bright_pearl",
        display_name="明亮珍珠白",
        bg_main="#ffffff",
        sidebar_bg="#f8fafc",
        card_bg="#ffffff",
        input_bg="#ffffff",
        menubar_bg="#ffffff",
        statusbar_bg="#ffffff",
        sidebar_title="#18181b",
        sidebar_subtitle="#71717a",
        sidebar_section="#52525b",
        text_primary="#18181b",
        text_muted="#71717a",
        text_caption="#52525b",
        card_title="#27272a",
        group_title="#3f3f46",
        border="#e4e4e7",
        border_strong="#d4d4d8",
        btn_bg="#ffffff",
        btn_hover="#f4f4f5",
        btn_pressed="#e4e4e7",
        btn_disabled_bg="#fafafa",
        btn_disabled_text="#a1a1aa",
        secondary_bg="#fafafa",
        primary_top="#818cf8",
        primary_bottom="#6366f1",
        primary_border="#4f46e5",
        primary_hover="#4f46e5",
        primary_text="#ffffff",
        tool_bg="#f4f4f5",
        tool_border="#d4d4d8",
        tool_text="#4338ca",
        tool_hover="#e4e4e7",
        list_bg="#ffffff",
        list_hover="#f4f4f5",
        list_selected_bg="#ede9fe",
        list_selected_text="#4338ca",
        list_selected_border="#c4b5fd",
        selection_bg="#ede9fe",
        selection_text="#3730a3",
        tab_bg="#f4f4f5",
        tab_text="#71717a",
        tab_hover_bg="#e4e4e7",
        tab_hover_text="#3f3f46",
        tab_selected_bg="#ffffff",
        tab_selected_text="#4f46e5",
        tab_accent="#6366f1",
        table_alt="#fafafa",
        table_header_bg="#f4f4f5",
        table_grid="#f4f4f5",
        workflow_active_bg="#6366f1",
        workflow_active_text="#ffffff",
        workflow_done_bg="#f0fdf4",
        workflow_done_text="#15803d",
        workflow_done_border="#86efac",
        workflow_step_bg="#ffffff",
        workflow_step_text="#71717a",
        workflow_step_border="#e4e4e7",
        workflow_arrow="#d4d4d8",
        workflow_title="#52525b",
        scroll_bg="#f4f4f5",
        scroll_handle="#d4d4d8",
        scroll_handle_hover="#a1a1aa",
        splitter="#e4e4e7",
        splitter_hover="#a1a1aa",
        session_bar_bg="#ffffff",
        session_bar_border="#e4e4e7",
        session_summary="#3f3f46",
        chip_bg="#fafafa",
        chip_text="#52525b",
        chip_border="#e4e4e7",
        zoom_label="#4338ca",
        status_muted="#71717a",
        status_info="#52525b",
        status_warning="#b45309",
        status_error="#dc2626",
        status_success="#059669",
    )


# Legacy IDs map to bright themes so saved preferences stay valid.
_LEGACY_MAP: dict[str, str] = {
    "professional_blue": "bright_daylight",
    "slate_classic": "bright_pearl",
    "forest_ledger": "bright_sky",
}

THEMES: dict[str, ColorTheme] = {
    "bright_daylight": _bright_blue(),
    "bright_sky": _bright_sky(),
    "bright_pearl": _bright_pearl(),
}


def theme_ids() -> list[str]:
    return list(THEMES.keys())


def resolve_theme_id(theme_id: str | None) -> str:
    if not theme_id:
        return DEFAULT_THEME_ID
    if theme_id in THEMES:
        return theme_id
    return _LEGACY_MAP.get(theme_id, DEFAULT_THEME_ID)


def get_theme(theme_id: str | None) -> ColorTheme:
    return THEMES[resolve_theme_id(theme_id)]
