"""
Edubot Knowledge Base - Trực tiếp bổ sung vào Agent
Được đọc trực tiếp mỗi khi tạo system prompt. Dùng TỪ PHỔ THÔNG, không VSTO/MSI/COM.
Cập nhật: 2026-08-30 - Đã đọc code VSTO/COM, kiểm chứng Insert -> HTML Frame
"""

KNOWLEDGE_VI = r"""
=== EDUPLAY STUDIO - TẤT CẢ TÍNH NĂNG (DỄ HIỂU) ===
App máy tính, không cần mạng (chỉ Edubot cần mạng). Dự án lưu ở Tài liệu/EduPlay.

1. TRANG CHỦ (vừa mở app):
- 3 nút lớn giữa màn hình: TẠO MỚI (tạo bài mới) → điền tên, mô tả, chọn kiểu Trắc nghiệm/Triệu phú/Bắt cá/Phiêu lưu → bấm Tạo và chỉnh sửa
- CHỈNH SỬA (mở bài cũ): bấm Duyệt dự án → tìm → Mở
- CHƠI: chơi thử bài đang mở, toàn màn hình
- Rê chuột sát mép trái cùng để hiện menu bên trái (Trang chủ, Dự án, Xem trước, các nút nhanh)
- Góc phải trên: nút Trợ giúp (?) và Cài đặt (bánh răng). Góc phải dưới: nút tròn tím 💬 để mở trò chuyện

2. DUYỆT DỰ ÁN (bấm CHỈNH SỬA ở Trang chủ):
- Ô tìm kiếm trên cùng, bộ lọc: Tất cả/Trắc nghiệm/Triệu phú/Bắt cá/Phiêu lưu, lọc theo thẻ
- Mỗi thẻ dự án có: Mở, Sao chép (tạo bản copy), Xóa (hỏi lại), Đổi tên, Chỉnh thẻ, ngày tạo
- Nút Làm mới, Nhập dự án từ file .eduplay

3. SOẠN CÂU HỎI (màn hình chính sau khi Tạo/Mở):
- Trên cùng: Lưu dự án (xanh lá) | Xem trước (xanh dương) | Xuất lên web (xanh dương) | Xuất nội bộ HTML (cam) | nút Trợ giúp/Cài đặt
- Bên trái có 4 thẻ:
  + Câu hỏi: danh sách câu hỏi bên trái. Nút + Thêm câu hỏi (xanh lá), Nhập khẩu (tím), Xóa đã chọn, Xem đã chọn, ô Tìm. Bấm vào câu hỏi để sửa ở giữa.
  + Thư viện: kho ảnh, âm thanh, hoạt hình có sẵn để kéo vào câu hỏi
  + Cấu hình Game: trộn câu hỏi (bật/tắt), thời gian mỗi câu (5-300 giây), điểm mỗi câu đúng, hiện giải thích sau khi trả lời, chế độ thi (1 lần / cho làm lại), nhạc nền (có sẵn hoặc chọn file nhạc của bạn)
  + Cài đặt: cỡ chữ, hiện số dòng, tự hoàn thành
- Ở giữa: chọn kiểu câu hỏi → điền câu hỏi → điền đáp án → chọn đáp án đúng → thêm giải thích (không bắt buộc) → bấm Chọn hình ảnh / Chọn âm thanh nếu muốn → bấm Lưu câu hỏi. Có nút Nhân bản để copy câu hỏi.
- Bên phải: khung Xem trước trực tiếp, bấm Làm mới để cập nhật
- Các kiểu câu hỏi: chọn đáp án (4 lựa chọn), đúng/sai, điền chỗ trống (gõ ___), nối cặp (trái=phải), trả lời ngắn

4. XEM TRƯỚC & CHƠI:
- Trong màn hình soạn: bấm Xem trước (xanh) để thử ngay trong app. Khác với Xem nhanh (chỉ xem 1 câu). Bấm Chơi ở Trang chủ để chơi toàn màn hình.

5. XUẤT - 3 CÁCH:
- Xuất ra file HTML (1 file duy nhất, mở bằng trình duyệt): Trong màn hình soạn → bấm nút cam Xuất nội bộ (HTML) trên cùng bên phải → chọn chỗ lưu → được file .html → gửi cho học sinh mở là chơi được.
- Xuất lên web (lấy link chia sẻ): Trong màn hình soạn → bấm nút xanh Xuất lên web → đợi chạy xong → copy link → gửi. Link dùng được khoảng 15 ngày, xuất lại cùng dự án sẽ ghi đè.
- Đưa vào PowerPoint: xem mục PowerPoint dưới. Còn có Xuất Native/EXE (nâng cao, tạo thư mục game chạy riêng, ít dùng).

6. NHẬP CÂU HỎI TỪ FILE:
- Trong màn hình soạn → bên trái bấm Nhập khẩu (tím) → chọn file Word (.docx .doc), Excel (.xlsx), hoặc .txt → app tự đọc và hiện danh sách câu hỏi tìm được → bấm Nhập để thêm vào. Ngoặc [...] chứa biểu thức toán (ví dụ [x+1]) được giữ nguyên, không tính là chỗ trống; muốn ép thành chỗ trống thì dùng 2 ngoặc [[x+1]].
- Mẫu để điền đúng: trong cửa sổ Nhập khẩu → bấm Tải mẫu → chọn chỗ lưu → mở file mẫu .docx/.xlsx ra sẽ thấy bảng mẫu (Word: cột Câu hỏi, Lựa chọn A-D, Đáp án đúng, Giải thích; Excel: các cột Câu hỏi, Tùy chọn A-D, Đáp án đúng, Giải thích, Loại câu hỏi) → điền theo → lưu → nhập lại. Mẫu ALTP (Ai là triệu phú): file Excel chỉ có 2 mục hướng dẫn, file Word hỗ trợ trắc nghiệm và đúng/sai, cả hai đều không có phần Chú ý.

7. CÀI ĐẶT (bấm bánh răng góc trên phải):
- Chung: chọn ngôn ngữ (Việt/Anh/Pháp/Tây Ban Nha/Đức), giao diện sáng/tối, tự lưu (bật/tắt, mấy giây lưu 1 lần), thông báo, cỡ chữ to nhỏ
- Soạn thảo: phông chữ, cỡ chữ
- Game mặc định: thời gian mặc định, có trộn không, điểm, hiện giải thích
- Tiện ích bổ sung: xem đã cài bộ chèn PowerPoint chưa, bấm Cài đặt / Mở thư mục

8. TRỢ GIÚP & TÌM NHANH:
- Trợ giúp: bấm dấu ? góc trên phải → chọn mục Tổng quan/Giao diện/Tạo dự án/Edubot/Xem trước/PowerPoint...
- Tìm nhanh: bấm Ctrl+K → gõ "mở dự án / tạo mới / xem trước / xuất" → bấm Enter

9. POWERPOINT - CÁCH ĐÚNG NHƯ TRONG HÌNH (Insert → HTML Frame):
- Cài 1 lần: Mở EduPlay Studio → bấm Cài đặt (bánh răng góc trên phải) → Tiện ích bổ sung → bấm Cài đặt → nếu máy hiện hỏi cho phép thì bấm Đồng ý → tắt mở lại PowerPoint.
- Chèn game: Trong EduPlay Studio → mở dự án → bấm nút cam Xuất nội bộ (HTML) → lưu file .html. Sau đó mở PowerPoint → mở bài thuyết trình → bấm thẻ Insert (Chèn) trên thanh trên cùng → nhìn sang phía phải cùng → thấy nhóm EduPlay → bấm nút HTML Frame (biểu tượng </> có chữ HTML Frame như trong hình bạn gửi) → chọn file .html vừa xuất → bấm Mở/Chèn → trên slide sẽ hiện khung "EduPlay Viewer" (nền xanh nhạt, chữ EduPlay Viewer) → có thể kéo to nhỏ, di chuyển → lưu bài PowerPoint (Ctrl+S). Khi trình chiếu (F5/Shift+F5), bấm vào khung để chơi, game chạy ngay trong slide, không nhảy slide lung tung. Muốn đổi slide thì bấm ra ngoài khung rồi bấm mũi tên.

10. KHÁC:
- Lưu: bấm Lưu dự án (xanh lá) hoặc nhắn Edubot 'lưu dự án'. Sao lưu: nhắn 'sao lưu dự án'.
- Liệt kê/đếm: nhắn 'liệt kê dự án', 'liệt kê câu hỏi', 'đếm câu hỏi / có bao nhiêu câu'.
- Cấu hình nhanh: nhắn 'đổi thời gian thành 45 giây', 'đổi điểm thành 10', 'bật/tắt trộn', 'bật giải thích', 'bật chế độ thi', 'đổi nhạc nền'.
- Đi lại: nhắn 'về trang chủ', 'mở duyệt dự án', 'mở soạn', 'mở cài đặt', 'mở trợ giúp'.
- Tính toán: nhắn Edubot 'tính 12x8:4' (được gõ x thay *, : thay /, vd: 12x8:4 = 24; tính cục bộ offline, đúng 100%) hoặc bấm Ctrl+T → nhập biểu thức → Enter. App KHÔNG có ô Tính toán ở góc phải trên.
- Chụp màn hình nhanh: nhắn 'chụp màn hình' hoặc ở Trang chủ hoặc menu trái → Chụp màn hình.
- AI Edubot: nhớ 5 tin gần nhất, tự nói theo ngôn ngữ bạn đang chat, 55+ việc (tạo/sửa/xóa/nhân bản/liệt kê/đếm/dịch/tóm tắt/nhập/xóa trùng, quản lý dự án, cấu hình game, xem trước, xuất HTML/web/PowerPoint, tìm ảnh, tìm web, tính toán...), tìm thông tin trên mạng theo chương trình của nước bạn, tự tìm ảnh phù hợp tải về thư mục Tài liệu/EduPlay/Dự án/media/...png và gắn vào câu hỏi.
- Edubot KHÔNG bao giờ nói 'chưa hỗ trợ / đang phát triển / ko có trong danh sách lệnh'. Mọi câu hỏi hướng dẫn xài app đều phải trả lời từng bước kèm vị trí nút.

11. VỀ EDUPLAY STUDIO (trả lời đúng từng chữ):
- Phát triển bởi: Nguyễn Thanh Tân & Bùi Ngô Anh Thư.
- Email hỗ trợ: support@eduplay-studio.io.vn
- Website chính thức: https://eduplay-studio.io.vn
- App chạy offline trên máy tính (chỉ Edubot cần mạng).

LƯU Ý: Khi hướng dẫn, luôn nói bằng lời dễ hiểu như trên, ví dụ "Trang chủ → TẠO MỚI" , "bên trái → Nhập khẩu", "trên cùng → Xuất nội bộ (HTML) nút cam", "thẻ Insert → nhóm EduPlay → nút HTML Frame". Không dùng từ khó như VSTO/MSI/COM/Admin/StackedWidget/QFrame.
"""

