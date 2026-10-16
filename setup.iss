; ============================================================
;  EduPlay Studio - Windows Installer (Inno Setup 6)
;  Version : 1.0.0 Official Release
;  Author  : VinCat Team (2026)
; ------------------------------------------------------------
;  * Installs the offline build from dist\EduPlayStudio
;  * Upgrade keeps data by default; "Clean install" wipes
;    EVERYTHING EduPlay ever created AND deletes this
;    machine's AI device ID on the server (Supabase
;    device_bindings via the AI gateway /device/delete),
;    so a fresh key is issued on reinstall.
;  * Uninstall: temp files are always removed. An options dialog
;    with checkboxes (ALL DEFAULT UNCHECKED) lets the user wipe
;    projects / settings+tokens+memory / Supabase device row /
;    PowerPoint Add-in individually. No yes/no questions.
; ============================================================

#define AppName "EduPlay Studio"
#define AppVersion "1.0.0"
#define AppRelease "Official Release"
#define AppVerName AppName + " " + AppVersion + " " + AppRelease
#define AppPublisher "VinCat Team"
#define OldPublisher "EduPlay Studio"
#define AppExeName "EduPlayStudio.exe"
; NOTE on AppId: NEVER use braces here. The original script used
; #define AppId "{{EDUPLAY-STUDIO-APP-2026}}", and through the
; #define indirection the trailing "}}" survived script unescaping,
; so every install created the malformed key
;   ...\Uninstall\{EDUPLAY-STUDIO-APP-2026}}_is1   (note "}}_is1").
; A brace-free ID avoids the whole escaping trap. The malformed
; legacy key is still detected/removed for upgrades (see
; GetUninstallString / granular wipe procedures below).
#define AppId "EduPlay-Studio-2026"
#define LegacyUninstallKey "{EDUPLAY-STUDIO-APP-2026}}_is1"
#define AppURL "https://game.eduplay-studio.io.vn"
#define SupportURL "https://game.eduplay-studio.io.vn/support"
#define UpdateURL "https://game.eduplay-studio.io.vn/download"
#define AiGatewayUrl "https://site--eduplay-ai--sx2zlgv27rbh.code.run"
#define AddinDisplayName "EduPlay PowerPoint Add-in"
#define AddinKeyName "EduPlayPowerPointAddin"

#define RepoRoot SourcePath
#define BuildDir RepoRoot + "dist\EduPlayStudio"
#define BuildExe BuildDir + "\EduPlayStudio.exe"
#define AppIcon RepoRoot + "eduplay_studio\eduplay\resources\icons\icon.ico"
#define OutputDir RepoRoot + "installer"

; ---- Fail fast with a clear message instead of a cryptic error ----
#ifexist BuildExe
#else
  #error "Standalone build not found at dist\EduPlayStudio\EduPlayStudio.exe. Run build_release.bat (or build_installer.bat) first."
#endif

#ifexist AppIcon
#else
  #error "Installer icon not found at eduplay_studio\eduplay\resources\icons\icon.ico."
#endif

