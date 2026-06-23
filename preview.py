#!/usr/bin/env python3
"""
Запускает отчётный скрипт и открывает результат в браузере.

Использование:
    python preview.py <script.py> [data.csv]

Примеры:
    python preview.py examples/funnel_report.py data/test_funnel.csv
    python preview.py examples/simple_table.py data/test_complaints.csv
    python preview.py my_custom_report.py
"""

import sys
import os
import re
import subprocess
import tempfile
import webbrowser
import argparse
from pathlib import Path

# ── Разрешённые пакеты (из requirements.txt) ─────────────────────────────────
_REQUIREMENTS_FILE = Path(__file__).parent / "requirements.txt"

def _load_allowed_packages() -> set[str]:
    """Читает requirements.txt и возвращает нижнерегистровые имена пакетов."""
    allowed = set()
    if not _REQUIREMENTS_FILE.exists():
        return allowed
    for line in _REQUIREMENTS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # "pandas==2.3.3" → "pandas"
        name = re.split(r"[=<>!;\s]", line)[0].lower().replace("-", "_")
        if name:
            allowed.add(name)
    return allowed


# Стандартные модули — всегда разрешены (неполный, но практический список)
_STDLIB = {
    "sys", "os", "re", "io", "csv", "json", "html", "math", "time", "abc",
    "ast", "copy", "enum", "functools", "hashlib", "heapq", "inspect",
    "itertools", "logging", "operator", "pathlib", "pickle", "pprint",
    "random", "shutil", "signal", "statistics", "string", "struct",
    "subprocess", "tempfile", "textwrap", "threading", "traceback", "typing",
    "unicodedata", "unittest", "urllib", "uuid", "warnings", "weakref",
    "datetime", "calendar", "collections", "contextlib", "dataclasses",
    "decimal", "fractions", "gc", "glob", "gzip", "http", "importlib",
    "platform", "socket", "sqlite3", "tarfile", "types", "zipfile", "zlib",
    "__future__", "builtins",
}


def _check_imports(script_path: Path) -> list[str]:
    """
    Статически парсит импорты скрипта и возвращает список пакетов,
    которых нет ни в stdlib, ни в requirements.txt.
    """
    allowed = _load_allowed_packages()
    source = script_path.read_text(encoding="utf-8", errors="ignore")

    imported = set()
    for m in re.finditer(
        r"^\s*(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)", source, re.MULTILINE
    ):
        top = m.group(1).lower()
        imported.add(top)

    unknown = []
    for pkg in sorted(imported):
        if pkg in _STDLIB or pkg in allowed:
            continue
        # некоторые пакеты устанавливаются под другим именем (e.g. sklearn → scikit_learn)
        if pkg.replace("_", "-") in {p.replace("_", "-") for p in allowed}:
            continue
        unknown.append(pkg)
    return unknown

