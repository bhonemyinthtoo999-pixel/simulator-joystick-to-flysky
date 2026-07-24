from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QListView, QScrollArea, QSplitter

from app.ui.page_mapping_release import MappingPage


_TEST_APPLICATION = QApplication.instance() or QApplication([])


def test_mapping_workspace_uses_two_column_channel_grid() -> None:
    page = MappingPage()
    page.resize(1110, 720)
    page.show()
    _TEST_APPLICATION.processEvents()

    assert page.channel_list.viewMode() == QListView.ViewMode.IconMode
    assert page.channel_list.flow() == QListView.Flow.LeftToRight
    assert page.channel_list.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert page.channel_list.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert page.channel_list.gridSize().height() == 58
    page.close()


def test_mapping_editor_has_no_scrollbars_at_desktop_width() -> None:
    page = MappingPage()
    page.resize(1110, 720)
    page.show()
    _TEST_APPLICATION.processEvents()

    splitter = page.findChild(QSplitter)
    editor = getattr(page, "_editor_scroll", None)
    channel_panel = getattr(page, "_channel_panel", None)

    assert splitter is not None
    assert splitter.orientation() == Qt.Orientation.Horizontal
    assert isinstance(editor, QScrollArea)
    assert editor.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert editor.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert channel_panel is not None
    assert channel_panel.minimumWidth() >= 390
    assert page.reverse_box.text() == "Reverse"
    assert page.auto_instruction.isHidden()
    page.close()
