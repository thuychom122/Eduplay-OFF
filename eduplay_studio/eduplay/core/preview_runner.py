import sys
import os
import ctypes

_this_dir = os.path.dirname(os.path.abspath(__file__))
_eduplay_core_dir = _this_dir
_eduplay_dir = os.path.dirname(_eduplay_core_dir)
_eduplay_studio_dir = os.path.dirname(_eduplay_dir)
for _p in (_eduplay_studio_dir, _eduplay_dir, _eduplay_core_dir):
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)


def is_compiled_app() -> bool:
    """True when running from a frozen/compiled bundle (exe).

    Covers PyInstaller/cx_Freeze (sys.frozen / sys._MEIPASS) and Nuitka
    standalone/onefile, which sets neither: there the process executable
    is our own EduPlayStudio.exe, not python.exe/pythonw.exe.
    """
    try:
        if getattr(sys, "frozen", False):
            return True
    except Exception:
        pass
    try:
        if getattr(sys, "__compiled__", False):
            return True
    except Exception:
        pass
    try:
        if getattr(sys, "_MEIPASS", None):
            return True
    except Exception:
        pass
    try:
        base = os.path.basename(str(sys.executable or "")).lower()
        if base and "python" not in base:
            return True
    except Exception:
        pass
    return False


def normalize_windows_path(path) -> str:
    raw = str(path or "").replace("/", "\\")
    for prefix in ("\\\\?\\", "\\\\.\\"):
        if raw.startswith(prefix):
            raw = raw[len(prefix):]
            break
    return raw


def get_current_process_executable() -> str:
    if os.name != "nt":
        return str(sys.executable or "")
    try:
        buf = ctypes.create_unicode_buffer(512)
        ctypes.windll.kernel32.GetModuleFileNameW(None, buf, 512)
        result = buf.value
        if result and os.path.isfile(result):
            return result
    except Exception:
        pass
    return str(sys.executable or "")


def resolve_frozen_preview_executable(*, executable: str, argv0: str, cwd: str = "", process_exe: str = "") -> str:
    candidates = [process_exe, executable, argv0]
    for c in candidates:
        candidate = normalize_windows_path(c)
        if candidate and os.path.isfile(candidate):
            return candidate
    return ""


def resolve_frozen_preview_working_directory(*, executable: str, argv0: str, cwd: str) -> str:
    for c in [cwd, executable, argv0]:
        candidate = normalize_windows_path(c)
        if candidate and os.path.isdir(os.path.dirname(candidate)):
            return os.path.dirname(candidate)
    return ""


def build_preview_process_command(*, executable: str, uri: str, title: str, frozen: bool) -> tuple[str, list[str]]:
    program = str(executable or "")
    safe_uri = str(uri or "")
    safe_title = str(title or "EduPlay Preview")
    if frozen:
        return program, ["--preview-runner", safe_uri, safe_title]
    return program, ["-u", "-m", "eduplay.core.preview_runner", safe_uri, safe_title]