KNOWLEDGE_EN = r"""
=== EDUPLAY STUDIO - ALL FEATURES (SIMPLE WORDS) ===
Computer program, works offline (only Edubot needs internet). Projects in Documents/EduPlay.

4 games: Quiz (5 types), Millionaire (only 1 of 4), Fishing, Adventure.
5 questions: multiple choice, true/false, fill blank ___, matching, short answer.

Layout:
- Top: EduPlay name, Help (?) and Settings (gear) on right.
- Home: 3 big buttons CREATE, EDIT, PLAY. Move mouse to very left edge to show left menu.
- Bottom right: purple round button to open chat.
- Create: Home → CREATE → name, description, pick type → Create.
- Browse: Home → EDIT → search/filter → Open/Duplicate/Delete/Rename.
- Editor: Left list (+Add, Import, Delete, Preview), middle edit question, right preview. Top: Save, Preview, Export.
- Preview: blue Preview button on top to test. Export: orange Export internal (HTML) for one .html file; blue Export to web for sharing link; for PowerPoint see below.
- Import: left → Import → choose Word/Excel using template → preview → Import. Download template inside import window. Brackets with math (e.g. [x+1]) stay literal; use double brackets [[x+1]] to force a blank. ALTP (Millionaire) templates: Excel has only 2 guide items, Word supports multiple choice and true/false, neither has the Note section.
- Settings: gear on top → General, Editor, Game, Add-ons.
- Help: ? on top → choose topic. Quick find: Ctrl+K.

PowerPoint (Insert → HTML Frame as in your image):
- Install once: Open EduPlay → Settings → Add-ons → Install → allow if asked → reopen PowerPoint.
- Insert: In EduPlay → Export to HTML (orange) → save .html. Open PowerPoint → open presentation → click Insert tab on top → look to far right → EduPlay group → click HTML Frame button (</> as in image) → choose .html → Insert → EduPlay Viewer frame appears on slide → resize → save. During slideshow, click frame to play.

Shortcuts: Ctrl+K, hover left edge, drag chat.

About (answer exactly):
- Developed by: Nguyễn Thanh Tân & Bùi Ngô Anh Thư.
- Support email: support@eduplay-studio.io.vn
- Official website: https://eduplay-studio.io.vn
- The app works offline (only Edubot needs internet).
"""

