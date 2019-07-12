# -*- coding: utf-8 -*-
import json
import re
import requests
import urllib.request
import urllib.parse

from bs4 import BeautifulSoup
from flask import Flask, request
from slack import WebClient
from slack.web.classes import extract_json
from slack.web.classes.blocks import *
from slack.web.classes.elements import *
from slack.web.classes.interactions import MessageInteractiveEvent
from slackeventsapi import SlackEventAdapter
from threading import Thread

SLACK_TOKEN = 'xoxb-678355204179-689797941829-Vs1A9Q4yZnD58umyEKA5KRF8'
SLACK_SIGNING_SECRET = '220c1d6ac84e8279a5f24523dc1ba808'
app = Flask(__name__)
# /listening 으로 슬랙 이벤트를 받습니다.
slack_events_adaptor = SlackEventAdapter(SLACK_SIGNING_SECRET, "/listening", app)
slack_web_client = WebClient(token=SLACK_TOKEN)

details = []

# 크롤링 함수 구현하기
def crawling_page(tap_url):
    url = "https://stdpc.pping.kr/stdpclist?cate_id="+tap_url+"&fitem=11"
    source_code = urllib.request.urlopen(url).read()
    soup = BeautifulSoup(source_code, "html.parser")

    # 페이지에서 각 매물의 정보를 추출합니다.
    crawling_details = []
    crawling_price = []
    crawling_links = []
    # link 크롤링
    for link_tag in soup.find_all('li', class_='pdItem'):
        crawling_links.append(link_tag.find('a').get('href'))

    # 가격 크롤링
    for price_tag in soup.find_all('span', class_='price'):
        strong_tag_list = price_tag.find('strong')
        crawling_price.append(strong_tag_list.get_text())

    #img src 클로링
    crawling_imgs = []
    for img_tag in soup.find_all('span', class_='pimg'):
        crawling_imgs.append(img_tag.find("img").get('src'))

    # 스펙 크롤링 , 취합
    div_tags = soup.find_all('div',class_='psec_detail')
    for i in range(0,len(div_tags)):
        li_tag_list = div_tags[i].find_all('li')
        crawling_details.append({
            "CPU": li_tag_list[0].get_text(),
            "MAIN": li_tag_list[1].get_text(),
            "MEM": li_tag_list[2].get_text(),
            "GPU": li_tag_list[3].get_text(),
            "SSD": li_tag_list[4].get_text(),
            "POW": li_tag_list[5].get_text(),
            "PRICE" : crawling_price[i],
            "LINK" : crawling_links[i],
            "IMG" : crawling_imgs[i]
        })
    global details
    details= crawling_details


def make_sale_message_blocks(cindex):
    # 탭 부분
    head_section = ActionsBlock(
        elements=[
            ButtonElement(
                text="가정/사무",
                style="danger",
                action_id="tap_office",value = '11'
            ),
            ButtonElement(
                text="게임", style="danger",
                action_id="tap_gaming", value = '22'
            ),
            ButtonElement(
                text="테마",
                style="danger",
                action_id="tap_theme", value = '33'
            ),
        ]
    )
    # 컴퓨터 이미지
    image_section = ImageBlock(
        image_url=details[cindex]['IMG'],
        alt_text="이미지를 불러오지 못했습니다."
    )
    # 스펙 및 상세 사양
    main_section = SectionBlock(
        text="```" +
             "---------------" + '\n' +
             "[PRICE]  : " + details[cindex]['PRICE'] + '\n' +
             "---------------" + '\n' +
             "[C P U]  : " + details[cindex]['CPU'] + '\n' +
             "[MAIN ]  : " + details[cindex]['MAIN'] + '\n' +
             "[M E M]  : " + details[cindex]['MEM'] + '\n' +
             "[G P U]  : " + details[cindex]['GPU'] + '\n' +
             "[S S D]  : " + details[cindex]['SSD'] + '\n' +
             "[POWER]  : " + details[cindex]['POW'] + "```"
    )
    # 제품 링크
    link_section = SectionBlock(
        text = "```" +"<"+details[cindex]["LINK"] + "|바로가기 >"+"```"
    )
    # 목록 버튼
    button_actions = ActionsBlock(
        elements=[
            ButtonElement(
                text="이전",
                action_id="price_down", value=str(cindex)
            ),
            ButtonElement(
                text="다음",
                action_id="price_up", value=str(cindex)
            ),
        ]
    )
    blocks = [head_section, image_section, main_section,link_section ,button_actions]
    return blocks


# 챗봇이 멘션을 받았을 경우
@slack_events_adaptor.on("app_mention")
def app_mentioned(event_data):
    channel = event_data["event"]["channel"]
    text = event_data["event"]["text"]
    mentioned_url = '2010100000'
    crawling_page(mentioned_url)
    massage_block = make_sale_message_blocks(0)


    slack_web_client.chat_postMessage(
        channel=channel,
        blocks=extract_json(massage_block)
    )


def click_Threding(click_event):
    what_event = click_event.action_id
    event_list = what_event.split('_')

    if event_list[0] == 'price':

        click_value = int(click_event.value)
        if event_list[1] == 'up':

            click_value += 0 if click_value >= 5 else 1
        else:
            click_value -= 0 if click_value <=0  else 1

        message_blocks = make_sale_message_blocks(click_value)

    elif event_list[0] == 'tap':
        if event_list[1] == 'office':
            crawling_url  = '2010100000'
        elif event_list[1] == 'gaming':
            crawling_url = '2010300000'
        else:
            crawling_url = '2010500000'

        crawling_page(crawling_url)
        message_blocks = make_sale_message_blocks(0)

    # 메시지를 채널에 올립니다
    slack_web_client.chat_postMessage(
        channel=click_event.channel.id,
        blocks=extract_json(message_blocks)
    )


@app.route("/click", methods=["GET", "POST"])
def on_button_click():
    # 버튼 클릭은 SlackEventsApi에서 처리해주지 않으므로 직접 처리합니다
    payload = request.values["payload"]
    click_event = MessageInteractiveEvent(json.loads(payload))
    Thread(target=click_Threding, args=(click_event,)).start()

    # Slack에게 클릭 이벤트를 확인했다고 알려줍니다
    return "OK", 200


# / 로 접속하면 서버가 준비되었다고 알려줍니다.
@app.route("/", methods=["GET"])
def index():
    return "<h1>Server is ready.</h1>"

if __name__ == '__main__':
    app.run('127.0.0.1', port=8080)