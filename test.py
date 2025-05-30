from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage

app = Flask(__name__)

# 替換成你自己的 token 與 secret
CHANNEL_SECRET = '0fe449bdf30538fdeae6e1f8232e66ee'
CHANNEL_ACCESS_TOKEN = 'Xq4TaM34We9aq9pW3t4FXIGyC5go1BNESYVroQr5oOcrY6hzew7YpDovviDkMbp8jQoexoJhXQhsuhhyEFHrhg6PoEPEQpwYNn5djtwvd91Qq+NaZtoJFTAl6/wLFuJPEZMHe1gZn/udOXCkIgauXQdB04t89/1O/w1cDnyilFU='

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    source = event.source
    print(f"來源類型: {source.type}")
    if source.type == 'group':
        print(f"群組 ID：{source.group_id}")
    elif source.type == 'user':
        print(f"使用者 ID：{source.user_id}")

if __name__ == "__main__":
    app.run(port=5000)
