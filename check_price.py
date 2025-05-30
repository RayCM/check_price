import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient
from linebot.v3.messaging.models import TextMessage, PushMessageRequest

# LINE 設定（從 GitHub Secrets 注入）
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
GROUP_ID = os.getenv("LINE_GROUP_ID")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
line_bot_api = MessagingApi(ApiClient(configuration))

# 查詢條件
TARGET_DEPART = '13:45'
TARGET_ARRIVE = '13:05'
PRICE_THRESHOLD = 50000

TRIP_URL = 'https://tw.trip.com/flights/ShowFareNext?lowpricesource=searchform&triptype=RT&class=Y&quantity=1&childqty=0&babyqty=0&jumptype=GoToNextJournay&dcity=tpe&acity=osl&aairport=osl&ddate=2025-09-27&dcityName=Taipei&acityName=Oslo&rdate=2025-10-11&currentseqno=2&criteriaToken=SGP_SGP-ALI_PIDReduce-fa581fb9-52dc-44f2-904a-c3713fc77085%5EList-e5e15878-8953-448b-b2c8-bafad1db43d2&shoppingid=SGP_SGP-ALI_PIDReduce-484e8781-9a5f-4912-8e4b-47cb424d78a9%5EList-20f7b900-7413-4173-87de-383261b6c2c6&groupKey=SGP_SGP-ALI_PIDReduce-484e8781-9a5f-4912-8e4b-47cb424d78a9%5EList-20f7b900-7413-4173-87de-383261b6c2c6&locale=zh-TW&curr=TWD'

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

def check_price():
    print("🔍 開始查詢 Trip.com...")

    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(TRIP_URL)
        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.result-item'))
        )

        cards = driver.find_elements(By.CSS_SELECTOR, '.result-item')
        print(f"✈️ 找到 {len(cards)} 筆航班")

        for card in cards:
            try:
                depart_testid = card.find_element(By.CSS_SELECTOR, '.is-departure_2a2b .time_cbcc').get_attribute('data-testid')
                depart_time = extract_time_from_testid(depart_testid)

                arrive_testid = card.find_element(By.CSS_SELECTOR, '.is-arrival_f407 .time_cbcc').get_attribute('data-testid')
                arrive_time = extract_time_from_testid(arrive_testid)

                price_el = card.find_element(By.CSS_SELECTOR, '.select-area-price [data-price]')
                price = int(price_el.get_attribute('data-price'))

                print(f"📋 出發：{depart_time}，抵達：{arrive_time}，票價：{price}")

                if depart_time == TARGET_DEPART and arrive_time == TARGET_ARRIVE and price <= PRICE_THRESHOLD:
                    message = (
                        f'🚨 發現低價票！\n'
                        f'去程：{depart_time} OSL\n'
                        f'回程：{arrive_time} TPE\n'
                        f'票價：{price} 元\n👉 {TRIP_URL}'
                    )
                    send_line_notification(message)
                    break
            except Exception as e:
                print("⚠️ 解析某航班失敗", e)

    except
