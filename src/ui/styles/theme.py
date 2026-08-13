# -*- coding: utf-8 -*-
"""
主题样式模块 - Material Design 层级配色

深色模式：#121212 基底 + 层级提升（卡片更亮）
文字用 rgba 透明度（87%/60%/38%）而非纯白
莫奈色系强调色，降饱和提明度
"""

import os
import json

# ===== 色板配置 =====
DEFAULT_THEMES = {
    "dark": {
        "name": "深色",
        # Material Design 层级：背景越深层级越低
        "bg_primary": "#121212",      # Level 0 - 应用基底
        "bg_secondary": "#1E1E1E",    # Level 1 - 侧边栏
        "bg_tertiary": "#2A2A2A",     # Level 2 - 卡片/输入框
        # 强调色 - 莫奈睡莲蓝（降饱和提明度）
        "accent": "#82B1FF",
        "accent_hover": "#A0C4FF",
        # 文字 - 用 rgba 透明度
        "text_primary": "rgba(255, 255, 255, 0.87)",
        "text_secondary": "rgba(255, 255, 255, 0.60)",
        "text_inverse": "#121212",
        "border": "#3A3A3A",
        "success": "#A5D6A7",
        "warning": "#FFCC80",
        "error": "#EF9A9A",
        "button_primary": "#82B1FF",
        "button_primary_hover": "#A0C4FF",
        "button_secondary": "#2A2A2A",
        "button_secondary_hover": "#3A3A3A",
        # 图标颜色
        "icon_color": "#D0D5E0",
    },
    "light": {
        "name": "浅色",
        # 莫奈风格浅色系：不是纯白，而是温暖的米白+柔和浅灰（不刺眼）
        "bg_primary": "#F7F5F2",      # 米白色背景（莫奈画布的底色）
        "bg_secondary": "#FBF9F6",    # 侧边栏略暖
        "bg_tertiary": "#FFFFFF",     # 卡片纯白但边框柔和
        # 强调色 - 莫奈雾蓝色（比dark模式浅一两个色度）
        "accent": "#7AA6DC",
        "accent_hover": "#5B93D0",
        # 文字 - 不是纯黑，而是柔和深灰（避免刺眼）
        "text_primary": "rgba(55, 58, 68, 0.90)",
        "text_secondary": "rgba(55, 58, 68, 0.60)",
        "text_inverse": "#FFFFFF",
        "border": "#DDE3EA",          # 柔和冷灰边框
        "success": "#5FA777",
        "warning": "#E0A864",
        "error": "#D96E6E",
        "button_primary": "#7AA6DC",
        "button_primary_hover": "#5B93D0",
        "button_secondary": "#EEF1F4",
        "button_secondary_hover": "#DDE3EA",
        "icon_color": "#4A4F5E",
    },
}

# ===== 莫奈调色盘 =====
PRESET_COLORS = [
    {"name": "睡莲蓝", "color": "#82B1FF"},
    {"name": "晨雾紫", "color": "#B39DDB"},
    {"name": "睡莲绿", "color": "#A5D6A7"},
    {"name": "日落玫瑰", "color": "#EF9A9A"},
    {"name": "麦田金", "color": "#FFCC80"},
    {"name": "雾凇青", "color": "#80CBC4"},
    {"name": "鸢尾蓝", "color": "#90CAF9"},
    {"name": "干草堆", "color": "#D7CCC8"},
    {"name": "日式桥", "color": "#A5D6A7"},
    {"name": "黄昏粉", "color": "#F48FB1"},
]


def _get_config_path():
    """获取主题配置文件路径"""
    if os.name == 'nt':
        base = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "LocalToolbox")
    else:
        base = os.path.join(os.path.expanduser("~"), ".localtoolbox")
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        pass
    return os.path.join(base, "theme_config.json")


def load_theme_config():
    """加载主题配置"""
    path = _get_config_path()
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"current_theme": "dark", "custom_accent": None}


