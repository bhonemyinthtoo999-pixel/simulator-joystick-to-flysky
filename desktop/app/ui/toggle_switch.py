from __future__ import annotations

from PySide6.QtCore import QLineF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPalette, QPen
from PySide6.QtWidgets import QAbstractButton, QSizePolicy


class ToggleSwitch(QAbstractButton):
    """Keyboard-accessible painted toggle that remains clear in light and dark UI."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedSize(54, 30)

    def sizeHint(self) -> QSize:
        return QSize(54, 30)

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        palette = self.palette()
        enabled = self.isEnabled()
        checked = self.isChecked()
        focused = self.hasFocus()

        track = QRectF(1.5, 3.0, self.width() - 3.0, self.height() - 6.0)
        radius = track.height() / 2.0

        if not enabled:
            track_color = palette.color(QPalette.ColorRole.Midlight)
            knob_color = palette.color(QPalette.ColorRole.Mid)
        elif checked:
            track_color = QColor("#4f46e5")
            knob_color = QColor("#ffffff")
        else:
            track_color = palette.color(QPalette.ColorRole.Mid)
            knob_color = palette.color(QPalette.ColorRole.Base)

        if focused and enabled:
            painter.setPen(QPen(QColor("#38bdf8"), 1.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(
                track.adjusted(-1.0, -1.0, 1.0, 1.0),
                radius + 1.0,
                radius + 1.0,
            )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(track, radius, radius)

        knob_diameter = track.height() - 6.0
        knob_y = track.top() + 3.0
        knob_x = (
            track.right() - knob_diameter - 3.0
            if checked
            else track.left() + 3.0
        )
        knob = QRectF(knob_x, knob_y, knob_diameter, knob_diameter)
        painter.setBrush(knob_color)
        painter.drawEllipse(knob)

        if checked and enabled:
            painter.setPen(QPen(QColor("#4f46e5"), 1.7))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            center = knob.center()
            painter.drawLine(
                QLineF(
                    center.x() - 4.0,
                    center.y(),
                    center.x() - 1.0,
                    center.y() + 3.0,
                )
            )
            painter.drawLine(
                QLineF(
                    center.x() - 1.0,
                    center.y() + 3.0,
                    center.x() + 5.0,
                    center.y() - 4.0,
                )
            )
