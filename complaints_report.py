"""
Отчёт: анализ обращений клиентов (жалобы + консультации).
Источник данных: complaints.csv
Колонки: report_dt, toxic_flag, unit, subj, prd, sum_cnt
"""

import sys
import io
import csv
import html
import json
from collections import defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import plotly.graph_objects as go

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
            rows = reader
            break
except Exception as e:
    print(f"<p style='color:red'>Ошибка чтения: {html.escape(str(e))}</p>")
    sys.exit(0)

# ── Нормализация ──────────────────────────────────────────────────────────────
for r in rows:
    try:
        r["sum_cnt"] = int(float(r.get("sum_cnt", 0) or 0))
    except (ValueError, TypeError):
        r["sum_cnt"] = 0
    r["_month"] = r.get("report_dt", "")[:7]

MONTH_NAMES = {
    "01": "Январь", "02": "Февраль", "03": "Март",
    "04": "Апрель", "05": "Май",     "06": "Июнь",
    "07": "Июль",   "08": "Август",  "09": "Сентябрь",
    "10": "Октябрь","11": "Ноябрь",  "12": "Декабрь",
}

def month_label(m: str) -> str:
    parts = m.split("-")
    return f"{MONTH_NAMES.get(parts[1], parts[1])} {parts[0]}" if len(parts) == 2 else m

months_sorted = sorted({r["_month"] for r in rows if r["_month"]})
def_month = months_sorted[-1] if months_sorted else ""

# ── Топ-4 продуктов за всё время ─────────────────────────────────────────────
product_totals: dict = defaultdict(int)
for r in rows:
    product_totals[r.get("prd", "—")] += r["sum_cnt"]
top4 = sorted(product_totals.items(), key=lambda x: x[1], reverse=True)[:4]
top4_max = top4[0][1] if top4 else 1

# ── График динамики ───────────────────────────────────────────────────────────
monthly: dict = defaultdict(lambda: {"Жалобы": 0, "Консультации": 0})
for r in rows:
    flag = r.get("toxic_flag", "")
    if flag in ("Жалобы", "Консультации"):
        monthly[r["_month"]][flag] += r["sum_cnt"]

x_labels = [month_label(m) for m in months_sorted]
y_comp   = [monthly[m]["Жалобы"]       for m in months_sorted]
y_cons   = [monthly[m]["Консультации"] for m in months_sorted]
y_total  = [y_comp[i] + y_cons[i]      for i in range(len(months_sorted))]

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=x_labels, y=y_total, name="Обращения",
    line=dict(color="#2f7a2f", width=2.5),
    fill="tozeroy", fillcolor="rgba(47,122,47,0.08)",
    hovertemplate="%{x}: <b>%{y:,}</b><extra>Обращения</extra>",
))
fig.add_trace(go.Scatter(
    x=x_labels, y=y_comp, name="Жалобы",
    line=dict(color="#ef4444", width=1.8, dash="dot"),
    hovertemplate="%{x}: %{y:,}<extra>Жалобы</extra>",
))
fig.add_trace(go.Scatter(
    x=x_labels, y=y_cons, name="Консультации",
    line=dict(color="#3b82f6", width=1.8, dash="dot"),
    hovertemplate="%{x}: %{y:,}<extra>Консультации</extra>",
))
fig.update_layout(
    margin=dict(l=0, r=0, t=8, b=0),
    height=280,
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                font=dict(size=12)),
    xaxis=dict(gridcolor="rgba(128,128,128,0.15)", tickfont=dict(size=11), showline=False),
    yaxis=dict(gridcolor="rgba(128,128,128,0.15)", tickfont=dict(size=11), showline=False),
    hovermode="x unified",
)
chart_html = fig.to_html(include_plotlyjs="cdn", full_html=False)

# ── Серализация для JS-фильтра карточек ──────────────────────────────────────
js_data = json.dumps(
    [{"month": r["_month"], "flag": r.get("toxic_flag", ""), "cnt": r["sum_cnt"]}
     for r in rows],
    ensure_ascii=False,
)

# ── Опции селекта месяца ─────────────────────────────────────────────────────
month_opts = "".join(
    f'<option value="{m}"{"selected" if m == def_month else ""}>{month_label(m)}</option>'
    for m in reversed(months_sorted)
)

