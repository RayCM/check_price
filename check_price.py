import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient
from linebot.v3.messaging.models import TextMessage, PushMessageRequest

# ===== LINE Bot 設定 =====
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
GROUP_ID = os.getenv("LINE_GROUP_ID")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
line_bot_api = MessagingApi(ApiClient(configuration))

# ===== 查詢條件 =====
TARGET_DEPART = '13:45'
TARGET_ARRIVE = '13:05'
PRICE_THRESHOLD = 41000
BASE_URL = 'https://tw.trip.com/flights/'
DEPART_CITY = 'TPE'
ARRIVE_CITY = 'OSL'
DEPART_DATE = '2025-09-27'
RETURN_DATE = '2025-10-11'

def send_line_notification(message):
    try:
        req = PushMessageRequest(to=GROUP_ID, messages=[TextMessage(text=message)])
        line_bot_api.push_message(req)
        print("✅ 成功發送 LINE 通知")
    except Exception as e:
        print("❌ 發送通知失敗：", e)

def extract_time_from_testid(testid):
    try:
        return testid.strip().split()[-1][:5]
    except Exception:
        return ''

def save_debug_files(driver, error):
    try:
        if driver:
            driver.save_screenshot("screenshot.png")
            with open("page_debug.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
        with open("run.log", "a", encoding="utf-8") as f:
            f.write(f"錯誤類型：{type(error).__name__}\n")
            f.write(f"錯誤訊息：{str(error)}\n")
            f.write(f"當前 URL：{driver.current_url if driver else 'N/A'}\n")
            f.write(f"當前 HTML 片段：{driver.page_source[:1000] if driver else 'N/A'}\n")
            f.write(f"堆棧追蹤：\n{str(error.__traceback__)}\n\n")
        print("📝 已儲存除錯資料")
    except Exception as e:
        print(f"⚠️ 儲存除錯資料失敗: {e}")

def try_form_action(description, action, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            print(f"📝 {description} (嘗試 {attempt+1}/{max_attempts})...")
            action()
            time.sleep(random.uniform(0.5, 1.5))
            return True
        except Exception as e:
            print(f"🚫 {description} 失敗：{str(e)}")
            if attempt == max_attempts - 1:
                raise
            time.sleep(2)
    return False

def ensure_dropdown_closed(driver):
    try:
        dropdown = driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="search_result_box"]')
        if dropdown:
            print("⚠️ 檢測到下拉選單，嘗試關閉...")
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(1)
            if driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="search_result_box"]'):
                driver.execute_script("document.body.click();")
                time.sleep(1)
        else:
            print("✅ 無下拉選單遮擋")
    except Exception as e:
        print(f"⚠️ 檢查下拉選單時出錯：{e}")

def handle_popups(driver):
    try:
        close_button = driver.find_element(By.XPATH, "//*[contains(text(), '不同意') or contains(text(), '關閉')]")
        driver.execute_script("arguments[0].click();", close_button)
        print("✅ 成功關閉通知彈窗")
    except NoSuchElementException:
        print("✅ 無通知彈窗")
    except Exception as e:
        print(f"⚠️ 處理通知彈窗時出錯：{e}")
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)

def select_date(driver, wait, date_input, target_date):
    driver.execute_script("arguments[0].click();", date_input)
    calendar = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'c-fuzzy-calendar')]")))
    month_header = calendar.find_element(By.XPATH, ".//div[contains(@class, 'c-fuzzy-calendar-month-header')]/span")
    current_month_text = month_header.text

    target_year, target_month = map(int, target_date.split('-')[:2])
    months = ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
    target_month_chinese = months[target_month - 1]
    target_year_month_chinese = f"{target_year} 年 {target_month_chinese}"

    while current_month_text != target_year_month_chinese:
        next_button = calendar.find_element(By.XPATH, ".//div[contains(@class, 'c-fuzzy-calendar-icon-next')]")
        if 'disabled' in next_button.get_attribute('class'):
            raise Exception(f"無法切換到 {target_year_month_chinese}")
        driver.execute_script("arguments[0].click();", next_button)
        wait.until(EC.staleness_of(month_header))
        month_header = calendar.find_element(By.XPATH, ".//div[contains(@class, 'c-fuzzy-calendar-month-header')]/span")
        current_month_text = month_header.text

    day = target_date.split('-')[2].lstrip("0")
    date_element = calendar.find_element(By.XPATH, f".//span[text()='{day}']")
    wait.until(EC.element_to_be_clickable(date_element))
    driver.execute_script("arguments[0].click();", date_element)