# ── Точные стили платформы MJ ─────────────────────────────────────────────────
# Скопировано из static/style.css — изменяй только вместе с оригиналом
PLATFORM_CSS = """\
:root {{
    --bg: #ffffff;
    --surface: #f4f8f4;
    --surface-strong: #e6f0e6;
    --text: #202a20;
    --text-muted: #4d5b4d;
    --accent: #2f7a2f;
    --accent-soft: #d9efdc;
    --border: #c7d5c7;
    --button-text: #ffffff;
    --shadow: rgba(45, 120, 45, 0.16);
}}
body.dark {{
    --bg: #111111;
    --surface: #1c1c1c;
    --surface-strong: #262626;
    --text: #f5f1ec;
    --text-muted: #c8c1b9;
    --accent: #e07618;
    --accent-soft: #3f2a11;
    --border: #3a3a3a;
    --button-text: #111111;
    --shadow: rgba(0, 0, 0, 0.4);
}}
* {{ box-sizing: border-box; }}
html, body {{ min-height: 100%; }}
body {{
    margin: 0;
    font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background:
        radial-gradient(circle at top left, rgba(75,155,75,0.12), transparent 28%),
        radial-gradient(circle at bottom right, rgba(46,120,46,0.14), transparent 25%),
        var(--bg);
    color: var(--text);
    transition: background 0.3s ease, color 0.3s ease;
}}
body.dark {{
    background:
        radial-gradient(circle at top left, rgba(224,122,29,0.12), transparent 30%),
        radial-gradient(circle at bottom right, rgba(255,145,50,0.14), transparent 26%),
        var(--bg);
}}
.page {{ max-width: 1440px; margin: 0 auto; padding: 28px 20px 40px; }}
header {{
    display: flex; align-items: center; justify-content: space-between;
    gap: 16px; padding: 20px 24px; margin-bottom: 28px;
    border: 1px solid var(--border); border-radius: 18px;
    background: var(--surface);
    box-shadow: 0 18px 50px -40px var(--shadow);
}}
header h1 {{ margin: 0; font-size: clamp(1.5rem, 2vw, 2.2rem); }}
.header-actions {{ display: flex; align-items: center; gap: 12px; }}
.button, .theme-toggle {{
    cursor: pointer; border: none; border-radius: 999px;
    padding: 12px 18px; font-weight: 600; text-decoration: none;
    transition: transform 0.2s ease, background-color 0.25s ease, color 0.25s ease;
    font-family: inherit; font-size: 0.9rem;
}}
.button:hover, .theme-toggle:hover {{ transform: translateY(-1px); }}
.button {{ background: var(--accent); color: var(--button-text); }}
.theme-toggle {{ background: rgba(255,255,255,0.1); color: var(--text); border: 1px solid var(--border); }}
.card {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 22px; padding: 24px; margin-bottom: 24px;
    box-shadow: 0 20px 55px -45px var(--shadow);
}}
.run-btn {{
    padding: 8px 22px; border-radius: 10px; border: none;
    background: var(--accent); color: var(--button-text);
    font-family: inherit; font-size: 0.9rem; font-weight: 600;
    cursor: pointer; transition: opacity 0.15s;
}}
.run-btn:hover {{ opacity: 0.85; }}
.run-btn:disabled {{ opacity: 0.5; cursor: not-allowed; }}
.preview-badge {{
    display: inline-block; background: var(--accent-soft); color: var(--accent);
    border: 1px solid var(--border); border-radius: 8px;
    padding: 3px 10px; font-size: 0.75rem; font-weight: 600; margin-top: 6px;
}}
#report-status {{ color: var(--text-muted); font-style: italic; font-size: 0.9rem; margin-bottom: 16px; min-height: 18px; }}
#report-error {{
    padding: 12px 16px; border-radius: 12px; font-size: 0.88rem;
    background: #fef2f2; border: 1px solid #fca5a5; color: #991b1b;
    margin-bottom: 16px; white-space: pre-wrap; font-family: monospace;
}}
body.dark #report-error {{ background: #3a1818; border-color: #7f3535; color: #e07070; }}
#report-output {{ width: 100%; }}
table {{ border-collapse: collapse; }}
.summary-card {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 16px; padding: 18px 22px;
    display: inline-block; min-width: 160px;
}}
.summary-label {{ font-size: 0.78rem; color: var(--text-muted); }}
.summary-value {{ font-size: 1.6rem; font-weight: 700; }}
.summary-sub   {{ font-size: 0.78rem; color: var(--text-muted); }}
.conv-high {{ background:#dcfce7;color:#166534;padding:2px 8px;border-radius:999px;font-size:0.78rem; }}
.conv-mid  {{ background:#fef9c3;color:#854d0e;padding:2px 8px;border-radius:999px;font-size:0.78rem; }}
.conv-low  {{ background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:999px;font-size:0.78rem; }}
.bar-track {{ background:var(--border);border-radius:999px;height:10px;overflow:hidden; }}
.bar-fill  {{ background:var(--accent);height:100%;border-radius:999px; }}
"""

