from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QGroupBox,
    QPushButton,
    QWidget,
)


LIGHT_QSS = r"""
QMainWindow, QDialog {
    background: #eef3fb;
    color: #172033;
}
QWidget#productAppRoot {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #edf4ff, stop:0.48 #f7f8ff, stop:1 #fff4fb);
}
QFrame#productNavigationPanel {
    border: 0;
    border-right: 1px solid #4f46e5;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #172554, stop:0.52 #312e81, stop:1 #581c87);
}
QFrame#productNavigationPanel QLabel {
    color: #eef2ff;
}
QFrame#productNavigationPanel QListWidget {
    background: transparent;
    color: #dbeafe;
    border: 0;
    outline: 0;
}
QFrame#productNavigationPanel QListWidget::item {
    border-radius: 10px;
    padding: 9px 10px;
    margin: 2px 0;
}
QFrame#productNavigationPanel QListWidget::item:hover {
    background: rgba(255, 255, 255, 32);
}
QFrame#productNavigationPanel QListWidget::item:selected {
    color: white;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0ea5e9, stop:0.52 #4f46e5, stop:1 #a855f7);
}
QFrame#productNavigationPanel QComboBox {
    color: #172033;
    background: #ffffff;
    border: 1px solid #a5b4fc;
}
QFrame[uiCard="true"], QGroupBox[uiCard="true"] {
    background: rgba(255, 255, 255, 238);
    border: 1px solid #d9e2f1;
    border-radius: 15px;
}
QGroupBox {
    margin-top: 13px;
    padding: 15px 12px 12px 12px;
    font-weight: 700;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 7px;
    color: #4338ca;
    background: #f8faff;
}
QPushButton {
    min-height: 22px;
    padding: 9px 16px;
    border-radius: 10px;
    border: 1px solid #3730a3;
    color: white;
    font-weight: 750;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #6366f1, stop:0.48 #4f46e5, stop:1 #3730a3);
}
QPushButton:hover {
    border-color: #312e81;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #818cf8, stop:0.48 #6366f1, stop:1 #4338ca);
}
QPushButton:pressed {
    padding-top: 11px;
    padding-bottom: 7px;
    border-color: #312e81;
    background: #3730a3;
}
QPushButton[buttonRole="success"] {
    border-color: #047857;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #34d399, stop:0.5 #10b981, stop:1 #047857);
}
QPushButton[buttonRole="success"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #6ee7b7, stop:0.5 #34d399, stop:1 #059669);
}
QPushButton[buttonRole="warning"] {
    border-color: #b45309;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #fbbf24, stop:0.5 #f59e0b, stop:1 #b45309);
}
QPushButton[buttonRole="warning"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #fcd34d, stop:0.5 #fbbf24, stop:1 #d97706);
}
QPushButton[buttonRole="danger"] {
    border-color: #b91c1c;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #fb7185, stop:0.5 #ef4444, stop:1 #b91c1c);
}
QPushButton[buttonRole="danger"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #fda4af, stop:0.5 #fb7185, stop:1 #dc2626);
}
QPushButton[buttonRole="secondary"] {
    color: #3730a3;
    border-color: #a5b4fc;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ffffff, stop:1 #e0e7ff);
}
QPushButton[buttonRole="secondary"]:hover {
    color: #312e81;
    border-color: #818cf8;
    background: #eef2ff;
}
QPushButton[buttonRole="ghost"] {
    color: #475569;
    border-color: #cbd5e1;
    background: rgba(255, 255, 255, 190);
}
QPushButton[buttonRole="ghost"]:hover {
    color: #1e293b;
    border-color: #94a3b8;
    background: #ffffff;
}
QPushButton:disabled {
    color: #94a3b8;
    border-color: #d7deea;
    background: #e9edf4;
}
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QPlainTextEdit {
    min-height: 26px;
    padding: 5px 9px;
    color: #172033;
    background: rgba(255, 255, 255, 245);
    border: 1px solid #c8d3e5;
    border-radius: 9px;
    selection-background-color: #6366f1;
}
QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QPlainTextEdit:hover {
    border-color: #818cf8;
}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QPlainTextEdit:focus {
    border: 2px solid #6366f1;
}
QListWidget {
    background: rgba(255, 255, 255, 220);
    border: 1px solid #d9e2f1;
    border-radius: 11px;
    outline: 0;
}
QListWidget::item {
    padding: 8px 9px;
    margin: 2px;
    border-radius: 8px;
}
QListWidget::item:hover {
    background: #eef2ff;
}
QListWidget::item:selected {
    color: white;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0ea5e9, stop:0.5 #4f46e5, stop:1 #8b5cf6);
}
QProgressBar {
    min-height: 17px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    background: #e8edf5;
    text-align: center;
}
QProgressBar::chunk {
    border-radius: 7px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #06b6d4, stop:0.5 #3b82f6, stop:1 #8b5cf6);
}
QCheckBox {
    spacing: 8px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #94a3b8;
    border-radius: 5px;
    background: white;
}
QCheckBox::indicator:checked {
    border-color: #4f46e5;
    background: #4f46e5;
}
QScrollBar:vertical {
    width: 11px;
    margin: 2px;
    background: transparent;
}
QScrollBar::handle:vertical {
    min-height: 28px;
    border-radius: 5px;
    background: #a5b4fc;
}
QScrollBar::handle:vertical:hover {
    background: #818cf8;
}
QToolTip {
    color: white;
    background: #172554;
    border: 1px solid #6366f1;
    border-radius: 7px;
    padding: 6px;
}
"""