def check_price():
    print("🔍 開始查詢 Trip.com...")
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    options.add_argument(f'user-agent={random.choice(user_agents)}')

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(BASE_URL)
        wait = WebDriverWait(driver, 120)
        handle_popups(driver)

        try_form_action("選擇來回票", lambda: driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[data-testid="flightType_RT"]')))))

        try_form_action("輸入出發地", lambda: (
            lambda wrapper: (
                driver.execute_script("arguments[0].click();", wrapper.find_element(By.CSS_SELECTOR, 'input[data-testid="search_city_from0"]')),
                wrapper.find_element(By.CSS_SELECTOR, 'input[data-testid="search_city_from0"]').send_keys(DEPART_CITY),
                wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[data-testid="0"]'))),
                driver.execute_script("arguments[0].click();", driver.find_element(By.CSS_SELECTOR, 'div[data-testid="0"]'))
            )
        )(wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="search_city_from0_wrapper"]')))))

        try_form_action("輸入目的地", lambda: (
            lambda wrapper: (
                driver.execute_script("arguments[0].click();", wrapper.find_element(By.CSS_SELECTOR, 'input[data-testid="search_city_to0"]')),
                wrapper.find_element(By.CSS_SELECTOR, 'input[data-testid="search_city_to0"]').send_keys(ARRIVE_CITY),
                wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[data-testid="0"]'))),
                driver.execute_script("arguments[0].click();", driver.find_element(By.CSS_SELECTOR, 'div[data-testid="0"]')),
                ensure_dropdown_closed(driver)
            )
        )(wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="search_city_to0_wrapper"]')))))

        try_form_action("選擇去程日期", lambda: select_date(driver, wait, wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[data-testid="search_date_depart0"]'))), DEPART_DATE))

        try_form_action("選擇回程日期", lambda: select_date(driver, wait, wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[data-testid="search_date_return0"]'))), RETURN_DATE))

        try_form_action("提交搜尋", lambda: driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[data-testid="search_btn"]')))))

        print("⌛ 等待搜尋結果頁面...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-price]')))
        trip_url = driver.current_url
        print(f"🔗 搜尋結果 URL: {trip_url}")

        cards = driver.find_elements(By.CSS_SELECTOR, '.result-item')
        print(f"✈️ 找到 {len(cards)} 筆航班")

        found = False
        for card in cards:
            try:
                depart = card.find_element(By.CSS_SELECTOR, '.is-departure_2a2b .time_cbcc').get_attribute('data-testid')
                arrive = card.find_element(By.CSS_SELECTOR, '.is-arrival_f407 .time_cbcc').get_attribute('data-testid')
                depart_time = extract_time_from_testid(depart)
                arrive_time = extract_time_from_testid(arrive)
                price = int(card.find_element(By.CSS_SELECTOR, '[data-price]').get_attribute('data-price'))

                print(f"📋 出發：{depart_time}，抵達：{arrive_time}，票價：{price}")
                if depart_time == TARGET_DEPART and arrive_time == TARGET_ARRIVE:
                    print("✅ 找到符合時間的航班")
                    found = True
                    if price <= PRICE_THRESHOLD:
                        msg = f'🚨 發現低價票！\n出發：{depart_time} OSL\n抵達：{arrive_time} TPE\n票價：{price} 元\n👉 {trip_url}'
                        send_line_notification(msg)
                    else:
                        print(f"⚠️ 價格太高：{price} > {PRICE_THRESHOLD}")
                    break
            except Exception as e:
                print("⚠️ 解析航班時出錯：", e)

        if not found:
            print("❗ 沒有找到符合條件的航班")

    except (TimeoutException, NoSuchElementException, WebDriverException) as e:
        print("🚫 Selenium 錯誤：", e)
        save_debug_files(driver, e)
    finally:
        if driver:
            driver.quit()
            print("🧹 WebDriver 已關閉")

if __name__ == "__main__":
    check_price()