"""
Отчёт: топ жалоб по теме и продукту за выбранный месяц.
Источник данных: complaints.csv
Колонки: report_dt, toxic_flag, unit, subj, prd, sum_cnt
"""

import sys
import csv
import html
import json
from collections import defaultdict

data_path = sys.argv[1] if len(sys.argv) > 1 else None

if not data_path:
    print("<p style='color:red'>Не задан путь к данным.</p>")
    sys.exit(0)

# ── Чтение ────────────────────────────────────────────────────────────────────
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

# ── Нормализуем числовые поля ─────────────────────────────────────────────────
for r in rows:
    try:
        r["sum_cnt"] = int(float(r.get("sum_cnt", 0) or 0))
    except (ValueError, TypeError):
        r["sum_cnt"] = 0
    r["_month"] = r.get("report_dt", "")[:7]

months   = sorted({r["_month"] for r in rows if r["_month"]}, reverse=True)
products = ["Все"] + sorted({r.get("prd", "") for r in rows if r.get("prd")})
def_month   = months[0]   if months   else ""
def_product = "Все"


def build_table(all_rows, month, product):
    filtered = [
        r for r in all_rows
        if r["_month"] == month
        and r.get("toxic_flag") == "Жалобы"
        and (product == "Все" or r.get("prd") == product)
    ]
    if not filtered:
        return "<p style='color:var(--text-muted)'>Нет данных.</p>"

    # Группируем по теме + продукту
    grouped = defaultdict(int)
    for r in filtered:
        grouped[(r.get("subj", "—"), r.get("prd", "—"))] += r["sum_cnt"]

    sorted_rows = sorted(grouped.items(), key=lambda x: x[1], reverse=True)[:20]
    total = sum(v for _, v in sorted_rows)

    trs = ""
    for i, ((subj, prd), cnt) in enumerate(sorted_rows):
        pct = cnt / total * 100 if total else 0
        bar_w = max(2, int(pct * 2))  # scale to max ~200px
        trs += f"""
        <tr>
          <td style='padding:7px 10px;font-size:0.82rem;color:var(--text-muted);'>{i+1}</td>
          <td style='padding:7px 10px;'>{html.escape(subj)}</td>
          <td style='padding:7px 10px;color:var(--text-muted);font-size:0.85rem;'>{html.escape(prd)}</td>
          <td style='padding:7px 10px;font-weight:600;'>{cnt:,}</td>
          <td style='padding:7px 10px;font-size:0.82rem;color:var(--text-muted);'>{pct:.1f}%</td>
          <td style='padding:7px 10px;min-width:100px;'>
            <div class='bar-track'><div class='bar-fill' style='width:{bar_w}px;max-width:100%;'></div></div>
          </td>
        </tr>"""

    return f"""
    <p style='color:var(--text-muted);font-size:0.85rem;margin-bottom:8px;'>
      Всего жалоб: <strong>{total:,}</strong> · показаны топ-{len(sorted_rows)}
    </p>
    <table style='width:100%;border-collapse:collapse;'>
      <thead><tr>
        <th style='padding:7px 10px;text-align:left;border-bottom:2px solid var(--border);'>#</th>
        <th style='padding:7px 10px;text-align:left;border-bottom:2px solid var(--border);'>Тема</th>
        <th style='padding:7px 10px;text-align:left;border-bottom:2px solid var(--border);'>Продукт</th>
        <th style='padding:7px 10px;text-align:left;border-bottom:2px solid var(--border);'>Кол-во</th>
        <th style='padding:7px 10px;text-align:left;border-bottom:2px solid var(--border);'>%</th>
        <th style='padding:7px 10px;text-align:left;border-bottom:2px solid var(--border);'></th>
      </tr></thead>
      <tbody>{trs}</tbody>
    </table>"""


def opts(values, default):
    return "".join(
        f'<option value="{html.escape(v)}"{"selected" if v==default else ""}>{html.escape(v)}</option>'
        for v in values
    )


table_html = build_table(rows, def_month, def_product)
js_rows    = json.dumps(rows, ensure_ascii=False)

