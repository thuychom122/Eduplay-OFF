<div align="center">

# 📥 Hướng dẫn Cài đặt

### EduPlay Studio 1.0.0 · Windows 10/11

<p>
  <img src="https://img.shields.io/badge/Windows-0078D4?style=for-the-badge&logo=windows&logoColor=white" alt="windows"/>
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="python"/>
  <img src="https://img.shields.io/badge/Build-Nuitka%20%2B%20Cython-43A047?style=for-the-badge" alt="build"/>
</p>

[⬅ Về README](README.md) · [🛡️ Bảo mật](SECURITY.md)

</div>

---

## 📑 Mục lục

1. [Yêu cầu hệ thống](#-1-yêu-cầu-hệ-thống)
2. [Cài từ mã nguồn](#-2-cài-từ-mã-nguồn-windows)
3. [Kết nối AI (không cần key)](#-3-kết-nối-ai-không-cần-key)
4. [Add-in PowerPoint](#-4-add-in-powerpoint)
5. [Build bản phát hành](#-5-build-bản-phát-hành--installer)
6. [Gỡ cài đặt](#-6-gỡ-cài-đặt)
7. [Gỡ rối thường gặp](#-7-gỡ-rối-thường-gặp)

---

## 🖥️ 1. Yêu cầu hệ thống

| Thành phần | Tối thiểu | Khuyến nghị |
|:---|:---|:---|
| **HĐH** | Windows 10 64-bit (17763+) | Windows 11 22H2+ |
| **CPU / RAM** | Dual-core · 4 GB | Quad-core · 8 GB+ |
| **Ổ cứng** | 1 GB trống | 5 GB (kèm dự án & export) |
| **Python** | 3.10 | **3.12** (đã kiểm thử) |
| **PowerPoint** | 2016+ (tùy chọn) | Microsoft 365 (đã kích hoạt) |
| **WebView2** | Evergreen Runtime (cho COM Add-in) | Bản mới nhất |

> [!NOTE]
> EduPlay Studio **chỉ hỗ trợ Windows** ở phiên bản 1.0.0. macOS/Linux chưa được kiểm thử.

---

## 📦 2. Cài từ mã nguồn (Windows)

### Bước 1 — Chuẩn bị

```powershell
# Kiểm tra Python
python --version   # phải ≥ 3.10
pip --version
```

> [!TIP]
> Nên dùng **Windows Terminal** hoặc **PowerShell 7+** để hiển thị tiếng Việt & emoji đúng.

### Bước 2 — Tạo môi trường ảo

```powershell
# Tại thư mục gốc dự án EDUPLAY-OFFLINE
python -m venv venv

# Kích hoạt
.\venv\Scripts\Activate.ps1          # PowerShell
# hoặc
.\venv\Scripts\activate.bat          # CMD
```

Bạn sẽ thấy prefix `(venv)` ở đầu dòng lệnh — nghĩa là đã vào môi trường ảo.

### Bước 3 — Cài phụ thuộc

```powershell
pip install --upgrade pip
pip install -r requirements.txt      # cài chính
# hoặc khóa chặt phiên bản:
pip install -r requirements.lock
```

| File | Khi nào dùng |
|:---|:---|
| `requirements.txt` | Cài linh hoạt, tự lấy bản mới tương thích |
| `requirements.lock` | Cài **reproducible** — khóa đúng phiên bản đã test |

### Bước 4 — Chạy ứng dụng

```powershell
python eduplay_studio\app.py
```

🎉 Cửa sổ **EduPlay Studio** sẽ mở. Ứng dụng chạy đầy đủ tính năng offline ngay —
không cần cấu hình AI trước (xem mục 3).

---

## 🤖 3. Kết nối AI (không cần key)

| Mục | Bắt buộc | Mặc định |
|:---|:---:|:---|
| Máy chủ AI | ❌ | `https://site--eduplay-ai--sx2zlgv27rbh.code.run` |
| `GROQ_MODEL` (chỉ khi đổi model) | ❌ | `openai/gpt-oss-20b` |

Edubot tự đăng ký thiết bị theo máy (`device_id` / `device_key` / `machine_fingerprint`)
nên không cần dán API key. Lần đầu mở app, máy chủ có thể cần vài giây khởi động —
Edubot sẽ tự thử lại và báo *"server đang khởi động"*.

```powershell
# Chỉ khi muốn ghim model
$env:GROQ_MODEL="openai/gpt-oss-20b"
python eduplay_studio\app.py
```

Trong **Cài đặt → AI** có thể bật *Cho phép truy cập Internet* và *Cho phép tải ảnh*.

<details>
<summary>🔐 Lưu ý bảo mật</summary>

- Key OpenAI/Gemini nếu bạn tự nhập được lưu **cục bộ**, không commit lên git.
- Khi gửi log/ảnh cho người khác, hãy **che key**.
- Token đăng ký thiết bị nằm ở `Documents\EduPlay\Settings\ai_proxy_token.txt`.

</details>

---

## 🔌 4. Add-in PowerPoint

### Tự động (khuyên dùng)

1. Mở **EduPlay Studio → ⚙️ Cài đặt → Add-in → Cài / Sửa Add-in**
2. Chấp nhận **UAC** (Cho phép thay đổi thiết bị)
3. **Khởi động lại PowerPoint**
4. Tìm tab **EduPlay** trên Ribbon (nếu không thấy → kiểm tra `Add-ins`)

### Thủ công (dành cho IT / triển khai phòng máy)

| Loại Add-in | File | Yêu cầu |
|:---|:---|:---|
| **VSTO (MSI)** | `eduplay/resources/vsto_addin/EduPlayPowerPointAddin.msi` | VSTO Runtime, Office đã kích hoạt |
| **COM (x64)** | `ppt_com_addin/EduPlayPowerPointAddin.sln` build `Release\|x64` | .NET 4.8, WebView2 |

Registry mà COM Add-in đăng ký:

```
HKCU\Software\Microsoft\Office\PowerPoint\Addins\EduPlay.PowerPointAddin.Connect
  LoadBehavior = 3 (DWORD)
  FriendlyName = EduPlay
  Description  = EduPlay PowerPoint Add-in
```

> [!IMPORTANT]
> Office **chưa kích hoạt** có thể ẩn toàn bộ Add-in. Hãy kích hoạt Office trước.

---

## 🏗️ 5. Build bản phát hành + Installer

### 5.1 Build portable (Nuitka + Cython)

```powershell
.\build_release.bat
```

- Yêu cầu: **Visual Studio Build Tools** → workload **Desktop development with C++** + Windows SDK.
- Workspace cô lập: `build_nuitka/` (không làm bẩn mã nguồn).
- Kết quả: `dist\EduPlayStudio\EduPlayStudio.exe` + thư viện (không đóng gói onefile để giữ Qt WebEngine ổn định).

### 5.2 Đóng gói Installer (Inno Setup 6)

```powershell
.\build_installer.bat
# → installer\EduPlay-Studio-v1.0.0-Setup.exe
```

| Tùy chọn Installer | Mô tả |
|:---|:---|
| `desktopicon` | Tạo shortcut Desktop |
| `fileassoc` | Gắn `.eduplay` mở bằng Studio |
| `addtopath` | Thêm vào PATH |
| `firewall` | Thêm rule Windows Firewall |

> [!TIP]
> Script `setup.iss` đã cấu hình đa ngôn ngữ **EN/VI**, tự phát hiện bản cũ (Upgrade vs Clean Install) và dọn cache khi gỡ.

---

## 🧹 6. Gỡ cài đặt

Mở **Cài đặt Windows → Ứng dụng → EduPlay Studio → Gỡ cài đặt**.

Trình gỡ sẽ hỏi 2 lần:

1. **Xóa settings/cache?** → `Documents\EduPlay\PublishCache`, `%LOCALAPPDATA%\EduPlayStudio` (gồm `logs\`), ...
2. **Xóa dự án?** → `Documents\EduPlay\Projects` & `Exports`

> ⚠️ `Documents\EduPlay\Settings` (chứa `ai_proxy_token`) **chỉ xóa khi chọn Gỡ sạch (cả 2 = Có)** — khi đó app cũng gửi lệnh xóa key trên server để cài lại tạo key mới.

---

## 🛠️ 7. Gỡ rối thường gặp

<details>
<summary>❌ <code>python</code> không nhận / pip lỗi</summary>

- Cài Python từ https://www.python.org — tick **Add python.exe to PATH**.
- Thử `py --version` thay vì `python`.
- Chạy PowerShell **với quyền thường** (không cần Admin) khi tạo venv.

</details>

<details>
<summary>❌ Edubot không phản hồi</summary>

- Kiểm tra kết nối mạng (Edubot là tính năng **duy nhất** cần Internet).
- Lần đầu máy chủ có thể đang khởi động — chờ vài giây rồi gửi lại.
- Kiểm tra trong **Cài đặt → AI** mục *Trạng thái máy chủ*.
- Tắt app rồi mở lại để đăng ký thiết bị mới.
- Mọi tính năng khác (soạn câu hỏi, xuất HTML, xuất link) vẫn chạy bình thường.

</details>

<details>
<summary>❌ Build Nuitka báo thiếu compiler</summary>

- Cài **Visual Studio Build Tools 2022** + **Desktop development with C++**.
- Cài **Windows SDK** mới nhất.
- Chạy `build_release.bat` từ **x64 Native Tools Command Prompt** nếu vẫn lỗi.

</details>

<details>
<summary>❌ PowerPoint không thấy Add-in</summary>

- Office phải **đã kích hoạt**.
- Kiểm tra `Tệp → Tùy chọn → Add-ins → COM Add-ins → Đi...` — tick `EduPlay`.
- Cài **WebView2 Evergreen Runtime** (COM Add-in).
- Chạy lại **Cài / Sửa Add-in** trong Studio bằng **Run as Administrator**.

</details>

<details>
<summary>❌ Antivirus chặn <code>EduPlayStudio.exe</code></summary>

- Đây là false-positive do Nuitka. Thêm thư mục `dist\EduPlayStudio` vào **Exclusions** của Windows Defender / AV.
- Hoặc build lại trên máy sạch.

</details>

---

<div align="center">

Cần trợ giúp thêm? → bấm nút **?** trong app (mục *Trợ giúp*) · [SECURITY.md](SECURITY.md) · ✉️ support@eduplay-studio.io.vn

[⬆ Lên đầu trang](#-hướng-dẫn-cài-đặt)

</div>
