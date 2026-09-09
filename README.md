# 满木工具箱 (LocalToolbox)

一个纯本地运行的 Windows 桌面工具箱，集成 33 个实用工具，覆盖 PDF / 图片 / 文档 / 文件 / 二维码 / 媒体 / 实用转换七大分类。基于 PySide6 构建，插件化架构，支持离线使用。

- 当前版本：**v1.3.9**
- 技术栈：Python 3.11+ · PySide6 · PyMuPDF · PyInstaller (onefile)
- 仓库：https://github.com/alloverzyt/manmulocoolbox

---

## 📌 文档维护规则（后续开发者必读）

> 本 README 是项目的**唯一交接入口**。任何人（人或 AI 助手）接手开发时，必须遵守以下规则，保证项目可持续演进。

### 1. 改动代码后必须同步的内容

| 改动类型 | 必须同步的位置 |
|---|---|
| 修复 bug / 新功能 | [CHANGELOG.md](CHANGELOG.md) 新增版本条目（格式：`## v1.x.x（日期）` + 修复/新增/优化小节） |
| 版本号升级 | 见下方「版本号联动清单」，**9 处缺一不可** |
| 新增插件 | ① 在 `src/plugins/<分类>/` 新建文件 ② 在 `config/plugin_config.json` 注册 ③ 更新下方「功能总览」表 ④ 在 `verify_all_plugins.py` 补充测试构造（如需特殊输入） |
| 新增外部依赖 | `src/core/dependency_manager.py` 添加下载源配置（先探测后选择机制），并在 CHANGELOG 说明 |

### 2. 版本号联动清单（升级版本时逐项修改）

1. `LocalToolbox.spec` → `name='满木工具箱_v1.x.x'`
2. `build.py` → `exe = 'dist/满木工具箱_v1.x.x.exe'`
3. `do_build.py` → 产物位置打印
4. `setup_and_build.py` → `exe_path`
5. `version_info.txt` → FileVersion / ProductVersion / OriginalFilename
6. `满木工具箱_setup.iss` → `#define MyAppVersion "1.x.x"`
7. `src/main.py` → `_save_first_run_done()` 中的 `version`
8. `src/ui/dialogs/about_dialog.py` → `APP_VERSION`
9. `CHANGELOG.md` → 新版本条目

### 3. 提交与发布规范

- 提交信息：`feat: vX.X.X 描述` / `fix: vX.X.X 描述` / `docs: 描述`，中文，说明「为什么」
- 发布：`python _publish_release.py vX.X.X`（从 version_info.txt 读版本号打 tag；GitHub Release 资产名用 ASCII：`FullWoodToolbox_vX.X.X.exe`）
- **每次改动后必须跑回归**：`python verify_all_plugins.py`，全部 PASS（或仅 NEEDS_ENV）才算完成

### 4. 架构硬约束（违反必踩坑）

- **插件动态导入**：`PluginManager` 用 importlib 按 `src.plugins.<分类>.<文件名>` 导入，插件文件**不能以 `_` 开头**；PyInstaller spec 已自动 walk 插件目录生成 hiddenimports，无需手动登记
- **多文件工具**：需要"同时看到所有文件"的插件（合并/比对类）必须设 `process_files_together = True`，否则 TaskWorker 会逐文件调用导致只收到 1 个文件
- **依赖拦截**：依赖外部工具（LibreOffice/FFmpeg）或可选库的插件必须实现 `check_environment()`，否则用户能拖文件但一运行就报错
- **纯参数工具**：时间戳/颜色转换等无文件工具设 `requires_files = False`，UI 才不强制拖放
- **打包版 pip**：`pip/setuptools/wheel` 必须在 spec 的 hiddenimports 中（曾因放入 excludes 导致打包版依赖安装全失败）
- **PYTHONHOME 污染**：onefile 启动时清理 `PYTHONHOME/PYTHONPATH/_MEIPASS2`（见 `src/main.py`），子进程 Python 才能正常启动；新增子进程调用务必用干净 env
- **体积 vs 功能**：spec excludes 中 pandas/openpyxl/rembg/onnxruntime 是有意排除的（rembg 需联网下模型，打包版显示"未安装"），勿盲目移除或加回；pdf2docx/numpy/cv2 是用户明确要求保留的
- **外部工具下载**：必须走「先并发探测源可达性 → 列出可用源 → 用户选择」流程，不要盲目顺序重试

