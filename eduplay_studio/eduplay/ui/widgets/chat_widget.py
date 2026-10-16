from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QTextEdit, QPushButton, QScrollArea,
                                QFrame, QSizePolicy, QFileDialog, QGraphicsBlurEffect, QGraphicsDropShadowEffect, QMenu)
from PySide6.QtCore import Qt, Signal, QTimer, QSize
from PySide6.QtGui import QFont, QTextCursor, QPalette, QColor, QTextOption, QKeyEvent
from eduplay.core.i18n import I18n
from eduplay.core.settings_manager import SettingsManager
from eduplay.ui.file_dialogs import get_open_file_names


class ChatInputTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptRichText(False)
        try:
            self.setFocusPolicy(Qt.StrongFocus)
        except Exception:
            pass
        try:
            self.setTabChangesFocus(False)
        except Exception:
            pass
        try:
            self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        except Exception:
            pass
        try:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        except Exception:
            pass

    def keyPressEvent(self, event: QKeyEvent):
        try:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
                try:
                    event.accept()
                except Exception:
                    pass
                owner = None
                try:
                    w = self.parentWidget()
                    while w is not None and not hasattr(w, "send_message"):
                        w = w.parentWidget()
                    owner = w
                except Exception:
                    owner = None
                if owner and hasattr(owner, "send_message"):
                    try:
                        owner.send_message()
                    except Exception:
                        pass
                return
        except Exception:
            pass
        super().keyPressEvent(event)


