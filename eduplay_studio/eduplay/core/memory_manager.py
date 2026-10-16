"""
Memory Manager - 2 tang ro rang:
- LONG-TERM (profile, toi da 800 ky tu): CHI dac diem nguoi dung (ten,
  tuoi, vai tro, so thich, phong cach...), ngan gon dang "a | b | c".
  KHONG ghi chi tiet nguoi dung da lam gi / chua lam gi. Chi de AI dua
  vao do ma phan hoi cho hop y.
- SESSION (ngan han): 5 tin nhan NGUOI DUNG gan nhat (khong tinh tin
  phan hoi cua AI). Het 1 phien (dong app) -> tom tat vao long-term
  TRUOC, roi xoa sach session.
- Trong phien KHONG tu tom tat dan; chi tom tat 1 lan khi end_session().
- File bo nho RIENG chong mat: %APPDATA%/EduPlayStudio/ai_memory.json
  (Roaming AppData - trinh go cai dat khong xoa) + mirror settings.json
  va Documents/EduPlay/Settings/ai_memory.json de tuong thich cu
"""
import os
import re
import time
from typing import List, Dict, Any
from pathlib import Path

MAX_SUMMARY_CHARS = 800
MAX_MESSAGE_CHARS = 600
MAX_RECENT_MESSAGES = 5
MEMORY_DIRNAME = "EduPlayStudio"
MEMORY_FILENAME = "ai_memory.json"

# Tín hiệu HỒ SƠ người dùng -> được giữ trong summary dài hạn
# (tính cách, sở thích, thói quen, điều quan tâm, danh tính) - cả 5 ngôn ngữ.
_PROFILE_PATTERNS = (
    # --- Tiếng Việt (có dấu + không dấu) ---
    r"\btôi là\b", r"\btoi la\b", r"\bmình là\b", r"\bminh la\b",
    r"\btên tôi\b", r"\bten toi\b", r"\btên mình\b", r"\bten minh\b",
    r"\btôi tên\b", r"\btoi ten\b", r"\bmình tên\b", r"\bminh ten\b",
    r"\btôi \d+ tuổi\b", r"\btoi \d+ tuoi\b",
    r"\bmình \d+ tuổi\b", r"\bminh \d+ tuoi\b",
    r"\bgọi tôi\b", r"\bgoi toi\b", r"\bgọi mình\b", r"\bgoi minh\b",
    r"\bhãy (nhớ|gọi|nho|goi)\b",
    r"\bnhớ (rằng|là|giúp|hộ) (tôi|mình)\b", r"\bnho (rang|la|giup|ho) (toi|minh)\b",
    r"\btôi (thích|không thích|ghét|muốn|quan tâm|hay|thường|đang dạy|dạy)\b",
    r"\btoi (thich|khong thich|ghet|muon|quan tam|hay|thuong|dang day|day)\b",
    r"\bmình (thích|không thích|muốn|quan tâm|hay|thường)\b",
    r"\bminh (thich|khong thich|muon|quan tam|hay|thuong)\b",
    r"\bsở thích\b", r"\bso thich\b", r"\bsở trường\b", r"\bso truong\b",
    r"\bphong cách\b", r"\bphong cach\b", r"\btính cách\b", r"\btinh cach\b",
    r"\bgu của (tôi|mình|toi|minh)\b",
    r"\bquan tâm (đến|tới)\b", r"\bquan tam (den|toi)\b",
    # --- English ---
    r"\bi am\b", r"\bmy name is\b", r"\bmy name's\b", r"\bcall me\b",
    r"\bi['’]m \d+\b",
    r"\bi (like|love|hate|prefer|want|teach)\b", r"\bremember that i\b",
    r"\bmy (hobby|hobbies|style|personality|favorite)\b",
    # --- Français ---
    r"\bje suis\b", r"\bje m'appelle\b", r"\bmon nom est\b",
    r"\bj'ai \d+ ans\b",
    r"\bappelle-moi\b", r"\bsouviens-toi que\b",
    r"\bj['’]aime\b", r"\bje (aime|adore|déteste|deteste|veux|préfère|prefere|enseigne)\b",
    r"\bje n['’]aime pas\b",
    r"\bmes (goûts|gouts|préférences|preferences|hobbies)\b",
    r"\bma personnalité\b", r"\bmon style\b", r"\bje m['’]intéresse\b",
    # --- Español ---
    r"\bme llamo\b", r"\bmi nombre es\b", r"\bllámame\b", r"\bllamame\b",
    r"\btengo \d+ años\b",
    r"\brecuerda que (yo|soy)\b",
    r"\bsoy (profesor|profesora|maestro|maestra|docente|estudiante|alumno|alumna)\b",
    r"\bme (gusta|gustan|encanta|encantan|interesa|interesan)\b", r"\bno me (gusta|gustan)\b",
    r"\b(yo )?(odio|quiero|prefiero|enseño|enseno)\b",
    r"\bmis (gustos|aficiones|hobbies)\b",
    r"\bmi (personalidad|estilo|favorito)\b",
    # --- Deutsch ---
    r"\bich bin\b", r"\bich heiße\b", r"\bich heisse\b",
    r"\bmein name ist\b", r"\bnenn mich\b", r"\berinnere dich,? dass\b",
    r"\bich (mag|liebe|hasse|will|möchte|moechte|bevorzuge|unterrichte)\b",
    r"\bmeine (hobbys|interessen|persönlichkeit|personlichkeit)\b",
    r"\bmein (stil|lieblings)\b",
)
try:
    _PROFILE_RES = [re.compile(p, flags=re.IGNORECASE) for p in _PROFILE_PATTERNS]
