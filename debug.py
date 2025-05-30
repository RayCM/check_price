from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 用你自己的值替換這兩個變數
CHANNEL_ACCESS_TOKEN = 'Xq4TaM34We9aq9pW3t4FXIGyC5go1BNESYVroQr5oOcrY6hzew7YpDovviDkMbp8jQoexoJhXQhsuhhyEFHrhg6PoEPEQpwYNn5djtwvd91Qq+NaZtoJFTAl6/wLFuJPEZMHe1gZn/udOXCkIgauXQdB04t89/1O/w1cDnyilFU='
CHANNEL_SECRET = '0fe449bdf30538fdeae6e1f8232e66ee'

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    reply = '✅ 已收到你的訊息！\n'

    # 檢查來源
    if event.source.user_id:
        reply += f"👤 你的 User ID 是：{event.source.user_id}"
        print(">>> User ID:", event.source.user_id)

    if event.source.group_id:
        reply += f"\n👥 群組 ID 是：{event.source.group_id}"
        print(">>> Group ID:", event.source.group_id)

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

if __name__ == "__main__":
    app.run()
