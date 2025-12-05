from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import base64
from models import (
    PurchaseResponse,
    UserLogin, UserRegister, LoginResponse, CartResponse,
    AddToCartRequest, ProductResponse, ChatMessage, ChatResponse, CheckoutRequest
)
from database import products, orders, users, carts, sessions
from agents import run_agent, create_agent_graph
import uuid
import jwt
from typing import List, Optional
from datetime import datetime

app = FastAPI(title="Electronics Retail API")

# Create the agent graph at module level
agent_graph = create_agent_graph()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT Configuration
SECRET_KEY = "your-secret-key-here"  # In production, use environment variable
ALGORITHM = "HS256"
security = HTTPBearer()

def create_access_token(user_id: str):
    payload = {"user_id": user_id}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None or user_id not in users:
            raise HTTPException(status_code=401, detail="Invalid token")
        return users[user_id]
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Health check
@app.get("/")
def root():
    return {"message": "Welcome to the Electronics Retail API"}

# Authentication endpoints
@app.post("/auth/register", response_model=LoginResponse)
def register(user_data: UserRegister):
    # Check if user already exists
    for user in users.values():
        if user["email"] == user_data.email:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    user_id = str(uuid.uuid4())
    users[user_id] = {
        "id": user_id,
        "email": user_data.email,
        "password": user_data.password,  # In production, hash this
        "name": user_data.name,
        "address": user_data.address
    }
    
    # Create access token
    access_token = create_access_token(user_id)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": user_data.email,
            "name": user_data.name,
            "address": user_data.address
        }
    }

@app.post("/auth/login", response_model=LoginResponse)
def login(user_data: UserLogin):
    # Find user by email
    user = None
    for u in users.values():
        if u["email"] == user_data.email and u["password"] == user_data.password:
            user = u
            break
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create access token
    access_token = create_access_token(user["id"])
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "address": user.get("address")
        }
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage):
    """
    Unified endpoint to handle all customer messages by interacting with the LangGraph agent.
    Supports image uploads via image_url (base64 encoded) in the ChatMessage.
    For file uploads, use /chat/upload endpoint.
    """
    session_id = message.session_id or str(uuid.uuid4())
    user_message = message.message
    image_url = message.image_url
    image_type = message.image_type

    # 1. Get or create the user's session
    if session_id not in sessions:
        sessions[session_id] = {"context": {}, "messages": [], "chat_history": []}
    session = sessions[session_id]

    # Store user message
    session["messages"].append({"role": "user", "content": user_message, "timestamp": datetime.now().isoformat()})

    # 2. Run the agent with the current message and session context
    agent_result = run_agent(user_message, session["context"], session["chat_history"], agent_graph, image_url, image_type)

    # Extract results from the agent's final state
    response_text = agent_result["response"]
    new_context_data = agent_result["data"]
    final_intent = agent_result["intent"]

    # 3. Perform database actions if the agent signals a completed purchase
    if final_intent == "purchase_complete" and new_context_data.get("purchase_complete"):
        order_details = new_context_data.get("order_details")
        if order_details:
            # For unauthenticated users, we'll use session_id as identifier
            order_details["session_id"] = session_id
            orders[order_details["order_id"]] = order_details

    # 4. Update the session context with the data returned by the agent
    session["context"].update(new_context_data)
    # If purchase is complete, clear the context for the next interaction
    if new_context_data.get("purchase_complete"):
        session["context"] = {}

    # Store assistant message
    session["messages"].append({"role": "assistant", "content": response_text, "timestamp": datetime.now().isoformat()})

    # Update chat_history with the new exchange
    session["chat_history"].append({"role": "user", "content": user_message})
    session["chat_history"].append({"role": "assistant", "content": response_text})

    # 5. Return the agent's response to the user
    return ChatResponse(
        message=response_text,
        intent=final_intent,
        session_id=session_id,
        data=new_context_data
    )

