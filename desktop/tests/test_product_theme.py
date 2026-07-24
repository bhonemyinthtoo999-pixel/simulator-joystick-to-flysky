from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QFrame, QPushButton, QVBoxLayout, QWidget

from app.ui.product_theme import ProductThemeController, classify_button


_TEST_APPLICATION = QApplication.instance() or QApplication([])


def test_button_roles_cover_colorful_product_actions() -> None:
    assert classify_button("Save validation report") == "success"
    assert classify_button("Install firmware") == "warning"
    assert classify_button("Disconnect") == "danger"
    assert classify_button("Open Joystick Monitor") == "secondary"
    assert classify_button("Close") == "ghost"
    assert classify_button("ဆက်လက်ပြင်ဆင်ရန်") == "primary"
    assert classify_button("Validation report သိမ်းရန်") == "success"


def test_theme_marks_cards_and_adds_button_depth() -> None:
    root = QWidget()
    root.setObjectName("productAppRoot")
    layout = QVBoxLayout(root)
    card = QFrame()
    card.setFrameShape(QFrame.Shape.StyledPanel)
    button = QPushButton("Save settings")
    layout.addWidget(card)
    layout.addWidget(button)

    controller = ProductThemeController(_TEST_APPLICATION, root)
    controller.polish_tree(root)

    assert card.property("uiCard") is True
    assert button.property("buttonRole") == "success"
    assert button.graphicsEffect() is not None
    assert "qlineargradient" in _TEST_APPLICATION.styleSheet()
    root.close()
