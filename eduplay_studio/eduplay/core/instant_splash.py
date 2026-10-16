"""Instant splash screen - hien NGAY LAP TUC khi bam mo app.

Module nay CHI duoc dung stdlib (tkinter/threading/os/sys/time) de cua so
hien len trong <1s, truoc moi import nang (PySide6/WebEngine). Tuyet doi
KHONG import bat ky module eduplay nao o day de tranh keo theo import nang.

Lifecyle:
    app.py -> instant_splash.show()      # dau tien, truoc PySide6
           -> ... import nang, tao MainWindow ...
           -> main_window.showMaximized()
           -> instant_splash.finish()    # hieu ung ket thuc (fade out)

Splash chay tren daemon thread rieng nen main thread co block khi import
thi cua so van hien. Moi thao tac tu main thread deu qua queue + after().

HAI LUOI AN TOAN DA THEM (giu nguyen giao dien goc):
1. _play_finish() KHONG goi root.quit() nua. Tk_Quit() goi ben trong
   after-callback tren thread KHONG phai main lam Tcl mat rang async handler,
   nen khi process tat Tk in "Tcl_AsyncDelete: async handler deleted by the
   wrong thread" roi abort (0x80000003). Bay gi chi return: pump het len
   reschedule, Tk mainloop tu thoat binh thuong roi finally cua thread
   splash moi destroy root tren DUNG thread do.
2. _abort_and_join() + atexit: neu app ket thuc khong di qua finish(), ap
   dung viec dung vong lap cua splash va join thread truoc khi interpreter
   tat, de root luon duoc huy tren thread tao ra no.
Moi ham deu try/except, khong bao gio lam crash app.
"""
import os
import sys
import threading
import time

try:
    import queue as _queue
except Exception:  # pragma: no cover
    import Queue as _queue  # type: ignore

BRAND = "#7F56D9"
BG = "#FFFFFF"
TEXT_DARK = "#0F172A"
TEXT_MUTED = "#64748B"

# i18n noi bo (stdlib-only nen khong dung duoc eduplay i18n o day;
# cac chuoi nay duoc mirror sang eduplay/resources/i18n/*.json khoa splash.*).
STRINGS = {
    "vi": {
        "starting": "Đang khởi động…",
        "loading_ui": "Đang tải giao diện…",
        "opening": "Đang mở EduPlay Studio…",
        "done": "Hoàn tất!",
    },
    "en": {
        "starting": "Starting…",
        "loading_ui": "Loading interface…",
        "opening": "Opening EduPlay Studio…",
        "done": "Done!",
    },
    "fr": {
        "starting": "Démarrage…",
        "loading_ui": "Chargement de l’interface…",
        "opening": "Ouverture d’EduPlay Studio…",
        "done": "Terminé !",
    },
    "es": {
        "starting": "Iniciando…",
        "loading_ui": "Cargando la interfaz…",
        "opening": "Abriendo EduPlay Studio…",
        "done": "¡Listo!",
    },
    "de": {
        "starting": "Wird gestartet…",
        "loading_ui": "Oberfläche wird geladen…",
        "opening": "EduPlay Studio wird geöffnet…",
        "done": "Fertig!",
    },
}
SUPPORTED_LANGS = ("vi", "en", "fr", "es", "de")

_lock = threading.RLock()
_state = {
    "thread": None,
    "queue": None,
    "ready": False,
    "shown": False,
    "finished": False,
    "abort": False,
}


def _disabled() -> bool:
    try:
        if str(os.environ.get("EDUPLAY_NO_SPLASH") or "").strip() in ("1", "true", "yes"):
            return True
    except Exception:
        pass
    try:
        if "--preview-runner" in (sys.argv or []):
            return True
    except Exception:
        pass
    return False


def _normalize_lang(code) -> str:
    try:
        s = str(code or "").strip().lower().replace("_", "-")
    except Exception:
        s = ""
    head = s.split("-")[0]
    if head in SUPPORTED_LANGS:
        return head
    return "en"


def _read_saved_language():
    """Doc app_language trong settings.json (nguoi dung da chon tu lan truoc).

    Chi dung stdlib + plain open, khong import eduplay.* de giu khoi dong nhanh.
    Tra ve ma ngon ngu hoac "" neu chua co."""
    try:
        home = os.path.expanduser("~") or ""
    except Exception:
        home = ""
    doc_bases = []
    try:
        for _k in ("OneDriveCommercial", "OneDrive", "OneDriveConsumer"):
            try:
                _v = os.environ.get(_k) or ""
            except Exception:
                _v = ""
            if _v and str(_v).strip():
                doc_bases.append(os.path.join(str(_v).strip(), "Documents"))
    except Exception:
        pass
    if home:
        doc_bases.append(os.path.join(home, "OneDrive", "Documents"))
        doc_bases.append(os.path.join(home, "Documents"))
    seen = set()
    for base in doc_bases:
        try:
            cand = os.path.join(base, "EduPlay", "Settings", "settings.json")
        except Exception:
            continue
        if cand in seen:
            continue
        seen.add(cand)
        try:
            if not os.path.exists(cand):
                continue
        except Exception:
            continue
        try:
            with open(cand, "r", encoding="utf-8", errors="ignore") as f:
                import json as _json
                data = _json.loads(f.read() or "{}")
        except Exception:
            continue
        try:
            lang = str((data or {}).get("app_language") or "").strip()
        except Exception:
            lang = ""
        if lang:
            return _normalize_lang(lang)
    return ""


