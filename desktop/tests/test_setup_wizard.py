from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.services.readiness_service import ReadinessItem, ReadinessReport
from app.ui.setup_wizard import SetupWizard


_APP = QApplication.instance() or QApplication([])


def ready_report() -> ReadinessReport:
    items = tuple(
        ReadinessItem(key, title, "ready", "Ready")
        for key, title in (
            ("controls", "Flight controls detected"),
            ("roles", "AETR device roles assigned"),
            ("calibration", "Controls calibrated"),
            ("mapping", "AETR mapping is valid"),
            ("adapter", "Hardware adapter connected"),
            ("safety", "Strict AETR failsafe armed"),
        )
    )
    return ReadinessReport(
        ready=True,
        headline="READY TO USE",
        summary="Everything is ready.",
        next_action="Open hardware test",
        next_page="Adapter / Firmware",
        items=items,
    )


def test_setup_wizard_accepts_ports_and_enables_finish_when_ready() -> None:
    wizard = SetupWizard()
    wizard.set_ports(
        [{"device": "COM10", "description": "USB-SERIAL CH340"}],
        "COM10",
    )
    wizard.set_report(ready_report())

    assert wizard.port_combo.currentData() == "COM10"
    assert wizard.finish_button.isEnabled()
    assert wizard.ready_title.text() == "READY TO USE"
    wizard.close()
