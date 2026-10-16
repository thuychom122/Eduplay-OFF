"""Shared Yes/No confirmation dialog with i18n button labels.

Qt's standard QMessageBox Yes/No buttons always render in English ("Yes"/"No")
because the app does not ship Qt locale catalogs. Every user-facing
confirmation must go through ask_confirm() so the buttons follow the app
language (common.yes / common.no).
"""

from PySide6.QtWidgets import QMessageBox

from eduplay.core.i18n import I18n


def _button_texts(lang: str):
    try:
        yes_text = I18n.t("common.yes", lang)
    except Exception:
        yes_text = ""
    try:
        no_text = I18n.t("common.no", lang)
    except Exception:
        no_text = ""
    if not yes_text or yes_text == "common.yes":
        yes_text = "Có" if str(lang or "").lower().startswith("vi") else "Yes"
    if not no_text or no_text == "common.no":
        no_text = "Không" if str(lang or "").lower().startswith("vi") else "No"
    return yes_text, no_text


def ask_confirm(parent, title: str, message: str, lang: str = "en", default_no: bool = True) -> bool:
    """Show a Yes/No question dialog. Returns True when the user picks Yes."""
    yes_text, no_text = _button_texts(lang)
    box = QMessageBox(parent)
    try:
        box.setWindowTitle(str(title or ""))
    except Exception:
        pass
    try:
        box.setText(str(message or ""))
    except Exception:
        pass
    try:
        box.setIcon(QMessageBox.Question)
    except Exception:
        pass
    try:
        yes_btn = box.addButton(yes_text, QMessageBox.YesRole)
    except Exception:
        yes_btn = None
    try:
        no_btn = box.addButton(no_text, QMessageBox.NoRole)
    except Exception:
        no_btn = None
    try:
        box.setDefaultButton(no_btn if default_no else yes_btn)
    except Exception:
        pass
    try:
        box.exec()
    except Exception:
        return False
    try:
        return box.clickedButton() == yes_btn
    except Exception:
        return False