# ── Топ-4: строки таблицы ────────────────────────────────────────────────────
top4_rows_html = ""
for i, (prd, cnt) in enumerate(top4):
    bar_w = int(cnt / top4_max * 100)
    top4_rows_html += f"""
    <tr>
      <td style='padding:11px 14px;font-size:.82rem;color:var(--text-muted);'>{i + 1}</td>
      <td style='padding:11px 14px;font-weight:500;'>{html.escape(prd)}</td>
      <td style='padding:11px 14px;font-weight:700;'>{cnt:,}</td>
      <td style='padding:11px 14px;min-width:160px;'>
        <div class='bar-track'><div class='bar-fill' style='width:{bar_w}%'></div></div>
      </td>
    </tr>"""

print(f"""
<style>
  select.rpt-sel {{
    padding: 8px 16px; border-radius: 10px; border: 1px solid var(--border);
    background: var(--surface); color: var(--text); font-size: .9rem;
    cursor: pointer; font-family: inherit; font-weight: 500;
  }}
  .kpi-grid {{
    display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px;
  }}
  .kpi-card {{
    background: var(--surface); border: 1px solid var(--border);
    border-radius: 18px; padding: 22px 26px; flex: 1; min-width: 180px;
    box-shadow: 0 12px 40px -30px var(--shadow);
  }}
  .kpi-label {{ font-size: .78rem; color: var(--text-muted); margin-bottom: 8px; letter-spacing:.03em; text-transform:uppercase; }}
  .kpi-value {{ font-size: 2.1rem; font-weight: 700; line-height: 1; }}
  .kpi-card.complaints .kpi-value {{ color: #ef4444; }}
  .kpi-card.consult    .kpi-value {{ color: #3b82f6; }}
  .kpi-card.total      .kpi-value {{ color: var(--accent); }}
  .section-title {{
    font-size: 1rem; font-weight: 600; margin: 0 0 16px;
  }}
  .rpt-table {{ width: 100%; border-collapse: collapse; }}
  .rpt-table th {{
    padding: 8px 14px; text-align: left;
    border-bottom: 2px solid var(--border);
    font-size: .78rem; color: var(--text-muted); font-weight: 600;
    text-transform: uppercase; letter-spacing: .04em;
  }}
  .rpt-table td {{ border-bottom: 1px solid var(--border); }}
  .rpt-table tbody tr:last-child td {{ border-bottom: none; }}
</style>

<div style='display:flex;align-items:center;gap:12px;margin-bottom:28px;'>
  <span style='font-size:.85rem;color:var(--text-muted);font-weight:500;'>Период:</span>
  <select class='rpt-sel' id='sel-month' onchange='updateCards()'>
    {month_opts}
  </select>
</div>

<div class='kpi-grid'>
  <div class='kpi-card complaints'>
    <div class='kpi-label'>Жалобы</div>
    <div class='kpi-value' id='kpi-complaints'>—</div>
  </div>
  <div class='kpi-card consult'>
    <div class='kpi-label'>Консультации</div>
    <div class='kpi-value' id='kpi-consult'>—</div>
  </div>
  <div class='kpi-card total'>
    <div class='kpi-label'>Обращений всего</div>
    <div class='kpi-value' id='kpi-total'>—</div>
  </div>
</div>

<div class='card' style='padding:22px 24px;margin-bottom:24px;'>
  <div class='section-title'>Динамика обращений</div>
  {chart_html}
</div>

<div class='card' style='padding:22px 24px;'>
  <div class='section-title'>Топ-4 продукта по обращениям за всё время</div>
  <table class='rpt-table'>
    <thead><tr>
      <th style='width:40px;'>#</th>
      <th>Продукт</th>
      <th>Обращений</th>
      <th></th>
    </tr></thead>
    <tbody>{top4_rows_html}</tbody>
  </table>
</div>

<script>
const _DATA = {js_data};

function fmt(n) {{
  return n.toLocaleString('ru-RU');
}}

function updateCards() {{
  const month = document.getElementById('sel-month').value;
  let complaints = 0, consult = 0;
  _DATA.forEach(function(r) {{
    if (r.month !== month) return;
    if (r.flag === 'Жалобы') complaints += r.cnt;
    else if (r.flag === 'Консультации') consult += r.cnt;
  }});
  document.getElementById('kpi-complaints').textContent = fmt(complaints);
  document.getElementById('kpi-consult').textContent    = fmt(consult);
  document.getElementById('kpi-total').textContent      = fmt(complaints + consult);
}}

document.addEventListener('DOMContentLoaded', updateCards);
updateCards();
</script>
""")
