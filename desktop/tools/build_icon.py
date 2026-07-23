from pathlib import Path
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SVG_PATH = ASSETS / "app_icon.svg"
PNG_PATH = ASSETS / "SimulatorJoystickToFlySky.png"
ICO_PATH = ASSETS / "SimulatorJoystickToFlySky.ico"

ICON_SIZES = [
    (16, 16),
    (24, 24),
    (32, 32),
    (48, 48),
    (64, 64),
    (128, 128),
    (256, 256),
]


def main() -> int:
    app = QGuiApplication.instance() or QGuiApplication(["build-icon"])
    renderer = QSvgRenderer(str(SVG_PATH))
    if not renderer.isValid():
        raise RuntimeError(f"Invalid SVG icon: {SVG_PATH}")

    image = QImage(1024, 1024, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    renderer.render(painter, QRectF(0, 0, 1024, 1024))
    painter.end()
    if not image.save(str(PNG_PATH), "PNG"):
        raise RuntimeError(f"Could not save {PNG_PATH}")

    with Image.open(PNG_PATH) as source:
        source.convert("RGBA").save(
            ICO_PATH,
            format="ICO",
            sizes=ICON_SIZES,
        )
    if not ICO_PATH.exists() or ICO_PATH.stat().st_size < 1024:
        raise RuntimeError(f"Invalid generated ICO: {ICO_PATH}")
    print(f"Built {ICO_PATH}")
    assert app is not None
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
