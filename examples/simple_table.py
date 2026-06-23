"""
Простой отчёт: читает любой CSV и показывает первые 50 строк в таблице.
Загрузи в Админка → Отчёты → + Добавить отчёт.
data_path = путь к CSV-файлу.
"""

import sys
import csv
import html

data_path = sys.argv[1] if len(sys.argv) > 1 else None

if not data_path:
    print("<p style='color:red'>Не задан путь к данным (data_path).</p>")
    sys.exit(0)

rows = []
try:
    for sep in (";", ",", "\t"):
        with open(data_path, encoding="utf-8-sig", newline="") as f:
            reader = list(csv.reader(f, delimiter=sep))
        if reader and len(reader[0]) > 1:
            break
    headers = reader[0]
    rows = reader[1:51]
except Exception as e:
    print(f"<p style='color:red'>Ошибка чтения файла: {html.escape(str(e))}</p>")
    sys.exit(0)

th = "".join(
    f"<th style='padding:8px 12px;text-align:left;border-bottom:2px solid var(--border);white-space:nowrap;'>{html.escape(h)}</th>"
    for h in headers
)
tr_rows = ""
for i, row in enumerate(rows):
    bg = "background:var(--surface)" if i % 2 == 0 else ""
    tds = "".join(
        f"<td style='padding:6px 12px;border-bottom:1px solid var(--border);font-size:0.85rem;'>{html.escape(str(v))}</td>"
        for v in row
    )
    tr_rows += f"<tr style='{bg}'>{tds}</tr>"

print(f"""
<div style='overflow-x:auto;'>
  <p style='color:var(--text-muted);font-size:0.85rem;margin-bottom:8px;'>
    Показаны первые {len(rows)} строк · {len(headers)} колонок
  </p>
  <table style='width:100%;border-collapse:collapse;'>
    <thead><tr>{th}</tr></thead>
    <tbody>{tr_rows}</tbody>
  </table>
</div>
""")
