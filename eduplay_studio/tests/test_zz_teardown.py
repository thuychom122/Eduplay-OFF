"""Module cleanup chay CUOI CUNG (ten 'zz' de dung thu tu alphabet).

Nhieu test tao widget cua Qt roi bo qua viec huy. Khi ca suite ket thuc,
Python tat interpreter: doi tuong Qt bi pha sau khi QApplication da bi
thu -> access violation 0xC0000005 o cua so loi (cac test van PASS, chi la
process chet luc thoat).

Module nay don dep mot lan cuoi truoc khi interpreter tat: huy het widget
top-level, xu ly event/DeferredDelete, thu gc. KHONG dung unittest.TestCase
vi module nay chi can chay khi import.
"""
import gc
import os
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _cleanup() -> None:
    try:
        import PySide6.QtWidgets as W

        app = W.QApplication.instance()
        if app is not None:
            for widget in app.topLevelWidgets():
                try:
                    widget.close()
                    widget.deleteLater()
                except Exception:
                    pass
            try:
                app.processEvents()
            except Exception:
                pass
            try:
                app.sendPostedEvents(None, 0)  # DeferredDelete
                app.processEvents()
            except Exception:
                pass
    except Exception:
        pass
    try:
        gc.collect()
    except Exception:
        pass


_cleanup()

# unittest se tu gan module nay vao suite; class rong de discovery khong loi.
class TestZZTeardown(unittest.TestCase):
    def test_noop(self):
        self.assertTrue(True)