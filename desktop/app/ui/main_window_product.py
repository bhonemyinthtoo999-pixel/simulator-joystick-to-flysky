from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QBoxLayout,
    QComboBox,
    QFrame,
    QLabel,
    QListView,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..services.localization_service import (
    SUPPORTED_LANGUAGES,
    apply_widget_language,
    localize_readiness_report,
    navigation_label,
    normalize_language,
    text,
)
from .main_window import MainWindow as _BaseMainWindow


class MainWindow(_BaseMainWindow):
    """Product shell with responsive navigation and English/Burmese UI."""

    NAVIGATION_KEYS = (
        "Dashboard",
        "Joystick Monitor",
        "Channel Mapping",
        "Calibration",
        "Profiles",
        "Adapter / Firmware",
        "Diagnostics",
        "Settings",
    )

    SETUP_STEP_KEYS = (
        "Welcome",
        "Flight controls",
        "Adapter firmware",
        "Calibration & mapping",
        "Ready check",
    )

    def __init__(self) -> None:
        self._language = "en"
        self._product_shell_ready = False
        self._default_application_font: QFont | None = None
        super().__init__()

        self._language = normalize_language(self.settings.language)
        app = QApplication.instance()
        if app is not None:
            self._default_application_font = QFont(app.font())

        self._install_product_navigation()
        self._wizard_body_layout = self._find_layout_with_widgets(
            self.setup_wizard,
            self.setup_wizard.steps,
            self.setup_wizard.stack,
        )
        self._wizard_footer_layout = self._find_layout_with_widgets(
            self.setup_wizard,
            self.setup_wizard.back_button,
            self.setup_wizard.next_button,
        )
        self.setup_wizard.installEventFilter(self)
        self._product_shell_ready = True
        self._apply_language()
        self._apply_responsive_layout()
        QTimer.singleShot(0, self._refresh_readiness)

    def _install_product_navigation(self) -> None:
        root = self.centralWidget()
        root_layout = root.layout() if root is not None else None
        if not isinstance(root_layout, QBoxLayout):
            return

        root_layout.removeWidget(self.navigation)
        self.navigation_panel = QFrame()
        self.navigation_panel.setObjectName("productNavigationPanel")
        self.navigation_panel.setStyleSheet(
            "QFrame#productNavigationPanel { border-right: 1px solid palette(midlight); background: palette(base); }"
        )
        navigation_layout = QVBoxLayout(self.navigation_panel)
        navigation_layout.setContentsMargins(12, 14, 12, 14)
        navigation_layout.setSpacing(10)

        self.navigation_brand = QLabel("Simulator Joystick to FlySky")
        self.navigation_brand.setWordWrap(True)
        self.navigation_brand.setStyleSheet("font-size: 15px; font-weight: 750;")
        self.navigation_language_label = QLabel("Language")
        self.navigation_language_label.setStyleSheet(
            "font-size: 10px; font-weight: 700; color: palette(mid);"
        )
        self.navigation_language = QComboBox()
        for code, label in SUPPORTED_LANGUAGES:
            self.navigation_language.addItem(label, code)

        for index, key in enumerate(self.NAVIGATION_KEYS):
            item = self.navigation.item(index)
            if item is not None:
                item.setData(Qt.ItemDataRole.UserRole, key)

        navigation_layout.addWidget(self.navigation_brand)
        navigation_layout.addWidget(self.navigation_language_label)
        navigation_layout.addWidget(self.navigation_language)
        navigation_layout.addWidget(self.navigation, 1)
        root_layout.insertWidget(0, self.navigation_panel)

        selected = self.navigation_language.findData(self._language)
        if selected >= 0:
            self.navigation_language.setCurrentIndex(selected)
        self.navigation_language.currentIndexChanged.connect(
            self._navigation_language_changed
        )

    @staticmethod
    def _find_layout_with_widgets(
        root: QWidget,
        first: QWidget,
        second: QWidget,
    ) -> QBoxLayout | None:
        for layout in root.findChildren(QBoxLayout):
            widgets = {
                layout.itemAt(index).widget()
                for index in range(layout.count())
                if layout.itemAt(index).widget() is not None
            }
            if first in widgets and second in widgets:
                return layout
        return None

    def _navigation_language_changed(self, _index: int) -> None:
        if not self._product_shell_ready:
            return
        language = normalize_language(self.navigation_language.currentData())
        if language == self._language:
            return
        self._language = language
        self.settings.language = language
        try:
            self.settings_store.save(self.settings)
        except OSError:
            pass
        self.settings_page.set_settings(self.settings)
        self._apply_language()
        self._refresh_readiness()

    def _apply_language(self) -> None:
        language = normalize_language(self._language)
        self._language = language
        self.settings.language = language

        selected = self.navigation_language.findData(language)
        if selected >= 0 and self.navigation_language.currentIndex() != selected:
            self.navigation_language.blockSignals(True)
            self.navigation_language.setCurrentIndex(selected)
            self.navigation_language.blockSignals(False)

        self.navigation_brand.setText(text("Simulator Joystick to FlySky", language))
        self.navigation_language_label.setText(text("Language", language))
        for index, key in enumerate(self.NAVIGATION_KEYS):
            item = self.navigation.item(index)
            if item is not None:
                item.setText(navigation_label(key, language))
                item.setData(Qt.ItemDataRole.UserRole, key)

        for index, key in enumerate(self.SETUP_STEP_KEYS):
            item = self.setup_wizard.steps.item(index)
            if item is not None:
                item.setText(f"{index + 1}.  {text(key, language)}")

        for index in range(self.pages.count()):
            page = self.pages.widget(index)
            setter = getattr(page, "set_language", None)
            if callable(setter):
                setter(language)
            else:
                apply_widget_language(page, language)
        apply_widget_language(self.setup_wizard, language)
        self.setup_wizard.setWindowTitle(
            text("Set up Simulator Joystick to FlySky", language)
        )
        self.setWindowTitle(text("Simulator Joystick to FlySky", language))
        self._apply_application_font(language)
        self._apply_wizard_responsive()

    def _apply_application_font(self, language: str) -> None:
        app = QApplication.instance()
        if app is None:
            return
        if language == "my":
            families = set(QFontDatabase.families())
            family = "Myanmar Text" if "Myanmar Text" in families else app.font().family()
            font = QFont(family, max(10, app.font().pointSize()))
            app.setFont(font)
        elif self._default_application_font is not None:
            app.setFont(QFont(self._default_application_font))

    def _refresh_readiness(self) -> None:
        super()._refresh_readiness()
        report = getattr(self, "_readiness_report", None)
        if report is None:
            return
        localized = localize_readiness_report(report, self._language)
        self._readiness_report = localized
        self.dashboard_page.set_readiness(localized)
        self.setup_wizard.set_report(localized)
        apply_widget_language(self.setup_wizard, self._language)

    def _save_settings(self, payload: dict[str, object]) -> None:
        super()._save_settings(payload)
        language = normalize_language(self.settings.language)
        if language != self._language:
            self._language = language
            self._apply_language()
        self._refresh_readiness()

    def _navigate_to_product_page(self, page_name: str) -> None:
        if page_name == "Setup":
            self._open_setup_wizard()
            return
        for index in range(self.navigation.count()):
            item = self.navigation.item(index)
            key = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
            if key == page_name or (item is not None and item.text() == page_name):
                self.navigation.setCurrentRow(index)
                self.showNormal()
                self.raise_()
                self.activateWindow()
                return

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        if self._product_shell_ready:
            self._apply_responsive_layout()

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if watched is self.setup_wizard and event.type() in {
            QEvent.Type.Resize,
            QEvent.Type.Show,
        }:
            QTimer.singleShot(0, self._apply_wizard_responsive)
        return super().eventFilter(watched, event)

    def _apply_responsive_layout(self) -> None:
        width = max(1, self.width())
        if width < 820:
            panel_width = 150
            self.navigation_brand.setStyleSheet("font-size: 12px; font-weight: 750;")
            self.navigation.setStyleSheet("font-size: 10px;")
        elif width < 1080:
            panel_width = 185
            self.navigation_brand.setStyleSheet("font-size: 14px; font-weight: 750;")
            self.navigation.setStyleSheet("")
        else:
            panel_width = 230
            self.navigation_brand.setStyleSheet("font-size: 15px; font-weight: 750;")
            self.navigation.setStyleSheet("")
        self.navigation_panel.setFixedWidth(panel_width)
        self._apply_wizard_responsive()

    def _apply_wizard_responsive(self) -> None:
        if not hasattr(self, "setup_wizard"):
            return
        width = max(1, self.setup_wizard.width())
        narrow = width < 760
        if self._wizard_body_layout is not None:
            self._wizard_body_layout.setDirection(
                QBoxLayout.Direction.TopToBottom
                if narrow
                else QBoxLayout.Direction.LeftToRight
            )
        if narrow:
            self.setup_wizard.steps.setMinimumWidth(0)
            self.setup_wizard.steps.setMaximumWidth(16777215)
            self.setup_wizard.steps.setFixedHeight(92)
            self.setup_wizard.steps.setFlow(QListView.Flow.LeftToRight)
            self.setup_wizard.steps.setWrapping(True)
        else:
            self.setup_wizard.steps.setMinimumHeight(0)
            self.setup_wizard.steps.setMaximumHeight(16777215)
            self.setup_wizard.steps.setFixedWidth(210)
            self.setup_wizard.steps.setFlow(QListView.Flow.TopToBottom)
            self.setup_wizard.steps.setWrapping(False)

        if self._wizard_footer_layout is not None:
            self._wizard_footer_layout.setDirection(
                QBoxLayout.Direction.TopToBottom
                if width < 680
                else QBoxLayout.Direction.LeftToRight
            )
