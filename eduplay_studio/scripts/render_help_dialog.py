"""Render hop thoai Tro giup ra PNG de kiem tra bang mat (chay offscreen)."""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest import mock

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication, QDialog, QMainWindow  # noqa: E402

from eduplay.ui.main_window import MainWindow  # noqa: E402

app = QApplication.instance() or QApplication([])

window = MainWindow.__new__(MainWindow)
QMainWindow.__init__(window)


class _StubSettings:
    def get_language(self):
        return "vi"

    def get_theme(self):
        return os.environ.get("RENDER_THEME", "light")

    def get(self, *_a, **_k):
        return None


window.settings_manager = _StubSettings()

captured = {}


def _fake_exec(self, *args, **kwargs):
    captured["dlg"] = self
    return QDialog.Accepted


with mock.patch.object(QDialog, "exec", new=_fake_exec):
    window.show_help()

dlg = captured["dlg"]
dlg.resize(1040, 680)
dlg.show()
app.processEvents()
for _ in range(6):
    app.processEvents()

out = sys.argv[1] if len(sys.argv) > 1 else "help_dialog.png"
pix = dlg.grab()
pix.save(out)
print("saved", out, pix.width(), "x", pix.height())