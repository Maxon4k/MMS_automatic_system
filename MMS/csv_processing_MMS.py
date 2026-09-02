import pandas as pd
import numpy as np
import re
from datetime import datetime

# Конфігурація залишається, вона спільна для обох компаній
REGION_CONFIG = {
    "Чернівці": {"id": "00300", "sum_ab": True},
    "Прикарпаття": {"id": "00800", "sum_ab": True},
    "Тернопіль": {"id": "00200", "sum_ab": True},
    "Київ": {"id": "03000", "sum_ab": True},
    "Вінниця": {"id": "00100", "sum_ab": True},
    "Закарпаття": {"id": "00701", "sum_ab": True},
    "Запоріжжя": {"id": "00400", "sum_ab": True},
    "КРЕМ": {"id": "02200", "sum_ab": True},
    "Одеса": {"id": "01000", "sum_ab": True},
    "Хмельницьк": {"id": "01800", "sum_ab": True},
    "Полтава": {"id": "01100", "sum_ab": True},
    "Миколаїв": {"id": "02500", "sum_ab": True},
    "Черкаси": {"id": "01900", "sum_ab": True},
    "Укрзалізниця": {"id": "02900", "sum_ab": True},
    "Дніпро": {"id": "02400", "sum_ab": True},
    "ПЕЕМ ЦЕК": {"id": "02700", "sum_ab": True},
    "Кіровоград": {"id": "02100", "sum_ab": True},
    "Рівне": {"id": "01500", "sum_ab": True},
    "Волинь": {"id": "00600", "sum_ab": True},
    "Чернігів": {"id": "02000", "sum_ab": True},
    "Суми": {"id": "02300", "sum_ab": True},
    "Львів": {"id": "00900", "sum_ab": True},
    "Житомир": {"id": "01600", "sum_ab": True},
    "Харків": {"id": "01200", "sum_ab": True},
    "Регіональні електромережі":{"id": "02800", "sum_ab": True},
}


def get_column_data(df, mga_id, type_char, row_indices):
    pattern = f"MGA-{mga_id}.*-{type_char}_"
    found_col = next((col for col in df.columns if re.search(pattern, str(col))), None)
    if found_col:
        # Вибираємо тільки ті рядки, які належать поточному дню
        series = df.loc[row_indices, found_col].copy()
        series = series.astype(str).str.replace(',', '.', regex=False).str.strip()
        vals = pd.to_numeric(series, errors='coerce').fillna(0).values

        # Якщо годин 23, додаємо 0 на місце 3-ї години або в кінець,
        # щоб результати завжди мали довжину 24 (для сумісності з іншим кодом)
        if len(vals) == 23:
            vals = np.insert(vals, 3, 0)  # Вставляємо 0 як 3-тю годину
        return vals
    return None


def parse_csv_file(filepath):
    print(f"🔄 Аналіз CSV (багатоденний режим): {filepath}")
    try:
        # 1. Зчитуємо файл
        df = pd.read_csv(filepath, sep=';', header=0)

        # 2. Витягуємо дату з першого стовпця для кожного рядка
        df['parsed_date'] = df.iloc[:, 0].str.extract(r'(\d{2}\.\d{2}\.\d{4})')[0]

        all_days_data = []

        # 3. Групуємо дані за датою
        for date_str, group in df.groupby('parsed_date', sort=False):
            target_date = datetime.strptime(date_str, "%d.%m.%Y")
            row_indices = group.index

            hours_in_day = len(group)
            results = {}
            status_report = {}
            ab_detail = {}
            group_status = {}  # NEW: {"A": bool, "B": bool} по кожному регіону

            for name, config in REGION_CONFIG.items():
                vals_a = get_column_data(df, config['id'], "A", row_indices)
                vals_b = get_column_data(df, config['id'], "B", row_indices)

                group_status[name] = {"A": vals_a is not None, "B": vals_b is not None}

                if vals_a is None and vals_b is None:
                    status_report[name] = "MISSING_B"
                    results[name] = np.zeros(24)
                    ab_detail[name] = {"A": 0.0, "B": 0.0}
                else:
                    a_clean = vals_a if vals_a is not None else np.zeros(24)
                    b_clean = vals_b if vals_b is not None else np.zeros(24)
                    status_report[name] = "OK_AB" if vals_a is not None and vals_b is not None else "OK_B"

                    results[name] = (a_clean + b_clean) / 1000.0
                    ab_detail[name] = {
                        "A": float(np.sum(a_clean) / 1000.0),
                        "B": float(np.sum(b_clean) / 1000.0),
                    }

            print(f"✅ Оброблено {date_str}: {hours_in_day} год.")
            all_days_data.append((target_date, results, status_report, ab_detail, group_status))

        return all_days_data
    except Exception as e:
        print(f"❌ Помилка CSV: {e}")
        import traceback
        traceback.print_exc()  # Це допоможе побачити де саме помилка
        return []