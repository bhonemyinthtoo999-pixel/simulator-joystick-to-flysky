from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QLabel


def clear_layout(layout: Any) -> None:
    while layout.count():
        item = layout.takeAt(0)
        child_layout = item.layout()
        widget = item.widget()
        if child_layout is not None:
            clear_layout(child_layout)
        if widget is not None:
            widget.deleteLater()


def page_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet("font-size: 24px; font-weight: 700;")
    return label