@app.post("/chat/upload", response_model=ChatResponse)
async def chat_with_upload(
    message: str = Form(...),
    session_id: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    image_type: Optional[str] = Form(None)
):
    """
    Endpoint to handle chat messages with file uploads.
    Supports image uploads for product defects, damaged shipping boxes, and fraudulent transaction OCR.
    """
    session_id = session_id or str(uuid.uuid4())
    user_message = message
    image_url = None

    # Handle image upload if provided
    if image:
        try:
            # Read image file and convert to base64
            image_data = await image.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            image_url = f"data:image/{image.content_type.split('/')[-1]};base64,{image_base64}"
            
            # Auto-detect image_type if not provided
            if not image_type:
                # Infer from message content
                message_lower = message.lower()
                if any(keyword in message_lower for keyword in ["defect", "broken", "damaged product", "faulty"]):
                    image_type = "product_defect"
                elif any(keyword in message_lower for keyword in ["damaged box", "shipping box", "package box", "delivery box"]):
                    image_type = "damaged_shipping_box"
                elif any(keyword in message_lower for keyword in ["fraud", "fraudulent", "unauthorized", "credit card", "transaction"]):
                    image_type = "fraudulent_transaction_ocr"
        except Exception as e:
            print(f"Error processing image: {e}")
            image_url = None

    # 1. Get or create the user's session
    if session_id not in sessions:
        sessions[session_id] = {"context": {}, "messages": [], "chat_history": []}
    session = sessions[session_id]

    # Store user message
    session["messages"].append({"role": "user", "content": user_message, "timestamp": datetime.now().isoformat()})

    # 2. Run the agent with the current message and session context
    agent_result = run_agent(user_message, session["context"], session["chat_history"], agent_graph, image_url, image_type)

    # Extract results from the agent's final state
    response_text = agent_result["response"]
    new_context_data = agent_result["data"]
    final_intent = agent_result["intent"]

    # 3. Perform database actions if the agent signals a completed purchase
    if final_intent == "purchase_complete" and new_context_data.get("purchase_complete"):
        order_details = new_context_data.get("order_details")
        if order_details:
            # For unauthenticated users, we'll use session_id as identifier
            order_details["session_id"] = session_id
            orders[order_details["order_id"]] = order_details

    # 4. Update the session context with the data returned by the agent
    session["context"].update(new_context_data)
    # If purchase is complete, clear the context for the next interaction
    if new_context_data.get("purchase_complete"):
        session["context"] = {}

    # Store assistant message
    session["messages"].append({"role": "assistant", "content": response_text, "timestamp": datetime.now().isoformat()})

    # Update chat_history with the new exchange
    session["chat_history"].append({"role": "user", "content": user_message})
    session["chat_history"].append({"role": "assistant", "content": response_text})

    # 5. Return the agent's response to the user
    return ChatResponse(
        message=response_text,
        intent=final_intent,
        session_id=session_id,
        data=new_context_data
    )

# Get chat session history
@app.get("/chat/session/{session_id}")
def get_session(session_id: str):
    """
    Get the conversation history for a specific session.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    return {
        "session_id": session_id,
        "messages": session["messages"]
    }

# Product endpoints
@app.get("/products", response_model=List[ProductResponse])
def get_products(featured: Optional[bool] = None):
    product_list = list(products.values())
    if featured is not None:
        product_list = [p for p in product_list if p["featured"] == featured]
    return product_list

@app.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: str):
    if product_id not in products:
        raise HTTPException(status_code=404, detail="Product not found")
    return products[product_id]

# Cart endpoints
@app.get("/cart", response_model=CartResponse)
def get_cart(current_user: dict = Depends(get_current_user)):
    user_cart = carts.get(current_user["id"], {})
    cart_items = []
    total = 0.0
    
    for product_id, quantity in user_cart.items():
        if product_id in products:
            product = products[product_id]
            item_total = product["price"] * quantity
            cart_items.append({
                "product": product,
                "quantity": quantity,
                "item_total": item_total
            })
            total += item_total
    
    return {"items": cart_items, "total": total}

@app.post("/cart/add")
def add_to_cart(request: AddToCartRequest, current_user: dict = Depends(get_current_user)):
    if request.product_id not in products:
        raise HTTPException(status_code=404, detail="Product not found")
    
    user_id = current_user["id"]
    if user_id not in carts:
        carts[user_id] = {}
    
    if request.product_id in carts[user_id]:
        carts[user_id][request.product_id] += request.quantity
    else:
        carts[user_id][request.product_id] = request.quantity
    
    return {"message": "Item added to cart"}

@app.delete("/cart/remove/{product_id}")
def remove_from_cart(product_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    if user_id in carts and product_id in carts[user_id]:
        del carts[user_id][product_id]
        return {"message": "Item removed from cart"}
    raise HTTPException(status_code=404, detail="Item not found in cart")

@app.put("/cart/update/{product_id}")
def update_cart_item(product_id: str, quantity: int, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    if user_id in carts and product_id in carts[user_id]:
        if quantity <= 0:
            del carts[user_id][product_id]
        else:
            carts[user_id][product_id] = quantity
        return {"message": "Cart updated"}
    raise HTTPException(status_code=404, detail="Item not found in cart")

# Checkout entire cart
@app.post("/checkout", response_model=PurchaseResponse)
def checkout_cart(
    request: CheckoutRequest,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    user_cart = carts.get(user_id, {})
    
    if not user_cart:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Generate order ID
    order_id = str(uuid.uuid4())[:8]
    orders[order_id] = {
        "user_id": user_id,
        "items": user_cart.copy(),
        "name": current_user["name"],
        "address": request.shipping_address,
        "payment": request.payment_method,
    }
    
    # Clear the cart
    carts[user_id] = {}
    
    return {"order_id": order_id, "status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)