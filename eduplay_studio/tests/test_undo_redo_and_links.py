import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class _FakeResponse:
    def __init__(self, status_code=200, text="{}"):
        self.status_code = status_code
        self.text = text


def _make_pm(testcase, tmpdir, name="Undo Game"):
    from eduplay.core.export_service import ExportService
    from eduplay.core.project_manager import ProjectManager

    # save_project() mo thread nen export preview HTML -> mock de tranh
    # race khi don TemporaryDirectory.
    orig_export = ExportService.export_to_html
    ExportService.export_to_html = lambda self, *a, **k: True
    testcase.addCleanup(setattr, ExportService, "export_to_html", orig_export)

    pm = ProjectManager()
    pm.projects_dir = Path(tmpdir) / "Projects"
    pm.ensure_projects_directory()
    created = pm.create_project(name, "desc", "quiz_classic")
    return pm, created


class TestUndoRedo(unittest.TestCase):
    def test_undo_redo_add_and_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            pm, _ = _make_pm(self, tmp)
            self.assertFalse(pm.can_undo())
            pm.add_question({"question": "Q1", "options": ["a", "b"], "correct_answer": 0})
            self.assertTrue(pm.can_undo())
            self.assertEqual(len(pm.get_current_project()["questions"]), 1)
            self.assertTrue(pm.undo())
            self.assertEqual(len(pm.get_current_project()["questions"]), 0)
            self.assertTrue(pm.can_redo())
            self.assertTrue(pm.redo())
            self.assertEqual(len(pm.get_current_project()["questions"]), 1)
            qid = pm.get_current_project()["questions"][0]["id"]
            pm.delete_question(qid)
            self.assertEqual(len(pm.get_current_project()["questions"]), 0)
            pm.undo()
            self.assertEqual(len(pm.get_current_project()["questions"]), 1)
            pm.redo()
            self.assertEqual(len(pm.get_current_project()["questions"]), 0)

    def test_undo_update_and_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            pm, _ = _make_pm(self, tmp)
            pm.add_question({"question": "Q1", "options": ["a", "b"], "correct_answer": 0})
            qid = pm.get_current_project()["questions"][0]["id"]
            pm.update_question(qid, {"question": "Q1 edited", "options": ["a", "b"], "correct_answer": 1})
            self.assertEqual(pm.get_current_project()["questions"][0]["question"], "Q1 edited")
            pm.undo()
            self.assertEqual(pm.get_current_project()["questions"][0]["question"], "Q1")
            pm.redo()
            self.assertEqual(pm.get_current_project()["questions"][0]["question"], "Q1 edited")
            pm.duplicate_question(qid)
            self.assertEqual(len(pm.get_current_project()["questions"]), 2)
            pm.undo()
            self.assertEqual(len(pm.get_current_project()["questions"]), 1)

    def test_history_cleared_on_load_and_create(self):
        with tempfile.TemporaryDirectory() as tmp:
            pm, p1 = _make_pm(self, tmp, "Game One")
            pm.add_question({"question": "Q1"})
            self.assertTrue(pm.can_undo())
            pm.load_project(p1["id"])
            self.assertFalse(pm.can_undo())
            self.assertFalse(pm.can_redo())

    def test_push_same_snapshot_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            pm, _ = _make_pm(self, tmp)
            pm.add_question({"question": "Q1"})
            depth_after_add = len(pm._undo_stack)
            # deleting a non-existent id must not add a junk step
            pm.delete_question("no-such-id")
            self.assertEqual(len(pm._undo_stack), depth_after_add)


class TestDuplicateNames(unittest.TestCase):
    def test_create_blocks_duplicates_case_insensitive(self):
        with tempfile.TemporaryDirectory() as tmp:
            pm, _ = _make_pm(self, tmp, "Bai Kiem Tra")
            with self.assertRaises(ValueError):
                pm.create_project("  BAI KIEM tra ", "d", "quiz_classic")
            p2 = pm.create_project("Bai Kiem Tra", "d", "quiz_classic", on_duplicate="suffix")
            self.assertNotEqual(p2["name"], "Bai Kiem Tra")

    def test_find_duplicate_project_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            pm, _ = _make_pm(self, tmp, "Same Name")
            # bypass the guard to simulate legacy duplicates
            second_id = pm._generate_project_id("Same Name")
            second_dir = pm.projects_dir / second_id
            second_dir.mkdir(parents=True, exist_ok=True)
            payload = dict(pm.get_current_project())
            payload["id"] = second_id
            (second_dir / f"{second_id}.eduplay").write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
            groups = pm.find_duplicate_project_names()
            self.assertEqual(len(groups), 1)
            self.assertEqual(groups[0]["count"], 2)
            self.assertEqual(len(groups[0]["ids"]), 2)


