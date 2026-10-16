"""Chuyển động dùng chung: tôn trọng cờ "giảm chuyển động" + rút ngắn animation.

Vì sao cần:
  1. Trước đây cờ accessibility.reduce_motion CHỈ được đọc ở đúng 1 chỗ
     (animation credits) - mọi hiệu ứng khác (intro, drawer, toast, coach
     marks, card trang chủ) vẫn chạy. Người bật "giảm chuyển động"
     (hoặc máy yếu) vẫn bị hiệu ứng nặng.
  2. Animation dài trên widget lớn = repaint nhiều khung hình = lag.
     Rút ngắn thời lượng giúp cảm giác "nhanh hơn" rõ rệt.

Cách dùng:
    from eduplay.ui.motion import motion_enabled, ms, set_opacity, fade_widget
    if motion_enabled():
        ... QPropertyAnimation ...
    else:
        set_opacity(widget, 1.0)
"""
from __future__ import annotations

# He so thu nho thoi luong (ms cua animation mac dinh se nhanh hon)
SPEED_UP = 1.25

_cache = {"value": None, "ts": 0.0}
_TTL = 2.0  # gi cache 2s: doc settings moi 1 lan, khong moi khung hinh


def _read_setting() -> bool:
    try:
        from eduplay.core.settings_manager import SettingsManager

        acc = SettingsManager().get_accessibility_settings() or {}
        return bool(acc.get("reduce_motion", False))
    except Exception:
        return False


def motion_enabled() -> bool:
    """True = user muon it hieu ung. False = duoc phep chay animation."""
    import time

    now = time.monotonic()
    cached = _cache.get("value")
    if cached is not None and (now - float(_cache.get("ts") or 0.0)) < _TTL:
        return bool(cached)
    value = _read_setting()
    _cache["value"] = bool(value)
    _cache["ts"] = now
    return bool(value)


def invalidate_cache() -> None:
    """Goi sau khi nguoi dung doi cai dat de ap dung ngay."""
    _cache["value"] = None
    _cache["ts"] = 0.0


def ms(duration_ms: float) -> int:
    """Rut ngan mot thoi luong, bo qua neu nguoi dung tat hieu ung."""
    try:
        if motion_enabled():
            return 0
        value = int(round(float(duration_ms) / SPEED_UP))
        return max(1, value)
    except Exception:
        return int(duration_ms or 0)


def set_opacity(widget, value: float) -> None:
    """Dat mo ngay (khong animation) - luon an toan, khong raise."""
    try:
        widget.setGraphicsEffect(None)
    except Exception:
        pass
    try:
        window_opacity = getattr(widget, "windowOpacity", None)
        if callable(window_opacity):
            value = max(0.0, min(1.0, float(value)))
            window_opacity(float(value))
    except Exception:
        pass
    try:
        from PySide6.QtWidgets import QGraphicsOpacityEffect

        eff = QGraphicsOpacityEffect(widget)
        eff.setOpacity(max(0.0, min(1.0, float(value))))
        widget.setGraphicsEffect(eff)
    except Exception:
        pass


def fade_overlay(parent, color: str = "#0F172A", duration_ms: int = 150,
                 alpha: int = 110):
    """Mot lop mau phu (overlay) fade de chuyen man hinh.

    RE nhon nhieu so voi QGraphicsOpacityEffect dat len ca stacked widget:
    overlay chi ve MOT mau phu nen moi khung hinh rat re, con effect tren
    widget lon phai render toan bo noi dung ra buffer rieng -> lag.

    Tra ve (overlay, animation) hoac (None, None) neu tat hieu ung.
    """
    if parent is None:
        return None, None
    try:
        if motion_enabled():
            return None, None
    except Exception:
        pass
    try:
        from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect
        from PySide6.QtGui import QColor
        from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

        overlay = QWidget(parent)
        overlay.setAttribute(parent.windowFlags() & 0x00020000, True)  # WA_TransparentForMouseEvents
        overlay.setAttribute(0x0020, True)  # WA_TranslucentBackground (no-op off-screen)
        overlay.setAutoFillBackground(True)
        c = QColor(color)
        c.setAlpha(int(alpha))
        overlay.setStyleSheet(f"background-color: rgba({c.red()},{c.green()},{c.blue()},{c.alpha()});")
        overlay.setGeometry(QRect(0, 0, parent.width(), parent.height()))
        overlay.raise_()
        overlay.show()

        eff = QGraphicsOpacityEffect(overlay)
        eff.setOpacity(1.0)
        overlay.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity", overlay)
        anim.setDuration(ms(duration_ms))
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.OutQuad)

        def _cleanup():
            try:
                overlay.hide()
                overlay.deleteLater()
            except Exception:
                pass

        anim.finished.connect(_cleanup)
        return overlay, anim
    except Exception:
        return None, None


def fade_widget(widget, start: float = 0.0, end: float = 1.0,
                duration_ms: int = 180, on_finished=None):
    """Mo dan mot widget (dung cho widget NHO nhu toast).

    Neu tat hieu ung -> dat thang, khong animation, van goi on_finished.
    Chi nen dung cho widget nho: QGraphicsOpacityEffect tren widget lon se
    render lai toan bo noi dung moi khung hinh -> lag. Khi do hay dung
    fade_overlay() thay the.

    Tra ve QPropertyAnimation hoac None.
    """
    try:
        if motion_enabled():
            set_opacity(widget, end)
            if callable(on_finished):
                on_finished()
            return None
    except Exception:
        pass
    try:
        from PySide6.QtCore import QPropertyAnimation
        from PySide6.QtWidgets import QGraphicsOpacityEffect

        eff = widget.graphicsEffect()
        if not isinstance(eff, QGraphicsOpacityEffect):
            eff = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(eff)
        eff.setOpacity(float(start))
        anim = QPropertyAnimation(eff, b"opacity", widget)
        anim.setDuration(ms(duration_ms))
        anim.setStartValue(float(start))
        anim.setEndValue(float(end))
        if callable(on_finished):
            anim.finished.connect(on_finished)
        anim.start()
        return anim
    except Exception:
        try:
            set_opacity(widget, end)
            if callable(on_finished):
                on_finished()
        except Exception:
            pass
        return None