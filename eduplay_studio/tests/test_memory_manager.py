import contextlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class _StubSettings:
    def __init__(self):
        self._data = {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value


@contextlib.contextmanager
def _isolated_fs(tmp):
    """Redirect BOTH the roaming memory file and the Documents mirror
    into tmp so tests never touch real user data."""
    from eduplay.core import memory_manager as mm_mod

    with mock.patch.dict(os.environ, {"APPDATA": str(tmp)}):
        with mock.patch(
            "eduplay.core.path_resolver.PathResolver.resolve_settings_dir",
            return_value=Path(tmp) / "Docs",
        ):
            yield mm_mod


class TestMemoryLimits(unittest.TestCase):
    def test_caps_are_enforced(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _isolated_fs(tmp) as mm_mod:
                mgr = mm_mod.MemoryManager(_StubSettings())
                for i in range(12):
                    mgr.add_message("user", "tin nhắn số %d " % i + "x" * 700)
                self.assertLessEqual(len(mgr.get_summary()), mm_mod.MAX_SUMMARY_CHARS)
                self.assertLessEqual(len(mgr.get_recent(99)), mm_mod.MAX_RECENT_MESSAGES)
                for m in mgr.get_recent(99):
                    self.assertLessEqual(len(m["content"]), mm_mod.MAX_MESSAGE_CHARS + 3)


class TestWatermarkNoDuplicates(unittest.TestCase):
    def test_close_twice_does_not_duplicate_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _isolated_fs(tmp):
                from eduplay.core.memory_manager import MemoryManager

                mgr = MemoryManager(_StubSettings())
                mgr.add_message("user", "tôi là giáo viên toán lớp 5")
                mgr.add_message("ai", "ok")
                # simulate app close
                mgr._summarize_into_memory(mgr.get_recent(5))
                mgr._save()
                first = mgr.get_summary()
                self.assertIn("giáo viên", first)
                # second close with nothing new -> summary must not grow
                mgr._summarize_into_memory(mgr.get_recent(5))
                mgr._save()
                self.assertEqual(mgr.get_summary(), first)


class TestRoamingStore(unittest.TestCase):
    def test_roaming_file_is_used_and_survives_settings_wipe(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _isolated_fs(tmp) as mm_mod:
                mgr = mm_mod.MemoryManager(_StubSettings())
                mgr.add_message("user", "tôi thích quiz trắc nghiệm")
                mgr._summarize_into_memory(mgr.get_recent(5))
                mgr._save()
                roaming = mm_mod.resolve_memory_file()
                self.assertTrue(str(roaming).startswith(str(tmp)))
                self.assertTrue(roaming.exists())
                data = json.loads(roaming.read_text(encoding="utf-8"))
                self.assertTrue(data.get("summary"))
                # fresh manager with WIPED settings still recovers from roaming
                with mock.patch(
                    "eduplay.core.path_resolver.PathResolver.resolve_settings_dir",
                    return_value=Path(tmp) / "DocsEmpty",
                ):
                    mgr3 = mm_mod.MemoryManager(None)
                self.assertEqual(mgr3.get_summary(), mgr.get_summary())

    def test_context_shape_for_ai(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _isolated_fs(tmp):
                from eduplay.core.memory_manager import MemoryManager

                mgr = MemoryManager(_StubSettings())
                mgr.add_message("user", "chào")
                ctx = mgr.get_context_for_ai()
                self.assertIn("memory_summary", ctx)
                self.assertIn("recent_messages", ctx)
                self.assertLessEqual(len(ctx["recent_messages"]), 5)

    def test_remember_question_is_not_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _isolated_fs(tmp) as mm_mod:
                self.assertFalse(mm_mod._is_profile_text("bạn nhớ tôi ko edubot?"))
                self.assertFalse(mm_mod._is_profile_text("tu te souviens de moi ?"))
                self.assertFalse(mm_mod._is_profile_text("erinnerst du dich?"))
                # lệnh nhớ thật vẫn giữ
                self.assertTrue(mm_mod._is_profile_text("hãy nhớ tôi là giáo viên toán"))
                self.assertTrue(mm_mod._is_profile_text("nhớ rằng tôi thích quiz khó"))
                self.assertTrue(mm_mod._is_profile_text("remember that I teach math"))

    def test_transient_ai_errors_not_stored(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _isolated_fs(tmp) as mm_mod:
                from eduplay.core.memory_manager import MemoryManager

                mgr = MemoryManager(_StubSettings())
                mgr.add_message("ai", "Không thể xác thực thiết bị với AI server. Hãy kiểm tra server và thử lại.")
                mgr.add_message("user", "chào edubot")
                recent = mgr.get_recent(5)
                self.assertEqual(len(recent), 1)
                self.assertEqual(recent[0]["content"], "chào edubot")
                # summary cũng không dính lỗi
                mgr._summarize_into_memory(mgr.get_recent(5))
                self.assertNotIn("xác thực", mgr.get_summary())


class TestSessionSemantics(unittest.TestCase):
    def test_session_keeps_only_user_messages(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _isolated_fs(tmp):
                from eduplay.core.memory_manager import MemoryManager

                mgr = MemoryManager(_StubSettings())
                mgr.add_message("user", "câu một")
                mgr.add_message("ai", "trả lời một (không được tính)")
                mgr.add_message("assistant", "trả lời hai (không được tính)")
                mgr.add_message("system", "tin hệ thống (không được tính)")
                mgr.add_message("user", "câu hai")
                recent = mgr.get_recent(99)
                self.assertEqual([m["content"] for m in recent], ["câu một", "câu hai"])
                for m in recent:
                    self.assertEqual(m["role"], "user")

    def test_session_cap_is_five_user_messages(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _isolated_fs(tmp):
                from eduplay.core.memory_manager import MemoryManager

                mgr = MemoryManager(_StubSettings())
                for i in range(8):
                    mgr.add_message("user", "câu %d" % i)
                    mgr.add_message("ai", "đáp %d" % i)
                recent = mgr.get_recent(99)
                self.assertEqual(len(recent), mm_max_recent())
                self.assertEqual(recent[0]["content"], "câu 3")
                self.assertEqual(recent[-1]["content"], "câu 7")

    def test_end_session_summarizes_then_clears(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _isolated_fs(tmp):
                from eduplay.core.memory_manager import MemoryManager

                mgr = MemoryManager(_StubSettings())
                mgr.add_message("user", "tôi tên An, 30 tuổi")
                mgr.add_message("user", "tạo 5 câu hỏi toán")
                profile = mgr.end_session()
                self.assertIn("An", profile)
                self.assertNotIn("tạo 5 câu", profile)
                self.assertEqual(mgr.get_recent(99), [])
                # phiên sau nap lai profile tu file
                mgr2 = MemoryManager(_StubSettings())
                self.assertIn("An", mgr2.get_summary())
                self.assertEqual(mgr2.get_recent(99), [])

    def test_task_clause_stripped_from_fact(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _isolated_fs(tmp):
                from eduplay.core.memory_manager import MemoryManager

                mgr = MemoryManager(_StubSettings())
                mgr.add_message("user", "tôi là giáo viên, hãy tạo 5 câu hỏi")
                profile = mgr.end_session()
                self.assertIn("giáo viên", profile)
                self.assertNotIn("tạo", profile)
                self.assertNotIn("câu hỏi", profile)

    def test_end_session_twice_no_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _isolated_fs(tmp):
                from eduplay.core.memory_manager import MemoryManager

                mgr = MemoryManager(_StubSettings())
                mgr.add_message("user", "tôi dạy môn văn")
                first = mgr.end_session()
                self.assertIn("văn", first)
                second = mgr.end_session()
                self.assertEqual(second, first)

    def test_old_store_migrates(self):
        with tempfile.TemporaryDirectory() as tmp:
            with _isolated_fs(tmp) as mm_mod:
                from eduplay.core.memory_manager import MemoryManager

                mgr = MemoryManager(_StubSettings())
                mgr._read_store({
                    "summary": "tôi thích quiz | hãy tạo 10 câu hỏi khó",
                    "recent": [
                        {"role": "ai", "content": "đáp cũ", "ts": 1.0},
                        {"role": "user", "content": "chào lại", "ts": 2.0},
                    ],
                    "summarized_ts": 999.0,
                })
                # summary cu duoc loc rac task, recent cu chi giu tin user
                self.assertIn("thích quiz", mgr.get_summary())
                self.assertNotIn("tạo 10 câu", mgr.get_summary())
                recent = mgr.get_recent(99)
                self.assertEqual(len(recent), 1)
                self.assertEqual(recent[0]["content"], "chào lại")


def mm_max_recent():
    from eduplay.core import memory_manager as mm_mod

    return mm_mod.MAX_RECENT_MESSAGES


if __name__ == "__main__":
    unittest.main()
