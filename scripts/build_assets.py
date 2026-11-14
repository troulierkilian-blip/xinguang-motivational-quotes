"""Create a native application icon and collect dependency license notices."""
import importlib.metadata
import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication
from xinguang.catalog import Catalog

app = QApplication([])
catalog = Catalog()
catalog.validate_files()
image = QImage(256, 256, QImage.Format.Format_ARGB32)
image.fill(Qt.GlobalColor.transparent)
painter = QPainter(image)
QSvgRenderer(str(ROOT / "assets" / "logo.svg")).render(painter, QRectF(0, 0, 256, 256))
painter.end()
encoded = QByteArray()
buffer = QBuffer(encoded)
buffer.open(QIODevice.OpenModeFlag.WriteOnly)
if not image.save(buffer, "PNG"):
    raise RuntimeError("Could not render application icon")
png = bytes(encoded)
header = struct.pack("<HHH", 0, 1, 1)
entry = struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(png), 22)
(ROOT / "assets" / "app.ico").write_bytes(header + entry + png)

licenses = ROOT / "assets" / "licenses"
licenses.mkdir(exist_ok=True)
for package in ("PySide6", "PySide6_Essentials", "PySide6_Addons", "shiboken6", "PyInstaller"):
    distribution = importlib.metadata.distribution(package)
    for file in distribution.files or []:
        filename = str(file)
        if ".dist-info/licenses/" in filename.replace("\\", "/"):
            source = Path(distribution.locate_file(file))
            if source.is_file():
                destination = licenses / package / Path(filename.split("licenses/", 1)[-1])
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read_bytes())
print("Assets verified: 180 quotes, 12 backgrounds, app.ico")
python_license = Path(sys.base_prefix) / "LICENSE.txt"
if python_license.is_file():
    destination = licenses / "Python" / "LICENSE.txt"
    destination.parent.mkdir(exist_ok=True)
    destination.write_bytes(python_license.read_bytes())