[Setup]
; ---- Identity ----
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppVerName}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#SupportURL}
AppUpdatesURL={#UpdateURL}
AppContact=support@eduplay-studio.io.vn
AppComments=Create quiz, fishing and Millionaire learning games - offline, no coding required
AppCopyright=Copyright (C) 2026 {#AppPublisher}

; ---- Folders ----
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
; NOTE: UninstallFilesDir intentionally left at default ({app}).
; A previous revision pointed it at {app}\uninstall while the
; cleanup entries still referenced {app}\unins000.* (dead entries).

; ---- Wizard look ----
DisableProgramGroupPage=yes
DisableDirPage=no
DisableReadyPage=no
DisableFinishedPage=no
DisableWelcomePage=no
ShowLanguageDialog=auto
WizardStyle=modern
WizardSizePercent=120,100
; NOTE: WizardResizable removed - obsolete and ignored since Inno 6.1.
; NOTE: UsedUserAreasWarning disabled on purpose - this installer
; intentionally manages per-user EduPlay data (Documents\EduPlay,
; LocalAppData caches) so upgrades and wipe-uninstalls behave.
UsedUserAreasWarning=no

; ---- Icons ----
SetupIconFile={#AppIcon}
UninstallDisplayIcon={app}\{#AppExeName}

; ---- Output ----
OutputDir={#OutputDir}
OutputBaseFilename=EduPlay-Studio-{#AppVersion}-Official-Setup
; lzma2/max: same format as ultra, but builds in minutes instead of
; hanging. Most of dist\ is already-compressed binaries (Qt DLLs,
; mp3, pak), so ultra64 only burns CPU for ~zero extra savings.
Compression=lzma2/max
SolidCompression=yes
CompressionThreads=auto
InternalCompressLevel=max

; ---- Version info (embedded in Setup.exe) ----
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription={#AppVerName} Installer
VersionInfoCopyright=Copyright (C) 2026 {#AppPublisher}
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

; ---- Privileges & OS ----
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=commandline dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763

; ---- Behaviour ----
AllowNoIcons=yes
ChangesEnvironment=yes
ChangesAssociations=yes
CloseApplications=force
RestartApplications=no
RestartIfNeededByRun=no
AllowCancelDuringInstall=yes
CreateUninstallRegKey=yes
UpdateUninstallLogAppName=yes
UsePreviousAppDir=yes
UsePreviousGroup=yes
UsePreviousTasks=yes
UsePreviousLanguage=yes
UsePreviousSetupType=yes
; NOTE: no AppMutex on purpose - the application does not create a
; named mutex, so AppMutex would only give a false sense of safety.
; Running instances are closed via CloseApplications + taskkill.
SetupLogging=yes
ShowComponentSizes=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
; Repo-vendored copy (tools\InnoSetup) instead of compiler:Languages\...
; so builds are warning-free and byte-identical on every machine.
Name: "vietnamese"; MessagesFile: "tools\InnoSetup\Vietnamese.isl"

[CustomMessages]
; ============ Tasks / Run ============
english.AdditionalTasks=Additional options:
english.DesktopIcon=Create a &desktop shortcut
english.FileAssoc=Open .eduplay project files with {#AppName}
english.AddToPath=Add the application folder to system &PATH (command line use)
english.FirewallException=Allow {#AppName} through &Windows Firewall
english.LaunchApp=Launch {#AppName}
vietnamese.AdditionalTasks=Tùy chọn bổ sung:
vietnamese.DesktopIcon=Tạo biểu tượng trên màn hình &desktop
vietnamese.FileAssoc=Mở file dự án .eduplay bằng {#AppName}
vietnamese.AddToPath=Thêm thư mục ứng dụng vào &PATH hệ thống (dùng dòng lệnh)
vietnamese.FirewallException=Cho phép {#AppName} đi qua Tường lửa &Windows
vietnamese.LaunchApp=Khởi chạy {#AppName}

; ============ Install: close app ============
english.ClosePrompt=EduPlay Studio is currently running. Setup must close it to continue. Click OK to close it now, or Cancel to exit Setup.
vietnamese.ClosePrompt=EduPlay Studio đang chạy. Bộ cài đặt cần tắt ứng dụng để tiếp tục. Bấm OK để tắt ngay, hoặc Cancel để thoát.

; ============ Install: previous version ============
english.OldLead=Version
english.OldMid=is already installed. How do you want to proceed?
english.OldYes=YES = Clean install (erase every EduPlay data folder and the server AI device ID, then install fresh)
english.OldNo=NO = Upgrade (keep all projects and settings)
english.OldCancel=CANCEL = Exit Setup
english.OldRecomm=Recommended: NO (Upgrade).
vietnamese.OldLead=Phiên bản
vietnamese.OldMid=đã được cài đặt. Bạn muốn tiếp tục thế nào?
vietnamese.OldYes=YES = Cài sạch (xóa toàn bộ dữ liệu EduPlay và ID thiết bị AI trên server, rồi cài mới)
vietnamese.OldNo=NO = Nâng cấp (giữ nguyên dự án và cài đặt)
vietnamese.OldCancel=CANCEL = Thoát bộ cài đặt
vietnamese.OldRecomm=Khuyên dùng: NO (Nâng cấp).
english.OldUninstFail=Could not remove the previous version. Setup will now exit.
vietnamese.OldUninstFail=Không gỡ được phiên bản cũ. Bộ cài đặt sẽ thoát.

; ============ Uninstall: close app ============
english.UnClosePrompt=EduPlay Studio is currently running. Click OK and the uninstaller will close it so removal can continue.
vietnamese.UnClosePrompt=EduPlay Studio đang chạy. Bấm OK để trình gỡ cài đặt tắt ứng dụng và tiếp tục.

; ============ Uninstall: wipe choice (checkbox dialog, all default OFF) ============
english.UnDlgTitle=Uninstall EduPlay Studio - remove extra data?
english.UnDlgNote=Temporary files are always removed. Tick anything else below ONLY if you want it permanently deleted. Everything is unchecked by default.
english.UnOptProjects=Projects, exports and templates (Documents\EduPlay\Projects, Exports, ...)
english.UnOptSettings=Settings, saved AI tokens and Edubot memory (Documents\EduPlay\Settings, AppData caches ...)
english.UnOptServer=This machine on the server (Supabase device_bindings row - a brand-new key is issued on reinstall)
english.UnOptAddin=PowerPoint Add-in (MSI package, Office registration and slide caches)
english.UnBtnGo=Continue uninstall
english.UnBtnCancel=Cancel
vietnamese.UnDlgTitle=Gỡ cài đặt EduPlay Studio - xóa thêm dữ liệu?
vietnamese.UnDlgNote=File tạm luôn bị xóa. Chỉ tick vào mục nào bên dưới NẾU bạn muốn xóa vĩnh viễn mục đó. Mặc định tất cả đều KHÔNG tick.
vietnamese.UnOptProjects=Dự án, file đã xuất và mẫu (Documents\EduPlay\Projects, Exports, ...)
vietnamese.UnOptSettings=Cài đặt, token AI đã lưu và bộ nhớ Edubot (Documents\EduPlay\Settings, cache AppData ...)
vietnamese.UnOptServer=Thiết bị này trên server (dòng device_bindings Supabase - cài lại sẽ được cấp key hoàn toàn mới)
vietnamese.UnOptAddin=Tiện ích PowerPoint (gói MSI, đăng ký Office và cache slide)
vietnamese.UnBtnGo=Tiếp tục gỡ
vietnamese.UnBtnCancel=Hủy bỏ

; ============ Uninstall: summary ============
english.SumDone=EduPlay Studio has been uninstalled.
english.SumTemp=Removed: temporary caches, preview files, registry entries and file associations.
english.SumKept=Kept: your projects and settings in Documents\EduPlay (reinstall to reuse them).
english.SumWipedProjects=Wiped: all projects, exports and templates in Documents\EduPlay.
english.SumWipedSettings=Wiped: settings, saved AI tokens, Edubot memory and local caches.
english.SumWipedAddin=Wiped: PowerPoint Add-in package, Office registration and slide caches.
english.SumKeptProjects=Kept: projects and exports in Documents\EduPlay.
english.SumKeptSettings=Kept: settings, AI tokens and Edubot memory.
english.SumKeptAddin=Kept: PowerPoint Add-in (still installed).
english.SumServerOk=Server: this machine's row in Supabase device_bindings was deleted. A new key will be issued on reinstall.
english.SumServerFail=Server: the AI server could not be reached (offline?). Local data was still wiped, but the old server key may remain until the next online reinstall.
english.SumServerSkipped=Server: this machine was left untouched (reinstall reuses the existing key).
vietnamese.SumDone=Đã gỡ cài đặt EduPlay Studio.
vietnamese.SumTemp=Đã xóa: cache tạm, file xem trước, khóa registry và liên kết file.
vietnamese.SumKept=Đã giữ: dự án và cài đặt trong Documents\EduPlay (cài lại là dùng tiếp).
vietnamese.SumWipedProjects=Đã xóa: toàn bộ dự án, file đã xuất và mẫu trong Documents\EduPlay.
vietnamese.SumWipedSettings=Đã xóa: cài đặt, token AI, bộ nhớ Edubot và cache máy.
vietnamese.SumWipedAddin=Đã xóa: gói PowerPoint Add-in, đăng ký Office và cache slide.
vietnamese.SumKeptProjects=Đã giữ: dự án và file đã xuất trong Documents\EduPlay.
vietnamese.SumKeptSettings=Đã giữ: cài đặt, token AI và bộ nhớ Edubot.
vietnamese.SumKeptAddin=Đã giữ: PowerPoint Add-in (vẫn còn cài).
vietnamese.SumServerOk=Server: đã xóa dòng thiết bị của máy này trong Supabase device_bindings. Cài lại sẽ được cấp key mới.
vietnamese.SumServerFail=Server: không liên lạc được với máy chủ AI (mất mạng?). Dữ liệu trên máy vẫn đã xóa, nhưng key cũ trên server có thể còn đến lần cài lại có mạng.
vietnamese.SumServerSkipped=Server: giữ nguyên thiết bị này (cài lại dùng tiếp key cũ).

; ---- Vietnamese texts missing from the bundled Vietnamese.isl ----
; (Inno falls back to English for these; defining them here removes
; the warnings AND gives Vietnamese users proper text.)
[Messages]
vietnamese.ArchiveIncorrectPassword=Mật khẩu không đúng
vietnamese.ArchiveIsCorrupted=File nén đã bị hỏng
vietnamese.ArchiveUnsupportedFormat=Định dạng file nén không được hỗ trợ
vietnamese.ButtonStopExtraction=&Dừng giải nén
vietnamese.DownloadingLabel2=Đang tải file...
vietnamese.ErrorDownloading=Đã xảy ra lỗi khi tải file:
vietnamese.ErrorExtracting=Đã xảy ra lỗi khi giải nén:
vietnamese.ErrorExtractionAborted=Đã hủy giải nén
vietnamese.ErrorExtractionFailed=Giải nén thất bại: %1
vietnamese.ExtractingLabel=Đang giải nén file...
vietnamese.RetryCancelCancel=Hủy bỏ
vietnamese.RetryCancelRetry=Thử &lại
vietnamese.RetryCancelSelectAction=Chọn hành động
vietnamese.SourceVerificationFailed=Xác minh file nguồn thất bại: %1
vietnamese.StatusDownloadFiles=Đang tải file...
vietnamese.StopExtraction=Bạn có chắc muốn dừng giải nén?
vietnamese.VerificationFileHashIncorrect=Mã hash của file không đúng
vietnamese.VerificationFileNameIncorrect=Tên file không đúng
vietnamese.VerificationFileSizeIncorrect=Dung lượng file không đúng
vietnamese.VerificationFileTagIncorrect=Thẻ (tag) của file không đúng
vietnamese.VerificationKeyNotFound=File chữ ký "%1" dùng khóa không xác định
vietnamese.VerificationSignatureDoesntExist=File chữ ký "%1" không tồn tại
vietnamese.VerificationSignatureInvalid=File chữ ký "%1" không hợp lệ

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopIcon}"; GroupDescription: "{cm:AdditionalTasks}"; Flags: checkedonce
Name: "fileassoc"; Description: "{cm:FileAssoc}"; GroupDescription: "{cm:AdditionalTasks}"; Flags: checkedonce
Name: "addtopath"; Description: "{cm:AddToPath}"; GroupDescription: "{cm:AdditionalTasks}"; Flags: unchecked
Name: "firewall"; Description: "{cm:FirewallException}"; GroupDescription: "{cm:AdditionalTasks}"; Flags: unchecked

[Dirs]
Name: "{app}"; Permissions: users-modify
Name: "{app}\logs"; Permissions: users-modify
Name: "{app}\cache"; Permissions: users-modify
Name: "{app}\temp"; Permissions: users-modify
Name: "{commonappdata}\{#AppName}"; Permissions: users-modify
Name: "{commonappdata}\{#AppName}\Templates"; Permissions: users-modify
Name: "{userdocs}\EduPlay"; Permissions: users-modify
Name: "{userdocs}\EduPlay\Projects"; Permissions: users-modify
Name: "{userdocs}\EduPlay\Exports"; Permissions: users-modify
Name: "{localappdata}\EduPlayStudio"; Permissions: users-modify
Name: "{localappdata}\EduPlayStudio\Cache"; Permissions: users-modify
Name: "{localappdata}\EduPlayStudio\Logs"; Permissions: users-modify

[Files]
; Main application tree (includes the PowerPoint add-in MSI under
; eduplay\resources\vsto_addin, which the app installs on demand
; from Settings - no separate installer step needed).
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs solidbreak

[InstallDelete]
; Stale Chromium/WebView2 preview profile shipped with older builds.
; Safe to drop before install: the app recreates it on first preview.
Type: filesandordirs; Name: "{app}\eduplay\preview_edge_profile"

[Registry]
; ---- App registration (new publisher) ----
Root: HKLM; Subkey: "Software\{#AppPublisher}\{#AppName}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\{#AppPublisher}\{#AppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletevalue
Root: HKLM; Subkey: "Software\{#AppPublisher}\{#AppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#AppVersion}"; Flags: uninsdeletevalue
Root: HKLM; Subkey: "Software\{#AppPublisher}\{#AppName}"; ValueType: string; ValueName: "Release"; ValueData: "{#AppRelease}"; Flags: uninsdeletevalue
Root: HKLM; Subkey: "Software\{#AppPublisher}\{#AppName}"; ValueType: string; ValueName: "ExecutablePath"; ValueData: "{app}\{#AppExeName}"; Flags: uninsdeletevalue
; NOTE: HKLM-only on purpose. In non-admin override installs Inno maps
; HKLM to HKCU automatically, while hardcoded HKCU entries would land
; in the elevated admin hive instead of the real user hive.

; ---- Extra Add/Remove Programs info ----
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1"; ValueType: string; ValueName: "DisplayIcon"; ValueData: "{app}\{#AppExeName},0"; Flags: uninsdeletevalue
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1"; ValueType: string; ValueName: "URLInfoAbout"; ValueData: "{#AppURL}"; Flags: uninsdeletevalue
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1"; ValueType: string; ValueName: "HelpLink"; ValueData: "{#SupportURL}"; Flags: uninsdeletevalue
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1"; ValueType: string; ValueName: "URLUpdateInfo"; ValueData: "{#UpdateURL}"; Flags: uninsdeletevalue
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1"; ValueType: dword; ValueName: "NoModify"; ValueData: "1"; Flags: uninsdeletevalue
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1"; ValueType: dword; ValueName: "NoRepair"; ValueData: "1"; Flags: uninsdeletevalue

; ---- File association (.eduplay) ----
Root: HKCR; Subkey: ".eduplay"; ValueType: string; ValueData: "EduPlayProject"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCR; Subkey: "EduPlayProject"; ValueType: string; ValueData: "EduPlay Project File"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCR; Subkey: "EduPlayProject\DefaultIcon"; ValueType: string; ValueData: "{app}\{#AppExeName},0"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCR; Subkey: "EduPlayProject\shell\open\command"; ValueType: string; ValueData: """{app}\{#AppExeName}"" ""%1"""; Flags: uninsdeletekey; Tasks: fileassoc

; ---- App Paths (Run dialog support) ----
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\{#AppExeName}"; ValueType: string; ValueData: "{app}\{#AppExeName}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\{#AppExeName}"; ValueType: string; ValueName: "Path"; ValueData: "{app}"; Flags: uninsdeletekey

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Comment: "Launch {#AppName}"; IconIndex: 0
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"; Comment: "Uninstall {#AppName}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Comment: "{#AppName}"; IconIndex: 0; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent unchecked
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""{#AppName}"" dir=in action=allow program=""{app}\{#AppExeName}"" enable=yes profile=any"; Flags: runhidden; Tasks: firewall; Check: IsAdminInstallMode

[UninstallRun]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#AppName}"""; Flags: runhidden; RunOnceId: "RemoveFirewall"

[UninstallDelete]
; Runtime droppings inside {app} that are NOT in the install log.
; Everything else lives in [Code] as the single source of truth.
Type: files; Name: "{app}\*.log"
Type: files; Name: "{app}\*.tmp"
Type: files; Name: "{app}\*.cache"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\cache"
Type: filesandordirs; Name: "{app}\temp"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\eduplay\preview_edge_profile"
Type: dirifempty; Name: "{app}"

[Code]
// ============================================================
//  Global state
// ============================================================
var
  WipeProjects: Boolean;     // uninstall: wipe projects/exports/templates
  WipeSettings: Boolean;     // uninstall: wipe settings/tokens/memory/caches
  WipeServer: Boolean;       // uninstall: delete Supabase device_bindings row
  WipeAddin: Boolean;        // uninstall: remove PowerPoint Add-in fully
  CleanInstallChosen: Boolean;
  // 0 = not attempted, 1 = server confirmed delete, 2 = failed/offline
  ServerDeleteState: Integer;

// ============================================================
//  Small safe wrappers (never raise)
// ============================================================
procedure SafeDelTree(const Path: String);
begin
  try
    if DirExists(Path) then
      DelTree(Path, True, True, True);
  except
  end;
end;

procedure SafeDeleteRegTree(const Root: Integer; const SubKey: String);
begin
  try
    RegDeleteKeyIncludingSubkeys(Root, SubKey);
  except
  end;
end;

function SafeRegReadString(const Root: Integer; const SubKey, ValueName: String): String;
var
  V: String;
begin
  Result := '';
  try
    if RegQueryStringValue(Root, SubKey, ValueName, V) then
      Result := V;
  except
    Result := '';
  end;
end;

// ============================================================
//  Running-instance handling
// ============================================================
function IsAppRunning(): Boolean;
var
  Locator, Service, Procs: Variant;
begin
  Result := False;
  try
    Locator := CreateOleObject('WbemScripting.SWbemLocator');
    Service := Locator.ConnectServer('localhost', 'root\CIMV2', '', '');
    Procs := Service.ExecQuery('SELECT ProcessId FROM Win32_Process WHERE Name="{#AppExeName}"');
    Result := (Procs.Count > 0);
  except
    Result := False;
  end;
end;

function CloseAppWithPrompt(const Prompt: String): Boolean;
var
  Code: Integer;
begin
  Result := True;
  if IsAppRunning() then
  begin
    if MsgBox(Prompt, mbConfirmation, MB_OKCANCEL) = IDOK then
    begin
      Exec('taskkill.exe', '/F /IM "{#AppExeName}"', '', SW_HIDE, ewWaitUntilTerminated, Code);
      Sleep(1500);
      Result := not IsAppRunning();
    end
    else
      Result := False;
  end;
end;

// ============================================================
//  Previous-install detection (new publisher key first,
//  then the legacy "EduPlay Studio" publisher key)
// ============================================================
function GetInstalledVersion(): String;
begin
  Result := SafeRegReadString(HKLM, 'Software\{#AppPublisher}\{#AppName}', 'Version');
  if Result = '' then
    Result := SafeRegReadString(HKCU, 'Software\{#AppPublisher}\{#AppName}', 'Version');
  if Result = '' then
    Result := SafeRegReadString(HKLM, 'Software\{#OldPublisher}\{#AppName}', 'Version');
  if Result = '' then
    Result := SafeRegReadString(HKCU, 'Software\{#OldPublisher}\{#AppName}', 'Version');
end;

function GetUninstallString(): String;
begin
  Result := SafeRegReadString(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1', 'UninstallString');
  if Result = '' then
    Result := SafeRegReadString(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1', 'UninstallString');
  // Legacy malformed key from the pre-1.0.0 script (see AppId note).
  // Braces below are inside a Pascal string literal: no {#...}, so
  // ISPP leaves them verbatim - exactly what we want here.
  if Result = '' then
    Result := SafeRegReadString(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#LegacyUninstallKey}', 'UninstallString');
  if Result = '' then
    Result := SafeRegReadString(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#LegacyUninstallKey}', 'UninstallString');
end;

function UninstallPreviousVersion(): Boolean;
var
  Cmd: String;
  Code: Integer;
begin
  Result := True;
  Cmd := RemoveQuotes(GetUninstallString());
  if Cmd <> '' then
  begin
    // NOTE: no /FORCEREMOVE here - that switch does not exist in Inno
    // and the old uninstaller keeps user data when silent. The new
    // installer wipes data itself when CleanInstallChosen (see below).
    Log('Uninstalling previous version silently (user data kept for now).');
    Result := Exec(Cmd, '/VERYSILENT /NORESTART /SUPPRESSMSGBOXES', '', SW_HIDE, ewWaitUntilTerminated, Code);
    if Result then
      Sleep(2000);
  end;
end;

// ============================================================
//  PATH handling
// ============================================================
procedure AddToPath();
var
  Path, AppPath: String;
begin
  try
    if not RegQueryStringValue(HKLM, 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 'Path', Path) then
      Path := '';
    AppPath := ExpandConstant('{app}');
    if Pos(AppPath, Path) = 0 then
    begin
      if (Path <> '') and (Path[Length(Path)] <> ';') then
        Path := Path + ';';
      Path := Path + AppPath;
      RegWriteStringValue(HKLM, 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 'Path', Path);
      Log('Added install folder to system PATH.');
    end;
  except
    Log('AddToPath failed.');
  end;
end;

procedure RemoveFromPath();
var
  Path, NewPath, Seg: String;
  I, Start: Integer;
begin
  try
    if not RegQueryStringValue(HKLM, 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 'Path', Path) then
      Exit;
    // Drop every PATH segment mentioning EduPlay (this installer only ever
    // adds its own folder). Needs neither {app} nor uninstall keys, so it
    // also runs clean when [Code] executes outside setup context
    // (IDE debugger), where ExpandConstant('{app}') would raise.
    NewPath := '';
    Start := 1;
    for I := 1 to Length(Path) + 1 do
    begin
      if (I > Length(Path)) or (Path[I] = ';') then
      begin
        Seg := Trim(Copy(Path, Start, I - Start));
        if (Seg <> '') and (Pos('EDUPLAY', Uppercase(Seg)) = 0) then
        begin
          if NewPath <> '' then
            NewPath := NewPath + ';';
          NewPath := NewPath + Seg;
        end;
        Start := I + 1;
      end;
    end;
    if NewPath <> Path then
    begin
      RegWriteStringValue(HKLM, 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 'Path', NewPath);
      Log('Removed EduPlay folder(s) from system PATH.');
    end;
  except
    Log('RemoveFromPath failed.');
  end;
end;

// ============================================================
//  Minimal JSON value reader.
//  settings.json keeps AI device auth nested as
//  "device_auth": { "device_id": ..., "device_key": ...,
//  "machine_fingerprint": ... }, so a first-occurrence
//  search for the key name is enough (keys are unique).
// ============================================================
function PosFrom(const Sub, S: String; FromIndex: Integer): Integer;
var
  Tail: String;
begin
  Result := 0;
  if FromIndex < 1 then FromIndex := 1;
  if FromIndex > Length(S) then Exit;
  Tail := Copy(S, FromIndex, Length(S) - FromIndex + 1);
  if Pos(Sub, Tail) > 0 then
    Result := Pos(Sub, Tail) + FromIndex - 1;
end;

function ExtractJsonValue(const JsonText, Key: String): String;
var
  P, Q, R, S: Integer;
  Search: String;
begin
  Result := '';
  Search := '"' + Key + '"';
  P := Pos(Search, JsonText);
  if P = 0 then Exit;
  Q := PosFrom(':', JsonText, P + Length(Search));
  if Q = 0 then Exit;
  R := PosFrom('"', JsonText, Q + 1);
  if R = 0 then Exit;
  S := PosFrom('"', JsonText, R + 1);
  if S = 0 then Exit;
  while (S > R + 1) and (JsonText[S - 1] = '\') do
  begin
    S := PosFrom('"', JsonText, S + 1);
    if S = 0 then Exit;
  end;
  Result := Copy(JsonText, R + 1, S - R - 1);
end;

function ReadDeviceAuthValue(const Key: String): String;
var
  Candidates: array[0..3] of String;
  I: Integer;
  Raw: AnsiString;
begin
  Result := '';
  Candidates[0] := ExpandConstant('{userdocs}\EduPlay\Settings\settings.json');
  Candidates[1] := ExpandConstant('{localappdata}\EduPlayStudio\settings.json');
  Candidates[2] := ExpandConstant('{localappdata}\EduPlay Studio\settings.json');
  Candidates[3] := ExpandConstant('{commonappdata}\EduPlay Studio\settings.json');
  for I := 0 to 3 do
  begin
    try
      if FileExists(Candidates[I]) and LoadStringFromFile(Candidates[I], Raw) then
      begin
        Result := ExtractJsonValue(Raw, Key);
        if Result <> '' then
        begin
          Log('Found "' + Key + '" in ' + Candidates[I]);
          Exit;
        end;
      end;
    except
    end;
  end;
end;

// ============================================================
//  Ask the AI gateway to delete this machine's row in the
//  Supabase device_bindings table. The server accepts a
//  fingerprint alone (falls back to delete-by-fingerprint),
//  but sending device_id / device_key too makes the match
//  exact. Read-only on local files; never raises.
// ============================================================
function DeleteRemoteAiBinding(): Boolean;
var
  Http: Variant;
  Fingerprint, DeviceId, DeviceKey, Body: String;
  Status: Integer;
begin
  Result := False;
  ServerDeleteState := 2;
  Fingerprint := ReadDeviceAuthValue('machine_fingerprint');
  if Fingerprint = '' then
  begin
    Log('AI device delete skipped: machine_fingerprint not found locally.');
    Exit;
  end;
  DeviceId := ReadDeviceAuthValue('device_id');
  DeviceKey := ReadDeviceAuthValue('device_key');
  Body := '{"machine_fingerprint":"' + Fingerprint + '"';
  if DeviceId <> '' then
    Body := Body + ',"device_id":"' + DeviceId + '"';
  if DeviceKey <> '' then
    Body := Body + ',"device_key":"' + DeviceKey + '"';
  Body := Body + '}';
  try
    Http := CreateOleObject('WinHttp.WinHttpRequest.5.1');
    Http.SetTimeouts(8000, 8000, 15000, 15000);
    Http.Open('POST', '{#AiGatewayUrl}/device/delete', False);
    Http.SetRequestHeader('Content-Type', 'application/json');
    Http.SetRequestHeader('X-Machine-Fingerprint', Fingerprint);
    if DeviceId <> '' then
      Http.SetRequestHeader('X-Device-Id', DeviceId);
    if DeviceKey <> '' then
      Http.SetRequestHeader('X-Device-Key', DeviceKey);
    Http.Send(Body);
    Status := Http.Status;
    Log('AI device delete: HTTP ' + IntToStr(Status));
    if (Status = 200) or (Status = 404) then
    begin
      Result := True;
      ServerDeleteState := 1;
    end;
  except
    Log('AI device delete failed (offline or server unreachable).');
  end;
end;

// ============================================================
//  PowerPoint add-in traces (created on demand by the app
//  via Settings - Add-in). Best effort, never raises.
// ============================================================
function ExtractMsiProductCode(const UninstallString: String): String;
var
  P, Q: Integer;
begin
  Result := '';
  P := Pos('{', UninstallString);
  Q := Pos('}', UninstallString);
  if (P > 0) and (Q > P) then
    Result := Copy(UninstallString, P, Q - P + 1);
end;

procedure UninstallAddinMsi();
var
  Roots: array[0..2] of Integer;
  Bases: array[0..2] of String;
  Subs: TArrayOfString;
  R, B, I: Integer;
  DisplayName, Uninst, ProductCode: String;
  Code: Integer;
begin
  Roots[0] := HKLM; Roots[1] := HKLM; Roots[2] := HKCU;
  Bases[0] := 'Software\Microsoft\Windows\CurrentVersion\Uninstall';
  Bases[1] := 'Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall';
  Bases[2] := 'Software\Microsoft\Windows\CurrentVersion\Uninstall';
  for R := 0 to 2 do
    for B := 0 to 2 do
    begin
      if (R = 0) and (B <> 0) then Continue;
      if (R = 1) and (B <> 1) then Continue;
      if (R = 2) and (B <> 2) then Continue;
      try
        if not RegGetSubkeyNames(Roots[R], Bases[B], Subs) then Continue;
        for I := 0 to GetArrayLength(Subs) - 1 do
        begin
          DisplayName := SafeRegReadString(Roots[R], Bases[B] + '\' + Subs[I], 'DisplayName');
          if Pos('{#AddinDisplayName}', DisplayName) = 0 then Continue;
          Uninst := SafeRegReadString(Roots[R], Bases[B] + '\' + Subs[I], 'UninstallString');
          ProductCode := ExtractMsiProductCode(Uninst);
          if ProductCode = '' then Continue;
          Log('Uninstalling add-in MSI ' + ProductCode);
          Exec('msiexec.exe', '/x ' + ProductCode + ' /qn /norestart', '', SW_HIDE, ewWaitUntilTerminated, Code);
        end;
      except
      end;
    end;
end;

procedure RemoveOfficeAddinRegistration();
var
  Names: TArrayOfString;
  I: Integer;
  Url, AddinName: String;
begin
  SafeDeleteRegTree(HKCU, 'Software\Microsoft\Office\PowerPoint\Addins\{#AddinKeyName}');
  try
    RegDeleteValue(HKCU, 'Software\Microsoft\Office\16.0\PowerPoint\Resiliency\DoNotDisableAddinList', '{#AddinKeyName}');
  except
  end;
  try
    RegDeleteValue(HKCU, 'Software\Microsoft\Office\15.0\PowerPoint\Resiliency\DoNotDisableAddinList', '{#AddinKeyName}');
  except
  end;
  SafeDeleteRegTree(HKCU, 'Software\EduPlayPowerPointAddin');
  // Sweep stale VSTO SolutionMetadata entries of this add-in
  try
    if RegGetSubkeyNames(HKCU, 'Software\Microsoft\VSTO\SolutionMetadata', Names) then
      for I := 0 to GetArrayLength(Names) - 1 do
      begin
        AddinName := SafeRegReadString(HKCU, 'Software\Microsoft\VSTO\SolutionMetadata\' + Names[I], 'addInName');
        Url := SafeRegReadString(HKCU, 'Software\Microsoft\VSTO\SolutionMetadata\' + Names[I], '');
        if (AddinName = '{#AddinKeyName}') or (Pos('{#AddinKeyName}', Url) > 0) then
        begin
          Log('Removing stale VSTO SolutionMetadata: ' + Names[I]);
          SafeDeleteRegTree(HKCU, 'Software\Microsoft\VSTO\SolutionMetadata\' + Names[I]);
        end;
      end;
  except
  end;
  // Sweep stale VSTO Inclusion trust entries of this add-in
  try
    if RegGetSubkeyNames(HKCU, 'Software\Microsoft\VSTO\Security\Inclusion', Names) then
      for I := 0 to GetArrayLength(Names) - 1 do
      begin
        Url := SafeRegReadString(HKCU, 'Software\Microsoft\VSTO\Security\Inclusion\' + Names[I], 'Url');
        if Pos('{#AddinKeyName}', Url) > 0 then
        begin
          Log('Removing stale VSTO Inclusion trust: ' + Names[I]);
          SafeDeleteRegTree(HKCU, 'Software\Microsoft\VSTO\Security\Inclusion\' + Names[I]);
        end;
      end;
  except
  end;
end;

// ============================================================
//  GRANULAR WIPE - each driven by one checkbox (all default OFF).
//  Local settings are read BEFORE anything is deleted, so the
//  server call always goes out first (see usPostUninstall).
// ============================================================
procedure WipeProjectsData();
var
  UserDocs: String;
begin
  try
    UserDocs := ExpandConstant('{userdocs}');
    // Whole tree only when settings go too; otherwise keep Settings/.
    if WipeSettings then
      SafeDelTree(UserDocs + '\EduPlay')
    else begin
      SafeDelTree(UserDocs + '\EduPlay\Projects');
      SafeDelTree(UserDocs + '\EduPlay\Exports');
      SafeDelTree(UserDocs + '\EduPlay\Templates');
      SafeDelTree(UserDocs + '\EduPlay\PublishCache');
    end;
    Log('Wiped projects/exports.');
  except
    Log('WipeProjectsData failed.');
  end;
end;

procedure WipeSettingsData();
var
  UserDocs, LocalAppData, RoamingAppData: String;
begin
  try
    UserDocs := ExpandConstant('{userdocs}');
    LocalAppData := ExpandConstant('{localappdata}');
    RoamingAppData := ExpandConstant('{userappdata}');
    // Documents-side settings + tokens (whole tree already gone
    // when projects are wiped together - SafeDelTree is idempotent).
    SafeDelTree(UserDocs + '\EduPlay\Settings');
    // Roaming Edubot memory (ai_memory.json) - previously missed.
    SafeDelTree(RoamingAppData + '\EduPlayStudio');
    // Local caches incl. the asset DB (eduplay.db) + AI proxy token.
    SafeDelTree(LocalAppData + '\EduPlayStudio');
    SafeDelTree(LocalAppData + '\EduPlay Studio');
    // Shared templates.
    SafeDelTree(ExpandConstant('{commonappdata}') + '\EduPlay Studio');
    Log('Wiped settings/tokens/memory/caches.');
  except
    Log('WipeSettingsData failed.');
  end;
end;

procedure WipeAddinData();
begin
  try
    // MSI package + Office/VSTO registration.
    UninstallAddinMsi();
    RemoveOfficeAddinRegistration();
    // Payload + slide caches (both historic dir names).
    SafeDelTree(ExpandConstant('{localappdata}') + '\EduPlayPowerPointAddin');
    SafeDelTree(ExpandConstant('{localappdata}') + '\EduPlayPPTAddin');
    // Add-in's own registry key (TrustedSlidesFolder) - previously missed.
    SafeDeleteRegTree(HKCU, 'Software\EduPlayPowerPointAddin');
    SafeDeleteRegTree(HKLM, 'Software\EduPlayPowerPointAddin');
    Log('Wiped PowerPoint Add-in.');
  except
    Log('WipeAddinData failed.');
  end;
end;

// ============================================================
//  ALWAYS-RUN traces - temp files, PATH, registry leftovers.
//  Runs on every uninstall, ticked or not.
// ============================================================
procedure RemoveAppTracesAlways();
var
  LocalAppData, TempDir: String;
begin
  try
    LocalAppData := ExpandConstant('{localappdata}');
    TempDir := GetEnv('TEMP');
    if TempDir = '' then
      TempDir := ExpandConstant('{tmp}');
    // Preview / updater temp.
    SafeDelTree(TempDir + '\eduplay_preview_files');
    SafeDelTree(TempDir + '\EduPlay');
    // Publish cache + runtime slide caches (pure caches, safe always).
    SafeDelTree(ExpandConstant('{userdocs}') + '\EduPlay\PublishCache');
    SafeDelTree(LocalAppData + '\EduPlayStudio\runtime_cache');
    SafeDelTree(LocalAppData + '\EduPlay Studio\runtime_cache');
    SafeDelTree(LocalAppData + '\EduPlayPowerPointAddin\TrustedSlides');
    SafeDelTree(LocalAppData + '\EduPlayPPTAddin\TrustedSlides');
    // System PATH scrub (no registry keys needed).
    RemoveFromPath();
    // Registry: publisher keys (new + legacy), file associations,
    // App Paths, uninstall keys (new + legacy). Inno removes most of
    // these itself; this is belt-and-braces for stale installs.
    SafeDeleteRegTree(HKLM, 'Software\{#AppPublisher}\{#AppName}');
    SafeDeleteRegTree(HKCU, 'Software\{#AppPublisher}\{#AppName}');
    SafeDeleteRegTree(HKLM, 'Software\{#OldPublisher}\{#AppName}');
    SafeDeleteRegTree(HKCU, 'Software\{#OldPublisher}\{#AppName}');
    SafeDeleteRegTree(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1');
    SafeDeleteRegTree(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#AppId}_is1');
    SafeDeleteRegTree(HKLM, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#LegacyUninstallKey}');
    SafeDeleteRegTree(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#LegacyUninstallKey}');
    SafeDeleteRegTree(HKCR, '.eduplay');
    SafeDeleteRegTree(HKCR, 'EduPlayProject');
    SafeDeleteRegTree(HKCU, 'Software\Classes\.eduplay');
    SafeDeleteRegTree(HKCU, 'Software\Classes\EduPlayProject');
    SafeDeleteRegTree(HKLM, 'Software\Microsoft\Windows\CurrentVersion\App Paths\{#AppExeName}');
    Log('Removed always-run traces.');
  except
    Log('RemoveAppTracesAlways failed.');
  end;
end;

// ============================================================
//  Event handlers
// ============================================================
function InitializeSetup(): Boolean;
var
  OldVersion, Question, NL: String;
  Response: Integer;
begin
  Result := True;
  CleanInstallChosen := False;
  NL := #13#10;

  if not CloseAppWithPrompt(CustomMessage('ClosePrompt')) then
  begin
    Result := False;
    Exit;
  end;

  if GetInstalledVersion() <> '' then
  begin
    OldVersion := GetInstalledVersion();
    if not WizardSilent() then
    begin
      Question := CustomMessage('OldLead') + ' ' + OldVersion + ' ' + CustomMessage('OldMid') + NL +
        NL + CustomMessage('OldYes') + NL +
        CustomMessage('OldNo') + NL +
        CustomMessage('OldCancel') + NL + NL +
        CustomMessage('OldRecomm');
      Response := MsgBox(Question, mbConfirmation, MB_YESNOCANCEL);
      case Response of
        IDYES: CleanInstallChosen := True;
        IDNO: CleanInstallChosen := False;
        else
        begin
          Result := False;
          Exit;
        end;
      end;
    end;

    if not UninstallPreviousVersion() then
    begin
      if not WizardSilent() then
        MsgBox(CustomMessage('OldUninstFail'), mbError, MB_OK);
      Result := False;
      Exit;
    end;

    // A silent old uninstaller never deletes user data, so a
    // "clean install" must wipe here - settings are still on
    // disk at this point, so the server call works.
    if CleanInstallChosen then
    begin
      Log('Clean install selected: wiping all EduPlay data.');
      // Server FIRST (settings still on disk for device_auth lookup).
      DeleteRemoteAiBinding();
      WipeProjects := True;
      WipeSettings := True;
      WipeAddin := True;
      WipeProjectsData();
      WipeSettingsData();
      WipeAddinData();
      RemoveAppTracesAlways();
      WipeProjects := False;
      WipeSettings := False;
      WipeAddin := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if WizardIsTaskSelected('addtopath') then
      AddToPath();
  end;
end;

// ============================================================
//  Uninstall options dialog - checkboxes like the install Tasks
//  page. ALL DEFAULT UNCHECKED (safe default: keep user data).
//  Works in the uninstaller (plain modal TForm, no wizard).
// ============================================================
function ShowUninstallOptionsDialog(): Boolean;
var
  Form: TForm;
  LblNote: TLabel;
  CbProjects, CbSettings, CbServer, CbAddin: TCheckBox;
  BtnGo, BtnCancel: TButton;
  Y: Integer;
begin
  Result := False;
  WipeProjects := False;
  WipeSettings := False;
  WipeServer := False;
  WipeAddin := False;
  try
    Form := TForm.Create(nil);
    try
      Form.Caption := CustomMessage('UnDlgTitle');
      Form.ClientWidth := 488;
      Form.ClientHeight := 300;
      Form.Position := poScreenCenter;
      Form.BorderStyle := bsDialog;
      LblNote := TLabel.Create(Form);
      LblNote.Parent := Form;
      LblNote.Left := 16;
      LblNote.Top := 12;
      LblNote.Width := 456;
      LblNote.Height := 56;
      LblNote.WordWrap := True;
      LblNote.Caption := CustomMessage('UnDlgNote');
      Y := 76;
      CbProjects := TCheckBox.Create(Form);
      CbProjects.Parent := Form;
      CbProjects.Left := 16; CbProjects.Top := Y; CbProjects.Width := 456;
      CbProjects.Caption := CustomMessage('UnOptProjects');
      CbProjects.Checked := False;
      Y := Y + 30;
      CbSettings := TCheckBox.Create(Form);
      CbSettings.Parent := Form;
      CbSettings.Left := 16; CbSettings.Top := Y; CbSettings.Width := 456;
      CbSettings.Caption := CustomMessage('UnOptSettings');
      CbSettings.Checked := False;
      Y := Y + 30;
      CbServer := TCheckBox.Create(Form);
      CbServer.Parent := Form;
      CbServer.Left := 16; CbServer.Top := Y; CbServer.Width := 456;
      CbServer.Caption := CustomMessage('UnOptServer');
      CbServer.Checked := False;
      Y := Y + 30;
      CbAddin := TCheckBox.Create(Form);
      CbAddin.Parent := Form;
      CbAddin.Left := 16; CbAddin.Top := Y; CbAddin.Width := 456;
      CbAddin.Caption := CustomMessage('UnOptAddin');
      CbAddin.Checked := False;
      BtnGo := TButton.Create(Form);
      BtnGo.Parent := Form;
      BtnGo.Left := 232; BtnGo.Top := 252; BtnGo.Width := 120;
      BtnGo.Caption := CustomMessage('UnBtnGo');
      BtnGo.ModalResult := mrOk;
      BtnGo.Default := True;
      BtnCancel := TButton.Create(Form);
      BtnCancel.Parent := Form;
      BtnCancel.Left := 360; BtnCancel.Top := 252; BtnCancel.Width := 112;
      BtnCancel.Caption := CustomMessage('UnBtnCancel');
      BtnCancel.ModalResult := mrCancel;
      BtnCancel.Cancel := True;
      if Form.ShowModal = mrOk then
      begin
        WipeProjects := CbProjects.Checked;
        WipeSettings := CbSettings.Checked;
        WipeServer := CbServer.Checked;
        WipeAddin := CbAddin.Checked;
        Log('Uninstall options: projects=' + IntToStr(Ord(WipeProjects)) + ' settings=' + IntToStr(Ord(WipeSettings)) + ' server=' + IntToStr(Ord(WipeServer)) + ' addin=' + IntToStr(Ord(WipeAddin)));
        Result := True;
      end;
    finally
      Form.Free;
    end;
  except
    Result := False;
  end;
end;

function InitializeUninstall(): Boolean;
begin
  Result := True;
  WipeProjects := False;
  WipeSettings := False;
  WipeServer := False;
  WipeAddin := False;
  ServerDeleteState := 0;

  if not UninstallSilent() then
  begin
    // Checkbox dialog (Cancel aborts the whole uninstall).
    if not ShowUninstallOptionsDialog() then
      Result := False;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  case CurUninstallStep of
    usUninstall:
    begin
      CloseAppWithPrompt(CustomMessage('UnClosePrompt'));
    end;

    usPostUninstall:
    begin
      // Server FIRST: DeleteRemoteAiBinding reads device_auth from
      // settings that the wipes below may delete.
      if WipeServer then
      begin
        Log('Uninstall: deleting Supabase device_bindings row first.');
        DeleteRemoteAiBinding();
      end;
      if WipeProjects then
      begin
        Log('Uninstall: wiping projects/exports.');
        WipeProjectsData();
      end;
      if WipeSettings then
      begin
        Log('Uninstall: wiping settings/tokens/memory/caches.');
        WipeSettingsData();
      end;
      if WipeAddin then
      begin
        Log('Uninstall: removing PowerPoint Add-in fully.');
        WipeAddinData();
      end;
      RemoveAppTracesAlways();
    end;
  end;
end;

procedure DeinitializeUninstall();
var
  Details: String;
begin
  Details := CustomMessage('SumTemp') + #13#10;
  if WipeProjects then
    Details := Details + CustomMessage('SumWipedProjects') + #13#10
  else
    Details := Details + CustomMessage('SumKeptProjects') + #13#10;
  if WipeSettings then
    Details := Details + CustomMessage('SumWipedSettings') + #13#10
  else
    Details := Details + CustomMessage('SumKeptSettings') + #13#10;
  if WipeAddin then
    Details := Details + CustomMessage('SumWipedAddin') + #13#10
  else
    Details := Details + CustomMessage('SumKeptAddin') + #13#10;
  if WipeServer then
  begin
    if ServerDeleteState = 1 then
      Details := Details + CustomMessage('SumServerOk')
    else
      Details := Details + CustomMessage('SumServerFail');
  end
  else
    Details := Details + CustomMessage('SumServerSkipped');

  if not UninstallSilent() then
    MsgBox(CustomMessage('SumDone') + #13#10 + #13#10 + Details, mbInformation, MB_OK);
end;
