; 满木工具箱 - Inno Setup 安装脚本
; 编译: ISCC.exe 满木工具箱_setup.iss

#define MyAppName "满木工具箱"
#define MyAppVersion "1.3.9"
; EXE 文件名 = 中文名 + 版本号（跟随 MyAppVersion 自动更新）
#define MyAppExeName "满木工具箱_v{#MyAppVersion}.exe"
#define MyAppPublisher "满木工具箱"
#define MyAppURL "https://www.cnblogs.com/alloverzyt"

[Setup]
; 应用唯一标识（请勿与其他应用重复）
AppId={{B5E2A4C1-9D8F-4E3A-B6C7-1D2E3F4A5B6C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
; 默认安装到 Program Files；以普通权限运行，不弹 UAC
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
; 卸载信息
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
; 压缩级别：极限（安装包更小，体积优化）
Compression=lzma2/max
SolidCompression=yes
; 输出
OutputDir=dist\installer
OutputBaseFilename={#MyAppName}_Setup_v{#MyAppVersion}
; 安装包图标与标题
SetupIconFile=resources\app.ico
WizardStyle=modern
; 免管理员权限安装（安装到用户目录，避免 UAC 弹窗）
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; 仅 64 位系统
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; 关闭时保持同版本可覆盖安装
CloseApplications=no

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"

[Files]
; 主程序 + 应用图标
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "resources\app.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; 开始菜单
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app.ico"; Tasks: ""
; 桌面快捷方式（可选）
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app.ico"; Tasks: desktopicon

[Run]
; 安装完成后运行（可选，静默安装时不运行）
Filename: "{app}\{#MyAppExeName}"; Description: "立即运行 {#MyAppName}"; Flags: nowait postinstall skipifsilent