# theme.js логика — встроена напрямую (не требует сервера)
THEME_JS = """\
function setTheme(t) {
    document.body.classList.toggle('dark', t === 'dark');
    localStorage.setItem('theme', t);
    const b = document.getElementById('themeToggleButton');
    if (b) { b.textContent = t === 'dark' ? '🌙' : '☀️'; }
}
function toggleTheme() {
    setTheme(document.body.classList.contains('dark') ? 'light' : 'dark');
}
window.addEventListener('DOMContentLoaded', function() {
    const saved = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    setTheme(saved || (prefersDark ? 'dark' : 'light'));
});
"""

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>📊 {report_title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
  <style>{css}</style>
</head>
<body>
<div class="page">
  <header>
    <div>
      <h1>📊 {report_title}</h1>
      <p style="margin:4px 0 0;color:var(--text-muted);font-size:0.88rem;">{report_desc}</p>
    </div>
    <div class="header-actions">
      <span class="preview-badge">⚡ Локальный превью</span>
      <button class="button" onclick="location.reload()">▶ Перезапустить</button>
      <button id="themeToggleButton" class="theme-toggle" type="button" onclick="toggleTheme()">☀️</button>
    </div>
  </header>

  <div id="report-status"></div>
  <div id="report-error" style="display:{error_display};">{error_text}</div>
  <div id="report-output">{output}</div>
</div>
<script>{theme_js}</script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(
        description="Локальный превью отчётного скрипта MJ"
    )
    parser.add_argument("script", help="Путь к Python-скрипту отчёта")
    parser.add_argument("data",   nargs="?", default=None,
                        help="Путь к CSV-файлу данных (опционально)")
    parser.add_argument("--no-open", action="store_true",
                        help="Не открывать браузер, только сохранить HTML")
    parser.add_argument("--out", default=None,
                        help="Сохранить HTML в файл (по умолчанию — временный файл)")
    args = parser.parse_args()

    script_path = Path(args.script).resolve()
    if not script_path.exists():
        print(f"❌ Скрипт не найден: {script_path}", file=sys.stderr)
        sys.exit(1)

    data_path = None
    if args.data:
        data_path = Path(args.data).resolve()
        if not data_path.exists():
            print(f"❌ Файл данных не найден: {data_path}", file=sys.stderr)
            sys.exit(1)

    # ── Проверяем импорты ────────────────────────────────────────────────────
    unknown_pkgs = _check_imports(script_path)
    if unknown_pkgs:
        print(
            f"⚠  Обнаружены пакеты, которых нет в requirements.txt: "
            f"{', '.join(unknown_pkgs)}\n"
            "   Скрипт может не запуститься на платформе. "
            "Продолжаем локальный запуск…",
            file=sys.stderr,
        )

    # ── Запускаем скрипт ──────────────────────────────────────────────────────
    cmd = [sys.executable, str(script_path)]
    if data_path:
        cmd.append(str(data_path))

    print(f"▶ Запускаем: {' '.join(cmd)}", file=sys.stderr)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            encoding="utf-8",
        )
    except subprocess.TimeoutExpired:
        print("❌ Превышено время выполнения (60 сек)", file=sys.stderr)
        sys.exit(1)

    report_output = ""
    error_display = "none"
    error_text    = ""

    if result.returncode != 0:
        print("❌ Скрипт завершился с ошибкой:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        error_display = "block"
        error_text    = result.stderr.strip()
    else:
        report_output = result.stdout
        if result.stderr:
            print("⚠ Stderr:", result.stderr, file=sys.stderr)

    # ── Оборачиваем в HTML ────────────────────────────────────────────────────
    report_title = script_path.stem.replace("_", " ").title()
    report_desc  = f"📂 {data_path.name}" if data_path else "Источник данных не указан"

    html_content = HTML_TEMPLATE.format(
        report_title  = report_title,
        report_desc   = report_desc,
        css           = PLATFORM_CSS,
        theme_js      = THEME_JS,
        error_display = error_display,
        error_text    = error_text,
        output        = report_output,
    )

    # ── Сохраняем и открываем ─────────────────────────────────────────────────
    if args.out:
        out_path = Path(args.out)
        out_path.write_text(html_content, encoding="utf-8")
        print(f"✓ Сохранено: {out_path.resolve()}", file=sys.stderr)
        if not args.no_open:
            webbrowser.open(out_path.resolve().as_uri())
    else:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".html", delete=False, encoding="utf-8",
            prefix="mj_preview_"
        ) as f:
            f.write(html_content)
            tmp_path = f.name
        print(f"✓ Временный файл: {tmp_path}", file=sys.stderr)
        if not args.no_open:
            webbrowser.open(Path(tmp_path).as_uri())
        else:
            print(html_content)


if __name__ == "__main__":
    main()
