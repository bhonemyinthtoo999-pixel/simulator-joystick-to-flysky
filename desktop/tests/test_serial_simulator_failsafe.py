from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication

from app.services.protocol_service import MessageType
from app.services.serial_service import SerialService


_APP = QCoreApplication.instance() or QCoreApplication([])


def test_simulator_enters_safe_aetr_after_desktop_timeout() -> None:
    service = SerialService()
    service._simulated = True

    service._simulate_request(
        MessageType.LIVE_CHANNELS,
        1,
        {"channels": [1620, 1410, 1780, 1540, 1900, 1100, 1500, 1500]},
    )
    active = service._simulated_status_payload()
    assert active["stream_active"] is True
    assert active["failsafe_active"] is False
    assert active["channels"][:4] == [1620, 1410, 1780, 1540]

    service._simulated_last_channels_at -= service._simulated_timeout_s + 0.2
    safe = service._simulated_status_payload()
    assert safe["stream_active"] is False
    assert safe["failsafe_active"] is True
    assert safe["stream_age_ms"] >= 700
    assert safe["channels"][:4] == [1500, 1500, 1000, 1500]


def test_explicit_status_request_returns_status_payload() -> None:
    service = SerialService()
    service._simulated = True
    service._simulate_request(MessageType.STATUS, 9, {})

    kind, sequence, payload = service._simulated_pending.pop()
    assert kind == MessageType.STATUS
    assert sequence == 9
    assert payload["ppm_active"] is True
    assert "channels" in payload
    assert _APP is not None
