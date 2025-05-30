import os
import requests
from bs4 import BeautifulSoup
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient
from linebot.v3.messaging.models import TextMessage, PushMessageRequest

# ===== LINE Bot =====
LINE_ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
LINE_GROUP_ID = os.getenv("LINE_GROUP_ID")

configuration = Configuration(access_token=LINE_ACCESS_TOKEN)
line_bot_api = MessagingApi(ApiClient(configuration))

# ===== 查詢條件 =====
TARGET_DEPART = '13:45'
TARGET_ARRIVE = '13:05'
PRICE_THRESHOLD = 42000

TRIP_URL = 'https://tw.trip.com/flights/ShowFareNext?lowpricesource=searchform&triptype=RT&class=Y&quantity=1&childqty=0&babyqty=0&jumptype=GoToNextJournay&dcity=tpe&acity=osl&aairport=osl&ddate=2025-09-27&dcityName=Taipei&acityName=Oslo&rdate=2025-10-11&currentseqno=2&criteriaToken=SGP_SGP-ALI_PIDReduce-fa581fb9-52dc-44f2-904a-c3713fc77085%5EList-e5e15878-8953-448b-b2c8-bafad1db43d2&shoppingid=SGP_SGP-ALI_PIDReduce-484e8781-9a5f-4912-8e4b-47cb424d78a9%5EList-20f7b900-7413-4173-87de-383261b6c2c6&groupKey=SGP_SGP-ALI_PIDReduce-484e8781-9a5f-4912-8e4b-47cb424d78a9%5EList-20f7b900-7413-4173-87de-383261b6c2c6&locale=zh-TW&curr=TWD'

def send_line_notification(message):
    try:
        req = PushMessageRequest(
            to=LINE_GROUP_ID,
            messages=[TextMessage(text=message)]
        )
        line_bot_api.push_message(req)
        print("✅ 成功發送 LINE 通知")
    except Exception as e:
        print("❌ 發送失敗：", e)

def check_price():
    print("🔍 正在查詢票價...")

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(TRIP_URL, headers=headers)
    if response.status_code != 200:
        print("⚠️ 無法取得網頁")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    cards = soup.select('.result-item')
    print(f"✈️ 找到 {len(cards)} 筆航班")

    for card in cards:
        try:
            depart_time = card.select_one('.is-departure_2a2b .time_cbcc').text.strip()
            arrive_time = card.select_one('.is-arrival_f407 .time_cbcc').text.strip()
            price_text = card.select_one('[data-price]')['data-price']
            price = int(price_text.replace(',', '').strip())

            print(f"出發：{depart_time}，抵達：{arrive_time}，票價：{price}")

            if depart_time == TARGET_DEPART and arrive_time == TARGET_ARRIVE and price <= PRICE_THRESHOLD:
                message = (
                    f'🚨 發現低價票！\n'
                    f'去程：{depart_time}（OSL）\n'
                    f'回程：{arrive_time}（TPE）\n'
                    f'票價：{price} 元\n👉 {TRIP_URL}'
                )
                send_line_notification(message)
                break
        except Exception as e:
            continue

if __name__ == "__main__":
    check_price()