print(f"""
<style>
  .bar-track {{ background:var(--border);border-radius:999px;height:10px;overflow:hidden; }}
  .bar-fill  {{ background:#ef4444;height:100%;border-radius:999px; }}
  select.rpt-sel {{ padding:5px 10px;border-radius:8px;border:1px solid var(--border);
                    background:var(--surface);color:var(--text);font-size:0.88rem;cursor:pointer; }}
</style>

<div style='display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px;align-items:center;'>
  <div>
    <div style='font-size:0.78rem;color:var(--text-muted);margin-bottom:4px;'>Месяц</div>
    <select class='rpt-sel' id='sel-month' onchange='rebuildTable()'>
      {opts(months, def_month)}
    </select>
  </div>
  <div>
    <div style='font-size:0.78rem;color:var(--text-muted);margin-bottom:4px;'>Продукт</div>
    <select class='rpt-sel' id='sel-product' onchange='rebuildTable()'>
      {opts(products, def_product)}
    </select>
  </div>
</div>

<div id='complaints-container'>{table_html}</div>

<script>
const _ROWS = {js_rows};

function rebuildTable() {{
  const month   = document.getElementById('sel-month').value;
  const product = document.getElementById('sel-product').value;
  const filtered = _ROWS.filter(r =>
    r._month === month && r.toxic_flag === 'Жалобы' &&
    (product === 'Все' || r.prd === product)
  );
  if (!filtered.length) {{
    document.getElementById('complaints-container').innerHTML =
      "<p style='color:var(--text-muted)'>Нет данных.</p>";
    return;
  }}
  const grouped = {{}};
  filtered.forEach(r => {{
    const k = r.subj + '||' + r.prd;
    grouped[k] = (grouped[k] || {{subj:r.subj,prd:r.prd,cnt:0}});
    grouped[k].cnt += +r.sum_cnt;
  }});
  const sorted = Object.values(grouped).sort((a,b)=>b.cnt-a.cnt).slice(0,20);
  const total  = sorted.reduce((s,x)=>s+x.cnt,0);
  let trs = '';
  sorted.forEach((x,i) => {{
    const pct  = total ? x.cnt/total*100 : 0;
    const barW = Math.max(2, Math.round(pct*2));
    trs += `<tr>
      <td style='padding:7px 10px;font-size:.82rem;color:var(--text-muted);'>${{i+1}}</td>
      <td style='padding:7px 10px;'>${{x.subj}}</td>
      <td style='padding:7px 10px;color:var(--text-muted);font-size:.85rem;'>${{x.prd}}</td>
      <td style='padding:7px 10px;font-weight:600;'>${{x.cnt.toLocaleString('ru-RU')}}</td>
      <td style='padding:7px 10px;font-size:.82rem;color:var(--text-muted);'>${{pct.toFixed(1)}}%</td>
      <td style='padding:7px 10px;min-width:100px;'>
        <div class='bar-track'><div class='bar-fill' style='width:${{barW}}px;max-width:100%;'></div></div>
      </td>
    </tr>`;
  }});
  document.getElementById('complaints-container').innerHTML = `
    <p style='color:var(--text-muted);font-size:.85rem;margin-bottom:8px;'>
      Всего жалоб: <strong>${{total.toLocaleString('ru-RU')}}</strong> · показаны топ-${{sorted.length}}
    </p>
    <table style='width:100%;border-collapse:collapse;'>
      <thead><tr>
        <th style='padding:7px 10px;text-align:left;border-bottom:2px solid var(--border);'>#</th>
        <th style='padding:7px 10px;text-align:left;border-bottom:2px solid var(--border);'>Тема</th>
        <th style='padding:7px 10px;text-align:left;border-bottom:2px solid var(--border);'>Продукт</th>
        <th style='padding:7px 10px;text-align:left;border-bottom:2px solid var(--border);'>Кол-во</th>
        <th style='padding:7px 10px;text-align:left;border-bottom:2px solid var(--border);'>%</th>
        <th style='padding:7px 10px;text-align:left;border-bottom:2px solid var(--border);'></th>
      </tr></thead>
      <tbody>${{trs}}</tbody>
    </table>`;
}}
</script>
""")
