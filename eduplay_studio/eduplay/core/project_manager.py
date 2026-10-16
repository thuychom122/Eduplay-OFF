"""
Project Manager - Handles project lifecycle and file management
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from eduplay.core.path_resolver import PathResolver

class ProjectManager:
    """Manages EduPlay projects and their lifecycle"""
    
    def __init__(self):
        """Initialize project manager"""
        self.projects_dir = self._get_projects_directory()
        self.current_project = None
        self._undo_stack: List = []
        self._redo_stack: List = []
        self.ensure_projects_directory()
    
    def _get_projects_directory(self) -> Path:
        """Get the projects directory path"""
        try:
            projects_dir = PathResolver.resolve_projects_dir()
        except Exception:
            user_profile = os.environ.get('USERPROFILE') or os.environ.get('HOME')
            base = Path(user_profile) if user_profile else Path(os.getcwd())
            projects_dir = base / "EduPlay" / "Projects"
        return projects_dir
    
    def ensure_projects_directory(self):
        """Ensure projects directory exists"""
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def _normalize_game_type(self, game_type: str) -> str:
        gt = str(game_type or "").strip().lower()
        if gt in ("quiz", "quiz_classic", "classic", "trắc nghiệm", "trac nghiem"):
            return "quiz_classic"
        if ("bắt cá" in gt) or ("bat ca" in gt) or ("câu cá" in gt) or ("cau ca" in gt) or ("fishing" in gt) or (gt == "fish"):
            return "fishing"
        if ("triệu phú" in gt) or ("trieu phu" in gt) or ("millionaire" in gt) or ("ai la trieu phu" in gt) or ("ai là triệu phú" in gt):
            return "quiz_millionaire"
        return gt or "quiz_classic"

    def _normalize_tags(self, tags: Any) -> List[str]:
        if not isinstance(tags, list):
            return []
        out: List[str] = []
        seen = set()
        for tag in tags:
            text = str(tag or "").strip()
            if not text:
                continue
            lowered = text.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            out.append(text)
        return out
    
    def normalize_project_name(self, name: Any) -> str:
        """Chuan hoa ten du an de so sanh trung: strip, gom khoang trang,
        case-insensitive, bo emoji cau-ca tu dong gan (🎣) o cuoi ten.

        Vi du: "Bai 1" (quiz) va "Bai 1 🎣" (fishing tu dong gan emoji)
        duoc coi la TRUNG nhau tren cung mot may.
        """
        try:
            text = str(name or "")
        except Exception:
            return ""
        try:
            import re as _re
            text = text.replace("🎣", " ")
            text = _re.sub(r"\s+", " ", text).strip()
            return text.casefold()
        except Exception:
            try:
                return " ".join(str(name or "").split()).lower()
            except Exception:
                return ""

    def is_project_name_taken(self, name: str, exclude_id: str = "") -> bool:
        """True neu da co project khac (id != exclude_id) trung ten (khong phan biet hoa/thuong)."""
        try:
            wanted = self.normalize_project_name(name)
        except Exception:
            wanted = ""
        if not wanted:
            return False
        try:
            excluded = str(exclude_id or "").strip()
        except Exception:
            excluded = ""
        try:
            for project in self.get_all_projects():
                try:
                    if not isinstance(project, dict):
                        continue
                    pid = str(project.get("id") or "").strip()
                    if excluded and pid == excluded:
                        continue
                    if self.normalize_project_name(project.get("name")) == wanted:
                        return True
                except Exception:
                    continue
        except Exception:
            return False
        return False

    def ensure_unique_project_name(self, name: str, exclude_id: str = "") -> str:
        """Tra ve ten chua ai dung: neu trung thi them hau to " (2)", " (3)", ..."""
        base = str(name or "").strip() or "Untitled Project"
        if not self.is_project_name_taken(base, exclude_id=exclude_id):
            return base
        counter = 2
        while True:
            candidate = f"{base} ({counter})"
            if not self.is_project_name_taken(candidate, exclude_id=exclude_id):
                return candidate
            counter += 1
            if counter > 1000:
                import uuid as _uuid
                return f"{base} ({_uuid.uuid4().hex[:6]})"

    def find_duplicate_project_names(self) -> List[Dict]:
        """Tim cac nhom project trung ten tren may (chuan hoa nhu khi tao moi).

        Tra ve [{"name": ten_hien_thi, "ids": [...], "count": n}] de UI canh bao
        nguoi dung doi ten (tranh tranh link khi publish).
        """
        groups: Dict[str, Dict] = {}
        try:
            for project in self.get_all_projects():
                try:
                    if not isinstance(project, dict):
                        continue
                    norm = self.normalize_project_name(project.get("name"))
                    if not norm:
                        continue
                    entry = groups.get(norm)
                    if entry is None:
                        entry = {"name": str(project.get("name") or "").strip(), "ids": []}
                        groups[norm] = entry
                    entry["ids"].append(str(project.get("id") or "").strip())
                except Exception:
                    continue
        except Exception:
            return []
        out = []
        for entry in groups.values():
            try:
                ids = [pid for pid in (entry.get("ids") or []) if pid]
                if len(set(ids)) > 1:
                    out.append({"name": entry.get("name", ""), "ids": sorted(set(ids)), "count": len(set(ids))})
            except Exception:
                continue
        try:
            out.sort(key=lambda item: str(item.get("name") or "").lower())
        except Exception:
            pass
        return out

    UNDO_LIMIT = 30
    # Undo bao phu: questions + game_config + name + description (doi ten,
    # sua cau hinh game cung hoan tac duoc). Snapshot deepcopy day du (ke ca
    # media base64) de undo khong bao gio lam mat du lieu; cac buoc giong
    # nhau lien tiep duoc bo qua nen RAM tang khong dang ke.

    def _snapshot_questions(self) -> List:
        try:
            import copy as _copy

            qs = (self.current_project or {}).get("questions", []) or []
            return _copy.deepcopy(qs) if isinstance(qs, list) else []
        except Exception:
            return []

    def _snapshot_state(self) -> Dict:
        """Snapshot full undo (questions + game_config + name + description)."""
        try:
            import copy as _copy

            cur = self.current_project or {}
            qs = cur.get("questions", []) or []
            cfg = cur.get("game_config", {}) or {}
            return {
                "questions": _copy.deepcopy(qs) if isinstance(qs, list) else [],
                "game_config": _copy.deepcopy(cfg) if isinstance(cfg, dict) else {},
                "name": str(cur.get("name") or ""),
                "description": str(cur.get("description") or ""),
            }
        except Exception:
            return {"questions": [], "game_config": {}, "name": "", "description": ""}

    def _push_undo(self) -> None:
        """Luu trang thai hien tai truoc khi sua (add/update/delete/duplicate)."""
        try:
            self.push_undo_state()
        except Exception:
            pass

    def push_undo_state(self) -> None:
        """Push full-state hien tai cua current_project (neu co thay doi)."""
        try:
            self.push_undo_snapshot(self._snapshot_state())
        except Exception:
            pass

    def push_undo_snapshot(self, snapshot) -> None:
        """Nhan push 1 snapshot cho san (editor goi truoc khi sua truc tiep).

        Chap nhan list questions (cu) hoac dict full-state; thieu truong nao
        thi lay tu state hien tai de undo khong lam mat du lieu. Bo qua neu
        giong buoc ke truoc.
        """
        try:
            if not isinstance(self.current_project, dict):
                return
            if getattr(self, "_undo_stack", None) is None:
                self._undo_stack = []
            if getattr(self, "_redo_stack", None) is None:
                self._redo_stack = []
            if isinstance(snapshot, dict):
                snap = dict(snapshot)
                base = self._snapshot_state()
                for field in ("questions", "game_config", "name", "description"):
                    if field not in snap:
                        snap[field] = base.get(field)
            elif isinstance(snapshot, list):
                import copy as _copy

                snap = self._snapshot_state()
                try:
                    snap["questions"] = _copy.deepcopy(snapshot)
                except Exception:
                    snap["questions"] = []
            else:
                return
            try:
                if self._undo_stack and self._undo_stack[-1] == snap:
                    return
            except Exception:
                pass
            self._undo_stack.append(snap)
            while len(self._undo_stack) > int(self.UNDO_LIMIT):
                self._undo_stack.pop(0)
            self._redo_stack = []
        except Exception:
            pass

    def clear_history(self) -> None:
        try:
            self._undo_stack = []
        except Exception:
            pass
        try:
            self._redo_stack = []
        except Exception:
            pass

    def can_undo(self) -> bool:
        try:
            return bool(getattr(self, "_undo_stack", None))
        except Exception:
            return False

    def can_redo(self) -> bool:
        try:
            return bool(getattr(self, "_redo_stack", None))
        except Exception:
            return False

    def _apply_undo_snapshot(self, snap: Dict) -> None:
        """Chep 4 truong undo vao current_project (khong cham cac truong khac)."""
        try:
            data = dict(snap or {})
            if "questions" in data:
                self.current_project["questions"] = data.get("questions") or []
            if "game_config" in data and isinstance(data.get("game_config"), dict):
                self.current_project["game_config"] = data.get("game_config")
            if "name" in data:
                self.current_project["name"] = str(data.get("name") or "")
            if "description" in data:
                self.current_project["description"] = str(data.get("description") or "")
        except Exception:
            pass

    def undo(self) -> bool:
        """Hoan tac lan sua gan nhat (cau hoi / cau hinh / ten). Tra ve True neu co thay doi."""
        try:
            if not isinstance(self.current_project, dict):
                return False
            stack = getattr(self, "_undo_stack", None) or []
            if not stack:
                return False
            if getattr(self, "_redo_stack", None) is None:
                self._redo_stack = []
            self._redo_stack.append(self._snapshot_state())
            self._apply_undo_snapshot(stack.pop())
            return bool(self.save_project(self.current_project))
        except Exception:
            return False

    def redo(self) -> bool:
        """Lam lai lan hoan tac gan nhat. Tra ve True neu co thay doi."""
        try:
            if not isinstance(self.current_project, dict):
                return False
            stack = getattr(self, "_redo_stack", None) or []
            if not stack:
                return False
            if getattr(self, "_undo_stack", None) is None:
                self._undo_stack = []
            self._undo_stack.append(self._snapshot_state())
            self._apply_undo_snapshot(stack.pop())
            return bool(self.save_project(self.current_project))
        except Exception:
            return False

    def create_project(self, name: str, description: str, game_type: str, on_duplicate: str = "error") -> Dict:
        """Create a new project.

        Khong cho phep 2 project trung ten tren cung 1 may (so sanh khong
        phan biet hoa/thuong, gom khoang trang, bo emoji 🎣 tu dong gan).

        - on_duplicate="error" (mac dinh): nem ValueError khi ten da ton tai.
          UI bat loi nay va hien canh bao cho nguoi dung doi ten khac.
        - on_duplicate="suffix": tu dong doi ten thanh "Ten (2)", "Ten (3)",
          ... cho cac luong tu dong (AI/nhap file) khong the hoi nguoi dung.
        """
        game_type = self._normalize_game_type(game_type)
        clean_name = str(name or "").strip()
        if not clean_name:
            raise ValueError("Tên dự án không được để trống.")
        mode = str(on_duplicate or "error").strip().lower()
        if self.is_project_name_taken(clean_name):
            if mode == "suffix":
                clean_name = self.ensure_unique_project_name(clean_name)
            else:
                raise ValueError(
                    f'Đã có dự án tên "{clean_name}" trên máy này. '
                    "Vui lòng chọn tên khác."
                )
        project_id = self._generate_project_id(clean_name)
        project_dir = self.projects_dir / project_id
        
        # Create project directory
        project_dir.mkdir(exist_ok=True)
        
        # Create project metadata
        project_data = {
            "id": project_id,
            "name": clean_name,
            "description": description,
            "game_type": game_type,
            "created_at": datetime.now().isoformat(),
            "modified_at": datetime.now().isoformat(),
            "tags": [],
            "questions": [],
            "game_config": self._get_default_game_config(game_type),
            "media_files": []
        }
        if game_type == "fishing":
            try:
                project_data["force_variant"] = "fishing"
                project_data["variant_marker"] = "fishing"
                cfg = dict(project_data.get("game_config") or {})
                cfg["variant_marker"] = "fishing"
                cfg["game_type"] = "Fishing Game"
                project_data["game_config"] = cfg
            except Exception:
                pass
        try:
            assets_dir = Path(__file__).parent.parent.parent / "assets_bundle"
            defaults = [
                ("background_music", assets_dir / "sound" / "background.mp3"),
                ("correct_sound", assets_dir / "sound" / "correct.wav"),
                ("wrong_sound", assets_dir / "sound" / "wrong.wav"),
                ("click_sound", assets_dir / "sound" / "click.wav"),
                ("bg_seaweed", assets_dir / "kenney_platformer-kit" / "PNG" / "Default" / "background_seaweed_a.png"),
                ("bg_rock", assets_dir / "kenney_platformer-kit" / "PNG" / "Default" / "background_rock_a.png")
            ]
            for asset_name, path in defaults:
                p = str(path)
                if os.path.exists(p):
                    project_data["media_files"].append({"name": asset_name, "path": p})
        except Exception:
            pass
        
        # Save project file
        project_file = project_dir / f"{project_id}.eduplay"
        with open(project_file, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, indent=2, ensure_ascii=False)
        
        # Create media directory
        media_dir = project_dir / "media"
        media_dir.mkdir(exist_ok=True)
        
        self.current_project = project_data
        try:
            self.clear_history()
        except Exception:
            pass
        return project_data
    
    def load_project(self, project_id: str) -> Optional[Dict]:
        """Load a project by ID"""
        project_file = self.projects_dir / project_id / f"{project_id}.eduplay"
        
        if not project_file.exists():
            return None
        
        try:
            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            changed = False
            try:
                qs = project_data.get("questions", [])
            except Exception:
                qs = []
            if isinstance(qs, list) and qs:
                try:
                    import uuid

                    existing = set()
                    for q in qs:
                        if not isinstance(q, dict):
                            continue
                        try:
                            qid0 = str(q.get("id") or "").strip()
                        except Exception:
                            qid0 = ""
                        if qid0:
                            if qid0 in existing:
                                qid0 = ""
                            else:
                                existing.add(qid0)
                                continue
                        if not qid0:
                            qid0 = f"q_{uuid.uuid4().hex[:10]}"
                            while qid0 in existing:
                                qid0 = f"q_{uuid.uuid4().hex[:10]}"
                            q["id"] = qid0
                            existing.add(qid0)
                            changed = True
                except Exception:
                    pass

            self.current_project = project_data
            try:
                self.clear_history()
            except Exception:
                pass
            if changed:
                try:
                    self.save_project(project_data)
                except Exception:
                    pass
            return project_data
            
        except Exception as e:
            print(f"Error loading project {project_id}: {e}")
            # File chinh loi -> thu khoi phuc tu backup xoay vong moi nhat
            try:
                restored = self._restore_from_backup(str(project_id))
                if isinstance(restored, dict):
                    return restored
            except Exception:
                pass
            return None

    BACKUP_KEEP = 5
    BACKUP_MIN_INTERVAL_SEC = 600

    def _backup_dir(self, project_id: str) -> Path:
        folder = self.projects_dir / str(project_id or "").strip() / "backups"
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        return folder

    def _write_rotating_backup(self, project_id: str) -> None:
        """Copy file .eduplay hien tai vao backups/ (toi da BACKUP_KEEP ban).

        Ghi throttled: moi project toi da 1 backup / BACKUP_MIN_INTERVAL_SEC
        de autosave lien tuc khong spam file.
        """
        pid = str(project_id or "").strip()
        if not pid:
            return
        try:
            now = datetime.now().timestamp()
        except Exception:
            now = 0.0
        try:
            last = float((getattr(self, "_last_backup_ts", None) or {}).get(pid, 0.0))
        except Exception:
            last = 0.0
        if now and last and (now - last) < self.BACKUP_MIN_INTERVAL_SEC:
            return
        try:
            src = self.projects_dir / pid / f"{pid}.eduplay"
            if not src.is_file():
                return
            raw = src.read_bytes()
            if not raw:
                return
            try:
                json.loads(raw.decode("utf-8"))
            except Exception:
                return
            folder = self._backup_dir(pid)
            try:
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            except Exception:
                stamp = "backup"
            dest = folder / f"{pid}_{stamp}.eduplay"
            counter = 1
            while dest.exists() and counter < 100:
                counter += 1
                dest = folder / f"{pid}_{stamp}_{counter}.eduplay"
            dest.write_bytes(raw)
            try:
                if getattr(self, "_last_backup_ts", None) is None:
                    self._last_backup_ts = {}
                self._last_backup_ts[pid] = now
            except Exception:
                pass
            try:
                files = sorted(
                    (p for p in folder.glob(f"{pid}_*.eduplay") if p.is_file()),
                    key=lambda p: p.name,
                )
                while len(files) > int(self.BACKUP_KEEP):
                    oldest = files.pop(0)
                    try:
                        oldest.unlink()
                    except Exception:
                        break
            except Exception:
                pass
        except Exception:
            pass

    def _newest_valid_backup(self, project_id: str):
        """Tra ve (path, data) cua backup hop le moi nhat, hoac (None, None)."""
        pid = str(project_id or "").strip()
        if not pid:
            return None, None
        try:
            folder = self.projects_dir / pid / "backups"
            if not folder.is_dir():
                return None, None
            files = sorted(
                (p for p in folder.glob(f"{pid}_*.eduplay") if p.is_file()),
                key=lambda p: p.name,
                reverse=True,
            )
            for cand in files:
                try:
                    data = json.loads(cand.read_text(encoding="utf-8"))
                    if isinstance(data, dict) and str(data.get("id") or "").strip() == pid:
                        return cand, data
                except Exception:
                    continue
        except Exception:
            pass
        return None, None

    def _restore_from_backup(self, project_id: str) -> Optional[Dict]:
        """Chep backup moi nhat len file chinh va nap vao current_project."""
        pid = str(project_id or "").strip()
        if not pid:
            return None
        path, data = self._newest_valid_backup(pid)
        if path is None or not isinstance(data, dict):
            return None
        try:
            dest = self.projects_dir / pid / f"{pid}.eduplay"
            dest.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
        try:
            self.current_project = data
            self.clear_history()
        except Exception:
            pass
        try:
            label = ""
            try:
                label = path.name
            except Exception:
                label = ""
            self._last_restore_info = {
                "id": pid,
                "name": str(data.get("name") or pid),
                "backup": label,
            }
        except Exception:
            pass
        return data

    def pop_last_restore_info(self) -> Optional[Dict]:
        """Lay + xoa thong tin khoi phuc gan nhat (UI hien dialog 1 lan)."""
        try:
            info = getattr(self, "_last_restore_info", None)
            self._last_restore_info = None
            return dict(info) if isinstance(info, dict) else None
        except Exception:
            return None
    
    def save_project(self, project_data: Dict = None) -> bool:
        """Save current or provided project"""
        if project_data is None:
            project_data = self.current_project
        
        if project_data is None:
            return False
        
        try:
            project_id = project_data["id"]
            project_file = self.projects_dir / project_id / f"{project_id}.eduplay"

            # Backup xoay vong truoc khi ghi de (chong mat bai khi file loi/mat dien)
            try:
                self._write_rotating_backup(str(project_id))
            except Exception:
                pass
            
            # FIX: auto-assign missing question ids trước khi lưu (ngăn lỗi Thiếu question_id khi thêm ảnh cho Q6)
            try:
                qs = project_data.get("questions", [])
                if isinstance(qs, list) and qs:
                    import uuid as _uuid
                    existing = set()
                    for _q in qs:
                        if isinstance(_q, dict):
                            _qid = str(_q.get("id") or "").strip()
                            if _qid:
                                existing.add(_qid)
                    for _q in qs:
                        if not isinstance(_q, dict):
                            continue
                        _qid = str(_q.get("id") or "").strip()
                        if not _qid or _qid in existing and list(qs).count(_q) >1:
                            # nếu trùng hoặc thiếu, tạo mới
                            _new = f"q_{_uuid.uuid4().hex[:10]}"
                            while _new in existing:
                                _new = f"q_{_uuid.uuid4().hex[:10]}"
                            _q["id"] = _new
                            existing.add(_new)
                        elif _qid in existing:
                            # kiểm tra trùng: nếu đã thấy trước thì đổi
                            # đếm số lần xuất hiện
                            pass
                    # đảm bảo unique lần 2
                    seen = set()
                    for _q in qs:
                        if not isinstance(_q, dict):
                            continue
                        _qid = str(_q.get("id") or "").strip()
                        if not _qid or _qid in seen:
                            _new = f"q_{_uuid.uuid4().hex[:10]}"
                            while _new in seen:
                                _new = f"q_{_uuid.uuid4().hex[:10]}"
                            _q["id"] = _new
                            seen.add(_new)
                        else:
                            seen.add(_qid)
            except Exception:
                pass
            
            # Update modified timestamp
            project_data["modified_at"] = datetime.now().isoformat()
            
            with open(project_file, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, indent=2, ensure_ascii=False)
            
            self.current_project = project_data

            # Auto-save preview HTML into project folder (background, non-blocking)
            try:
                import copy as _copy
                import threading as _threading
                _proj_snap = _copy.deepcopy(project_data)
                _out_dir = str(self.projects_dir / project_id)
                def _save_preview():
                    try:
                        from eduplay.core.export_service import ExportService
                        _svc = ExportService()
                        _name = str(_proj_snap.get("name") or project_id)
                        # Sanitize name same way export_service does
                        _safe = ''.join([c for c in _name if c.isalnum() or c in (' ', '-', '_')]).strip().replace(' ', '_') or 'EduPlay_Game'
                        _preview_name = _safe + "_preview"
                        _svc.export_to_html(_proj_snap, _out_dir, bundle_resources=True, single_file=True, output_filename=_preview_name)
                    except Exception:
                        pass
                _t = _threading.Thread(target=_save_preview, daemon=True)
                _t.start()
            except Exception:
                pass

            return True
            
        except Exception as e:
            print(f"Error saving project: {e}")
            return False
    
    def get_all_projects(self) -> List[Dict]:
        """Get all projects"""
        projects = []
        
        try:
            # Use fast existence check bypassing global OneDrive patch for speed
            # (project files are under Documents/EduPlay/Projects which is already resolved)
            from eduplay.core.path_resolver import _ORIG_EXISTS, _is_resolving, _set_resolving
            def _fast_exists(p: Path) -> bool:
                try:
                    prev = _is_resolving()
                    _set_resolving(True)
                    try:
                        # Direct OS check without heavy candidate probing
                        return Path(p).stat().is_file() if hasattr(Path(p), 'stat') else False
                    except (FileNotFoundError, NotADirectoryError, OSError):
                        return False
                    finally:
                        _set_resolving(prev)
                except Exception:
                    try:
                        return p.exists()
                    except Exception:
                        return False

            for project_dir in self.projects_dir.iterdir():
                if project_dir.is_dir():
                    project_file = project_dir / f"{project_dir.name}.eduplay"
                    
                    # Fast path: use stat instead of patched exists (0.58s -> 0.001s for missing)
                    try:
                        is_file = _fast_exists(project_file)
                    except Exception:
                        try:
                            is_file = project_file.exists()
                        except Exception:
                            is_file = False
                    if is_file:
                        try:
                            with open(project_file, 'r', encoding='utf-8') as f:
                                project_data = json.load(f)
                            
                            # Add file metadata
                            stat = project_file.stat()
                            project_data["file_size"] = stat.st_size
                            project_data["file_modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
                            
                            projects.append(project_data)
                            
                        except Exception as e:
                            # File loi -> thu khoi phuc tu backup roi moi bo qua
                            restored_ok = False
                            try:
                                restored = self._restore_from_backup(str(project_dir.name))
                                if isinstance(restored, dict):
                                    try:
                                        stat = project_file.stat()
                                        restored["file_size"] = stat.st_size
                                        restored["file_modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
                                    except Exception:
                                        pass
                                    projects.append(restored)
                                    restored_ok = True
                                    try:
                                        names = getattr(self, "_restored_names", None)
                                        if names is None:
                                            names = []
                                            self._restored_names = names
                                        label = str(restored.get("name") or project_dir.name)
                                        if label not in names:
                                            names.append(label)
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                            if not restored_ok:
                                print(f"Error reading project {project_dir.name}: {e}")
                            continue
            
            # Sort by modification date (newest first)
            projects.sort(key=lambda x: x.get("modified_at", ""), reverse=True)
            
        except Exception as e:
            print(f"Error scanning projects directory: {e}")
        
        return projects

    def pop_restored_names(self) -> List[str]:
        """Lay + xoa danh sach ten project vua duoc khoi phuc tu backup."""
        try:
            names = list(getattr(self, "_restored_names", None) or [])
        except Exception:
            names = []
        try:
            self._restored_names = []
        except Exception:
            pass
        return [str(n) for n in names if str(n or "").strip()]

    def get_all_project_tags(self, projects: Optional[List[Dict]] = None) -> List[str]:
        source = projects if isinstance(projects, list) else self.get_all_projects()
        seen = set()
        out: List[str] = []
        for project in source:
            if not isinstance(project, dict):
                continue
            for tag in self._normalize_tags(project.get("tags")):
                lowered = tag.lower()
                if lowered in seen:
                    continue
                seen.add(lowered)
                out.append(tag)
        out.sort(key=lambda item: item.lower())
        return out

    def filter_projects(
        self,
        projects: List[Dict],
        search_text: str = "",
        template_filter: str = "all",
        tag_filter: str = "all",
        recent_only: bool = False,
        recent_project_ids: Optional[List[str]] = None,
    ) -> List[Dict]:
        items = [p for p in (projects or []) if isinstance(p, dict)]
        query = str(search_text or "").strip().lower()
        wanted_template = str(template_filter or "all").strip().lower()
        wanted_tag = str(tag_filter or "all").strip().lower()
        recent_ids = [str(pid or "").strip() for pid in (recent_project_ids or []) if str(pid or "").strip()]
        recent_set = set(recent_ids)

        filtered: List[Dict] = []
        for project in items:
            if recent_only and str(project.get("id") or "").strip() not in recent_set:
                continue

            project_tags = self._normalize_tags(project.get("tags"))
            project["tags"] = project_tags

            if query:
                haystack = " ".join(
                    [
                        str(project.get("name") or ""),
                        str(project.get("description") or ""),
                        str(project.get("game_type") or ""),
                        " ".join(project_tags),
                    ]
                ).lower()
                if query not in haystack:
                    continue

            if wanted_template not in ("", "all"):
                project_game_type = self._normalize_game_type(project.get("game_type", "quiz_classic"))
                if project_game_type != self._normalize_game_type(wanted_template):
                    continue

            if wanted_tag not in ("", "all"):
                lowered_tags = {tag.lower() for tag in project_tags}
                if wanted_tag not in lowered_tags:
                    continue

            filtered.append(project)

        if recent_only and recent_ids:
            order = {pid: index for index, pid in enumerate(recent_ids)}
            filtered.sort(key=lambda project: order.get(str(project.get("id") or "").strip(), len(order)))
        return filtered

    def update_project_tags(self, project_id: str, tags: List[Any]) -> Optional[Dict]:
        project = self.load_project(project_id)
        if not isinstance(project, dict):
            return None
        project["tags"] = self._normalize_tags(tags)
        ok = self.save_project(project)
        return project if ok else None
    
    def delete_project(self, project_id: str) -> bool:
        """Delete a project - robust for OneDrive/readonly/locked files"""
        try:
            pid = str(project_id or "").strip()
            if not pid:
                return False
            project_dir = self.projects_dir / pid
            # Resolve via PathResolver for OneDrive junctions
            try:
                # Prefer resolver-aware existence check
                from eduplay.core.path_resolver import PathResolver as _PR
                # Bypass global patch for direct check
                try:
                    exists = project_dir.exists()
                except Exception:
                    exists = False
                if not exists:
                    # try resolver
                    alt = _PR.resolve_projects_dir() / pid
                    if alt != project_dir and alt.exists():
                        project_dir = alt
                    else:
                        return False
            except Exception:
                if not project_dir.exists():
                    return False
            if not project_dir.exists():
                return False
            # Try normal rmtree with onerror to clear readonly
            def _on_rm_error(func, path, exc_info):
                try:
                    os.chmod(path, 0o777)
                    func(path)
                except Exception:
                    try:
                        # Try unlink for files, rmdir for dirs
                        p = Path(path)
                        if p.is_file() or p.is_symlink():
                            p.unlink(missing_ok=True)
                        elif p.is_dir():
                            try:
                                os.rmdir(path)
                            except Exception:
                                pass
                    except Exception:
                        pass
            try:
                shutil.rmtree(project_dir, onerror=_on_rm_error)
            except Exception as e2:
                # Fallback: try via pathlib unlink loop
                try:
                    for child in sorted(project_dir.rglob("*"), reverse=True):
                        try:
                            if child.is_file() or child.is_symlink():
                                try:
                                    os.chmod(child, 0o777)
                                except Exception:
                                    pass
                                child.unlink(missing_ok=True)
                            elif child.is_dir():
                                try:
                                    child.rmdir()
                                except Exception:
                                    pass
                        except Exception:
                            continue
                    try:
                        project_dir.rmdir()
                    except Exception:
                        pass
                except Exception:
                    pass
                # Verify
                try:
                    if project_dir.exists():
                        print(f"Error deleting project {pid}: still exists after rmtree ({e2})")
                        return False
                except Exception:
                    pass
            # Clear current_project if it was the deleted one
            try:
                if self.current_project and str(self.current_project.get("id") or "").strip() == pid:
                    self.current_project = None
            except Exception:
                pass
            # Verify deletion
            try:
                if project_dir.exists():
                    return False
            except Exception:
                pass
            return True
        except Exception as e:
            try:
                print(f"Error deleting project {project_id}: {e}")
            except Exception:
                pass
            return False

    def duplicate_project(self, project_id: str) -> Optional[Dict]:
        try:
            src = self.load_project(project_id)
            if not isinstance(src, dict):
                return None
        except Exception:
            return None

        try:
            import copy
            import uuid

            out = copy.deepcopy(src)
            src_name = str(out.get("name") or project_id).strip() or project_id
            # Nhan ban cung khong duoc trung ten voi project san co tren may.
            try:
                out["name"] = self.ensure_unique_project_name(f"{src_name} (Copy)")
            except Exception:
                out["name"] = f"{src_name} (Copy)"
            new_id = self._generate_project_id(out["name"])
            out["id"] = new_id
            out["created_at"] = datetime.now().isoformat()
            out["modified_at"] = datetime.now().isoformat()

            tags = out.get("tags", [])
            if not isinstance(tags, list):
                out["tags"] = []
            else:
                out["tags"] = [str(t).strip() for t in tags if str(t or "").strip()]

            qs = out.get("questions", [])
            if not isinstance(qs, list):
                qs = []
            existing = set()
            new_qs = []
            for q in qs:
                if not isinstance(q, dict):
                    continue
                q2 = copy.deepcopy(q)
                qid = f"q_{uuid.uuid4().hex[:10]}"
                while qid in existing:
                    qid = f"q_{uuid.uuid4().hex[:10]}"
                q2["id"] = qid
                existing.add(qid)
                new_qs.append(q2)
            out["questions"] = new_qs

            proj_dir = self.projects_dir / new_id
            proj_dir.mkdir(parents=True, exist_ok=True)
            proj_file = proj_dir / f"{new_id}.eduplay"
            with open(proj_file, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=2, ensure_ascii=False)

            try:
                media_dir = proj_dir / "media"
                media_dir.mkdir(exist_ok=True)
            except Exception:
                pass

            return out
        except Exception:
            return None
    
    def _normalize_for_dedup(self, text: str) -> str:
        """Chuẩn hoá text để so trùng: lower, bỏ dấu câu thừa, khoảng trắng."""
        try:
            import re
            import unicodedata
            t = str(text or "").strip().lower()
            if not t:
                return ""
            # Đ -> d trước khi NFD để không bị mất
            try:
                t = t.replace("đ", "d").replace("Đ", "d")
            except Exception:
                pass
            # Bỏ dấu tiếng Việt để so sánh gần đúng
            try:
                t_norm = unicodedata.normalize("NFD", t)
                t_norm = "".join(ch for ch in t_norm if unicodedata.category(ch) != "Mn")
            except Exception:
                t_norm = t
            # Sau khi bỏ dấu, đ đã thành d nên giữ lại; thay thế lại đ nếu còn sót
            try:
                t_norm = t_norm.replace("đ", "d")
            except Exception:
                pass
            # Giữ chữ/số, bỏ ký tự đặc biệt
            try:
                t_norm = re.sub(r"[^a-z0-9\s]", " ", t_norm)
                t_norm = re.sub(r"\s+", " ", t_norm).strip()
            except Exception:
                t_norm = " ".join(t_norm.split())
            return t_norm
        except Exception:
            try:
                return " ".join(str(text or "").lower().split())
            except Exception:
                return ""

    def _is_duplicate_question(self, new_q: Dict, existing_questions: List[Dict]) -> bool:
        """Kiểm tra câu mới có trùng với câu đã có không (so nội dung + đáp án)."""
        try:
            new_text = str((new_q or {}).get("question") or "").strip()
            if not new_text:
                return False
            new_norm = self._normalize_for_dedup(new_text)
            if not new_norm or len(new_norm) < 5:
                return False
            # So với từng câu cũ
            for eq in existing_questions or []:
                if not isinstance(eq, dict):
                    continue
                eq_text = str(eq.get("question") or "").strip()
                if not eq_text:
                    continue
                eq_norm = self._normalize_for_dedup(eq_text)
                if not eq_norm:
                    continue
                # 1) Exact match sau chuẩn hoá
                if new_norm == eq_norm:
                    return True
                # 2) Một câu chứa hoàn toàn câu kia và độ dài chênh <20% => trùng
                try:
                    if len(new_norm) >= 15 and len(eq_norm) >= 15:
                        if new_norm in eq_norm or eq_norm in new_norm:
                            # Nếu câu ngắn là substring của câu dài và tỉ lệ dài >0.85
                            ratio = min(len(new_norm), len(eq_norm)) / max(len(new_norm), len(eq_norm))
                            if ratio > 0.85:
                                return True
                except Exception:
                    pass
                # 3) Check options trùng (cho multiple_choice): nếu question gần giống và options giống nhau
                try:
                    if new_norm[:60] == eq_norm[:60]:
                        # Cùng 60 ký tự đầu => nghi trùng
                        new_opts = (new_q or {}).get("options")
                        eq_opts = eq.get("options")
                        if isinstance(new_opts, list) and isinstance(eq_opts, list) and len(new_opts) >= 2 and len(eq_opts) >= 2:
                            nn = set(self._normalize_for_dedup(str(o)) for o in new_opts if str(o or "").strip())
                            en = set(self._normalize_for_dedup(str(o)) for o in eq_opts if str(o or "").strip())
                            if nn and en and len(nn & en) >= min(len(nn), len(en)) - 1:
                                return True
                except Exception:
                    pass
            return False
        except Exception:
            return False

    def add_question(self, question_data: Dict) -> bool:
        """Add a question to current project - có chống trùng lặp"""
        if not self.current_project:
            return False
        
        try:
            if "questions" not in self.current_project:
                self.current_project["questions"] = []

            questions = self.current_project.get("questions", []) or []
            # === Safety net: chặn trùng lặp ngay tại tầng lưu ===
            try:
                if self._is_duplicate_question(question_data, questions):
                    print(f"[DEDUP] skip duplicate question: {str(question_data.get('question') or '')[:60]}")
                    return False
            except Exception:
                pass

            existing_ids = set()
            try:
                for q in questions:
                    if isinstance(q, dict):
                        qid = str(q.get("id") or "").strip()
                        if qid:
                            existing_ids.add(qid)
            except Exception:
                existing_ids = set()

            qid = ""
            try:
                qid = str(question_data.get("id") or "").strip()
            except Exception:
                qid = ""

            if not qid or qid in existing_ids:
                import uuid

                qid = f"q_{uuid.uuid4().hex[:10]}"
                while qid in existing_ids:
                    qid = f"q_{uuid.uuid4().hex[:10]}"
                question_data["id"] = qid

            try:
                self._push_undo()
            except Exception:
                pass
            self.current_project["questions"].append(question_data)
            return self.save_project()
            
        except Exception as e:
            print(f"Error adding question: {e}")
            return False
    
    def update_question(self, question_id: str, question_data: Dict) -> bool:
        """Update a question in current project"""
        if not self.current_project:
            return False
        
        try:
            questions = self.current_project.get("questions", [])
            
            for i, question in enumerate(questions):
                if question.get("id") == question_id:
                    # Preserve ID
                    try:
                        self._push_undo()
                    except Exception:
                        pass
                    question_data["id"] = question_id
                    questions[i] = question_data
                    break
            
            return self.save_project()
            
        except Exception as e:
            print(f"Error updating question {question_id}: {e}")
            return False
    
    def delete_question(self, question_id: str) -> bool:
        """Delete a question from current project"""
        if not self.current_project:
            return False
        
        try:
            questions = self.current_project.get("questions", [])
            try:
                will_remove = any(
                    isinstance(q, dict) and str(q.get("id") or "") == str(question_id or "")
                    for q in (questions or [])
                )
                if will_remove:
                    self._push_undo()
            except Exception:
                pass
            self.current_project["questions"] = [
                q for q in questions if q.get("id") != question_id
            ]
            
            return self.save_project()
            
        except Exception as e:
            print(f"Error deleting question {question_id}: {e}")
            return False

    def duplicate_question(self, question_id: str) -> str:
        if not self.current_project:
            return ""
        try:
            questions = self.current_project.get("questions", []) or []
        except Exception:
            questions = []
        if not isinstance(questions, list) or not question_id:
            return ""

        try:
            import copy
            import uuid

            idx = -1
            src = None
            for i, q in enumerate(questions):
                if isinstance(q, dict) and str(q.get("id") or "") == str(question_id):
                    idx = i
                    src = q
                    break
            if idx < 0 or not isinstance(src, dict):
                return ""

            existing = set()
            for q in questions:
                if isinstance(q, dict):
                    qid = str(q.get("id") or "").strip()
                    if qid:
                        existing.add(qid)
            new_id = f"q_{uuid.uuid4().hex[:10]}"
            while new_id in existing:
                new_id = f"q_{uuid.uuid4().hex[:10]}"

            dup = copy.deepcopy(src)
            dup["id"] = new_id
            try:
                self._push_undo()
            except Exception:
                pass
            questions.insert(idx + 1, dup)
            self.current_project["questions"] = questions
            ok = self.save_project(self.current_project)
            return new_id if ok else ""
        except Exception:
            return ""
    
    def add_media_file(self, file_path: str, file_name: str) -> Optional[str]:
        """Add a media file to current project"""
        if not self.current_project:
            return None
        
        try:
            project_id = self.current_project["id"]
            project_dir = self.projects_dir / project_id
            media_dir = project_dir / "media"
            
            # Copy file to project media directory
            dest_path = media_dir / file_name
            shutil.copy2(file_path, dest_path)
            
            # Add to project metadata
            if "media_files" not in self.current_project:
                self.current_project["media_files"] = []
            
            media_info = {
                "name": file_name,
                "path": str(dest_path.relative_to(project_dir)),
                "type": self._get_file_type(file_name),
                "added_at": datetime.now().isoformat()
            }
            
            self.current_project["media_files"].append(media_info)
            self.save_project()
            
            return str(dest_path)
            
        except Exception as e:
            print(f"Error adding media file: {e}")
            return None
    
    def update_game_config(self, config: Dict) -> bool:
        """Update game configuration"""
        if not self.current_project:
            return False

        try:
            try:
                self.push_undo_state()
            except Exception:
                pass
            self.current_project["game_config"] = config
            return self.save_project()

        except Exception as e:
            print(f"Error updating game config: {e}")
            return False

    def rename_project(self, project_id: str, new_name: str) -> Dict:
        """Doi ten project: kiem tra trung ten + hoan tac duoc.

        Tra ve project dict da luu; nem ValueError khi ten rong/trung.
        """
        clean = str(new_name or "").strip()
        if not clean:
            raise ValueError("Tên dự án không được để trống.")
        pid = str(project_id or "").strip()
        if not pid:
            raise ValueError("Thiếu id dự án.")
        if self.is_project_name_taken(clean, exclude_id=pid):
            raise ValueError(
                f'Đã có dự án tên "{clean}" trên máy này. '
                "Vui lòng chọn tên khác."
            )
        data = self.load_project(pid)
        if not isinstance(data, dict):
            raise ValueError("Không tìm thấy dự án để đổi tên.")
        try:
            self.push_undo_state()
        except Exception:
            pass
        data["name"] = clean
        if not self.save_project(data):
            raise ValueError("Không lưu được tên mới.")
        return self.current_project or data
    
    def get_current_project(self) -> Optional[Dict]:
        """Get current project"""
        return self.current_project
    
    def set_current_project(self, project_data: Dict):
        """Set current project"""
        self.current_project = project_data
        try:
            self.clear_history()
        except Exception:
            pass
    
    def _generate_project_id(self, name: str) -> str:
        """Generate unique project ID"""
        import uuid
        safe_name = "".join(c for c in name if c.isalnum() or c in "_- ").replace(" ", "_")
        return f"{safe_name}_{uuid.uuid4().hex[:8]}"
    
    def _get_default_game_config(self, game_type: str) -> Dict:
        """Get default game configuration"""
        if game_type == "fishing":
            return {
                "background_music": "assets/sound/background.mp3",
                "correct_sound": "assets/sound/correct.wav",
                "wrong_sound": "assets/sound/wrong.wav",
                "fish_objects": [
                    {"sprite": "assets/kenney_platformer-kit/PNG/Default/fish_blue.png", "wrong_sprite": "assets/kenney_platformer-kit/PNG/Default/fish_blue_skeleton.png", "sound": "assets/sound/click.wav", "tag": "fish"},
                    {"sprite": "assets/kenney_platformer-kit/PNG/Default/fish_green.png", "wrong_sprite": "assets/kenney_platformer-kit/PNG/Default/fish_green_skeleton.png", "sound": "assets/sound/click.wav", "tag": "fish"},
                    {"sprite": "assets/kenney_platformer-kit/PNG/Default/fish_orange.png", "wrong_sprite": "assets/kenney_platformer-kit/PNG/Default/fish_orange_skeleton.png", "sound": "assets/sound/click.wav", "tag": "fish"}
                ],
                "speed": 5,
                "score_per_fish": 10,
                "time_limit": 60
            }
        else:  # quiz_classic
            return {
                "background_music": "assets/sound/background.mp3",
                "correct_sound": "assets/sound/correct.wav",
                "wrong_sound": "assets/sound/wrong.wav",
                "time_per_question": 30,
                "show_explanation": True,
                "randomize_questions": True
            }
    
    def _get_file_type(self, file_name: str) -> str:
        """Get file type based on extension"""
        ext = file_name.lower().split('.')[-1] if '.' in file_name else ''
        
        image_exts = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg']
        audio_exts = ['mp3', 'wav', 'ogg', 'm4a']
        video_exts = ['mp4', 'avi', 'mov', 'wmv', 'flv']
        
        if ext in image_exts:
            return "image"
        elif ext in audio_exts:
            return "audio"
        elif ext in video_exts:
            return "video"
        else:
            return "other"
"""
Nguyen-Thanh-Tan ¬_¬
"""
