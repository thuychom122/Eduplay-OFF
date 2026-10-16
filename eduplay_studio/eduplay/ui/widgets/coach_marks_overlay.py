from PySide6.QtWidgets import QWidget, QFrame, QLabel, QPushButton, QCheckBox, QHBoxLayout
from PySide6.QtCore import Qt, QRect, Signal, QPoint, QTimer, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QPolygonF, QBrush


class CoachMarksOverlay(QWidget):
    finished = Signal(bool)

    def __init__(self, parent: QWidget, marks: list[tuple[QWidget, str]], lang: str = "en", group_size: int = 3):
        super().__init__(parent)
        self._lang = str(lang or "en")
        self._marks = [(w, str(t or "")) for (w, t) in (marks or []) if w is not None]
        self._group_size = max(1, int(group_size or 3))
        self._current_page = 0
        self._total_pages = max(1, (len(self._marks) + self._group_size - 1) // self._group_size) if self._marks else 1
        self._bubbles: list[QFrame] = []
        self._targets: list[QWidget] = []
        self._arrow_dirs: list[str | None] = []
        self._dismiss_check = None
        self._done_btn = None
        self._next_btn = None
        self._fallback_lbl = None
        self._footer = None
        self.setAttribute(Qt.WA_StyledBackground, True)
        # Keep the onboarding as a child overlay of the main window.
        # Using Qt.Tool here creates a separate native window on Windows,
        # which can render the dimmed background as an opaque black layer.
        self.setFocusPolicy(Qt.NoFocus)
        self.setMouseTracking(True)
        self._build_ui()

    def _build_ui(self):
        for w, text in self._marks:
            bubble = QFrame(self)
            bubble.setObjectName("coach-bubble")
            bubble.setAttribute(Qt.WA_StyledBackground, True)
            lbl = QLabel(text, bubble)
            lbl.setWordWrap(True)
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            # Đảm bảo font hỗ trợ tiếng Việt đầy đủ dấu
            try:
                from PySide6.QtGui import QFont
                f = QFont("Segoe UI", 10)
                f.setWeight(QFont.Bold)
                lbl.setFont(f)
            except Exception:
                pass
            lay = QHBoxLayout(bubble)
            lay.setContentsMargins(14, 11, 14, 11)
            lay.addWidget(lbl)
            bubble.setStyleSheet(
                """
                #coach-bubble {
                    background-color: #FFFFFF;
                    border: 1.4px solid rgba(127,86,217,0.92);
                    border-radius: 14px;
                }
                #coach-bubble QLabel {
                    color: #1E293B;
                    font-size: 13.5px;
                    font-weight: 700;
                    line-height: 1.35;
                    font-family: 'Segoe UI', 'Be Vietnam Pro', Arial, sans-serif;
                }
                """
            )
            # Do bong nhe de bubble noi hon tren nen xam mo, dep hon
            try:
                from PySide6.QtWidgets import QGraphicsDropShadowEffect
                shadow = QGraphicsDropShadowEffect(bubble)
                shadow.setBlurRadius(18)
                shadow.setOffset(0, 6)
                shadow.setColor(QColor(15, 23, 42, 38))
                bubble.setGraphicsEffect(shadow)
            except Exception:
                pass
            bubble.hide()
            self._bubbles.append(bubble)
            self._targets.append(w)
            self._arrow_dirs.append(None)

        self._fallback_lbl = QLabel(self)
        self._fallback_lbl.setAlignment(Qt.AlignCenter)
        self._fallback_lbl.setWordWrap(True)
        self._fallback_lbl.setStyleSheet(
            "color:#F8FAFC;font-size:16px;font-weight:600;background:transparent;padding:24px;"
        )
        self._fallback_lbl.hide()

        try:
            from eduplay.core.i18n import I18n

            dismiss_text = I18n.t("onboarding.dismiss", self._lang)
        except Exception:
            dismiss_text = "Đừng hiện lại" if self._lang == "vi" else "Don't show again"
        try:
            from eduplay.core.i18n import I18n

            done_text = I18n.t("onboarding.done", self._lang)
        except Exception:
            done_text = "Xong" if self._lang == "vi" else "Done"

        # Group the Done button + "don't show again" checkbox into a single
        # footer pill so they stay together and never float loose at the
        # extreme screen corner (which previously landed on the taskbar).
        # Yêu cầu hình 2: cho màu trắng
        self._footer = QFrame(self)
        self._footer.setObjectName("coach-footer")
        self._footer.setAttribute(Qt.WA_StyledBackground, True)
        self._footer.setStyleSheet(
            """
            #coach-footer {
                background-color: #FFFFFF;
                border: 1.2px solid rgba(203,213,225,0.95);
                border-radius: 14px;
            }
            #coach-footer QCheckBox { color:#334155; font-weight:700; background:transparent; }
            #coach-footer QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1.2px solid #CBD5E1;
                background-color: #FFFFFF;
            }
            #coach-footer QCheckBox::indicator:checked {
                background-color: #7F56D9;
                border-color: #7F56D9;
            }
            #coach-footer QPushButton {
                background-color: #7F56D9;
                color: #FFFFFF;
                border: none;
                border-radius: 12px;
                padding: 10px 20px;
                font-weight: 800;
                font-size: 14px;
            }
            #coach-footer QPushButton:hover { background-color: #6941C6; }
            """
        )
        # Bóng nhẹ cho pill trắng nổi trên nền xám mờ
        try:
            from PySide6.QtWidgets import QGraphicsDropShadowEffect
            _f_shadow = QGraphicsDropShadowEffect(self._footer)
            _f_shadow.setBlurRadius(16)
            _f_shadow.setOffset(0, 4)
            _f_shadow.setColor(QColor(15, 23, 42, 28))
            self._footer.setGraphicsEffect(_f_shadow)
        except Exception:
            pass
        footer_lay = QHBoxLayout(self._footer)
        footer_lay.setContentsMargins(16, 10, 16, 10)
        footer_lay.setSpacing(12)
        footer_lay.addStretch(1)
        self._dismiss_check = QCheckBox(dismiss_text, self._footer)
        self._dismiss_check.setCursor(Qt.PointingHandCursor)
        footer_lay.addWidget(self._dismiss_check)
        # Nút Tiếp tục / Xong cho phân trang
        try:
            from eduplay.core.i18n import I18n
            next_text = I18n.t("onboarding.next", self._lang)
            if next_text == "onboarding.next":
                next_text = "Tiếp tục" if self._lang == "vi" else "Next"
        except Exception:
            next_text = "Tiếp tục" if self._lang == "vi" else "Next"
        self._next_btn = QPushButton(next_text, self._footer)
        self._next_btn.setObjectName("coach-next-btn")
        self._next_btn.setCursor(Qt.PointingHandCursor)
        self._next_btn.setFocusPolicy(Qt.NoFocus)
        self._next_btn.setStyleSheet(
            """
            QPushButton#coach-next-btn {
                background-color: #7F56D9;
                color: #FFFFFF;
                border: none;
                border-radius: 12px;
                padding: 10px 20px;
                font-weight: 800;
                font-size: 14px;
            }
            QPushButton#coach-next-btn:hover { background-color: #6941C6; }
            """
        )
        self._next_btn.clicked.connect(self._on_next_clicked)
        footer_lay.addWidget(self._next_btn)
        self._done_btn = QPushButton(done_text, self._footer)
        self._done_btn.setObjectName("coach-done-btn")
        self._done_btn.setCursor(Qt.PointingHandCursor)
        self._done_btn.setFocusPolicy(Qt.NoFocus)
        footer_lay.addWidget(self._done_btn)
        self._done_btn.clicked.connect(self._on_done_clicked)
        # Cập nhật hiển thị nút theo trang
        self._update_footer_buttons()

    def _update_footer_buttons(self):
        try:
            is_last = self._current_page >= (self._total_pages - 1)
            if hasattr(self, '_next_btn') and self._next_btn:
                self._next_btn.setVisible(not is_last)
            if hasattr(self, '_done_btn') and self._done_btn:
                # Đổi text thành "Xong" ở trang cuối, "Tiếp tục" sẽ do _next_btn đảm nhận
                # Giữ _done_btn luôn là "Xong" nhưng chỉ hiện ở trang cuối
                self._done_btn.setVisible(is_last)
        except Exception:
            pass

    def _on_next_clicked(self):
        try:
            if self._current_page < self._total_pages - 1:
                self._current_page += 1
                self._update_footer_buttons()
                # Ẩn/hiện bubble theo trang mới
                try:
                    self._reposition()
                    self.update()
                except Exception:
                    pass
                # Đảm bảo focus
                try:
                    self.raise_()
                    self.activateWindow()
                except Exception:
                    pass
                return
            # Nếu đã ở trang cuối mà bấm Tiếp tục (hiếm), coi như Xong
            self._on_done_clicked()
        except Exception:
            try:
                self._on_done_clicked()
            except Exception:
                pass

    def _get_current_page_marks(self):
        """Trả về danh sách (bubble, target, text, arrow_dir) cho trang hiện tại."""
        try:
            start = self._current_page * self._group_size
            end = min(start + self._group_size, len(self._marks))
            indices = list(range(start, end))
            return indices
        except Exception:
            return list(range(len(self._marks)))

    def _on_done_clicked(self):
        try:
            dont_show = bool(self._dismiss_check.isChecked()) if self._dismiss_check else False
        except Exception:
            dont_show = False
        try:
            self.hide()
        except Exception:
            pass
        try:
            self.finished.emit(dont_show)
        except Exception:
            pass
        try:
            self.deleteLater()
        except Exception:
            pass

    def mousePressEvent(self, event):
        try:
            if not event or event.button() != Qt.LeftButton:
                super().mousePressEvent(event)
                return
        except Exception:
            try:
                super().mousePressEvent(event)
            except Exception:
                pass
            return

        try:
            p = event.position().toPoint() if hasattr(event, "position") else event.pos()
        except Exception:
            p = None

        target = None
        if p is not None:
            current_indices = set(self._get_current_page_marks())
            for idx, w in enumerate(self._targets):
                if idx not in current_indices:
                    continue
                r = self._target_rect(w)
                try:
                    if r.contains(p):
                        target = w
                        break
                except Exception:
                    continue

        if target is None:
            try:
                super().mousePressEvent(event)
            except Exception:
                pass
            return

        try:
            dont_show = bool(self._dismiss_check.isChecked()) if self._dismiss_check else False
        except Exception:
            dont_show = False

        click_cb = getattr(target, "click", None)
        try:
            self.hide()
        except Exception:
            pass
        try:
            self.finished.emit(dont_show)
        except Exception:
            pass
        try:
            self.deleteLater()
        except Exception:
            pass

        if callable(click_cb):
            try:
                QTimer.singleShot(0, click_cb)
            except Exception:
                pass

    def showEvent(self, event):
        try:
            self.setGeometry(self.parentWidget().rect())
        except Exception:
            pass
        try:
            self.raise_()
            self.activateWindow()
        except Exception:
            pass
        try:
            self._schedule_reposition()
        except Exception:
            pass
        try:
            # Chỉ hiện bubble của trang hiện tại để tránh đè nhau
            current_indices = set(self._get_current_page_marks())
            visible_count = 0
            for idx, b in enumerate(self._bubbles):
                if idx in current_indices:
                    b.show()
                    b.raise_()
                    visible_count += 1
                else:
                    b.hide()
            if self._fallback_lbl:
                if visible_count == 0:
                    self._fallback_lbl.show()
                    self._fallback_lbl.raise_()
                else:
                    self._fallback_lbl.hide()
            self._update_footer_buttons()
        except Exception:
            pass
        try:
            super().showEvent(event)
        except Exception:
            pass

    def resizeEvent(self, event):
        try:
            self._reposition()
        except Exception:
            pass
        try:
            super().resizeEvent(event)
        except Exception:
            pass
        # Đảm bảo font hỗ trợ tiếng Việt cho bubble sau khi resize
        try:
            for b in self._bubbles:
                for lbl in b.findChildren(QLabel):
                    lbl.setStyleSheet(lbl.styleSheet() + " font-family: 'Segoe UI', 'Be Vietnam Pro', Arial, sans-serif;")
        except Exception:
            pass

    def _target_rect(self, w: QWidget) -> QRect:
        try:
            # Dùng mapToGlobal/mapFromGlobal để khớp hoàn toàn với nút thật, tránh lệch do layout lồng nhau
            # Đặc biệt với nút to trong thẻ, cần lấy geometry chính xác
            g_pos = w.mapToGlobal(QPoint(0, 0))
            g_rect = QRect(g_pos.x(), g_pos.y(), w.width(), w.height())
            # Chuyển về tọa độ overlay (con của main window)
            top_left = self.mapFromGlobal(g_pos)
            return QRect(top_left.x(), top_left.y(), g_rect.width(), g_rect.height())
        except Exception:
            try:
                rect = w.rect()
                top_left = w.mapTo(self, rect.topLeft())
                return QRect(top_left.x(), top_left.y(), rect.width(), rect.height())
            except Exception:
                try:
                    top_left = w.mapTo(self, QPoint(0, 0))
                    return QRect(top_left.x(), top_left.y(), w.width(), w.height())
                except Exception:
                    return QRect(0, 0, 0, 0)

    def _is_edge_strip(self, r: QRect) -> bool:
        """A thin full-height target like the left-edge hover hotzone.

        Such targets are invisible strips; placing a bubble directly beside
        them lands on top of card content, so they need special placement.
        """
        try:
            if r.width() <= 12 and r.height() >= int(self.height() * 0.6):
                return True
        except Exception:
            pass
        return False

    def _is_large_tile(self, r: QRect) -> bool:
        """A big clickable card/tile such as the home action cards.

        For large tiles we want the description bubble clearly outside the
        highlight area, usually centered below or above the card, instead of
        floating over the card itself.
        """
        try:
            if r.width() >= 150 and r.height() >= 150:
                return True
            if r.width() >= int(self.width() * 0.18) and r.height() >= int(self.height() * 0.22):
                return True
        except Exception:
            pass
        return False

    def _schedule_reposition(self):
        """Reposition now and retry a few times so bubbles track targets whose
        geometry settles after the home entrance animation / layout pass."""
        try:
            self._reposition()
        except Exception:
            pass
        try:
            for ms in (60, 220, 600):
                QTimer.singleShot(ms, self._reposition)
        except Exception:
            pass

    def _reposition(self):
        margin = 20
        footer_h = self._footer.height() if getattr(self, "_footer", None) else 0
        footer_reserved = max(80, int(footer_h) + 24)
        base_max_w = int(min(340, max(220, self.width() * 0.26)))
        visible_count = 0
        placed_rects: list[QRect] = []
        small_top_seen = 0
        # Ensure arrow dir list matches targets length
        try:
            if len(self._arrow_dirs) != len(self._targets):
                self._arrow_dirs = [None] * len(self._targets)
        except Exception:
            self._arrow_dirs = [None] * len(self._targets)
        # Chỉ xử lý các bubble thuộc trang hiện tại để tránh đè nhau
        current_indices = set(self._get_current_page_marks())
        for idx, w in enumerate(self._targets):
            bubble = self._bubbles[idx]
            # Ẩn bubble không thuộc trang hiện tại
            if idx not in current_indices:
                bubble.hide()
                try:
                    self._arrow_dirs[idx] = None
                except Exception:
                    pass
                continue
            r = self._target_rect(w)
            if r.width() <= 0 or r.height() <= 0:
                bubble.hide()
                try:
                    self._arrow_dirs[idx] = None
                except Exception:
                    pass
                continue
            visible_count += 1
            # Nút nhỏ trên header (help/settings 44x44) dùng bubble nhỏ hơn để không đè nhau
            is_small_top = False
            try:
                if r.width() <= 60 and r.height() <= 60 and r.top() <= 80:
                    is_small_top = True
            except Exception:
                is_small_top = False
            max_bubble_w = 260 if is_small_top else base_max_w
            bubble.setFixedWidth(max_bubble_w)
            try:
                bubble.adjustSize()
            except Exception:
                pass
            bw = bubble.width()
            bh = bubble.height()

            if self._is_edge_strip(r):
                # Thanh bên: đặt bubble ở giữa cạnh trái, không đè nút Tạo mới
                # Yêu cầu: chỉ bo góc bên phải, bên trái để thẳng sát mép
                try:
                    bubble.setStyleSheet(
                        """
                        #coach-bubble {
                            background-color: #FFFFFF;
                            border: 1.4px solid rgba(127,86,217,0.92);
                            border-top-left-radius: 0px;
                            border-bottom-left-radius: 0px;
                            border-top-right-radius: 14px;
                            border-bottom-right-radius: 14px;
                        }
                        #coach-bubble QLabel {
                            color: #1E293B;
                            font-size: 13.5px;
                            font-weight: 700;
                            line-height: 1.35;
                        }
                        """
                    )
                except Exception:
                    pass
                # Giữ bubble ở góc dưới-trái, gần mép nhưng phía trên footer, tránh đè lên thẻ
                x = max(margin, r.right() + margin)
                y = max(margin, self.height() - footer_reserved - bh - margin)
                # Tránh đè lên bubble trước
                for pr in placed_rects:
                    if QRect(x, y, bw, bh).intersects(pr):
                        y = pr.top() - bh - margin
                        y = max(margin, y)
                bubble.move(int(x), int(y))
                try:
                    bubble.show()
                    bubble.raise_()
                except Exception:
                    pass
                placed_rects.append(QRect(int(x), int(y), bw, bh))
                try:
                    self._arrow_dirs[idx] = "left"
                except Exception:
                    pass
                continue

            if self._is_large_tile(r):
                center_x = int(r.center().x() - bw / 2)
                x = max(margin, min(self.width() - bw - margin, center_x))
                below_y = r.bottom() + margin
                above_y = r.top() - margin - bh
                chosen_dir = None
                # Ưu tiên đặt phía trên thẻ cho đẹp như screenshot, tránh đè footer
                if above_y >= margin and above_y + bh <= self.height() - footer_reserved:
                    # Nếu cả trên và dưới đều vừa, ưu tiên trên để bubble không đè footer và gần tiêu đề hơn
                    # Kiểm tra xem trên có đủ chỗ và không quá sát mép trên
                    if above_y >= 80 or not (below_y + bh <= self.height() - footer_reserved):
                        y = above_y
                        chosen_dir = "bottom"
                    elif below_y + bh <= self.height() - footer_reserved:
                        y = below_y
                        chosen_dir = "top"
                    else:
                        y = above_y
                        chosen_dir = "bottom"
                elif above_y >= margin:
                    y = above_y
                    chosen_dir = "bottom"
                elif below_y + bh <= self.height() - footer_reserved:
                    y = below_y
                    chosen_dir = "top"
                else:
                    y = max(margin, min(self.height() - footer_reserved - bh, int((self.height() - footer_reserved - bh) / 2)))
                    # Fallback: decide by vertical relation
                    if y + bh < r.top():
                        chosen_dir = "bottom"
                    elif y > r.bottom():
                        chosen_dir = "top"
                    else:
                        chosen_dir = "top"
                # Tránh đè lên bubble trước (dù hiếm cho thẻ lớn)
                for pr in placed_rects:
                    if QRect(int(x), int(y), bw, bh).intersects(pr):
                        y = pr.bottom() + 8
                        y = min(y, self.height() - footer_reserved - bh - margin)
                        break
                bubble.move(int(x), int(y))
                try:
                    bubble.show()
                    bubble.raise_()
                except Exception:
                    pass
                placed_rects.append(QRect(int(x), int(y), bw, bh))
                # Re-evaluate dir if y shifted across threshold
                try:
                    brect = QRect(int(x), int(y), bw, bh)
                    if brect.top() > r.bottom():
                        chosen_dir = "top"
                    elif brect.bottom() < r.top():
                        chosen_dir = "bottom"
                    self._arrow_dirs[idx] = chosen_dir
                except Exception:
                    try:
                        self._arrow_dirs[idx] = chosen_dir
                    except Exception:
                        pass
                continue

            # Nút nhỏ trên header: Trợ giúp (?) -> sang trái, Cài đặt (gear) -> ở dưới
            if is_small_top:
                small_margin = 12
                # Tự động co width theo độ dài chữ để mũi tên đẹp hơn
                try:
                    _txt = ""
                    try:
                        _txt = str(self._marks[idx][1] or "")
                    except Exception:
                        _txt = ""
                    if _txt:
                        try:
                            fm = bubble.fontMetrics()
                        except Exception:
                            fm = None
                        if fm is not None:
                            tw = int(fm.horizontalAdvance(_txt)) + 36
                            ideal = max(210, min(300, tw))
                            if ideal < bw:
                                bubble.setFixedWidth(ideal)
                                try:
                                    bubble.adjustSize()
                                except Exception:
                                    pass
                                bw = bubble.width()
                                bh = bubble.height()
                except Exception:
                    pass
                # Phân biệt ? (Trợ giúp) -> sang trái, Cài đặt -> ở dưới
                # Dùng thứ tự: small_top đầu tiên là ? , thứ 2 là cài đặt (theo marks của MainWindow)
                # Kết hợp text để robust khi chỉ có 1 bubble
                is_help = False
                try:
                    _t = str(self._marks[idx][1] or "").lower()
                    if "trợ giúp" in _t or "tro giup" in _t or "help" in _t or "?" in _t:
                        is_help = True
                    # Fallback theo thứ tự: bubble small_top đầu tiên luôn là help
                    if small_top_seen == 0:
                        is_help = True
                    elif small_top_seen == 1:
                        is_help = False
                except Exception:
                    is_help = (small_top_seen == 0)
                if is_help and small_top_seen == 0:
                    # Trợ giúp: đặt sang TRÁI của nút ? , mũi tên phải chỉ vào ?
                    x_left = r.left() - margin - bw
                    # Nếu không đủ chỗ bên trái (màn hình nhỏ) thì fallback sang dưới
                    if x_left >= small_margin:
                        x = x_left
                        y = max(small_margin, min(self.height() - footer_reserved - bh - margin, int(r.center().y() - bh / 2)))
                        # Tránh đè lên bubble trước
                        for pr in placed_rects:
                            if QRect(int(x), int(y), bw, bh).intersects(pr):
                                y = pr.bottom() + 10
                                y = min(y, self.height() - footer_reserved - bh - margin)
                                break
                        bubble.move(int(x), int(y))
                        try:
                            bubble.show()
                            bubble.raise_()
                        except Exception:
                            pass
                        placed_rects.append(QRect(int(x), int(y), bw, bh))
                        try:
                            self._arrow_dirs[idx] = "right"
                        except Exception:
                            pass
                        small_top_seen += 1
                        continue
                    # fallback: nếu không đủ chỗ trái thì đặt dưới như cũ
                # Cài đặt (hoặc help fallback): đặt DƯỚI nút, mũi tên trên chỉ lên
                center_x = int(r.center().x() - bw / 2)
                below_y = r.bottom() + 14
                x = max(small_margin, min(self.width() - bw - small_margin, center_x))
                y = below_y
                for pr in placed_rects:
                    if QRect(int(x), int(y), bw, bh).intersects(pr):
                        y = pr.bottom() + 10
                        y = min(y, self.height() - footer_reserved - bh - margin)
                        break
                bubble.move(int(x), int(y))
                try:
                    bubble.show()
                    bubble.raise_()
                except Exception:
                    pass
                placed_rects.append(QRect(int(x), int(y), bw, bh))
                try:
                    self._arrow_dirs[idx] = "top"
                except Exception:
                    pass
                small_top_seen += 1
                continue

            # Header band: các nút trên dải header (y ≤ 110) luôn ưu tiên đặt DƯỚI
            # để bubble không đè tiêu đề/che phủ các bubble khác và mũi tên chỉ lên (đúng vị trí)
            try:
                _header_band = bool(r.top() <= 110 and not self._is_large_tile(r) and not self._is_edge_strip(r))
            except Exception:
                _header_band = False
            if _header_band:
                try:
                    center_x = int(r.center().x() - bw / 2)
                    x = max(margin, min(self.width() - bw - margin, center_x))
                    below_y = r.bottom() + 14
                    above_y = r.top() - margin - bh
                    fits_below = (below_y + bh) <= (self.height() - footer_reserved)
                    fits_above = above_y >= margin
                    if fits_below:
                        y = below_y
                        chosen_header_dir = "top"
                    elif fits_above:
                        y = above_y
                        chosen_header_dir = "bottom"
                    else:
                        # Không đủ chỗ dọc -> fallback sang logic generic phía dưới
                        _header_band = False
                    if _header_band:
                        # Tránh đè lên bubble trước (khi group_size >1) -> dời xuống
                        for pr in placed_rects:
                            if QRect(int(x), int(y), bw, bh).intersects(pr):
                                y = pr.bottom() + 10
                                y = min(y, self.height() - footer_reserved - bh - margin)
                                y = max(margin, y)
                                # Nếu vẫn đè sau khi dời, tiếp tục kiểm tra với các bubble còn lại
                                # (đơn giản: chỉ dời 1 lần vì với group_size=1 sẽ không có pr)
                        bubble.move(int(x), int(y))
                        try:
                            bubble.show()
                            bubble.raise_()
                        except Exception:
                            pass
                        placed_rects.append(QRect(int(x), int(y), bw, bh))
                        try:
                            # Nếu dời xuống quá xa mà vượt qua ngưỡng, cập nhật hướng
                            if y > r.bottom():
                                chosen_header_dir = "top"
                            elif y + bh < r.top():
                                chosen_header_dir = "bottom"
                            self._arrow_dirs[idx] = chosen_header_dir
                        except Exception:
                            try:
                                self._arrow_dirs[idx] = chosen_header_dir
                            except Exception:
                                pass
                        continue
                except Exception:
                    pass

            # Nút FAB/chat ở góc dưới phải (Edubot) -> luôn đặt phía trên, mũi tên chỉ xuống
            try:
                is_fab_candidate = False
                if r.width() <= 72 and r.height() <= 72 and r.width() > 0 and r.height() > 0:
                    if r.bottom() >= int(self.height() * 0.65) and r.right() >= int(self.width() * 0.65):
                        is_fab_candidate = True
                if is_fab_candidate:
                    center_x_fab = int(r.center().x() - bw / 2)
                    # Clamp để bubble không tràn ra ngoài màn hình
                    x = max(margin, min(self.width() - bw - margin, center_x_fab))
                    # Hơi lệch sang trái một chút để không đè mép phải
                    if x + bw > self.width() - margin:
                        x = self.width() - bw - margin
                    y_above = r.top() - margin - bh
                    y_below = r.bottom() + margin
                    # Ưu tiên đặt trên nếu đủ chỗ, ngược lại đặt bên trái
                    if y_above >= margin and (y_above + bh) <= (self.height() - footer_reserved):
                        y = y_above
                        chosen_dir_fab = "bottom"
                    elif y_below + bh <= (self.height() - footer_reserved):
                        y = y_below
                        chosen_dir_fab = "top"
                    else:
                        # Fallback: đặt bên trái, mũi tên phải
                        x_left = r.left() - margin - bw
                        if margin <= x_left and (x_left + bw) <= (self.width() - margin):
                            x = x_left
                            y = max(margin, min(self.height() - footer_reserved - bh - margin, int(r.center().y() - bh / 2)))
                            chosen_dir_fab = "right"
                        else:
                            y = max(margin, y_above)
                            chosen_dir_fab = "bottom"
                    # Tránh đè lên bubble trước: thử chuyển sang bên trái trước khi đẩy lên
                    for pr in placed_rects:
                        if QRect(int(x), int(y), bw, bh).intersects(pr):
                            x_left = r.left() - margin - bw
                            y_centered = int(r.center().y() - bh / 2)
                            y_centered = max(margin, min(self.height() - footer_reserved - bh - margin, y_centered))
                            # Thử đặt sang trái, mũi tên phải chỉ vào nút chat
                            if margin <= x_left and (x_left + bw) <= (self.width() - margin):
                                test_rect = QRect(int(x_left), int(y_centered), bw, bh)
                                overlap_left = False
                                for pr2 in placed_rects:
                                    if test_rect.intersects(pr2):
                                        overlap_left = True
                                        break
                                if not overlap_left:
                                    x = x_left
                                    y = y_centered
                                    chosen_dir_fab = "right"
                                    break
                            # Nếu trái không được, thử dịch trái nhẹ
                            alt_x = max(margin, x - 24)
                            if not QRect(int(alt_x), int(y), bw, bh).intersects(pr):
                                x = alt_x
                            else:
                                y = pr.top() - bh - 10
                                y = max(margin, min(self.height() - footer_reserved - bh - margin, y))
                            break
                    bubble.move(int(x), int(y))
                    try:
                        bubble.show()
                        bubble.raise_()
                    except Exception:
                        pass
                    placed_rects.append(QRect(int(x), int(y), bw, bh))
                    try:
                        self._arrow_dirs[idx] = chosen_dir_fab
                    except Exception:
                        pass
                    continue
            except Exception:
                pass

            center_x = int(r.center().x() - bw / 2)
            center_y = int(r.center().y() - bh / 2)
            right_pos = (r.right() + margin, center_y)
            left_pos = (r.left() - margin - bw, center_y)
            above_pos = (center_x, r.top() - margin - bh)
            below_pos = (center_x, r.bottom() + margin)

            if r.bottom() >= (self.height() - footer_reserved - 40):
                candidates = (above_pos, right_pos, left_pos, below_pos)
                cands_dir = ("bottom", "left", "right", "top")
            elif r.left() <= int(self.width() * 0.12):
                candidates = (right_pos, below_pos, above_pos, left_pos)
                cands_dir = ("left", "top", "bottom", "right")
            elif r.right() >= int(self.width() * 0.88):
                candidates = (left_pos, below_pos, above_pos, right_pos)
                cands_dir = ("right", "top", "bottom", "left")
            else:
                candidates = (above_pos, right_pos, left_pos, below_pos)
                cands_dir = ("bottom", "left", "right", "top")

            x = margin
            y = margin
            placed = False
            chosen_dir = cands_dir[0] if cands_dir else "top"
            for c_i, (cand_x, cand_y) in enumerate(candidates):
                fits_h = margin <= cand_x and (cand_x + bw) <= (self.width() - margin)
                fits_v = margin <= cand_y and (cand_y + bh) <= (self.height() - footer_reserved)
                if fits_h and fits_v:
                    # Kiểm tra đè lên bubble đã đặt
                    overlap = False
                    for pr in placed_rects:
                        if QRect(int(cand_x), int(cand_y), bw, bh).intersects(pr):
                            overlap = True
                            break
                    if not overlap:
                        x, y = cand_x, cand_y
                        try:
                            chosen_dir = cands_dir[c_i]
                        except Exception:
                            chosen_dir = "top"
                        placed = True
                        break
            if not placed:
                x = max(margin, min(self.width() - bw - margin, candidates[0][0]))
                y = max(margin, min(self.height() - footer_reserved - bh, candidates[0][1]))
                try:
                    chosen_dir = cands_dir[0]
                except Exception:
                    chosen_dir = "top"
                # Vẫn kiểm tra đè, nếu đè thì dịch xuống
                for pr in placed_rects:
                    if QRect(int(x), int(y), bw, bh).intersects(pr):
                        y = pr.bottom() + 8
                        y = min(y, self.height() - footer_reserved - bh - margin)
                        break
            bubble.move(int(x), int(y))
            try:
                bubble.show()
                bubble.raise_()
            except Exception:
                pass
            placed_rects.append(QRect(int(x), int(y), bw, bh))
            try:
                # After final y shift, verify direction still points to target
                # If shifted vertically a lot, keep original but if now clearly above/below adjust
                final_rect = QRect(int(x), int(y), bw, bh)
                if final_rect.bottom() < r.top() and chosen_dir not in ("bottom",):
                    # Bubble ended above target
                    chosen_dir = "bottom"
                elif final_rect.top() > r.bottom() and chosen_dir not in ("top",):
                    # Bubble below target
                    if r.width() > 60 or r.height() > 60:
                        chosen_dir = "top"
                self._arrow_dirs[idx] = chosen_dir
            except Exception:
                try:
                    self._arrow_dirs[idx] = chosen_dir
                except Exception:
                    pass

        if self._fallback_lbl:
            try:
                if visible_count == 0:
                    self._fallback_lbl.show()
                    self._fallback_lbl.raise_()
                    fw = max(200, int(self.width() * 0.5))
                    fh = max(80, int(self.height() * 0.22))
                    fx = int((self.width() - fw) / 2)
                    fy = int((self.height() - fh) / 2 - footer_reserved / 2)
                    if fy < margin:
                        fy = margin
                    self._fallback_lbl.setGeometry(fx, fy, fw, fh)
                    self._fallback_lbl.setText(
                        "👋\\n" + (self._marks[0][1] if self._marks else "Welcome!")
                    )
                else:
                    self._fallback_lbl.hide()
            except Exception:
                pass

        if getattr(self, "_footer", None):
            try:
                self._footer.adjustSize()
                fw = self._footer.width()
                fh = self._footer.height()
                fx = int((self.width() - fw) / 2)
                fy = self.height() - fh - margin
                if fy < margin:
                    fy = margin
                self._footer.move(fx, fy)
                self._footer.show()
                self._footer.raise_()
            except Exception:
                pass
        try:
            self.update()
        except Exception:
            pass

    def paintEvent(self, event):
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing, True)
            # Xám làm trong suốt thay vì đen (theo yêu cầu) - 110/255 ~43% trong suốt
            p.fillRect(self.rect(), QColor(128, 128, 128, 110))
            pen = QPen(QColor("#7F56D9"))
            pen.setWidth(2)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            current_indices = set(self._get_current_page_marks())
            for idx, w in enumerate(self._targets):
                if idx not in current_indices:
                    continue
                r = self._target_rect(w)
                if r.width() <= 0 or r.height() <= 0:
                    continue
                # Với thanh bên (edge strip 6px): chỉ bo góc phải, trái để thẳng sát mép
                if self._is_edge_strip(r):
                    # Vẽ highlight cho mép trái: chỉ bo phải
                    try:
                        from PySide6.QtGui import QPainterPath
                        path = QPainterPath()
                        # Tạo rect chỉ bo phải: dùng QPainterPath với 2 góc phải bo
                        # Vẽ thủ công: rect với top-left và bottom-left vuông, top-right/bottom-right bo
                        radius = 10
                        # Bắt đầu từ top-left (vuông)
                        path.moveTo(r.left(), r.top())
                        path.lineTo(r.right() - radius, r.top())
                        path.arcTo(r.right() - 2*radius, r.top(), 2*radius, 2*radius, 90, -90)
                        path.lineTo(r.right(), r.bottom() - radius)
                        path.arcTo(r.right() - 2*radius, r.bottom() - 2*radius, 2*radius, 2*radius, 0, -90)
                        path.lineTo(r.left(), r.bottom())
                        path.lineTo(r.left(), r.top())
                        p.drawPath(path)
                    except Exception:
                        # Fallback: vẽ rect thường nếu path lỗi
                        p.drawRoundedRect(r, 16, 16)
                    continue
                # Nguyên cái nút to luôn - viền phải khớp hoàn toàn với nút thật, không inset
                # Nút #card-button có border-radius 12px, dùng pen 2px vẽ trực tiếp trên rect
                try:
                    is_btn = False
                    try:
                        is_btn = w.objectName() == "card-button"
                    except Exception:
                        is_btn = False
                    if not is_btn:
                        try:
                            is_btn = bool(w.property("primary") or w.property("success") or w.property("warning"))
                        except Exception:
                            is_btn = False
                    radius = 12 if is_btn else 16
                except Exception:
                    radius = 12
                # Vẽ khớp hoàn toàn, không lệch 1px
                p.drawRoundedRect(r, radius, radius)
            # --- Mũi tên chỉ từ bubble tới target ---
            try:
                # Vẽ tam giác nhỏ gắn trên viền bubble, hướng đúng tới vùng được hướng dẫn
                # Làm mũi tên to hơn, bo hơn và viền đậm hơn cho đẹp
                arrow_pen = QPen(QColor(127, 86, 217, 235))
                arrow_pen.setWidth(1.2)
                arrow_pen.setJoinStyle(Qt.RoundJoin)
                arrow_pen.setCapStyle(Qt.RoundCap)
                p.setPen(arrow_pen)
                p.setBrush(QBrush(QColor("#FFFFFF")))
                arrow_half_base = 10
                arrow_h = 11
                current_indices = set(self._get_current_page_marks())
                for idx, w in enumerate(self._targets):
                    if idx not in current_indices:
                        continue
                    try:
                        dir_name = None
                        try:
                            dir_name = self._arrow_dirs[idx] if idx < len(self._arrow_dirs) else None
                        except Exception:
                            dir_name = None
                        if not dir_name:
                            continue
                        bubble = self._bubbles[idx] if idx < len(self._bubbles) else None
                        if bubble is None or not bubble.isVisible():
                            continue
                        brect = bubble.geometry()
                        if brect.width() <= 0 or brect.height() <= 0:
                            continue
                        r = self._target_rect(w)
                        if r.width() <= 0 or r.height() <= 0:
                            continue
                        poly = QPolygonF()
                        # Margin trong để mũi tên không chạm bo góc 14px (cần >=14)
                        arrow_margin = 16
                        if dir_name == "top":
                            # Bubble nằm dưới target -> mũi tên trên đỉnh bubble chỉ lên
                            cx = int(r.center().x())
                            min_cx = brect.x() + arrow_margin
                            max_cx = brect.x() + brect.width() - arrow_margin
                            if max_cx >= min_cx:
                                cx = max(min_cx, min(max_cx, cx))
                            else:
                                cx = brect.center().x()
                            y_edge = brect.y()
                            poly.append(QPointF(float(cx), float(y_edge - arrow_h)))
                            poly.append(QPointF(float(cx - arrow_half_base), float(y_edge + 0.6)))
                            poly.append(QPointF(float(cx + arrow_half_base), float(y_edge + 0.6)))
                        elif dir_name == "bottom":
                            cx = int(r.center().x())
                            min_cx = brect.x() + arrow_margin
                            max_cx = brect.x() + brect.width() - arrow_margin
                            if max_cx >= min_cx:
                                cx = max(min_cx, min(max_cx, cx))
                            else:
                                cx = brect.center().x()
                            y_edge = brect.y() + brect.height()
                            poly.append(QPointF(float(cx), float(y_edge + arrow_h)))
                            poly.append(QPointF(float(cx + arrow_half_base), float(y_edge - 0.6)))
                            poly.append(QPointF(float(cx - arrow_half_base), float(y_edge - 0.6)))
                        elif dir_name == "left":
                            cy = int(r.center().y())
                            min_cy = brect.y() + arrow_margin
                            max_cy = brect.y() + brect.height() - arrow_margin
                            if max_cy >= min_cy:
                                cy = max(min_cy, min(max_cy, cy))
                            else:
                                cy = brect.center().y()
                            x_edge = brect.x()
                            poly.append(QPointF(float(x_edge - arrow_h), float(cy)))
                            poly.append(QPointF(float(x_edge + 0.6), float(cy - arrow_half_base)))
                            poly.append(QPointF(float(x_edge + 0.6), float(cy + arrow_half_base)))
                        elif dir_name == "right":
                            cy = int(r.center().y())
                            min_cy = brect.y() + arrow_margin
                            max_cy = brect.y() + brect.height() - arrow_margin
                            if max_cy >= min_cy:
                                cy = max(min_cy, min(max_cy, cy))
                            else:
                                cy = brect.center().y()
                            x_edge = brect.x() + brect.width()
                            poly.append(QPointF(float(x_edge + arrow_h), float(cy)))
                            poly.append(QPointF(float(x_edge - 0.6), float(cy + arrow_half_base)))
                            poly.append(QPointF(float(x_edge - 0.6), float(cy - arrow_half_base)))
                        else:
                            continue
                        # Chỉ vẽ khi tam giác nằm trong overlay (tránh tràn ra ngoài khi target sát biên)
                        p.drawPolygon(poly)
                    except Exception:
                        continue
            except Exception:
                pass
            p.end()
        except Exception:
            pass
