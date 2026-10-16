"""Render man hinh Trang chu ra PNG de kiem hieu ung bang mat (offscreen)."""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtGui import QPixmap  # noqa: E402
from PySide6.QtCore import QEvent  # noqa: E402

app = QApplication.instance() or QApplication([])

from eduplay.ui.screens.home_screen import HomeScreen  # noqa: E402

win = HomeScreen()
win.resize(1200, 820)
win.show()
for _ in range(8):
    app.processEvents()


def pump(n=10):
    for _ in range(n):
        app.processEvents()


out = sys.argv[1] if len(sys.argv) > 1 else "home.png"

# 1) trang thai thuong
win.grab().save(out)
print("saved", out, "(normal)")

# 2) hover vao card "CHINH SUA" -> nen tang len + bong do
# (phai cho animation vao chay xong truoc: trong lúc do card dang co
#  QGraphicsOpacityEffect nen hieu ung bong do co tinh de khong ghi de)
import time as _time  # noqa: E402

_deadline = _time.time() + 2.0
while _time.time() < _deadline:
    app.processEvents()
    _time.sleep(0.02)

card = getattr(win, "edit_card", None)
if card is not None:
    print("sau entrance -> effect:", type(card.graphicsEffect()).__name__)
    try:
        card.enterEvent(QEvent(QEvent.Type.Enter))
    except Exception as exc:
        print("enterEvent loi:", exc)
    pump(6)
    p2 = out.replace(".png", "_hover.png")
    win.grab().save(p2)
    print("saved", p2, "(hover)")
    print("graphicsEffect:", type(card.graphicsEffect()).__name__)
    print("pos:", card.pos(), "base:", getattr(card, "_base_pos", None))

# 3) do chi phi ve: bao gioi o 60 lan roi do thoi gian trung binh
import time  # noqa: E402

t0 = time.perf_counter()
for _ in range(60):
    win.grab()
paint_ms = (time.perf_counter() - t0) / 60 * 1000
print(f"thoi gian ve 1 khung hinh: {paint_ms:.1f} ms")

card2 = getattr(win, "edit_card", None)
if card2 is not None:
    try:
        card2.leaveEvent(QEvent(QEvent.Type.Leave))
    except Exception:
        pass
    pump(4)
    print("sau leave -> effect:", card2.graphicsEffect())
t0 = time.perf_counter()
for _ in range(60):
    win.grab()
paint2 = (time.perf_counter() - t0) / 60 * 1000
print(f"thoi gian ve (khong hover): {paint2:.1f} ms")