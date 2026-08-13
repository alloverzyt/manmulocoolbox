import os
import sys
import subprocess
from typing import Optional, List


def find_libreoffice() -> Optional[str]:
    search_paths = []

    # 应用自带（工具下载器安装到 <根>/resources/libreoffice）
    if getattr(sys, 'frozen', False):
        app_res = os.path.join(os.path.dirname(sys.executable), 'resources')
    else:
        app_res = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'resources'
        )
    search_paths.append(os.path.join(app_res, 'libreoffice', 'program', 'soffice.exe'))

    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
        search_paths.append(os.path.join(base, 'libreoffice', 'program', 'soffice.exe'))
        search_paths.append(os.path.join(base, 'LibreOffice', 'program', 'soffice.exe'))

    if sys.platform == 'win32':
        search_paths.extend([
            r'C:\Program Files\LibreOffice\program\soffice.exe',
            r'C:\Program Files (x86)\LibreOffice\program\soffice.exe',
        ])
    elif sys.platform == 'darwin':
        search_paths.append('/Applications/LibreOffice.app/Contents/MacOS/soffice')
    else:
        search_paths.extend([
            '/usr/bin/libreoffice',
            '/usr/bin/soffice',
            '/snap/bin/libreoffice',
        ])

    for path in search_paths:
        if os.path.isfile(path):
            return path

    lo_path = subprocess.run(
        ['where', 'libreoffice'] if sys.platform == 'win32' else ['which', 'libreoffice'],
        capture_output=True, text=True
    )
    if lo_path.returncode == 0 and lo_path.stdout.strip():
        return lo_path.stdout.strip().split('\n')[0]

    return None


def libreoffice_convert(input_path: str, output_dir: str, format_filter: str = "pdf",
                        soffice_path: str = None) -> Optional[str]:
    soffice = soffice_path or find_libreoffice()
    if not soffice:
        return None

    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        soffice,
        '--headless',
        '--convert-to', format_filter,
        '--outdir', output_dir,
        input_path
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=300,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        if result.returncode == 0:
            output_name = os.path.splitext(os.path.basename(input_path))[0] + f'.{format_filter}'
            output_path = os.path.join(output_dir, output_name)
            if os.path.isfile(output_path):
                return output_path
        return None
    except Exception:
        return None


def libreoffice_to_images(input_path: str, output_dir: str, dpi: int = 300,
                          soffice_path: str = None) -> List[str]:
    soffice = soffice_path or find_libreoffice()
    if not soffice:
        return []

    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        soffice,
        '--headless',
        '--convert-to', 'png',
        '--outdir', output_dir,
        input_path
    ]

    try:
        subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=300,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )

        base_name = os.path.splitext(os.path.basename(input_path))[0]
        page_files = []
        for f in sorted(os.listdir(output_dir)):
            if f.startswith(base_name) and f.endswith('.png'):
                page_files.append(os.path.join(output_dir, f))
        return page_files
    except Exception:
        return []