except Exception:
    _PROFILE_RES = []

# "Tôi muốn..." + động từ task một lần -> KHÔNG phải sở thích dài hạn (5 ngôn ngữ).
_TASK_AFTER_WANT = (
    "tạo", "tao", "thêm", "them", "tính", "tinh", "mở", "mo", "lưu", "luu",
    "xóa", "xoá", "xoa", "sửa", "sua", "liệt kê", "liet ke", "đếm", "dem",
    "xuất", "xuat", "nhập", "nhap", "chụp", "chup", "tìm", "tim",
    "create", "add", "calculate", "open", "save", "delete", "remove",
    "list", "count", "export", "import",
    "créer", "creer", "ajouter", "calculer", "ouvrir", "supprimer",
    "générer", "generer", "lister", "compter", "traduire", "résumer",
    "crear", "añadir", "anadir", "calcular", "abrir", "eliminar",
    "generar", "listar", "contar", "traducir", "resumir",
    "erstellen", "hinzufügen", "hinzufugen", "berechnen", "öffnen", "offnen",
    "löschen", "loschen", "generieren", "auflisten", "zählen", "zahlen",
    "übersetzen", "ubersetzen", "zusammenfassen",
)

# Task một lần -> không bao giờ vào summary dài hạn (5 ngôn ngữ).
_TASK_PATTERNS = (
    r"^\s*(tạo|tao|thêm|them|tính|tinh|mở|mo|open|lưu|luu|save|xóa|xoá|xoa|delete|sửa|sua|edit|liệt kê|liet ke|đếm|dem|hướng dẫn|huong dan|chụp|chup|tìm|tim|search|dịch|dich|tóm tắt|tom tat|tách|tach|tính toán)\b",
    r"^\s*(créer|creer|ajouter|calculer|ouvrir|supprimer|générer|generer|lister|compter|traduire|résumer|guide-moi|explique)\b",
    r"^\s*(crear|añadir|anadir|calcular|abrir|eliminar|generar|listar|contar|traducir|resumir|guíame|explica)\b",
    r"^\s*(erstellen|erstelle|hinzufügen|berechne|berechnen|öffne|öffnen|lösche|löschen|generiere|generieren|zusammenfassen|anleitung)\b",
    r"^\s*(create|add|calculate|open|save|delete|remove|list|count|export|import|generate|translate|summarize)\b",
    r"\b(câu hỏi|dự án|project|projet|proyecto|projekt|quiz|game|powerpoint|html|file|ảnh|hình ảnh|nhạc|điểm|thời gian|trộn|cấu hình|question|pregunta|frage)\b.*\b(tạo|thêm|tính|xóa|sửa|mở|lưu|xuất|nhập|créer|crée|supprime|ouvre|ajoute|crear|crea|generar|elimina|abre|erstellen|erstelle|berechnen|lösche|füge|create|delete|open|save)\b",
    r"^\s*[\d\+\-\*\/\%\^\(\)xX:×÷\s\.,]+\s*\??\s*$",
)
try:
    _TASK_RES = [re.compile(p, flags=re.IGNORECASE) for p in _TASK_PATTERNS]
except Exception:
    _TASK_RES = []