DARK_QSS = r"""
QMainWindow, QDialog {
    background: #0b1020;
    color: #e5e7eb;
}
QWidget#productAppRoot {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0b1226, stop:0.52 #11142b, stop:1 #21102c);
}
QFrame#productNavigationPanel {
    border: 0;
    border-right: 1px solid #6366f1;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #111b42, stop:0.52 #262261, stop:1 #48125d);
}
QFrame#productNavigationPanel QLabel { color: #eef2ff; }
QFrame#productNavigationPanel QListWidget {
    background: transparent;
    color: #dbeafe;
    border: 0;
    outline: 0;
}
QFrame#productNavigationPanel QListWidget::item {
    border-radius: 10px;
    padding: 9px 10px;
    margin: 2px 0;
}
QFrame#productNavigationPanel QListWidget::item:hover { background: rgba(255,255,255,28); }
QFrame#productNavigationPanel QListWidget::item:selected {
    color: white;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0891b2, stop:0.5 #4f46e5, stop:1 #9333ea);
}
QFrame#productNavigationPanel QComboBox {
    color: #e5e7eb;
    background: #172033;
    border: 1px solid #6366f1;
}
QFrame[uiCard="true"], QGroupBox[uiCard="true"] {
    background: rgba(23, 30, 51, 238);
    border: 1px solid #334155;
    border-radius: 15px;
}
QGroupBox {
    margin-top: 13px;
    padding: 15px 12px 12px 12px;
    font-weight: 700;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 7px;
    color: #a5b4fc;
    background: #11182b;
}
QPushButton {
    min-height: 22px;
    padding: 9px 16px;
    border-radius: 10px;
    border: 1px solid #6366f1;
    color: white;
    font-weight: 750;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #6366f1, stop:0.5 #4f46e5, stop:1 #312e81);
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #818cf8, stop:0.5 #6366f1, stop:1 #4338ca);
}
QPushButton:pressed {
    padding-top: 11px;
    padding-bottom: 7px;
    background: #312e81;
}
QPushButton[buttonRole="success"] {
    border-color: #10b981;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #34d399, stop:0.5 #10b981, stop:1 #047857);
}
QPushButton[buttonRole="warning"] {
    border-color: #f59e0b;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #fbbf24, stop:0.5 #f59e0b, stop:1 #b45309);
}
QPushButton[buttonRole="danger"] {
    border-color: #ef4444;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #fb7185, stop:0.5 #ef4444, stop:1 #991b1b);
}
QPushButton[buttonRole="secondary"] {
    color: #c7d2fe;
    border-color: #6366f1;
    background: #232b47;
}
QPushButton[buttonRole="secondary"]:hover { background: #303a61; }
QPushButton[buttonRole="ghost"] {
    color: #cbd5e1;
    border-color: #475569;
    background: #151c2f;
}
QPushButton[buttonRole="ghost"]:hover { background: #202a45; }
QPushButton:disabled {
    color: #64748b;
    border-color: #334155;
    background: #1e293b;
}
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox, QPlainTextEdit {
    min-height: 26px;
    padding: 5px 9px;
    color: #e5e7eb;
    background: #151d31;
    border: 1px solid #3c4a64;
    border-radius: 9px;
    selection-background-color: #6366f1;
}
QComboBox:hover, QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QPlainTextEdit:hover {
    border-color: #818cf8;
}
QComboBox:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QPlainTextEdit:focus {
    border: 2px solid #818cf8;
}
QListWidget {
    background: #141b2d;
    border: 1px solid #334155;
    border-radius: 11px;
    outline: 0;
}
QListWidget::item { padding: 8px 9px; margin: 2px; border-radius: 8px; }
QListWidget::item:hover { background: #252f4c; }
QListWidget::item:selected {
    color: white;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0891b2, stop:0.5 #4f46e5, stop:1 #9333ea);
}
QProgressBar {
    min-height: 17px;
    border: 1px solid #475569;
    border-radius: 8px;
    background: #1e293b;
}
QProgressBar::chunk {
    border-radius: 7px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #06b6d4, stop:0.5 #3b82f6, stop:1 #8b5cf6);
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #64748b;
    border-radius: 5px;
    background: #111827;
}
QCheckBox::indicator:checked { border-color: #818cf8; background: #6366f1; }
QScrollBar:vertical { width: 11px; margin: 2px; background: transparent; }
QScrollBar::handle:vertical { min-height: 28px; border-radius: 5px; background: #4f5d78; }
QScrollBar::handle:vertical:hover { background: #6366f1; }
QToolTip {
    color: white;
    background: #172554;
    border: 1px solid #818cf8;
    border-radius: 7px;
    padding: 6px;
}
"""


