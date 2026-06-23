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

# ── Стили платформы MJ (встроенные для автономного превью) ────────────────────
PLATFORM_CSS = """
:root {
  --bg:         #f8fafc;
  --surface:    #ffffff;
  --border:     #e2e8f0;
  --text:       #1e293b;
  --text-muted: #64748b;
  --accent:     #3b82f6;
}
body.dark {
  --bg:         #0f172a;
  --surface:    #1e293b;
  --border:     #334155;
  --text:       #f1f5f9;
  --text-muted: #94a3b8;
  --accent:     #60a5fa;
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: var(--bg);
  color: var(--text);
  margin: 0;
  padding: 32px;
  font-size: 14px;
  line-height: 1.6;
}
.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 28px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
  gap: 12px;
}
.preview-title {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text-muted);
}
.preview-badge {
  background: #fef3c7;
  color: #92400e;
  border: 1px solid #fde68a;
  border-radius: 6px;
  padding: 3px 10px;
  font-size: 0.75rem;
  font-weight: 600;
}
.theme-btn {
  padding: 6px 14px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  cursor: pointer;
  font-size: 0.82rem;
}
.summary-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 18px 22px;
  display: inline-block;
  min-width: 160px;
}
.summary-label { font-size: 0.78rem; color: var(--text-muted); }
.summary-value { font-size: 1.6rem; font-weight: 700; }
.summary-sub   { font-size: 0.78rem; color: var(--text-muted); }
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 16px;
}
table { border-collapse: collapse; }
.conv-high { background:#dcfce7;color:#166534;padding:2px 8px;border-radius:999px;font-size:0.78rem; }
.conv-mid  { background:#fef9c3;color:#854d0e;padding:2px 8px;border-radius:999px;font-size:0.78rem; }
.conv-low  { background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:999px;font-size:0.78rem; }
.bar-track { background:var(--border);border-radius:999px;height:10px;overflow:hidden; }
.bar-fill  { background:var(--accent);height:100%;border-radius:999px; }
"""

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>Preview: {script_name}</title>
  <style>{css}</style>
</head>
<body>
  <div class="preview-header">
    <div>
      <div class="preview-title">📋 Preview: {script_name}</div>
      {data_badge}
    </div>
    <div style="display:flex;gap:8px;align-items:center;">
      <span class="preview-badge">⚡ Локальный превью</span>
      <button class="theme-btn" onclick="document.body.classList.toggle('dark')">🌙 Тема</button>
    </div>
  </div>
  <div id="report-output">
{output}
  </div>
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

    if result.returncode != 0:
        print("❌ Скрипт завершился с ошибкой:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        # Показываем ошибку в браузере тоже
        err_html = f"<pre style='color:#dc2626;background:#fef2f2;padding:16px;border-radius:8px;'>{result.stderr}</pre>"
        report_output = err_html
    else:
        report_output = result.stdout
        if result.stderr:
            print("⚠ Stderr:", result.stderr, file=sys.stderr)

    # ── Оборачиваем в HTML ────────────────────────────────────────────────────
    data_badge = ""
    if data_path:
        data_badge = f'<div style="font-size:0.78rem;color:var(--text-muted);margin-top:4px;">📂 {data_path.name}</div>'

    html_content = HTML_TEMPLATE.format(
        script_name=script_path.name,
        css=PLATFORM_CSS,
        data_badge=data_badge,
        output=report_output,
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
