# -*- coding: utf-8 -*-
"""修复SVGs - 确保stroke-width不被误删"""
import urllib.request, time, re, os

ICON_MAP = {
    "pdf": "file-text",
    "image": "image",
    "document": "file-text",
    "file": "file",
    "qrcode": "qr-code",
    "media": "clapperboard",
    "tools": "wrench",
    "box": "package",
    "download": "download",
    "refresh": "refresh-cw",
    "settings": "settings",
    "moon": "moon",
    "sun": "sun",
    "about": "info",
    "play": "play",
    "close": "x",
    "check": "check",
    "folder": "folder",
    "upload": "upload",
    "chevron_right": "chevron-right",
    "palette": "palette",
    "search": "search",
    "edit": "pen-tool",
    "hash": "hash",
    "target": "target",
    "tag": "tag",
    "clock": "clock",
    "compress": "minimize-2",
    "lock": "lock",
    "link": "link",
    "chart": "bar-chart-2",
    "trash": "trash-2",
    "save": "save",
}

BASE_URL = "https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/{}.svg"
output_path = r"e:\TRAE\LocalToolbox\src\ui\widgets\_svg_icons.py"

def clean_svg(svg: str) -> str:
    """清理SVG: 移除class、width、height属性，但保留stroke-width"""
    svg = re.sub(r'class="[^"]*"', '', svg)
    # 只匹配 <svg 标签中的 width/height 属性
    svg = re.sub(r'(<svg[^>]*?)\s+width="\d+"', r'\1', svg)
    svg = re.sub(r'(<svg[^>]*?)\s+height="\d+"', r'\1', svg)
    svg = re.sub(r'\s+', ' ', svg).strip()
    return svg

def download_icon(name):
    url = BASE_URL.format(name)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8')

icons = {}
failed = []
print(f"Downloading {len(ICON_MAP)} icons...")
for key, lucide_name in ICON_MAP.items():
    if key in icons:
        continue
    ok = False
    for attempt in range(3):
        try:
            svg = download_icon(lucide_name)
            svg = clean_svg(svg)
            icons[key] = svg
            print(f"  OK  {key}")
            ok = True
            break
        except Exception as e:
            print(f"  retry {attempt+1} {key}: {e}")
            time.sleep(1)
    if not ok:
        failed.append(key)

with open(output_path, 'w', encoding='utf-8') as f:
    f.write('# -*- coding: utf-8 -*-\n')
    f.write('"""\n')
    f.write('Lucide Icons 内嵌SVG数据\n')
    f.write('来源: https://lucide.dev (ISC License, 免费商用)\n')
    f.write('所有图标使用 stroke="currentColor" 支持动态换色。\n')
    f.write('通过 QSvgRenderer 渲染到 QPixmap。\n')
    f.write('"""\n\n')
    f.write('SVG_ICONS = {}\n\n')
    for key in sorted(icons.keys()):
        svg = icons[key]
        f.write(f'SVG_ICONS["{key}"] = """{svg}"""\n\n')

print(f"\nGenerated: {output_path}")
print(f"Total: {len(icons)}, Failed: {failed}")
