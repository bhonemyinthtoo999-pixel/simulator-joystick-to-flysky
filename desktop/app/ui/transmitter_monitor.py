from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


_DEFAULT_THEME = {
    "primary": "#4f46e5",
    "primary_light": "#818cf8",
    "primary_dark": "#312e81",
    "secondary": "#06b6d4",
    "accent": "#a855f7",
    "success": "#10b981",
}


def _theme_palette() -> dict[str, str]:
    app = QApplication.instance()
    payload = app.property("simjoyThemePalette") if app is not None else None
    colors = dict(_DEFAULT_THEME)
    if isinstance(payload, dict):
        colors.update({str(key): str(value) for key, value in payload.items()})
    return colors


def _with_alpha(color: str | QColor, alpha: int) -> QColor:
    result = QColor(color) if not isinstance(color, QColor) else QColor(color)
    result.setAlpha(max(0, min(255, alpha)))
    return result


class TransmitterCanvas(QWidget):
    """Read-only Mode 2 radio animation driven by final AETR output pulses."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(350)
        self._channels = [1500, 1500, 1000, 1500]
        self._link_state = "offline"

    def set_channels(self, channels: list[int]) -> None:
        values = [1500, 1500, 1000, 1500]
        for index, value in enumerate(channels[:4]):
            values[index] = max(800, min(2200, int(value)))
        if values != self._channels:
            self._channels = values
            self.update()

    def set_link_state(self, state: str) -> None:
        clean = state if state in {"live", "failsafe", "simulator", "offline", "paused"} else "offline"
        if clean != self._link_state:
            self._link_state = clean
            self.update()

    @staticmethod
    def _centered(value: int) -> float:
        return max(-1.0, min(1.0, (float(value) - 1500.0) / 500.0))

    @staticmethod
    def _unipolar(value: int) -> float:
        return max(-1.0, min(1.0, ((float(value) - 1000.0) / 500.0) - 1.0))

    def _state_accent(self, colors: dict[str, str]) -> QColor:
        if self._link_state == "live":
            return QColor(colors.get("success", "#10b981"))
        if self._link_state == "failsafe":
            return QColor("#f59e0b")
        if self._link_state == "paused":
            return QColor("#f97316")
        if self._link_state == "simulator":
            return QColor(colors["secondary"])
        return QColor("#94a3b8")

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        colors = _theme_palette()
        palette = self.palette()
        dark = palette.color(QPalette.ColorRole.Window).lightness() < 128
        text = QColor("#f8fafc" if dark else "#172033")
        muted = QColor("#94a3b8" if dark else "#64748b")
        surface = QColor("#111827" if dark else "#f8fafc")
        surface_alt = QColor("#1f2937" if dark else "#e2e8f0")
        accent = self._state_accent(colors)

        bounds = QRectF(self.rect()).adjusted(10.0, 10.0, -10.0, -10.0)
        body = QRectF(
            bounds.left() + bounds.width() * 0.035,
            bounds.top() + 22.0,
            bounds.width() * 0.93,
            bounds.height() - 38.0,
        )

        shadow = body.translated(0.0, 8.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_with_alpha("#020617", 70 if dark else 45))
        painter.drawRoundedRect(shadow, 34.0, 34.0)

        body_gradient = QLinearGradient(body.topLeft(), body.bottomRight())
        if dark:
            body_gradient.setColorAt(0.0, QColor("#25324a"))
            body_gradient.setColorAt(0.48, QColor("#111827"))
            body_gradient.setColorAt(1.0, QColor(colors["primary_dark"]))
        else:
            body_gradient.setColorAt(0.0, QColor("#ffffff"))
            body_gradient.setColorAt(0.52, QColor("#edf2f7"))
            body_gradient.setColorAt(1.0, _with_alpha(colors["primary_light"], 95))
        painter.setBrush(body_gradient)
        painter.setPen(QPen(_with_alpha(colors["primary"], 155), 1.6))
        painter.drawRoundedRect(body, 34.0, 34.0)

        grip_height = body.height() * 0.46
        grip_width = body.width() * 0.18
        left_grip = QRectF(
            body.left() + body.width() * 0.025,
            body.bottom() - grip_height - 10.0,
            grip_width,
            grip_height,
        )
        right_grip = QRectF(
            body.right() - grip_width - body.width() * 0.025,
            body.bottom() - grip_height - 10.0,
            grip_width,
            grip_height,
        )
        grip_color = _with_alpha(colors["primary_dark"], 145 if dark else 72)
        painter.setPen(QPen(_with_alpha(colors["primary"], 105), 1.0))
        painter.setBrush(grip_color)
        painter.drawRoundedRect(left_grip, 28.0, 28.0)
        painter.drawRoundedRect(right_grip, 28.0, 28.0)

        antenna_x = body.center().x()
        painter.setPen(QPen(_with_alpha(colors["primary_dark"], 190), 8.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(antenna_x, body.top() + 4.0), QPointF(antenna_x, body.top() - 20.0))
        painter.setPen(QPen(_with_alpha(colors["primary_light"], 220), 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(antenna_x, body.top() - 20.0), QPointF(antenna_x, body.top() - 27.0))

        self._draw_shoulder_switch(
            painter,
            QRectF(body.left() + body.width() * 0.12, body.top() + 13.0, 50.0, 18.0),
            colors,
            dark,
        )
        self._draw_shoulder_switch(
            painter,
            QRectF(body.right() - body.width() * 0.12 - 50.0, body.top() + 13.0, 50.0, 18.0),
            colors,
            dark,
        )

        screen_width = min(205.0, body.width() * 0.25)
        screen_height = min(88.0, max(62.0, body.height() * 0.27))
        screen = QRectF(
            body.center().x() - screen_width / 2.0,
            body.top() + 28.0,
            screen_width,
            screen_height,
        )
        screen_gradient = QLinearGradient(screen.topLeft(), screen.bottomRight())
        screen_gradient.setColorAt(0.0, QColor("#07111f"))
        screen_gradient.setColorAt(1.0, QColor("#13233a"))
        painter.setBrush(screen_gradient)
        painter.setPen(QPen(_with_alpha(colors["primary_light"], 190), 1.4))
        painter.drawRoundedRect(screen, 12.0, 12.0)

        dot = QPointF(screen.left() + 18.0, screen.top() + 18.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent)
        painter.drawEllipse(dot, 5.0, 5.0)
        painter.setPen(QPen(_with_alpha(accent, 80), 4.0))
        painter.drawEllipse(dot, 8.0, 8.0)

        painter.setFont(QFont(painter.font().family(), 10, QFont.Weight.Bold))
        painter.setPen(QColor("#e2e8f0"))
        painter.drawText(
            screen.adjusted(12.0, 8.0, -12.0, -screen.height() * 0.52),
            Qt.AlignmentFlag.AlignCenter,
            "AETR OUTPUT",
        )
        painter.setFont(QFont(painter.font().family(), 11, QFont.Weight.Black))
        painter.setPen(accent)
        painter.drawText(
            screen.adjusted(12.0, screen.height() * 0.42, -12.0, -8.0),
            Qt.AlignmentFlag.AlignCenter,
            self._link_state.upper(),
        )

        left_center = QPointF(body.left() + body.width() * 0.29, body.top() + body.height() * 0.60)
        right_center = QPointF(body.left() + body.width() * 0.71, body.top() + body.height() * 0.60)
        radius = min(body.width() * 0.125, body.height() * 0.205)
        radius = max(38.0, radius)

        yaw = self._centered(self._channels[3])
        throttle = self._unipolar(self._channels[2])
        roll = self._centered(self._channels[0])
        pitch = self._centered(self._channels[1])

        self._draw_gimbal(
            painter,
            left_center,
            radius,
            yaw,
            throttle,
            "THROTTLE / YAW",
            f"CH3  {self._channels[2]}     CH4  {self._channels[3]}",
            colors,
            surface,
            surface_alt,
            text,
            muted,
            accent,
        )
        self._draw_gimbal(
            painter,
            right_center,
            radius,
            roll,
            pitch,
            "PITCH / ROLL",
            f"CH2  {self._channels[1]}     CH1  {self._channels[0]}",
            colors,
            surface,
            surface_alt,
            text,
            muted,
            accent,
        )

        self._draw_trim_controls(painter, left_center, radius, colors, dark)
        self._draw_trim_controls(painter, right_center, radius, colors, dark)

        footer = QRectF(body.left() + body.width() * 0.22, body.bottom() - 27.0, body.width() * 0.56, 20.0)
        painter.setFont(QFont(painter.font().family(), 8))
        painter.setPen(muted)
        painter.drawText(
            footer,
            Qt.AlignmentFlag.AlignCenter,
            "MODE 2  •  FINAL CALIBRATED AETR OUTPUT  •  READ ONLY",
        )

    @staticmethod
    def _draw_shoulder_switch(
        painter: QPainter,
        rect: QRectF,
        colors: dict[str, str],
        dark: bool,
    ) -> None:
        painter.setPen(QPen(_with_alpha(colors["primary_light"], 150), 1.0))
        painter.setBrush(QColor("#0f172a" if dark else "#cbd5e1"))
        painter.drawRoundedRect(rect, 8.0, 8.0)
        lever = QRectF(rect.center().x() - 5.0, rect.top() - 7.0, 10.0, 17.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(colors["secondary"]))
        painter.drawRoundedRect(lever, 4.0, 4.0)

    @staticmethod
    def _draw_trim_controls(
        painter: QPainter,
        center: QPointF,
        radius: float,
        colors: dict[str, str],
        dark: bool,
    ) -> None:
        fill = QColor("#273449" if dark else "#dbe4ef")
        pen = QPen(_with_alpha(colors["primary"], 115), 1.0)
        painter.setPen(pen)
        painter.setBrush(fill)
        horizontal = QRectF(center.x() - 23.0, center.y() + radius + 11.0, 46.0, 9.0)
        vertical = QRectF(center.x() + radius + 11.0, center.y() - 23.0, 9.0, 46.0)
        painter.drawRoundedRect(horizontal, 4.0, 4.0)
        painter.drawRoundedRect(vertical, 4.0, 4.0)

    @staticmethod
    def _draw_gimbal(
        painter: QPainter,
        center: QPointF,
        radius: float,
        x_value: float,
        y_value: float,
        title: str,
        values: str,
        colors: dict[str, str],
        surface: QColor,
        surface_alt: QColor,
        text: QColor,
        muted: QColor,
        accent: QColor,
    ) -> None:
        outer = QRectF(center.x() - radius, center.y() - radius, radius * 2.0, radius * 2.0)
        halo = QRectF(outer).adjusted(-6.0, -6.0, 6.0, 6.0)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_with_alpha(colors["primary"], 45))
        painter.drawEllipse(halo)

        ring = QRadialGradient(center, radius)
        ring.setColorAt(0.0, surface)
        ring.setColorAt(0.72, surface_alt)
        ring.setColorAt(1.0, QColor(colors["primary_dark"]))
        painter.setBrush(ring)
        painter.setPen(QPen(_with_alpha(colors["primary_light"], 180), 1.5))
        painter.drawEllipse(outer)

        inner = outer.adjusted(radius * 0.17, radius * 0.17, -radius * 0.17, -radius * 0.17)
        painter.setBrush(surface)
        painter.setPen(QPen(_with_alpha(colors["primary"], 90), 1.0))
        painter.drawEllipse(inner)

        painter.setPen(QPen(_with_alpha(muted, 135), 1.0, Qt.PenStyle.DashLine))
        painter.drawLine(
            QPointF(center.x() - radius * 0.70, center.y()),
            QPointF(center.x() + radius * 0.70, center.y()),
        )
        painter.drawLine(
            QPointF(center.x(), center.y() - radius * 0.70),
            QPointF(center.x(), center.y() + radius * 0.70),
        )

        travel = radius * 0.57
        knob = QPointF(center.x() + x_value * travel, center.y() - y_value * travel)
        painter.setPen(QPen(_with_alpha("#020617", 90), 7.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(center + QPointF(2.0, 3.0), knob + QPointF(2.0, 3.0))
        painter.setPen(QPen(accent, 4.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(center, knob)

        knob_gradient = QRadialGradient(knob - QPointF(radius * 0.04, radius * 0.04), radius * 0.18)
        knob_gradient.setColorAt(0.0, QColor(colors["primary_light"]))
        knob_gradient.setColorAt(0.55, accent)
        knob_gradient.setColorAt(1.0, QColor(colors["primary_dark"]))
        painter.setBrush(knob_gradient)
        painter.setPen(QPen(_with_alpha("#ffffff", 170), 1.3))
        painter.drawEllipse(knob, radius * 0.16, radius * 0.16)

        title_rect = QRectF(center.x() - radius * 1.35, center.y() + radius + 22.0, radius * 2.7, 20.0)
        value_rect = QRectF(center.x() - radius * 1.5, center.y() + radius + 43.0, radius * 3.0, 24.0)
        painter.setFont(QFont(painter.font().family(), 9, QFont.Weight.Bold))
        painter.setPen(text)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, title)

        pill = QPainterPath()
        pill.addRoundedRect(value_rect.adjusted(7.0, 1.0, -7.0, -1.0), 9.0, 9.0)
        painter.setPen(QPen(_with_alpha(colors["primary"], 80), 1.0))
        painter.setBrush(_with_alpha(surface, 215))
        painter.drawPath(pill)
        painter.setFont(QFont(painter.font().family(), 8, QFont.Weight.DemiBold))
        painter.setPen(muted)
        painter.drawText(value_rect, Qt.AlignmentFlag.AlignCenter, values)


class LiveTransmitterMonitor(QFrame):
    """Dashboard view of final output that never changes physical adapter routing."""

    def __init__(self) -> None:
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setProperty("uiCard", True)
        self.setObjectName("liveTransmitterMonitor")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(11)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Live transmitter monitor")
        title.setStyleSheet("font-size: 21px; font-weight: 800;")
        note = QLabel(
            "Read-only view of the final AETR values. Opening this monitor never disconnects Arduino or interrupts FlySky trainer PPM."
        )
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 11px; color: palette(mid);")
        title_box.addWidget(title)
        title_box.addWidget(note)

        self.link_badge = QLabel("OFFLINE")
        self.link_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.link_badge.setMinimumWidth(150)
        self.link_badge.setMinimumHeight(42)
        header.addLayout(title_box, 1)
        header.addWidget(self.link_badge)

        self.link_detail = QLabel(
            "Connect and identify a physical adapter to view the live trainer output path."
        )
        self.link_detail.setWordWrap(True)
        self.link_detail.setStyleSheet(
            "font-size: 12px; padding: 9px 12px; border: 1px solid palette(midlight); "
            "border-radius: 9px; background: palette(alternate-base);"
        )
        self.canvas = TransmitterCanvas()

        layout.addLayout(header)
        layout.addWidget(self.link_detail)
        layout.addWidget(self.canvas)

    def update_live(
        self,
        channels: list[int],
        *,
        adapter_kind: str,
        connection: str,
        streaming: bool,
        failsafe: bool,
    ) -> None:
        self.canvas.set_channels(channels)
        physical = adapter_kind in {"arduino_uno", "arduino_mega", "arduino", "esp32"}
        colors = _theme_palette()

        if failsafe:
            state = "failsafe"
            label = "FAILSAFE"
            detail = "Strict AETR failsafe is active. The animation shows the safe output values currently being sent."
            foreground = "#92400e"
            background = "#fef3c7"
            border = "#f59e0b"
        elif physical and streaming:
            state = "live"
            label = "LIVE HARDWARE"
            detail = (
                f"Streaming final AETR output to {connection or adapter_kind}. "
                "Trainer output remains active while this page is open."
            )
            foreground = "#065f46"
            background = "#d1fae5"
            border = colors.get("success", "#10b981")
        elif adapter_kind == "simulator":
            state = "simulator"
            label = "OFFLINE SIMULATOR"
            detail = "Software-only adapter simulation. No physical trainer-port signal is produced."
            foreground = colors["primary_dark"]
            background = colors.get("soft", "#eef2ff")
            border = colors["secondary"]
        elif physical:
            state = "paused"
            label = "OUTPUT PAUSED"
            detail = (
                f"Physical adapter detected at {connection or adapter_kind}, "
                "but live channel streaming is temporarily paused."
            )
            foreground = "#9a3412"
            background = "#ffedd5"
            border = "#f97316"
        else:
            state = "offline"
            label = "OFFLINE"
            detail = (
                "Connect and identify Arduino UNO/Nano, Mega 2560 or ESP32-S3 "
                "to monitor the physical output path."
            )
            foreground = "#475569"
            background = "#e2e8f0"
            border = "#94a3b8"

        self.canvas.set_link_state(state)
        self.link_badge.setText(label)
        self.link_badge.setStyleSheet(
            "font-weight: 850; padding: 9px 14px; border-radius: 12px; "
            f"color: {foreground}; background: {background}; border: 2px solid {border};"
        )
        self.link_detail.setText(detail)
