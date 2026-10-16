from __future__ import annotations

from typing import List

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QApplication
from PySide6.QtGui import QIcon


_LIGHT_FILE_DIALOG_STYLE = """
    QFileDialog, QDialog, QWidget {
        background-color: #FFFFFF;
        color: #101828;
    }
    QLabel { color: #101828; }
    QLineEdit, QListView, QTreeView, QAbstractItemView, QComboBox {
        background-color: #FFFFFF;
        color: #101828;
        selection-background-color: #7F56D9;
        selection-color: #FFFFFF;
    }
    QHeaderView::section {
        background-color: #F2F4F7;
        color: #101828;
        padding: 4px 8px;
        border: none;
    }
    QPushButton {
        background-color: #F2F4F7;
        color: #101828;
        border: 1px solid #D0D5DD;
        border-radius: 6px;
        padding: 6px 10px;
    }
    QPushButton:hover { background-color: #EAECF0; }
"""

_DEFAULT_FILE_DIALOG_STYLE = _LIGHT_FILE_DIALOG_STYLE

_DARK_FILE_DIALOG_STYLE = """
    QFileDialog, QDialog, QWidget {
        background-color: #1E1E24;
        color: #E0E0E0;
    }
    QLabel { color: #E0E0E0; }
    QLineEdit, QListView, QTreeView, QAbstractItemView, QComboBox {
        background-color: #25252B;
        color: #E0E0E0;
        selection-background-color: #7F56D9;
        selection-color: #FFFFFF;
    }
    QHeaderView::section {
        background-color: #2A2A30;
        color: #E0E0E0;
        padding: 4px 8px;
        border: none;
    }
    QPushButton {
        background-color: #2A2A30;
        color: #E0E0E0;
        border: 1px solid #3A3A40;
        border-radius: 6px;
        padding: 6px 10px;
    }
    QPushButton:hover { background-color: #3A3A40; }
"""

# Suggestion (filename completer) popup is a top-level QListView, so the dialog
# stylesheet does not reach it — style it explicitly per theme.
_LIGHT_POPUP_STYLE = """
    QListView {
        background-color: #FFFFFF;
        color: #101828;
        border: 1px solid #D0D5DD;
        border-radius: 6px;
        padding: 4px;
        outline: none;
    }
    QListView::item { padding: 6px 10px; border: none; }
    QListView::item:selected {
        background-color: #7F56D9;
        color: #FFFFFF;
    }
    QListView::item:hover { background-color: #F2F4F7; }
"""
_DARK_POPUP_STYLE = """
    QListView {
        background-color: #25252B;
        color: #E0E0E0;
        border: 1px solid #3A3A40;
        border-radius: 6px;
        padding: 4px;
        outline: none;
    }
    QListView::item { padding: 6px 10px; border: none; }
    QListView::item:selected {
        background-color: #7F56D9;
        color: #FFFFFF;
    }
    QListView::item:hover { background-color: #2A2A30; }
"""


def _resolve_dialog_theme(theme=None) -> str:
    if theme in ("light", "dark"):
        return theme
    try:
        from eduplay.core.settings_manager import SettingsManager
        t = SettingsManager().get_theme() or "light"
        return "dark" if str(t).lower() == "dark" else "light"
    except Exception:
        return "light"


def _style_filename_completer_popups(dlg, light: bool) -> None:
    """Theme the file-name suggestion popup (top-level QListView)."""
    try:
        from PySide6.QtWidgets import QLineEdit, QComboBox
    except Exception:
        return
    style = _LIGHT_POPUP_STYLE if light else _DARK_POPUP_STYLE
    try:
        widgets = list(dlg.findChildren(QLineEdit)) + list(dlg.findChildren(QComboBox))
    except Exception:
        return
    for w in widgets:
        try:
            comp = w.completer()
        except Exception:
            comp = None
        if comp is None:
            continue
        try:
            popup = comp.popup()
        except Exception:
            continue
        if popup is None:
            continue
        try:
            popup.setStyleSheet(style)
        except Exception:
            continue


def _create_dialog(
    parent,
    title: str,
    file_mode: QFileDialog.FileMode,
    accept_mode: QFileDialog.AcceptMode,
    directory: str = "",
    name_filter: str = "",
    theme: str | None = None,
) -> QFileDialog:
    dlg = QFileDialog(parent, title, directory)
    dlg.setFileMode(file_mode)
    dlg.setAcceptMode(accept_mode)
    try:
        icon = None
        try:
            icon = parent.windowIcon() if parent else None
        except Exception:
            icon = None
        try:
            if icon is None or icon.isNull():
                icon = QApplication.windowIcon()
        except Exception:
            pass
        try:
            if icon is None or icon.isNull():
                base = Path(__file__).resolve().parents[1]
                ico = base / "resources" / "icons" / "icon.ico"
                png = base / "resources" / "icons" / "icon.png"
                if ico.exists():
                    icon = QIcon(str(ico))
                elif png.exists():
                    icon = QIcon(str(png))
        except Exception:
            pass
        if icon is not None and not icon.isNull():
            dlg.setWindowIcon(icon)
    except Exception:
        pass
    try:
        if name_filter:
            dlg.setNameFilter(name_filter)
    except Exception:
        pass
    try:
        dlg.setOption(QFileDialog.DontUseNativeDialog, True)
    except Exception:
        pass
    try:
        dlg.setWindowModality(Qt.ApplicationModal)
    except Exception:
        pass
    try:
        _theme = _resolve_dialog_theme(theme)
    except Exception:
        _theme = "light"
    try:
        dlg.setStyleSheet(_LIGHT_FILE_DIALOG_STYLE if _theme != "dark" else _DARK_FILE_DIALOG_STYLE)
    except Exception:
        pass
    try:
        _style_filename_completer_popups(dlg, _theme != "dark")
    except Exception:
        pass
    return dlg


