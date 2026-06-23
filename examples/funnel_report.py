"""
Отчёт: воронка продаж по продуктам и каналам.
Источник данных: funnel_data.csv
Колонки: report_dt, dash_channel, dash_product, sort, step_name, value

Показывает:
- фильтр по продукту и каналу
- воронку с конверсиями
"""

import sys
import csv
import html
from collections import defaultdict

data_path = sys.argv[1] if len(sys.argv) > 1 else None

if not data_path:
    print("<p style='color:red'>Не задан путь к данным.</p>")
    sys.exit(0)

# ── Чтение CSV ────────────────────────────────────────────────────────────────
rows = []
try:
    for sep in (";", ","):
        with open(data_path, encoding="utf-8-sig", newline="") as f:
            reader = list(csv.DictReader(f, delimiter=sep))
        if reader and len(reader[0]) > 1:
            break
    rows = reader
except Exception as e:
    print(f"<p style='color:red'>Ошибка: {html.escape(str(e))}</p>")
    sys.exit(0)

# ── Извлекаем уникальные значения для фильтров ────────────────────────────────
products  = sorted({r["dash_product"]  for r in rows if r.get("dash_product")})
channels  = sorted({r["dash_channel"]  for r in rows if r.get("dash_channel")})
dates     = sorted({r["report_dt"][:7] for r in rows if r.get("report_dt")}, reverse=True)

# ── По умолчанию берём первый продукт, первый канал, последний месяц ──────────
def_product = products[0]  if products else ""
def_channel = channels[0]  if channels else ""
def_date    = dates[0]     if dates    else ""


def conv_badge(pct: float) -> str:
    if pct >= 60:
        cls = "conv-high"
    elif pct >= 30:
        cls = "conv-mid"
    else:
        cls = "conv-low"
    return f'<span class="{cls}">{pct:.1f}%</span>'


def build_funnel_html(product: str, channel: str, month: str, all_rows: list) -> str:
    filtered = [
        r for r in all_rows
        if r.get("dash_product") == product
        and r.get("dash_channel") == channel
        and r.get("report_dt", "")[:7] == month
    ]
    if not filtered:
        return "<p style='color:var(--text-muted)'>Нет данных для выбранных фильтров.</p>"

    steps = sorted(filtered, key=lambda r: int(r.get("sort", 0)))
    first_val = int(steps[0]["value"]) if steps else 1

    rows_html = ""
    prev_val = None
    for i, s in enumerate(steps):
        val = int(s["value"])
        pct_prev  = (val / prev_val * 100) if prev_val else 100.0
        pct_first = (val / first_val * 100) if first_val else 100.0
        bar_w = max(4, int(pct_first))
        val_fmt = f"{val:,}".replace(",", " ")

        rows_html += f"""
        <tr>
          <td style='padding:8px 10px;color:var(--text-muted);font-size:0.82rem;'>{i+1}</td>
          <td style='padding:8px 10px;'>{html.escape(s['step_name'])}</td>
          <td style='padding:8px 10px;font-weight:600;'>{val_fmt}</td>
          <td style='padding:8px 10px;'>{conv_badge(pct_prev) if prev_val else '—'}</td>
          <td style='padding:8px 10px;'>{conv_badge(pct_first)}</td>
          <td style='padding:8px 10px;min-width:120px;'>
            <div class='bar-track'>
              <div class='bar-fill' style='width:{bar_w}%'></div>
            </div>
          </td>
        </tr>"""
        prev_val = val

    return f"""
    <table class='funnel-table' style='width:100%;border-collapse:collapse;'>
      <thead>
        <tr>
          <th style='padding:8px 10px;text-align:left;border-bottom:2px solid var(--border);'>#</th>
          <th style='padding:8px 10px;text-align:left;border-bottom:2px solid var(--border);'>Шаг</th>
          <th style='padding:8px 10px;text-align:left;border-bottom:2px solid var(--border);'>Значение</th>
          <th style='padding:8px 10px;text-align:left;border-bottom:2px solid var(--border);'>Конв. к пред.</th>
          <th style='padding:8px 10px;text-align:left;border-bottom:2px solid var(--border);'>Конв. от начала</th>
          <th style='padding:8px 10px;text-align:left;border-bottom:2px solid var(--border);'>Бар</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>"""


# ── Генерируем опции селектов ──────────────────────────────────────────────────
def opts(values, default):
    return "".join(
        f'<option value="{html.escape(v)}"{"selected" if v==default else ""}>{html.escape(v)}</option>'
        for v in values
    )


funnel_html = build_funnel_html(def_product, def_channel, def_date, rows)

