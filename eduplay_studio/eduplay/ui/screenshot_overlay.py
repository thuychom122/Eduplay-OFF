import sys
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, Signal, QTimer, QPoint, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QPixmap, QGuiApplication


class ScreenshotOverlay(QWidget):
    """Transparent fullscreen overlay for area-selection screenshot."""

    capture_done = Signal(object)

    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self._main_window = main_window
        self._dragging = False
        self._start = QPoint()
        self._end = QPoint()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setCursor(Qt.CrossCursor)

    def start(self):
        if self._main_window:
            self._main_window.showMinimized()
        QTimer.singleShot(350, self._show_overlay)

    def _show_overlay(self):
        screen = QGuiApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            self.setGeometry(geo)
        self.showFullScreen()
        self.raise_()
        self.activateWindow()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 80))

        if self._dragging and not self._start.isNull() and not self._end.isNull():
            sel = QRect(self._start, self._end).normalized()
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillRect(sel, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            pen = QPen(QColor(255, 255, 255, 220), 2, Qt.SolidLine)
            painter.setPen(pen)
            painter.drawRect(sel)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._start = event.pos()
            self._end = event.pos()
            self.update()

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._end = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self._end = event.pos()
            sel = QRect(self._start, self._end).normalized()
            self.hide()
            if sel.width() > 5 and sel.height() > 5:
                QTimer.singleShot(150, lambda: self._capture(sel))
            else:
                self._restore_and_close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self._dragging = False
            self._restore_and_close()

    def _capture(self, rect: QRect):
        try:
            from PIL import ImageGrab
            bbox = (rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height())
            pil_img = ImageGrab.grab(bbox=bbox)
            data = pil_img.tobytes("raw", "RGBA")
            qimg = QPixmap.fromImage(
                __import__("PySide6.QtGui", fromlist=["QImage"]).QImage(
                    data, pil_img.width, pil_img.height, pil_img.width * 4,
                    __import__("PySide6.QtGui", fromlist=["QImage"]).QImage.Format_RGBA8888,
                )
            )
            self.capture_done.emit(qimg)
        except Exception:
            try:
                screen = QGuiApplication.primaryScreen()
                if screen:
                    qimg = screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())
                    self.capture_done.emit(qimg)
            except Exception:
                pass
        self._restore_and_close()

    def _restore_and_close(self):
        if self._main_window:
            self._main_window.showNormal()
            self._main_window.raise_()
            self._main_window.activateWindow()
        self.close()
