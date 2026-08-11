import os
from typing import Any, Dict, List

from ...core.plugin_interface import BasePlugin, PluginInput, PluginResult
from ...utils.file_utils import ensure_dir, get_output_dir


class ColorConverterPlugin(BasePlugin):
    @property
    def id(self) -> str:
        return "color_converter"

    @property
    def name(self) -> str:
        return "颜色转换器"

    @property
    def description(self) -> str:
        return "在HEX/RGB/HSL/CMYK等颜色格式之间相互转换"

    @property
    def category(self) -> str:
        return "utility"

    @property
    def icon(self) -> str:
        return "palette"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def requires_files(self) -> bool:
        return False

    @property
    def supported_input_formats(self) -> List[str]:
        return ["*"]

    @property
    def supported_output_formats(self) -> List[str]:
        return ["txt"]

    @property
    def options_schema(self) -> Dict[str, Any]:
        return {
            "input_format": {
                "type": "select",
                "label": "输入格式",
                "default": "hex",
                "options": [
                    {"label": "HEX (#FF5733)", "value": "hex"},
                    {"label": "RGB (255, 87, 51)", "value": "rgb"},
                    {"label": "HSL (10, 100%, 60%)", "value": "hsl"},
                    {"label": "CMYK (0, 66, 80, 0)", "value": "cmyk"}
                ]
            },
            "color_value": {
                "type": "string",
                "label": "颜色值",
                "default": "#FF5733"
            }
        }

    def execute(self, input_data: PluginInput, progress_callback=None) -> PluginResult:
        options = input_data.options
        input_format = options.get("input_format", "hex")
        color_value = options.get("color_value", "#FF5733")

        try:
            rgb = self._parse_to_rgb(input_format, color_value)
            if rgb is None:
                return PluginResult(success=False, error=f"无法解析颜色值: {color_value}")

            r, g, b = rgb

            hex_str = f"#{r:02X}{g:02X}{b:02X}"
            hsl = self._rgb_to_hsl(r, g, b)
            cmyk = self._rgb_to_cmyk(r, g, b)

            results = {
                "HEX": hex_str,
                "RGB": f"rgb({r}, {g}, {b})",
                "RGB_Normalized": f"rgb({r/255:.2f}, {g/255:.2f}, {b/255:.2f})",
                "HSL": f"hsl({hsl[0]}, {hsl[1]}%, {hsl[2]}%)",
                "HSV": self._rgb_to_hsv_str(r, g, b),
                "CMYK": f"cmyk({cmyk[0]}, {cmyk[1]}, {cmyk[2]}, {cmyk[3]})",
                "Brightness": f"{(0.299 * r + 0.587 * g + 0.114 * b):.1f}",
                "Luminance": f"({0.2126 * r/255 + 0.7152 * g/255 + 0.0722 * b/255:.4f})",
            }

            color_preview = f"\033[48;2;{r};{g};{b}m  \033[0m"

            message = f"颜色转换结果:\n"
            message += f"{'=' * 40}\n"
            for k, v in results.items():
                message += f"  {k}: {v}\n"

            return PluginResult(
                success=True,
                output_paths=[],
                message=message,
                metadata={"hex": hex_str, "rgb": rgb, "hsl": hsl, "cmyk": cmyk}
            )

        except Exception as e:
            return PluginResult(success=False, error=f"颜色转换失败: {str(e)}")

    def _parse_to_rgb(self, fmt: str, value: str):
        try:
            value = value.strip()
            if fmt == "hex":
                value = value.lstrip('#')
                if len(value) == 3:
                    value = ''.join(c * 2 for c in value)
                if len(value) == 6:
                    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
                return None

            elif fmt == "rgb":
                parts = value.replace('rgb(', '').replace(')', '').split(',')
                if len(parts) == 3:
                    return tuple(max(0, min(255, int(p.strip()))) for p in parts)
                return None

            elif fmt == "hsl":
                parts = value.replace('hsl(', '').replace(')', '').split(',')
                if len(parts) == 3:
                    h = float(parts[0].strip())
                    s = float(parts[1].strip().rstrip('%')) / 100
                    l = float(parts[2].strip().rstrip('%')) / 100
                    return self._hsl_to_rgb(h, s, l)
                return None

            elif fmt == "cmyk":
                parts = value.replace('cmyk(', '').replace(')', '').split(',')
                if len(parts) == 4:
                    c, m, y, k = [float(p.strip()) / 100.0 for p in parts]
                    return self._cmyk_to_rgb(c, m, y, k)
                return None

        except (ValueError, AttributeError):
            pass
        return None

    def _hsl_to_rgb(self, h: float, s: float, l: float):
        c = (1 - abs(2 * l - 1)) * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = l - c / 2
        if h < 60:
            r, g, b = c, x, 0
        elif h < 120:
            r, g, b = x, c, 0
        elif h < 180:
            r, g, b = 0, c, x
        elif h < 240:
            r, g, b = 0, x, c
        elif h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
        return (round((r + m) * 255), round((g + m) * 255), round((b + m) * 255))

    def _rgb_to_hsl(self, r: int, g: int, b: int):
        r_n, g_n, b_n = r / 255, g / 255, b / 255
        mx = max(r_n, g_n, b_n)
        mn = min(r_n, g_n, b_n)
        l = (mx + mn) / 2
        if mx == mn:
            h, s = 0, 0
        else:
            d = mx - mn
            s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
            if mx == r_n:
                h = (g_n - b_n) / d + (6 if g_n < b_n else 0)
            elif mx == g_n:
                h = (b_n - r_n) / d + 2
            else:
                h = (r_n - g_n) / d + 4
            h *= 60
        return (round(h), round(s * 100), round(l * 100))

    def _rgb_to_hsv_str(self, r: int, g: int, b: int):
        r_n, g_n, b_n = r / 255, g / 255, b / 255
        mx = max(r_n, g_n, b_n)
        mn = min(r_n, g_n, b_n)
        d = mx - mn
        v = mx
        s = 0 if mx == 0 else d / mx
        if d == 0:
            h = 0
        elif mx == r_n:
            h = 60 * (((g_n - b_n) / d) % 6)
        elif mx == g_n:
            h = 60 * ((b_n - r_n) / d + 2)
        else:
            h = 60 * ((r_n - g_n) / d + 4)
        return f"hsv({round(h)}, {round(s * 100)}%, {round(v * 100)}%)"

    def _rgb_to_cmyk(self, r: int, g: int, b: int):
        r_n, g_n, b_n = r / 255, g / 255, b / 255
        k = 1 - max(r_n, g_n, b_n)
        if k == 1:
            return (0, 0, 0, 100)
        c = (1 - r_n - k) / (1 - k)
        m = (1 - g_n - k) / (1 - k)
        y = (1 - b_n - k) / (1 - k)
        return (round(c * 100), round(m * 100), round(y * 100), round(k * 100))

    def _cmyk_to_rgb(self, c: float, m: float, y: float, k: float):
        r = 255 * (1 - c) * (1 - k)
        g = 255 * (1 - m) * (1 - k)
        b = 255 * (1 - y) * (1 - k)
        return (max(0, min(255, round(r))), max(0, min(255, round(g))), max(0, min(255, round(b))))