def _system_lang() -> str:
    """Ngon ngu cua may (dung cho lan chay dau tien)."""
    try:
        import locale as _locale
        loc = (_locale.getdefaultlocale()[0] or "")
        if loc:
            return _normalize_lang(loc)
    except Exception:
        pass
    try:
        import ctypes as _ctypes
        buf = _ctypes.create_unicode_buffer(85)
        if _ctypes.windll.kernel32.GetUserDefaultLocaleName(buf, 85):
            return _normalize_lang(buf.value)
    except Exception:
        pass
    return "en"


def _resolve_lang() -> str:
    """Uu tien: ngon ngu nguoi dung da chon > ngon ngu may."""
    try:
        saved = _read_saved_language()
        if saved:
            return saved
    except Exception:
        pass
    try:
        return _system_lang()
    except Exception:
        return "en"


def tr(key: str, lang=None) -> str:
    try:
        l = _normalize_lang(lang) if lang else get_lang()
        return STRINGS.get(l, STRINGS["en"]).get(str(key or ""), STRINGS["en"].get(str(key or ""), ""))
    except Exception:
        return ""


def get_lang() -> str:
    try:
        with _lock:
            l = str(_state.get("lang") or "")
        if l in SUPPORTED_LANGS:
            return l
    except Exception:
        pass
    return "en"


def _resource_path(*parts: str) -> str:
    """Tim file resource ca khi chay dev lan Nuitka frozen (khong raise)."""
    try:
        cands = []
        try:
            exe_base = os.path.basename(str(sys.executable or "")).lower()
            frozen = bool(getattr(sys, "frozen", False) or (exe_base and "python" not in exe_base))
        except Exception:
            frozen = False
        if frozen:
            try:
                cands.append(os.path.join(os.path.dirname(os.path.abspath(sys.executable)), *parts))
            except Exception:
                pass
        try:
            here = os.path.dirname(os.path.abspath(__file__))
            # eduplay/core/instant_splash.py -> eduplay/...
            cands.append(os.path.join(os.path.dirname(os.path.dirname(here)), *parts))
        except Exception:
            pass
        for c in cands:
            try:
                if c and os.path.exists(c):
                    return c
            except Exception:
                continue
    except Exception:
        pass
    return ""


