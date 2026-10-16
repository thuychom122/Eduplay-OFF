"""Delegate ve dong NHOM trong danh sach dieu huong cua hop thoai Tro giup.

QSS khong ho tro property selector cho tung item cua QListWidget (chi ho tro
mot so trang thai mac dinh), nen khong style duoc "dong nhom" bang
`QListWidget::item[...]=...`. De phan biet ro rang giua NHOM (nho, chu nho
in hoa, khong co khung) va MUC (the o, co icon, bo vien), ta ve bang delegate.
"""
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QStyledItemDelegate

GROUP_ROLE = Qt.ItemDataRole.UserRole + 1


class HelpNavDelegate(QStyledItemDelegate):
    """Ve dong nhom khac kieu voi dong muc."""

    def __init__(self, color_hex: str = "#7F56D9", rule_hex: str = "#E2E8F0", parent=None):
        super().__init__(parent)
        self._color = QColor(color_hex)
        self._rule = QColor(rule_hex)

    # --- helpers ---------------------------------------------------------
    @staticmethod
    def is_group(index) -> bool:
        try:
            return str(index.data(GROUP_ROLE) or "") == "group"
        except Exception:
            return False

    # --- override --------------------------------------------------------
    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        try:
            if self.is_group(index):
                return QSize(size.width(), max(30, size.height()))
        except Exception:
            pass
        return size

    def paint(self, painter: QPainter, option, index):
        try:
            if not self.is_group(index):
                super().paint(painter, option, index)
                return
        except Exception:
            try:
                super().paint(painter, option, index)
            except Exception:
                pass
            return

        painter.save()
        try:
            text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
            try:
                text = text.upper()
            except Exception:
                pass
            font = QFont(option.font)
            try:
                size = font.pointSizeF()
            except Exception:
                size = 0.0
            if size <= 0:
                size = 9.0
            font.setPointSizeF(max(8.0, size - 1.0))
            font.setBold(True)
            try:
                font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.8)
            except Exception:
                pass
            painter.setFont(font)
            painter.setPen(QPen(self._color))

            rect = option.rect.adjusted(8, 0, -8, 0)
            text_rect = rect.adjusted(0, 2, 0, -6)
            painter.drawText(
                text_rect,
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                text,
            )

            # duong phan cach nho duoi dong nhom
            pen = QPen(self._rule)
            try:
                pen.setWidthF(1.0)
            except Exception:
                pass
            painter.setPen(pen)
            y = rect.bottom() - 5
            painter.drawLine(rect.left(), y, rect.right(), y)
        except Exception:
            pass
        finally:
            painter.restore()