class ChatWidget(QWidget):
    message_sent = Signal(str)
    file_uploaded = Signal(str)
    dock_mode_changed = Signal(bool)
    width_mode_changed = Signal(str)
    detail_level_changed = Signal(str)
    visibility_changed = Signal(bool)
    voice_status_msg = Signal(str)
    voice_text_msg = Signal(str)
    voice_error_msg = Signal(str)
    voice_done = Signal()
    google_play_next = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_minimized = True
        self._busy = False
        try:
            self.language = SettingsManager().get_language() or 'en'
        except Exception:
            self.language = 'en'
        self._manual_positioned = False
        self._scale = 1.0
        self.is_docked = False
        self.width_mode = 'narrow'
        self.detail_level = 'chuẩn'
        self.messages = []
        self._pending_attachments = []
        self.setup_ui()
        try:
            self.voice_status_msg.connect(self._on_voice_status)
        except Exception:
            pass
        try:
            self.voice_text_msg.connect(self._on_voice_text)
        except Exception:
            pass
        try:
            self.voice_error_msg.connect(self._on_voice_error)
        except Exception:
            pass
        try:
            self.voice_done.connect(self._on_voice_done)
        except Exception:
            pass
        try:
            self.google_play_next.connect(self._play_google_next)
        except Exception:
            pass
        try:
            self.set_language(self.language)
        except Exception:
            pass
        
    def setup_ui(self):
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        try:
            self.theme = SettingsManager().get_theme() or 'dark'
        except Exception:
            self.theme = 'dark'

        self.chat_container = QWidget()
        self.chat_container.setObjectName("chat-container")
        if self.theme == 'dark':
            base_bg = 'rgba(18,20,28,0.88)'
            base_border = '#313543'
        else:
            base_bg = '#E6F7FF'
            base_border = '#93C5FD'
        docked = getattr(self, "is_docked", False)
        radius_style = "border-radius: 0px;"
        self.chat_container.setStyleSheet(f"""
            #chat-container {{
                background-color: {base_bg};
                border: 1px solid {base_border};
                {radius_style}
                padding: 0px;
            }}
        """)
        
        container_layout = QVBoxLayout(self.chat_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # Header
        header = self.create_header()
        container_layout.addWidget(header)
        
        # Chat area
        chat_area = self.create_chat_area()
        container_layout.addWidget(chat_area)
        
        # Input area
        input_area = self.create_input_area()
        container_layout.addWidget(input_area)
        try:
            container_layout.setStretch(0, 0)  # header
            container_layout.setStretch(1, 1)  # chat
            container_layout.setStretch(2, 0)  # input
        except Exception:
            pass
        
        layout.addWidget(self.chat_container)
        try:
            from PySide6.QtGui import QColor
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(30)
            shadow.setOffset(0, 10)
            shadow.setColor(QColor(0, 0, 0, 160))
            self.chat_container.setGraphicsEffect(shadow)
        except Exception:
            pass
        
        self.setMinimumSize(360, 460)
        
    def create_header(self):
        header = QWidget()
        header.setObjectName("chat-header")
        try:
            brand = SettingsManager().get("brand_color", "#10B981")
        except Exception:
            brand = "#10B981"
        theme = getattr(self, 'theme', 'dark')
        if theme == 'dark':
            header_bg = 'linear-gradient(135deg, #1B1F2A, #222739)'
            btn_bg = '#111827'
            btn_hover_bg = '#1F2937'
            btn_border = '#374151'
            btn_fg = '#E5E7EB'
            close_bg = '#B91C1C'
            close_hover_bg = '#DC2626'
        else:
            header_bg = '#E6F7FF'
            btn_bg = '#EEF2FF'
            btn_hover_bg = '#E0EAFF'
            btn_border = '#7F56D9'
            btn_fg = '#7F56D9'
            close_bg = '#DC2626'
            close_hover_bg = '#EF4444'
        header.setStyleSheet(f"""
            #chat-header {{
                background: {header_bg};
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                padding: 4px 14px 10px 14px;
            }}
        """)
        header_btn_style = f"""
            QPushButton {{
                background-color: {btn_bg};
                border: 1px solid {btn_border};
                border-radius: 16px;
                color: {btn_fg};
                min-width: 32px;
                max-width: 32px;
                min-height: 32px;
                max-height: 32px;
                padding: 0px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover_bg};
                border-color: {btn_border};
            }}
        """
        close_btn_style = f"""
            QPushButton {{
                background-color: {close_bg};
                border: 1px solid {close_bg};
                border-radius: 16px;
                color: #FFFFFF;
                min-width: 32px;
                max-width: 32px;
                min-height: 32px;
                max-height: 32px;
                padding: 0px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {close_hover_bg};
                border-color: {close_hover_bg};
            }}
        """
        layout = QHBoxLayout(header)
        try:
            layout.setContentsMargins(16, 10, 22, 10)
            layout.setSpacing(14)
            layout.setAlignment(Qt.AlignVCenter)
        except Exception:
            pass
        
        title = QLabel(self._t('title').upper())
        title.setStyleSheet(f"""
            QLabel {{
                color: {('#FFFFFF' if theme == 'dark' else '#1A1A1A')};
                font-weight: 800;
                font-size: 16px;
            }}
        """)
        self._title_label = title
        layout.addWidget(title)
        
        layout.addStretch()

        minimize_btn = QPushButton("–")
        minimize_btn.setStyleSheet(header_btn_style)
        minimize_btn.clicked.connect(self.toggle_minimize)
        try:
            minimize_btn.setToolTip(self._t('minimize'))
        except Exception:
            pass
        layout.addWidget(minimize_btn)
        
        # Close button
        close_btn = QPushButton("✖")
        close_btn.setStyleSheet(close_btn_style)
        close_btn.clicked.connect(self.hide)
        try:
            close_btn.setToolTip(self._t('close'))
        except Exception:
            pass
        layout.addWidget(close_btn)

        self._header_btns = [minimize_btn, close_btn]
        self.chat_header = header
        try:
            for b in header.findChildren(QPushButton):
                try:
                    t = str(b.text() or "").strip()
                except Exception:
                    t = ""
                if t in ("⋯", "...", "…", "💬", "🗨", "🗨️", "💭"):
                    try:
                        b.setVisible(False)
                    except Exception:
                        pass
        except Exception:
            pass
        return header

    def create_chat_area(self):
        # Chat messages area - ScrollArea
        self.chat_view = QScrollArea()
        self.chat_view.setWidgetResizable(True)
        self.chat_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        try:
            self.chat_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        except Exception:
            pass
            
        self.chat_view.setFrameShape(QFrame.NoFrame)
        self.chat_view.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        
        # Container for messages
        self.chat_content = QWidget()
        self.chat_content.setObjectName("chat_content")
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setContentsMargins(16, 16, 16, 16)
        self.chat_layout.setSpacing(16)
        self.chat_layout.addStretch() # Push messages to top (spacer at bottom)
        
        self.chat_view.setWidget(self.chat_content)
        
        theme = getattr(self, 'theme', 'dark')
        chat_bg = '#FFFFFF' if theme != 'dark' else '#020617'
        self.chat_content.setStyleSheet(f"#chat_content {{ background-color: {chat_bg}; }}")
        
        return self.chat_view
        
    def _render_message(self, sender, message, message_type):
        """Render a message as a bubble widget"""
        try:
            brand = SettingsManager().get("brand_color", "#7F56D9")
            theme = getattr(self, 'theme', SettingsManager().get_theme() or 'dark')
        except Exception:
            brand = "#7F56D9"
            theme = getattr(self, 'theme', 'dark')
            
        # Row container
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        
        # Message processing - co giãn định dạng, xử lý header trước khi đổi \n
        try:
            msg = str(message)
            import re
            # Lấy theme để chỉnh màu code cho phù hợp, tránh nền chữ đậm hơn khung như screenshot
            try:
                _theme = getattr(self, 'theme', 'dark')
            except Exception:
                _theme = 'dark'
            msg = msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            # Code block / inline code - nền rất nhẹ để không đậm hơn bubble (fix "chữ trong khung có nền đậm hơn")
            _code_bg = "rgba(255,255,255,0.08)" if _theme == 'dark' else "rgba(0,0,0,0.03)"
            _pre_bg = "rgba(255,255,255,0.06)" if _theme == 'dark' else "rgba(0,0,0,0.02)"
            msg = re.sub(
                rf"```(.*?)```",
                rf"<pre style='background:{_pre_bg}; padding:8px; border-radius:6px; font-family:Consolas, \"Cascadia Mono\", \"Courier New\", monospace; white-space:pre-wrap;'>\1</pre>",
                msg,
                flags=re.DOTALL,
            )
            msg = re.sub(
                rf"`(.*?)`",
                rf"<code style='background:{_code_bg}; padding:2px 4px; border-radius:4px; font-family:Consolas, \"Cascadia Mono\", \"Courier New\", monospace;'>\1</code>",
                msg,
            )
            # Markdown table -> HTML table (phải trước header/bold để giữ cấu trúc)
            def _md_table_to_html(m):
                block = m.group(0)
                lines = [l.rstrip() for l in block.strip().splitlines() if l.strip()]
                if len(lines) < 2:
                    return block
                # Tách header
                try:
                    header_cells = [c.strip() for c in lines[0].strip().strip('|').split('|')]
                    # Bỏ dòng separator |---|---|
                    # Kiểm tra dòng 2 có phải separator không
                    sep = lines[1].strip()
                    if not re.match(r"^\|?[\s:\-|]+\|?[\s:\-|]*$", sep):
                        # Không phải table chuẩn, trả về block gốc
                        return block
                    rows = []
                    for line in lines[2:]:
                        if not line.strip().startswith('|'):
                            break
                        # Bỏ dòng chỉ có |---|---|
                        if re.match(r"^\|?[\s:\-|]+\|?[\s:\-|]*$", line.strip()):
                            continue
                        cells = [c.strip() for c in line.strip().strip('|').split('|')]
                        # Bỏ hàng rỗng
                        if not any(c for c in cells):
                            continue
                        rows.append(cells)
                    if not header_cells or not rows:
                        return block
                    # Style theo theme - header nhẹ để không đậm hơn chữ, nền bảng trong suốt để khớp bubble
                    th_bg = "rgba(127,86,217,0.08)" if theme != 'dark' else "rgba(127,86,217,0.12)"
                    th_fg = "#1F2937" if theme != 'dark' else "#F9FAFB"
                    td_border = "#E5E7EB" if theme != 'dark' else "#4B5563"
                    table_bg = "transparent"
                    html = f"<table style='border-collapse:collapse; width:100%; margin:10px 0; font-size:12px; border:1px solid {td_border}; background:{table_bg}; border-radius:6px; overflow:hidden;'>"
                    html += "<thead><tr>"
                    for h in header_cells:
                        h_cell = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", h)
                        h_cell = re.sub(r"\*(.+?)\*", r"<i>\1</i>", h_cell)
                        html += f"<th style='border:1px solid {td_border}; padding:7px 8px; background:{th_bg}; color:{th_fg}; text-align:left; font-weight:800;'>{h_cell or ''}</th>"
                    html += "</tr></thead><tbody>"
                    for r in rows:
                        html += "<tr>"
                        # Đảm bảo đủ cột bằng header
                        for idx in range(len(header_cells)):
                            c = r[idx] if idx < len(r) else ""
                            c = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", c)
                            c = re.sub(r"\*(.+?)\*", r"<i>\1</i>", c)
                            # Giữ <br> trong cell nếu có
                            html += f"<td style='border:1px solid {td_border}; padding:6px 8px; vertical-align:top;'>{c}</td>"
                        html += "</tr>"
                    html += "</tbody></table>"
                    return html
                except Exception:
                    return block
            # Tìm khối table: header |...| \n separator |---|---| \n rows |...|
            try:
                msg = re.sub(r"(?:^\|.*\|.*\n)(?:^\|[\s:\-|]+\|.*\n)(?:^\|.*\|.*(?:\n|$))+", _md_table_to_html, msg, flags=re.MULTILINE)
            except Exception:
                pass
            # Header markdown ##, ### -> bold lớn
            msg = re.sub(r"^###\s+(.+)$", r"<b style='font-size:15px; color:inherit;'>\1</b>", msg, flags=re.MULTILINE)
            msg = re.sub(r"^##\s+(.+)$", r"<b style='font-size:16px; color:inherit;'>\1</b>", msg, flags=re.MULTILINE)
            msg = re.sub(r"^#\s+(.+)$", r"<b style='font-size:18px; color:inherit;'>\1</b>", msg, flags=re.MULTILINE)
            # Bold/italic/underline
            msg = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", msg)
            msg = re.sub(r"\*(.+?)\*", r"<i>\1</i>", msg)
            msg = re.sub(r"__(.+?)__", r"<u>\1</u>", msg)
            # Cuối cùng mới đổi \n -> <br> để giữ header/code/table
            # Nhưng giữ nguyên table đã là HTML, không đổi <br> trong table
            # Tạm tách table ra, đổi \n phần còn lại
            try:
                parts = re.split(r"(<table.*?</table>)", msg, flags=re.DOTALL)
                out_parts = []
                for p in parts:
                    if p.strip().lower().startswith("<table"):
                        out_parts.append(p)
                    else:
                        out_parts.append(p.replace("\n", "<br>"))
                msg = "".join(out_parts)
            except Exception:
                msg = msg.replace("\n", "<br>")
        except Exception:
            msg = str(message)

        bubble = QLabel(msg)
        bubble.setWordWrap(True)
        # Cho phép bôi đen + Ctrl+C, chuột phải Copy (fix "cho phép copy")
        bubble.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        bubble.setContextMenuPolicy(Qt.DefaultContextMenu)
        bubble.setOpenExternalLinks(True)
        bubble.setTextFormat(Qt.RichText)
        
        # Styles
        if message_type == "user":
            bg = brand
            fg = "#FFFFFF"
            border = f"1px solid {brand}"
            radius_style = "border-radius: 18px; border-bottom-right-radius: 2px;"
            row_layout.addStretch()
            row_layout.addWidget(bubble)
        else:
            if theme == 'dark':
                bg = "#1F2937"
                fg = "#F9FAFB"
                border = "1px solid #374151"
            else:
                bg = "#F3F4F6"
                fg = "#111827"
                border = "1px solid #E5E7EB"
            radius_style = "border-radius: 18px; border-bottom-left-radius: 2px;"
            row_layout.addWidget(bubble)
            # Nút Copy cho AI (cho phép copy text trả lời)
            try:
                from PySide6.QtWidgets import QPushButton as _CopyBtn
                copy_btn = _CopyBtn("📋")
                copy_btn.setToolTip("Copy" if getattr(self, 'language', 'en') != 'vi' else "Sao chép")
                copy_btn.setFixedSize(28, 28)
                copy_btn.setCursor(Qt.PointingHandCursor)
                copy_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        border: none;
                        border-radius: 8px;
                        font-size: 14px;
                        padding: 0px;
                    }}
                    QPushButton:hover {{
                        background-color: {'rgba(255,255,255,0.08)' if theme == 'dark' else 'rgba(0,0,0,0.06)'};
                    }}
                """)
                # Lưu plain text gốc để copy (không phải HTML)
                _plain_to_copy = str(message if message is not None else "")
                def _do_copy(checked=False, txt=_plain_to_copy):
                    try:
                        from PySide6.QtWidgets import QApplication as _QApp
                        cb = _QApp.clipboard()
                        cb.setText(str(txt))
                    except Exception:
                        pass
                    try:
                        copy_btn.setText("✓")
                        from PySide6.QtCore import QTimer as _QTimer2
                        _QTimer2.singleShot(1200, lambda: copy_btn.setText("📋"))
                    except Exception:
                        pass
                copy_btn.clicked.connect(_do_copy)
                # Đặt sau bubble, trước stretch để không đè
                row_layout.addWidget(copy_btn, 0, Qt.AlignBottom)
            except Exception:
                pass
            # Nút loa đọc phản hồi AI
            try:
                from PySide6.QtWidgets import QPushButton as _SpeakBtn
                speak_btn = _SpeakBtn("🔊")
                try:
                    _lang = getattr(self, 'language', 'en')
                    from eduplay.core.i18n import I18n as _I18nSpk
                    _tip = _I18nSpk.t("chat.voice.read", _lang)
                    speak_btn.setToolTip(_tip if _tip and _tip != "chat.voice.read" else ("Đọc" if _lang == 'vi' else "Read aloud"))
                except Exception:
                    pass
                speak_btn.setFixedSize(28, 28)
                speak_btn.setCursor(Qt.PointingHandCursor)
                speak_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        border: none;
                        border-radius: 8px;
                        font-size: 14px;
                        padding: 0px;
                    }}
                    QPushButton:hover {{
                        background-color: {'rgba(255,255,255,0.08)' if theme == 'dark' else 'rgba(0,0,0,0.06)'};
                    }}
                """)
                _plain_to_speak = str(message if message is not None else "")
                speak_btn.clicked.connect(lambda checked=False, txt=_plain_to_speak, btn=speak_btn: self._toggle_speak(txt, btn))
                row_layout.addWidget(speak_btn, 0, Qt.AlignBottom)
            except Exception:
                pass
            row_layout.addStretch()
            
        bubble.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border: {border};
                {radius_style}
                padding: 10px 16px;
                font-size: 13px;
                line-height: 1.4;
                font-family: "Segoe UI", "Segoe UI Emoji", "Apple Color Emoji", sans-serif;
            }}
        """)
        
        # Max width
        try:
            max_w = int(self.chat_view.width() * 0.8)
        except:
            max_w = 280
        bubble.setMaximumWidth(max(200, max_w))
        
        # Add to layout before stretch
        try:
            cnt = self.chat_layout.count()
            if cnt > 0:
                item = self.chat_layout.itemAt(cnt - 1)
                if item.spacerItem():
                    self.chat_layout.insertWidget(cnt - 1, row)
                else:
                    self.chat_layout.addWidget(row)
            else:
                self.chat_layout.addWidget(row)
        except Exception:
            pass
            
        # Scroll to bottom
        QTimer.singleShot(50, self._scroll_to_bottom)

    def _scroll_to_bottom(self):
        try:
            sb = self.chat_view.verticalScrollBar()
            sb.setValue(sb.maximum())
        except:
            pass

    def add_message(self, sender, message, message_type="user"):
        """Add a message to the chat display"""
        try:
            sender_s = str(sender or "").strip().lower()
        except Exception:
            sender_s = ""
        if (message_type != "user") and sender_s in ("ai", "system"):
            try:
                message = self._sanitize_ai_chat_text(message)
            except Exception:
                pass
        self.messages.append({"sender": sender, "message": message, "type": message_type})
        self._render_message(sender, message, message_type)

    def _sanitize_ai_chat_text(self, text):
        try:
            s = str(text or "")
        except Exception:
            s = ""
        if not s:
            return s
        try:
            import re
        except Exception:
            re = None
        try:
            s = re.sub(r"<think>[\s\S]*?</think>", "", s, flags=re.IGNORECASE) if re is not None else s
        except Exception:
            pass
        # Fix lỗi font ô vuông: AI hay dùng ①②③☐☑1️⃣2️⃣ mà font không đủ → hiện □
        # → Chuẩn hóa tất cả về "1.", "2." ASCII để hiển thị 100% (theo system prompt đã cấm emoji số)
        try:
            if re is not None:
                # Thay các ký tự ô vuông / số vòng tròn thành số thường
                s = s.replace("☐", "-").replace("☑", "-").replace("☒", "-").replace("□", "-").replace("▢", "-").replace("▣", "-")
                s = s.replace("①", "1.").replace("②", "2.").replace("③", "3.").replace("④", "4.").replace("⑤", "5.").replace("⑥", "6.")
                s = s.replace("⑦", "7.").replace("⑧", "8.").replace("⑨", "9.").replace("⑩", "10.")
                # Emoji keycap 1️⃣-🔟 (gồm VS16 + combining) → 1., 2., ... để tránh ô vuông trên Win cũ
                # 1️⃣ = \u0031\ufe0f\u20e3, 2️⃣ = \u0032\ufe0f\u20e3, ..., 🔟 = \U0001f51f
                s = s.replace("0️⃣", "0.").replace("1️⃣", "1.").replace("2️⃣", "2.").replace("3️⃣", "3.").replace("4️⃣", "4.")
                s = s.replace("5️⃣", "5.").replace("6️⃣", "6.").replace("7️⃣", "7.").replace("8️⃣", "8.").replace("9️⃣", "9.").replace("🔟", "10.")
                # Fallback nếu AI dùng dạng không có VS16
                s = s.replace("\u20e3", ".")
                # Giữ lại emoji trang trí nhẹ (😊, 📚, ✨, ✅, 🔍, 💬, 🤖) – đã có Segoe UI Emoji, nhưng số thì chuẩn hóa rồi
                # Dọn "6 px" kỹ thuật thừa
                s = re.sub(r"\(?điểm\s*6\s*px[^\)]*\)", "", s, flags=re.IGNORECASE)
                s = re.sub(r"6\s*px\s*bên\s*trái", "sát mép trái", s, flags=re.IGNORECASE)
                s = re.sub(r"hover\s*0\.3s", "", s, flags=re.IGNORECASE)
        except Exception:
            pass
        tool_names = (
            "CREATE_PROJECT",
            "OPEN_PROJECT",
            "ADD_QUESTION",
            "UPDATE_QUESTION",
            "DELETE_QUESTION",
            "DUPLICATE_QUESTION",
            "DUPLICATE_PROJECT",
            "DELETE_PROJECT",
            "UPDATE_PROJECT",
            "SET_QUESTION_IMAGE",
            "SET_QUESTION_IMAGE_URL",
            "SEARCH_IMAGE",
            "UPDATE_GAME_CONFIG",
            "READ_PROJECT_DETAILS",
            "WEB_SEARCH",
            "WEB_FETCH",
            "NAVIGATE",
            "OPEN_SCREEN",
            "NAVIGATE_SCREEN",
            "SHOW_SCREEN",
            "OPEN_SETTINGS",
            "SHOW_SETTINGS",
            "OPEN_HELP",
            "SHOW_HELP",
            "OPEN_COMMAND_PALETTE",
            "PREVIEW",
            "EXPORT_HTML",
            "EXPORT_WEB",
            "SET_THEME",
            "SET_LANGUAGE",
            "SET_FONT",
            "UPDATE_TAGS",
            "ADD_TAG",
            "REMOVE_TAG",
            "SEARCH_PROJECTS",
            "GET_STATS",
            "CLEAR_CHAT",
            "RESET_MEMORY",
            "TRANSLATE_QUESTION",
            "SUMMARIZE_PROJECT",
            "IMPORT_QUESTIONS",
            "AUTO_CREATE_FULL_PROJECT",
            "GENERATE_FROM_IMAGE",
            "SPLIT_DOCUMENT",
        )
        # Nghiêm cấm lộ lệnh: loại bỏ mọi dạng COMMAND trong chat
        # Cả khi ở đầu dòng, trong dòng, hoặc inline
        if re is not None:
            try:
                # Xóa toàn bộ đoạn TOOL_NAME: {json} hoặc TOOL_NAME: [...] inline
                for tn in tool_names:
                    # dạng INLINE: ADD_QUESTION: {...}
                    s = re.sub(rf"\b{tn}\s*:\s*\{{.*?\}}", "", s, flags=re.IGNORECASE | re.DOTALL)
                    s = re.sub(rf"\b{tn}\s*:\s*\[.*?\]", "", s, flags=re.IGNORECASE | re.DOTALL)
                    # dạng COMMAND: {\"key\":...}
                    s = re.sub(rf"\b{tn}\b", "", s, flags=re.IGNORECASE)
                # Xóa leftover COMMAND: prefix
                s = re.sub(r"\bCOMMAND\s*:\s*", "", s, flags=re.IGNORECASE)
            except Exception:
                pass
        lines = str(s or "").splitlines()
        out_lines = []
        for ln in lines:
            t = str(ln or "").strip()
            # Bỏ các dòng rỗng hoặc chỉ còn ký tự rỗng sau khi xóa lệnh ( [], {}, -- )
            if not t or t in ("[]", "{}", "--", "—", "-", "*"):
                if out_lines and out_lines[-1] != "":
                    out_lines.append("")
                continue
            if re is not None and re.match(r"^\s*[\[\]\{\}]+\s*$", t):
                continue
            tl = t.upper()
            if tl.startswith("TOOL_ERROR:"):
                continue
            if "COMMAND:" in tl:
                continue
            if re is not None and re.match(r"^\[TOOL_NAME\s*:\s*[A-Za-z0-9_]+\]\s*$", t):
                continue
            if re is not None and re.match(r"^\[(?:XEM_[A-Z0-9_]+)\]\s*$", t):
                continue
            if t.startswith("[") and (":" in t) and t.endswith("]"):
                try:
                    cmd = t[1 : t.find(":")].strip().upper()
                except Exception:
                    cmd = ""
                if cmd in tool_names:
                    continue
            if re is not None:
                m = re.match(r"^(?:[\-\*\u2022]?\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*:\s*", t)
                if m and str(m.group(1) or "").strip().upper() in tool_names:
                    continue
                # Inline detection: nếu dòng chứa bất kỳ tool name nào + dấu : thì bỏ dòng đó
                if any(tn in tl for tn in tool_names):
                    # nếu dòng đó có tool pattern thì coi như lộ lệnh -> bỏ
                    # (pattern dựng từ tool_names để tự đồng bộ khi thêm lệnh mới)
                    try:
                        _tn_pat = "|".join(tool_names)
                    except Exception:
                        _tn_pat = "CREATE_PROJECT|OPEN_PROJECT|ADD_QUESTION|UPDATE_QUESTION|DELETE_QUESTION|SET_QUESTION_IMAGE|SET_QUESTION_IMAGE_URL|SEARCH_IMAGE|UPDATE_GAME_CONFIG|READ_PROJECT_DETAILS|WEB_SEARCH|WEB_FETCH"
                    if re.search(rf"\b(?:{_tn_pat})\s*:", tl):
                        continue
            out_lines.append(str(ln or ""))
        out = "\n".join(out_lines).strip()
        try:
            if len(out) >= 2 and ((out.startswith('"') and out.endswith('"')) or (out.startswith("'") and out.endswith("'"))):
                out2 = out[1:-1]
                out2 = out2.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"').replace("\\'", "'").replace("\\\\", "\\")
                out = out2.strip()
        except Exception:
            pass
        return out

    def _format_rich_text(self, message) -> str:
        try:
            msg = str(message)
            import re
            try:
                _theme2 = getattr(self, 'theme', 'dark')
            except Exception:
                _theme2 = 'dark'
            _c_bg = "rgba(255,255,255,0.08)" if _theme2 == 'dark' else "rgba(0,0,0,0.03)"
            _p_bg = "rgba(255,255,255,0.06)" if _theme2 == 'dark' else "rgba(0,0,0,0.02)"
            msg = msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            msg = msg.replace("\n", "<br>")
            msg = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", msg)
            msg = re.sub(r"\*(.+?)\*", r"<i>\1</i>", msg)
            msg = re.sub(r"__(.+?)__", r"<u>\1</u>", msg)
            msg = re.sub(
                r"```(.*?)```",
                lambda m: f"<pre style='background:{_p_bg}; padding:8px; border-radius:6px; font-family:Consolas, \"Cascadia Mono\", \"Courier New\", monospace; white-space:pre-wrap;'>{m.group(1)}</pre>",
                msg,
                flags=re.DOTALL,
            )
            msg = re.sub(
                r"`(.*?)`",
                lambda m: f"<code style='background:{_c_bg}; padding:2px 4px; border-radius:4px; font-family:Consolas, \"Cascadia Mono\", \"Courier New\", monospace;'>{m.group(1)}</code>",
                msg,
            )
            return msg
        except Exception:
            return str(message)

    def set_status(self, text: str, owner=None):
        try:
            theme = getattr(self, 'theme', SettingsManager().get_theme() or 'dark')
        except Exception:
            theme = getattr(self, 'theme', 'dark')

        row = getattr(self, "_status_row", None)
        bubble = getattr(self, "_status_bubble", None)
        if not row or not bubble:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)

            bubble = QLabel()
            bubble.setWordWrap(True)
            bubble.setTextInteractionFlags(Qt.NoTextInteraction)
            bubble.setTextFormat(Qt.RichText)

            if theme == 'dark':
                bg = "rgba(31,41,55,0.55)"
                fg = "#E5E7EB"
                border = "1px solid rgba(55,65,81,0.55)"
            else:
                bg = "rgba(243,244,246,0.8)"
                fg = "#111827"
                border = "1px solid rgba(229,231,235,0.9)"
            radius_style = "border-radius: 18px; border-bottom-left-radius: 2px;"

            bubble.setStyleSheet(f"""
                QLabel {{
                    background-color: {bg};
                    color: {fg};
                    border: {border};
                    {radius_style}
                    padding: 10px 16px;
                    font-size: 12px;
                    line-height: 1.35;
                    font-family: "Segoe UI", "Segoe UI Emoji", "Apple Color Emoji", sans-serif;
                }}
            """)

            row_layout.addWidget(bubble)
            row_layout.addStretch()
            self._status_row = row
            self._status_bubble = bubble
            try:
                self._status_owner = owner
            except Exception:
                pass

            try:
                cnt = self.chat_layout.count()
                if cnt > 0:
                    item = self.chat_layout.itemAt(cnt - 1)
                    if item.spacerItem():
                        self.chat_layout.insertWidget(cnt - 1, row)
                    else:
                        self.chat_layout.addWidget(row)
                else:
                    self.chat_layout.addWidget(row)
            except Exception:
                pass
        else:
            try:
                self._status_owner = owner
            except Exception:
                pass

        # Lưu base text để làm hiệu ứng chấm động
        try:
            base = str(text or "").strip()
            # bỏ dấu ... cuối để chuẩn hóa
            import re as _re_dot
            base = _re_dot.sub(r"\.+$", "", base).strip()
            self._status_base_text = base
            self._status_dot = 0
        except Exception:
            try:
                self._status_base_text = str(text or "").strip()
                self._status_dot = 0
            except Exception:
                pass

        # Dừng timer cũ nếu có
        try:
            t = getattr(self, "_status_timer", None)
            if t:
                try:
                    t.stop()
                except Exception:
                    pass
                try:
                    t.deleteLater()
                except Exception:
                    pass
        except Exception:
            pass

        # Tạo timer hiệu ứng chấm ... -> . -> .. -> ... lặp
        try:
            from PySide6.QtCore import QTimer as _QTimer
            timer = _QTimer(self)
            timer.setInterval(450)
            def _tick():
                try:
                    b = getattr(self, "_status_base_text", "") or str(text or "").strip()
                    import re as _re2
                    b = _re2.sub(r"\.+$", "", b).strip()
                    d = int(getattr(self, "_status_dot", 0) or 0) + 1
                    if d > 3:
                        d = 1
                    self._status_dot = d
                    dots = "." * d
                    bubble.setText(self._format_rich_text(b + dots))
                except Exception:
                    pass
            timer.timeout.connect(_tick)
            self._status_timer = timer
            self._status_dot = 0
            # Hiển thị ngay lần đầu
            try:
                bubble.setText(self._format_rich_text(self._status_base_text + "."))
                self._status_dot = 1
            except Exception:
                try:
                    bubble.setText(str(text))
                except Exception:
                    pass
            timer.start()
        except Exception:
            try:
                bubble.setText(self._format_rich_text(text))
            except Exception:
                try:
                    bubble.setText(str(text))
                except Exception:
                    pass

        try:
            max_w = int(self.chat_view.width() * 0.8)
        except Exception:
            max_w = 280
        try:
            bubble.setMaximumWidth(max(200, max_w))
        except Exception:
            pass

        QTimer.singleShot(50, self._scroll_to_bottom)

    def clear_status(self, owner=None):
        try:
            if owner is not None and getattr(self, "_status_owner", None) != owner:
                return
        except Exception:
            pass
        # Dừng timer hiệu ứng
        try:
            t = getattr(self, "_status_timer", None)
            if t:
                try:
                    t.stop()
                except Exception:
                    pass
                try:
                    t.deleteLater()
                except Exception:
                    pass
            self._status_timer = None
            self._status_base_text = ""
            self._status_dot = 0
        except Exception:
            pass
        row = getattr(self, "_status_row", None)
        if not row:
            return
        try:
            self.chat_layout.removeWidget(row)
        except Exception:
            pass
        try:
            row.deleteLater()
        except Exception:
            pass
        try:
            self._status_row = None
            self._status_bubble = None
            self._status_owner = None
        except Exception:
            pass

    def create_input_area(self):
        input_widget = QFrame()
        input_widget.setObjectName("chat-input")
        theme = getattr(self, 'theme', 'dark')
        input_bg = '#E6F7FF' if theme != 'dark' else 'rgba(27,31,42,0.7)'
        self._input_bg_style = f"#chat-input {{ background-color: {input_bg}; border-bottom-left-radius: 14px; border-bottom-right-radius: 14px; padding: 10px; }}"
        input_widget.setStyleSheet(self._input_bg_style)

        root = QVBoxLayout(input_widget)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        attach_bar = QFrame()
        attach_bar.setObjectName("chat-attach-bar")
        attach_bar.setStyleSheet("background: transparent;")
        attach_layout = QHBoxLayout(attach_bar)
        attach_layout.setContentsMargins(0, 0, 0, 0)
        attach_layout.setSpacing(6)

        attach_scroll = QScrollArea()
        attach_scroll.setFrameShape(QFrame.NoFrame)
        attach_scroll.setWidgetResizable(True)
        attach_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        attach_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        attach_scroll.setFixedHeight(36)

        attach_inner = QWidget()
        attach_inner_layout = QHBoxLayout(attach_inner)
        attach_inner_layout.setContentsMargins(0, 0, 0, 0)
        attach_inner_layout.setSpacing(6)
        attach_inner_layout.addStretch()

        attach_scroll.setWidget(attach_inner)
        attach_layout.addWidget(attach_scroll)

        try:
            attach_bar.hide()
        except Exception:
            pass

        self._attach_bar = attach_bar
        self._attach_inner = attach_inner
        self._attach_inner_layout = attach_inner_layout
        self._attach_scroll = attach_scroll

        root.addWidget(attach_bar)

        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        input_box = QFrame()
        input_box.setObjectName("chat-input-box")
        input_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        ib_layout = QHBoxLayout(input_box)
        ib_layout.setContentsMargins(10, 8, 8, 8)
        ib_layout.setSpacing(8)

        self.upload_btn = QPushButton("📎")
        self.upload_btn.setStyleSheet("")
        try:
            from PySide6.QtGui import QFont as _QFont
            self.upload_btn.setFont(_QFont("Segoe UI Emoji", 16))
        except Exception:
            pass
        try:
            self.upload_btn.setProperty("no_bg", True)
        except Exception:
            pass
        self.upload_btn.clicked.connect(self.upload_file)
        ib_layout.addWidget(self.upload_btn, 0, Qt.AlignVCenter)

        # Voice input button (mới - tương tác tự nhiên)
        self.voice_btn = QPushButton("🎤")
        self.voice_btn.setStyleSheet("")
        try:
            from PySide6.QtGui import QFont as _QFont2
            self.voice_btn.setFont(_QFont2("Segoe UI Emoji", 16))
        except Exception:
            pass
        try:
            self.voice_btn.setProperty("no_bg", True)
        except Exception:
            pass
        try:
            self.voice_btn.setToolTip("Nhấn để nói" if getattr(self, 'language', 'vi') == 'vi' else "Voice input")
        except Exception:
            pass
        self.voice_btn.clicked.connect(self.start_voice_input)
        ib_layout.addWidget(self.voice_btn, 0, Qt.AlignVCenter)

        self.input_field = ChatInputTextEdit(self)
        try:
            self.input_field.setPlaceholderText(self._t('input_placeholder'))
        except Exception:
            pass
        self.input_field.setStyleSheet("")
        try:
            self.input_field.textChanged.connect(self._update_input_height)
        except Exception:
            pass
        ib_layout.addWidget(self.input_field, 1)

        self.send_btn = QPushButton("➤")
        self.send_btn.setStyleSheet("")
        try:
            from PySide6.QtGui import QFont as _QFont
            self.send_btn.setFont(_QFont("Segoe UI Emoji", 16))
        except Exception:
            pass
        try:
            self.send_btn.setProperty("no_bg", True)
        except Exception:
            pass
        self.send_btn.clicked.connect(self.send_message)
        ib_layout.addWidget(self.send_btn, 0, Qt.AlignVCenter)

        layout.addWidget(input_box, 1)
        self._input_layout = layout
        try:
            self.upload_btn.setToolTip(self._t("chat.upload_tooltip", "Attach"))
            self.send_btn.setToolTip(self._t('send'))
            self.voice_btn.setToolTip("Giọng nói" if getattr(self, 'language', 'vi') == 'vi' else "Voice")
        except Exception:
            pass
        self._input_buttons = [self.upload_btn, self.voice_btn, self.send_btn]
        root.addWidget(row)
        try:
            self._update_input_height()
        except Exception:
            pass
        return input_widget

    def _render_attachments(self):
        try:
            pending = list(getattr(self, "_pending_attachments", []) or [])
        except Exception:
            pending = []

        bar = getattr(self, "_attach_bar", None)
        inner_layout = getattr(self, "_attach_inner_layout", None)
        if not bar or not inner_layout:
            return

        try:
            while inner_layout.count():
                item = inner_layout.takeAt(0)
                w = item.widget()
                if w:
                    try:
                        w.deleteLater()
                    except Exception:
                        pass
        except Exception:
            pass

        if not pending:
            try:
                bar.hide()
            except Exception:
                pass
            return

        try:
            bar.show()
        except Exception:
            pass

        try:
            theme = getattr(self, "theme", "dark")
            if theme == "dark":
                chip_bg = "rgba(19,22,33,0.95)"
                chip_fg = "#E5E7EB"
                chip_border = "#374151"
                chip_hover = "rgba(35,40,58,1.0)"
            else:
                chip_bg = "#FFFFFF"
                chip_fg = "#0F172A"
                chip_border = "#CBD5E1"
                chip_hover = "#F1F5F9"
        except Exception:
            chip_bg = "#FFFFFF"
            chip_fg = "#0F172A"
            chip_border = "#CBD5E1"
            chip_hover = "#F1F5F9"

        for fp in pending:
            try:
                import os
                name = os.path.basename(str(fp or "")) or str(fp or "")
            except Exception:
                name = str(fp or "")

            chip = QPushButton(f"📎 {name}  ×")
            chip.setStyleSheet(
                f"QPushButton {{ background-color: {chip_bg}; color: {chip_fg}; border: 1px solid {chip_border}; "
                f"border-radius: 10px; padding: 4px 10px; text-align: left; }}"
                f"QPushButton:hover {{ background-color: {chip_hover}; }}"
            )

            def _mk_remove(path):
                def _remove():
                    try:
                        cur = list(getattr(self, "_pending_attachments", []) or [])
                    except Exception:
                        cur = []
                    try:
                        cur = [p for p in cur if str(p) != str(path)]
                    except Exception:
                        pass
                    self._pending_attachments = cur
                    try:
                        self._render_attachments()
                    except Exception:
                        pass
                return _remove

            chip.clicked.connect(_mk_remove(fp))
            inner_layout.addWidget(chip)

        inner_layout.addStretch()

    def _update_input_height(self):
        te = getattr(self, "input_field", None)
        if not te:
            return
        try:
            scale = float(getattr(self, "_scale", 1.0) or 1.0)
        except Exception:
            scale = 1.0
        try:
            fm = te.fontMetrics()
            line_h = int(fm.lineSpacing())
        except Exception:
            line_h = 18
        pad = int(18 * scale)
        min_lines = 1
        max_lines = 3
        min_h = max(int((min_lines * line_h) + pad), int(34 * scale), 28)
        max_h = max(int((max_lines * line_h) + pad), min_h)
        desired = min_h
        try:
            desired = int(float(te.document().size().height()) + pad)
        except Exception:
            desired = min_h
        h = max(min_h, min(max_h, desired))
        try:
            te.setFixedHeight(h)
        except Exception:
            pass

    def apply_theme(self):
        try:
            self.theme = SettingsManager().get_theme() or 'dark'
        except Exception:
            self.theme = 'dark'
            
        # Update chat content background
        if hasattr(self, 'chat_content'):
            chat_bg = '#FFFFFF' if self.theme != 'dark' else '#020617'
            self.chat_content.setStyleSheet(f"#chat_content {{ background-color: {chat_bg}; }}")
            
        # Re-render messages with new theme
        if hasattr(self, 'chat_layout') and hasattr(self, 'messages'):
            # Clear existing items
            while self.chat_layout.count():
                item = self.chat_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            # Re-add stretch to push messages up
            self.chat_layout.addStretch()
            
            # Re-render all messages
            for msg in self.messages:
                self._render_message(msg['sender'], msg['message'], msg['type'])
        
        if self.theme == 'dark':
            base_bg = 'rgba(18,20,28,0.88)'
            base_border = '#313543'
        else:
            base_bg = '#E6F7FF'
            base_border = '#93C5FD'
            
        docked = getattr(self, "is_docked", False)
        if docked:
            radius_style = "border-top-left-radius: 20px; border-bottom-left-radius: 20px; border-top-right-radius: 0px; border-bottom-right-radius: 0px;"
        else:
            radius_style = "border-radius: 20px;"
            
        if hasattr(self, 'chat_container'):
            self.chat_container.setStyleSheet(f"""
                #chat-container {{
                    background-color: {base_bg};
                    border: 1px solid {base_border};
                    {radius_style}
                    padding: 0px;
                }}
            """)
            
        input_bg = '#E6F7FF' if self.theme != 'dark' else 'rgba(27,31,42,0.7)'
        self._input_bg_style = f"#chat-input {{ background-color: {input_bg}; border-bottom-left-radius: 14px; border-bottom-right-radius: 14px; padding: 10px; }}"
        try:
            self.findChild(QWidget, "chat-input").setStyleSheet(self._input_bg_style)
        except Exception:
            pass

        try:
            brand = SettingsManager().get("brand_color", "#7F56D9")
        except Exception:
            brand = "#7F56D9"
        try:
            self.findChild(QWidget, "chat-header").setStyleSheet(f"""
                #chat-header {{
                    background-color: {brand};
                    background: linear-gradient(135deg, {brand}, #059669);
                    border-top-left-radius: 16px;
                    border-top-right-radius: 16px;
                    padding: 12px;
                }}
            """)
        except Exception:
            pass
            
        # Input field and buttons styling
        try:
            if self.theme == 'dark':
                input_bg_color = "rgba(30, 30, 40, 0.8)"
                input_text_color = "#FFFFFF"
                input_border = "1px solid #374151"
                placeholder_color = "#9CA3AF"
                box_bg = "rgba(19, 22, 33, 0.9)"
            else:
                input_bg_color = "#FFFFFF"
                input_text_color = "#1A1A1A"
                input_border = "1px solid #CBD5E1"
                placeholder_color = "#64748B"
                box_bg = "#FFFFFF"
                
            if hasattr(self, 'input_field') and self.input_field:
                self.input_field.setStyleSheet(f"""
                    QTextEdit {{
                        background-color: {input_bg_color};
                        color: {input_text_color};
                        border: none;
                        border-radius: 8px;
                        padding: 8px;
                    }}
                """)
            try:
                box = self.findChild(QFrame, "chat-input-box")
                if box:
                    box.setStyleSheet(f"QFrame#chat-input-box {{ background-color: {box_bg}; border: {input_border}; border-radius: 12px; }}")
            except Exception:
                pass
            try:
                self._render_attachments()
            except Exception:
                pass
                
            # Input buttons
            for btn in getattr(self, '_input_buttons', []):
                if not btn: continue
                
                # Default values based on theme
                if self.theme == 'dark':
                    bg_color = "rgba(19, 22, 33, 0.95)"
                    text_color = "#E5E7EB"
                    border = "1px solid #374151"
                    hover_bg = "rgba(35, 40, 58, 1.0)"
                else:
                    bg_color = "#FFFFFF"
                    text_color = "#64748B"
                    border = "1px solid #E2E8F0"
                    hover_bg = "#F8FAFC"
                
                if btn.property("no_bg"):
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: transparent;
                            color: {text_color};
                            border: none;
                            border-radius: 10px;
                            padding: 0px;
                            min-width: 34px;
                            max-width: 34px;
                            min-height: 34px;
                            max-height: 34px;
                        }}
                        QPushButton:hover {{
                            background-color: {hover_bg};
                        }}
                    """)
                else:
                    if btn.property("primary"):
                        bg_color = "#7F56D9"
                        text_color = "#FFFFFF"
                        border = "none"
                        hover_bg = "#6941C6"
                    elif btn.property("success"):
                        bg_color = "#12B76A"
                        text_color = "#FFFFFF"
                        border = "none"
                        hover_bg = "#0F9C5A"
                    elif btn.property("warning"):
                        bg_color = "#F79009"
                        text_color = "#FFFFFF"
                        border = "none"
                        hover_bg = "#D97706"
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {bg_color};
                            color: {text_color};
                            border: {border};
                            border-radius: 999px;
                            padding: 0px;
                            min-width: 36px;
                            max-width: 36px;
                            min-height: 36px;
                            max-height: 36px;
                        }}
                        QPushButton:hover {{
                            background-color: {hover_bg};
                        }}
                    """)
        except Exception:
            pass

        try:
            self._resize_controls()
        except Exception:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            self._resize_controls()
        except Exception:
            pass
        try:
            if not getattr(self, "_manual_positioned", False):
                from PySide6.QtWidgets import QApplication
                screen = QApplication.primaryScreen().availableGeometry()
                x = min(max(self.x(), screen.left()), screen.right() - self.width())
                y = min(max(self.y(), screen.top()), screen.bottom() - self.height())
                self.move(x, y)
        except Exception:
            pass

    def _resize_controls(self):
        w = max(self.width(), 320)
        h = max(self.height(), 360)
        scale = getattr(self, "_scale", 1.0)
        btn = max(int(32 * scale), min(int(48 * scale), int(h * 0.07)))
        radius = btn // 2
        theme = getattr(self, "theme", "dark")
        if theme == "dark":
            btn_bg = "rgba(19,22,33,0.95)"
            btn_hover = "rgba(35,40,58,1.0)"
            btn_border = "#374151"
            btn_fg = "#E5E7EB"
        else:
            btn_bg = "#EEF2FF"
            btn_hover = "#E0EAFF"
            btn_border = "#7F56D9"
            btn_fg = "#7F56D9"
        header_btns = getattr(self, '_header_btns', [])
        for idx, b in enumerate(header_btns):
            b.setMinimumSize(btn, btn)
            b.setMaximumSize(btn, btn)
            try:
                bg = btn_bg
                hover_bg = btn_hover
                fg = btn_fg
                border = btn_border
                if idx == 1:
                    bg = "#DC2626"
                    hover_bg = "#EF4444"
                    border = "#DC2626"
                    fg = "#FFFFFF"
                style = (
                    f"QPushButton {{ padding: 0px; margin: 0px; border-radius: {radius}px; "
                    f"background-color: {bg}; color: {fg}; border: 1px solid {border}; }}"
                    f"QPushButton:hover {{ background-color: {hover_bg}; }}"
                )
                b.setStyleSheet(style)
                hf = b.font()
                hf.setPointSizeF(max(9.0, min(14.0, 10.0 * float(scale))))
                b.setFont(hf)
            except Exception:
                pass
        try:
            if hasattr(self, "chat_header") and self.chat_header:
                header_h = max(int(btn * 1.6), int(44 * scale))
                self.chat_header.setMinimumHeight(header_h)
                self.chat_header.setMaximumHeight(header_h)
        except Exception:
            pass
        try:
            # Font size calculation preserved for potential future use or other widgets
            fsize = max(int(13 * scale), min(int(20 * scale), int(w * 0.035 * scale)))
            pad = max(int(8 * scale), min(int(18 * scale), int(w * 0.02 * scale)))
        except Exception:
            pass
        try:
            ih = max(int(40 * scale), min(int(56 * scale), int(h * 0.09)))
            for b in getattr(self, '_input_buttons', []):
                b.setMinimumHeight(ih)
                b.setMaximumHeight(ih)
                b.setMinimumWidth(ih)
                b.setMaximumWidth(ih)
                try:
                    bf = b.font()
                    bf.setPointSizeF(max(12.0, min(24.0, 15.0 * float(scale))))
                    b.setFont(bf)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            min_text = max(int(160 * scale), int(h * 0.5))
            if hasattr(self, 'chat_view'):
                # Adjust scroll area minimum height if needed, or just pass
                pass
        except Exception:
            pass
        try:
            if hasattr(self, "input_field") and self.input_field:
                ff = self.input_field.font()
                ff.setPointSizeF(max(12.0, min(22.0, 14.0 * float(scale))))
                self.input_field.setFont(ff)
                try:
                    self._update_input_height()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if hasattr(self, "_title_label") and self._title_label:
                f = self._title_label.font()
                base = 16.0
                f.setPointSizeF(max(12.0, min(22.0, base * float(scale))))
                self._title_label.setFont(f)
        except Exception:
            pass
        
    def set_scale(self, scale: float):
        try:
            self._scale = max(0.55, min(1.9, float(scale)))
        except Exception:
            self._scale = 1.0
        try:
            self._resize_controls()
        except Exception:
            pass

        
    def send_message(self):
        """Send user message"""
        try:
            if bool(getattr(self, "_busy", False)):
                return
        except Exception:
            pass
        message = ""
        try:
            message = str(self.input_field.toPlainText() or "").strip()
        except Exception:
            try:
                message = str(self.input_field.text() or "").strip()
            except Exception:
                message = ""
        try:
            files = list(getattr(self, "_pending_attachments", []) or [])
        except Exception:
            files = []
        if not message and not files:
            return

        display = message
        if files:
            try:
                import os
                names = [os.path.basename(str(p or "")) for p in files]
            except Exception:
                names = [str(p or "") for p in files]
            tail = ", ".join([n for n in names if n])[:220]
            if display:
                display = display + "\n\n" + ("Đính kèm: " if getattr(self, "language", "vi") == "vi" else "Attachments: ") + tail
            else:
                display = ("Đính kèm: " if getattr(self, "language", "vi") == "vi" else "Attachments: ") + tail
            
        # Add user message
        self.add_message("You", display, "user")
        
        # Clear input
        try:
            self.input_field.clear()
        except Exception:
            pass
        try:
            self._pending_attachments = []
            self._render_attachments()
        except Exception:
            pass
        try:
            self._update_input_height()
        except Exception:
            pass
        
        # Emit signal for AI processing
        payload = message
        if not payload:
            payload = "Phân tích các file đính kèm" if getattr(self, "language", "vi") == "vi" else "Analyze the attached files"
        if files:
            payload = payload + "\n\n[ATTACHMENTS]\n" + "\n".join([str(p) for p in files if str(p or "").strip()])
        self.message_sent.emit(payload)
        
        # Simulate AI response only when mock mode is enabled
        try:
            if bool(SettingsManager().get('ai.mock', False)):
                QTimer.singleShot(700, lambda: self.simulate_ai_response(message))
        except Exception:
            pass

    def set_busy(self, busy: bool):
        try:
            self._busy = bool(busy)
        except Exception:
            self._busy = bool(busy)
        disabled = bool(getattr(self, "_busy", False))
        try:
            if hasattr(self, "input_field") and self.input_field:
                self.input_field.setEnabled(not disabled)
                try:
                    if disabled:
                        self.input_field.setPlaceholderText(self._t('busy_placeholder'))
                    else:
                        self.input_field.setPlaceholderText(self._t('input_placeholder'))
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if hasattr(self, "send_btn") and self.send_btn:
                self.send_btn.setEnabled(not disabled)
        except Exception:
            pass
        try:
            if hasattr(self, "upload_btn") and self.upload_btn:
                self.upload_btn.setEnabled(not disabled)
        except Exception:
            pass

    def set_language(self, lang: str):
        self.language = lang or 'en'
        try:
            # Update UI texts
            self.input_field.setPlaceholderText(self._t('input_placeholder'))
            if hasattr(self, '_header_btns'):
                try:
                    if len(self._header_btns) >= 5:
                        self._header_btns[0].setToolTip(self._t('dock'))
                        self._header_btns[1].setToolTip(self._t('wide'))
                        self._header_btns[2].setToolTip(self._t('detail'))
                        self._header_btns[3].setToolTip(self._t('minimize'))
                        self._header_btns[4].setToolTip(self._t('close'))
                except Exception:
                    pass
            try:
                self.findChild(QLabel).setText(self._t('title').upper())
            except Exception:
                pass
        except Exception:
            pass
        try:
            if not getattr(self, "messages", None):
                self.add_message("Edubot", self._t('welcome'), "ai")
        except Exception:
            pass

    def _t(self, key: str) -> str:
        mapping = {
            'welcome': 'chat.welcome',
            'title': 'chat.title',
            'input_placeholder': 'chat.input_placeholder',
            'busy_placeholder': 'chat.busy_placeholder',
            'send': 'chat.send',
            'upload': 'chat.upload',
            'suggest': 'chat.suggest',
            'copy': 'chat.copy',
            'dock': 'chat.dock',
            'wide': 'chat.wide',
            'detail': 'chat.detail',
            'brief': 'chat.brief',
            'standard': 'chat.standard',
            'detailed': 'chat.detailed',
            'minimize': 'chat.minimize',
            'close': 'chat.close'
        }
        lang = getattr(self, 'language', 'en')
        return I18n.t(mapping.get(key, key), lang)

    def upload_file(self):
        try:
            try:
                from eduplay.core.i18n import I18n as _UpI18n
                _lang = getattr(self, "language", "en")
                caption = _UpI18n.t("chat.attach_title", _lang)
                filt = _UpI18n.t("chat.attach_filter", _lang)
                if not caption or caption == "chat.attach_title":
                    raise ValueError("i18n-missing")
                if not filt or filt == "chat.attach_filter":
                    raise ValueError("i18n-missing")
            except Exception:
                if getattr(self, "language", "vi") == "vi":
                    caption = "Đính kèm tệp"
                    filt = "Tài liệu (*.docx *.doc *.pdf *.txt);;Hình ảnh (*.png *.jpg *.jpeg *.webp *.bmp *.gif);;All Files (*.*)"
                else:
                    caption = "Attach files"
                    filt = "Documents (*.docx *.doc *.pdf *.txt);;Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif);;All Files (*.*)"
            files = get_open_file_names(self, caption, "", filt)
            if not files:
                return
            cur = list(getattr(self, "_pending_attachments", []) or [])
            for fp in files:
                p = str(fp or "").strip()
                if not p:
                    continue
                if p not in cur:
                    cur.append(p)
            self._pending_attachments = cur
            self._render_attachments()
        except Exception as e:
            self.add_message("AI", f"Upload failed: {str(e)}", "ai")

    def _on_voice_status(self, msg: str):
        # Hiển thị trạng thái ghi/phân tích ở placeholder + nút, KHÔNG tạo bubble chat, KHÔNG chạm input text
        try:
            try:
                if not hasattr(self, "_orig_input_placeholder"):
                    try:
                        self._orig_input_placeholder = self.input_field.placeholderText()
                    except Exception:
                        self._orig_input_placeholder = ""
            except Exception:
                pass
            try:
                self.input_field.setPlaceholderText(str(msg or ""))
            except Exception:
                pass
            # Xóa status bubble cũ nếu còn (tránh kẹt "Đang ghi âm." như screenshot)
            try:
                self.clear_status()
            except Exception:
                pass
        except Exception:
            pass

    def _on_voice_text(self, text: str):
        try:
            text = str(text or "").strip()
            if not text:
                return
            text = self._auto_correct_text(text)
            try:
                cur = str(self.input_field.toPlainText() or "").strip()
            except Exception:
                cur = ""
            new_text = (cur + " " + text).strip() if cur else text
            try:
                self.input_field.setPlainText(new_text)
                self.input_field.setFocus()
                try:
                    cursor = self.input_field.textCursor()
                    cursor.movePosition(cursor.End)
                    self.input_field.setTextCursor(cursor)
                except Exception:
                    pass
            except Exception:
                try:
                    self.input_field.setText(new_text)
                except Exception:
                    pass
            try:
                self.clear_status()
            except Exception:
                pass
        except Exception:
            pass
        print(f"[VOICE] text -> input: {str(text)[:80]}", flush=True)

    def _on_voice_error(self, msg: str):
        # Báo lỗi ở placeholder 2s rồi trả lại, không spam bubble chat
        try:
            try:
                self.input_field.setPlaceholderText(str(msg or ""))
            except Exception:
                pass
            try:
                self.clear_status()
            except Exception:
                pass
            from PySide6.QtCore import QTimer
            try:
                orig = getattr(self, "_orig_input_placeholder", "")
            except Exception:
                orig = ""
            QTimer.singleShot(2000, lambda: self._restore_voice_placeholder(orig))
        except Exception:
            pass
        print(f"[VOICE] error: {str(msg)[:200]}", flush=True)

    def _restore_voice_placeholder(self, orig=None):
        try:
            if orig is None:
                orig = getattr(self, "_orig_input_placeholder", "")
            self.input_field.setPlaceholderText(str(orig or ""))
        except Exception:
            pass

    def _on_voice_done(self):
        try:
            self._voice_recording = False
            self._voice_stop_requested = False
            try:
                self.send_btn.clicked.disconnect()
            except Exception:
                pass
            self.send_btn.setText(self._orig_send_text if hasattr(self, "_orig_send_text") else "➤")
            try:
                from PySide6.QtGui import QFont as _QFontRestore
                self.send_btn.setFont(_QFontRestore("Segoe UI Emoji", 16))
            except Exception:
                pass
            self.send_btn.setStyleSheet("")
            try:
                self.send_btn.setProperty("no_bg", True)
            except Exception:
                pass
            self.send_btn.setToolTip(self._orig_send_tooltip if hasattr(self, "_orig_send_tooltip") else "")
            self.send_btn.clicked.connect(self.send_message)
            self.send_btn.setEnabled(True)
        except Exception:
            pass
        try:
            self.voice_btn.setEnabled(True)
            self.voice_btn.setText("🎤")
        except Exception:
            pass
        # Trả lại placeholder gốc + xóa status bubble kẹt
        try:
            self._restore_voice_placeholder()
        except Exception:
            pass
        try:
            self.clear_status()
        except Exception:
            pass

    def start_voice_input(self):
        """Whisper-only, gọn như ChatGPT: bấm 🎤 ghi, nút ➤ → ⏹ để ngắt, ghi xong cho thẳng vào khung nhập."""
        if getattr(self, "_voice_recording", False):
            try:
                self._voice_stop_requested = True
            except Exception:
                pass
            return
        self._voice_recording = True
        self._voice_stop_requested = False
        try:
            self._orig_send_text = self.send_btn.text()
            self._orig_send_tooltip = self.send_btn.toolTip()
            try:
                self.send_btn.clicked.disconnect()
            except Exception:
                pass
            self.send_btn.setText("⏹")
            try:
                from PySide6.QtGui import QFont as _QFontStop
                self.send_btn.setFont(_QFontStop("Segoe UI Symbol", 18))
            except Exception:
                pass
            self.send_btn.setStyleSheet("QPushButton { background-color: #EF4444; color: #FFFFFF; border: none; border-radius: 16px; min-width: 32px; max-width: 32px; min-height: 32px; max-height: 32px; } QPushButton:hover { background-color: #DC2626; }")
            self.send_btn.setToolTip("Dừng ghi" if getattr(self,'language','vi')=='vi' else "Stop")
            self.send_btn.clicked.connect(self._stop_voice_recording)
            self.send_btn.setEnabled(True)
            self.voice_btn.setEnabled(False)
            self.voice_btn.setText("●")
        except Exception:
            pass
        def _t_voice(key, fallback):
            try:
                from eduplay.core.i18n import I18n
                v = I18n.t(key, getattr(self, 'language','vi') or 'vi')
                if v and v != key:
                    return v
            except Exception:
                pass
            return fallback
        import threading
        def _collect_whisper_keys():
            keys = []
            try:
                from eduplay.core.settings_manager import SettingsManager
                sm = SettingsManager()
                single = str(sm.get("ai_settings.groq_api_key", "") or "").strip()
                if single:
                    keys.append(single)
                multi = sm.get("ai_settings.groq_api_keys", "") or sm.get("ai_settings.groq_keys", "")
                if isinstance(multi, list):
                    for k in multi:
                        k = str(k or "").strip()
                        if k and k not in keys:
                            keys.append(k)
                elif isinstance(multi, str) and multi.strip():
                    import re
                    for part in re.split(r"[,;\s]+", multi.strip()):
                        part = part.strip()
                        if part and part not in keys:
                            keys.append(part)
            except Exception:
                pass
            try:
                import os as _os
                for env_name in ("GROQ_API_KEY", "GROQ_KEY_1", "GROQ_KEY_2", "GROQ_KEY_3", "GROQ_KEY_4", "GROQ_KEY_5"):
                    k = str(_os.getenv(env_name) or "").strip()
                    if k and k not in keys:
                        keys.append(k)
                raw = str(_os.getenv("GROQ_API_KEYS") or "").strip()
                if raw:
                    import re
                    for part in re.split(r"[,;\s]+", raw):
                        part = part.strip()
                        if part and part not in keys:
                            keys.append(part)
            except Exception:
                pass
            return keys
        def _run_voice():
            tmp_wav = None
            try:
                import tempfile, os
                from pathlib import Path
                tmp_wav = Path(tempfile.gettempdir()) / f"eduplay_voice_{os.getpid()}_{int(__import__('time').time()*1000)}.wav"
                print("[VOICE] start recording", flush=True)
                try:
                    self.voice_status_msg.emit(_t_voice("chat.voice.recording", "Dang ghi am..."))
                except Exception:
                    pass
                recorded = False
                rec_err = ""
                # Ưu tiên sounddevice chunked để bấm ⏹ dừng vẫn giữ audio đã nói; ghi bằng wave stdlib (không cần soundfile)
                try:
                    import sounddevice as sd
                    import time as _time
                    import wave as _wave
                    sr_rate = 16000
                    chunk_dur = 0.3
                    max_dur = 15.0
                    chunks = []
                    start_t = _time.time()
                    silent_chunks = 0
                    print("[VOICE] recording via sounddevice (stoppable)", flush=True)
                    while True:
                        if getattr(self, "_voice_stop_requested", False):
                            print("[VOICE] stop requested, keep recorded chunks", flush=True)
                            break
                        if _time.time() - start_t >= max_dur:
                            break
                        try:
                            rec = sd.rec(int(chunk_dur * sr_rate), samplerate=sr_rate, channels=1, dtype='int16')
                            sd.wait()
                        except Exception as e_chunk:
                            print(f"[VOICE] chunk failed: {str(e_chunk)[:100]}", flush=True)
                            break
                        chunks.append(rec)
                        try:
                            import numpy as _np
                            peak = int(abs(rec).max()) if rec.size else 0
                            if peak < 300:
                                silent_chunks += 1
                            else:
                                silent_chunks = 0
                            # Tự dừng sau 2s im lặng mà đã có ít nhất 1.5s tiếng
                            if silent_chunks >= 7 and len(chunks) >= 5:
                                print("[VOICE] auto-stop on silence", flush=True)
                                break
                        except Exception:
                            pass
                        if getattr(self, "_voice_stop_requested", False):
                            break
                    if chunks:
                        import numpy as _np
                        data = _np.concatenate(chunks, axis=0)
                        with _wave.open(str(tmp_wav), "wb") as wf:
                            wf.setnchannels(1)
                            wf.setsampwidth(2)
                            wf.setframerate(sr_rate)
                            wf.writeframes(data.tobytes())
                        recorded = True
                        print(f"[VOICE] recorded {len(chunks)} chunks", flush=True)
                    else:
                        raise RuntimeError("no_chunks")
                except ImportError as e:
                    print(f"[VOICE] no sounddevice ({str(e)[:80]}), fallback sr.listen", flush=True)
                    try:
                        import speech_recognition as sr
                        r = sr.Recognizer()
                        with sr.Microphone() as source:
                            r.adjust_for_ambient_noise(source, duration=0.4)
                            audio = r.listen(source, timeout=8, phrase_time_limit=10)
                            with open(tmp_wav, "wb") as f:
                                f.write(audio.get_wav_data())
                            recorded = True
                        print("[VOICE] recorded via microphone (sr fallback)", flush=True)
                    except ImportError as e2:
                        print(f"[VOICE] missing speech_recognition: {e2}", flush=True)
                        try:
                            self.voice_error_msg.emit(_t_voice("chat.voice.not_installed", "Thiet bi chua cai voice"))
                        except Exception:
                            pass
                        return
                    except Exception as e_sr:
                        print(f"[VOICE] mic record failed: {str(e_sr)[:150]}", flush=True)
                        try:
                            self.voice_error_msg.emit(f"Voice loi mic: {str(e_sr)[:80]}")
                        except Exception:
                            pass
                        return
                except Exception as e_sr:
                    # sounddevice lỗi (thiếu NumPy như log: "NumPy must be installed") hoặc no_chunks
                    # → fallback sr.listen thay vì báo lỗi ngay
                    print(f"[VOICE] sounddevice failed ({str(e_sr)[:100]}), fallback sr.listen", flush=True)
                    try:
                        if tmp_wav.exists() and tmp_wav.stat().st_size > 1000:
                            recorded = True
                        else:
                            raise e_sr
                    except Exception:
                        pass
                    if not recorded:
                        try:
                            import speech_recognition as sr
                            r = sr.Recognizer()
                            with sr.Microphone() as source:
                                r.adjust_for_ambient_noise(source, duration=0.4)
                                audio = r.listen(source, timeout=8, phrase_time_limit=10)
                                with open(tmp_wav, "wb") as f:
                                    f.write(audio.get_wav_data())
                                recorded = True
                            print("[VOICE] recorded via microphone (sr fallback after sounddevice fail)", flush=True)
                        except ImportError as e2:
                            print(f"[VOICE] missing speech_recognition: {e2}", flush=True)
                            try:
                                self.voice_error_msg.emit(_t_voice("chat.voice.not_installed", "Thiet bi chua cai voice"))
                            except Exception:
                                pass
                            return
                        except Exception as e_sr2:
                            print(f"[VOICE] mic record failed: {str(e_sr2)[:150]}", flush=True)
                            try:
                                self.voice_error_msg.emit(f"Voice loi mic: {str(e_sr2)[:80]}")
                            except Exception:
                                pass
                            return
                if not recorded or not tmp_wav.exists():
                    print("[VOICE] no audio recorded", flush=True)
                    try:
                        self.voice_error_msg.emit("Voice loi: no_audio")
                    except Exception:
                        pass
                    return
                # Bấm ⏹ là để kết thúc và phân tích, không phải hủy → reset flag trước STT
                try:
                    self._voice_stop_requested = False
                except Exception:
                    pass
                try:
                    self.voice_status_msg.emit(_t_voice("chat.voice.analyzing", "Dang phan tich..."))
                except Exception:
                    pass
                print(f"[VOICE] analyzing {tmp_wav} size={tmp_wav.stat().st_size if tmp_wav.exists() else 0}", flush=True)
                # Google STT free, thử cả 5 ngôn ngữ (vi/en/fr/es/de), ưu tiên ngôn ngữ UI trước
                text = ""
                last_err = ""
                try:
                    import speech_recognition as sr
                    r = sr.Recognizer()
                    with sr.AudioFile(str(tmp_wav)) as source:
                        audio = r.record(source)
                    _cur = str(getattr(self, 'language', 'vi') or 'vi').lower()[:2]
                    _order = ["vi-VN", "en-US", "fr-FR", "es-ES", "de-DE"]
                    _pref = {"vi": "vi-VN", "en": "en-US", "fr": "fr-FR", "es": "es-ES", "de": "de-DE"}.get(_cur)
                    if _pref and _pref in _order:
                        _order = [_pref] + [c for c in _order if c != _pref]
                    print(f"[VOICE] Google STT free order={_order}", flush=True)
                    for lang_code in _order:
                        try:
                            text2 = r.recognize_google(audio, language=lang_code)
                            if str(text2 or "").strip():
                                text = str(text2).strip()
                                print(f"[VOICE] Google STT OK lang={lang_code} len={len(text)}", flush=True)
                                break
                        except Exception as e_one:
                            try:
                                import speech_recognition as _sr_one
                                if isinstance(e_one, _sr_one.UnknownValueError):
                                    continue
                                last_err = str(e_one)[:150]
                            except Exception:
                                pass
                            continue
                    if not text and not last_err:
                        last_err = "Nghe không rõ, nói to/rõ lại"
                except Exception as e_google:
                    try:
                        import speech_recognition as _sr_err
                        if isinstance(e_google, _sr_err.UnknownValueError):
                            last_err = "Nghe không rõ, nói to/rõ lại"
                        elif isinstance(e_google, _sr_err.RequestError):
                            last_err = f"Không gọi được Google STT (mạng): {str(e_google)[:80]}"
                        else:
                            last_err = str(e_google)[:200] or type(e_google).__name__
                    except Exception:
                        last_err = str(e_google)[:200] or "unknown"
                    print(f"[VOICE] Google STT fail: {last_err}", flush=True)
                try:
                    if tmp_wav and tmp_wav.exists():
                        tmp_wav.unlink(missing_ok=True)
                except Exception:
                    pass
                if text:
                    print(f"[VOICE] done text len={len(text)}", flush=True)
                    try:
                        self.voice_text_msg.emit(text)
                    except Exception as e:
                        print(f"[VOICE] emit text failed: {e}", flush=True)
                else:
                    low = str(last_err).lower()
                    if any(k in low for k in ["429", "503", "overloaded", "rate", "capacity", "busy", "quota"]):
                        try:
                            self.voice_error_msg.emit(_t_voice("chat.voice.overloaded", "Hien tai tinh nang nay dang qua tai"))
                        except Exception:
                            pass
                    else:
                        try:
                            self.voice_error_msg.emit(f"Voice loi: {last_err[:100] or 'empty'}")
                        except Exception:
                            pass
            except Exception as e:
                print(f"[VOICE] fatal: {str(e)[:200]}", flush=True)
                try:
                    self.voice_error_msg.emit(f"Voice loi: {str(e)[:100]}")
                except Exception:
                    pass
            finally:
                try:
                    if tmp_wav and tmp_wav.exists():
                        tmp_wav.unlink(missing_ok=True)
                except Exception:
                    pass
                try:
                    self.voice_done.emit()
                except Exception:
                    pass
        threading.Thread(target=_run_voice, daemon=True).start()

    def _stop_voice_recording(self):
        """Ngắt ghi âm khi đang ghi - bấm ⏹ để dừng"""
        try:
            self._voice_stop_requested = True
            self.send_btn.setText("⏸")
        except Exception:
            pass

    def _auto_correct_text(self, text: str) -> str:
        """Auto-correct tiếng Việt đơn giản: sửa lỗi gõ thường gặp, chuẩn hóa khoảng trắng"""
        try:
            import re
            t = str(text or "")
            # chuẩn hóa khoảng trắng
            t = re.sub(r'\s+', ' ', t).strip()
            # sửa lỗi thường gặp
            reps = {
                "cau hoi": "câu hỏi", "cau hỏi": "câu hỏi", "trac nghiem": "trắc nghiệm",
                "dang ": "dạng ", "bao luc": "bạo lực", "hoc duong": "học đường",
                "k ": "không ", "ko ": "không ", "dc ": "được ", "vs ": "với ",
            }
            low = t.lower()
            for k, v in reps.items():
                if k in low:
                    # thay thế giữ nguyên hoa thường đơn giản
                    t = re.sub(re.escape(k), v, t, flags=re.IGNORECASE)
            # viết hoa chữ đầu
            if t and t[0].islower():
                t = t[0].upper() + t[1:]
            return t
        except Exception:
            return text

    def _get_tts(self):
        tts = getattr(self, "_tts_engine", None)
        if tts is not None:
            return tts
        try:
            from PySide6.QtTextToSpeech import QTextToSpeech
            try:
                print(f"[TTS] engines={QTextToSpeech.availableEngines()}", flush=True)
            except Exception:
                pass
            # Chọn engine có voice khớp ngôn ngữ UI (winrt thường có voice Việt, sapi chỉ có Anh)
            try:
                _uilang = str(getattr(self, 'language', 'en') or 'en').lower()[:2]
            except Exception:
                _uilang = "en"
            tts = None
            _best = None
            _best_score = -1
            for _eng in ("winrt", "sapi", None):
                try:
                    _cand = QTextToSpeech(_eng, self) if _eng else QTextToSpeech(self)
                except Exception as e_eng:
                    print(f"[TTS] engine {_eng} failed: {str(e_eng)[:80]}", flush=True)
                    continue
                _score = 0
                try:
                    for v in _cand.availableVoices():
                        try:
                            _vl = v.locale().name().lower()
                        except Exception:
                            _vl = ""
                        if _uilang in _vl or (_uilang == "vi" and "vie" in _vl):
                            _score = 2
                            break
                    else:
                        _score = 1 if len(_cand.availableVoices()) else 0
                except Exception:
                    _score = 0
                print(f"[TTS] engine candidate {_eng}: score={_score}", flush=True)
                if _score > _best_score:
                    if _best is not None:
                        try:
                            _best.deleteLater()
                        except Exception:
                            pass
                    _best = _cand
                    _best_score = _score
                else:
                    try:
                        _cand.deleteLater()
                    except Exception:
                        pass
                if _best_score >= 2:
                    break
            tts = _best
            if tts is None:
                return None
            try:
                tts.setVolume(1.0)
                try:
                    tts.setRate(0.0)
                except Exception:
                    pass
            except Exception:
                pass
            try:
                _vinfo = []
                for v in tts.availableVoices()[:8]:
                    try:
                        _vinfo.append(f"{v.name()}@{v.locale().name()}")
                    except Exception:
                        _vinfo.append("?")
                print(f"[TTS] engine={tts.engine()}, voices={len(tts.availableVoices())} {_vinfo}", flush=True)
            except Exception as e:
                print(f"[TTS] engine info failed: {str(e)[:100]}", flush=True)
            try:
                tts.errorOccurred.connect(lambda _err, _msg="": print(f"[TTS] engine error: {_msg or _err}", flush=True))
            except Exception:
                pass
            self._tts_engine = tts
            return tts
        except Exception as e:
            print(f"[TTS] unavailable: {str(e)[:100]}", flush=True)
            return None

    def _detect_speak_lang(self, text: str) -> str:
        # Nhận diện vi/en/fr/es/de từ nội dung text để đọc đúng giọng
        try:
            t = str(text or "").lower()
        except Exception:
            return "en"
        if not t.strip():
            return str(getattr(self, 'language', 'en') or 'en').lower()[:2]
        vi_chars = "âăđêôơưáàảãạéèẻẽẹíìỉĩịóòỏõọúùủũụýỳỷỹỵ"
        if any(c in t for c in vi_chars):
            return "vi"
        if any(c in t for c in "ñ¿¡"):
            return "es"
        if any(c in t for c in "äöüß"):
            return "de"
        try:
            import re as _re_lang
            tokens = set(_re_lang.findall(r"[a-zà-ỹ]+", t))
        except Exception:
            tokens = set(t.split())
        vi_hits = len([w for w in tokens if w in {"xin", "chào", "bạn", "mình", "không", "được", "của", "và", "cho", "với", "này", "câu", "hỏi", "trắc", "nghiệm", "giáo", "học", "bạo", "lực", "đường", "xin", "cảm", "ơn"}])
        if vi_hits >= 2:
            return "vi"
        fr_hits = len([w for w in tokens if w in {"bonjour", "merci", "vous", "avec", "pour", "question", "projet"}])
        es_hits = len([w for w in tokens if w in {"hola", "gracias", "pregunta", "proyecto", "por", "para"}])
        de_hits = len([w for w in tokens if w in {"hallo", "danke", "bitte", "frage", "projekt", "und", "nicht", "mit"}])
        best = max((("fr", fr_hits), ("es", es_hits), ("de", de_hits)), key=lambda x: x[1])
        if best[1] >= 2:
            return best[0]
        if any(c in t for c in "éèêàçôùû") and fr_hits >= 1:
            return "fr"
        return "vi" if vi_hits >= 1 and len(tokens) <= 10 else ("en" if best[1] == 0 else best[0])

    def _get_tts_for_lang(self, lang: str):
        # Đảm bảo engine hiện tại có voice cho lang, nếu không thử engine khác
        try:
            tts = self._get_tts()
            if tts is None:
                return None
            try:
                for v in tts.availableVoices():
                    try:
                        _vl = v.locale().name().lower()
                    except Exception:
                        _vl = ""
                    if lang in _vl or (lang == "vi" and "vie" in _vl):
                        return tts
            except Exception:
                pass
            # Engine hiện tại không có voice → thử engine còn lại
            try:
                from PySide6.QtTextToSpeech import QTextToSpeech
                _cur_eng = ""
                try:
                    _cur_eng = str(tts.engine())
                except Exception:
                    pass
                for _eng in ("winrt", "sapi"):
                    if _eng in _cur_eng:
                        continue
                    try:
                        _cand = QTextToSpeech(_eng, self)
                    except Exception:
                        continue
                    try:
                        for v in _cand.availableVoices():
                            try:
                                _vl = v.locale().name().lower()
                            except Exception:
                                _vl = ""
                            if lang in _vl or (lang == "vi" and "vie" in _vl):
                                print(f"[TTS] switch engine {_cur_eng}->{_eng} for lang={lang}", flush=True)
                                try:
                                    old = getattr(self, "_tts_engine", None)
                                    if old is not None:
                                        try:
                                            old.deleteLater()
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                                try:
                                    _cand.setVolume(1.0)
                                except Exception:
                                    pass
                                self._tts_engine = _cand
                                self._tts_connected = False
                                return _cand
                    except Exception:
                        pass
                    try:
                        _cand.deleteLater()
                    except Exception:
                        pass
            except Exception:
                pass
            return tts
        except Exception:
            return self._get_tts()

    def _toggle_speak(self, text: str, btn=None):
        print("[TTS] button clicked", flush=True)
        try:
            import re as _re_spk
            plain = _re_spk.sub(r"<[^>]+>", " ", str(text or ""))
            # Bỏ emoji để SAPI không câm
            try:
                plain = "".join(c for c in plain if not (0x1F300 <= ord(c) <= 0x1FAFF or 0x2600 <= ord(c) <= 0x27BF or 0xFE00 <= ord(c) <= 0xFE0F))
            except Exception:
                pass
            plain = _re_spk.sub(r"\s+", " ", plain).strip()
        except Exception:
            plain = str(text or "").strip()
        if not plain:
            print("[TTS] empty text, skip", flush=True)
            return
        # Giới hạn độ dài đọc để không kẹt
        if len(plain) > 800:
            plain = plain[:800].rstrip() + "..."
        # Nhận diện ngôn ngữ của chính đoạn text (không dùng ngôn ngữ UI)
        _lang = self._detect_speak_lang(plain)
        print(f"[TTS] speak len={len(plain)} text_lang={_lang} ui_lang={getattr(self, 'language', '?')}", flush=True)
        try:
            tts = self._get_tts_for_lang(_lang)
            if tts is None:
                tts = self._get_tts()
            if tts is None:
                return
            # Chọn voice khớp ngôn ngữ của text; không có thì fallback Google TTS (giọng đúng lang)
            _matched = False
            try:
                try:
                    for v in tts.availableVoices():
                        try:
                            _vl = v.locale().name().lower()
                        except Exception:
                            _vl = ""
                        if _lang in _vl or (_lang == "vi" and "vie" in _vl):
                            try:
                                tts.setVoice(v)
                                _matched = True
                                print(f"[TTS] voice matched: {v.name()}@{_vl}", flush=True)
                                break
                            except Exception:
                                continue
                except Exception:
                    pass
                if not _matched:
                    print(f"[TTS] no native voice for lang={_lang}, Google TTS fallback", flush=True)
                    self._speak_google(plain, _lang, btn)
                    return
            except Exception:
                pass
            # Bấm lại khi đang đọc thì dừng
            try:
                from PySide6.QtTextToSpeech import QTextToSpeech as _QTTS
                _speaking = _QTTS.State.Speaking
                try:
                    _is_speaking = (tts.state() == _speaking)
                except Exception:
                    _is_speaking = False
                if _is_speaking:
                    try:
                        tts.stop()
                    except Exception:
                        pass
                    try:
                        if btn is not None:
                            btn.setText("🔊")
                    except Exception:
                        pass
                    # Nếu đang đọc đúng text này thì chỉ dừng
                    if str(getattr(self, "_tts_last_text", "")) == plain:
                        return
            except Exception:
                pass
            self._tts_last_text = plain
            try:
                if btn is not None:
                    btn.setText("🔇")
                    from PySide6.QtCore import QTimer as _QTimerSpk
                    def _restore_spk():
                        try:
                            btn.setText("🔊")
                        except Exception:
                            pass
                    # Khôi phục icon sau tối đa 30s
                    _QTimerSpk.singleShot(30000, _restore_spk)
            except Exception:
                pass
            tts.say(plain)
            try:
                print(f"[TTS] say called, state={tts.state()}", flush=True)
            except Exception:
                pass
            # Khôi phục icon khi đọc xong (kết nối 1 lần, tránh spam connect)
            try:
                if not getattr(self, "_tts_connected", False):
                    from PySide6.QtTextToSpeech import QTextToSpeech as _QTTS2
                    _spk_state = _QTTS2.State.Speaking
                    def _on_tts_state(_s):
                        try:
                            if _s != _spk_state:
                                for b in list(getattr(self, "_tts_buttons", []) or []):
                                    try:
                                        b.setText("🔊")
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                    tts.stateChanged.connect(_on_tts_state)
                    self._tts_connected = True
                try:
                    _lst = list(getattr(self, "_tts_buttons", []) or [])
                    if btn is not None and btn not in _lst:
                        _lst.append(btn)
                    self._tts_buttons = _lst[-5:]
                except Exception:
                    pass
            except Exception:
                pass
        except Exception as e:
            print(f"[TTS] speak failed: {str(e)[:120]}", flush=True)

    def _stop_google(self):
        try:
            pl = getattr(self, "_google_player", None)
            if pl is not None:
                try:
                    pl.stop()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            self._google_playing = False
        except Exception:
            pass

    def _speak_google(self, text: str, lang: str, btn=None):
        # Chống bấm dồn khi đang tải: bấm lại thì bỏ qua (tránh 4 thread cùng tải)
        try:
            if getattr(self, "_google_loading", False):
                print("[TTS] Google already loading, ignore", flush=True)
                return
            if str(getattr(self, "_google_last_text", "")) == str(text or "") and getattr(self, "_google_playing", False):
                try:
                    self._stop_google()
                except Exception:
                    pass
                try:
                    self._google_playing = False
                    if btn is not None:
                        btn.setText("🔊")
                except Exception:
                    pass
                return
        except Exception:
            pass
        try:
            self._google_loading = True
        except Exception:
            pass
        # Dừng Qt TTS đang đọc (nếu có)
        try:
            tts = getattr(self, "_tts_engine", None)
            if tts is not None:
                try:
                    tts.stop()
                except Exception:
                    pass
        except Exception:
            pass
        print(f"[TTS] Google TTS lang={lang} len={len(text or '')}", flush=True)
        try:
            if btn is not None:
                btn.setText("🔇")
        except Exception:
            pass
        import threading as _th
        def _run_dl():
            try:
                import re as _re
                parts, cur = [], ""
                for sent in _re.split(r"(?<=[.!?…])\s+", str(text or "")):
                    if len(cur) + len(sent) + 1 <= 180:
                        cur = (cur + " " + sent).strip()
                    else:
                        if cur:
                            parts.append(cur)
                        cur = sent
                if cur:
                    parts.append(cur)
                parts = [p for p in parts if p][:6]
                print(f"[TTS] Google parts={len(parts)}", flush=True)
                if not parts:
                    try:
                        self.voice_error_msg.emit("Voice loi: empty")
                    except Exception:
                        pass
                    return
                import requests as _rq
                from pathlib import Path as _Path
                import tempfile as _tf
                files = []
                for i, part in enumerate(parts):
                    try:
                        from urllib.parse import quote as _quote
                        url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl={lang}&client=tw-ob&q={_quote(part)}"
                        print(f"[TTS] Google chunk {i} downloading...", flush=True)
                        r = _rq.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": "https://translate.google.com/"}, timeout=10)
                        print(f"[TTS] Google chunk {i} HTTP {r.status_code} bytes={len(r.content or b'')}", flush=True)
                        if r.status_code != 200 or not r.content:
                            continue
                        fp = _Path(_tf.gettempdir()) / f"eduplay_tts_{i}_{abs(hash(part)) % 100000}.mp3"
                        fp.write_bytes(r.content)
                        files.append(str(fp))
                    except Exception as e_dl:
                        print(f"[TTS] Google chunk {i} fail: {str(e_dl)[:100]}", flush=True)
                        continue
                if not files:
                    try:
                        self.voice_error_msg.emit("Voice loi: Google TTS blocked")
                    except Exception:
                        pass
                    try:
                        if btn is not None:
                            btn.setText("🔊")
                    except Exception:
                        pass
                    return
                self._google_last_text = str(text or "")
                self._google_playing = True
                self._google_files = files
                self._google_idx = 0
                self._google_btn = btn
                try:
                    self.google_play_next.emit()
                except Exception:
                    pass
            except Exception as e:
                print(f"[TTS] Google prep fail: {str(e)[:120]}", flush=True)
                try:
                    self.voice_error_msg.emit(f"Voice loi: {str(e)[:80]}")
                except Exception:
                    pass
            finally:
                try:
                    self._google_loading = False
                except Exception:
                    pass
        _th.Thread(target=_run_dl, daemon=True).start()

    def _play_google_next(self):
        print("[TTS] _play_google_next called", flush=True)
        try:
            files = list(getattr(self, "_google_files", []) or [])
            idx = int(getattr(self, "_google_idx", 0) or 0)
            btn = getattr(self, "_google_btn", None)
            if idx >= len(files):
                try:
                    self._google_playing = False
                    if btn is not None:
                        btn.setText("🔊")
                except Exception:
                    pass
                return
            from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
            from PySide6.QtCore import QUrl
            try:
                old = getattr(self, "_google_player", None)
                if old is not None:
                    try:
                        old.stop()
                    except Exception:
                        pass
            except Exception:
                pass
            player = QMediaPlayer(self)
            audio = QAudioOutput(self)
            try:
                audio.setVolume(1.0)
            except Exception:
                pass
            try:
                player.setAudioOutput(audio)
            except Exception:
                pass
            self._google_player = player
            self._google_audio = audio
            def _on_status(st):
                try:
                    from PySide6.QtMultimedia import QMediaPlayer as _QMP
                    if st == _QMP.MediaStatus.EndOfMedia:
                        self._google_idx = idx + 1
                        self._play_google_next()
                except Exception:
                    pass
            try:
                player.mediaStatusChanged.connect(_on_status)
            except Exception:
                pass
            def _on_err(_e, _s=""):
                print(f"[TTS] Google play err: {_s or _e}", flush=True)
            try:
                player.errorOccurred.connect(_on_err)
            except Exception:
                pass
            player.setSource(QUrl.fromLocalFile(files[idx]))
            player.play()
            print(f"[TTS] playing chunk {idx+1}/{len(files)}", flush=True)
        except Exception as e:
            print(f"[TTS] Google play fail: {str(e)[:120]}", flush=True)
            try:
                self._google_playing = False
            except Exception:
                pass

    def _show_next_suggestions(self, last_topic: str = ""):
        """Gợi ý 3 câu tiếp theo sau khi AI tạo xong"""
        try:
            lang = getattr(self, 'language', 'vi')
            if lang == 'vi':
                base = [
                    f"Tạo thêm 5 câu về {last_topic}" if last_topic else "Tạo thêm 5 câu nữa",
                    "Thêm ảnh cho các câu vừa tạo",
                    "Xuất HTML để xem trước",
                ]
            else:
                base = [
                    f"Create 5 more about {last_topic}" if last_topic else "Create 5 more",
                    "Add images to new questions",
                    "Export HTML to preview",
                ]
            # hiện gợi ý dưới dạng tin AI nhẹ (không spam nếu đã có)
            self.add_message("AI", "Gợi ý tiếp: " + " | ".join([f"\"{x}\"" for x in base]) if lang=='vi' else "Next: " + " | ".join([f"\"{x}\"" for x in base]), "ai")
        except Exception:
            pass
        
    def simulate_ai_response(self, user_message):
        """Simulate AI response based on user message"""
        message_lower = user_message.lower()
        lang = getattr(self, 'language', 'en')
        if lang == 'vi':
            if any(k in message_lower for k in ["câu hỏi", "quiz", "trắc nghiệm"]):
                response = "Mình có thể tạo câu hỏi trắc nghiệm cho bạn! Hãy thử yêu cầu: ví dụ ‘Tạo 5 câu hỏi Toán lớp 6 về phân số’."
            elif "game" in message_lower or "trò chơi" in message_lower:
                response = "Mình giúp thiết kế trò chơi giáo dục! Bạn muốn gợi ý cơ chế trò chơi cho chủ đề của bạn, hay tạo Quiz Classic hoặc Câu Cá?"
            elif any(k in message_lower for k in ["giúp", "hỗ trợ", "assist", "help"]):
                response = "Mình sẵn sàng hỗ trợ! Mình có thể:\n• Tạo câu hỏi theo chủ đề\n• Gợi ý cơ chế/gameplay\n• Định dạng câu hỏi chuẩn\n• Gợi ý nội dung giáo dục\n\nBạn muốn làm việc với phần nào?"
            elif any(k in message_lower for k in ["xin chào", "chào", "hello", "hi"]):
                response = "Xin chào! Bạn muốn mình hỗ trợ gì để tạo game giáo dục hôm nay?"
            else:
                response = "Mình hiểu bạn đang cần trợ giúp. Bạn mô tả rõ hơn loại câu hỏi hoặc trò chơi giáo dục bạn muốn tạo nhé!"
        else:
            if "question" in message_lower or "quiz" in message_lower:
                response = "I can help you create quiz questions! Try asking me to generate questions about a specific topic, like 'Generate 5 questions about photosynthesis'."
            elif "game" in message_lower:
                response = "I can help you design educational games! Would you like me to suggest game mechanics for your topic, or help you create a fishing game or quiz classic?"
            elif "help" in message_lower or "assist" in message_lower:
                response = "I'm here to help! I can:\n• Generate quiz questions on any topic\n• Suggest game mechanics and designs\n• Help with question formatting\n• Provide educational content suggestions\n\nWhat would you like to work on?"
            elif "hello" in message_lower or "hi" in message_lower:
                response = "Hello! How can I assist you with creating educational games today?"
            elif "math" in message_lower or "science" in message_lower or "history" in message_lower:
                response = f"Great! I can help you create educational content about {message_lower.split()[0]}. What specific topic would you like to focus on?"
            else:
                response = "I understand you're looking for help. Could you tell me more about what kind of educational game or questions you'd like to create?"
            
        self.add_message("AI", response, "ai")
        
    def set_ai_response(self, response):
        """Set actual AI response (for real AI integration)"""
        try:
            response = str(response)
        except Exception:
            response = ""
        try:
            _rl = response.lower()
            if ("image" in _rl) and ("support" in _rl or "cannot read" in _rl or "not support" in _rl):
                try:
                    from eduplay.core.i18n import I18n as _I18n
                    response = _I18n.t("ai.error_image_input", getattr(self, "language", "en") or "en")
                except Exception:
                    pass
        except Exception:
            pass
        try:
            self._last_ai_response = response
        except Exception:
            self._last_ai_response = None
        self.add_message("AI", response, "ai")
        
    def toggle_minimize(self):
        """Toggle chat window minimize state"""
        try:
            self.is_minimized = True
        except Exception:
            pass
        try:
            self.hide()
        except Exception:
            pass
            
    def showEvent(self, event):
        """Handle show event"""
        super().showEvent(event)
        try:
            self.is_minimized = False
            if not getattr(self, "_manual_positioned", False):
                from PySide6.QtWidgets import QApplication
                screen = QApplication.primaryScreen().availableGeometry()
                x = screen.right() - self.width() - 20
                y = screen.bottom() - self.height() - 20
                if x < screen.left() + 10:
                    x = screen.left() + 10
                if y < screen.top() + 10:
                    y = screen.top() + 10
                self.move(x, y)
        except Exception:
            pass
        
    def mousePressEvent(self, event):
        """Handle mouse press for dragging"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging"""
        if event.buttons() == Qt.LeftButton:
            try:
                dp = getattr(self, "drag_position", None)
                if dp is None:
                    dp = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                    self.drag_position = dp
                self.move(event.globalPosition().toPoint() - dp)
                event.accept()
            except Exception:
                try:
                    self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                except Exception:
                    pass

"""
Nguyen-Thanh-Tan ¬_¬
"""