def _splash_thread_main(q, logo_path: str, lang: str) -> None:
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception:
        return
    try:
        lang = _normalize_lang(lang)
    except Exception:
        lang = "en"
    try:
        _t = STRINGS.get(lang, STRINGS["en"])
    except Exception:
        _t = STRINGS["en"]
    root = None
    try:
        root = tk.Tk()
    except Exception:
        return
    try:
        root.withdraw()
        try:
            root.overrideredirect(True)
        except Exception:
            pass
        try:
            root.attributes("-topmost", True)
        except Exception:
            pass
        try:
            root.configure(bg=BG)
        except Exception:
            pass
        W, H = 460, 320
        try:
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            x = max(0, int((sw - W) / 2))
            y = max(0, int((sh - H) / 2))
            root.geometry(f"{W}x{H}+{x}+{y}")
        except Exception:
            x, y = 0, 0
        # KHOA CUNG kich thuoc: noi dung doi (chu dai/ngan, bar doi mode)
        # khong duoc lam cua so co gian giua chung.
        try:
            root.minsize(W, H)
            root.maxsize(W, H)
            root.resizable(False, False)
        except Exception:
            pass

        try:
            outer = tk.Frame(root, bg=BRAND, padx=2, pady=2)
            # Tat co gian theo noi dung: overrideredirect bo qua min/maxsize
            # cua window manager nen phai khoa tu frame ben trong.
            try:
                outer.pack_propagate(False)
                outer.configure(width=W, height=H)
            except Exception:
                pass
            outer.pack(fill="both", expand=True)
            body = tk.Frame(outer, bg=BG)
            try:
                body.pack_propagate(False)
                body.configure(width=W - 4, height=H - 4)
            except Exception:
                pass
            body.pack(fill="both", expand=True)
        except Exception:
            body = root

        # Logo
        logo_img = None
        try:
            if logo_path:
                logo_img = tk.PhotoImage(file=logo_path)
                try:
                    w, h = int(logo_img.width()), int(logo_img.height())
                    if w > 128 or h > 128:
                        fx = max(1, w // 128)
                        fy = max(1, h // 128)
                        f = max(fx, fy)
                        if f > 1:
                            logo_img = logo_img.subsample(f, f)
                except Exception:
                    pass
        except Exception:
            logo_img = None
        try:
            if logo_img is not None:
                _state["logo_ref"] = logo_img  # chong GC
                tk.Label(body, image=logo_img, bg=BG).pack(pady=(26, 6))
            else:
                tk.Label(body, text="E", font=("Segoe UI", 64, "bold"), fg=BRAND, bg=BG).pack(pady=(18, 0))
        except Exception:
            pass
        try:
            tk.Label(body, text="EDUPLAY STUDIO", font=("Segoe UI", 20, "bold"), fg=TEXT_DARK, bg=BG).pack()
            tk.Label(body, text="Học. Tạo. Chơi.", font=("Segoe UI", 11), fg=TEXT_MUTED, bg=BG).pack(pady=(0, 10))
        except Exception:
            pass
        try:
            bar = ttk.Progressbar(body, mode="indeterminate", length=340)
            bar.pack(pady=(4, 6))
            try:
                bar.start(12)
            except Exception:
                pass
        except Exception:
            bar = None
        try:
            status = tk.Label(body, text=_t.get("starting", "Starting…"), font=("Segoe UI", 10), fg=TEXT_MUTED, bg=BG,
                              wraplength=400, justify="center", width=52)
            status.pack(pady=(0, 8))
        except Exception:
            status = None

        box = {"root": root, "bar": bar, "status": status, "W": W, "H": H, "x": x, "y": y}
        with _lock:
            _state["box"] = box
            _state["ready"] = True
        try:
            root.deiconify()
        except Exception:
            pass

        def _pump():
            try:
                while True:
                    try:
                        job = q.get_nowait()
                    except Exception:
                        break
                    try:
                        kind = job[0]
                        if kind == "status" and status is not None:
                            try:
                                status.config(text=str(job[1] or ""))
                            except Exception:
                                pass
                        elif kind == "abort":
                            return
                        elif kind == "hide":
                            # An tam khi co cua so EduPlay khac hien
                            # (vd hop chon ngon ngu lan dau mo app).
                            try:
                                root.withdraw()
                            except Exception:
                                pass
                        elif kind == "reshow":
                            try:
                                root.deiconify()
                                try:
                                    root.attributes("-topmost", True)
                                except Exception:
                                    pass
                                try:
                                    root.lift()
                                except Exception:
                                    pass
                            except Exception:
                                pass
                        elif kind == "finish":
                            try:
                                _play_finish(root, bar, status, str(job[1] or ""))
                            except Exception:
                                pass
                            return
                    except Exception:
                        continue
            except Exception:
                pass
            try:
                root.after(30, _pump)
            except Exception:
                pass

        try:
            root.after(30, _pump)
        except Exception:
            pass
        try:
            root.mainloop()
        except Exception:
            pass
    finally:
        try:
            # Giai phong anh logo ngay tren thread splash de __del__
            # chay dung thread Tcl (tranh warning luc tat process).
            with _lock:
                _logo = _state.pop("logo_ref", None)
            if _logo is not None:
                try:
                    del _logo
                except Exception:
                    pass
        except Exception:
            pass
        try:
            # Xa het callback/timer dang cho tren dung thread truoc khi huy.
            if root is not None:
                try:
                    root.update_idletasks()
                except Exception:
                    pass
                try:
                    root.update()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if root is not None:
                root.destroy()
        except Exception:
            pass
        with _lock:
            _state["ready"] = False
            _state["box"] = None


def _play_finish(root, bar, status, done_text: str) -> None:
    """Hieu ung ket thuc: day bar 100% + fade out (~0.45s) roi dong.

    KHONG duoc goi root.quit() o day: ham nay chay ben trong after-callback cua
    Tk tren thread khong phai main thread. Tk_Quit() o trong timer callback tren
    thread phu lam Tcl mat rang async handler, nen khi process tat Tk in
    'Tcl_AsyncDelete: async handler deleted by the wrong thread' va abort
    (0x80000003). Thay vao do ta return, pump het len reschedule nen mainloop
    tu thoat binh thuong roi finally cua thread splash moi destroy root.
    """
    # Giu nguyen kich thuoc/vi tri trong luc ket thuc.
    try:
        root.minsize(460, 320)
        root.maxsize(460, 320)
        root.resizable(False, False)
    except Exception:
        pass
    try:
        if bar is not None:
            try:
                bar.stop()
            except Exception:
                pass
            try:
                bar.config(mode="determinate", maximum=100, value=100)
                root.update_idletasks()
            except Exception:
                pass
    except Exception:
        pass
    try:
        if status is not None:
            status.config(text=done_text or "Hoàn tất!")
            root.update_idletasks()
    except Exception:
        pass
    try:
        time.sleep(0.12)
    except Exception:
        pass
    try:
        steps = 12
        for i in range(steps, -1, -1):
            try:
                root.attributes("-alpha", i / float(steps))
            except Exception:
                break
            try:
                root.update()
            except Exception:
                break
            try:
                time.sleep(0.03)
            except Exception:
                break
    except Exception:
        pass
    # KHONG root.quit() -> xem ghi chu ham. Pump se ngung reschedule,
    # mainloop tu thoat va finally cua thread splash goi root.destroy().


def show() -> bool:
    """Hien splash ngay lap tuc. Tra ve True neu da bat dau hien."""
    try:
        if _disabled():
            return False
        with _lock:
            if _state.get("shown"):
                return True
            try:
                lang = _resolve_lang()
            except Exception:
                lang = "en"
            _state["lang"] = lang
            _state["shown"] = True
            _state["finished"] = False
            _state["abort"] = False
            q = _queue.Queue()
            _state["queue"] = q
        try:
            logo = _resource_path("eduplay", "resources", "icons", "icon.png")
        except Exception:
            logo = ""
        t = threading.Thread(
            target=_splash_thread_main, args=(q, logo, lang),
            name="eduplay-instant-splash", daemon=True,
        )
        with _lock:
            _state["thread"] = t
        try:
            t.start()
        except Exception:
            with _lock:
                _state["shown"] = False
            return False
        return True
    except Exception:
        return False


def set_status(text: str) -> None:
    try:
        with _lock:
            q = _state.get("queue")
            shown = bool(_state.get("shown"))
            finished = bool(_state.get("finished"))
        if not shown or finished or q is None:
            return
        try:
            q.put_nowait(("status", str(text or "")))
        except Exception:
            pass
    except Exception:
        pass


def set_status_key(key: str) -> None:
    """Dat trang thai theo khoa i18n (starting/loading_ui/opening/done)."""
    try:
        set_status(tr(key))
    except Exception:
        pass


def _post_job(kind: str) -> None:
    try:
        with _lock:
            q = _state.get("queue")
            shown = bool(_state.get("shown"))
            finished = bool(_state.get("finished"))
        if not shown or finished or q is None:
            return
        try:
            q.put_nowait((kind, ""))
        except Exception:
            pass
    except Exception:
        pass


def hide() -> None:
    """An tam splash khi co cua so EduPlay khac hien (vd hop chon ngon ngu).
    Thread van song; goi reshow() de hien lai, finish() de ket thuc."""
    _post_job("hide")


def reshow() -> None:
    """Hien lai splash sau khi cua so khac dong."""
    _post_job("reshow")


def set_progress(value) -> None:  # giu API, hien tai dung indeterminate
    try:
        set_status("")
    except Exception:
        pass


def finish(done_text=None) -> None:
    """Chay hieu ung ket thuc roi tat splash. Khong bao gio raise/block lau."""
    try:
        if done_text is None:
            try:
                done_text = tr("done")
            except Exception:
                done_text = "Done!"
    except Exception:
        done_text = "Done!"
    try:
        with _lock:
            q = _state.get("queue")
            shown = bool(_state.get("shown"))
            if not shown or _state.get("finished"):
                return
            _state["finished"] = True
        if q is None:
            return
        try:
            q.put_nowait(("finish", str(done_text or "")))
        except Exception:
            pass
        # cho hieu ung fade xong (toi da ~1.5s), khong block app
        try:
            t = None
            with _lock:
                t = _state.get("thread")
            if t is not None and t.is_alive():
                t.join(timeout=1.5)
        except Exception:
            pass
    except Exception:
        pass


def _abort_and_join(timeout: float = 4.0) -> bool:
    """Buoc splash Tk huy root tren DUNG thread tao no, roi join.

    Bat buoc khi app ket thuc khong qua finish(): interpreter thi giai phong
    Tk root o main thread, Tk in 'Tcl_AsyncDelete: async handler deleted by
    the wrong thread' va co the lam crash process ngay luc thoat.
    """
    try:
        with _lock:
            q = _state.get("queue")
            t = _state.get("thread")
            _state["abort"] = True
        if t is None:
            return True
        try:
            if t.is_alive() and q is not None:
                q.put_nowait(("abort", ""))
        except Exception:
            pass
        try:
            t.join(timeout=timeout)
        except Exception:
            pass
        try:
            return not t.is_alive()
        except Exception:
            return True
    except Exception:
        return False


try:
    import atexit as _atexit

    _atexit.register(_abort_and_join)
except Exception:
    pass