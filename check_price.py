import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
PRICE_THRESHOLD = 50000

TRIP_URL = 'https://tw.trip.com/flights/ShowFareNext?lowpricesource=searchform&triptype=RT&class=Y&quantity=1&childqty=0&babyqty=0&jumptype=GoToNextJournay&dcity=tpe&acity=osl&aairport=osl&ddate=2025-09-27&dcityName=Taipei&acityName=Oslo&rdate=2025-10-11&currentseqno=2&criteriaToken=SGP_SGP-ALI_PIDReduce-5a93837e-5859-4c5d-8458-3f04ce82331e%5EList-b93dcabd-4769-4951-8057-5f16d6a9c43f&shoppingid=SGP_SGP-ALI_PIDReduce-d4e23ca5-72a8-4389-97b7-5a3b20fe38e4%5EList-47ba7440-8114-4410-85d5-69e76481d8b6&groupKey=SGP_SGP-ALI_PIDReduce-d4e23ca5-72a8-4389-97b7-5a3b20fe38e4%5EList-47ba7440-8114-4410-85d5-69e76481d8b6&locale=zh-TW&curr=TWD'  # ⚠️ 替換為你自己的網址

# ===== LINE 通知函式 =====
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

# ===== 擷取時間字串 =====
def extract_time_from_testid(testid):
    try:
        return testid.strip().split()[-1][:5]
    except Exception as e:
        print("⚠️ 時間解析錯誤：", e)
        return ''

# ===== 主查詢邏輯 =====
def check_price():
    print("🔍 開始查詢 Trip.com...")

    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(options=options)

    try:
        print("🌐 前往 Trip.com 網頁中...")
        driver.get(TRIP_URL)

        print("⌛ 等待航班清單載入...")
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.result-item'))
        )

        cards = driver.find_elements(By.CSS_SELECTOR, '.result-item')
        print(f"✈️ 找到 {len(cards)} 筆航班")

        found = False

        for card in cards:
            try:
                depart_el = card.find_element(By.CSS_SELECTOR, '.is-departure_2a2b .time_cbcc')
                arrive_el = card.find_element(By.CSS_SELECTOR, '.is-arrival_f407 .time_cbcc')

                depart_time = extract_time_from_testid(depart_el.get_attribute('data-testid'))
                arrive_time = extract_time_from_testid(arrive_el.get_attribute('data-testid'))

                price_el = card.find_element(By.CSS_SELECTOR, '.select-area-price [data-price]')
                price = int(price_el.get_attribute('data-price'))

                print(f"📋 出發：{depart_time}，抵達：{arrive_time}，票價：{price}")

                if depart_time == TARGET_DEPART and arrive_time == TARGET_ARRIVE:
                    print("✅ 找到符合條件的航班")
                    found = True
                    if price <= PRICE_THRESHOLD:
                        message = (
                            f'🚨 發現低價票！\n'
                            f'去程：{depart_time} OSL\n'
                            f'回程：{arrive_time} TPE\n'
                            f'票價：{price} 元\n👉 {TRIP_URL}'
                        )
                        send_line_notification(message)
                    else:
                        print("⚠️ 時間符合，但票價高於門檻")
                    break

            except Exception as e:
                print("⚠️ 某筆航班解析失敗：", e)
                continue

        if not found:
            print("❗ 沒有找到符合條件的航班")

    except Exception as e:
        print("🚫 整體錯誤：", e)
        with open("page_debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

    finally:
        driver.quit()
        print("🧹 WebDriver 已關閉")

# ===== 執行程式 =====
if __name__ == "__main__":
    check_price()
