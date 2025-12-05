from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import base64
from models import (
    PurchaseResponse, OrderResponse, ComplaintResponse,
    UserLogin, UserRegister, LoginResponse, CartResponse,
    AddToCartRequest, ProductResponse, ChatMessage, ChatResponse, CheckoutRequest
)
from database import (
    get_all_products, get_product_by_id, 
    get_user_by_email, get_user_by_id, create_user,
    get_cart, update_cart,
    create_order, get_user_orders, get_user_complaints, update_order,
    get_session, update_session
)
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
security_optional = HTTPBearer(auto_error=False)

def create_access_token(user_id: str):
    payload = {"user_id": user_id}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        user = get_user_by_id(user_id)
        if user_id is None or not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional)):
    if not credentials:
        return None
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        return get_user_by_id(user_id)
    except:
        return None

# Health check
@app.get("/")
def root():
    return {"message": "Welcome to the Electronics Retail API"}

# Authentication endpoints
@app.post("/auth/register", response_model=LoginResponse)
def register(user_data: UserRegister):
    # Check if user already exists
    if get_user_by_email(user_data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    user_id = str(uuid.uuid4())
    new_user = {
        "id": user_id,
        "email": user_data.email,
        "password": user_data.password,  # In production, hash this
        "name": user_data.name,
        "address": user_data.address
    }
    create_user(new_user)
    
    # Create access token
    access_token = create_access_token(user_id)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": new_user
    }

@app.post("/auth/login", response_model=LoginResponse)
def login(user_data: UserLogin):
    # Find user by email
    user = get_user_by_email(user_data.email)
    
    if not user or user["password"] != user_data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create access token
    access_token = create_access_token(user["id"])
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(message: ChatMessage, user: dict = Depends(get_current_user)):
    """
    Unified endpoint to handle all customer messages by interacting with the LangGraph agent.
    Supports image uploads via image_url (base64 encoded) in the ChatMessage.
    For file uploads, use /chat/upload endpoint.
    Requires authentication.
    """
    session_id = message.session_id or str(uuid.uuid4())
    user_message = message.message
    image_url = message.image_url
    image_type = message.image_type
    
    user_id = user["id"]

    # 1. Get or create the user's session
    session = get_session(session_id)

    # Store user message
    session["messages"].append({"role": "user", "content": user_message, "timestamp": datetime.now().isoformat()})
    
    # Update session in DB
    update_session(session_id, session)

    # 2. Run the agent with the current message and session context
    agent_result = run_agent(user_message, session["context"], session["chat_history"], agent_graph, image_url, image_type, user_id=user_id, session_id=session_id)

    # Extract results from the agent's final state
    response_text = agent_result["response"]
    new_context_data = agent_result["data"]
    final_intent = agent_result["intent"]

    # 3. Perform database actions if the agent signals a completed purchase
    if final_intent == "purchase_complete" and new_context_data.get("purchase_complete"):
        order_details = new_context_data.get("order_details")
        if order_details:
            # Ensure user_id is attached to the order
            order_details["user_id"] = user_id
            order_details["session_id"] = session_id
            create_order(order_details)

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
    
    # Update session in DB again
    update_session(session_id, session)

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
    user_id: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    image_type: Optional[str] = Form(None),
    user: dict = Depends(get_current_user)
):
    """
    Endpoint to handle chat messages with file uploads.
    Supports image uploads for product defects, damaged shipping boxes, and fraudulent transaction OCR.
    Requires authentication.
    """
    session_id = session_id or str(uuid.uuid4())
    user_message = message
    image_url = None
    
    actual_user_id = user["id"]

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
    session = get_session(session_id)

    # Store user message
    session["messages"].append({"role": "user", "content": user_message, "timestamp": datetime.now().isoformat()})

    # Update session in DB
    update_session(session_id, session)

    # 2. Run the agent with the current message and session context
    agent_result = run_agent(user_message, session["context"], session["chat_history"], agent_graph, image_url, image_type, user_id=actual_user_id, session_id=session_id)

    # Extract results from the agent's final state
    response_text = agent_result["response"]
    new_context_data = agent_result["data"]
    final_intent = agent_result["intent"]

    # 3. Perform database actions if the agent signals a completed purchase
    if final_intent == "purchase_complete" and new_context_data.get("purchase_complete"):
        order_details = new_context_data.get("order_details")
        if order_details:
            # Ensure user_id is attached to the order
            order_details["user_id"] = actual_user_id
            order_details["session_id"] = session_id
            create_order(order_details)

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
    
    # Update session in DB again
    update_session(session_id, session)

    # 5. Return the agent's response to the user
    return ChatResponse(
        message=response_text,
        intent=final_intent,
        session_id=session_id,
        data=new_context_data
    )

