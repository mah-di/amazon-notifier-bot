from datetime import datetime
from sqlalchemy import create_engine, Table, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship


Engine = create_engine("sqlite:///db.sqlite3")
Base = declarative_base()


association_table = Table(
    'association_table',
    Base.metadata,
    Column('username', String, ForeignKey('users.username')),
    Column('product_asin', String, ForeignKey('products.asin'))
)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    chat_id = Column(Integer, unique=True, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    username = Column(String, unique=True, nullable=False)
    stock_notification = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    is_admin = Column(Boolean, default=False)

    products = relationship('Product', secondary=association_table, backref="users")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    asin = Column(String, unique=True, nullable=False)
    price = Column(String, nullable=False)
    stock = Column(String, nullable=False)
    url = Column(String, nullable=False)
    last_checked = Column(DateTime, default=datetime.now)
    last_updated = Column(DateTime, default=datetime.now)


if __name__ == '__main__':
    Base.metadata.create_all(Engine)
