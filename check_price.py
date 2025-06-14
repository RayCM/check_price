import os
import time
import re
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
PRICE_THRESHOLD = 41000
TRIP_URL = 'https://tw.trip.com/flights/ShowFareNext?lowpricesource=searchform&triptype=RT&class=Y&quantity=1&childqty=0&babyqty=0&jumptype=GoToNextJournay&dcity=tpe&acity=osl&dairport=tpe&aairport=osl&ddate=2025-09-27&dcityName=Taipei&acityName=Oslo&rdate=2025-10-11&currentseqno=2&criteriaToken=SGP_SGP-ALI_PIDReduce-abc523f1-244d-4275-ae09-2fd3deb41511%5EList-a3bc3d8b-89b8-4386-b257-2eebb0a511a4&shoppingid=SGP_SGP-ALI_PIDReduce-fe7d4a8a-29c0-4ce2-b6b7-6af8c32bcf5b%5EList-e71ea733-b4d7-4752-b48f-a302b01f9bac&groupKey=SGP_SGP-ALI_PIDReduce-fe7d4a8a-29c0-4ce2-b6b7-6af8c32bcf5b%5EList-e71ea733-b4d7-4752-b48f-a302b01f9bac&locale=zh-TW&curr=TWD'

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
    except:
        return ''

def parse_price_text(text):
    try:
        # 移除 "NT$" 與 ","，轉換為整數
        return int(text.replace("NT$", "").replace(",", "").strip())
    except:
        return None

def check_price():
    print("🔍 開始查詢 Trip.com...")

    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )

    driver = webdriver.Chrome(options=options)

    try:
        print("🌐 前往 Trip.com 網頁中...")
        driver.get(TRIP_URL)

        print("⌛ 等待票價資料出現...")
        WebDriverWait(driver, 90).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-price]'))
        )

        print("⏳ 等待 JavaScript 完整渲染...")
        time.sleep(5)

        cards = driver.find_elements(By.CSS_SELECTOR, '.result-item')
        print(f"✈️ 找到 {len(cards)} 筆航班")

        found = False

        for card in cards:
            try:
                depart = card.find_element(By.CSS_SELECTOR, '.is-departure_2a2b .time_cbcc').get_attribute('data-testid')
                arrive = card.find_element(By.CSS_SELECTOR, '.is-arrival_f407 .time_cbcc').get_attribute('data-testid')
                depart_time = extract_time_from_testid(depart)
                arrive_time = extract_time_from_testid(arrive)

                # 改用從 aria-label 裡擷取價格
                price_aria = card.find_element(By.CSS_SELECTOR, '.flight-info.is-v2').get_attribute('aria-label')
                match = re.search(r'來回價格：NT\$[\d,]+', price_aria)
                if match:
                    price_text = match.group().replace('來回價格：', '')
                    price = parse_price_text(price_text)
                else:
                    price = None

                print(f"📋 出發：{depart_time}，抵達：{arrive_time}，票價：{price}")

                if depart_time == TARGET_DEPART and arrive_time == TARGET_ARRIVE:
                    print("✅ 找到符合時間的航班")
                    found = True
                    if price is not None and price <= PRICE_THRESHOLD:
                        print("💰 價格也符合條件，將發送通知")
                        msg = f'🚨 發現低價票！\n出發：{depart_time} OSL\n抵達：{arrive_time} TPE\n票價：{price} 元\n👉 {TRIP_URL}'
                        send_line_notification(msg)
                    else:
                        print(f"⚠️ 價格太高：{price} > {PRICE_THRESHOLD}，不發送通知")
                    break

            except Exception as e:
                print("⚠️ 某筆航班解析失敗：", e)
                print(card.get_attribute("outerHTML"))

        if not found:
            print("❗ 沒有找到符合條件的航班")

    except Exception as e:
        print("🚫 整體錯誤：", e)
        with open("page_debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        driver.save_screenshot("screenshot.png")

    finally:
        driver.quit()
        print("🧹 WebDriver 已關閉")

if __name__ == "__main__":
    check_price()
