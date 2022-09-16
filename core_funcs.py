import re
import configparser

from utils import get_data, construct_message, extract_data_from_message, send, send_message
from db_utils import is_valid_request, save_to_database, request_limit_reached, db_lookup, db_bulk_lookup, fetch_product, remove_association_entry, reassign_product


CFG = configparser.ConfigParser()
CFG.read('config.ini')
MAX_REQUESTS = CFG['settings']['max_requests']


async def scrape_handler(asin, user_info):
    raw_data = await get_data(asin=asin)

    if raw_data['title'] is None or raw_data['price'] is None:
        return f"Unexpected error occured, couldn't retrieve product information. Please try again.\n\n"

    processed_data = await save_to_database(raw_data, user_info)
    return construct_message(processed_data)

async def pre_scrape_checker(asin, user_info):
    if await is_valid_request(user_info.username, asin):
        product = await fetch_product(asin)
        
        if product:
            await save_to_database(product, user_info, obj=True)
            return construct_message(product)
        
        return await scrape_handler(asin, user_info)

    return f"You already have this product (Asin: {asin}) registered.\n\n"

async def argumnent_validator(arg, user_info):
    if re.search(r"^((https://www.amazon.com)|(http://www.amazon.com)|(https://amazon.com)|(http://amazon.com)|(www.amazon.com)|(amazon.com)).*/dp/[A-Z0-9]{10}[/?].*$", arg):
        if await request_limit_reached(user_info.username):
            return f"Sorry, maximum tracking request limit({MAX_REQUESTS}) reached.\n\n"

        asin = re.findall(r'/dp/([A-Z0-9]{10})[/?]', arg)[0]
        return await pre_scrape_checker(asin, user_info)    
    
    if re.search(r'^[A-Z0-9]{10}$', arg):
        if await request_limit_reached(user_info.username):
            return f"Sorry, maximum tracking request limit({MAX_REQUESTS}) reached.\n\n"

        asin = arg
        return await pre_scrape_checker(asin, user_info)

    return "Invalid product URL (or) Asin. Please try again with valid parameters."

async def register(chat_id, user_info, args):
    for arg in args:
        msg = await argumnent_validator(arg, user_info)
        await send(chat_id, msg)

async def single_update(chat_id, username, asin):
    product = await db_lookup(username, asin)

    if not product:
        return "Can't get update since this product is no longer in your tracking list."
    
    await send_message(chat_id, product)
    return None

async def bulk_update(chat_id):
    products = await db_bulk_lookup(chat_id)
    
    if not products:
        return "You don't have any product registered for tracking."

    for product in products:
        await send_message(chat_id, product)

    return None

async def process_update(this_bot, chat_id, username, msg=None):
    if msg:
        if msg.from_user == this_bot and msg.text.startswith(('Update Alert!', 'Title: ', 'Last checked: ', 'Tracking Restarted!')):
            data = extract_data_from_message(msg.text)
            return await single_update(chat_id, username, data['asin'])

        return "Invalid update request..."
    
    return f"Please reply to any of the product related messages from the bot of the product you want to get update of."

async def stop_updates(this_bot, username, msg):
    if msg and msg.from_user == this_bot and msg.text.startswith(('Update Alert!', 'Title: ', 'Last checked: ', 'Tracking Restarted!')):
        data = extract_data_from_message(msg.text)
        try:
            await remove_association_entry(username, asin=data['asin'])

            return f"Product ({ data['url'] }) has been removed from your tracking list. To start recieiving updates again, reply with /restart"
        except Exception as e:
            print(e)
            return "An unexpected error occured, please try again."

    return "Please reply to any of the product related messages from the bot of the product you don't want to recieve updates of anymore."

async def stop_all_updates(username):
    try:
        await remove_association_entry(username)

        return f"Tracking stopped. You won't receive any more updates."
    except Exception as e:
        print(e)
        return f"An unexpected error occured, please try again."

async def restart_updates(this_bot, chat_id, username, msg):
    if msg and msg.from_user == this_bot and msg.text.startswith(('Update Alert!', 'Title: ', 'Last checked: ', 'Tracking Restarted!', 'Product (')):
        stop_msg = False
        if msg.text.startswith('Product ('):
            stop_msg = True
        data = extract_data_from_message(msg.text, stop_msg=stop_msg)

        try:
            product = await reassign_product(username, asin=data['asin'])
            if product:
                await send_message(chat_id, product, restart_updates=True)
                return None

            return "You already have this product registered."
        except Exception as e:
            print(e)
            return "An unexpected error occured, please try again."
 
    return "Please reply to any of the product related messages from the bot of the previously updating stopped product you want to start recieving updates of again."
