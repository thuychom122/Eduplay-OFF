## EduPlay PowerPoint VSTO Add-in

### 0) Cấu trúc
| Thư mục | Vai trò |
|:---|:---|
| `EduPlayPowerPointAddinVsto/` | Add-in VSTO (Ribbon, taskpane, khung HTML trên slide) |
| `EduPlayPowerPointAddin.Core/` | Logic dùng chung (đọc/ghi khung HTML trong PPTX) |
| `EduPlayPowerPointAddin.Core.Tests/` | Unit test (xUnit) cho phần Core |

Nút trên Ribbon: tab **Insert** → nhóm **EduPlay** → nút **HTML Frame**.

### 1) Mở project
- Mở solution: `ppt_vsto_addin/EduPlayPowerPointAddinVsto.sln`
- Yêu cầu: Visual Studio + workload Office/SharePoint development (VSTO)

### 2) Build
- Build project `EduPlayPowerPointAddinVsto` (Release)

### 2b) Chạy test phần Core
```powershell
dotnet test ppt_vsto_addin\EduPlayPowerPointAddin.Core.Tests\
```

### 3) Xuất MSI (để EduPlay Studio tự cài/repair)
- Tạo MSI theo 1 trong 2 cách:
  - Visual Studio Installer Projects extension (recommended): tạo Setup Project và build ra `EduPlayPowerPointAddin.msi`
  - WiX Toolset: dùng WiX v4 + file `ppt_vsto_addin/installer_wix/EduPlayPowerPointAddin.wxs`
- Đặt DisplayName: `EduPlay PowerPoint Add-in`
- Output cần copy vào app:
  - `eduplay_studio/eduplay/resources/vsto_addin/EduPlayPowerPointAddin.msi`
  - (đường dẫn này đã tồn tại trong repo — app sẽ tự tìm thấy MSI khi bấm *Cài đặt → Tiện ích bổ sung → Cài đặt*)

#### Build MSI bằng WiX (tự động)
- Script sẽ tự cài `wix` .NET tool (WiX v4.x) nếu máy chưa có.
- Chạy ở repo root:
  - `build_ppt_vsto_addin_msi.cmd`