# ── Сериализуем данные в JS для фильтрации на клиенте ────────────────────────
import json
js_rows = json.dumps(rows, ensure_ascii=False)

print(f"""
<style>
  .bar-track {{ background:var(--border);border-radius:999px;height:10px;overflow:hidden; }}
  .bar-fill  {{ background:var(--accent);height:100%;border-radius:999px; }}
  .conv-high {{ background:#dcfce7;color:#166534;padding:2px 8px;border-radius:999px;font-size:0.78rem; }}
  .conv-mid  {{ background:#fef9c3;color:#854d0e;padding:2px 8px;border-radius:999px;font-size:0.78rem; }}
  .conv-low  {{ background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:999px;font-size:0.78rem; }}
  select.rpt-sel {{ padding:5px 10px;border-radius:8px;border:1px solid var(--border);
                    background:var(--surface);color:var(--text);font-size:0.88rem;cursor:pointer; }}
</style>

<div style='display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px;align-items:center;'>
  <div>
    <div style='font-size:0.78rem;color:var(--text-muted);margin-bottom:4px;'>Продукт</div>
    <select class='rpt-sel' id='sel-product' onchange='rebuildFunnel()'>
      {opts(products, def_product)}
    </select>
  </div>
  <div>
    <div style='font-size:0.78rem;color:var(--text-muted);margin-bottom:4px;'>Канал</div>
    <select class='rpt-sel' id='sel-channel' onchange='rebuildFunnel()'>
      {opts(channels, def_channel)}
    </select>
  </div>
  <div>
    <div style='font-size:0.78rem;color:var(--text-muted);margin-bottom:4px;'>Месяц</div>
    <select class='rpt-sel' id='sel-date' onchange='rebuildFunnel()'>
      {opts(dates, def_date)}
    </select>
  </div>
</div>

<div id='funnel-container'>{funnel_html}</div>

<script>
const _ALL_ROWS = {js_rows};

function convBadge(pct) {{
  const cls = pct >= 60 ? 'conv-high' : pct >= 30 ? 'conv-mid' : 'conv-low';
  return '<span class="' + cls + '">' + pct.toFixed(1) + '%</span>';
}}

function rebuildFunnel() {{
  const product = document.getElementById('sel-product').value;
  const channel = document.getElementById('sel-channel').value;
  const month   = document.getElementById('sel-date').value;
  const steps = _ALL_ROWS
    .filter(r => r.dash_product === product && r.dash_channel === channel && r.report_dt.slice(0,7) === month)
    .sort((a,b) => +a.sort - +b.sort);

  if (!steps.length) {{
    document.getElementById('funnel-container').innerHTML =
      "<p style='color:var(--text-muted)'>Нет данных.</p>";
    return;
  }}
  const firstVal = +steps[0].value;
  let prev = null, html = '';
  steps.forEach((s, i) => {{
    const val = +s.value;
    const pctPrev  = prev ? val/prev*100 : 100;
    const pctFirst = val/firstVal*100;
    const barW = Math.max(4, Math.round(pctFirst));
    const fmt = val.toLocaleString('ru-RU');
    html += `<tr>
      <td style='padding:8px 10px;color:var(--text-muted);font-size:.82rem;'>${{i+1}}</td>
      <td style='padding:8px 10px;'>${{s.step_name}}</td>
      <td style='padding:8px 10px;font-weight:600;'>${{fmt}}</td>
      <td style='padding:8px 10px;'>${{prev ? convBadge(pctPrev) : '—'}}</td>
      <td style='padding:8px 10px;'>${{convBadge(pctFirst)}}</td>
      <td style='padding:8px 10px;min-width:120px;'>
        <div class='bar-track'><div class='bar-fill' style='width:${{barW}}%'></div></div>
      </td>
    </tr>`;
    prev = val;
  }});
  document.getElementById('funnel-container').innerHTML =
    `<table class='funnel-table' style='width:100%;border-collapse:collapse;'>
      <thead><tr>
        <th style='padding:8px 10px;text-align:left;border-bottom:2px solid var(--border);'>#</th>
        <th style='padding:8px 10px;text-align:left;border-bottom:2px solid var(--border);'>Шаг</th>
        <th style='padding:8px 10px;text-align:left;border-bottom:2px solid var(--border);'>Значение</th>
        <th style='padding:8px 10px;text-align:left;border-bottom:2px solid var(--border);'>Конв. к пред.</th>
        <th style='padding:8px 10px;text-align:left;border-bottom:2px solid var(--border);'>Конв. от начала</th>
        <th style='padding:8px 10px;text-align:left;border-bottom:2px solid var(--border);'>Бар</th>
      </tr></thead>
      <tbody>${{html}}</tbody>
    </table>`;
}}
</script>
""")
