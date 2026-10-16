"""Test cho 6 tinh nang phien nay: auto-renew, backup, viewer 404,
confirm publish, links dialog (may + tim kiem), undo mo rong."""

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _make_pm(testcase, tmpdir, name="S6 Game"):
    from eduplay.core.export_service import ExportService
    from eduplay.core.project_manager import ProjectManager

    orig_export = ExportService.export_to_html
    ExportService.export_to_html = lambda self, *a, **k: True
    testcase.addCleanup(setattr, ExportService, "export_to_html", orig_export)

    pm = ProjectManager()
    pm.projects_dir = Path(tmpdir) / "Projects"
    pm.ensure_projects_directory()
    created = pm.create_project(name, "desc", "quiz_classic")
    return pm, created


class TestAutoRenew(unittest.TestCase):
    def test_renews_only_soon_and_expired(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        now = int(time.time())
        items = [
            {"key": "fresh", "name": "Fresh", "expires_at": now + 86400 * 10},
            {"key": "soon", "name": "Soon", "expires_at": now + 86400 * 2},
            {"key": "old", "name": "Old", "expires_at": now - 100},
            {"key": "unknown", "name": "Unknown", "expires_at": 0},
        ]
        renewed_keys = []

        def _fake_renew(key, database_url=""):
            renewed_keys.append(key)
            return {"ok": True, "expires_at": now + 86400 * 15, "error": ""}

        with patch.object(
            ExportService, "list_published_games",
            return_value={"ok": True, "items": items, "error": ""},
        ), patch.object(ExportService, "renew_published_game", side_effect=_fake_renew):
            res = svc.auto_renew_soon_expiring("https://demo.firebaseio.com", threshold_days=3)
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("checked"), 4)
        self.assertEqual(sorted(r["key"] for r in res.get("renewed")), ["old", "soon"])

    def test_list_failure_is_safe(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        with patch.object(
            ExportService, "list_published_games",
            return_value={"ok": False, "items": [], "error": "net down"},
        ):
            res = svc.auto_renew_soon_expiring("https://demo.firebaseio.com")
        self.assertFalse(res.get("ok"))
        self.assertEqual(res.get("renewed"), [])


class TestBackup(unittest.TestCase):
    def test_backup_written_and_rotated(self):
        with tempfile.TemporaryDirectory() as tmp:
            pm, created = _make_pm(self, tmp)
            pid = created["id"]
            pm.BACKUP_MIN_INTERVAL_SEC = 0
            for i in range(7):
                cur = pm.get_current_project()
                cur["description"] = f"edit {i}"
                self.assertTrue(pm.save_project(cur))
            backups = sorted((pm.projects_dir / pid / "backups").glob(f"{pid}_*.eduplay"))
            self.assertEqual(len(backups), pm.BACKUP_KEEP)
            # throttled: luu lien tiep khong tao them
            pm.BACKUP_MIN_INTERVAL_SEC = 3600
            cur = pm.get_current_project()
            cur["description"] = "throttled"
            pm.save_project(cur)
            backups2 = list((pm.projects_dir / pid / "backups").glob(f"{pid}_*.eduplay"))
            self.assertEqual(len(backups2), pm.BACKUP_KEEP)

    def test_corrupt_file_restored_on_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            pm, created = _make_pm(self, tmp)
            pid = created["id"]
            pm.BACKUP_MIN_INTERVAL_SEC = 0
            cur = pm.get_current_project()
            cur["questions"] = [{"id": "q1", "question": "Q?"}]
            pm.save_project(cur)
            # save lan 2 de backup giu ban CO cau hoi (backup luu trang thai truoc-save)
            pm.save_project(pm.get_current_project())
            # lam hong file chinh
            (pm.projects_dir / pid / f"{pid}.eduplay").write_text("{hong json", encoding="utf-8")
            loaded = pm.load_project(pid)
            self.assertIsNotNone(loaded)
            self.assertEqual(len(loaded.get("questions") or []), 1)
            info = pm.pop_last_restore_info()
            self.assertIsNotNone(info)
            self.assertEqual(info.get("id"), pid)
            self.assertIsNone(pm.pop_last_restore_info())

    def test_corrupt_file_restored_in_listing(self):
        with tempfile.TemporaryDirectory() as tmp:
            pm, created = _make_pm(self, tmp)
            pid = created["id"]
            pm.BACKUP_MIN_INTERVAL_SEC = 0
            pm.save_project(pm.get_current_project())
            (pm.projects_dir / pid / f"{pid}.eduplay").write_text("broken{{", encoding="utf-8")
            projects = pm.get_all_projects()
            self.assertEqual(len(projects), 1)
            self.assertIn(created["name"], pm.pop_restored_names())
            self.assertEqual(pm.pop_restored_names(), [])


class TestUndoExtended(unittest.TestCase):
    def test_rename_and_undo(self):
        with tempfile.TemporaryDirectory() as tmp:
            pm, created = _make_pm(self, tmp, "Old Name")
            pid = created["id"]
            out = pm.rename_project(pid, "New Name")
            self.assertEqual(out.get("name"), "New Name")
            self.assertTrue(pm.can_undo())
            pm.undo()
            self.assertEqual(pm.get_current_project().get("name"), "Old Name")
            pm.redo()
            self.assertEqual(pm.get_current_project().get("name"), "New Name")
            with self.assertRaises(ValueError):
                pm.rename_project(pid, "  ")
            pm.create_project("Taken", "d", "quiz_classic", on_duplicate="suffix")
            with self.assertRaises(ValueError):
                pm.rename_project(pid, "taken")

    def test_game_config_and_undo(self):
        with tempfile.TemporaryDirectory() as tmp:
            pm, created = _make_pm(self, tmp)
            before = dict(pm.get_current_project().get("game_config") or {})
            cfg = dict(before)
            cfg["time_per_question"] = 99
            pm.update_game_config(cfg)
            self.assertEqual(pm.get_current_project()["game_config"].get("time_per_question"), 99)
            pm.undo()
            self.assertEqual(
                pm.get_current_project()["game_config"].get("time_per_question"),
                before.get("time_per_question"),
            )
            pm.redo()
            self.assertEqual(pm.get_current_project()["game_config"].get("time_per_question"), 99)

    def test_list_snapshot_keeps_other_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            pm, created = _make_pm(self, tmp, "Keep Me")
            pm.push_undo_snapshot([{"id": "q1", "question": "Q"}])
            pm.undo()
            # undo list cu van giu ten (khong bi xoa nhu ban dau)
            self.assertEqual(pm.get_current_project().get("name"), "Keep Me")


class TestConfirmPublishDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls._app = QApplication.instance() or QApplication([])

    def _make_window(self):
        from PySide6.QtWidgets import QMainWindow

        from eduplay.ui.main_window import MainWindow

        window = MainWindow.__new__(MainWindow)
        QMainWindow.__init__(window)

        class _StubSettings:
            def get_language(self):
                return "vi"

            def get_theme(self):
                return "dark"

            def get(self, key, default=None):
                return default

        window.settings_manager = _StubSettings()
        return window

    def _preview(self, **over):
        base = {
            "success": True, "phase": "preview", "tmp_dir": "t", "name": "Bai Test",
            "html_path": "x.html", "html_bytes": 204800, "question_count": 5,
            "preview": {"key": "bai-test", "play_link": "https://game.eduplay-studio.io.vn/bai-test",
                        "reused": True, "conflict": False, "base_slug": "bai-test", "resolved": True},
        }
        base.update(over)
        return base

    def test_accept_returns_true(self):
        from PySide6.QtWidgets import QDialog

        window = self._make_window()
        with patch.object(QDialog, "exec", return_value=QDialog.Accepted):
            self.assertTrue(window._confirm_publish(self._preview()))

    def test_reject_returns_false(self):
        from PySide6.QtWidgets import QDialog

        window = self._make_window()
        with patch.object(QDialog, "exec", return_value=QDialog.Rejected):
            self.assertFalse(window._confirm_publish(self._preview()))

    def test_conflict_preview_ok(self):
        from PySide6.QtWidgets import QDialog

        window = self._make_window()
        pv = dict(self._preview()["preview"])
        pv.update({"key": "bai-test-abc123", "reused": False, "conflict": True})
        with patch.object(QDialog, "exec", return_value=QDialog.Accepted):
            self.assertTrue(window._confirm_publish(self._preview(preview=pv)))


class TestLinksDialogSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls._app = QApplication.instance() or QApplication([])

    def test_machine_column_and_search(self):
        from eduplay.ui.widgets.published_links_dialog import PublishedLinksDialog

        items = [
            {"key": "toan-1", "name": "Toan 1", "play_link": "https://x/toan-1",
             "created_at": 1, "expires_at": 1799999999, "days_left": 9, "expired": False,
             "owner_device_name": "PC Lab", "owner_project_id": "a"},
            {"key": "van-2", "name": "Van 2", "play_link": "https://x/van-2",
             "created_at": 2, "expires_at": 1799999999, "days_left": 9, "expired": False,
             "owner_device_name": "", "owner_device_id": "dev_1234567890abcdef", "owner_project_id": "b"},
        ]
        with patch(
            "eduplay.core.export_service.ExportService.list_published_games",
            return_value={"ok": True, "items": list(items), "error": ""},
        ):
            dlg = PublishedLinksDialog(settings_manager=None, parent=None)
            self.assertEqual(dlg.table.columnCount(), 5)
            self.assertEqual(dlg.table.rowCount(), 2)
            self.assertEqual(dlg.table.item(0, 1).text(), "PC Lab")
            machine_short = dlg.table.item(1, 1).text()
            self.assertTrue(machine_short, "may khong ten phai hien id rut gon")
            dlg.search_input.setText("toan")
            self.assertEqual(dlg.table.rowCount(), 1)
            dlg.search_input.setText("pc lab")
            self.assertEqual(dlg.table.rowCount(), 1)
            dlg.search_input.setText("khong-co")
            self.assertEqual(dlg.table.rowCount(), 0)


class TestViewerMissingPage(unittest.TestCase):
    def test_viewer_has_friendly_missing_page(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "eduplay", "resources", "firebase_hosting"))
        with open(os.path.join(base, "firebase_viewer.html"), encoding="utf-8") as f:
            html = f.read()
        for needle in (
            "renderMissingPage",
            "expires_at",
            "contactHint",
            "prettyNameFromSlug",
            "location.reload()",
        ):
            self.assertIn(needle, html)
        for lang_word in ("Đã copy link!", "Link copied!", "Lien copié", "Enlace copiado", "Link kopiert"):
            self.assertIn(lang_word, html)