_DANGER = (
    "delete", "reset", "disconnect", "abort", "cancel", "remove",
    "ဖျက်", "ဖြုတ်", "ပယ်ဖျက်", "ရပ်ရန်",
)
_WARNING = (
    "firmware", "failsafe", "bootloader", "reboot", "offline simulator",
    "test", "စမ်းသပ်", "စမ်းရန်",
)
_SUCCESS = (
    "save", "finish", "complete", "connect", "install", "apply",
    "validate", "create support", "သိမ်း", "ပြီးဆုံး", "ချိတ်ဆက်",
    "တင်ရန်", "စစ်ဆေးမှု", "ဖန်တီး",
)
_SECONDARY = (
    "open", "refresh", "back", "later", "export", "import", "duplicate",
    "ဖွင့်", "ပြန်စစ်", "နောက်သို့", "နောက်မှ", "ထုတ်ယူ", "သွင်းယူ",
)
_GHOST = (
    "close", "settings", "help", "view", "ပိတ်ရန်", "ဆက်တင်", "အကူအညီ",
)


def classify_button(text: str) -> str:
    clean = " ".join(str(text).casefold().split())
    if any(token in clean for token in _DANGER):
        return "danger"
    if any(token in clean for token in _WARNING):
        return "warning"
    if any(token in clean for token in _SUCCESS):
        return "success"
    if any(token in clean for token in _GHOST):
        return "ghost"
    if any(token in clean for token in _SECONDARY):
        return "secondary"
    return "primary"


class ProductThemeController(QObject):
    """Apply a colorful product theme without touching realtime I/O services."""

    def __init__(self, app: QApplication, root: QWidget) -> None:
        super().__init__(root)
        self.app = app
        self.root = root
        self.dark = app.palette().color(QPalette.ColorRole.Window).lightness() < 128
        self.app.setStyle("Fusion")
        self.app.setStyleSheet(DARK_QSS if self.dark else LIGHT_QSS)
        self.app.installEventFilter(self)
        central = getattr(root, "centralWidget", lambda: None)()
        if isinstance(central, QWidget):
            central.setObjectName("productAppRoot")
        self.polish_tree(root)

    def polish_tree(self, root: QWidget | None) -> None:
        if root is None:
            return
        widgets: list[QWidget] = [root]
        widgets.extend(root.findChildren(QWidget))
        for widget in widgets:
            if isinstance(widget, QPushButton):
                self.polish_button(widget)
            elif isinstance(widget, QGroupBox):
                widget.setProperty("uiCard", True)
                self._refresh(widget)
            elif isinstance(widget, QFrame):
                if widget.frameShape() == QFrame.Shape.StyledPanel:
                    widget.setProperty("uiCard", True)
                    self._refresh(widget)

    def polish_button(self, button: QPushButton) -> None:
        role = classify_button(button.text())
        if button.property("buttonRole") != role:
            button.setProperty("buttonRole", role)
            self._refresh(button)
        button.setCursor(button.cursor().shape())
        self._set_button_depth(button, pressed=False)

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if isinstance(watched, QPushButton):
            event_type = event.type()
            if event_type == QEvent.Type.Show:
                self.polish_button(watched)
            elif event_type == QEvent.Type.MouseButtonPress:
                self._set_button_depth(watched, pressed=True)
            elif event_type in {
                QEvent.Type.MouseButtonRelease,
                QEvent.Type.Leave,
                QEvent.Type.EnabledChange,
            }:
                self._set_button_depth(watched, pressed=False)
        return False

    def _set_button_depth(self, button: QPushButton, *, pressed: bool) -> None:
        role = str(button.property("buttonRole") or "primary")
        raised = button.isEnabled() and role not in {"ghost", "secondary"}
        effect = button.graphicsEffect()
        if not isinstance(effect, QGraphicsDropShadowEffect):
            effect = QGraphicsDropShadowEffect(button)
            button.setGraphicsEffect(effect)
        if not raised:
            effect.setEnabled(False)
            return
        effect.setEnabled(True)
        effect.setColor(QColor(15, 23, 42, 105 if not self.dark else 150))
        effect.setBlurRadius(8.0 if pressed else 18.0)
        effect.setOffset(0.0, 1.0 if pressed else 4.0)

    @staticmethod
    def _refresh(widget: QWidget) -> None:
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()
