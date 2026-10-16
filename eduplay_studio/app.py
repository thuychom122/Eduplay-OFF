from __future__ import annotations

import os
import sys
from pathlib import Path


def _bootstrap_third_party_py() -> None:
    candidates = []
    # Nuitka exe sets neither sys.frozen nor sys.__compiled__: fall back
    # to exe-name check (our exe is not python.exe/pythonw.exe).
    try:
        _exe_base = os.path.basename(str(sys.executable or "")).lower()
        _frozen = bool(getattr(sys, "frozen", False) or (_exe_base and "python" not in _exe_base))
    except Exception:
        _frozen = bool(getattr(sys, "frozen", False))
    if _frozen:
        candidates.append(Path(sys.executable).resolve().parent / "third_party_py")
    candidates.append(Path(__file__).resolve().parent / "third_party_py")

    for candidate in candidates:
        if not candidate.is_dir():
            continue
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)


_bootstrap_third_party_py()

# OneDrive-aware file access: patch open/Path.exists to handle file://, %20, 8.3, Files On-Demand, junctions
try:
    from eduplay.core import path_resolver as _pr
    if hasattr(_pr, "install_global_patches"):
        _pr.install_global_patches()
    elif hasattr(_pr.PathResolver, "install_global_patches"):
        _pr.PathResolver.install_global_patches()
except Exception:
    pass

# Crash log cho ban build exe (dist) chay voi --windows-console-mode=disable:
# khi khong co console, moi exception se lam exe "tudong tat" ma khong de lai
# dau vet. Khoi nay (stdlib-only) ghi moi loi khong bat duoc ra file log de
# nguoi dung/ky thuat mo ra xem thay vi doan mo.
_CRASH_LOG_DIR = None

def _crash_log_dir():
    global _CRASH_LOG_DIR
    if _CRASH_LOG_DIR is not None:
        return _CRASH_LOG_DIR
    candidates = []
    try:
        base = os.environ.get("LOCALAPPDATA") or ""
        if base.strip():
            candidates.append(Path(base) / "EduPlayStudio" / "logs")
    except Exception:
        pass
    try:
        home = os.path.expanduser("~") or ""
        if home.strip():
            candidates.append(Path(home) / "Documents" / "EduPlay" / "Settings" / "logs")
    except Exception:
        pass
    try:
        import tempfile as _tf
        candidates.append(Path(_tf.gettempdir()) / "EduPlayStudio" / "logs")
    except Exception:
        pass
    for cand in candidates:
        try:
            cand.mkdir(parents=True, exist_ok=True)
            _CRASH_LOG_DIR = cand
            return cand
        except Exception:
            continue
    _CRASH_LOG_DIR = Path(".")
    return _CRASH_LOG_DIR


def _write_crash_log(title: str, detail: str = "") -> str:
    try:
        import traceback as _tb
        import datetime as _dt
        log_dir = _crash_log_dir()
        stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        body = f"[{stamp}] {title}\n{detail or ''}\n{'-' * 60}\n"
        try:
            with open(log_dir / "crash.log", "a", encoding="utf-8", errors="replace") as f:
                f.write(body)
        except Exception:
            pass
        try:
            day = _dt.datetime.now().strftime("%Y%m%d")
            with open(log_dir / f"crash-{day}.log", "a", encoding="utf-8", errors="replace") as f:
                f.write(body)
        except Exception:
            pass
        return str(log_dir / "crash.log")
    except Exception:
        return ""


