import time
import schedule
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from linebot.v3.messaging import MessagingApi
from linebot.v3.messaging.models import TextMessage

# ====== LINE Bot 設定 ======
CHANNEL_ACCESS_TOKEN = 'Xq4TaM34We9aq9pW3t4FXIGyC5go1BNESYVroQr5oOcrY6hzew7YpDovviDkMbp8jQoexoJhXQhsuhhyEFHrhg6PoEPEQpwYNn5djtwvd91Qq+NaZtoJFTAl6/wLFuJPEZMHe1gZn/udOXCkIgauXQdB04t89/1O/w1cDnyilFU='
GROUP_ID = 'C720692394736422eb5ed85bd1ff65f1a'
line_bot_api = MessagingApi(CHANNEL_ACCESS_TOKEN)

# ====== 航班條件 ======
TARGET_DEPART = '13:45'
TARGET_ARRIVE = '13:05'
PRICE_THRESHOLD = 45000

# ====== 查詢網址 ======
TRIP_URL = 'https://tw.trip.com/flights/ShowFareNext?lowpricesource=searchform&triptype=RT&class=Y&quantity=1&childqty=0&babyqty=0&jumptype=GoToNextJournay&dcity=tpe&acity=osl&aairport=osl&ddate=2025-09-27&dcityName=Taipei&acityName=Oslo&rdate=2025-10-11&currentseqno=2&criteriaToken=SGP_SGP-ALI_PIDReduce-fa581fb9-52dc-44f2-904a-c3713fc77085%5EList-e5e15878-8953-448b-b2c8-bafad1db43d2&shoppingid=SGP_SGP-ALI_PIDReduce-484e8781-9a5f-4912-8e4b-47cb424d78a9%5EList-20f7b900-7413-4173-87de-383261b6c2c6&groupKey=SGP_SGP-ALI_PIDReduce-484e8781-9a5f-4912-8e4b-47cb424d78a9%5EList-20f7b900-7413-4173-87de-383261b6c2c6&locale=zh-TW&curr=TWD'

# ====== LINE 通知函式 ======
def send_line_notification(message):
    try:
        line_bot_api.push_message(GROUP_ID, TextMessage(text=message))
        print("✅ 成功發送 LINE 通知")
    except Exception as e:
        print("❌ 發送通知失敗：", e)

# ====== 主查詢邏輯 ======
def check_price():
    print("🔍 正在檢查票價...")

    # Debug: log 檔路徑
    print("📁 log.txt 路徑：", os.path.abspath("log.txt"))

    # 寫入 log
    with open("log.txt", "a", encoding="utf-8") as log_file:
        log_file.write("🔍 開始檢查票價\n")

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get(TRIP_URL)
        WebDriverWait(driver, 120).until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[data-price]')))

        flights = driver.find_elements(By.CSS_SELECTOR, '[data-price]')
        with open("log.txt", "a", encoding="utf-8") as log_file:
            for flight in flights:
                log_file.write("航班資訊：\n")
                log_file.write(flight.text + "\n\n")

                if TARGET_DEPART in flight.text and TARGET_ARRIVE in flight.text:
                    price = int(flight.get_attribute('data-price'))
                    print(f"✈️ 找到航班：{TARGET_DEPART} → {TARGET_ARRIVE}，票價：{price}")
                    if price <= PRICE_THRESHOLD:
                        message = f'🚨 發現低價票！\n航班：{TARGET_DEPART} OSL → {TARGET_ARRIVE} TPE\n票價：{price} 元'
                        send_line_notification(message)
                    return
        print("❗ 未找到符合條件的航班")

    except Exception as e:
        err_msg = str(e) if str(e) else "（錯誤內容為空）"
        print("🚫 發生錯誤：", err_msg)

        # 寫入 log
        with open("log.txt", "a", encoding="utf-8") as log_file:
            log_file.write(f"[錯誤] {err_msg}\n")

        # 寫入 HTML 原始碼供除錯
        with open("page_debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

    finally:
        driver.quit()

# ====== 啟動排程 ======
schedule.every(3).minutes.do(check_price)
print("✈️ 開始監控票價中...")

while True:
    schedule.run_pending()
    time.sleep(1)