def save_theme_config(config: dict):
    """保存主题配置"""
    path = _get_config_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def get_theme_colors(theme_name: str, custom_accent: str = None) -> dict:
    """获取主题颜色"""
    if theme_name not in DEFAULT_THEMES:
        theme_name = "dark"
    colors = dict(DEFAULT_THEMES[theme_name])
    if custom_accent:
        colors["accent"] = custom_accent
        colors["button_primary"] = custom_accent
        hover = _lighten_color(custom_accent, 1.15)
        colors["accent_hover"] = hover
        colors["button_primary_hover"] = hover
    return colors


def _darken_color(color_hex: str, factor: float) -> str:
    c = color_hex.lstrip('#')
    r = int(int(c[0:2], 16) * factor)
    g = int(int(c[2:4], 16) * factor)
    b = int(int(c[4:6], 16) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


def _lighten_color(color_hex: str, factor: float) -> str:
    c = color_hex.lstrip('#')
    r = min(255, int(int(c[0:2], 16) * factor))
    g = min(255, int(int(c[2:4], 16) * factor))
    b = min(255, int(int(c[4:6], 16) * factor))
    return f"#{r:02x}{g:02x}{b:02x}"


def _rgba(color_hex: str, opacity: float) -> str:
    c = color_hex.lstrip('#')
    r = int(c[0:2], 16)
    g = int(c[2:4], 16)
    b = int(c[4:6], 16)
    return f"rgba({r}, {g}, {b}, {opacity})"


def _mix_color(color_a: str, color_b: str, ratio_a: float = 0.5) -> str:
    """按比例混合两个颜色。用于强调色联动背景色，视觉色调统一。"""
    ratio_b = 1.0 - ratio_a
    a = color_a.lstrip('#')
    b = color_b.lstrip('#')
    ar, ag, ab = int(a[0:2], 16), int(a[2:4], 16), int(a[4:6], 16)
    br, bg, bb = int(b[0:2], 16), int(b[2:4], 16), int(b[4:6], 16)
    r = min(255, int(ar * ratio_a + br * ratio_b))
    g = min(255, int(ag * ratio_a + bg * ratio_b))
    bl = min(255, int(ab * ratio_a + bb * ratio_b))
    return f"#{r:02x}{g:02x}{bl:02x}"


def _tint_color(base_hex: str, tint_hex: str, tint_alpha: float) -> str:
    """
    计算「纯色 base_hex 上面叠一层 tint_hex × tint_alpha 透明度」后的最终等效纯色。
    替代 QSS 的 rgba()，避免 Qt 样式合成时透出父级背景而出现"阴间色"。
    """
    return _mix_color(tint_hex, base_hex, tint_alpha)


def get_theme_colors(theme_name: str, custom_accent: str = None) -> dict:
    """获取主题颜色 - 有custom_accent时背景层级也往强调色偏，整体视觉不割裂"""
    if theme_name not in DEFAULT_THEMES:
        theme_name = "dark"
    colors = dict(DEFAULT_THEMES[theme_name])
    if custom_accent:
        colors["accent"] = custom_accent
        colors["button_primary"] = custom_accent
        hover = _lighten_color(custom_accent, 1.15)
        colors["accent_hover"] = hover
        colors["button_primary_hover"] = hover
        # 强调色联动：背景混5%~8%的强调色，让整体色调跟着调色盘走
        mix = 0.08 if theme_name == "dark" else 0.06
        colors["bg_primary"]   = _mix_color(custom_accent, colors["bg_primary"],   mix)
        colors["bg_secondary"] = _mix_color(custom_accent, colors["bg_secondary"], mix)
        colors["bg_tertiary"]  = _mix_color(custom_accent, colors["bg_tertiary"],  mix * 0.7)
    return colors


def generate_stylesheet(theme_name: str, custom_accent: str = None) -> str:
    """
    生成统一来源的 QSS - 所有层级颜色都从 get_theme_colors 返回的字典派生
    （调色盘设置 custom_accent 会联动改变 bg_* 背景色，整体色调一致）
    """
    c = get_theme_colors(theme_name, custom_accent)
    dark = theme_name == "dark"

    # 所有层级统一派生
    # hover/selected 统一用「强调色+低透明度」叠在原始卡片背景上，
    # 避免对近白/近黑颜色做"明暗系数"乘法时出现截断0或不变的"阴间色"bug。
    base_bg = c["bg_primary"]
    # 按钮文字色：深色背景用深色字（按钮是亮色雾蓝/绿所以压深色字）；浅色背景用白色字
    btn_text_on_accent = "#1A1A1A" if dark else "#FFFFFF"
    card_bg = c["bg_tertiary"]

    if dark:
        card_hover      = _tint_color(card_bg, c["accent"], 0.14)
        card_selected   = _tint_color(card_bg, c["accent"], 0.22)
        input_bg        = c["bg_secondary"]
        header_bg       = _lighten_color(base_bg, 1.20)
        sidebar_bg      = _lighten_color(base_bg, 1.06)
        nav_hover       = _tint_color(sidebar_bg, c["accent"], 0.10)
        nav_selected    = _tint_color(sidebar_bg, c["accent"], 0.20)
        border_color    = _rgba("#FFFFFF", 0.08)
        border_hover    = _tint_color("#888888", c["accent"], 0.40)
        btn_secondary_bg    = header_bg
        btn_secondary_hover = _tint_color(header_bg, c["accent"], 0.22)
    else:
        # 浅色模式：所有 hover/selected 都算出等效纯色，不再依赖 Qt 合成
        card_hover      = _tint_color(card_bg, c["accent"], 0.14)
        card_selected   = _tint_color(card_bg, c["accent"], 0.20)
        input_bg        = c["bg_tertiary"]
        header_bg       = _darken_color(base_bg, 0.97)
        sidebar_bg      = c["bg_secondary"]
        nav_hover       = _tint_color(sidebar_bg, c["accent"], 0.10)
        nav_selected    = _tint_color(sidebar_bg, c["accent"], 0.20)
        border_color    = c["border"]
        border_hover    = _tint_color("#AAB0BA", c["accent"], 0.55)
        btn_secondary_bg    = c["button_secondary"]
        btn_secondary_hover = _tint_color(c["button_secondary"], c["accent"], 0.18)

    return f"""
/* ===== 全局：背景继承链 =====
   所有容器默认继承父级背景；只有带objectName/明确选择器的才覆盖
*/
* {{
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 14px;
    color: {c['text_primary']};
}}

QMainWindow {{ background-color: {base_bg}; }}
/* 经验1395153：QStackedWidget/QScrollArea/viewport 是最常见的"背景没切换"元凶
   必须显式给它们设背景色，否则会残留黑色默认viewport */
QStackedWidget, QWidget#centralWidget {{ background-color: {base_bg}; }}
QScrollArea {{ background-color: {base_bg}; border: none; }}
QScrollArea > QWidget > QWidget {{ background-color: {base_bg}; }}  /* viewport */
QAbstractScrollArea, QAbstractItemView {{ background-color: {base_bg}; }}

QWidget {{ background-color: {base_bg}; color: {c['text_primary']}; }}
QLabel {{ background: transparent; color: {c['text_primary']}; }}

/* 工具卡片、FileDropArea、GroupBox需要独立背景的控件，用自身选择器覆盖 */
QFrame#toolCard, QWidget#fileDropArea, QGroupBox {{
    background-color: {card_bg};
}}

/* ===== 侧边栏 ===== */
QWidget#sidebar {{
    background-color: {sidebar_bg};
    border-right: 1px solid {border_color};
}}

QLabel#sidebarTitle {{
    color: {c['text_primary']};
    font-size: 20px;
    font-weight: bold;
    background: transparent;
}}

/* 侧边栏导航项 */
QListWidget#navList {{
    background-color: transparent;
    border: none;
    padding: 8px 10px;
    outline: none;
    font-size: 15px;
    color: {c['text_primary']};
}}

QListWidget#navList::item {{
    padding: 14px 18px;
    border-radius: 10px;
    margin: 2px 0;
    border: 1px solid transparent;
    color: {c['text_primary']};
}}

QListWidget#navList::item:selected {{
    background-color: {nav_selected};
    border: 1px solid {border_hover};
    color: {c['text_primary']};
}}

QListWidget#navList::item:hover {{
    background-color: {nav_hover};
}}

/* ===== 滚动条 ===== */
QScrollArea {{ border: none; background-color: transparent; }}

QScrollBar:vertical {{
    background: transparent; width: 8px; border-radius: 4px; margin: 4px 2px;
}}
QScrollBar::handle:vertical {{
    background: {_rgba(c['border'] if dark else '#CCCCCC', 0.5 if dark else 0.6)};
    border-radius: 4px; min-height: 40px;
}}
QScrollBar::handle:vertical:hover {{ background: {c['accent']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QScrollBar:horizontal {{
    background: transparent; height: 8px; border-radius: 4px; margin: 0 4px;
}}
QScrollBar::handle:horizontal {{
    background: {_rgba(c['border'] if dark else '#CCCCCC', 0.5 if dark else 0.6)};
    border-radius: 4px; min-width: 40px;
}}
QScrollBar::handle:horizontal:hover {{ background: {c['accent']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ===== 文件拖拽区域 - 圆角边框 ===== */
QWidget#fileDropArea {{
    background-color: {_rgba(c['accent'], 0.06 if dark else 0.08)};
    border: 2px dashed {_rgba(c['accent'], 0.3 if dark else 0.35)};
    border-radius: 14px;
}}
QWidget#fileDropArea:hover {{
    background-color: {_rgba(c['accent'], 0.10 if dark else 0.12)};
    border: 2px dashed {_rgba(c['accent'], 0.5)};
}}
QWidget#fileDropArea[dragging="true"] {{
    background-color: {_rgba(c['accent'], 0.15 if dark else 0.18)};
    border: 2px solid {c['accent']};
}}

/* ===== 工具卡片 - 实色背景，比主背景亮 ===== */
QFrame#toolCard {{
    background-color: {card_bg};
    border: 1px solid {border_color};
    border-radius: 12px;
    padding: 4px;
}}

QFrame#toolCard:hover {{
    border: 1px solid {border_hover};
    background-color: {card_hover};
}}

QFrame#toolCard[selected="true"] {{
    border: 1px solid {_rgba(c['accent'], 0.6)};
    background-color: {card_selected};
}}

/* ===== 通用按钮 ===== */
QPushButton {{
    background-color: {btn_secondary_bg};
    color: {c['text_primary']};
    border: 1px solid {border_color};
    border-radius: 10px;
    padding: 10px 22px;
    min-height: 22px;
}}

QPushButton:hover {{
    background-color: {btn_secondary_hover};
    border: 1px solid {border_hover};
    color: {c['accent']};
}}

QPushButton:pressed {{
    background-color: {card_hover if dark else btn_secondary_hover};
}}

QPushButton:disabled {{
    background-color: {_rgba(c['border'], 0.15 if dark else 0.1)};
    color: {c['text_secondary']};
    border: 1px solid transparent;
}}

/* 主按钮 */
QPushButton#primaryBtn {{
    background-color: {c['button_primary']};
    color: {btn_text_on_accent};
    border: none;
    border-radius: 12px;
    padding: 12px 32px;
    min-height: 26px;
    font-size: 14px;
    font-weight: bold;
}}

QPushButton#primaryBtn:hover {{
    background-color: {c['button_primary_hover']};
}}

QPushButton#primaryBtn:pressed {{
    background-color: {_darken_color(c['button_primary'], 0.88)};
}}

QPushButton#primaryBtn:disabled {{
    background-color: {_rgba(c['border'], 0.2)};
    color: {_rgba(btn_text_on_accent, 0.4)};
}}

/* ===== 拖拽区域 ===== */
QFileDropArea {{
    background-color: {card_bg};
    border: 2px dashed {border_color};
    border-radius: 14px;
}}

QFileDropArea[dragging="true"] {{
    border: 2px dashed {c['accent']};
    background-color: {_rgba(c['accent'], 0.06)};
}}

/* ===== 底部「展开操作区」入口按钮 ===== */
QPushButton#expandBtn {{
    background-color: {_tint_color(base_bg, c['accent'], 0.10)};
    color: {c['accent']};
    border: 1px solid {_rgba(c['accent'], 0.35 if dark else 0.30)};
    border-radius: 21px;
    padding: 8px 30px;
    font-size: 13px;
    font-weight: bold;
}}
QPushButton#expandBtn:hover {{
    background-color: {_tint_color(base_bg, c['accent'], 0.18)};
    border: 1px solid {_rgba(c['accent'], 0.6)};
}}
QPushButton#expandBtn:pressed {{
    background-color: {_tint_color(base_bg, c['accent'], 0.26)};
}}

/* ===== 操作面板（底部抽屉）- 不透明层级背景，避免与底部内容混为一体 ===== */
QWidget#operationPanel {{
    background-color: {_lighten_color(base_bg, 1.16) if dark else card_bg};
    border: 1px solid {border_color};
    border-radius: 14px;
    padding: 14px;
}}

/* 面板顶部拖拽手柄 - 悬浮高亮提示可上下拖动调整面板高度 */
QWidget#panelDragHandle {{
    background: transparent;
    border: none;
}}
QWidget#panelDragHandle:hover {{
    background: {_rgba(c['accent'], 0.22 if dark else 0.28)};
    border-radius: 4px;
}}

/* 面板标题 - 强调色，与普通文字区分 */
QLabel#panelTitle {{
    color: {c['accent']};
    font-weight: bold;
    background: transparent;
}}

/* 面板右上角「收起」按钮 - 强调色边框，与普通按钮区分 */
QPushButton#panelCollapseBtn {{
    background-color: {_tint_color(card_bg, c['accent'], 0.08)};
    color: {c['accent']};
    border: 1px solid {_rgba(c['accent'], 0.40 if dark else 0.35)};
    border-radius: 15px;
    padding: 4px 16px;
    font-size: 12px;
    font-weight: bold;
}}
QPushButton#panelCollapseBtn:hover {{
    background-color: {_tint_color(card_bg, c['accent'], 0.16)};
    border: 1px solid {c['accent']};
}}
QPushButton#panelCollapseBtn:pressed {{
    background-color: {_tint_color(card_bg, c['accent'], 0.24)};
}}

/* 窗口右上角浮动「收起操作区」按钮 */
QPushButton#floatCollapseBtn {{
    background-color: {_tint_color(card_bg, c['accent'], 0.08)};
    color: {c['accent']};
    border: 1px solid {_rgba(c['accent'], 0.40 if dark else 0.35)};
    border-radius: 14px;
    padding: 4px 16px;
    font-size: 12px;
    font-weight: bold;
}}
QPushButton#floatCollapseBtn:hover {{
    background-color: {_tint_color(card_bg, c['accent'], 0.16)};
    border: 1px solid {c['accent']};
}}
QPushButton#floatCollapseBtn:pressed {{
    background-color: {_tint_color(card_bg, c['accent'], 0.24)};
}}

QLabel#hintLabel {{
    background-color: {_tint_color(card_bg, c['accent'], 0.10 if dark else 0.08)};
    color: {c['text_secondary']};
    border: 1px solid {_rgba(c['accent'], 0.25)};
    border-radius: 10px;
    padding: 8px 16px;
    font-size: 13px;
}}

/* 依赖缺失提示条 - 警示色（warning），与普通提示条区分 */
QLabel#envHintLabel {{
    background-color: {_tint_color(card_bg, c['warning'], 0.12 if dark else 0.10)};
    color: {c['warning']};
    border: 1px solid {_rgba(c['warning'], 0.45)};
    border-radius: 10px;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: bold;
}}

/* ===== 进度条 ===== */
QProgressBar {{
    background-color: {_rgba(c['border'], 0.2)};
    border: none; border-radius: 8px; height: 16px;
}}
QProgressBar::chunk {{
    background-color: {c['accent']}; border-radius: 8px;
}}

/* ===== 滑块 ===== */
QSlider::groove:horizontal {{
    border: none;
    height: 10px;
    background: {_rgba(c['border'], 0.3)};
    border-radius: 5px;
}}
QSlider::sub-page:horizontal {{
    background: {c['accent']};
    border-radius: 5px;
}}
QSlider::handle:horizontal {{
    background: {c['accent']};
    border: 3px solid {card_bg if dark else '#FFFFFF'};
    width: 22px;
    height: 22px;
    margin: -7px 0;
    border-radius: 11px;
}}
QSlider::handle:horizontal:hover {{
    background: {c['accent_hover']};
}}

/* ===== 输入框 ===== */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {{
    background-color: {input_bg};
    border: 1px solid {border_color};
    border-radius: 10px;
    padding: 8px 14px;
    color: {c['text_primary']};
    selection-background-color: {c['accent']};
    selection-color: {btn_text_on_accent};
    min-height: 22px;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus {{
    border: 1px solid {c['accent']};
}}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background-color: {c['bg_tertiary']};
    border: 1px solid {border_color};
    selection-background-color: {c['accent']};
    selection-color: {btn_text_on_accent};
    outline: none; padding: 4px;
}}

/* ===== 表格 ===== */
QTableWidget {{
    background-color: {card_bg};
    gridline-color: {border_color};
    border: 1px solid {border_color};
    border-radius: 10px;
    outline: none;
}}
QTableWidget::item {{
    padding: 10px 8px;
    border-bottom: 1px solid {border_color};
}}
QTableWidget::item:selected {{
    background-color: {_rgba(c['accent'], 0.15)};
}}
QHeaderView::section {{
    background-color: {header_bg};
    color: {c['text_primary']};
    padding: 10px 8px;
    border: none;
    border-bottom: 1px solid {border_color};
    font-weight: bold;
}}

/* ===== 消息框 ===== */
QMessageBox {{ background-color: {c['bg_primary']}; }}
QMessageBox QLabel {{ color: {c['text_primary']}; }}
QMessageBox QPushButton {{
    background-color: {c['button_primary']};
    color: {btn_text_on_accent}; border: none; border-radius: 8px;
    padding: 10px 24px; font-weight: bold; min-width: 80px; min-height: 22px;
}}
QMessageBox QPushButton:hover {{ background-color: {c['button_primary_hover']}; }}

/* ===== 状态栏 ===== */
QStatusBar {{
    background-color: {sidebar_bg};
    color: {c['text_secondary']};
    border-top: 1px solid {border_color};
}}

/* ===== 分组框 ===== */
QGroupBox {{
    border: 1px solid {border_color};
    border-radius: 12px;
    margin-top: 18px;
    padding: 18px 14px 14px 14px;
    color: {c['text_primary']};
    background-color: transparent;
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin; left: 14px; padding: 0 8px;
}}

/* ===== 复选框 ===== */
QCheckBox {{ spacing: 8px; color: {c['text_primary']}; min-height: 24px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px; border-radius: 5px;
    border: 1px solid {_rgba(c['border'], 0.6 if dark else 0.4)};
    background-color: {input_bg};
}}
QCheckBox::indicator:checked {{
    background-color: {c['accent']}; border-color: {c['accent']};
}}

/* ===== 选项卡 ===== */
QTabWidget::pane {{
    border: 1px solid {border_color}; border-radius: 10px;
    top: -1px; background-color: transparent;
}}
/* 扁平 Material 风格 Tab：选中项用强调色下划线，无凸起遮挡分割线 */
QTabBar::tab {{
    background: transparent;
    color: {c['text_secondary']};
    padding: 10px 22px;
    margin-right: 4px;
    border: none;
    border-bottom: 2px solid transparent;
    min-height: 22px;
}}
QTabBar::tab:selected {{ color: {c['accent']}; border-bottom: 2px solid {c['accent']}; font-weight: bold; }}
QTabBar::tab:hover:!selected {{ color: {c['text_primary']}; }}

/* ===== 工具提示 ===== */
QToolTip {{
    background-color: {c['bg_tertiary']};
    color: {c['text_primary']};
    border: 1px solid {border_color};
    padding: 6px 10px; border-radius: 8px;
}}

/* ===== 对话框 ===== */
QDialog {{ background-color: {c['bg_primary']}; }}
"""


# 向后兼容
DARK_QSS = generate_stylesheet("dark", None)
LIGHT_QSS = generate_stylesheet("light", None)
COLOR_THEMES = DEFAULT_THEMES
