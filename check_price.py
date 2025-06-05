import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, ElementClickInterceptedException
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
DEPART_DATE = '2025-09-27'  # 目標出發日期
RETURN_DATE = '2025-10-11'  # 目標回程日期

def send_line_notification(message):
    try:
        req = PushMessageRequest(
            to=GROUP_ID,
            messages=[TextMessage(text=message)]
        )
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
        print("📝 已儲存 page_debug.html、screenshot.png 與 run.log 作為除錯資料")
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

def ensure_dropdown_closed(driver, wait):
    try:
        dropdown = driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="search_result_box"]')
        if dropdown:
            print("⚠️ 檢測到下拉選單，嘗試關閉...")
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
            time.sleep(1)
            if driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="search_result_box"]'):
                print("⚠️ 下拉選單仍未關閉，嘗試點擊空白區域...")
                driver.execute_script("document.body.click();")
                time.sleep(1)
        else:
            print("✅ 無下拉選單遮擋")
    except Exception as e:
        print(f"⚠️ 檢查下拉選單時出錯：{e}")

def handle_popups(driver, wait):
    try:
        # 等待通知彈窗出現，最多 5 秒
        notification_popup = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '允許通知')]")))
        print("⚠️ 檢測到通知彈窗，嘗試關閉...")
        try:
            close_button = driver.find_element(By.XPATH, "//*[contains(text(), '不同意') or contains(text(), '關閉')]")
            close_button.click()
            print("✅ 成功關閉通知彈窗")
        except NoSuchElementException:
            print("⚠️ 找不到關閉按鈕，模擬按下 ESC 鍵...")
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        time.sleep(1)
    except TimeoutException:
        print("✅ 無通知彈窗")
    except Exception as e:
        print(f"⚠️ 處理通知彈窗時出錯：{e}")

def check_price():
    print("🔍 開始查詢 Trip.com...")
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--remote-debugging-port=9222')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--enable-logging')  # 啟用瀏覽器日誌
    options.add_argument('--disable-extensions')  # 禁用擴充功能
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    options.add_argument(f'user-agent={random.choice(user_agents)}')

    driver = None
    try:
        driver = webdriver.Chrome(options=options)

        print("🌐 前往 Trip.com 首頁...")
        driver.get(BASE_URL)

        wait = WebDriverWait(driver, 120)

        handle_popups(driver, wait)

        print("📝 填寫搜尋條件...")

        try_form_action("選擇來回票", lambda: driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[data-testid="flightType_RT"]')))))

        try_form_action("輸入出發地", lambda: (
            lambda depart_wrapper: (
                driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'i[data-testid="cityLabel_delete_0"]')))) if driver.find_elements(By.CSS_SELECTOR, 'i[data-testid="cityLabel_delete_0"]') else None,
                time.sleep(0.5),
                driver.execute_script("arguments[0].click();", depart_wrapper.find_element(By.CSS_SELECTOR, 'input[data-testid="search_city_from0"]')),
                depart_wrapper.find_element(By.CSS_SELECTOR, 'input[data-testid="search_city_from0"]').send_keys(DEPART_CITY),
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="search_result_box"]'))),
                wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[data-testid="0"]'))),
                driver.execute_script("arguments[0].click();", driver.find_element(By.CSS_SELECTOR, 'div[data-testid="0"]'))
            )
        )(wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="search_city_from0_wrapper"]')))))

        try_form_action("輸入目的地", lambda: (
            lambda arrive_wrapper: (
                driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'i[data-testid="cityLabel_delete_0"]')))) if driver.find_elements(By.CSS_SELECTOR, 'i[data-testid="cityLabel_delete_0"]') else None,
                time.sleep(0.5),
                driver.execute_script("arguments[0].click();", arrive_wrapper.find_element(By.CSS_SELECTOR, 'input[data-testid="search_city_to0"]')),
                arrive_wrapper.find_element(By.CSS_SELECTOR, 'input[data-testid="search_city_to0"]').send_keys(ARRIVE_CITY),
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="search_result_box"]'))),
                wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[data-testid="0"]'))),
                driver.execute_script("arguments[0].click();", driver.find_element(By.CSS_SELECTOR, 'div[data-testid="0"]')),
                arrive_wrapper.find_element(By.CSS_SELECTOR, 'input[data-testid="search_city_to0"]').send_keys(Keys.ENTER),
                ensure_dropdown_closed(driver, wait)
            )
        )(wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="search_city_to0_wrapper"]')))))

        # 直接設定去程日期
        try_form_action("設定去程日期", lambda: (
            depart_date_input := wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[data-testid="search_date_depart0"]'))),
            depart_date_input.clear(),
            depart_date_input.send_keys(DEPART_DATE)  # 注意：如果 YYYY-MM-DD 格式無效，請檢查輸入框格式（例如改為 27/09/2025）
        ))

        # 直接設定回程日期
        try_form_action("設定回程日期", lambda: (
            return_date_input := wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[data-testid="search_date_return0"]'))),
            return_date_input.clear(),
            return_date_input.send_keys(RETURN_DATE)  # 注意：如果 YYYY-MM-DD 格式無效，請檢查輸入框格式（例如改為 11/10/2025）
        ))

        try_form_action("提交搜尋", lambda: driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[data-testid="search_btn"]')))))

        print("⌛ 等待搜尋結果頁面...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-price]')))
        trip_url = driver.current_url
        print(f"🔗 獲取搜尋結果 URL: {trip_url}")

        print("✈️ 解析航班資料...")
        cards = driver.find_elements(By.CSS_SELECTOR, '.result-item')
        print(f"✈️ 找到 {len(cards)} 筆航班")

        found = False
        for card in cards:
            try:
                depart = card.find_element(By.CSS_SELECTOR, '.is-departure_2a2b .time_cbcc').get_attribute('data-testid')
                arrive = card.find_element(By.CSS_SELECTOR, '.is-arrival_f407 .time_cbcc').get_attribute('data-testid')
                depart_time = extract_time_from_testid(depart)
                arrive_time = extract_time_from_testid(arrive)

                price_el = card.find_element(By.CSS_SELECTOR, '[data-price]')
                price = int(price_el.get_attribute('data-price'))

                print(f"📋 出發：{depart_time}，抵達：{arrive_time}，票價：{price}")

                if depart_time == TARGET_DEPART and arrive_time == TARGET_ARRIVE:
                    print("✅ 找到符合時間的航班")
                    found = True
                    if price <= PRICE_THRESHOLD:
                        print("💰 價格也符合條件，將發送通知")
                        msg = f'🚨 發現低價票！\n出發：{depart_time} OSL\n抵達：{arrive_time} TPE\n票價：{price} 元\n👉 {trip_url}'
                        send_line_notification(msg)
                    else:
                        print(f"⚠️ 價格太高：{price} > {PRICE_THRESHOLD}，不發送通知")
                    break

            except Exception as e:
                print("⚠️ 某筆航班解析失敗：", e)

        if not found:
            print("❗ 沒有找到符合條件的航班")

    except (TimeoutException, NoSuchElementException, WebDriverException, ElementClickInterceptedException) as e:
        print("🚫 Selenium 錯誤：", e)
        save_debug_files(driver, e)
    except Exception as e:
        print("🚫 其他錯誤：", e)
        save_debug_files(driver, e)
    finally:
        if driver:
            driver.quit()
            print("🧹 WebDriver 已關閉")

if __name__ == "__main__":
    check_price()