def _resolve_initial_directory(directory: str = "") -> str:
    """Resolve initial directory for dialogs, handling OneDrive correctly."""
    if directory and str(directory).strip():
        try:
            from eduplay.core.path_resolver import PathResolver
            # Try to resolve via PathResolver (handles OneDrive, long path, etc.)
            p = PathResolver.resolve_user_file_any(directory)
            if p and p.exists():
                return str(p if p.is_dir() else p.parent)
            # If directory is a folder path that exists, return it
            norm = PathResolver.normalize_user_path(directory)
            if norm:
                cand = PathResolver.resolve_user_file_any(norm)
                if cand:
                    return str(cand if cand.is_dir() else cand.parent)
                # Fallback to normalized path if it exists
                if Path(norm).exists():
                    return str(Path(norm) if Path(norm).is_dir() else Path(norm).parent)
        except Exception:
            pass
        return str(directory)
    # No directory provided: default to Documents/EduPlay via PathResolver (OneDrive-aware)
    try:
        from eduplay.core.path_resolver import PathResolver
        docs = PathResolver.resolve_documents()
        # Prefer EduPlay Projects folder if exists
        eduplay = docs / "EduPlay"
        projects = eduplay / "Projects"
        if projects.exists():
            return str(projects)
        if eduplay.exists():
            return str(eduplay)
        return str(docs)
    except Exception:
        try:
            return str(Path.home() / "Documents")
        except Exception:
            return ""


def get_open_file_name(parent, title: str, directory: str = "", name_filter: str = "") -> str:
    directory = _resolve_initial_directory(directory)
    dlg = _create_dialog(
        parent=parent,
        title=title,
        file_mode=QFileDialog.ExistingFile,
        accept_mode=QFileDialog.AcceptOpen,
        directory=directory,
        name_filter=name_filter,
    )
    if dlg.exec():
        sel = dlg.selectedFiles()
        raw = sel[0] if sel else ""
        # Normalize returned path via PathResolver (handles OneDrive, 8.3, long path)
        try:
            from eduplay.core.path_resolver import PathResolver
            resolved = PathResolver.resolve_user_file(raw)
            if resolved:
                return str(resolved)
            # Also handle directory case
            resolved_any = PathResolver.resolve_user_file_any(raw)
            if resolved_any:
                return str(resolved_any)
        except Exception:
            pass
        return raw
    return ""


def get_open_file_names(parent, title: str, directory: str = "", name_filter: str = "") -> List[str]:
    directory = _resolve_initial_directory(directory)
    dlg = _create_dialog(
        parent=parent,
        title=title,
        file_mode=QFileDialog.ExistingFiles,
        accept_mode=QFileDialog.AcceptOpen,
        directory=directory,
        name_filter=name_filter,
    )
    if dlg.exec():
        raw_list = list(dlg.selectedFiles() or [])
        # Normalize each via PathResolver
        try:
            from eduplay.core.path_resolver import PathResolver
            out = []
            for raw in raw_list:
                resolved = PathResolver.resolve_user_file(raw)
                if resolved:
                    out.append(str(resolved))
                else:
                    resolved_any = PathResolver.resolve_user_file_any(raw)
                    out.append(str(resolved_any) if resolved_any else raw)
            return out
        except Exception:
            return raw_list
    return []


def get_save_file_name(parent, title: str, directory: str = "", name_filter: str = "") -> str:
    """OneDrive-aware Save dialog. Returns normalized path."""
    directory = _resolve_initial_directory(directory)
    dlg = _create_dialog(
        parent=parent,
        title=title,
        file_mode=QFileDialog.AnyFile,
        accept_mode=QFileDialog.AcceptSave,
        directory=directory,
        name_filter=name_filter,
    )
    if dlg.exec():
        sel = dlg.selectedFiles()
        raw = sel[0] if sel else ""
        if not raw:
            return ""
        # Normalize via PathResolver (handles OneDrive, file://, %20)
        try:
            from eduplay.core.path_resolver import PathResolver
            # For save, we want normalized path even if file doesn't exist yet
            norm = PathResolver.normalize_user_path(raw)
            if norm:
                # Try to resolve parent via resolver (handles OneDrive)
                parent_p = PathResolver.resolve_user_file_any(str(Path(norm).parent))
                if parent_p and parent_p.exists():
                    return str(parent_p / Path(norm).name)
                return norm
        except Exception:
            pass
        return raw
    return ""


def get_existing_directory(parent, title: str, directory: str = "") -> str:
    """OneDrive-aware Directory picker. Returns normalized existing dir."""
    directory = _resolve_initial_directory(directory)
    dlg = _create_dialog(
        parent=parent,
        title=title,
        file_mode=QFileDialog.Directory,
        accept_mode=QFileDialog.AcceptOpen,
        directory=directory,
    )
    try:
        dlg.setOption(QFileDialog.ShowDirsOnly, True)
    except Exception:
        pass
    if dlg.exec():
        sel = dlg.selectedFiles()
        raw = sel[0] if sel else ""
        if not raw:
            return ""
        try:
            from eduplay.core.path_resolver import PathResolver
            resolved = PathResolver.resolve_user_file_any(raw)
            if resolved and resolved.exists():
                return str(resolved)
            norm = PathResolver.normalize_user_path(raw)
            if norm:
                cand = PathResolver.resolve_user_file_any(norm)
                if cand and cand.exists():
                    return str(cand)
                if Path(norm).exists():
                    return norm
        except Exception:
            pass
        return raw
    return ""