KNOWLEDGE_FR = KNOWLEDGE_EN
KNOWLEDGE_ES = KNOWLEDGE_EN
KNOWLEDGE_DE = KNOWLEDGE_EN

def get_knowledge(lang: str) -> str:
    l = str(lang or "vi").lower().strip().split("_")[0].split("-")[0]
    if l == "vi":
        return KNOWLEDGE_VI
    elif l == "en":
        return KNOWLEDGE_EN
    elif l == "fr":
        return KNOWLEDGE_FR
    elif l == "es":
        return KNOWLEDGE_ES
    elif l == "de":
        return KNOWLEDGE_DE
    return KNOWLEDGE_EN

# Navigation map - plain, accurate, read from VSTO/COM code
NAVIGATION_MAP = {
    "create_project": "Trang chủ → bấm TẠO MỚI → điền tên + mô tả + chọn kiểu trò chơi → bấm Tạo và chỉnh sửa",
    "open_project": "Trang chủ → bấm CHỈNH SỬA → Duyệt dự án → gõ tìm hoặc chọn thẻ dự án → bấm Mở",
    "save_project": "Trong màn hình soạn: bấm Lưu dự án (xanh lá) trên cùng, hoặc nhắn Edubot 'lưu dự án'",
    "list_projects": "Nhắn Edubot 'liệt kê dự án' hoặc vào Trang chủ → CHỈNH SỬA để xem tất cả",
    "list_questions": "Nhắn Edubot 'liệt kê câu hỏi' để xem 20 câu đầu của dự án đang mở",
    "count_questions": "Nhắn Edubot 'đếm câu hỏi / có bao nhiêu câu' để biết số lượng",
    "add_question": "Trong màn hình soạn: cột bên trái → thẻ Câu hỏi → bấm + Thêm câu hỏi → ở giữa chọn kiểu câu hỏi → điền nội dung và đáp án → bấm Lưu",
    "edit_question": "Trong màn hình soạn: bấm vào câu hỏi bên trái → sửa ở giữa → bấm Lưu",
    "delete_question": "Trong màn hình soạn: chọn câu bên trái → bấm Xóa đã chọn (hoặc nhắn Edubot 'xóa câu 2')",
    "duplicate_question": "Nhắn Edubot 'nhân bản câu 2' hoặc trong soạn: chọn câu → Nhân bản",
    "remove_duplicates": "Nhắn Edubot 'xóa câu trùng lặp' để lọc câu trùng nội dung",
    "set_time": "Nhắn Edubot 'đổi thời gian mỗi câu thành 45 giây' (5-300s) hoặc vào Cấu hình Game",
    "set_points": "Nhắn Edubot 'đổi điểm mỗi câu thành 10' hoặc vào Cấu hình Game",
    "shuffle": "Nhắn Edubot 'bật/tắt trộn câu hỏi' hoặc vào Cấu hình Game → trộn",
    "explanation": "Nhắn Edubot 'bật/hiện giải thích' hoặc vào Cấu hình Game",
    "exam_mode": "Nhắn Edubot 'bật chế độ thi 1 lần / cho làm lại' hoặc vào Cấu hình Game",
    "music": "Nhắn Edubot 'đổi nhạc nền' hoặc vào Cấu hình Game → nhạc nền",
    "preview": "Trong màn hình soạn: bấm Xem trước (nút xanh trên cùng) để thử; bấm Chơi để chơi toàn màn hình. Lưu ý: Xem trước = xem thử trong app, khác Xem nhanh (chỉ 1 câu)",
    "quick_preview": "Trong màn hình soạn: bấm Xem nhanh để chỉ xem 1 câu đang chọn",
    "export_html": "Trong màn hình soạn: bấm nút cam Xuất nội bộ (HTML) trên cùng bên phải → chọn chỗ lưu → được file .html mở bằng trình duyệt là chơi được",
    "export_web": "Trong màn hình soạn: bấm nút xanh Xuất lên web trên cùng → đợi chạy xong → copy link chia sẻ cho người khác",
    "export_powerpoint": "Cài 1 lần: Mở EduPlay Studio → bấm Cài đặt (bánh răng góc trên phải) → Tiện ích bổ sung → bấm Cài đặt → nếu máy hỏi cho phép thì bấm Đồng ý → tắt mở lại PowerPoint. Chèn game: Trong EduPlay → Xuất ra file HTML (nút cam) → mở PowerPoint → mở bài thuyết trình → bấm thẻ Insert trên thanh trên cùng → nhìn sang phải cùng thấy nhóm EduPlay → bấm nút HTML Frame (như trong hình, biểu tượng </>) → chọn file .html vừa xuất → bấm Mở/Chèn → khung EduPlay hiện trên slide → kéo chỉnh → lưu bài",
    "import": "Trong màn hình soạn: cột trái → bấm Nhập khẩu (nút tím) → chọn file Word/Excel theo mẫu → xem trước → bấm Nhập. Mẫu: trong cửa sổ Nhập khẩu → bấm Tải mẫu để lấy file mẫu",
    "template": "Trong màn hình soạn → Nhập khẩu → bấm Tải mẫu → chọn chỗ lưu → mở file mẫu .docx/.xlsx ra điền theo bảng (Câu hỏi, Lựa chọn A-D/Tùy chọn A-D, Đáp án đúng, Giải thích)",
    "settings": "Góc trên phải → bấm Cài đặt (bánh răng) → các thẻ Chung/Soạn thảo/Game/Tiện ích bổ sung",
    "help": "Góc trên phải → bấm Trợ giúp (dấu ?) → chọn mục cần xem",
    "command_palette": "Bấm Ctrl+K → gõ 'mở dự án / tạo mới / xem trước / xuất'",
    "chat": "Góc dưới phải → nút tròn tím có chữ 💬 → bấm để mở trò chuyện",
    "go_home": "Nhắn Edubot 'về trang chủ' hoặc bấm Trang chủ ở menu trái (rê chuột sát mép trái)",
    "open_browser": "Nhắn Edubot 'mở duyệt dự án' hoặc Trang chủ → CHỈNH SỬA",
    "screenshot": "Nhắn Edubot 'chụp màn hình' hoặc Trang chủ → menu trái → Chụp màn hình",
    "calculate": "Nhắn Edubot 'tính 12*8+5' để tính toán chính xác 100%",
    "app_info": "Nhắn Edubot 'thông tin app / tác giả / email hỗ trợ / website' (Nguyễn Thanh Tân & Bùi Ngô Anh Thư, support@eduplay-studio.io.vn, https://eduplay-studio.io.vn)",
}

