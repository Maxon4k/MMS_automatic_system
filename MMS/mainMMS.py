import calendar
import os
import glob
import time
import shutil
import stat
import schedule
from datetime import datetime, date
from dotenv import load_dotenv
import numpy as np

import selenium_mms
import csv_processing_MMS
import excel_writer_MMS
import telegram_notifier
import monthly_template
import graf_update

load_dotenv()

HEADLESS_MODE = True


def create_backup(source_file, backup_dir, suffix):
    try:
        if not os.path.exists(source_file) or not os.path.exists(backup_dir): return
        name, ext = os.path.splitext(os.path.basename(source_file))
        new_filename = f"{name.replace('копія', '').strip()} {datetime.now().strftime('%m %d')} {suffix}{ext}"
        dest_path = os.path.join(backup_dir, new_filename)
        shutil.copyfile(source_file, dest_path)
        os.chmod(dest_path, stat.S_IWRITE)
        print(f"📦 Бекап {suffix} збережено.")
    except Exception as e:
        print(f"⚠️ Помилка бекапу: {e}")


def run_process_for_company(cfg, start_date=None, end_date=None):
    name = cfg['name']
    print(f"\n🚀 >>> ОБРОБКА: {name} <<<")

    # Передаємо стан HEADLESS_MODE в селеніум
    selenium_mms.run_downloader(cfg['key_path'], cfg['key_pass'], cfg['download_dir'],
                                start_date, end_date, use_headless=HEADLESS_MODE)
    time.sleep(5)

    csv_files = glob.glob(os.path.join(cfg['download_dir'], "*.csv"))
    if not csv_files:
        print(f"❌ CSV для {name} не знайдено.")
        return

    target_csv = max(csv_files, key=os.path.getmtime)
    if time.time() - os.path.getmtime(target_csv) > 300:
        print(f"❌ Новий файл не знайдено.")
        return

    print(f"📄 Обробка: {os.path.basename(target_csv)}")
    excel_writer_MMS.import_network_schedule(cfg['excel_path'], cfg['graf_path'])

    days_data = csv_processing_MMS.parse_csv_file(target_csv)

    if days_data:
        for t_date, data, report, ab_detail, group_status in days_data:
            daily_total = sum(np.sum(v) for v in data.values())
            sum_a = sum(v["A"] for v in ab_detail.values())
            sum_b = sum(v["B"] for v in ab_detail.values())

            print(f"\n▶️ Дата: {t_date.strftime('%d.%m.%Y')} | Сума: {daily_total:.4f} MWH")
            print(f"   Група A: {sum_a:.4f} MWH | Група B: {sum_b:.4f} MWH")

            successful = [region_name for region_name, status in report.items() if status in ("OK_AB", "OK_B")]

            # Регіони, де немає хоча б однієї з груп
            problems = []
            for region_name, gs in group_status.items():
                missing_groups = [g for g in ("A", "B") if not gs[g]]
                if missing_groups:
                    parts = ", ".join(f"Група {g} - немає" for g in missing_groups)
                    problems.append(f"{region_name}: {parts}")

            if successful:
                print(f"   ✅ ОСР з даними ({len(successful)}): {', '.join(successful)}")
            if problems:
                print(f"   ❌ Проблемні ОСР ({len(problems)}):")
                for p in problems:
                    print(f"      - {p}")

            msg_lines = [
                f"📊 <b>{name}</b> — {t_date.strftime('%d.%m.%Y')}",
                f"Група A: {sum_a:.4f} MWH",
                f"Група B: {sum_b:.4f} MWH",
                f"Разом: {daily_total:.4f} MWH",
            ]
            if problems:
                msg_lines.append("\n⚠️ Проблемні ОСР:")
                msg_lines.extend(problems)

            telegram_notifier.send_message("\n".join(msg_lines))

        excel_writer_MMS.write_data_to_master(cfg['excel_path'], days_data)
        create_backup(cfg['excel_path'], cfg['backup_dir'], name)
    else:
        print(
            f"⚠️ УВАГА: Файл CSV завантажився, але парсер не знайшов у ньому потрібних даних (можливо, на сайті за цей день пусто або змінився формат).")


