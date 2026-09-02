import os
import time
import glob
from datetime import datetime, timedelta

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys

# --- КОНФІГУРАЦІЯ ---
load_dotenv()
KEY_PASSWORD = os.getenv("KEY_PASSWORD2")
KEY_PATH = os.getenv("KEY_PATH2")
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR")


def run_downloader(key_path=None, key_password=None, download_dir=None, start_date=None, end_date=None,
                   use_headless=True):
    """
    Універсальна функція завантаження.
    Якщо дати не передані, завантажує за вчора.
    Якщо передані різні дати — активує режим 'Інтервал (погодинно)'.
    """
    # Використовуємо передані параметри або значення з .env за замовчуванням
    k_path = key_path if key_path else KEY_PATH
    k_pass = key_password if key_password else KEY_PASSWORD
    d_dir = download_dir if download_dir else DOWNLOAD_DIR

    # Визначаємо дати
    if not start_date:
        start_date = (datetime.now() - timedelta(days=1)).strftime("%d%m%Y")
    if not end_date:
        end_date = start_date

    is_interval = start_date != end_date

    print(f"🚀 Запуск Selenium ({'ІНТЕРВАЛ' if is_interval else 'ЩОДЕННО'}): {start_date} - {end_date}")
    print(f"🖥️ Режим Headless: {use_headless}")

    chrome_options = Options()
    if use_headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")

    absolute_download_path = os.path.abspath(d_dir) if d_dir else os.path.join(os.path.expanduser("~"), "Downloads")
    if not os.path.exists(absolute_download_path):
        os.makedirs(absolute_download_path)

    prefs = {
        "download.default_directory": absolute_download_path,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
        "profile.default_content_settings.popups": 0
    }
    chrome_options.add_experimental_option("prefs", prefs)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    # Дозвіл на завантаження файлів у фоновому режимі
    driver.execute_cdp_cmd("Page.setDownloadBehavior", {
        "behavior": "allow",
        "downloadPath": absolute_download_path
    })

    wait = WebDriverWait(driver, 40)

    try:
        # --- АВТОРИЗАЦІЯ ---
        driver.get("https://mms.ua.energy/sign-in")

        try:
            cookie_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"))
            )
            cookie_btn.click()
            print("✅ Банер Cookies закрито.")
        except:
            print("ℹ️ Банер Cookies не з'явився.")

        print("Крок 1: Вхід через ЦСК...")
        btn_signin = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Sign in with Certification Centre')]")))
        driver.execute_script("arguments[0].click();", btn_signin)
        time.sleep(3)

        print("Вибір типу носія: Файловий носій...")
        file_method = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Файловий носій')]")))
        driver.execute_script("arguments[0].click();", file_method)
        time.sleep(3)

        print("Крок 2: Вибір АЦСК...")
        select_element = wait.until(EC.presence_of_element_located((By.ID, "CAsServersSelect")))
        select = Select(select_element)
        try:
            select.select_by_value("24")
        except:
            select.select_by_visible_text('КНЕДП ТОВ "Центр сертифікації ключів "Україна"')
        time.sleep(3)

        print("Крок 3: Завантаження ключа...")
        file_input = driver.find_element(By.ID, "PKeyFileInput")
        file_input.send_keys(os.path.abspath(k_path))
        time.sleep(3)

        print("Крок 4: Введення пароля...")
        password_field = driver.find_element(By.ID, "PKeyPassword")
        password_field.send_keys(k_pass)
        time.sleep(3)

        print("Крок 5: Натискання Продовжити...")
        btn_login = driver.find_element(By.ID, "id-app-login-sign-form-file-key-sign-button")
        driver.execute_script("arguments[0].click();", btn_login)

        print("Очікуємо завантаження кабінету...")
        time.sleep(5)

        print("Крок 6: Підтвердження угоди...")
        try:
            btn_accept = wait.until(EC.element_to_be_clickable((By.ID, "btnAcceptUserDataAgreement")))
            driver.execute_script("arguments[0].click();", btn_accept)
            time.sleep(3)
        except:
            print("Угода не з'явилась або вже прийнята.")

        # --- НАВІГАЦІЯ ---
        print("Крок 7: Відкриття Балансування NEW...")
        btn_menu = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(), 'Балансування NEW')]]")))
        driver.execute_script("arguments[0].click();", btn_menu)
        time.sleep(5)

        print("Крок 8: Перехід до компонентів...")
        btn_components = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[@role='menuitem' and contains(., 'Компоненти балансування')]")))
        driver.execute_script("arguments[0].click();", btn_components)

        print("Сторінка компонентів завантажена. Чекаємо ініціалізації таблиці...")
        time.sleep(5)

        # Перемикання в iFrame
        iframe = wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
        driver.switch_to.frame(iframe)

        # Крок 9: Вибір типу даних (Робимо ПЕРЕД датами)
        print("Крок 9: Вибір типу даних...")
        dropdowns = driver.find_elements(By.CSS_SELECTOR, ".p-dropdown")
        if dropdowns:
            driver.execute_script("arguments[0].click();", dropdowns[0])
            time.sleep(1)
            option = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//li[contains(@aria-label, 'Вимірювані дані')]")))
            driver.execute_script("arguments[0].click();", option)
            time.sleep(3)

        # ВИБІР ПЕРІОДУ (Тільки якщо Інтервал)
        if is_interval:
            print("⚙️ Обираємо 'Інтервал (погодинно)'...")
            period_dd = wait.until(EC.element_to_be_clickable((By.ID, "timeInterval")))
            driver.execute_script("arguments[0].click();", period_dd)
            time.sleep(1.5)
            actions = webdriver.ActionChains(driver)
            actions.send_keys(Keys.END).send_keys(Keys.ENTER).perform()
            time.sleep(3)
            # Розблокування поля "До"
            driver.execute_script("document.getElementById('to').classList.remove('p-calendar-disabled');")
            driver.execute_script("document.getElementsByName('to')[0].removeAttribute('disabled');")
            time.sleep(2)

        # ФУНКЦІЯ ВВОДУ
        def type_date(xpath, d_str, label=""):
            print(f"✍️ Введення дати {label}: {d_str}")
            el = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
            driver.execute_script("arguments[0].click(); arguments[0].focus();", el)
            time.sleep(0.8)
            el.send_keys(Keys.CONTROL + "a")
            time.sleep(0.2)
            el.send_keys(Keys.BACKSPACE)
            time.sleep(1.0)
            for ch in d_str:
                el.send_keys(ch)
                time.sleep(0.3)
            # Фіксація через JS події
            driver.execute_script(
                "arguments[0].dispatchEvent(new Event('input', { bubbles: true })); arguments[0].dispatchEvent(new Event('change', { bubbles: true })); arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));",
                el)
            time.sleep(0.5)
            el.send_keys(Keys.TAB)

        # Введення дати ВІД (Виконується ЗАВЖДИ)
        type_date("//span[@id='from']//input", start_date, "ВІД")

        # Введення дати ДО (Тільки якщо Інтервал)
        if is_interval:
            print("⏳ Очікуємо стабілізації сайту...")
            time.sleep(3.0)
            date_input_to = wait.until(EC.presence_of_element_located((By.XPATH, "//span[@id='to']//input")))
            driver.execute_script(
                "arguments[0].removeAttribute('disabled'); arguments[0].classList.remove('p-disabled'); arguments[0].parentElement.classList.remove('p-calendar-disabled');",
                date_input_to)
            time.sleep(1.0)
            type_date("//span[@id='to']//input", end_date, "ДО")

        # ПРИБРАНО: Фінальне натискання ENTER
        # driver.find_element(By.XPATH, "//span[@id='from']//input").send_keys(Keys.ENTER)

        print("✅ Дати введені, переходимо до налаштувань таблиці...")
        time.sleep(2)

        print("Крок 11: Пагінація 100...")
        dropdown_pagination = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//div[contains(@class, 'p-paginator')]//div[contains(@class, 'p-dropdown')]"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", dropdown_pagination)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", dropdown_pagination)

        option_100 = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//li[contains(@class, 'p-dropdown-item') and normalize-space(.)='100']"))
        )
        driver.execute_script("arguments[0].click();", option_100)
        time.sleep(3)

        print("Крок 12: Вибір всіх елементів...")
        try:
            target_element = wait.until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//thead//input[contains(@class, 'p-checkbox-input') and contains(@aria-label, 'All items')]"
                ))
            )
            driver.execute_script("arguments[0].click();", target_element)
        except Exception as e:
            print(f"Помилка чекбоксу 'Всі': {e}")

        time.sleep(2)

        print("Крок 13: Зняття GENERATION")
        try:
            generation_checkboxes = driver.find_elements(By.XPATH,
                                                         "//tr[.//div[normalize-space()='GENERATION']]//input[@type='checkbox']")
            for checkbox in generation_checkboxes:
                if checkbox.get_attribute("aria-checked") == "true":
                    driver.execute_script("arguments[0].click();", checkbox)
        except Exception as e:
            print(f"Помилка при знятті GENERATION: {e}")

        time.sleep(2)

        print("Крок 14: Звіт...")
        try:
            report_dropdown = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//div[@role='button' and @aria-label='Вибрати мітку']"))
            )
            driver.execute_script("arguments[0].click();", report_dropdown)

            last_rep = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//li[normalize-space()='останній доступний']"))
            )
            driver.execute_script("arguments[0].click();", last_rep)
        except Exception as e:
            print(f"Помилка звіту: {e}")

        time.sleep(5)

        print("Крок 15: Графік")
        try:
            show_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Показати часові ряди']"))
            )
            driver.execute_script("arguments[0].click();", show_btn)
            time.sleep(3)
        except Exception as e:
            print(f"Помилка графіку: {e}")

        #print("Крок 16: Зміна одиниць на MWH")
        #try:
        #    unit_trigger = wait.until(
        #        EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='button'][aria-label='Select Unit']"))
        #    )
        #   driver.execute_script("arguments[0].click();", unit_trigger)
        #    time.sleep(2)
        #    mwh_option = wait.until(
        #        EC.element_to_be_clickable(
        #            (By.XPATH, "//li[contains(@class, 'p-dropdown-item') and normalize-space(.)='MWH']"))
        #   )
        #    driver.execute_script("arguments[0].click();", mwh_option)
        #    time.sleep(5)
        #except Exception as e:
        #    print(f"Помилка зміни одиниць: {e}")

        print("Крок 17: Чекбокс 'Зріз даних'")
        try:
            target_checkbox = wait.until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//div[contains(text(), 'Зріз даних')]/preceding-sibling::div//input[contains(@class, 'p-checkbox-input')]"
                ))
            )
            driver.execute_script("arguments[0].click();", target_checkbox)
            time.sleep(3)
        except Exception as e:
            print(f"Помилка чекбокса 'Зріз даних': {e}")

        print("Крок 18: Натискання кнопки 'Завантажити CSV'...")
        try:
            download_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Завантажити CSV']"))
            )
            driver.execute_script("arguments[0].click();", download_btn)
            print("✅ Завантаження CSV ініційовано. Очікуємо 10с...")

            seconds_waited = 0
            while seconds_waited < 30:  # Чекаємо максимум 30 секунд
                time.sleep(1)
                seconds_waited += 1
                # Перевіряємо, чи є в папці недокачані файли .crdownload
                crdownloads = glob.glob(os.path.join(absolute_download_path, "*.crdownload"))
                if not crdownloads and glob.glob(os.path.join(absolute_download_path, "export*.csv")):
                    break  # Файл докачався, виходимо з циклу

            # Перейменування файлу для унікальності
            files = glob.glob(os.path.join(absolute_download_path, "export*.csv"))
            if files:
                latest = max(files, key=os.path.getmtime)
                new_name = os.path.join(absolute_download_path, f"mms_{start_date}_{end_date}.csv")
                os.rename(latest, new_name)
                print(f"📦 Файл збережено як: {os.path.basename(new_name)}")

        except Exception as e:
            print(f"ПОМИЛКА завантаження: {e}")

    except Exception as e:
        print(f"❌ CRITICAL ERROR IN SELENIUM: {e}")
        driver.save_screenshot("debug_error.png")
        import traceback
        traceback.print_exc()

    finally:
        print("Закриття браузера...")
        driver.quit()


if __name__ == "__main__":
    run_downloader()