class TestNewI18nKeys(unittest.TestCase):
    def test_all_new_keys_in_five_languages(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "eduplay", "resources", "i18n"))
        datas = {}
        for lang in ("en", "vi", "fr", "es", "de"):
            with open(os.path.join(base, f"{lang}.json"), "r", encoding="utf-8") as f:
                datas[lang] = json.load(f)
        for key in (
            "publish.autorenew_title",
            "publish.autorenew_message",
            "publish.confirm_title",
            "publish.confirm_ok",
            "publish.row_name",
            "publish.row_questions",
            "publish.row_size",
            "publish.row_link",
            "publish.row_status",
            "publish.status_overwrite",
            "publish.status_new",
            "publish.status_conflict",
            "publish.status_unknown",
            "publish.expiry_note",
            "project.backup_restored_title",
            "project.backup_restored_message",
            "project.backup_restored_list",
            "links.col_machine",
            "links.search_placeholder",
            "help.sections.tips.title",
            "help.sections.tips.subtitle",
            "help.sections.tips.content",
        ):
            for lang in ("en", "vi", "fr", "es", "de"):
                self.assertIn(key, datas[lang], f"missing {key} in {lang}")

    def test_help_contents_mention_new_features(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "eduplay", "resources", "i18n"))
        with open(os.path.join(base, "vi.json"), "r", encoding="utf-8") as f:
            vi = json.load(f)
        preview = vi.get("help.sections.preview_export.content", "")
        self.assertIn("bảng xác nhận", preview)
        self.assertIn("tự gia hạn", preview)
        self.assertIn("Links", preview)
        create = vi.get("help.sections.create_project.content", "")
        self.assertIn("Ctrl+Z", create)
        self.assertIn("backup", create)
        edubot = vi.get("help.sections.edubot.content", "")
        self.assertIn("xóa bộ nhớ", edubot)
        tips = vi.get("help.sections.tips.content", "")
        self.assertIn("Ctrl+Z", tips)
        self.assertIn("crash.log", tips)


