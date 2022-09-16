import re
import aiohttp
import configparser

from bs4 import BeautifulSoup
from time import sleep
from datetime import datetime
from telegram._bot import Bot


CFG = configparser.ConfigParser()
CFG.read('config.ini')
URL_PREFIX = CFG['settings']['url_prefix']
URL_SUFFIX = CFG['settings']['url_suffix']
PRODUCT_TITLE = CFG['selectors']['product_title']
PRODUCT_PRICE = CFG['selectors']['product_price']
PRODUCT_STOCK = CFG['selectors']['product_stock']
TOKEN = CFG['credentials']['token']
RETRY_MESSAGING_INTERVAL = int(CFG['settings']['retry_messaging_interval'])
RETRY_SCRAPING_INTERVAL = int(CFG['settings']['retry_scraping_interval'])
MAX_MESSAGING_RETRY = int(CFG['settings']['max_messaging_retry'])
MAX_SCRAPING_RETRY = int(CFG['settings']['max_scraping_retry'])


def construct_url(asin):
    return URL_PREFIX + str(asin) + URL_SUFFIX

def elapsed_time(start_time):
    to_str = ''
    interval = (datetime.now() - start_time).seconds

    if interval // (60*60*24*365) > 0:
        to_str += f"{ interval // (60*60*24*365) }yr "

    if interval // (60*60*24) > 0:
        to_str += f"{ (interval // (60*60*24))%365 }day "

    if interval // (60*60) > 0:
        to_str += f"{ (interval // (60*60))%(24) }hr "

    if interval // (60) > 0:
        to_str += f"{ (interval // (60))%(60) }min(s) ago"

    if interval // 60 == 0:
        to_str += f"just now"

    return to_str

def construct_message(obj, old_price=None, auto_update=False, restart_updates=False, notify_admin=False, stock_update=False):
    title = obj.title if obj.title != '' else 'No information...'
    price = obj.price if obj.price != '' else 'No information...'
    stock = obj.stock if obj.stock != '' else 'No information...'
    url = obj.url

    time_since = elapsed_time(obj.last_checked)

    if auto_update:
        if old_price not in [None, '']:
            return f'Update Alert! Price updated.\nLast checked: { time_since }\n\nTitle: { title }\n\nStock Status: { stock }\nPrevious Price: { old_price }\nUpdated Price: { price }\n\nBuy Now: { url }\n\n'
        elif stock_update:
            return f'Update Alert! Stock updated.\nLast checked: { time_since }\n\nTitle: { title }\n\nStock Status: { stock }\nPrevious Price: { old_price }\nUpdated Price: { price }\n\nBuy Now: { url }\n\n'
        else:
            return f'Update Alert! Price updated.\nLast checked: { time_since }\n\nTitle: { title }\n\nStock Status: { stock }\nPrice: { price }\n\nBuy Now: { url }\n\n'

    if restart_updates:
        return f"Tracking Restarted!\nLast checked: { time_since }\n\nTitle: { title }\n\nStock Status: { stock }\nPrice: { price }\n\nBuy Now: { url }\n\n"

    if notify_admin:
        return f"Admin Notification!\nLast checked: { time_since }\n\nTitle: { title }\n\nStock Status: { stock }\nPrice: { price }\n\nBuy Now: { url }\n\n"

    return f"Last checked: { time_since }\n\nTitle: { title }\n\nStock Status: { stock }\nPrice: { price }\n\nBuy Now: { url }\n\n"

async def send(chat_id, msg):
    retries = 0
    while retries <= MAX_MESSAGING_RETRY:
        try:
            async with Bot(token=TOKEN) as bot:
                await bot.send_message(chat_id=chat_id, text=msg)
                return
        except Exception as e:
            retries += 1
            print(f"Failed to send message: {e}\nRetrying in {RETRY_MESSAGING_INTERVAL} seconds ({retries}/{MAX_MESSAGING_RETRY})")
            sleep(RETRY_MESSAGING_INTERVAL)

async def send_message(chat_id, obj, old_price=None, auto_update=False, restart_updates=False, notify_admin=False, stock_update=False):
    msg = construct_message(obj, old_price=old_price, auto_update=auto_update, restart_updates=restart_updates, notify_admin=notify_admin, stock_update=stock_update)
    await send(chat_id, msg)

async def get_data(asin=None, url=None):
    if url is None:
        url = construct_url(asin)

    retries = 0
    while retries <= MAX_SCRAPING_RETRY:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    data = {
                        'title': None,
                        'asin': asin,
                        'price': None,
                        'stock': None,
                        'url': url
                    }

                    try:
                        data['title'] = soup.select_one(PRODUCT_TITLE).text.strip()
                        data['price'] = soup.select_one(PRODUCT_PRICE).text.strip()
                        data['stock'] = soup.select_one(PRODUCT_STOCK).text.strip()
                    except Exception as e:
                        print(e)

            return data

        except Exception as e:
            retries += 1
            print(f"Failed to send message: {e}\nRetrying in {RETRY_SCRAPING_INTERVAL} seconds ({retries}/{MAX_SCRAPING_RETRY})")
            sleep(RETRY_SCRAPING_INTERVAL)

def get_comparable_price(raw_price):
    try:
        return float(raw_price.strip('$').strip())
    except:
        return -1

def extract_url_from_message(msg, stop_msg=False):
    if stop_msg:
        return msg.split('(')[1].split(')')[0]

    return msg.split('Buy Now: ')[1]

def extract_data_from_message(msg, stop_msg=False):
    url = extract_url_from_message(msg, stop_msg)
    asin = re.findall(r'/dp/([A-Z0-9]{10})/', url)[0]

    return {'asin': asin, 'url': url}

def start_response():
    with open('command_response_start.txt', 'r') as f:
        response = f.read()

    return response

def about_response():
    with open('command_response_about.txt', 'r') as f:
        response = f.read()

    return response

def help_response():
    with open('command_response_help.txt', 'r') as f:
        response = f.read()

    return response