def _run_qt_preview(uri: str, title: str) -> bool:
    import multiprocessing as _mp
    _cores = _mp.cpu_count() or 4
    allow_autoplay = True
    _gpu_flags = (
        " --ignore-gpu-blocklist"
        " --enable-gpu --enable-gpu-rasterization --enable-zero-copy --enable-oop-rasterization"
        " --use-angle=d3d11 --enable-accelerated-2d-canvas --enable-accelerated-video-decode"
        f" --num-raster-threads={_cores} --renderer-process-limit={_cores} --max-active-webgl-contexts=16"
        " --enable-threaded-compositing --enable-features=Vulkan,CanvasOopRasterization"
        " --disable-gpu-watchdog"
        " --disable-background-timer-throttling"
        " --disable-renderer-backgrounding"
        " --disable-backgrounding-occluded-windows"
        " --disable-features=CalculateNativeWinOcclusion,IntensiveWakeUpThrottling"
    )
    base_flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
    autoplay_flag = "--autoplay-policy=no-user-gesture-required"
    # Always ensure GPU flags present, add autoplay only for quick preview
    needed = _gpu_flags + (f" {autoplay_flag}" if allow_autoplay else "")
    if needed.strip() not in base_flags:
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (needed.strip() + (" " + base_flags if base_flags else ""))
    elif allow_autoplay and autoplay_flag not in base_flags:
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (autoplay_flag + " " + base_flags)

    try:
        from PySide6.QtCore import QTimer, QUrl, Qt, QCoreApplication
        from PySide6.QtWidgets import QApplication, QMainWindow
        from PySide6.QtWebEngineWidgets import QWebEngineView
        try:
            from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile
        except Exception:
            from PySide6.QtWebEngineWidgets import QWebEngineSettings
            QWebEngineProfile = None
    except Exception:
        return False

    # Desktop GL như Chrome
    try:
        QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    except Exception:
        pass
    os.environ["QT_ANGLE_PLATFORM"] = "warp"
    os.environ["QSG_RENDER_LOOP"] = "threaded"
    for _k in ("QTWEBENGINE_DISABLE_GPU"):
        try:
            os.environ.pop(_k, None)
        except Exception:
            pass

    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)
    # Tận dụng RAM: tăng cache WebEngine lên 512MB, bật threaded
    try:
        from PySide6.QtWebEngineCore import QWebEngineProfile
        prof = QWebEngineProfile.defaultProfile()
        prof.setHttpCacheMaximumSize(512 * 1024 * 1024)
        prof.setPersistentStoragePath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "preview_cache"))
    except Exception:
        pass

    # Ensure the preview window shows the application icon (the app's global
    # window icon does not carry over into this separate process).
    try:
        from PySide6.QtGui import QIcon
        _icon_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icons")
        for _ext in ("ico", "png"):
            _ic = os.path.join(_icon_dir, "icon." + _ext)
            if os.path.exists(_ic):
                app.setWindowIcon(QIcon(_ic))
                break
    except Exception:
        pass

    window = QMainWindow()
    window.setWindowTitle(str(title or "EduPlay Preview"))
    window.resize(1280, 840)
    # Tránh chớp trắng 2 lần: nền tối, chưa show cho tới khi page load xong
    try:
        from PySide6.QtGui import QColor
        window.setStyleSheet("QMainWindow{background:#0b1020;}")
    except Exception:
        pass

    web_view = QWebEngineView()
    try:
        web_view.page().setBackgroundColor(QColor("#0b1020"))
    except Exception:
        try:
            from PySide6.QtGui import QColor as _QC
            web_view.page().setBackgroundColor(_QC("#0b1020"))
        except Exception:
            pass
    try:
        settings = web_view.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        # GPU-accelerated rendering — bật lại để tận dụng GPU, không để 2-3 fps CPU fallback
        try:
            settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        except Exception:
            pass
        try:
            settings.setAttribute(QWebEngineSettings.WebGLEnabled, True)
        except Exception:
            pass
        try:
            settings.setAttribute(QWebEngineSettings.Accelerated2DCanvasEnabled, True)
        except Exception:
            pass
        try:
            settings.setAttribute(QWebEngineSettings.DnsPrefetchEnabled, True)
        except Exception:
            pass
        if allow_autoplay:
            try:
                settings.setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, False)
            except Exception:
                pass
            try:
                QWebEngineSettings.defaultSettings().setAttribute(
                    QWebEngineSettings.PlaybackRequiresUserGesture, False
                )
            except Exception:
                pass
            try:
                profile = web_view.page().profile()
                if profile:
                    profile.settings().setAttribute(
                        QWebEngineSettings.PlaybackRequiresUserGesture, False
                    )
            except Exception:
                pass
    except Exception:
        pass
    try:
        web_view.page().setAudioMuted(False)
    except Exception:
        pass

    ready_state = {"printed": False}

    def _print_ready():
        if ready_state["printed"]:
            return
        ready_state["printed"] = True
        try:
            print("EDUPLAY_PREVIEW_READY", flush=True)
        except Exception:
            pass
        # Hiện cửa sổ 1 lần duy nhất khi game sẵn sàng — hết chớp 2 lần
        try:
            window.showMaximized()
            window.raise_()
            window.activateWindow()
        except Exception:
            try:
                window.show()
            except Exception:
                pass

    # Chỉ báo sẵn sàng khi load xong, không phải loadStarted + immediate
    try:
        web_view.loadFinished.connect(lambda ok: _print_ready() if ok else None)
    except Exception:
        pass
    # Fallback: nếu loadFinished không bắn (file://), báo sau 1.2s
    QTimer.singleShot(1200, _print_ready)

    window.setCentralWidget(web_view)
    # Chưa show ở đây — đợi loadFinished mới show
    try:
        web_view.setUrl(QUrl(str(uri or "")))
    except Exception:
        return False

    if owns_app:
        app.exec()
        return True

    try:
        app.exec()
    except Exception:
        return False
    return True


