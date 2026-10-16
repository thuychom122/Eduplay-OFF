import hashlib
import json
import os
import sys
import unittest
from unittest import mock


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _make_service():
    from eduplay.core.export_service import ExportService

    return ExportService()


def _desc(key="PINNED", local="LOCALHASH", versions=None, content_hash=None):
    versions = {"PINNED": {}} if versions is None else versions
    manifest = {"key": "PINNED", "latest_key": "PINNED", "versions": versions}
    if content_hash is not None:
        manifest["content_hash"] = content_hash
    return {"key": key, "local_key": local, "manifest": manifest}


class TestLibraryPackUsable(unittest.TestCase):
    def test_pinned_with_matching_content_hash_is_usable(self):
        es = _make_service()
        self.assertTrue(es._is_library_pack_usable(_desc(content_hash="LOCALHASH")))

    def test_content_hash_mismatch_is_not_usable(self):
        es = _make_service()
        self.assertFalse(es._is_library_pack_usable(_desc(content_hash="OTHER")))

    def test_missing_hash_without_legacy_match_is_not_usable(self):
        es = _make_service()
        self.assertFalse(es._is_library_pack_usable(_desc(content_hash=None)))

    def test_legacy_content_keyed_pack_is_usable(self):
        es = _make_service()
        d = _desc(key="LOCALHASH", local="LOCALHASH",
                  versions={"LOCALHASH": {}}, content_hash=None)
        d["manifest"]["key"] = "LOCALHASH"
        d["manifest"]["latest_key"] = "LOCALHASH"
        self.assertTrue(es._is_library_pack_usable(d))

    def test_unconfirmed_key_is_not_usable(self):
        es = _make_service()
        d = _desc()
        d["manifest"] = {"key": "X", "latest_key": "Y", "versions": {"X": {}},
                         "content_hash": "LOCALHASH"}
        self.assertFalse(es._is_library_pack_usable(d))

    def test_empty_descriptor_is_not_usable(self):
        es = _make_service()
        self.assertFalse(es._is_library_pack_usable({}))
        self.assertFalse(es._is_library_pack_usable(None))


class TestOrphanedDerivedPacks(unittest.TestCase):
    def test_keeps_library_referenced_and_drops_orphan_derived(self):
        es = _make_service()
        games = {"g1": {"asset_pack_key": "PINNED"}, "g2": {"asset_pack_key": "D1"}}
        flags = {
            "PINNED": {"library": True, "never_delete": True},
            "D1": {},
            "D2": {"library": False},
        }
        self.assertEqual(es._orphaned_derived_pack_keys(games, flags), ["D2"])

    def test_empty_inputs(self):
        es = _make_service()
        self.assertEqual(es._orphaned_derived_pack_keys({}, {}), [])
        self.assertEqual(es._orphaned_derived_pack_keys(None, None), [])


class TestUploadOnceSkip(unittest.TestCase):
    def _sha(self, assets):
        return hashlib.sha256(
            json.dumps(assets, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    def test_method_skips_unchanged_pack_without_touching_firebase(self):
        from eduplay.core.export_service import ExportService

        es = ExportService()
        pinned = ExportService.LIBRARY_ASSET_PACK_KEYS["classic"]
        assets = {"tok1": "data:audio/mpeg;base64,QUJD"}
        local_hash = self._sha(assets)
        descriptor = {
            "profile": "classic",
            "key": pinned,
            "local_key": local_hash,
            "assets": assets,
            "manifest": {
                "key": pinned,
                "latest_key": pinned,
                "content_hash": local_hash,
                "versions": {pinned: {"key": pinned}},
            },
        }
        with mock.patch.object(
            ExportService, "_resolve_library_asset_pack_descriptor", return_value=descriptor
        ):
            with mock.patch("firebase_admin.initialize_app") as fake_init:
                with mock.patch("firebase_admin.db") as fake_db:
                    r = es.publish_library_asset_pack("classic", "https://demo.firebaseio.com")
        self.assertTrue(r.get("ok"))
        self.assertTrue(r.get("skipped"))
        self.assertEqual(r.get("key"), pinned)
        fake_init.assert_not_called()
        fake_db.reference.assert_not_called()

    def test_method_reuploads_when_content_changed(self):
        from eduplay.core.export_service import ExportService

        es = ExportService()
        pinned = ExportService.LIBRARY_ASSET_PACK_KEYS["classic"]
        assets = {"tok1": "data:audio/mpeg;base64,QUJD"}
        descriptor = {
            "profile": "classic",
            "key": pinned,
            "local_key": self._sha(assets),
            "assets": assets,
            "manifest": {
                "key": pinned,
                "latest_key": pinned,
                "content_hash": "0" * 64,
                "versions": {pinned: {"key": pinned}},
            },
        }
        with mock.patch.object(
            ExportService, "_resolve_library_asset_pack_descriptor", return_value=descriptor
        ):
            r = es.publish_library_asset_pack("classic", "https://demo.firebaseio.com")
        self.assertFalse(r.get("skipped", False))

    def test_standalone_script_skips_unchanged_profile(self):
        import upload_library_asset_packs as ulap_mod
        from eduplay.core.export_service import ExportService

        pinned = ExportService.LIBRARY_ASSET_PACK_KEYS["classic"]
        assets = {"tok1": "data:audio/mpeg;base64,QUJD"}
        content_hash = self._sha(assets)
        packs = {
            "classic": {
                "profile": "classic",
                "key": content_hash,
                "assets": assets,
                "payload": {"encoding": "base64", "encoded": "", "size_bytes": 0, "chunks": [""]},
                "meta": {"encoding": "base64", "chunk_size": 200000, "total_chunks": 1,
                         "asset_count": 1, "hash": content_hash, "size_bytes": 0},
            }
        }
        manifest = {
            "profile": "classic",
            "key": pinned,
            "latest_key": pinned,
            "content_hash": content_hash,
            "library": True,
            "never_delete": True,
            "pinned": True,
            "versions": {pinned: {"key": pinned}},
            "known_keys": {pinned: True},
            "version_count": 1,
        }

        class _FakeResp:
            def __init__(self, payload=None):
                self.status_code = 200
                self._payload = payload
                import json as _json
                self.text = _json.dumps(payload)

            def json(self):
                return self._payload

        puts = []

        class _FakeRequests:
            def get(self, url, **kwargs):
                if url.endswith("/asset_pack_libraries/classic.json"):
                    return _FakeResp(manifest)
                return _FakeResp(None)

            def put(self, url, data=None, headers=None):
                puts.append(url)
                return _FakeResp(True)

        stored = ulap_mod.upload_library_asset_packs(
            "https://demo.firebaseio.com", packs, requests_module=_FakeRequests())
        self.assertEqual(puts, [])
        self.assertIn("classic", stored)


if __name__ == "__main__":
    unittest.main()
