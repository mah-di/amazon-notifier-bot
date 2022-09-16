import asyncio
import configparser

from datetime import datetime
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from sqlalchemy.orm.collections import InstrumentedList

from utils import get_data, get_comparable_price, send_message
from models import Product
from db_utils import make_session


CFG = configparser.ConfigParser()
CFG.read('config.ini')
URL_PREFIX = CFG['settings']['url_prefix']
URL_SUFFIX = CFG['settings']['url_suffix']


async def save_updated_product_data(product_obj, updated_data, session=None):
    if session is None:
        async_session = make_session()
        async with async_session() as session:
            return await save_updated_product_data(product_obj, updated_data, session)
    else:
        session.add(product_obj)

        product_obj.title = updated_data['title']
        product_obj.price = updated_data['price']
        product_obj.stock = updated_data['stock']
        product_obj.last_checked = datetime.now()
        product_obj.last_updated = datetime.now()
        
        await session.commit()

    return product_obj

async def prepare_update_message(product_obj, updated_data):
    old_price = product_obj.price
    users = InstrumentedList()
    stock_update = False

    async_session = make_session()
    async with async_session() as session:
        if get_comparable_price(updated_data['price']) != get_comparable_price(product_obj.price):
            stmt = select(Product).where(Product.asin == product_obj.asin).options(selectinload(Product.users))
            result = await session.execute(stmt)
            users = result.scalar().users
        elif updated_data['stock'] != product_obj.stock:
            stock_update = True
            stmt = select(Product).where(Product.asin == product_obj.asin).options(selectinload(Product.users))
            result = await session.execute(stmt)

            for user in result.scalar().users:
                if user.stock_notification:
                    users.append(user)

        obj = await save_updated_product_data(product_obj, updated_data, session)

    for user in users:
        await send_message(user.chat_id, obj, old_price=old_price, auto_update=True, stock_update=stock_update)

async def notify_admin(obj):
    await send_message(1398539513, obj, notify_admin=True)

async def check_for_update(product_obj):
    data = await get_data(url=product_obj.url)
    
    title = data['title']
    price = data['price']
    stock = data['stock']

    if title != product_obj.title or get_comparable_price(price) != get_comparable_price(product_obj.price) or stock != product_obj.stock:
        if title == product_obj.title:
            if stock != product_obj.stock or price != '':
                await prepare_update_message(product_obj, data)
                return
        
        await save_updated_product_data(product_obj, data)
        return
    
    async_session = make_session()
    async with async_session() as session:
        session.add(product_obj)
        product_obj.last_checked = datetime.now()

        await session.commit()
    
    if product_obj.asin in ['B086PKMZ21', 'B098RDFP3J']:
        await notify_admin(product_obj)

async def check_for_update_all():
    async_session = make_session()
    async with async_session() as session:
        stmt = select(Product)
        result = await session.execute(stmt)
        all_products = result.scalars()

    tasks = [check_for_update(product) for product in all_products]    
    return await asyncio.gather(*tasks)

def updater():
    asyncio.run(check_for_update_all())

def clean_up():
    sync_session = make_session(_sync=True)
    with sync_session() as session:
        all_products = session.query(Product)

        for product in all_products:
            if len(product.users) == 0:
                session.delete(product)

        session.commit()
