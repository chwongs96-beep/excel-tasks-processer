"""Application-wide Qt stylesheet — theme-driven."""

from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.ui.themes import DEFAULT_THEME_ID, THEMES, ColorTheme, get_theme, resolve_theme_id

_SETTINGS_KEY = "ui/theme"


def load_theme_id() -> str:
    settings = QSettings()
    saved = settings.value(_SETTINGS_KEY, DEFAULT_THEME_ID)
    if isinstance(saved, str):
        return resolve_theme_id(saved)
    return DEFAULT_THEME_ID


def save_theme_id(theme_id: str) -> None:
    settings = QSettings()
    settings.setValue(_SETTINGS_KEY, resolve_theme_id(theme_id))


def current_theme() -> ColorTheme:
    return get_theme(load_theme_id())


def build_stylesheet(theme: ColorTheme) -> str:
    t = theme
    return f"""
        QMainWindow {{
            background-color: {t.bg_main};
        }}
        QWidget {{
            font-family: "Microsoft JhengHei UI", "Segoe UI", sans-serif;
            font-size: 14px;
            color: {t.text_primary};
        }}

        QWidget#sidebar {{
            background-color: {t.sidebar_bg};
            border-right: 1px solid {t.border};
            border-radius: 0px;
        }}
        QWidget#sidebar QScrollArea,
        QWidget#sidebar QScrollArea > QWidget > QWidget {{
            background-color: {t.sidebar_bg};
        }}
        QWidget#sidebarHeader {{
            background-color: {t.sidebar_bg};
            border-bottom: 1px solid {t.border};
        }}
        QWidget#sidebarFooter {{
            background-color: {t.sidebar_bg};
            border-top: 2px solid {t.border};
        }}
        QLabel#sidebarScrollHint {{
            color: {t.sidebar_subtitle};
            font-size: 11px;
            padding-top: 4px;
        }}
        QWidget#sidebarContent {{
            background-color: transparent;
        }}
        QScrollArea#sidebarScroll {{
            background-color: {t.sidebar_bg};
            border: none;
        }}
        QLabel#sidebarSection {{
            color: {t.card_title};
            font-size: 13px;
            font-weight: 700;
            padding: 6px 2px 2px 2px;
        }}
        QLabel#sidebarTitle {{
            color: {t.sidebar_title};
            font-size: 17px;
            font-weight: 700;
            padding: 4px 2px 10px 2px;
        }}
        QLabel#sidebarSubtitle {{
            color: {t.sidebar_subtitle};
            font-size: 12px;
            padding-bottom: 10px;
        }}

        QFrame#card {{
            background-color: {t.card_bg};
            border: 1px solid {t.border};
            border-radius: 10px;
        }}
        QLabel#cardTitle {{
            color: {t.card_title};
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.5px;
            padding: 0px 0px 4px 0px;
        }}

        QGroupBox {{
            font-weight: 600;
            font-size: 12px;
            color: {t.card_title};
            border: 1px solid {t.border};
            border-radius: 10px;
            margin-top: 14px;
            padding: 14px 12px 12px 12px;
            background: {t.card_bg};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 8px;
            color: {t.group_title};
        }}

        QPushButton {{
            border: 1px solid {t.border_strong};
            border-radius: 8px;
            padding: 8px 16px;
            background: {t.btn_bg};
            color: {t.text_primary};
            min-height: 36px;
            font-size: 14px;
        }}
        QPushButton[compact="true"] {{
            min-height: 32px;
            padding: 6px 10px;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background: {t.btn_hover};
            border-color: {t.scroll_handle_hover};
        }}
        QPushButton:pressed {{
            background: {t.btn_pressed};
        }}
        QPushButton:disabled {{
            color: {t.btn_disabled_text};
            background: {t.btn_disabled_bg};
        }}
        QPushButton[primary="true"] {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {t.primary_top}, stop:1 {t.primary_bottom});
            color: {t.primary_text};
            border: 1px solid {t.primary_border};
            font-weight: 600;
        }}
        QPushButton[primary="true"]:hover {{
            background: {t.primary_hover};
        }}
        QPushButton[secondary="true"] {{
            background: {t.secondary_bg};
            border-color: {t.border_strong};
            color: {t.card_title};
        }}
        QPushButton[ghost="true"] {{
            background: transparent;
            border: 1px solid transparent;
            color: {t.text_caption};
            text-align: left;
            padding-left: 8px;
        }}
        QPushButton[ghost="true"]:hover {{
            background: {t.btn_hover};
            border-color: {t.border};
        }}
        QPushButton[tool="true"] {{
            background: {t.tool_bg};
            border-color: {t.tool_border};
            color: {t.tool_text};
        }}
        QPushButton[tool="true"]:hover {{
            background: {t.tool_hover};
        }}

        QListWidget {{
            border: 1px solid {t.border};
            border-radius: 8px;
            background: {t.list_bg};
            padding: 4px;
            outline: none;
        }}
        QListWidget::item {{
            padding: 10px 12px;
            border-radius: 6px;
            margin: 3px 0;
            min-height: 48px;
            font-size: 13px;
        }}
        QListWidget::item:selected {{
            background: {t.list_selected_bg};
            color: {t.list_selected_text};
            border: 1px solid {t.list_selected_border};
        }}
        QListWidget::item:hover:!selected {{
            background: {t.list_hover};
        }}

        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {{
            border: 1px solid {t.border_strong};
            border-radius: 8px;
            padding: 5px 10px;
            background: {t.input_bg};
            min-height: 32px;
            selection-background-color: {t.selection_bg};
            font-size: 14px;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QRadioButton {{
            spacing: 8px;
            padding: 4px 0;
        }}
        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
        }}

        QWidget#workspace {{
            background-color: {t.bg_main};
        }}
        QFrame#previewCard {{
            background: {t.card_bg};
            border: 1px solid {t.border};
            border-radius: 12px;
        }}
        QLabel#previewTitle {{
            font-size: 16px;
            font-weight: 600;
            color: {t.card_title};
            padding: 2px 0 6px 0;
        }}

        QFrame#sessionBar {{
            background: {t.session_bar_bg};
            border: 1px solid {t.session_bar_border};
            border-radius: 10px;
        }}
        QFrame#sessionBar QLabel#sessionSummary {{
            color: {t.session_summary};
            font-size: 13px;
        }}

        QTabWidget::pane {{
            border: none;
            background: transparent;
            top: -1px;
        }}
        QTabBar::tab {{
            background: {t.tab_bg};
            color: {t.tab_text};
            padding: 10px 22px;
            font-size: 14px;
            min-height: 20px;
            margin-right: 4px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            border: 1px solid {t.border};
            border-bottom: none;
        }}
        QTabBar::tab:selected {{
            background: {t.tab_selected_bg};
            color: {t.tab_selected_text};
            font-weight: 600;
            border-bottom: 2px solid {t.tab_accent};
        }}
        QTabBar::tab:hover:!selected {{
            background: {t.tab_hover_bg};
            color: {t.tab_hover_text};
        }}

        QTableView {{
            border: none;
            gridline-color: {t.table_grid};
            background: {t.card_bg};
            alternate-background-color: {t.table_alt};
            selection-background-color: {t.selection_bg};
            selection-color: {t.selection_text};
        }}
        QHeaderView::section {{
            background: {t.table_header_bg};
            color: {t.text_caption};
            padding: 10px 8px;
            font-size: 13px;
            min-height: 32px;
            border: none;
            border-bottom: 2px solid {t.border};
            font-weight: 600;
        }}

        QTextEdit#logPanel {{
            border: 1px solid {t.border};
            border-radius: 10px;
            background: {t.card_bg};
            color: {t.text_caption};
            font-family: "Consolas", "Microsoft JhengHei UI", monospace;
            font-size: 12px;
        }}

        QStatusBar {{
            background: {t.statusbar_bg};
            border-top: 1px solid {t.border};
            color: {t.status_muted};
        }}
        QMenuBar {{
            background: {t.menubar_bg};
            border-bottom: 1px solid {t.border};
            padding: 2px 0;
        }}
        QMenuBar::item:selected {{
            background: {t.btn_hover};
            border-radius: 4px;
        }}

        QLabel[role="hint"] {{
            color: {t.text_muted};
            font-size: 11px;
            line-height: 1.4;
        }}
        QLabel[role="caption"] {{
            color: {t.text_caption};
            font-size: 12px;
            padding: 2px 0 6px 0;
        }}
        QLabel[role="workflow-step-active"] {{
            background: {t.workflow_active_bg};
            color: {t.workflow_active_text};
            border-radius: 14px;
            padding: 8px 16px;
            font-weight: 600;
            font-size: 13px;
        }}
        QLabel[role="workflow-step"] {{
            background: {t.workflow_step_bg};
            color: {t.workflow_step_text};
            border: 1px solid {t.workflow_step_border};
            border-radius: 14px;
            padding: 8px 16px;
            font-size: 13px;
        }}
        QLabel[role="workflow-step-done"] {{
            background: {t.workflow_done_bg};
            color: {t.workflow_done_text};
            border: 1px solid {t.workflow_done_border};
            border-radius: 14px;
            padding: 8px 16px;
            font-size: 13px;
        }}
        QLabel#workflowTitle {{
            font-weight: 600;
            color: {t.workflow_title};
            font-size: 12px;
        }}
        QLabel#workflowArrow {{
            color: {t.workflow_arrow};
            font-size: 14px;
        }}
        QPushButton#zoomBtn {{
            min-width: 36px;
            max-width: 36px;
            min-height: 32px;
            max-height: 32px;
            padding: 4px;
            font-weight: 700;
        }}
        QLabel[role="stat-chip"] {{
            background: {t.chip_bg};
            color: {t.chip_text};
            border: 1px solid {t.chip_border};
            border-radius: 8px;
            padding: 5px 12px;
            font-size: 11px;
        }}
        QLabel#zoomUiLabel {{
            color: {t.status_muted};
            font-size: 12px;
        }}
        QLabel#zoomPercent {{
            font-weight: 600;
            color: {t.zoom_label};
        }}

        QScrollArea {{
            border: none;
            background: transparent;
        }}
        QScrollArea#sidebarScroll QScrollBar:vertical {{
            background: {t.scroll_bg};
            width: 12px;
            border-radius: 6px;
            margin: 4px 2px;
        }}
        QScrollArea#sidebarScroll QScrollBar::handle:vertical {{
            background: {t.scroll_handle};
            border-radius: 6px;
            min-height: 32px;
        }}
        QScrollArea#sidebarScroll QScrollBar::handle:vertical:hover {{
            background: {t.scroll_handle_hover};
        }}
        QScrollBar:vertical {{
            background: {t.scroll_bg};
            width: 10px;
            border-radius: 5px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: {t.scroll_handle};
            border-radius: 5px;
            min-height: 24px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {t.scroll_handle_hover};
        }}
        QSplitter::handle {{
            background: {t.splitter};
        }}
        QSplitter::handle:hover {{
            background: {t.splitter_hover};
        }}

        QWidget#sidebarContent QGroupBox {{
            border: none;
            background: transparent;
            margin-top: 4px;
            padding: 0;
        }}
        QWidget#sidebarContent QGroupBox::title {{
            color: {t.sidebar_section};
            font-size: 11px;
            font-weight: 600;
        }}
        QWidget#sidebar QPushButton[ghost="true"] {{
            color: {t.text_caption};
        }}
        QWidget#sidebar QPushButton[ghost="true"]:hover {{
            background: {t.btn_hover};
            border-color: {t.border};
        }}
        """


def apply_app_style(app: QApplication, theme_id: str | None = None) -> ColorTheme:
    theme = get_theme(theme_id or load_theme_id())
    app.setStyleSheet(build_stylesheet(theme))
    return theme


def apply_theme(app: QApplication, theme_id: str) -> ColorTheme:
    theme = get_theme(theme_id)
    save_theme_id(theme.id)
    app.setStyleSheet(build_stylesheet(theme))
    return theme