class TestPublishKeyInfo(unittest.TestCase):
    def test_resolver_returns_tuple_with_conflict_info(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        dev_a = "dev_" + "a" * 32
        dev_b = "dev_" + "b" * 32
        db = {"bai-1": {"name": "Bai 1", "owner_device_id": dev_a, "owner_project_id": "x"}}

        def _fake_fetch(key, database_url, service_account_b64="", service_account_info=None):
            data = db.get(key)
            return dict(data) if data else None

        with patch.object(ExportService, "_fetch_published_game_meta", side_effect=_fake_fetch):
            key, info = svc._resolve_publish_key(
                "Bai 1", project_id="Bai 1_zzzz9999", device_id=dev_b, database_url="https://x"
            )
            self.assertNotEqual(key, "bai-1")
            self.assertTrue(key.startswith("bai-1-"))
            self.assertTrue(info.get("conflict"))
            self.assertFalse(info.get("reused"))
            key2, info2 = svc._resolve_publish_key(
                "Bai 1", project_id="Bai 1_zzzz9999", device_id=dev_a, database_url="https://x"
            )
            self.assertEqual(key2, "bai-1")
            self.assertTrue(info2.get("reused"))

    def test_list_renew_delete_published_games(self):
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        now = int(time.time())
        games = {
            "mine-1": {
                "name": "Mine",
                "owner_device_id": "dev_me",
                "owner_device_name": "PC",
                "created_at": now - 86400,
                "expires_at": now + 86400 * 3 + 7200,
            },
            "theirs-1": {"name": "Theirs", "owner_device_id": "dev_other", "created_at": now},
        }
        calls = {}

        def _fake_get(url, *args, **kwargs):
            calls["get"] = url
            return _FakeResponse(200, json.dumps(games))

        def _fake_put(url, data=None, headers=None):
            calls["put"] = (url, data)
            return _FakeResponse(200, "{}")

        def _fake_delete(url, *args, **kwargs):
            calls["delete"] = url
            return _FakeResponse(200, "{}")

        with patch.object(ExportService, "_get_publish_device_id", return_value="dev_me"):
            with patch.object(ExportService, "_read_service_account_b64", return_value=""):
                with patch("requests.get", side_effect=_fake_get):
                    res = svc.list_published_games("https://demo.firebaseio.com")
        self.assertTrue(res.get("ok"))
        self.assertEqual(len(res.get("items")), 1)
        self.assertEqual(res["items"][0]["key"], "mine-1")
        self.assertEqual(res["items"][0]["play_link"], f"{svc.PLAY_BASE_URL}/mine-1")
        self.assertEqual(res["items"][0]["days_left"], 3)
        self.assertFalse(res["items"][0]["expired"])

        with patch.object(ExportService, "_read_service_account_b64", return_value=""):
            with patch("requests.put", side_effect=_fake_put):
                renewed = svc.renew_published_game("mine-1", "https://demo.firebaseio.com")
        self.assertTrue(renewed.get("ok"))
        self.assertTrue(renewed.get("expires_at", 0) > now)
        self.assertIn("/games/mine-1/expires_at.json", calls["put"][0])

        with patch.object(ExportService, "_read_service_account_b64", return_value=""):
            with patch("requests.delete", side_effect=_fake_delete):
                deleted = svc.delete_published_game("mine-1", "https://demo.firebaseio.com")
        self.assertTrue(deleted.get("ok"))
        self.assertIn("/games/mine-1.json", calls["delete"])

    def test_list_renew_delete_prefers_admin_sdk(self):
        """Khi co service account: dung Admin SDK, khong goi REST."""
        from eduplay.core.export_service import ExportService

        svc = ExportService()
        now = int(time.time())
        admin_data = {
            "mine-1": {"name": "Mine", "owner_device_id": "dev_me", "created_at": now, "expires_at": now + 100},
        }
        rest_calls = []

        class _FakeRef:
            def __init__(self, store):
                self._store = store

            def get(self):
                return dict(self._store)

            def set(self, value):
                self._store["value"] = value

            def delete(self):
                self._store["deleted"] = True

        store = dict(admin_data)
        with patch.object(ExportService, "_get_publish_device_id", return_value="dev_me"), \
             patch.object(ExportService, "_admin_db_reference", return_value=_FakeRef(store)), \
             patch("requests.get", side_effect=lambda *a, **k: rest_calls.append("get") or _FakeResponse(401, "x")), \
             patch("requests.put", side_effect=lambda *a, **k: rest_calls.append("put") or _FakeResponse(401, "x")), \
             patch("requests.delete", side_effect=lambda *a, **k: rest_calls.append("delete") or _FakeResponse(401, "x")):
            res = svc.list_published_games("https://demo.firebaseio.com")
            self.assertTrue(res.get("ok"))
            self.assertEqual(len(res.get("items")), 1)
            renewed = svc.renew_published_game("mine-1", "https://demo.firebaseio.com")
            self.assertTrue(renewed.get("ok"))
            deleted = svc.delete_published_game("mine-1", "https://demo.firebaseio.com")
            self.assertTrue(deleted.get("ok"))
        self.assertEqual(rest_calls, [], "Admin co san thi khong duoc goi REST")


class TestDeviceName(unittest.TestCase):
    def test_device_name_roundtrip(self):
        from eduplay.core.settings_manager import SettingsManager

        with tempfile.TemporaryDirectory() as tmp:
            sm = SettingsManager(settings_dir=Path(tmp))
            sm.set_device_name("  PC Phong Hoc  ")
            self.assertEqual(sm.get_device_name(), "PC Phong Hoc")

    def test_i18n_links_keys_exist_everywhere(self):
        import json as _json

        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "eduplay", "resources", "i18n"))
        datas = {}
        for lang in ("en", "vi", "fr", "es", "de"):
            with open(os.path.join(base, f"{lang}.json"), "r", encoding="utf-8") as f:
                datas[lang] = _json.load(f)
        for key in (
            "browser.links",
            "browser.import_renamed",
            "links.title",
            "links.renew",
            "links.delete",
            "links.confirm_delete_message",
            "settings.device_name",
            "settings.open_log_folder",
            "project.duplicate_title",
            "project.duplicate_message",
            "project.dup_scan_title",
            "project.dup_scan_message",
            "publish.conflict_note",
            "editor.undo_tip",
            "editor.redo_tip",
        ):
            for lang in ("en", "vi", "fr", "es", "de"):
                self.assertIn(key, datas[lang], f"missing {key} in {lang}")


if __name__ == "__main__":
    unittest.main()
