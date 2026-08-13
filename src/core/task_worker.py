import os
import sys
import json
import shutil
from typing import Optional, List

from PySide6.QtCore import QThread, Signal

from .plugin_interface import BasePlugin, PluginInput, PluginResult
from .events import EventBus


class TaskWorker(QThread):
    progress = Signal(int, str)
    completed = Signal(bool, str, str, list)  # success, message, error, output_paths
    file_completed = Signal(str, bool, str)

    def __init__(self, plugin: BasePlugin, input_data: PluginInput, parent=None):
        super().__init__(parent)
        self._plugin = plugin
        self._input_data = input_data
        self._cancelled = False

    def run(self):
        try:
            input_data = PluginInput(
                file_paths=self._input_data.file_paths[:],
                options=self._input_data.options.copy()
            )
            total = len(input_data.file_paths)
            output_dir = input_data.options.get("output_dir", "")

            all_outputs = []
            errors = []

            # 环境/输入校验（双保险：UI 已拦截，但直接 API 调用也拦得住）
            env_hint = self._plugin.check_environment()
            if env_hint:
                self.completed.emit(False, "缺少依赖", env_hint, [])
                return
            # 无文件工具（时间戳/颜色/二维码生成）不校验文件输入
            if self._plugin.requires_files:
                validate_err = self._plugin.validate_input(input_data)
                if validate_err:
                    self.completed.emit(False, "输入无效", validate_err, [])
                    return

            # 整批处理（合并/比对类工具）：一次 execute 接收全部文件，
            # 否则逐文件调用会让它们永远只看到 1 个文件
            if self._plugin.process_files_together and input_data.file_paths:
                try:
                    self.progress.emit(0, f"处理中: {total} 个文件")

                    result = self._plugin.execute(
                        input_data,
                        progress_callback=lambda p, m, t=total: self.progress.emit(p, m)
                    )

                    if result.success:
                        all_outputs.extend(result.output_paths)
                        for fp in input_data.file_paths:
                            self.file_completed.emit(fp, True, result.message)
                    else:
                        errors.append(result.error or "处理失败")
                        for fp in input_data.file_paths:
                            self.file_completed.emit(fp, False, result.error)
                except Exception as e:
                    errors.append(str(e))
                    for fp in input_data.file_paths:
                        self.file_completed.emit(fp, False, str(e))

                if errors:
                    success = len(errors) < total
                    msg = f"完成: {total - len(errors)}/{total} 成功"
                    err_msg = "\n".join(errors[:3])
                    if len(errors) > 3:
                        err_msg += f"\n... 还有 {len(errors) - 3} 个错误"
                    self.completed.emit(success, msg, err_msg, all_outputs)
                else:
                    self.completed.emit(True, f"全部完成 ({total}个文件)", "", all_outputs)
                return

            for idx, file_path in enumerate(input_data.file_paths):
                if self._cancelled:
                    break

                try:
                    self.progress.emit(
                        int((idx / max(total, 1)) * 100),
                        f"处理中: {os.path.basename(file_path)}"
                    )

                    single_input = PluginInput(
                        file_paths=[file_path],
                        options=input_data.options
                    )

                    result = self._plugin.execute(
                        single_input,
                        progress_callback=lambda p, m, i=idx, t=total: self.progress.emit(
                            int(((i + p / 100) / max(t, 1)) * 100), m
                        )
                    )

                    if result.success:
                        all_outputs.extend(result.output_paths)
                        self.file_completed.emit(file_path, True, result.message)
                    else:
                        errors.append(f"{file_path}: {result.error}")
                        self.file_completed.emit(file_path, False, result.error)

                except Exception as e:
                    errors.append(f"{file_path}: {str(e)}")
                    self.file_completed.emit(file_path, False, str(e))

            if errors:
                success = len(errors) < total
                msg = f"完成: {total - len(errors)}/{total} 成功"
                err_msg = "\n".join(errors[:3])
                if len(errors) > 3:
                    err_msg += f"\n... 还有 {len(errors) - 3} 个错误"
                self.completed.emit(success, msg, err_msg, all_outputs)
            else:
                self.completed.emit(True, f"全部完成 ({total}个文件)", "", all_outputs)

        except Exception as e:
            self.completed.emit(False, "执行失败", str(e), [])

    def cancel(self):
        self._cancelled = True
        self._plugin.cancel()