# Alias tương thích cũ (giữ để code khác import không vỡ; logic mới dùng _PROFILE_RES)
IMPORTANT_KEYWORDS = (
    "tôi là", "tên tôi", "gọi tôi", "tôi thích", "sở thích",
    "phong cách", "tính cách",
)


def _is_task_only(text: str) -> bool:
    """True nếu tin nhắn là task một lần (không phải hồ sơ người dùng)."""
    try:
        s = str(text or "").strip()
    except Exception:
        return True
    if not s:
        return True
    try:
        for rx in _TASK_RES:
            if rx.search(s):
                return True
    except Exception:
        pass
    return False


def _is_profile_text(text: str) -> bool:
    """True nếu câu chứa tín hiệu hồ sơ (tính cách/thói quen/quan tâm/danh tính).

    Ngoại lệ: 'tôi muốn/mình muốn' + động từ task một lần (tạo/tính/mở/xóa...)
    thì là yêu cầu việc, KHÔNG phải sở thích dài hạn.
    """
    try:
        s = str(text or "").strip()
    except Exception:
        return False
    if not s:
        return False
    try:
        low = s.lower()
    except Exception:
        low = ""
    try:
        matched = any(rx.search(s) for rx in _PROFILE_RES)
    except Exception:
        matched = False
    if not matched:
        return False
    # "tôi muốn / i want / je veux / quiero / ich will..." + task -> việc, không lưu
    try:
        _want_heads = []
        for _w in ("muốn", "muon", "want", "veux", "quiero", "will", "möchte", "mochte"):
            if _w in low:
                try:
                    _want_heads.append(low.split(_w, 1)[1][:40])
                except Exception:
                    continue
        if _want_heads and any(
            v in head for head in _want_heads for v in _TASK_AFTER_WANT
        ):
            return False
    except Exception:
        pass
    # đã là profile thì giữ lại (vd: "tôi thích quiz" vẫn là sở thích)
    return True


def _extract_profile_facts(text: str) -> List[str]:
    """Trich dac diem ho so trong tin nhan, loai bo menh de task.

    Tach tin thanh menh de (theo cau, phay, ;:|xuong dong); chi giu menh de
    co tin hieu profile VA khong phai task mot lan. Vd:
    "toi la giao vien, hay tao 5 cau hoi" -> giu "toi la giao vien",
    bo "hay tao 5 cau hoi".
    """
    try:
        s = str(text or "").strip()
    except Exception:
        return []
    if not s:
        return []
    try:
        chunks = re.split(r"[|;\n]+", s)
    except Exception:
        chunks = [s]
    facts: List[str] = []
    for chunk in chunks:
        try:
            c = str(chunk or "").strip()
        except Exception:
            continue
        if not c:
            continue
        try:
            sents = re.split(r"(?<=[.!?])\s+", c)
        except Exception:
            sents = [c]
        for sent in sents:
            t = str(sent or "").strip()
            if not t:
                continue
            try:
                clauses = [x.strip() for x in re.split(r"[,;:]+", t) if str(x or "").strip()]
            except Exception:
                clauses = [t]
            kept_any = False
            for clause in clauses:
                cc = str(clause or "").strip()
                if not cc or len(cc) > 140:
                    continue
                # menh de task (tao/tinh/mo/xoa...) khong bao gio vao profile
                try:
                    if _is_task_only(cc):
                        continue
                except Exception:
                    pass
                if _is_profile_text(cc):
                    facts.append(cc)
                    kept_any = True
            if not kept_any and len(clauses) <= 1 and len(t) <= 140:
                # ca cau ngan co tin hieu profile (vd: "toi la giao vien toan lop 5")
                try:
                    if _is_profile_text(t) and not _is_task_only(t):
                        facts.append(t)
                except Exception:
                    pass
    seen = set()
    out: List[str] = []
    for f in facts:
        k = f.strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(f.strip())
    return out


def _prune_summary(summary: str, max_chars: int = MAX_SUMMARY_CHARS) -> str:
    """Lọc summary cũ: chỉ giữ các đoạn hồ sơ, bỏ rác task một lần."""
    try:
        s = str(summary or "").strip()
    except Exception:
        return ""
    if not s:
        return ""
    try:
        segs = [x.strip() for x in re.split(r"\s*\|\s*", s) if str(x or "").strip()]
    except Exception:
        segs = [s]
    kept: List[str] = []
    for seg in segs:
        if _is_profile_text(seg):
            kept.append(seg[:140])
    out = " | ".join(kept).strip(" |")
    if len(out) > max_chars:
        out = out[-max_chars:].strip()
        if "|" in out:
            idx = out.find("|")
            if 0 <= idx < 100:
                out = out[idx + 1:].strip()
    return out

