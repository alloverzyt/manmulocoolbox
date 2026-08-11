# -*- coding: utf-8 -*-
import urllib.request, time, re

failed = {'box': 'package', 'close': 'x'}
for key, name in failed.items():
    for attempt in range(3):
        try:
            url = f'https://cdn.jsdelivr.net/npm/lucide-static@latest/icons/{name}.svg'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=20) as r:
                svg = r.read().decode('utf-8')
            svg = re.sub(r'class="[^"]*"', '', svg)
            svg = re.sub(r'width="\d+"', '', svg)
            svg = re.sub(r'height="\d+"', '', svg)
            svg = re.sub(r'\s+', ' ', svg).strip()
            with open(r'e:\TRAE\LocalToolbox\src\ui\widgets\_svg_icons.py', 'a', encoding='utf-8') as f:
                f.write(f'SVG_ICONS["{key}"] = """{svg}"""\n\n')
            print(f'OK {key}')
            break
        except Exception as e:
            print(f'retry {attempt+1} {key}: {e}')
            time.sleep(2)