def get_configs():
    return [

        {"name": "Goer", "key_path": os.getenv("GOER_KEY_PATH"), "key_pass": os.getenv("GOER_KEY_PASSWORD"),
        "download_dir": os.getenv("GOER_DOWNLOAD_DIR"), "excel_path": os.getenv("GOER_EXCEL_PATH"),
        "graf_path": os.getenv("GOER_GRAF_PATH"), "backup_dir": os.getenv("GOER_BACKUP_DIR")},
        {"name": "Lu", "key_path": os.getenv("LU_KEY_PATH"), "key_pass": os.getenv("LU_KEY_PASSWORD"),
        "download_dir": os.getenv("LU_DOWNLOAD_DIR"), "excel_path": os.getenv("LU_EXCEL_PATH"),
        "graf_path": os.getenv("LU_GRAF_PATH"), "backup_dir": os.getenv("LU_BACKUP_DIR")},
    ]


def daily_job():
    print(f"\n⏰ ЗАПУСК ЩОДЕННОЇ ВИГРУЗКИ")
    for cfg in get_configs():
        run_process_for_company(cfg)


def auto_monthly_reload():
    today = date.today()

    if today.day == 12:
        start_date_obj = date(today.year, today.month, 1)
        end_date_obj = date(today.year, today.month, 11)
    elif today.day == 23:
        start_date_obj = date(today.year, today.month, 12)
        end_date_obj = date(today.year, today.month, 22)
    elif today.day == 1:
        prev_month = today.month - 1 or 12
        prev_year = today.year if today.month > 1 else today.year - 1
        last_day = calendar.monthrange(prev_year, prev_month)[1]
        start_date_obj = date(prev_year, prev_month, 23)
        end_date_obj = date(prev_year, prev_month, last_day)
    else:
        return

    start_date = start_date_obj.strftime("%d%m%Y")
    end_date = end_date_obj.strftime("%d%m%Y")

    print(f"\n🔁 АВТО-ПЕРЕВИВАНТАЖЕННЯ ({today.day} числа): {start_date} - {end_date}")
    for cfg in get_configs():
        run_process_for_company(cfg, start_date, end_date)

def monthly_template_job():
    if not monthly_template.is_last_day_of_month():
        return
    print("\n📅 ОСТАННІЙ ДЕНЬ МІСЯЦЯ")
    results = monthly_template.run_monthly_maintenance(get_configs())
    for name, path in results:
        if path:
            telegram_notifier.send_message(f"📄 {name}: створено {os.path.basename(path)}")

def graf_check_job():
    print("\n🔎 ПЕРЕВІРКА ЗМІН У БЕКАПАХ")
    for cfg in get_configs():
        changed = graf_update.run_for_company(cfg)
        if changed:
            telegram_notifier.send_message(f"🟡 {cfg['name']}: знайдено зміни, графік оновлено")

def interval_job():
    print("\n--- РЕЖИМ ПЕРЕВИВАНТАЖЕННЯ ІНТЕРВАЛУ ---")
    start = input("Дата ПОЧАТКУ (ДДММРРРР): ")
    end = input("Дата КІНЦЯ (ДДММРРРР): ")
    for cfg in get_configs():
        run_process_for_company(cfg, start, end)


if __name__ == "__main__":
    #mode = input("Показувати вікно браузера? (y/n): ").lower()
    #HEADLESS_MODE = False if mode == 'y' else True

    print("\n1. Режим очікування (13:45)")
    print("\n2. Перевивантаження зараз")
    choice = input("\nВаш вибір: ")

    if choice == "1":
        print(f"🤖 Очікування 13:45 (Headless={HEADLESS_MODE})...")
        schedule.every().day.at("13:45").do(daily_job)
        schedule.every().day.at("13:00").do(auto_monthly_reload)
        schedule.every().day.at("14:45").do(monthly_template_job)
        schedule.every().day.at("15:05").do(graf_check_job)
        #daily_job()
        while True:
            schedule.run_pending()
            time.sleep(15)
    elif choice == "2":
        interval_job()