from PySide6.QtCore import QCoreApplication

from app.services.joystick_service import JoystickService


def test_joystick_state_signal_preserves_nested_python_payload() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    service = JoystickService(demo_enabled=False)
    received: list[object] = []
    service.state_changed.connect(received.append)

    payload = {
        7: {
            "instance_id": 7,
            "axes": [0.25, -0.5],
            "buttons": [False, True],
            "hats": [(0, 1)],
        }
    }
    service.state_changed.emit(payload)
    app.processEvents()

    assert received == [payload]
