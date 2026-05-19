"""Small UI helpers."""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QPushButton, QVBoxLayout, QWidget

from app.ui.styles import current_theme
from app.ui.ui_metrics import (
    BTN_HEIGHT,
    BTN_HEIGHT_COMPACT,
    BTN_HEIGHT_PRIMARY,
    CARD_PADDING,
    CARD_SPACING,
)


def set_tooltip(widget: QWidget, text: str) -> None:
    widget.setToolTip(text)
    widget.setStatusTip(text)


def mark_primary(button: QPushButton) -> None:
    button.setProperty("primary", True)
    _repolish(button)


def mark_secondary(button: QPushButton) -> None:
    button.setProperty("secondary", True)
    _repolish(button)


def mark_tool(button: QPushButton) -> None:
    button.setProperty("tool", True)
    button.setProperty("compact", True)
    _repolish(button)


def mark_compact(button: QPushButton) -> None:
    button.setProperty("compact", True)
    _repolish(button)


def mark_ghost(button: QPushButton) -> None:
    button.setProperty("ghost", True)
    _repolish(button)


def _repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def card_frame(title: str | None = None) -> tuple[QFrame, QVBoxLayout]:
    """White rounded card; optional title (omit when section label is outside)."""
    from PySide6.QtWidgets import QLabel

    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    pad = CARD_PADDING
    layout.setContentsMargins(pad, pad - 2, pad, pad)
    layout.setSpacing(CARD_SPACING)
    if title:
        heading = QLabel(title)
        heading.setObjectName("cardTitle")
        layout.addWidget(heading)
    return frame, layout


def sized_button(
    text: str,
    *,
    height: int = BTN_HEIGHT,
    min_width: int = 0,
) -> QPushButton:
    btn = QPushButton(text)
    btn.setMinimumHeight(height)
    if min_width > 0:
        btn.setMinimumWidth(min_width)
    return btn


def hint_label(text: str) -> QWidget:
    from PySide6.QtWidgets import QLabel

    label = QLabel(text)
    label.setProperty("role", "hint")
    label.setWordWrap(True)
    return label


def themed_help_css() -> str:
    """CSS for help/readme browsers to keep theme colors consistent."""
    t = current_theme()
    return f"""
        body {{
            color: {t.text_primary};
            background: {t.card_bg};
            font-family: "Microsoft JhengHei UI", "Segoe UI", sans-serif;
            line-height: 1.55;
        }}
        h1, h2, h3, h4, h5 {{
            color: {t.card_title};
        }}
        p, li, td, th, span, div {{
            color: {t.text_primary};
        }}
        a {{
            color: {t.tab_accent};
        }}
        table, th, td {{
            border-color: {t.border};
        }}
        code {{
            color: {t.text_primary};
            background: {t.secondary_bg};
            border: 1px solid {t.border};
            border-radius: 4px;
            padding: 1px 4px;
        }}
    """


def wrap_help_html(html: str) -> str:
    return f"<style>{themed_help_css()}</style>{html}"