class TestHelpDialogSections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls._app = QApplication.instance() or QApplication([])

    def _collect_help_rows(self):
        """Tra ve (ds muc that, ds nhom) cua danh sach ben trai."""
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QDialog, QMainWindow

        from eduplay.ui.main_window import MainWindow

        window = MainWindow.__new__(MainWindow)
        QMainWindow.__init__(window)

        class _StubSettings:
            def get_language(self):
                return "vi"

        window.settings_manager = _StubSettings()
        items = []

        def _capture(self, item):
            items.append(item)

        with patch.object(QDialog, "exec", return_value=QDialog.Accepted):
            with patch("PySide6.QtWidgets.QListWidget.addItem", new=_capture):
                window.show_help()

        real, groups = [], []
        try:
            from eduplay.ui.widgets.help_nav_delegate import GROUP_ROLE
        except Exception:
            GROUP_ROLE = Qt.ItemDataRole.UserRole + 1
        for it in items:
            try:
                is_group = str(it.data(GROUP_ROLE) or "") == "group"
            except Exception:
                is_group = False
            (groups if is_group else real).append(str(it.text()))
        return real, groups

    def test_help_dialog_is_grouped_by_task(self):
        """Tro giup sap xep theo VIEC lam, co nhom, khong phai danh sach tinh nang."""
        real, groups = self._collect_help_rows()

        self.assertEqual(len(real), 12, f"phai co 12 muc that: {real}")
        self.assertGreaterEqual(len(groups), 4, "phai co nhom de nguoi dung quet lau hon")
        self.assertEqual(len(groups), len(set(groups)), "ten nhom phai la duy nhat")
        # Moc la muc "Bắt đầu nhanh" chu khong phai muc trung gian
        self.assertIn("Bắt đầu nhanh", real)
        # Cac muc phai theo dung thu tu cong viec
        self.assertLess(real.index("Bắt đầu nhanh"), len(real) - 1)

    def test_help_groups_use_real_i18n_labels(self):
        real, groups = self._collect_help_rows()
        self.assertTrue(all(g.strip() for g in groups), f"nhom rong: {groups}")

    def test_help_content_has_no_broken_letters(self):
        """Catches artifacts like "[ó] 3 cách" left by a bad regex replace.

        Khi dùng re.sub, phần thay thế là chuỗi literal; nếu viết "[âa]" trong
        replacement thì nó bị ghi thẳng vào nội dung.
        """
        import json
        import re
        from pathlib import Path

        base = Path(__file__).resolve().parent.parent / "eduplay" / "resources" / "i18n"
        closed = re.compile(r"\[[^\[\]]{1,3}\]")
        unclosed = re.compile(r"\[[^\[\]<>\n]{1,3}(?=[<\s])")
        allowed = ("[...]", "[x+1]", "[Nội dung trợ giúp]")

        def _ok(fragment: str) -> bool:
            # "[Nội" la phan dau cua "[Nội dung trợ giúp]" hop le.
            return any(fragment == a or a.startswith(fragment) for a in allowed)

        for lang in ("vi", "en", "fr", "es", "de"):
            data = json.loads((base / f"{lang}.json").read_text(encoding="utf-8"))
            for key, value in data.items():
                if not key.startswith("help."):
                    continue
                text = str(value)
                for m in closed.finditer(text):
                    self.assertTrue(
                        _ok(m.group(0)),
                        f"{lang}:{key} con chuoi rac {m.group(0)!r}",
                    )
                for m in unclosed.finditer(text):
                    self.assertTrue(
                        _ok(m.group(0)),
                        f"{lang}:{key} con ngoac khong dong {m.group(0)!r}",
                    )

    def test_help_content_has_no_filler_headers(self):
        """Tieu de rong kieu 'Phan 1 - Gioi thieu' lam tai lieu doc nhu log thay doi."""
        import json
        from pathlib import Path

        base = Path(__file__).resolve().parent.parent / "eduplay" / "resources" / "i18n"
        filler = ("giới thiệu", "hướng dẫn chi tiết", "tính năng nâng cao")
        import re

        for lang in ("vi", "en", "fr", "es", "de"):
            data = json.loads((base / f"{lang}.json").read_text(encoding="utf-8"))
            for key, value in data.items():
                if not (key.startswith("help.sections.") and key.endswith(".content")):
                    continue
                low = str(value).lower()
                for name in filler:
                    self.assertNotIn(
                        f"phần 1 — {name}", low, f"{lang}:{key} con tieu de rong"
                    )
                    self.assertNotIn(
                        f"phần 2 — {name}", low, f"{lang}:{key} con tieu de rong"
                    )

    def test_help_content_uses_theme_tokens_not_hardcoded_hex(self):
        """Mau hex hardcode se chet khi doi sang theme toi."""
        import json
        from pathlib import Path
        import re

        base = Path(__file__).resolve().parent.parent / "eduplay" / "resources" / "i18n"
        shown = (
            "quickstart", "editor", "import", "media", "browse",
            "preview", "export", "powerpoint_addin", "edubot",
            "settings", "keyboard_shortcuts", "troubleshooting",
        )
        for lang in ("vi", "en", "fr", "es", "de"):
            data = json.loads((base / f"{lang}.json").read_text(encoding="utf-8"))
            for name in shown:
                key = f"help.sections.{name}.content"
                value = str(data.get(key) or "")
                self.assertTrue(value.strip(), f"{lang}:{key} rong")
                self.assertIsNone(
                    re.search(r"#[0-9A-Fa-f]{6}", value),
                    f"{lang}:{key} con mau hex hardcode",
                )
                self.assertIn("{{", value, f"{lang}:{key} chua dung token mau")

    def test_help_content_has_no_missing_glyph_emoji(self):
        """U+1F6DF (Ring buoy) khong co trong Segoe UI Emoji cua Windows -> o vuong.

        Chi kiem tra ky tu da bi chung minh la hong; cac emoji khac da hien
        dung nen khong cam doan vao chung.
        """
        import json
        from pathlib import Path

        base = Path(__file__).resolve().parent.parent / "eduplay" / "resources" / "i18n"
        broken = "\U0001F6DF"
        for lang in ("vi", "en", "fr", "es", "de"):
            data = json.loads((base / f"{lang}.json").read_text(encoding="utf-8"))
            for key, value in data.items():
                if not key.startswith("help.sections."):
                    continue
                self.assertNotIn(broken, str(value), f"{lang}:{key} dung emoji thieu glyph")

    def test_help_group_rows_use_custom_delegate(self):
        """QSS khong property selector cho item -> phai co delegate ve rieng."""
        from PySide6.QtWidgets import QListWidget, QStyleOptionViewItem, QDialog, QMainWindow

        from eduplay.ui.main_window import MainWindow
        from eduplay.ui.widgets.help_nav_delegate import HelpNavDelegate, GROUP_ROLE

        window = MainWindow.__new__(MainWindow)
        QMainWindow.__init__(window)

        class _StubSettings:
            def get_language(self):
                return "vi"

        window.settings_manager = _StubSettings()
        captured = {}

        def _fake_exec(self, *args, **kwargs):
            captured["dlg"] = self
            return QDialog.Accepted

        with patch.object(QDialog, "exec", new=_fake_exec):
            window.show_help()

        dlg = captured.get("dlg")
        self.assertIsNotNone(dlg)
        lists = dlg.findChildren(QListWidget)
        self.assertTrue(lists, "khong tim thay danh sach muc")
        nav = lists[0]
        delegate = nav.itemDelegateForColumn(0)
        self.assertIsInstance(delegate, HelpNavDelegate)

        group_row = None
        real_row = None
        for r in range(nav.count()):
            it = nav.item(r)
            if str(it.data(GROUP_ROLE) or "") == "group":
                group_row = group_row if group_row is not None else r
            elif real_row is None:
                real_row = r
        self.assertIsNotNone(group_row)
        self.assertIsNotNone(real_row)

        def _hint(row):
            idx = nav.model().index(row, 0)
            return delegate.sizeHint(QStyleOptionViewItem(), idx)

        # Dong nhom phai cao hon dong muc de tach kienh
        self.assertGreater(_hint(group_row).height(), _hint(real_row).height())

    def test_help_detail_title_keeps_text_next_to_icon(self):
        """setPixmap tren QLabel se XOA text nen phai tach icon + chu rieng."""
        from PySide6.QtWidgets import QDialog, QMainWindow, QLabel

        from eduplay.ui.main_window import MainWindow

        window = MainWindow.__new__(MainWindow)
        QMainWindow.__init__(window)

        class _StubSettings:
            def get_language(self):
                return "vi"

        window.settings_manager = _StubSettings()
        captured = {}

        def _fake_exec(self, *args, **kwargs):
            captured["dlg"] = self
            return QDialog.Accepted

        with patch.object(QDialog, "exec", new=_fake_exec):
            window.show_help()

        dlg = captured.get("dlg")
        self.assertIsNotNone(dlg, "khong bat duoc help dialog")
        texts = [
            str(lb.text()).strip()
            for lb in dlg.findChildren(QLabel)
            if str(lb.text()).strip()
        ]
        self.assertTrue(
            any(t in ("Bắt đầu nhanh", "Soạn & chỉnh câu hỏi", "Edubot (AI)") for t in texts),
            f"tieu de mat chu sau khi gan icon: {texts}",
        )

    def test_help_items_use_real_icons_not_emoji_text(self):
        """Emoji de trong text se bi o vuong khi font dang dung khong co glyph."""
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QDialog, QMainWindow

        from eduplay.ui.main_window import MainWindow

        window = MainWindow.__new__(MainWindow)
        QMainWindow.__init__(window)

        class _StubSettings:
            def get_language(self):
                return "vi"

        window.settings_manager = _StubSettings()
        items = []

        def _capture(self, item):
            items.append(item)

        with patch.object(QDialog, "exec", return_value=QDialog.Accepted):
            with patch("PySide6.QtWidgets.QListWidget.addItem", new=_capture):
                window.show_help()

        real = []
        try:
            from eduplay.ui.widgets.help_nav_delegate import GROUP_ROLE
        except Exception:
            GROUP_ROLE = Qt.ItemDataRole.UserRole + 1
        for it in items:
            try:
                if str(it.data(GROUP_ROLE) or "") == "group":
                    continue
            except Exception:
                pass
            real.append(it)

        self.assertEqual(len(real), 12)
        for it in real:
            text = str(it.text())
            self.assertTrue(text.strip())
            for ch in text:
                self.assertFalse(
                    ord(ch) > 0x2500,
                    f"muc tro giup chua emoji (se bi o vuong): {text!r}",
                )
            self.assertFalse(it.icon().isNull(), f"muc thieu icon: {text!r}")


if __name__ == "__main__":
    unittest.main()