def resolve_memory_file() -> Path:
    """Đường dẫn file bộ nhớ riêng, nằm ngoài mọi thư mục mà trình
    gỡ cài đặt xóa (Program Files, LocalAppData, CommonAppData,
    Documents/EduPlay, registry app)."""
    try:
        base = os.environ.get("APPDATA")
        if base and str(base).strip():
            root = Path(str(base).strip())
        else:
            root = Path.home() / ".config"
        d = root / MEMORY_DIRNAME
        d.mkdir(parents=True, exist_ok=True)
        return d / MEMORY_FILENAME
    except Exception:
        try:
            return Path.home() / ("." + MEMORY_FILENAME)
        except Exception:
            return Path(os.getcwd()) / ("." + MEMORY_FILENAME)


class MemoryManager:
    def __init__(self, settings_manager=None):
        self.settings_manager = settings_manager
        self._memory_summary = ""
        self._session_messages: List[Dict[str, Any]] = []
        self._max_recent = MAX_RECENT_MESSAGES
        self._max_summary_chars = MAX_SUMMARY_CHARS
        self._load()

    def _settings_key(self) -> str:
        return "ai_memory"

    def _read_store(self, data) -> bool:
        """Nap 1 store (dict) vao memory. Tra ve True neu co du lieu.

        Tuong thich file cu {summary, recent[], summarized_ts}: summary loc
        1 lan ve chi con dac diem; recent chi lay tin user (bo tin AI cu).
        """
        try:
            if not isinstance(data, dict):
                return False
            summary = str(data.get("summary") or data.get("profile") or "").strip()
            rec = data.get("recent") or data.get("session") or []
            session = []
            if isinstance(rec, list):
                for r in rec:
                    try:
                        if not isinstance(r, dict):
                            continue
                        if str(r.get("role") or "").strip().lower() not in ("", "user"):
                            continue
                        content = str(r.get("content") or "").strip()
                        if not content:
                            continue
                        try:
                            ts = float(r.get("ts") or 0.0)
                        except Exception:
                            ts = 0.0
                        session.append({"role": "user", "content": content[:MAX_MESSAGE_CHARS], "ts": ts})
                    except Exception:
                        continue
            session = session[-self._max_recent:]
            if not summary and not session:
                return False
            try:
                summary = _prune_summary(summary, self._max_summary_chars)
            except Exception:
                summary = summary[: self._max_summary_chars]
            self._memory_summary = summary[: self._max_summary_chars]
            self._session_messages = session
            return True
        except Exception:
            return False

    def _load(self):
        # Ưu tiên 1: file bộ nhớ riêng (chống mất khi gỡ/cài lại)
        try:
            p = resolve_memory_file()
            if p.exists():
                import json
                j = json.loads(p.read_text(encoding="utf-8", errors="ignore") or "{}")
                if self._read_store(j):
                    return
        except Exception:
            pass
        # Ưu tiên 2: settings_manager
        try:
            if self.settings_manager:
                data = self.settings_manager.get(self._settings_key(), {}) or {}
                if self._read_store(data):
                    return
        except Exception:
            pass
        # Ưu tiên 3: file cũ trong Documents (tương thích bản cũ)
        if not self._memory_summary and not self._session_messages:
            try:
                from eduplay.core.path_resolver import PathResolver
                p = PathResolver.resolve_settings_dir() / "ai_memory.json"
                if p.exists():
                    import json
                    j = json.loads(p.read_text(encoding="utf-8", errors="ignore") or "{}")
                    self._read_store(j)
            except Exception:
                pass

    def _payload(self) -> dict:
        return {
            "summary": self._memory_summary,
            "recent": self._session_messages,
            "updated_at": time.time(),
        }

    def _save(self):
        try:
            if self.settings_manager:
                self.settings_manager.set(self._settings_key(), self._payload())
        except Exception:
            pass
        try:
            from eduplay.core.path_resolver import PathResolver
            import json
            p = PathResolver.resolve_settings_dir() / "ai_memory.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(self._payload(), ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        try:
            import json as _json
            p = resolve_memory_file()
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(_json.dumps(self._payload(), ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def add_message(self, role: str, content: str):
        """Them 1 tin NGUOI DUNG vao session (giu 5 tin gan nhat).

        Tin AI/system KHONG dem vao bo nho phien (theo spec: session chi
        tinh tin nhan nguoi dung). Trong phien khong tu tom tat.
        """
        try:
            role = str(role or "").strip().lower()
            content = str(content or "").strip()
            if not content:
                return
            if role != "user":
                return
            if len(content) > MAX_MESSAGE_CHARS:
                content = content[:MAX_MESSAGE_CHARS].rstrip() + "..."
            self._session_messages.append({"role": "user", "content": content, "ts": time.time()})
            self._session_messages = self._session_messages[-self._max_recent:]
            self._save()
        except Exception:
            pass

    def _summarize_into_memory(self, messages: List[Dict[str, Any]]):
        """Gop tin user vao profile dai han - CHI dac diem nguoi dung.

        - Chi xet tin user; menh de task mot lan (tao/xoa/tinh...) bi loai.
        - Dedup voi profile hien tai de khong phinh; cat 800 ky tu.
        """
        try:
            if not messages:
                return
            pieces = []
            for m in messages:
                try:
                    if not isinstance(m, dict):
                        continue
                    if str((m or {}).get("role") or "").strip().lower() not in ("", "user"):
                        continue
                    c = str((m or {}).get("content") or "").strip()
                except Exception:
                    continue
                if not c:
                    continue
                for fact in _extract_profile_facts(c):
                    try:
                        low_fact = fact.strip().lower()
                    except Exception:
                        continue
                    if not low_fact:
                        continue
                    try:
                        cur_low = str(self._memory_summary or "").lower()
                    except Exception:
                        cur_low = ""
                    try:
                        dup_old = any(
                            (low_fact in str(p or "").strip().lower())
                            or (str(p or "").strip().lower() in low_fact)
                            for p in pieces
                        )
                    except Exception:
                        dup_old = False
                    if low_fact in cur_low or dup_old:
                        continue
                    pieces.append(fact.strip())
            if not pieces:
                return
            new_part = " | ".join(pieces)
            if self._memory_summary:
                combined = (self._memory_summary + " | " + new_part).strip(" |")
            else:
                combined = new_part
            if len(combined) > self._max_summary_chars:
                combined = combined[-self._max_summary_chars:].strip()
                if "|" in combined:
                    idx = combined.find("|")
                    if idx != -1 and idx < 100:
                        combined = combined[idx+1:].strip()
            self._memory_summary = combined
        except Exception:
            pass

    def end_session(self) -> str:
        """Ket thuc 1 phien: tom tat session vao profile TRUOC, roi xoa session.

        Goi khi dong app. Tra ve profile hien tai.
        """
        try:
            try:
                self._summarize_into_memory(list(self._session_messages))
            except Exception:
                pass
            self._session_messages = []
            try:
                self._save()
            except Exception:
                pass
        except Exception:
            pass
        try:
            return str(self._memory_summary or "").strip()
        except Exception:
            return ""

    def get_recent(self, n: int = 5) -> List[Dict[str, str]]:
        """5 tin NGUOI DUNG gan nhat cua phien (khong gom tin AI)."""
        try:
            return list(self._session_messages[-n:])
        except Exception:
            return []

    def get_summary(self) -> str:
        try:
            return str(self._memory_summary or "").strip()
        except Exception:
            return ""

    def get_session_messages(self) -> List[Dict[str, Any]]:
        """Toan bo session hien tai (user-only, toi da 5)."""
        try:
            return list(self._session_messages)
        except Exception:
            return []

    def get_context_for_ai(self) -> Dict[str, Any]:
        """Tra ve context gon cho AI: profile dai han + 5 tin user gan nhat."""
        try:
            return {
                "memory_summary": self.get_summary(),
                "recent_messages": self.get_recent(5),
            }
        except Exception:
            return {"memory_summary": "", "recent_messages": []}

    def clear(self):
        """Xoa ca profile dai han + session (lenh xoa cua user)."""
        self._memory_summary = ""
        self._session_messages = []
        self._save()

    # Alias cho tương thích
    def add_user_message(self, content: str):
        self.add_message("user", content)

    def add_ai_message(self, content: str):
        """Khong luu (session chi tinh tin nhan nguoi dung). Giu de tuong thich."""
        return
