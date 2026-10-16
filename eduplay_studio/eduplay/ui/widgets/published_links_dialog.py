"""Published links manager - xem/gia han/xoa cac link do may nay xuat ban.

Mo tu man hinh Duyet du an (nut "Links"). Chi liet ke entry co
owner_device_id trung voi may nay de khong cham vao bai cua may khac.
"""

from datetime import datetime

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QAbstractItemView, QHeaderView,
)


class PublishedLinksDialog(QDialog):
    """Dialog quan ly link da xuat ban cua may nay."""

    def __init__(self, settings_manager=None, parent=None):
        super().__init__(parent)
        if settings_manager is None:
            try:
                from eduplay.core.settings_manager import SettingsManager

                settings_manager = SettingsManager()
            except Exception:
                settings_manager = None
        self.settings_manager = settings_manager
        self._items = []
        try:
            self.setWindowTitle(self._t("links.title", "Published links"))
        except Exception:
            self.setWindowTitle("Published links")
        try:
            self.setModal(True)
        except Exception:
            pass
        try:
            self.resize(860, 520)
        except Exception:
            pass
        self._build_ui()
        try:
            self._apply_theme()
        except Exception:
            pass
        self.refresh_links()

    def _theme(self) -> str:
        try:
            if self.settings_manager is not None:
                t = str(self.settings_manager.get_theme() or "").strip().lower()
                if t in ("dark", "light"):
                    return t
        except Exception:
            pass
        return "dark"

    def _apply_theme(self):
        theme = self._theme()
        if theme == "light":
            dlg_bg = "#FFFFFF"
            text = "#0F1728"
            subtle = "#667085"
            table_bg = "#FFFFFF"
            header_bg = "#F2F4F7"
            grid = "#E2E8F0"
            sel_bg = "#7F56D9"
            sel_text = "#FFFFFF"
            btn_bg = "#F3F4F6"
            btn_border = "#D0D5DD"
            btn_text = "#111827"
            btn_hover = "#E5E7EB"
            btn_pressed = "#D5DBE5"
            input_bg = "#FFFFFF"
            input_border = "#D0D5DD"
            accent = "#7F56D9"
        else:
            dlg_bg = "#0B0E14"
            text = "#EDEEF3"
            subtle = "#9AA3B2"
            table_bg = "#111827"
            header_bg = "#1B1F2A"
            grid = "#2A2F3A"
            sel_bg = "#7F56D9"
            sel_text = "#FFFFFF"
            btn_bg = "#1B1F2A"
            btn_border = "#2A2F3A"
            btn_text = "#EDEEF3"
            btn_hover = "#222739"
            btn_pressed = "#2B3345"
            input_bg = "#111827"
            input_border = "#374151"
            accent = "#7F56D9"
        self.setStyleSheet(
            f"""
            QDialog {{
                background-color: {dlg_bg};
                color: {text};
            }}
            QLabel {{
                color: {text};
                background: transparent;
            }}
            QTableWidget {{
                background-color: {table_bg};
                color: {text};
                gridline-color: {grid};
                border: 1px solid {grid};
                border-radius: 8px;
                selection-background-color: {sel_bg};
                selection-color: {sel_text};
            }}
            QTableWidget::item:selected {{
                background-color: {sel_bg};
                color: {sel_text};
            }}
            QHeaderView::section {{
                background-color: {header_bg};
                color: {text};
                border: none;
                border-bottom: 1px solid {grid};
                padding: 8px;
                font-weight: 700;
            }}
            QTableCornerButton::section {{
                background-color: {header_bg};
                border: none;
            }}
            QLineEdit {{
                background-color: {input_bg};
                color: {text};
                border: 1px solid {input_border};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {accent};
            }}
            QLineEdit:hover {{
                border: 1px solid {accent};
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_text};
                border: 1px solid {btn_border};
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
                border-color: {accent};
            }}
            QPushButton:pressed {{
                background-color: {btn_pressed};
                border-color: {accent};
            }}
            QPushButton:disabled {{
                color: {subtle};
            }}
            """
        )

    def _lang(self) -> str:
        try:
            if self.settings_manager is not None:
                return self.settings_manager.get_language() or "en"
        except Exception:
            pass
        return "en"

    def _t(self, key: str, fallback: str, **kwargs) -> str:
        try:
            from eduplay.core.i18n import I18n

            value = I18n.t(key, self._lang(), **kwargs)
            if isinstance(value, str) and value:
                try:
                    return value.format(**kwargs) if kwargs else value
                except Exception:
                    return value
        except Exception:
            pass
        try:
            return fallback.format(**kwargs) if kwargs else fallback
        except Exception:
            return fallback

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        top = QHBoxLayout()
        self.status_label = QLabel(self._t("links.loading", "Loading..."))
        self.status_label.setWordWrap(True)
        top.addWidget(self.status_label, 1)
        self.refresh_btn = QPushButton(self._t("links.refresh", "Refresh"))
        try:
            self.refresh_btn.clicked.connect(self.refresh_links)
        except Exception:
            pass
        top.addWidget(self.refresh_btn)
        layout.addLayout(top)

        self.search_input = QLineEdit()
        try:
            self.search_input.setPlaceholderText(self._t("links.search_placeholder", "Tìm theo tên / link / máy..."))
            self.search_input.setClearButtonEnabled(True)
            self.search_input.textChanged.connect(self._on_search_changed)
        except Exception:
            pass
        layout.addWidget(self.search_input)

        self.table = QTableWidget(0, 5)
        try:
            self.table.setHorizontalHeaderLabels([
                self._t("links.col_name", "Name"),
                self._t("links.col_machine", "Machine"),
                self._t("links.col_link", "Link"),
                self._t("links.col_expiry", "Expires"),
                self._t("links.col_actions", "Actions"),
            ])
        except Exception:
            pass
        try:
            self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.table.setSelectionMode(QAbstractItemView.SingleSelection)
            self.table.verticalHeader().setVisible(False)
            self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
            self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
            self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        except Exception:
            pass
        layout.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        bottom.addStretch()
        self.close_btn = QPushButton(self._t("links.close", "Close"))
        try:
            self.close_btn.clicked.connect(self.accept)
        except Exception:
            pass
        bottom.addWidget(self.close_btn)
        layout.addLayout(bottom)

    def _expiry_text(self, item: dict) -> str:
        try:
            expires = int(item.get("expires_at") or 0)
        except Exception:
            expires = 0
        if not expires:
            return self._t("links.no_expiry", "—")
        try:
            day = datetime.fromtimestamp(expires).strftime("%d/%m/%Y")
        except Exception:
            day = ""
        try:
            expired = bool(item.get("expired"))
            days_left = item.get("days_left")
        except Exception:
            expired, days_left = False, None
        if expired:
            return self._t("links.expired", "Expired") + (f" ({day})" if day else "")
        if isinstance(days_left, int):
            return self._t("links.days_left", "Còn {n} ngày ({day})", n=days_left, day=day)
        return day or self._t("links.no_expiry", "—")

    def refresh_links(self):
        try:
            self.status_label.setText(self._t("links.loading", "Loading..."))
        except Exception:
            pass
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
        except Exception:
            pass
        items = []
        error = ""
        try:
            from eduplay.core.export_service import ExportService

            svc = ExportService()
            try:
                device_id = svc._get_publish_device_id()
            except Exception:
                device_id = ""
            res = svc.list_published_games(ExportService.DATABASE_URL, device_id=device_id, only_mine=True)
            if isinstance(res, dict):
                items = list(res.get("items") or [])
                error = str(res.get("error") or "")
        except Exception as e:
            try:
                error = str(e)
            except Exception:
                error = "error"
        try:
            QApplication.restoreOverrideCursor()
        except Exception:
            pass
        self._items = items
        self._render(items, error)

    def _on_search_changed(self, _text: str = ""):
        try:
            self._render(list(self._items or []))
        except Exception:
            pass

    def _machine_label(self, item: dict) -> str:
        try:
            label = str(item.get("owner_device_name") or "").strip()
            if label:
                return label
        except Exception:
            pass
        try:
            dev = str(item.get("owner_device_id") or "").strip()
            if dev.startswith("dev_") and len(dev) > 10:
                return "…" + dev[-6:]
            return dev
        except Exception:
            return ""

    def _render(self, items, error: str = ""):
        try:
            self.table.setRowCount(0)
        except Exception:
            pass
        if error and not items:
            try:
                self.status_label.setText(self._t("links.error", "Không tải được danh sách link: {error}", error=error))
            except Exception:
                pass
            return
        if not items:
            try:
                self.status_label.setText(self._t("links.empty", "Máy này chưa xuất bản link nào."))
            except Exception:
                pass
            return
        try:
            query = str(self.search_input.text() or "").strip().lower() if hasattr(self, "search_input") else ""
        except Exception:
            query = ""
        shown = 0
        for item in items:
            try:
                if query:
                    hay = " ".join([
                        str(item.get("name") or ""),
                        str(item.get("play_link") or ""),
                        str(item.get("owner_device_name") or ""),
                        str(item.get("key") or ""),
                    ]).lower()
                    if query not in hay:
                        continue
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(str(item.get("name") or "")))
                self.table.setItem(row, 1, QTableWidgetItem(self._machine_label(item)))
                self.table.setItem(row, 2, QTableWidgetItem(str(item.get("play_link") or "")))
                self.table.setItem(row, 3, QTableWidgetItem(self._expiry_text(item)))
                cell = self._action_cell(dict(item))
                self.table.setCellWidget(row, 4, cell)
                shown += 1
            except Exception:
                continue
        try:
            if query:
                self.status_label.setText(self._t("links.count", "{n} link của máy này", n=shown))
            else:
                self.status_label.setText(self._t("links.count", "{n} link của máy này", n=len(items)))
        except Exception:
            pass

    def _small_button(self, text: str):
        btn = QPushButton(text)
        try:
            btn.setStyleSheet("QPushButton { padding: 4px 10px; border-radius: 6px; }")
        except Exception:
            pass
        return btn

    def _action_cell(self, item: dict):
        from PySide6.QtWidgets import QWidget

        box = QWidget()
        lay = QHBoxLayout(box)
        try:
            lay.setContentsMargins(2, 2, 2, 2)
            lay.setSpacing(4)
        except Exception:
            pass
        copy_btn = self._small_button(self._t("links.copy", "Copy"))
        open_btn = self._small_button(self._t("links.open", "Open"))
        renew_btn = self._small_button(self._t("links.renew", "Renew"))
        del_btn = self._small_button(self._t("links.delete", "Delete"))

        def _copy():
            try:
                QApplication.clipboard().setText(str(item.get("play_link") or ""))
                self.status_label.setText(self._t("links.copied", "Đã copy link."))
            except Exception:
                pass

        def _open():
            try:
                QDesktopServices.openUrl(QUrl(str(item.get("play_link") or "")))
            except Exception:
                pass

        def _renew():
            key = str(item.get("key") or "")
            try:
                QApplication.setOverrideCursor(Qt.WaitCursor)
            except Exception:
                pass
            ok, err, new_exp = False, "", 0
            try:
                from eduplay.core.export_service import ExportService

                res = ExportService().renew_published_game(key, ExportService.DATABASE_URL)
                ok = bool((res or {}).get("ok"))
                err = str((res or {}).get("error") or "")
                new_exp = int((res or {}).get("expires_at") or 0)
            except Exception as e:
                try:
                    err = str(e)
                except Exception:
                    err = "error"
            try:
                QApplication.restoreOverrideCursor()
            except Exception:
                pass
            if ok:
                try:
                    item["expires_at"] = new_exp
                    item["expired"] = False
                    from datetime import datetime as _dt

                    now_ts = int(_dt.now().timestamp())
                    item["days_left"] = max(0, int((new_exp - now_ts) // 86400))
                except Exception:
                    pass
                self.status_label.setText(self._t("links.renewed", "Đã gia hạn thêm 15 ngày."))
                self._render(list(self._items or []))
            else:
                self.status_label.setText(self._t("links.error", "Không tải được danh sách link: {error}", error=err))

        def _delete():
            key = str(item.get("key") or "")
            name = str(item.get("name") or key)
            try:
                ans = QMessageBox.question(
                    self,
                    self._t("links.confirm_delete_title", "Xóa link?"),
                    self._t("links.confirm_delete_message", 'Xóa link của "{name}"? Người khác đang mở link này sẽ không xem được nữa.', name=name),
                )
            except Exception:
                ans = QMessageBox.Yes
            if ans != QMessageBox.Yes:
                return
            try:
                QApplication.setOverrideCursor(Qt.WaitCursor)
            except Exception:
                pass
            ok, err = False, ""
            try:
                from eduplay.core.export_service import ExportService

                res = ExportService().delete_published_game(key, ExportService.DATABASE_URL)
                ok = bool((res or {}).get("ok"))
                err = str((res or {}).get("error") or "")
            except Exception as e:
                try:
                    err = str(e)
                except Exception:
                    err = "error"
            try:
                QApplication.restoreOverrideCursor()
            except Exception:
                pass
            if ok:
                try:
                    self._items = [it for it in (self._items or []) if str(it.get("key") or "") != key]
                except Exception:
                    pass
                self.status_label.setText(self._t("links.deleted", "Đã xóa link."))
                self._render(list(self._items or []))
            else:
                self.status_label.setText(self._t("links.error", "Không tải được danh sách link: {error}", error=err))

        try:
            copy_btn.clicked.connect(_copy)
            open_btn.clicked.connect(_open)
            renew_btn.clicked.connect(_renew)
            del_btn.clicked.connect(_delete)
        except Exception:
            pass
        for b in (copy_btn, open_btn, renew_btn, del_btn):
            lay.addWidget(b)
        return box
