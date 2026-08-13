# -*- coding: utf-8 -*-
"""
程序入口模块

负责程序的启动流程：
1. 检查是否首次运行
2. 如果是首次运行，显示欢迎向导
3. 创建并显示主窗口
"""

import sys
import os

# 添加项目根目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import Qt

from src.ui.main_window import MainWindow
from src.ui.welcome_dialog import WelcomeDialog


def _get_config_dir():
    """
    获取配置文件存储目录

    优先使用 %APPDATA%/LocalToolbox，如无权限则回退到用户主目录
    """
    candidates = []

    if sys.platform == "win32":
        # 优先使用 APPDATA
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidates.append(os.path.join(appdata, "LocalToolbox"))
        # 回退到 LOCALAPPDATA
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            candidates.append(os.path.join(localappdata, "LocalToolbox"))
        # 最后回退到用户主目录
        candidates.append(os.path.join(os.path.expanduser("~"), ".localtoolbox"))
    else:
        candidates.append(os.path.join(os.path.expanduser("~"), ".localtoolbox"))

    # 尝试创建目录，失败则尝试下一个路径
    for config_dir in candidates:
        try:
            os.makedirs(config_dir, exist_ok=True)
            # 测试是否可写
            test_file = os.path.join(config_dir, ".write_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            return config_dir
        except (PermissionError, OSError):
            continue

    # 所有路径都失败，使用临时目录
    import tempfile
    config_dir = os.path.join(tempfile.gettempdir(), "LocalToolbox")
    os.makedirs(config_dir, exist_ok=True)
    return config_dir


def _check_first_run():
    """
    检查是否首次运行

    Returns:
        True 表示环境已就绪（非首次或依赖已安装）
        False 表示需要显示欢迎向导
    """
    # 在冻结环境中(PyInstaller打包)，直接返回True跳过欢迎向导
    if getattr(sys, 'frozen', False):
        # 尝试保存一次配置，确保下次不会再弹出
        try:
            _save_first_run_done()
        except Exception:
            pass
        return True

    config_file = os.path.join(_get_config_dir(), "app_config.json")

    # 尝试读取配置文件
    if os.path.isfile(config_file):
        try:
            import json
            with open(config_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if not cfg.get("first_run", True):
                    return True
        except Exception:
            pass

    # 检查依赖状态
    from src.core.dependency_manager import check_all_dependencies
    status = check_all_dependencies()
    return status["all_essential_ok"]


def _save_first_run_done():
    """保存首次运行完成状态"""
    config_file = os.path.join(_get_config_dir(), "app_config.json")
    try:
        import json
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump({"first_run": False, "version": "1.3.8"}, f, indent=2)
    except Exception:
        pass


def main():
    """主函数"""
    # 启用高 DPI 支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # 创建应用实例
    app = QApplication(sys.argv)
    app.setApplicationName("满木工具箱")
    app.setOrganizationName("满木工具箱")
    app.setStyle("Fusion")

    # 检查首次运行
    env_ready = _check_first_run()

    # 如果环境未就绪，显示欢迎向导
    if not env_ready:
        dialog = WelcomeDialog()
        if dialog.exec() != QDialog.Accepted:
            sys.exit(0)
        _save_first_run_done()

    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
