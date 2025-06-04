import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
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
            f.write(str(error) + "\n")
        print("📝 已儲存 page_debug.html、screenshot.png 與 run.log 作為除錯資料")
    except Exception as e:
        print(f"⚠️ 儲存除錯資料失敗: {e}")

def check_price():
    print("🔍 開始查詢 Trip.com...")
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--remote-debugging-port=9222')
    options.add_argument('--window-size=1920,1080')
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )

    driver = None
    try:
        driver = webdriver.Chrome(options=options)

        print("🌐 前往 Trip.com 首頁...")
        driver.get(BASE_URL)

        print("📝 填寫搜尋條件...")
        wait = WebDriverWait(driver, 60)

        try:
            print("📝 選擇來回票...")
            round_trip = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[data-testid="flightType_RT"]')))
            driver.execute_script("arguments[0].click();", round_trip)  # 使用 JavaScript 點擊
            time.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            print(f"🚫 選擇來回票失敗：{str(e)}")
            # 備用選擇器（基於 aria-label）
            try:
                round_trip_label = wait.until(EC.element_to_be_clickable((By.XPATH, '//div[@aria-label="來回"]')))
                round_trip_label.click()
                time.sleep(random.uniform(0.5, 1.5))
            except Exception as e2:
                print(f"🚫 備用選擇器失敗：{str(e2)}")
                raise

        try:
            print("📝 輸入出發地...")
            depart_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[placeholder="出發地"]')))
            depart_input.click()
            depart_input.clear()
            depart_input.send_keys(DEPART_CITY)
            time.sleep(random.uniform(0.5, 1.5))
            wait.until(EC.element_to_be_clickable((By.XPATH, '//div[contains(text(), "台北 (TPE)") and contains(@class, "city-item")]'))).click()
        except Exception as e:
            print(f"🚫 輸入出發地失敗：{str(e)}")
            raise

        try:
            print("📝 輸入目的地...")
            arrive_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[placeholder="目的地"]')))
            arrive_input.click()
            arrive_input.clear()
            arrive_input.send_keys(ARRIVE_CITY)
            time.sleep(random.uniform(0.5, 1.5))
            wait.until(EC.element_to_be_clickable((By.XPATH, '//div[contains(text(), "奧斯陸 (OSL)") and contains(@class, "city-item")]'))).click()
        except Exception as e:
            print(f"🚫 輸入目的地失敗：{str(e)}")
            raise

        try:
            print("📝 選擇去程日期...")
            depart_date_input = wait.until(EC.element_to_be_clickable((By.XPATH, '//input[@placeholder="任何日期"]')))
            depart_date_input.click()
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[aria-label="2025年9月27日"]'))).click()
            time.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            print(f"🚫 選擇去程日期失敗：{str(e)}")
            raise

        try:
            print("📝 選擇回程日期...")
            return_date_input = wait.until(EC.element_to_be_clickable((By.XPATH, '(//input[@placeholder="任何日期"])[2]')))
            return_date_input.click()
            wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[aria-label="2025年10月11日"]'))).click()
            time.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            print(f"🚫 選擇回程日期失敗：{str(e)}")
            raise

        try:
            print("📝 提交搜尋...")
            search_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'div[data-testid="search_btn"]')))
            search_button.click()
        except Exception as e:
            print(f"🚫 提交搜尋失敗：{str(e)}")
            raise

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

    except (TimeoutException, NoSuchElementException, WebDriverException) as e:
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