# Get chat session history
@app.get("/chat/session/{session_id}")
def get_session_endpoint(session_id: str):
    """
    Get the conversation history for a specific session.
    """
    session = get_session(session_id)
    # Check if session exists (has messages) or return empty structure
    # The helper get_session always returns a dict, so we can check if it has content or not
    # However, for 404 behavior we might need to change get_session or check here if empty
    
    return {
        "session_id": session_id,
        "messages": session["messages"]
    }

# Product endpoints
@app.get("/products", response_model=List[ProductResponse])
def get_products_endpoint(featured: Optional[bool] = None):
    return get_all_products(featured)

@app.get("/products/{product_id}", response_model=ProductResponse)
def get_product_endpoint(product_id: str):
    product = get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

# Cart endpoints
@app.get("/cart", response_model=CartResponse)
def get_cart_endpoint(current_user: dict = Depends(get_current_user)):
    user_cart = get_cart(current_user["id"])
    cart_items = []
    total = 0.0
    
    for product_id, quantity in user_cart.items():
        product = get_product_by_id(product_id)
        if product:
            item_total = product["price"] * quantity
            cart_items.append({
                "product": product,
                "quantity": quantity,
                "item_total": item_total
            })
            total += item_total
    
    return {"items": cart_items, "total": total}

@app.post("/cart/add")
def add_to_cart_endpoint(request: AddToCartRequest, current_user: dict = Depends(get_current_user)):
    product = get_product_by_id(request.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    user_id = current_user["id"]
    user_cart = get_cart(user_id)
    
    if request.product_id in user_cart:
        user_cart[request.product_id] += request.quantity
    else:
        user_cart[request.product_id] = request.quantity
    
    update_cart(user_id, user_cart)
    
    return {"message": "Item added to cart"}

@app.delete("/cart/remove/{product_id}")
def remove_from_cart_endpoint(product_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    user_cart = get_cart(user_id)
    
    if product_id in user_cart:
        del user_cart[product_id]
        update_cart(user_id, user_cart)
        return {"message": "Item removed from cart"}
    raise HTTPException(status_code=404, detail="Item not found in cart")

@app.put("/cart/update/{product_id}")
def update_cart_item_endpoint(product_id: str, quantity: int, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    user_cart = get_cart(user_id)
    
    if product_id in user_cart:
        if quantity <= 0:
            del user_cart[product_id]
        else:
            user_cart[product_id] = quantity
        update_cart(user_id, user_cart)
        return {"message": "Cart updated"}
    raise HTTPException(status_code=404, detail="Item not found in cart")

# Checkout entire cart
@app.post("/checkout", response_model=PurchaseResponse)
def checkout_cart_endpoint(
    request: CheckoutRequest,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    user_cart = get_cart(user_id)
    
    if not user_cart:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Generate order ID
    order_id = str(uuid.uuid4())[:8]
    
    order_data = {
        "order_id": order_id,
        "user_id": user_id,
        "items": user_cart.copy(),
        "name": current_user["name"],
        "address": request.shipping_address,
        "payment": request.payment_method,
        "status": "confirmed",
        "order_date": datetime.now().isoformat()
    }
    create_order(order_data)
    
    # Clear the cart
    update_cart(user_id, {})
    
    return {"order_id": order_id, "status": "success"}

@app.get("/orders", response_model=List[OrderResponse])
def get_orders_endpoint(current_user: dict = Depends(get_current_user)):
    user_orders = get_user_orders(current_user["id"])
    
    updated_orders = []
    for order in user_orders:
        # Simulate status updates based on time elapsed
        try:
            # Handle cases where isoformat might be slightly different or timezone aware/naive mismatch
            # Assuming stored as isoformat string
            if order.get("order_date"):
                order_date = datetime.fromisoformat(order["order_date"])
                elapsed_minutes = (datetime.now() - order_date).total_seconds() / 60
                
                current_status = order.get("status", "").lower()
                new_status = None
                
                if elapsed_minutes > 10 and current_status != "delivered":
                    new_status = "delivered"
                elif elapsed_minutes > 5 and current_status not in ["shipped", "delivered"]:
                    new_status = "shipped"
                elif elapsed_minutes > 1 and current_status not in ["processing", "shipped", "delivered"]:
                    new_status = "processing"
                
                if new_status:
                    update_order(order["order_id"], {"status": new_status})
                    order["status"] = new_status
        except Exception as e:
            print(f"Error simulating status update for order {order.get('order_id')}: {e}")

        # Calculate totals if not stored
        if not order.get("total_amount"):
            total = 0.0
            items = order.get("items", {})
            for pid, qty in items.items():
                p = get_product_by_id(pid)
                if p:
                    total += p["price"] * qty
            order["total_amount"] = total
        updated_orders.append(order)
            
    return updated_orders

@app.get("/complaints", response_model=List[ComplaintResponse])
def get_complaints_endpoint(current_user: dict = Depends(get_current_user)):
    return get_user_complaints(current_user["id"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)