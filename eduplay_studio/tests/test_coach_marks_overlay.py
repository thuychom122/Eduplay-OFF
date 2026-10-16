import os
import sys
import unittest

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QWidget


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestCoachMarksOverlay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.app = QApplication.instance() or QApplication([])

    def test_overlay_stays_embedded_in_parent_window(self):
        from eduplay.ui.widgets.coach_marks_overlay import CoachMarksOverlay

        parent = QWidget()
        parent.resize(800, 600)
        target = QLabel("Create", parent)
        target.setGeometry(100, 120, 160, 48)
        target.show()

        overlay = CoachMarksOverlay(parent, [(target, "Create a new project")], lang="en")

        self.assertIs(overlay.parentWidget(), parent)
        self.assertFalse(bool(overlay.windowFlags() & Qt.Tool))

    def test_done_button_emits_finished_once(self):
        from eduplay.ui.widgets.coach_marks_overlay import CoachMarksOverlay

        parent = QWidget()
        parent.resize(800, 600)
        target = QLabel("Create", parent)
        target.setGeometry(100, 120, 160, 48)
        target.show()

        overlay = CoachMarksOverlay(parent, [(target, "Create a new project")], lang="en")
        received = []
        overlay.finished.connect(received.append)

        overlay._on_done_clicked()

        self.assertEqual(received, [False])

    def test_footer_groups_done_and_dismiss(self):
        from eduplay.ui.widgets.coach_marks_overlay import CoachMarksOverlay

        parent = QWidget()
        parent.resize(800, 600)
        target = QLabel("Create", parent)
        target.setGeometry(100, 120, 160, 48)
        target.show()

        overlay = CoachMarksOverlay(parent, [(target, "Create a new project")], lang="en")

        # Done + "don't show again" must live together in a footer pill so
        # they no longer float loose at the extreme screen corner.
        self.assertIsNotNone(getattr(overlay, "_footer", None))
        self.assertIs(overlay._done_btn.parentWidget(), overlay._footer)
        self.assertIs(overlay._dismiss_check.parentWidget(), overlay._footer)

    def test_left_edge_hotzone_bubble_kept_off_card_center(self):
        from eduplay.ui.widgets.coach_marks_overlay import CoachMarksOverlay

        parent = QWidget()
        parent.resize(1280, 800)
        # Thin full-height left-edge strip (like LeftEdgeHotZone).
        hotzone = QWidget(parent)
        hotzone.setGeometry(0, 0, 6, 800)
        hotzone.show()

        overlay = CoachMarksOverlay(parent, [(hotzone, "Preview: hover the left edge")], lang="en")
        overlay.setGeometry(parent.rect())
        overlay._reposition()
        bubble = overlay._bubbles[0]

        # The edge-strip bubble must be pushed to the lower area (not vertically
        # centered over the leftmost card) and stay within the window bounds.
        self.assertGreater(bubble.y(), parent.height() // 2)
        self.assertGreaterEqual(bubble.x(), 20)
        self.assertLessEqual(bubble.x() + bubble.width(), parent.width() - 20)

    def test_large_card_bubble_placed_below_card(self):
        from eduplay.ui.widgets.coach_marks_overlay import CoachMarksOverlay

        parent = QWidget()
        parent.resize(1280, 800)
        # Big home-card-like target.
        card = QWidget(parent)
        card.setGeometry(200, 150, 400, 260)
        card.show()

        overlay = CoachMarksOverlay(parent, [(card, "Create: start a new learning project")], lang="en")
        overlay.setGeometry(parent.rect())
        overlay._reposition()
        bubble = overlay._bubbles[0]

        # The bubble should sit either below or above the card (ưu tiên trên cho đẹp), not overlap, and be centered.
        is_below = bubble.y() >= card.geometry().bottom() + 10
        is_above = bubble.y() + bubble.height() <= card.geometry().top() - 10
        self.assertTrue(is_below or is_above, "bubble is not clearly above or below card")
        if is_below:
            self.assertEqual(overlay._arrow_dirs[0], "top")
        else:
            self.assertEqual(overlay._arrow_dirs[0], "bottom")
        self.assertLessEqual(bubble.y() + bubble.height(), parent.height() - 80)
        self.assertGreaterEqual(bubble.y(), 10)
        bubble_center_x = bubble.x() + bubble.width() // 2
        card_center_x = card.geometry().center().x()
        self.assertLess(abs(bubble_center_x - card_center_x), 60)

    def test_three_home_card_bubbles_are_separate_and_below_cards(self):
        from eduplay.ui.widgets.coach_marks_overlay import CoachMarksOverlay

        parent = QWidget()
        parent.resize(1600, 900)
        cards = []
        for i in range(3):
            card = QWidget(parent)
            card.setGeometry(120 + i * 460, 200, 400, 260)
            card.show()
            cards.append(card)

        overlay = CoachMarksOverlay(parent, [(c, f"Step {i}") for i, c in enumerate(cards)], lang="en")
        overlay.setGeometry(parent.rect())
        overlay._reposition()

        for i, (card, bubble) in enumerate(zip(cards, overlay._bubbles)):
            is_below = bubble.y() >= card.geometry().bottom() + 10
            is_above = bubble.y() + bubble.height() <= card.geometry().top() - 10
            self.assertTrue(is_below or is_above, f"card {i} bubble is not above or below card")
            # Arrow hướng đúng: dưới -> top, trên -> bottom
            expected_dir = "top" if is_below else "bottom"
            self.assertEqual(overlay._arrow_dirs[i], expected_dir, f"card {i} arrow dir wrong")
            self.assertLessEqual(
                bubble.y() + bubble.height(), parent.height() - 80, f"card {i} bubble hits footer area"
            )
            self.assertGreaterEqual(bubble.y(), 10, f"card {i} bubble too high")
            bubble_center_x = bubble.x() + bubble.width() // 2
            card_center_x = card.geometry().center().x()
            self.assertLess(
                abs(bubble_center_x - card_center_x), 60, f"card {i} bubble is not centered"
            )

        # Bubbles should not overlap each other horizontally.
        rects = [b.geometry() for b in overlay._bubbles]
        for i in range(len(rects) - 1):
            self.assertFalse(
                rects[i].intersects(rects[i + 1]),
                f"bubbles {i} and {i + 1} overlap",
            )


if __name__ == "__main__":
    unittest.main()