def _normalize_uri(uri: str) -> str:
    uri = str(uri or "").strip()
    if not uri:
        return uri
    if uri.startswith(("http://", "https://", "file://")):
        return uri
    # Assume local file path -> file:// URL
    try:
        from urllib.parse import urljoin, pathname2url
        return "file:///" + pathname2url(os.path.abspath(uri)).lstrip("/")
    except Exception:
        return "file:///" + uri.replace("\\", "/")


def _set_edge_browser_args():
    """Push Chromium switches into WebView2 via its env var.

    This is the ONLY reliable way to enable autoplay (audio) and GPU
    rasterization in Edge/WebView2 — simulated JS gestures are untrusted and
    do not satisfy the autoplay policy.
    """
    import multiprocessing as _mp
    _cores = _mp.cpu_count() or 4
    _args = (
        "--autoplay-policy=no-user-gesture-required"
        " --ignore-gpu-blocklist"
        " --enable-gpu --enable-gpu-rasterization --enable-zero-copy"
        " --use-angle=d3d11 --enable-accelerated-2d-canvas --enable-accelerated-video-decode"
        f" --num-raster-threads={_cores} --renderer-process-limit={_cores}"
        " --disable-background-timer-throttling --disable-renderer-backgrounding"
        " --disable-backgrounding-occluded-windows"
        " --disable-features=CalculateNativeWinOcclusion,IntensiveWakeUpThrottling"
    )
    try:
        os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = _args
    except Exception:
        pass
    # Keep WebView2 from re-using a stuck user-data dir across runs
    try:
        _udd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "preview_edge_profile")
        os.environ["WEBVIEW2_USER_DATA_FOLDER"] = os.path.abspath(_udd)
    except Exception:
        pass


def _run_edge_preview(uri: str, title: str) -> bool:
    try:
        import webview
    except Exception as e:
        print("pywebview is not installed:", e)
        return False
    _set_edge_browser_args()

    _uri = _normalize_uri(uri)
    _title = str(title or "EduPlay Preview")

    def _ready():
        try:
            print("EDUPLAY_PREVIEW_READY", flush=True)
        except Exception:
            pass

    try:
        webview.create_window(
            _title,
            url=_uri,
            easy_drag=False,
            maximized=True,
            background_color="#0b1020",
        )
    except TypeError:
        try:
            webview.create_window(_title, url=_uri, easy_drag=False, maximized=True)
        except TypeError:
            webview.create_window(_title, url=_uri)

    try:
        webview.start(_ready, gui="edgechromium", debug=False)
    except Exception as e:
        print("Edge preview failed:", e)
        return False
    return True


def main():
    argv = list(sys.argv[1:])
    if argv and argv[0] == "--preview-runner":
        argv = argv[1:]
    if len(argv) < 1:
        print("Usage: python -m eduplay.core.preview_runner <file_or_url> [title]")
        sys.exit(1)
    uri = argv[0]
    title = argv[1] if len(argv) > 1 else "EduPlay Preview"

    # Primary: native Edge / WebView2 (same engine as Chrome) — no flicker,
    # no lag, full audio via autoplay-policy switch.
    try:
        if _run_edge_preview(uri, title):
            return
    except Exception as e:
        print("Edge preview failed:", e)

    # Fallback: Qt WebEngine
    try:
        if _run_qt_preview(uri, title):
            return
    except Exception as e:
        print("Qt preview fallback failed:", e)

    print("All preview backends failed.")
    sys.exit(3)

if __name__ == "__main__":
    main()

