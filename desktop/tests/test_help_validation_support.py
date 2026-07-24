from __future__ import annotations

import json
import os
from pathlib import Path
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.services.diagnostics_service import DiagnosticEntry
from app.services.hardware_validation_service import HardwareValidationStore
from app.services.support_package_service import SupportPackageService
from app.ui.page_help import HelpPage
from app.ui.validation_wizard import HardwareValidationWizard


_TEST_APPLICATION = QApplication.instance() or QApplication([])


def test_help_page_switches_language_and_reflows() -> None:
    page = HelpPage()
    page.set_version("0.8.3")
    page.set_language("my")
    page.resize(720, 700)
    page._apply_responsive_layout()

    assert "အကူအညီ" in page.title.text()
    assert "0.8.3" in page.about_text.text()
    assert page.actions_grid.getItemPosition(
        page.actions_grid.indexOf(page.support_card)
    )[0] == 1
    page.close()


def test_validation_requires_all_live_and_manual_checks() -> None:
    wizard = HardwareValidationWizard()
    wizard.set_snapshot(
        {
            "controls_ready": True,
            "adapter_ready": True,
            "streaming": True,
            "mapping_ready": True,
            "ppm_active": True,
            "board": "Arduino UNO/Nano ATmega328P",
            "firmware_version": "0.3.0",
            "channels": [1500, 1500, 1000, 1500],
        }
    )
    assert not wizard.complete_button.isEnabled()
    for box in wizard.manual_checks.values():
        box.setChecked(True)
    assert wizard.complete_button.isEnabled()
    wizard.set_language("my")
    assert "Hardware" in wizard.title.text()
    wizard.close()


def test_validation_store_round_trip(tmp_path: Path) -> None:
    store = HardwareValidationStore(tmp_path / "validation.json")
    store.save({"board": "UNO", "validated_at": "2026-07-24T00:00:00+00:00"})
    loaded = store.load()
    assert loaded["board"] == "UNO"
    assert loaded["schema_version"] == 1


def test_support_package_contains_only_expected_support_files(tmp_path: Path) -> None:
    path = SupportPackageService.create(
        tmp_path / "support.zip",
        context={
            "application": {"version": "0.8.3"},
            "adapter": {"kind": "arduino_uno"},
            "note": "no passwords here",
        },
        diagnostics=[
            DiagnosticEntry("12:00:00.000", "INFO", "Test", "Everything is healthy")
        ],
        validation_report={"board": "UNO", "validated_at": "now"},
    )

    assert path.exists()
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        assert names == {
            "README.txt",
            "support-context.json",
            "diagnostics.txt",
            "hardware-validation.json",
        }
        manifest = json.loads(archive.read("support-context.json"))
        assert manifest["privacy"]["contains_passwords"] is False
        assert manifest["application_context"]["application"]["version"] == "0.8.3"
        assert "Everything is healthy" in archive.read("diagnostics.txt").decode("utf-8")
