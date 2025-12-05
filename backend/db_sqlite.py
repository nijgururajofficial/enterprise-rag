import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'ecommerce.db')}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    name = Column(String)
    address = Column(String, nullable=True)

class Product(Base):
    __tablename__ = "products"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    price = Column(Float)
    category = Column(String, index=True)
    description = Column(String)
    image = Column(String)
    stock = Column(Integer)
    featured = Column(Boolean, default=False)
    rating = Column(Float)

class Order(Base):
    __tablename__ = "orders"
    order_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    product_name = Column(String)
    items = Column(JSON) # Storing items as JSON for simplicity
    name = Column(String)
    address = Column(String)
    payment = Column(String)
    order_date = Column(String)
    status = Column(String)
    session_id = Column(String, nullable=True)

class Cart(Base):
    __tablename__ = "carts"
    user_id = Column(String, primary_key=True, index=True)
    items = Column(JSON, default=dict)

class Session(Base):
    __tablename__ = "sessions"
    session_id = Column(String, primary_key=True, index=True)
    context = Column(JSON, default=dict)
    messages = Column(JSON, default=list)
    chat_history = Column(JSON, default=list)

class Complaint(Base):
    __tablename__ = "complaints"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    session_id = Column(String)
    issue_type = Column(String)
    description = Column(String)
    status = Column(String)
    created_at = Column(String)
    resolution = Column(String, nullable=True)

def init_db():
    Base.metadata.create_all(bind=engine)

