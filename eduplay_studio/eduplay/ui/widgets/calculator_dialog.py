"""Hộp thoại Tính toán nhanh (Ctrl+T) - theo theme light/dark của app."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton,
)

from eduplay.core.i18n import I18n


class CalculatorDialog(QDialog):
    DARK_QSS = """
            QDialog#calculator-dialog {
                background-color: #101828;
                border: 1px solid #344054;
                border-radius: 16px;
            }
            QLineEdit {
                background-color: #182230;
                color: #F8FAFC;
                border: 1px solid #7F56D9;
                border-radius: 12px;
                padding: 12px 14px;
                font-size: 16px;
            }
            QLineEdit:focus {
                border: 1px solid #7F56D9;
            }
            QPushButton {
                background-color: #FFFFFF;
                color: #1F2937;
                border: 1px solid #D1D5DB;
                border-radius: 10px;
                padding: 8px 22px;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #F0FDF4;
                border: 1px solid #7F56D9;
            }
            QPushButton#calc-ok {
                background-color: #7F56D9;
                color: #FFFFFF;
                border: 1px solid #7F56D9;
            }
            QPushButton#calc-ok:hover {
                background-color: #6D3FC4;
            }
            """

    LIGHT_QSS = """
            QDialog#calculator-dialog {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 16px;
            }
            QLineEdit {
                background-color: #FFFFFF;
                color: #1F2937;
                border: 1px solid #7F56D9;
                border-radius: 12px;
                padding: 12px 14px;
                font-size: 16px;
            }
            QLineEdit:focus {
                border: 1px solid #7F56D9;
            }
            QPushButton {
                background-color: #FFFFFF;
                color: #1F2937;
                border: 1px solid #D1D5DB;
                border-radius: 10px;
                padding: 8px 22px;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #F0FDF4;
                border: 1px solid #7F56D9;
            }
            QPushButton#calc-ok {
                background-color: #7F56D9;
                color: #FFFFFF;
                border: 1px solid #7F56D9;
            }
            QPushButton#calc-ok:hover {
                background-color: #6D3FC4;
            }
            """

    def __init__(self, parent=None, lang: str = "en", theme: str | None = None):
        super().__init__(parent)
        self._lang = str(lang or "en")
        self._theme = self._resolve_theme(theme)
        self._expression = ""
        self.setModal(True)
        self.setWindowTitle(self._tr("calculator.title", "Tính toán nhanh (Ctrl+T)", "Quick calculator (Ctrl+T)"))
        self.setMinimumWidth(480)
        self.setObjectName("calculator-dialog")
        self._build()
        self.apply_theme(self._theme)

    @staticmethod
    def _resolve_theme(theme: str | None) -> str:
        try:
            t = str(theme or "").strip().lower()
        except Exception:
            t = ""
        if t in ("light", "dark"):
            return t
        try:
            from eduplay.core.settings_manager import SettingsManager
            t2 = str(SettingsManager().get_theme() or "").strip().lower()
            if t2 in ("light", "dark"):
                return t2
        except Exception:
            pass
        return "light"

    def _t(self, vi: str, en: str) -> str:
        return vi if str(self._lang or "en").startswith("vi") else en

    def _tr(self, key: str, fallback_vi: str, fallback_en: str) -> str:
        try:
            value = I18n.t(key, self._lang)
            if isinstance(value, str) and value != key and value.strip():
                return value
        except Exception:
            pass
        return self._t(fallback_vi, fallback_en)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        self.prompt_label = QLabel(
            self._tr(
                "calculator.prompt",
                "Nhập biểu thức (vd: 12x8:4, dùng x thay *, : thay /):",
                "Enter expression (e.g. 12*8+5, x for *, : for /):",
            )
        )
        root.addWidget(self.prompt_label)

        self.input = QLineEdit()
        self.input.setPlaceholderText("12x8:4")
        self.input.textChanged.connect(self._update_live_result)
        self.input.returnPressed.connect(self.accept)
        root.addWidget(self.input)

        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        root.addWidget(self.result_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.ok_btn = QPushButton("OK")
        self.ok_btn.setObjectName("calc-ok")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton(self._t("Hủy", "Cancel"))
        self.cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self.ok_btn)
        btn_row.addWidget(self.cancel_btn)
        root.addLayout(btn_row)

    def apply_theme(self, theme: str | None = None):
        try:
            t = self._resolve_theme(theme if theme is not None else getattr(self, "_theme", None))
        except Exception:
            t = "light"
        self._theme = t
        try:
            if t == "dark":
                self.prompt_label.setStyleSheet("QLabel{font-size:13px;color:#E5E7EB;}")
                self.result_label.setStyleSheet("QLabel{font-size:14px;font-weight:700;color:#E5E7EB;}")
                self.setStyleSheet(self.DARK_QSS)
            else:
                self.prompt_label.setStyleSheet("QLabel{font-size:13px;color:#0F172A;}")
                self.result_label.setStyleSheet("QLabel{font-size:14px;font-weight:700;color:#0F172A;}")
                self.setStyleSheet(self.LIGHT_QSS)
        except Exception:
            pass

    def _update_live_result(self):
        try:
            from eduplay.core.ai_tool_payloads import safe_calculate
        except Exception:
            return
        try:
            expr = str(self.input.text() or "").strip()
        except Exception:
            expr = ""
        if not expr:
            try:
                self.result_label.setText("")
            except Exception:
                pass
            return
        try:
            ok, _clean, res = safe_calculate(expr)
        except Exception as e:
            ok, res = False, str(e)
        try:
            if ok:
                self.result_label.setText(f"= {res}")
            else:
                self.result_label.setText(str(res or ""))
        except Exception:
            pass

    def open_and_focus(self) -> str:
        try:
            self.input.clear()
            self.result_label.setText("")
        except Exception:
            pass
        self.show()
        self.raise_()
        self.activateWindow()
        try:
            self.input.setFocus()
        except Exception:
            pass
        if self.exec() == QDialog.Accepted:
            try:
                self._expression = str(self.input.text() or "").strip()
            except Exception:
                self._expression = ""
            return self._expression
        return ""

    def get_expression(self) -> str:
        return str(getattr(self, "_expression", "") or "").strip()
