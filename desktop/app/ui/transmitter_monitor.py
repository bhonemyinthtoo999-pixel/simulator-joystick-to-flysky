from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class TransmitterCanvas(QWidget):
    """Read-only Mode 2 transmitter animation driven by final AETR pulses."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(330)
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

    def _accent(self) -> QColor:
        if self._link_state == "live":
            return QColor("#2e9b63")
        if self._link_state == "failsafe":
            return QColor("#d97706")
        if self._link_state == "simulator":
            return QColor("#4f7fc7")
        if self._link_state == "paused":
            return QColor("#a66b10")
        return QColor("#7b8794")

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        palette = self.palette()
        background = palette.color(palette.ColorRole.Base)
        panel = palette.color(palette.ColorRole.AlternateBase)
        text = palette.color(palette.ColorRole.Text)
        muted = palette.color(palette.ColorRole.Mid)
        accent = self._accent()

        bounds = QRectF(self.rect()).adjusted(10.0, 8.0, -10.0, -8.0)
        body = QRectF(bounds.left() + bounds.width() * 0.08, bounds.top() + 20.0, bounds.width() * 0.84, bounds.height() - 36.0)

        painter.setPen(QPen(muted, 1.2))
        painter.setBrush(panel)
        painter.drawRoundedRect(body, 30.0, 30.0)

        shoulder = QRectF(body.left() + body.width() * 0.08, body.top() - 13.0, body.width() * 0.84, 46.0)
        painter.setBrush(background)
        painter.drawRoundedRect(shoulder, 20.0, 20.0)

        screen = QRectF(body.center().x() - 80.0, body.top() + 42.0, 160.0, 82.0)
        painter.setPen(QPen(muted, 1.0))
        painter.setBrush(background)
        painter.drawRoundedRect(screen, 10.0, 10.0)
        painter.setPen(text)
        painter.drawText(screen.adjusted(8.0, 8.0, -8.0, -46.0), Qt.AlignmentFlag.AlignCenter, "AETR LIVE")
        painter.setPen(accent)
        painter.drawText(screen.adjusted(8.0, 38.0, -8.0, -8.0), Qt.AlignmentFlag.AlignCenter, self._link_state.upper())

        left_center = QPointF(body.left() + body.width() * 0.27, body.top() + body.height() * 0.60)
        right_center = QPointF(body.left() + body.width() * 0.73, body.top() + body.height() * 0.60)
        radius = min(body.width(), body.height()) * 0.165

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
            f"CH3 {self._channels[2]}   CH4 {self._channels[3]}",
            panel,
            background,
            muted,
            text,
            accent,
        )
        self._draw_gimbal(
            painter,
            right_center,
            radius,
            roll,
            pitch,
            "PITCH / ROLL",
            f"CH2 {self._channels[1]}   CH1 {self._channels[0]}",
            panel,
            background,
            muted,
            text,
            accent,
        )

        painter.setPen(muted)
        footer = QRectF(body.left() + 22.0, body.bottom() - 28.0, body.width() - 44.0, 20.0)
        painter.drawText(footer, Qt.AlignmentFlag.AlignCenter, "Mode 2 visualization • final output sent to the active adapter")

    @staticmethod
    def _draw_gimbal(
        painter: QPainter,
        center: QPointF,
        radius: float,
        x_value: float,
        y_value: float,
        title: str,
        values: str,
        panel: QColor,
        background: QColor,
        muted: QColor,
        text: QColor,
        accent: QColor,
    ) -> None:
        outer = QRectF(center.x() - radius, center.y() - radius, radius * 2.0, radius * 2.0)
        painter.setPen(QPen(muted, 1.2))
        painter.setBrush(background)
        painter.drawEllipse(outer)

        painter.setPen(QPen(muted, 1.0, Qt.PenStyle.DashLine))
        painter.drawLine(QPointF(center.x() - radius * 0.82, center.y()), QPointF(center.x() + radius * 0.82, center.y()))
        painter.drawLine(QPointF(center.x(), center.y() - radius * 0.82), QPointF(center.x(), center.y() + radius * 0.82))

        travel = radius * 0.68
        knob = QPointF(center.x() + x_value * travel, center.y() - y_value * travel)
        painter.setPen(QPen(accent, 3.0))
        painter.drawLine(center, knob)
        painter.setBrush(accent)
        painter.drawEllipse(knob, radius * 0.14, radius * 0.14)
        painter.setBrush(panel)
        painter.setPen(QPen(background, 2.0))
        painter.drawEllipse(knob, radius * 0.055, radius * 0.055)

        title_rect = QRectF(center.x() - radius * 1.25, center.y() + radius + 10.0, radius * 2.5, 22.0)
        value_rect = QRectF(center.x() - radius * 1.35, center.y() + radius + 32.0, radius * 2.7, 20.0)
        painter.setPen(text)
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, title)
        painter.setPen(muted)
        painter.drawText(value_rect, Qt.AlignmentFlag.AlignCenter, values)


class LiveTransmitterMonitor(QFrame):
    """Dashboard section that observes live output without changing adapter routing."""

    def __init__(self) -> None:
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("liveTransmitterMonitor")
        self.setStyleSheet(
            "QFrame#liveTransmitterMonitor { border: 1px solid palette(midlight); border-radius: 14px; background: palette(base); }"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Live transmitter monitor")
        title.setStyleSheet("font-size: 19px; font-weight: 700;")
        note = QLabel(
            "Read-only view of the final AETR values. Opening this monitor never disconnects Arduino or interrupts FlySky trainer PPM."
        )
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 11px; color: palette(mid);")
        title_box.addWidget(title)
        title_box.addWidget(note)

        self.link_badge = QLabel("OFFLINE")
        self.link_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.link_badge.setMinimumWidth(135)
        self.link_badge.setStyleSheet("font-weight: 800; padding: 8px 12px; border: 1px solid palette(midlight); border-radius: 10px;")
        header.addLayout(title_box, 1)
        header.addWidget(self.link_badge)

        self.link_detail = QLabel("Connect and identify a physical adapter to view the live trainer output path.")
        self.link_detail.setWordWrap(True)
        self.link_detail.setStyleSheet("font-size: 12px;")
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

        if failsafe:
            state = "failsafe"
            label = "FAILSAFE"
            detail = "Strict AETR failsafe is active. The animation shows the safe output values currently being sent."
            color = "#d97706"
        elif physical and streaming:
            state = "live"
            label = "LIVE HARDWARE"
            detail = f"Streaming final AETR output to {connection or adapter_kind}. Trainer output remains active while this page is open."
            color = "#238453"
        elif adapter_kind == "simulator":
            state = "simulator"
            label = "OFFLINE SIMULATOR"
            detail = "Software-only adapter simulation. No physical trainer-port signal is produced."
            color = "#4f7fc7"
        elif physical:
            state = "paused"
            label = "OUTPUT PAUSED"
            detail = f"Physical adapter detected at {connection or adapter_kind}, but live channel streaming is temporarily paused."
            color = "#a66b10"
        else:
            state = "offline"
            label = "OFFLINE"
            detail = "Connect and identify Arduino UNO/Nano, Mega 2560 or ESP32-S3 to monitor the physical output path."
            color = "palette(mid)"

        self.canvas.set_link_state(state)
        self.link_badge.setText(label)
        self.link_badge.setStyleSheet(
            f"font-weight: 800; padding: 8px 12px; border: 1px solid palette(midlight); border-radius: 10px; color: {color};"
        )
        self.link_detail.setText(detail)