def _install_crash_handlers() -> None:
    try:
        import faulthandler as _fh
        import threading as _th
        try:
            _fh.enable()
        except Exception:
            pass
        try:
            log_dir = _crash_log_dir()
            _fh_file = open(log_dir / "faulthandler.log", "a", encoding="utf-8", errors="replace")
            try:
                # Giu handle suot doi app (tranh ResourceWarning + dam bao ghi duoc)
                globals()["_FH_LOG_FILE"] = _fh_file
            except Exception:
                pass
            try:
                _fh.enable(file=_fh_file)
            except Exception:
                try:
                    _fh_file.close()
                except Exception:
                    pass
                try:
                    globals().pop("_FH_LOG_FILE", None)
                except Exception:
                    pass
        except Exception:
            pass
    except Exception:
        pass

    def _hook(exc_type, exc_value, exc_tb):
        try:
            import traceback as _tb
            detail = "".join(_tb.format_exception(exc_type, exc_value, exc_tb))
        except Exception:
            detail = str(exc_value) if exc_value is not None else ""
        try:
            _write_crash_log(f"UNCAUGHT {getattr(exc_type, '__name__', exc_type)}: {exc_value}", detail)
        except Exception:
            pass
        try:
            sys.__excepthook__(exc_type, exc_value, exc_tb)
        except Exception:
            pass

    try:
        sys.excepthook = _hook
    except Exception:
        pass

    try:
        def _unraisable_hook(args):
            try:
                _hook(args.exc_type, args.exc_value, args.exc_traceback)
            except Exception:
                pass

        sys.unraisablehook = _unraisable_hook
    except Exception:
        pass

    try:
        import threading as _th

        def _thread_hook(args):
            try:
                _hook(args.exc_type, args.exc_value, args.exc_traceback)
            except Exception:
                pass

        _th.excepthook = _thread_hook
    except Exception:
        pass


_install_crash_handlers()

# Windows consoles (and Python's default cp1252 encoding) cannot print
# Vietnamese characters. Reconfigure stdout/stderr to UTF-8 up front so
# every log line -- including the [AI] progress messages -- survives.
if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr is not None and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ban exe build voi --windows-console-mode=disable khong co console:
# sys.stdout/sys.stderr co the la None hoac ghi vao do se loi, ma codebase
# goi print() o rat nhieu noi (ai_service, export_service...). Neu khong va,
# print() dau tien sau khi mo app se nem RuntimeError (lost sys.stdout)
# va exe "tu tat" ngay lap tuc. Thay the bang null-stream chiu loi.
class _NullStream:
    def write(self, *args, **kwargs):
        return 0

    def writelines(self, *args, **kwargs):
        return None

    def flush(self, *args, **kwargs):
        return None

    def isatty(self):
        return False

    def reconfigure(self, *args, **kwargs):
        return None


def _ensure_console_streams() -> None:
    for _name in ("stdout", "stderr"):
        try:
            _stream = getattr(sys, _name, None)
        except Exception:
            _stream = None
        _broken = _stream is None
        if not _broken:
            try:
                _broken = not hasattr(_stream, "write") or not hasattr(_stream, "flush")
            except Exception:
                _broken = True
        if not _broken:
            try:
                _stream.flush()
            except Exception:
                _broken = True
        if _broken:
            try:
                setattr(sys, _name, _NullStream())
            except Exception:
                pass


_ensure_console_streams()

# SPLASH HIEN NGAY: stdlib-only, phai chay TRUOC moi import nang (PySide6).
# Cua so intro hien trong <1s sau khi bam mo app, dung yen cho den khi
# MainWindow ve xong thi finish() chay hieu ung ket thuc (xem EduPlayApp.exec).
try:
    from eduplay.core import instant_splash as _instant_splash
    _instant_splash.show()
except Exception:
    _instant_splash = None  # type: ignore

import json
import time
import tempfile
from typing import Dict, List, Optional, Any

try:
    if os.name == "nt":
        import multiprocessing as _mp
        _cores = _mp.cpu_count() or 4
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
            f"--ignore-gpu-blocklist --enable-gpu --enable-gpu-rasterization --enable-zero-copy "
            f"--enable-oop-rasterization --use-angle=d3d11 --enable-accelerated-2d-canvas "
            f"--enable-accelerated-video-decode --num-raster-threads={_cores} --renderer-process-limit={_cores} "
            f"--max-active-webgl-contexts=16 --enable-threaded-compositing "
            f"--disable-gpu-watchdog --disable-background-timer-throttling --disable-renderer-backgrounding "
            f"--disable-backgrounding-occluded-windows --disable-features=CalculateNativeWinOcclusion,IntensiveWakeUpThrottling "
            f"--enable-features=Vulkan,CanvasOopRasterization"
        )
        os.environ["QT_ANGLE_PLATFORM"] = "d3d11"
        os.environ["QSG_RENDER_LOOP"] = "threaded"
        os.environ["QSG_RENDER_TIMING"] = "0"
        for _k in ("QTWEBENGINE_DISABLE_GPU", "QTWEBENGINE_DISABLE_SANDBOX"):
            os.environ.pop(_k, None)