TOOL_EXAMPLES = {
    "create_project": 'CREATE_PROJECT: {"name":"Toán lớp 4","game_type":"quiz_classic","description":"Phân số"}',
    "open_project": 'OPEN_PROJECT: {"name":"Toán lớp 4"}',
    "save_project": 'SAVE_PROJECT: {}',
    "list_projects": 'LIST_PROJECTS: {}',
    "list_questions": 'LIST_QUESTIONS: {}',
    "count_questions": 'COUNT_QUESTIONS: {}',
    "add_mc": 'ADD_QUESTION: {"type":"multiple_choice","question":"1+1=?","options":["1","2","3","4"],"correct_answer":1,"explanation":"1+1=2"}',
    "update": 'UPDATE_QUESTION: {"question_number":2,"patch":{"explanation":"Giải thích mới"}}',
    "delete": 'DELETE_QUESTION: {"question_number":2}',
    "config": 'UPDATE_GAME_CONFIG: {"randomize_questions":true,"question_time":45}',
    "set_time": 'SET_QUESTION_TIME: {"seconds":45}',
    "set_points": 'SET_POINTS: {"points":10}',
    "enable_shuffle": 'ENABLE_SHUFFLE: {}',
    "calculate": 'CALCULATE: {"expression":"12*8+5"}',
    "go_home": 'GO_HOME: {}',
}