---

## 功能总览（33 个工具 · 7 大分类）

| 分类 | 工具 |
|---|---|
| 📄 PDF处理 | PDF转图片、PDF合并、PDF拆分、PDF压缩、PDF水印、PDF加密解密、PDF提取 |
| 🖼️ 图片处理 | 格式转换、批量压缩、按大小压缩（二分搜索逼近目标体积）、图片转PDF、去除背景*、EXIF管理、SVG转PNG、图片OCR（规划中） |
| 📊 文档转换 | PPT转图片、Word转PDF、PDF转Word、Excel转PDF、Markdown转换 |
| 📁 文件工具 | 批量重命名、重复文件查找、哈希校验、文件整理、格式识别 |
| 🔲 二维码 | 生成二维码、识别二维码 |
| 🎬 媒体工具 | 视频转GIF、提取音频、音频格式转换 |
| 🔧 实用工具 | JSON/CSV/YAML互转、时间戳转换、颜色转换器 |

\* 「去除背景」依赖 rembg（需联网下载模型），仅在源码版可用，打包版显示「未安装」。

**通用体验**：整页拖放 + 批量处理、异步任务（QThread）不卡 UI、Material 深色 / 莫奈暖白浅色主题、调色盘自定义主题色、首次启动欢迎向导、依赖管理页（未装依赖的工具会被红色警示拦截）。

## 项目结构

```
LocalToolbox/
├── run.py                  # 源码启动入口
├── src/
│   ├── main.py             # 程序入口（环境变量清理、首次运行向导）
│   ├── core/               # 核心：plugin_interface / plugin_manager / task_worker / dependency_manager / events
│   ├── plugins/            # 插件目录，按分类组织（pdf/image/document/file/qrcode/media/utility）
│   ├── ui/                 # 界面：main_window、pages、widgets（icon_drawer 简笔画图标体系）、dialogs、styles
│   └── utils/              # ffmpeg_helper / libreoffice_helper / tool_downloader / file_utils
├── config/plugin_config.json   # 分类与插件注册表（enabled 开关）
├── resources/              # 图标、logo、内置 ffmpeg
├── LocalToolbox.spec       # PyInstaller 打包配置（onefile、Qt 瘦身、防误报）
├── build.py / do_build.py  # 一键打包脚本
├── 满木工具箱_setup.iss    # Inno Setup 安装包脚本
├── verify_all_plugins.py   # 全插件实操回归验证
├── ui_verify_all.py        # UI 全流程验证
├── _publish_release.py     # GitHub Release 发布脚本
└── CHANGELOG.md            # 更新日志（交接必读）
```

## 快速开始（源码运行）

```bash
# 1. 安装 Python 3.11+（Windows，勾选 Add to PATH）
# 2. 安装依赖
pip install -r requirements.txt
# 3. 启动
python run.py
```

首次启动会显示欢迎向导并自动检测依赖；LibreOffice（文档转换类）与 FFmpeg（媒体类）可在应用内「依赖管理页」一键下载（多源探测，国内含腾讯云镜像）。

## 打包与发布

```bash
# 打包单文件 EXE（onefile，产物：dist/满木工具箱_v1.3.9.exe）
python build.py

# 或仅执行 PyInstaller
python do_build.py

# 构建 Inno Setup 安装包
# 用 Inno Setup Compiler 打开 满木工具箱_setup.iss 编译

# 发布 GitHub Release
python _publish_release.py v1.3.9
```

打包要点（已固化在 spec 中）：onefile 模式、禁用 UPX、版本信息 + 图标防杀软误报、Qt 模块手工瘦身、ffplay/ffprobe 不打包（只保留 ffmpeg.exe）。

## 回归验证

```bash
python verify_all_plugins.py   # 为每个插件构造真实测试文件并真实执行，输出 PASS/FAIL/NEEDS_ENV 报告
python ui_verify_all.py        # UI 全流程自动化验证
```

## 更新日志

见 [CHANGELOG.md](CHANGELOG.md)——从 v1.2 到 v1.3.9 的完整演进记录，包含每个版本踩过的坑与修复根因，**接手开发前建议通读**。
