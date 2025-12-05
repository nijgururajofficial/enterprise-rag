import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from db_sqlite import SessionLocal, init_db, Product, User, Order, Cart, Session as DbSession, Complaint
from initial_data import products as initial_products, users as initial_users

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

load_dotenv()

# Initialize SQLite
init_db()

# Initialize ChromaDB
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PERSIST_DIRECTORY = os.path.join(BASE_DIR, "chroma_db")
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vector_store = Chroma(
    collection_name="products",
    embedding_function=embeddings,
    persist_directory=PERSIST_DIRECTORY,
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Seeding Data ---
def seed_data():
    db = SessionLocal()
    
    # Seed Products if empty
    if db.query(Product).count() == 0:
        print("Seeding products to SQLite and ChromaDB...")
        product_docs = []
        for p_id, p_data in initial_products.items():
            # Add to SQLite
            db_product = Product(
                id=p_data["id"],
                name=p_data["name"],
                price=p_data["price"],
                category=p_data["category"],
                description=p_data["description"],
                image=p_data["image"],
                stock=p_data["stock"],
                featured=p_data["featured"],
                rating=p_data["rating"]
            )
            db.add(db_product)
            
            # Prepare for ChromaDB
            # We'll store the product ID in metadata to link back to SQLite
            doc = Document(
                page_content=f"{p_data['name']} - {p_data['description']} Category: {p_data['category']}",
                metadata=p_data
            )
            product_docs.append(doc)
        
        db.commit()
        
        # Add to ChromaDB
        if product_docs:
            vector_store.add_documents(product_docs)
            print("Products seeded.")

    # Seed Users if empty
    if db.query(User).count() == 0:
        print("Seeding users...")
        for u_id, u_data in initial_users.items():
            db_user = User(
                id=u_data["id"],
                email=u_data["email"],
                password=u_data["password"],
                name=u_data["name"],
                address=u_data["address"]
            )
            db.add(db_user)
        db.commit()
        print("Users seeded.")
    
    db.close()

# Run seeding on module import
seed_data()

# --- Data Access Layers (replacing global dicts) ---

def to_dict(obj):
    if not obj:
        return None
    d = obj.__dict__.copy()
    if "_sa_instance_state" in d:
        del d["_sa_instance_state"]
    return d

# Products
def get_all_products(featured: Optional[bool] = None) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        query = db.query(Product)
        if featured is not None:
            query = query.filter(Product.featured == featured)
        products = query.all()
        return [to_dict(p) for p in products]
    finally:
        db.close()

def get_product_by_id(product_id: str) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        return to_dict(product)
    finally:
        db.close()

def search_products_vector(query: str, k: int = 5, filter_criteria: dict = None) -> List[Dict[str, Any]]:
    """
    Search products using ChromaDB vector store.
    """
    # Chroma filter format
    where_filter = {}
    if filter_criteria:
        if "category" in filter_criteria:
            where_filter["category"] = filter_criteria["category"]
        if "min_rating" in filter_criteria:
             # Chroma doesn't support complex operators easily in 'where', handled in post-processing usually
             # or strict match. We'll handle complex filtering after retrieval or improve metadata
             pass
             
    results = vector_store.similarity_search(query, k=k * 2, filter=where_filter if where_filter else None) # Fetch more to filter
    
    products = []
    for doc in results:
        p_data = doc.metadata
        
        # Apply filters that vector search might miss or that are range-based
        if filter_criteria:
            if "min_price" in filter_criteria and p_data.get("price", 0) < filter_criteria["min_price"]:
                continue
            if "max_price" in filter_criteria and p_data.get("price", 0) > filter_criteria["max_price"]:
                continue
            if "min_rating" in filter_criteria and p_data.get("rating", 0) < filter_criteria["min_rating"]:
                continue
        
        products.append(p_data)
        if len(products) >= k:
            break
            
    return products

# Users
def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        return to_dict(user)
    finally:
        db.close()

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        return to_dict(user)
    finally:
        db.close()

def create_user(user_data: Dict[str, Any]):
    db = SessionLocal()
    try:
        db_user = User(**user_data)
        db.add(db_user)
        db.commit()
        return user_data
    finally:
        db.close()

# Carts
def get_cart(user_id: str) -> Dict[str, int]:
    db = SessionLocal()
    try:
        cart = db.query(Cart).filter(Cart.user_id == user_id).first()
        if cart:
            return cart.items or {}
        return {}
    finally:
        db.close()

def update_cart(user_id: str, items: Dict[str, int]):
    db = SessionLocal()
    try:
        cart = db.query(Cart).filter(Cart.user_id == user_id).first()
        if not cart:
            cart = Cart(user_id=user_id, items=items)
            db.add(cart)
        else:
            cart.items = items
        db.commit()
    finally:
        db.close()

# Orders
def create_order(order_data: Dict[str, Any]):
    db = SessionLocal()
    try:
        # Separate JSON fields or ensure they are dicts
        items = order_data.pop("items", {})
        
        db_order = Order(
            order_id=order_data["order_id"],
            user_id=order_data.get("user_id"), # Optional for guest checkout?
            product_name=order_data.get("product_name"),
            items=items,
            name=order_data["name"],
            address=order_data["address"],
            payment=order_data["payment"],
            order_date=order_data.get("order_date"),
            status=order_data.get("status"),
            session_id=order_data.get("session_id")
        )
        db.add(db_order)
        db.commit()
    finally:
        db.close()

def get_order(order_id: str) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.order_id == order_id).first()
        return to_dict(order)
    finally:
        db.close()

def update_order(order_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if order:
            for key, value in data.items():
                if hasattr(order, key):
                    setattr(order, key, value)
            db.commit()
            return to_dict(order)
        return None
    finally:
        db.close()

def get_user_orders(user_id: str) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        orders = db.query(Order).filter(Order.user_id == user_id).all()
        return [to_dict(o) for o in orders]
    finally:
        db.close()

# Sessions
def get_session(session_id: str) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        session = db.query(DbSession).filter(DbSession.session_id == session_id).first()
        if session:
            return {
                "context": session.context or {},
                "messages": session.messages or [],
                "chat_history": session.chat_history or []
            }
        # Return default structure if not found (lazy creation logic in main app)
        return {"context": {}, "messages": [], "chat_history": []}
    finally:
        db.close()

def update_session(session_id: str, data: Dict[str, Any]):
    db = SessionLocal()
    try:
        session = db.query(DbSession).filter(DbSession.session_id == session_id).first()
        if not session:
            session = DbSession(
                session_id=session_id,
                context=data.get("context", {}),
                messages=data.get("messages", []),
                chat_history=data.get("chat_history", [])
            )
            db.add(session)
        else:
            if "context" in data:
                session.context = data["context"]
            if "messages" in data:
                session.messages = data["messages"]
            if "chat_history" in data:
                session.chat_history = data["chat_history"]
        db.commit()
    finally:
        db.close()

# Complaints
def create_complaint(complaint_data: Dict[str, Any]):
    db = SessionLocal()
    try:
        db_complaint = Complaint(**complaint_data)
        db.add(db_complaint)
        db.commit()
        return complaint_data
    finally:
        db.close()

def get_user_complaints(user_id: str) -> List[Dict[str, Any]]:
    db = SessionLocal()
    try:
        complaints = db.query(Complaint).filter(Complaint.user_id == user_id).all()
        return [to_dict(c) for c in complaints]
    finally:
        db.close()
