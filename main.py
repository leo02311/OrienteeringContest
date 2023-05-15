import re
import datetime
import os
import math
os.environ["FLASK_ENV"] = "development"
from flask import Flask, request, abort ,jsonify ,render_template, make_response, session

from firebase_admin import credentials, firestore, initialize_app

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    FollowEvent, MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
)

import configparser 

app = Flask(__name__,template_folder='templates')

#import firebase
cred = credentials.Certificate('key.json')
default_app = initialize_app(cred)
db = firestore.client()
todo_ref = db.collection(u'lineId')

#add linebot channel
config = configparser.ConfigParser()
config.read('config.ini')
line_bot_api = LineBotApi(config.get('line-bot', 'channel_access_token')) #已存於config.ini
handler = WebhookHandler(config.get('line-bot', 'channel_secret'))

#get Student Number
def getSN(id):
  collection_ref = todo_ref.document(id)
  doc = collection_ref.get({u'studentNumber'})
  if doc.exists:
    return doc.to_dict().get(u'studentNumber')
  else:
    return None

#get point
def getData(id):
  collection_ref = todo_ref.document(id)
  doc = collection_ref.get({u'point'})
  if doc.exists:
    return doc.to_dict().get(u'point')
  else:
    return None

#get time
def getTime(id):
    collection_ref = todo_ref.document(id)
    doc = collection_ref.get({u'time'})
    if doc.exists:
        return doc.to_dict().get(u'time')
    else:
        return None


@app.route('/')
def index():
    #load user data
    if 'userId' in request.cookies:
        id = request.cookies.get('userId')
        if getData(str(id)) is not None:
            return render_template('index.html', data=getData(str(id)), sc=getSN(str(id)))
    return render_template('index.html')

@app.route('/get', methods=['POST','GET'])
def get():
    if request.method == "POST":
        response = request.get_json()
        resp = make_response('idRecord')
        resp.set_cookie('userId', ''+response['id'],expires = datetime.datetime.utcnow() + datetime.timedelta(days=30))
        return resp
    return render_template('index.html')

@app.route('/send', methods=['POST','GET'])
def send():#send the output to user
    if request.method == "POST":
        response = request.get_json()
        id = request.cookies.get('userId')
        if (id != None):
            if getTime(str(id)) is not None:
                r = getTime(str(id))
                data = {
                    u'studentNumber': response['studentNumber'],
                    u'point': response['point'],
                    u'time': response['record'] + r,
                }
                target = todo_ref.document('' + id)
                target.set(data, merge=True)
                s = 0
                values = getTime(str(id))
                txt = ['{:.2f}'.format(x) for x in getTime(str(id))]
                for x in range(0, len(values)):
                    s += values[x]
                line_bot_api.multicast([id],TextSendMessage(text='時間紀錄:\n' + '秒,\n'.join(txt) + '秒\n時間統計:' + str(math.ceil(s)) + '秒'))
                return response
            sn = {
                response[u'studentNumber']: id,
            }
            todo_ref.document(u'studentNumber').set(sn, merge = True)
            data = {
                u'studentNumber': response['studentNumber'],
                u'point': response['point'],
                u'time': response['record'],
            }
            target = todo_ref.document(''+id)
            target.set(data, merge=True)
            s=0
            values = getTime(str(id))
            txt = ['{:.2f}'.format(x) for x in getTime(str(id))]
            for x in range(0, len(values)):
                s += values[x]
            line_bot_api.multicast([id], TextSendMessage(text='時間紀錄:\n'+ '秒,\n'.join(txt) +'秒\n時間統計:'+str(math.ceil(s))+'秒'))
        return response
    return render_template('index.html')


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

@handler.add(FollowEvent)
def handle_follow(event):
    if event.type == "follow":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="查看規則或有問題請按右上選單\n開始競賽請按左上選單\n左下選單有問題時請查看\n右下選單為safari開啟定位教學")
        )

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    if event.source.user_id =='#': #填入line在verify時回傳的user_id
        return 'OK'

    elif event.source.user_id =='#':
        if event.message.text[0:8] == '!create ':
            st = event.message.text[8:18]
            id = event.message.text[18:]
            sn = {
                st: id,
            }
            todo_ref.document(u'studentNumber').set(sn, merge=True)
            data = {
                u'studentNumber': st,
                u'point': [0],
                u'time': [0],
            }
            target = todo_ref.document('' + id)
            target.set(data, merge=True)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="新增資料" + id + ":" + st)
            )

        if event.message.text[0:5] == '!add ':
            txt = event.message.text[5:]
            if getData(str(txt)) is not None:
                r = getData(str(txt))
                if len(r)<=15:
                    r.append(len(r))
                    target = todo_ref.document('' + str(txt))
                    target.update({u'point': r})
                text = ['{:d}'.format(x) for x in getData(str(txt))]
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="目前資料為["+','.join(text)+"]")
                )
            else:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="沒有資料可以增加")
                )

    else:
        if event.message.text == '鼠倫一個':
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="安安")
            )

        if event.message.text == '鼠鼠給我時間':
            if getData(event.source.user_id) is not None:
                if getTime(event.source.user_id) is not None:
                    values = getTime(str(event.source.user_id))
                    txt = ['{:.2f}'.format(x) for x in getTime(str(event.source.user_id))]
                    s = 0
                    for x in range(0, len(values)):
                        s += values[x]
                    if len(getData(event.source.user_id)) == 16:
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(text='除了時間你還想要什麼\n鼠鼠的命嗎?\n但是鼠鼠已經死了\n呵\n狀態:已完成\n時間紀錄(僅供參考):\n' + '秒,\n '.join(txt) + '秒\n時間統計:' + str(math.ceil(s)) + '秒'))
                    else:
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(text='還差一點點呢\n完成之後想要鼠鼠的獎勵嗎?\n狀態:未完成\n時間紀錄(僅供參考):\n' + '秒,\n '.join(txt) + '秒\n時間統計:' + str(math.ceil(s)) + '秒'))
                else:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text='鼠倫不會說話\n沒有時間紀錄的事鼠鼠不會說出去的'))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text='鼠倫不會說話\n沒有到點紀錄的事鼠鼠不會說出去的'))

        if event.message.text == '!report':
                a = '#'
                b = '#'
                txt = str([event.source.user_id]).strip("[']")
                line_bot_api.push_message(a, TextSendMessage(text=txt))
                line_bot_api.push_message(b, TextSendMessage(text=txt))
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="這是給鼠鼠的嗎?(已收到回報)")
                )

        if event.message.text == '!定位教學':
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text="safari定位教學\n1.前往「設定」>「隱私權」>「定位服務」\n2.確定「定位服務」已開啟\n3.向下捲動以尋找 safari\n4.點一下safari選擇「下次詢問」再回到line開啟\n5.進入定向頁面會詢問是否開啟定位再選擇開啟(如有問題再與相關人員聯絡)\n6.之後再依相同步驟可將定位選項關閉")
            )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(threaded=True,host='0.0.0.0',  port=port )


