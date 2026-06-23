#!/usr/bin/env python3
"""
Генерирует синтетические CSV-данные для тестирования отчётов.

Использование:
    python generate_synthetic.py <format> [--rows N] [--out file.csv]

Форматы:
    funnel          — воронка продаж (funnel_data.csv)
    complaints      — жалобы и обращения (complaints.csv)
    client_metrics  — клиентские метрики (client_metrics.csv)
    clickstream     — кликстрим (clickstream_monthly.csv)

Примеры:
    python generate_synthetic.py funnel
    python generate_synthetic.py complaints --rows 200 --out test_complaints.csv
"""

import sys
import csv
import random
import argparse
from datetime import date, timedelta
from io import StringIO

# ── Общие справочники ─────────────────────────────────────────────────────────

PRODUCTS  = ["Дебетовая карта", "Кредитная карта", "Потребительский кредит",
             "Ипотека", "Вклад", "Накопительный счёт", "Страхование"]
CHANNELS  = ["PUSH", "Email", "SMS", "APP", "WEB"]
UNITS     = ["Розничный блок", "Корпоративный блок", "Малый бизнес"]
MONTHS    = [date(2025, m, 1) for m in range(1, 13)] + [date(2026, m, 1) for m in range(1, 7)]

rng = random.Random(42)   # воспроизводимость


def rand_month() -> date:
    return rng.choice(MONTHS)


# ── Генераторы ────────────────────────────────────────────────────────────────

def gen_funnel(n_rows: int) -> list[dict]:
    """funnel_data.csv — воронка продаж."""
    STEPS = [
        (1, "предложение сформировано"),
        (2, "информирование о предложении"),
        (3, "клиент ознакомился"),
        (4, "переход к оформлению"),
        (5, "заявка подана"),
        (6, "одобрение"),
        (7, "выдача"),
    ]
    rows = []
    combos = [(p, c, d) for p in PRODUCTS for c in CHANNELS for d in MONTHS[-6:]]
    rng.shuffle(combos)
    for product, channel, dt in combos[:n_rows // len(STEPS) + 1]:
        base = rng.randint(50_000, 500_000)
        for sort, step_name in STEPS:
            base = int(base * rng.uniform(0.45, 0.85))
            rows.append({
                "report_dt":    dt.strftime("%Y-%m-%d"),
                "dash_channel": channel,
                "dash_product": product,
                "sort":         sort,
                "step_name":    step_name,
                "value":        max(base, 1),
            })
            if len(rows) >= n_rows:
                break
        if len(rows) >= n_rows:
            break
    return rows


def gen_complaints(n_rows: int) -> list[dict]:
    """complaints.csv — жалобы и обращения."""
    SUBJECTS_COMPLAINTS = [
        "Неверное списание", "Блокировка карты/счёта",
        "Начисление комиссии", "Ошибка перевода",
        "Отказ в кредите", "Некорректные проценты",
        "Проблема с мобильным приложением", "Долгое рассмотрение",
    ]
    SUBJECTS_REQUESTS = [
        "Запрос выписки", "Смена тарифа", "Подключение услуги",
        "Изменение лимита", "Консультация",
    ]
    rows = []
    for _ in range(n_rows):
        dt   = rand_month()
        flag = rng.choice(["Жалобы", "Жалобы", "Обращения"])  # жалоб чуть больше
        subjs = SUBJECTS_COMPLAINTS if flag == "Жалобы" else SUBJECTS_REQUESTS
        rows.append({
            "report_dt": dt.strftime("%Y-%m-%dT00:00:00+03:00"),
            "toxic_flag": flag,
            "unit":       rng.choice(UNITS),
            "subj":       rng.choice(subjs),
            "prd":        rng.choice(PRODUCTS),
            "sum_cnt":    rng.randint(1, 150),
        })
    return rows


def gen_client_metrics(n_rows: int) -> list[dict]:
    """client_metrics.csv — клиентские метрики (TAM/SAM/SOM)."""
    STEPS = [
        (1, "Рынок TAM",      "Общий размер рынка",           "TAM_GENERAL"),
        (2, "Доступный рынок SAM", "Целевой сегмент по критериям банка", "SAM_GENERAL"),
        (3, "Достижимый рынок SOM", "Реальная доля рынка",    "SOM_GENERAL"),
        (4, "Текущий портфель", "Активная клиентская база",   "CURRENT"),
        (5, "Целевой портфель", "План на конец года",         "TARGET"),
    ]
    rows = []
    for i, (product, dt) in enumerate(
        [(p, d) for p in PRODUCTS for d in MONTHS[-4:]]
    ):
        base = rng.randint(5_000_000, 50_000_000)
        for step_id, step_name, metodika, codename in STEPS:
            base = int(base * rng.uniform(0.3, 0.7))
            rows.append({
                "id":           len(rows) + 1,
                "unit":         rng.choice(UNITS),
                "product_name": product,
                "date_":        dt.strftime("%Y-%m-%dT00:00:00"),
                "fvalue":       max(base, 1000),
                "step_name":    step_name,
                "step_id":      step_id,
                "metodika":     metodika,
                "step_codename": codename,
            })
            if len(rows) >= n_rows:
                break
        if len(rows) >= n_rows:
            break
    return rows


def gen_clickstream(n_rows: int) -> list[dict]:
    """clickstream_monthly.csv — агрегированный кликстрим."""
    rows = []
    for _ in range(n_rows):
        sessions     = rng.randint(10_000, 500_000)
        clicks       = int(sessions * rng.uniform(0.05, 0.35))
        conversions  = int(clicks   * rng.uniform(0.02, 0.15))
        revenue      = conversions  * rng.randint(500, 15_000)
        rows.append({
            "report_dt":   rand_month().strftime("%Y-%m-%d"),
            "channel":     rng.choice(CHANNELS),
            "product":     rng.choice(PRODUCTS),
            "sessions":    sessions,
            "clicks":      clicks,
            "conversions": conversions,
            "revenue":     revenue,
        })
    return rows


# ── Реестр форматов ───────────────────────────────────────────────────────────

FORMATS = {
    "funnel":         (gen_funnel,         300),
    "complaints":     (gen_complaints,     300),
    "client_metrics": (gen_client_metrics, 200),
    "clickstream":    (gen_clickstream,    300),
}


def write_csv(rows: list[dict], out) -> None:
    if not rows:
        return
    writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Генерация синтетических CSV для тестирования отчётов MJ"
    )
    parser.add_argument("format", choices=list(FORMATS.keys()),
                        help="Формат данных")
    parser.add_argument("--rows", type=int, default=None,
                        help="Количество строк (по умолчанию зависит от формата)")
    parser.add_argument("--out", default=None,
                        help="Путь к выходному файлу (по умолчанию — stdout)")
    args = parser.parse_args()

    gen_fn, default_rows = FORMATS[args.format]
    n = args.rows or default_rows
    rows = gen_fn(n)

    if args.out:
        with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
            write_csv(rows, f)
        print(f"✓ Записано {len(rows)} строк → {args.out}", file=sys.stderr)
    else:
        out = StringIO()
        write_csv(rows, out)
        print(out.getvalue(), end="")


if __name__ == "__main__":
    main()
