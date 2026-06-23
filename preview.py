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
import subprocess
import tempfile
import webbrowser
import argparse
from pathlib import Path

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
