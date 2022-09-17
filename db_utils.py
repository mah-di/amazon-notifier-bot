import configparser

from sqlalchemy import insert, create_engine
from sqlalchemy.orm import sessionmaker, selectinload
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from models import User, Product, association_table
from utils import get_data


CFG = configparser.ConfigParser()
CFG.read('config.ini')
MAX_REQUESTS = int(CFG['settings']['max_requests'])


def construct_db_uri(_sync=False):
    if _sync:
        return f"{CFG['credentials']['db_sync_uri_prefix']}/{CFG['credentials']['db_file']}"

    return f"{CFG['credentials']['db_async_uri_prefix']}/{CFG['credentials']['db_file']}"

def make_session(_sync=False):
    if _sync:
        db_uri = construct_db_uri(_sync=True)
        Engine = create_engine(db_uri)
        return sessionmaker(bind=Engine, expire_on_commit=False)
    
    db_uri = construct_db_uri()
    Engine = create_async_engine(db_uri)
    return sessionmaker(Engine, class_=AsyncSession, expire_on_commit=False)

async def is_associated(username, asin):
    async_session = make_session()
    async with async_session() as session:
        stmt = select(association_table).where(association_table.c.username == username, association_table.c.product_asin == asin)
        result = await session.execute(stmt)
    
    return True if result.scalar() else False

async def is_valid_request(username, asin):
    async_session = make_session() 
    async with async_session() as session:
        stmt = select(association_table).where(association_table.c.username == username, association_table.c.product_asin == asin)
        result = await session.execute(stmt)
        
    return False if result.scalar() else True

async def request_limit_reached(username):
    async_session = make_session() 
    async with async_session() as session:
        stmt = select(User).where(User.username == username).options(selectinload(User.products))
        result = await session.execute(stmt)
        user = result.scalar()
    
    return True if len(user.products) == MAX_REQUESTS else False

async def create_user(user_info):
    first_name = user_info.first_name
    last_name = user_info.last_name
    username = user_info.username
    chat_id = user_info.id

    async_session = make_session()
    async with async_session() as session:
        user = User(chat_id=chat_id, first_name=first_name, last_name=last_name, username=username)
        session.add(user)

        await session.commit()

    return user

async def create_product(data):
    title = data['title']
    asin = data['asin']
    price = data['price']
    stock = data['stock']
    url = data['url']

    async_session = make_session()
    async with async_session() as session:
        product = Product(title=title, asin=asin, price=price, stock=stock, url=url)
        session.add(product)

        await session.commit()
        
    return product

async def create_association(username, asin):
    async_session = make_session()
    async with async_session() as session:
        stmt = insert(association_table).values(username=username, product_asin=asin)
        await session.execute(stmt)

        await session.commit()

async def fetch_user(username):
    async_session = make_session()
    async with async_session() as session:
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        user = result.scalar()

    return user

async def fetch_product(asin):
    async_session = make_session()
    async with async_session() as session:
        stmt = select(Product).where(Product.asin == asin)
        result = await session.execute(stmt)
        product = result.scalar()

    return product

async def fetch_association(username, asin):
    async_session = make_session()
    async with async_session() as session:
        stmt = select(association_table).where(association_table.c.username == username, association_table.c.product_asin == asin)
        result = await session.execute(stmt)

    return result.scalar()

async def fetch_or_create_user(user_info):
    user = await fetch_user(user_info.username)

    if not user:
        user = await create_user(user_info)

    return user

async def fetch_or_create_product(data):
    product = await fetch_product(data['asin'])

    if not product:
        product = await create_product(data)

    return product

async def save_to_database(data, user_info, obj=False):
    user = await fetch_or_create_user(user_info)

    if obj:
        product = data
    else:
        product = await fetch_or_create_product(data)

    await create_association(user.username, product.asin)

    return product

async def db_lookup(username, asin):
    if await is_associated(username, asin):
        async_session = make_session()
        async with async_session() as session:
            stmt = select(Product).where(Product.asin == asin)
            result = await session.execute(stmt)
            product = result.scalar()

        return product

    return None

async def db_bulk_lookup(chat_id):
    async_session = make_session()
    async with async_session() as session:
        stmt = select(User).where(User.chat_id == chat_id).options(selectinload(User.products))
        result = await session.execute(stmt)
        products = result.scalar().products

    if len(products) == 0:
        return None

    return products

async def remove_association_entry(username, asin=None):
    async_session = make_session()
    async with async_session() as session:
        if asin is not None:
            stmt = association_table.delete().where(association_table.c.username == username, association_table.c.product_asin == asin)
        else:
            stmt = association_table.delete().where(association_table.c.username == username)
        
        await session.execute(stmt)
        await session.commit()

async def reassign_product(username, asin):
    already_associated = await fetch_association(username, asin)

    if already_associated:
        return None

    product = await fetch_product(asin)
    if not product:
        data = await get_data(asin=asin)
        product = await create_product(data)

    await create_association(username, asin)
    return product