except Exception:
    pass

from PySide6.QtCore import Qt, QSettings, QStandardPaths, QUrl, QThread, Signal, QEventLoop
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox, QFileDialog,
    QProgressBar, QFrame, QSplitter, QTabWidget, QScrollArea, QSizePolicy,
    QSpacerItem, QGridLayout, QGroupBox, QCheckBox, QRadioButton, QSpinBox,
    QDoubleSpinBox, QDateEdit, QTimeEdit, QDateTimeEdit, QListView, QListWidget,
    QTreeWidget, QHeaderView, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QAbstractScrollArea, QAbstractButton, QAbstractSlider, QAbstractSpinBox,
    QStatusBar, QToolBar,
    QMenu, QMenuBar, QDialog, QMessageBox, QWizard, QWizardPage,
    QErrorMessage
)
from PySide6.QtWidgets import QProgressDialog
from PySide6.QtWidgets import QProxyStyle, QStyle
from PySide6.QtGui import (
    QAction, QActionGroup, QCursor, QFont, QFontDatabase, QIcon, QImage,
    QKeySequence, QLinearGradient, QPalette, QPixmap, QBrush, QPen, QPolygon,
    QRegion, QTransform, QValidator, QIntValidator, QDoubleValidator,
    QInputMethod, QInputMethodEvent, QInputMethodQueryEvent, QTouchEvent, QTabletEvent,
    QWheelEvent, QFocusEvent, QCloseEvent, QContextMenuEvent, QDragEnterEvent,
    QDragMoveEvent, QDragLeaveEvent, QDropEvent, QHelpEvent, QHoverEvent, QMouseEvent,
    QMoveEvent, QResizeEvent, QShowEvent, QHideEvent, QPaintEvent, QEnterEvent,
    QNativeGestureEvent, QScrollEvent, QNativeInterface, QPlatformSurfaceEvent,
    QWindow, QBackingStore, QPaintEngine, QPaintDevice
)
# NOTE: QtWebEngine/QtPrintSupport co tinh KHONG import o top-level de giam
# vai giay chet khi khoi dong; cac module can (editor/preview) tu import lazy.
from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator, QCoreApplication

from eduplay.core.ai_service import AIService
from eduplay.core.asset_loader import load_asset_text
from eduplay.core.project_manager import ProjectManager
from eduplay.core.settings_manager import SettingsManager
from eduplay.core.asset_manager import AssetManager
from eduplay.core.import_service import ImportService
from eduplay.ui.main_window import MainWindow
from eduplay.core.update_checker import UpdateChecker

class EduPlayApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("EduPlay - Studio")
        self.setApplicationVersion("1.0.0")
        self.setOrganizationName("EduPlay")
        try:
            icon_path = self._get_icon_path()
            if icon_path:
                self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass
        
        self.main_window = None
        self.ai_service = None
        self.splash_shown = False

    def notify(self, receiver, event):
        """Catch-all: moi exception trong slot/event Qt deu duoc ghi log,
        app tiep tuc chay thay vi sap. Day la luoi chong crash cuoi cung."""
        try:
            return QApplication.notify(self, receiver, event)
        except Exception as e:
            try:
                import traceback as _tb

                try:
                    who = f"{type(receiver).__name__}.{getattr(event, 'type', lambda: '?')() if hasattr(event, 'type') else '?'}"
                except Exception:
                    who = "?"
                _write_crash_log(f"SLOT EXCEPTION [{who}]: {e}", _tb.format_exc())
            except Exception:
                pass
            return False
    
    def _play_intro_animation(self):
        try:
            if hasattr(self, "main_window") and self.main_window:
                try:
                    if hasattr(self.main_window, "start_startup_animation"):
                        self.main_window.start_startup_animation()
                except Exception:
                    pass
        except Exception:
            pass

    def _apply_theme_stylesheet(self, settings_manager: SettingsManager) -> None:
        try:
            theme = settings_manager.get_theme() or "light"
        except Exception:
            theme = "light"
        try:
            qss_name = "dark_theme.qss" if theme == "dark" else "light_theme.qss"
            qss = load_asset_text(f"eduplay/resources/styles/{qss_name}")
            try:
                brand = settings_manager.get("brand_color", "#10B981")
                if brand and brand.startswith("#"):
                    qss = qss.replace("#7F56D9", brand)
            except Exception:
                pass
            self.setStyleSheet(qss)
        except Exception:
            pass
        try:
            from PySide6.QtGui import QFont, QFontDatabase
            fam = "Segoe UI"
            if fam in QFontDatabase.families():
                self.setFont(QFont(fam, 11))
        except Exception:
            pass

    def _maybe_prompt_language_on_first_run(self, settings_manager: SettingsManager) -> None:
        try:
            if hasattr(settings_manager, "should_run_first_time_flow"):
                first_run = bool(settings_manager.should_run_first_time_flow())
            elif getattr(settings_manager, "settings_file_existed", False):
                first_run = False
            else:
                first_run = bool(settings_manager.get("first_run", True))
        except Exception:
            first_run = False
        if not first_run:
            try:
                from eduplay.core.i18n import I18n
                I18n.set_locale(settings_manager.get_language() or "en")
            except Exception:
                pass
            return
        try:
            sys_lang = (QLocale.system().name() or "").split("_")[0].strip().lower()
        except Exception:
            sys_lang = "en"
        supported = ["en", "vi", "fr", "es", "de"]
        suggested = sys_lang if sys_lang in supported else "en"
        try:
            from eduplay.core.i18n import I18n
            I18n.set_locale(suggested)
        except Exception:
            I18n = None  # type: ignore
        try:
            from eduplay.ui.widgets.custom_dropdown import FlatDropdown
        except Exception:
            FlatDropdown = None  # type: ignore
        # Man hinh chon ngon ngu lan dau mo app: an splash tam
        # de nguoi dung tap trung tra loi (xem anh mo ta).
        dlg = QDialog()
        try:
            dlg.setWindowModality(Qt.ApplicationModal)
        except Exception:
            pass
        try:
            title = I18n.t("first_run.language.title", suggested) if I18n else "Select language"
            heading = I18n.t("first_run.language.heading", suggested) if I18n else "Choose your language"
            desc = I18n.t("first_run.language.desc", suggested) if I18n else "You can change this later in Settings."
            label = I18n.t("first_run.language.label", suggested) if I18n else "Application language:"
            ok_text = I18n.t("first_run.language.continue", suggested) if I18n else "Continue"
            cancel_text = I18n.t("first_run.language.skip", suggested) if I18n else "Use default"
        except Exception:
            title = "Select language"
            heading = "Choose your language"
            desc = "You can change this later in Settings."
            label = "Application language:"
            ok_text = "Continue"
            cancel_text = "Use default"
        dlg.setWindowTitle(title)
        dlg.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                color: #101828;
            }
            QLabel {
                color: #101828;
                background-color: transparent;
            }
            QPushButton {
                background-color: #7F56D9;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
                font-weight: 600;
                font-size: 14px;
                min-width: 110px;
            }
            QPushButton:hover {
                background-color: #8B66E9;
            }
            QPushButton#cancel-btn {
                background-color: #F2F4F7;
                color: #344054;
                border: 1px solid #D0D5DD;
            }
            QPushButton#cancel-btn:hover {
                background-color: #E4E7EC;
            }
        """)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        title_lbl = QLabel(heading)
        title_lbl.setStyleSheet("font-size: 18px; font-weight: 700;")
        layout.addWidget(title_lbl)
        desc_lbl = QLabel(desc)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #667085;")
        layout.addWidget(desc_lbl)
        layout.addWidget(QLabel(label))
        if FlatDropdown:
            lang_combo = FlatDropdown()
            try:
                names = [I18n.t("lang.en", suggested), I18n.t("lang.vi", suggested), I18n.t("lang.fr", suggested), I18n.t("lang.es", suggested), I18n.t("lang.de", suggested)] if I18n else ["English", "Vietnamese", "French", "Spanish", "German"]
            except Exception:
                names = ["English", "Vietnamese", "French", "Spanish", "German"]
            for n, c in zip(names, supported):
                lang_combo.addItem(n, c)
            try:
                lang_combo.setCurrentData(suggested)
            except Exception:
                pass
        else:
            lang_combo = QComboBox()
            for c in supported:
                lang_combo.addItem(c.upper(), c)
            try:
                lang_combo.setCurrentIndex(supported.index(suggested))
            except Exception:
                pass
        layout.addWidget(lang_combo)
        actions = QHBoxLayout()
        actions.addStretch()
        cancel_btn = QPushButton(cancel_text)
        try:
            cancel_btn.setObjectName("cancel-btn")
        except Exception:
            pass
        ok_btn = QPushButton(ok_text)
        try:
            ok_btn.setDefault(True)
        except Exception:
            pass
        cancel_btn.clicked.connect(dlg.reject)
        ok_btn.clicked.connect(dlg.accept)
        actions.addWidget(cancel_btn)
        actions.addWidget(ok_btn)
        layout.addLayout(actions)
        try:
            dlg.setFixedWidth(420)
        except Exception:
            pass
        # An splash tam khi hop chon ngon ngu hien (xem anh mo ta).
        _was_hidden = False
        try:
            if _instant_splash is not None and hasattr(_instant_splash, "hide"):
                _instant_splash.hide()
                _was_hidden = True
        except Exception:
            pass
        try:
            accepted = dlg.exec()
        except BaseException:
            # Native modal-loop failure (observed as RPC_E_CANTCALLOUT_ININPUTSYNCCALL
            # aborting dlg.exec on some machines, e.g. under AV message hooks):
            # fall back to the suggested language instead of dying. first_run
            # stays true, so onboarding still shows and the user can pick a
            # language later in Settings.
            accepted = 0
        selected = suggested
        try:
            if accepted:
                selected = lang_combo.currentData() or suggested
        except Exception:
            selected = suggested
        try:
            settings_manager.set_language(selected)
        except Exception:
            try:
                settings_manager.set("app_language", selected)
            except Exception:
                pass
        try:
            from eduplay.core.i18n import I18n
            I18n.set_locale(selected)
        except Exception:
            pass
        finally:
            try:
                if _was_hidden and _instant_splash is not None and hasattr(_instant_splash, "reshow"):
                    _instant_splash.reshow()
            except Exception:
                pass
    
    def exec(self):
        """Start the application event loop"""
        # SettingsManager MUST be constructed BEFORE AIService and shared with
        # it. If AIService is created first without a settings_manager, it builds
        # its own internal SettingsManager (inside _resolve_base_url/_device_key)
        # which writes settings.json before we reach the explicit construction.
        # The later instance would then see the file as "pre-existing" and
        # silently skip the first-time flow (language popup + onboarding), even
        # on a machine where settings.json did not exist before launch.
        settings_manager = SettingsManager()
        self.ai_service = AIService(settings_manager)

        # AI loi KHONG duoc giet app: canh bao roi van mo de dung soan thao
        # offline (Edubot se tu bao "chua san sang" khi duoc goi).
        self._ai_ready = True
        if not self.ai_service.check_ready_fast():
            self._ai_ready = False
            try:
                if _instant_splash is not None and hasattr(_instant_splash, "hide"):
                    _instant_splash.hide()
            except Exception:
                pass
            try:
                QMessageBox.warning(
                    None,
                    "AI chưa sẵn sàng",
                    ("Không kết nối được AI server lúc khởi động.\n\n"
                     "App vẫn mở bình thường để soạn bài offline; "
                     "Edubot sẽ hoạt động lại khi có mạng/cấu hình đúng."),
                )
            except Exception:
                pass
            try:
                _write_crash_log("AI not ready at startup (graceful continue)", "")
            except Exception:
                pass

        if self._ai_ready and not self.ai_service.setup_ai():
            self._ai_ready = False
            try:
                if _instant_splash is not None and hasattr(_instant_splash, "hide"):
                    _instant_splash.hide()
            except Exception:
                pass
            try:
                QMessageBox.warning(
                    None,
                    "AI chưa sẵn sàng",
                    ("Không khởi tạo được AI service.\n\n"
                     "App vẫn mở bình thường để soạn bài offline."),
                )
            except Exception:
                pass
            try:
                _write_crash_log("AI setup failed at startup (graceful continue)", "")
            except Exception:
                pass
        
        try:
            self._apply_theme_stylesheet(settings_manager)
        except Exception:
            pass
        try:
            if _instant_splash is not None:
                _instant_splash.set_status_key("loading_ui")
        except Exception:
            pass
        try:
            self._maybe_prompt_language_on_first_run(settings_manager)
        except Exception:
            pass
        project_manager = ProjectManager()
        asset_manager = AssetManager()
        try:
            asset_manager.scan_bundled_assets()
        except Exception:
            pass
        import_service = ImportService()

        try:
            if _instant_splash is not None:
                _instant_splash.set_status_key("opening")
        except Exception:
            pass
        self.main_window = MainWindow(
            project_manager=project_manager,
            ai_service=self.ai_service,
            asset_manager=asset_manager,
            settings_manager=settings_manager,
            import_service=import_service,
        )
        try:
            # Start background update check after main window created so dialogs have a parent
            try:
                checker = UpdateChecker(settings_manager, self.applicationVersion())
            except Exception:
                checker = UpdateChecker(settings_manager, "0.0.0")

            def _on_update_available(payload: dict):
                try:
                    title = f"Update available: {payload.get('tag_name', '')}"
                    body = payload.get('body', '') or payload.get('name', '') or ''
                    from eduplay.ui.widgets.confirm_dialog import ask_confirm
                    try:
                        _update_lang = settings_manager.get_language() if settings_manager else "en"
                    except Exception:
                        _update_lang = "en"
                    if ask_confirm(
                        self.main_window,
                        title,
                        f"A new version is available: {payload.get('tag_name')}\n\nDo you want to download and install it now?\n\n{body}",
                        _update_lang,
                        default_no=False,
                    ):
                        # find an exe asset
                        assets = payload.get('assets', []) or []
                        download_url = None
                        for a in assets:
                            name = str(a.get('name') or "").lower()
                            if name.endswith('.exe') or 'setup' in name:
                                download_url = a.get('browser_download_url')
                                break
                        if not download_url and assets:
                            download_url = assets[0].get('browser_download_url')
                        if download_url:
                            progress = QProgressDialog("Downloading update...", "Cancel", 0, 100, self.main_window)
                            progress.setWindowModality(Qt.WindowModal)
                            progress.setAutoClose(False)
                            progress.setValue(0)

                            def _on_progress(pct: int):
                                try:
                                    progress.setValue(int(pct))
                                except Exception:
                                    pass

                            def _on_done(path: str):
                                try:
                                    progress.close()
                                except Exception:
                                    pass
                                try:
                                    if os.name == 'nt':
                                        os.startfile(path)
                                    else:
                                        import subprocess
                                        subprocess.Popen([path], shell=False)
                                except Exception:
                                    QMessageBox.information(self.main_window, "Installer", f"Downloaded to: {path}")

                            checker.download_progress.connect(_on_progress)
                            checker.download_completed.connect(_on_done)
                            checker.error.connect(lambda e: QMessageBox.warning(self.main_window, "Update error", str(e)))
                            checker.download_asset(download_url)
                            progress.exec()

                except Exception:
                    pass

            checker.update_available.connect(_on_update_available)
            checker.error.connect(lambda e: None)
            checker.check_for_update()
        except Exception:
            pass
        try:
            # Create the startup overlay before the first window paint so Home
            # does not flash briefly ahead of the intro.
            if hasattr(self.main_window, "_startup_animation_requested"):
                self.main_window._startup_animation_requested = True
        except Exception:
            pass
        self._play_intro_animation()
        try:
            self.main_window.showMaximized()
        except Exception:
            self.main_window.show()
        # Quet trung ten du an 1 lan khi mo app (khong chan, chi canh bao).
        try:
            if hasattr(self.main_window, "maybe_warn_duplicate_project_names"):
                self.main_window.maybe_warn_duplicate_project_names()
        except Exception:
            pass
        # Tu gia han link sap het han (chay nen, chi thong bao khi co).
        try:
            if hasattr(self.main_window, "auto_renew_expiring_links"):
                self.main_window.auto_renew_expiring_links()
        except Exception:
            pass
        # App da ve xong frame dau -> tat splash bang hieu ung ket thuc
        # (intro overlay ben trong MainWindow tiep tuc nhu cu).
        try:
            try:
                QApplication.processEvents()
            except Exception:
                pass
            if _instant_splash is not None:
                _instant_splash.finish()
        except Exception:
            pass
        
        return super().exec()
    
    def _get_icon_path(self):
        """Get icon path - try multiple locations"""
        icon_paths = [
            "eduplay/resources/icons/icon.ico",
            os.path.join(os.path.dirname(__file__), "eduplay", "resources", "icons", "icon.ico"),
            os.path.join(os.path.dirname(__file__), "eduplay", "resources", "icons", "icon.png"),
        ]
        
        for path in icon_paths:
            if os.path.exists(path):
                return path
        
        return None


def main():
    """Main entry point for the application"""
    try:
        return _main_guarded()
    except BaseException as e:
        try:
            import traceback as _tb
            detail = _tb.format_exc()
        except Exception:
            detail = str(e)
        log_path = ""
        try:
            log_path = _write_crash_log(f"STARTUP CRASH: {e}", detail)
        except Exception:
            pass
        try:
            if _instant_splash is not None and hasattr(_instant_splash, "hide"):
                _instant_splash.hide()
        except Exception:
            pass
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            if QApplication.instance() is not None:
                QMessageBox.critical(
                    None,
                    "EduPlay Studio - Lỗi khởi động",
                    "EduPlay Studio gặp lỗi khi khởi động và phải tắt.\n\n"
                    f"Chi tiết: {e}\n\n"
                    + (f"Nhật ký lỗi: {log_path}\nHãy gửi file này cho bộ phận hỗ trợ." if log_path else "Hãy thử chạy lại ứng dụng."),
                )
                return 1
        except Exception:
            pass
        # KHONG dung tkinter de bao loi: splash Tk co the con chay o thread
        # nen tao them Tk root o main thread se in "Tcl_AsyncDelete: async
        # handler deleted by the wrong thread" va gay crash khi thoat.
        try:
            print(f"FATAL startup crash: {e}\n{detail}", file=sys.stderr)
        except Exception:
            pass
        return 1


def _main_guarded():
    if len(sys.argv) >= 2 and sys.argv[1] == "--preview-runner":
        from eduplay.core import preview_runner
        sys.argv = [sys.argv[0], *sys.argv[2:]]
        return preview_runner.main()
    try:
        QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    except Exception:
        pass
    # Compress high-frequency input events (mouse/tablet/wheel) so the event
    # queue stays small during drags/scrolls. Cheap, safe overall win.
    try:
        QApplication.setAttribute(Qt.AA_CompressHighFrequencyEvents, True)
    except Exception:
        pass
    # Drop the per-dialog context "?" help button (clutter + tiny overhead).
    try:
        QApplication.setAttribute(Qt.AA_DisableWindowContextHelpButton, True)
    except Exception:
        pass
    app = EduPlayApp(sys.argv)
    # Application-wide window icon so every window/dialog inherits it automatically.
    # Must run AFTER the QApplication exists (QIcon loads a QPixmap).
    try:
        from PySide6.QtGui import QIcon
        import os as _os
        _icon_dir = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "eduplay", "resources", "icons"))
        _icon = None
        for _cand in ("icon.ico", "icon.png"):
            _cand_path = _os.path.join(_icon_dir, _cand)
            if _os.path.exists(_cand_path):
                _icon = QIcon(_cand_path)
                break
        if _icon is not None and not _icon.isNull():
            QApplication.setWindowIcon(_icon)
    except Exception:
        pass
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

"""
Nguyen-Thanh-Tan ¬_¬
"""
