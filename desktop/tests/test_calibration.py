from app.services.calibration_service import AxisCalibration, CalibrationSession


def test_axis_calibration_maps_endpoints_and_center() -> None:
    calibration = AxisCalibration(minimum=-0.8, center=0.1, maximum=0.9, deadzone=0.02)
    assert calibration.normalize(-0.8) == -1.0
    assert calibration.normalize(0.1) == 0.0
    assert calibration.normalize(0.9) == 1.0
    assert calibration.to_rc(0.1) == 1500


def test_session_collects_limits() -> None:
    session = CalibrationSession(2)
    session.observe([-0.5, 0.25])
    session.observe([0.8, -0.75])
    session.capture_center([0.1, -0.1])
    result = session.result()
    assert result[0].minimum == -0.5
    assert result[0].maximum == 0.8
    assert result[0].center == 0.1
