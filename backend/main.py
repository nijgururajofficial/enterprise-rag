from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models import (
    QueryRequest, PurchaseRequest, PurchaseResponse, RecommendationResponse,
    UserLogin, UserRegister, LoginResponse, UserResponse, CartResponse,
    AddToCartRequest, ProductResponse, ChatMessage, ChatResponse
)
from database import products, orders, users, carts, sessions
from agents import get_product_recommendations, detect_intent, generate_response, extract_purchase_info
import uuid
import jwt
import re
from typing import List, Optional
from datetime import datetime

app = FastAPI(title="Electronics Retail API")

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

# ============================================
# UNIFIED CHAT ENDPOINT - Main AI Agent Interface
# ============================================
"""
UNIFIED MESSAGING SYSTEM - How it works:

1. Customer sends a message from the browser to /chat endpoint
2. The endpoint routes the message to the correct AI Agent based on detected intent
3. AI Agent uses customer preferences/needs to recommend products
4. Customer can accept (purchase) or decline the recommendation
5. If accepting, customer provides Name, Shipping Address, and Payment in a message
6. System validates the information and completes the transaction
7. Customer receives an order number upon successful purchase

Example conversation flow:
- User: "I need a laptop for work"
- AI: Recommends laptop with details, asks if they want to purchase
- User: "Yes, I'll buy it"
- AI: Asks for purchase information
- User: "Name: John Doe, Address: 123 Main St, Payment: Credit Card"
- AI: Returns order number and confirmation
"""

@app.post("/chat", response_model=ChatResponse)
def chat(message: ChatMessage, current_user: dict = Depends(get_current_user)):
    """
    Unified endpoint to handle all customer messages.
    This endpoint:
    1. Receives messages from the browser
    2. Routes to the correct AI agent based on intent
    3. Handles product recommendations
    4. Processes purchase decisions and transactions
    5. Returns order numbers upon successful purchase
    """
    user_id = current_user["id"]
    
    # Get or create session
    session_id = message.session_id or str(uuid.uuid4())
    
    if session_id not in sessions:
        sessions[session_id] = {
            "context": {},
            "messages": [],
            "user_id": user_id,
            "created_at": datetime.now().isoformat()
        }
    
    session = sessions[session_id]
    
    # Merge context from message with session context
    if message.context:
        session["context"].update(message.context)
    
    # Store user message
    session["messages"].append({
        "role": "user",
        "content": message.message,
        "timestamp": datetime.now().isoformat()
    })
    
    # Detect intent using AI agent
    intent = detect_intent(message.message, session["context"])
    
    # Handle different intents
    if intent == "recommendation":
        # AI Agent recommends product based on customer preferences
        response_text, data = generate_response(intent, message.message, session["context"])
        
        # Update session context with recommended product
        session["context"]["recommended_product"] = data.get("product")
        session["context"]["awaiting_purchase_decision"] = data.get("awaiting_purchase_decision", False)
        
        # Store assistant message
        session["messages"].append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat()
        })
        
        return ChatResponse(
            message=response_text,
            intent="recommendation",
            session_id=session_id,
            data=data
        )
    
    elif intent == "purchase_accept":
        # Customer accepts the recommendation
        product = session["context"].get("recommended_product")
        
        # Pre-fill user info if available
        user_info = {
            "name": current_user.get("name"),
            "address": current_user.get("address")
        }
        
        # Generate response asking for missing info or payment
        missing_info = []
        if not user_info.get("name"):
            missing_info.append("your full name")
        if not user_info.get("address"):
            missing_info.append("shipping address")
        
        if missing_info:
            response_text = (
                f"Excellent! I'll help you complete your purchase of the **{product['name']}**.\n\n"
                f"I need the following information:\n"
                f"{chr(10).join([f'{i+1}️⃣ {info}' for i, info in enumerate(missing_info)])}\n"
                f"{len(missing_info)+1}️⃣ Payment method\n\n"
                f"You can provide all information in one message."
            )
        else:
            # User info is complete, just ask for payment
            response_text = (
                f"Excellent! I'll help you complete your purchase of the **{product['name']}**.\n\n"
                f"I have your details:\n"
                f"✓ Name: {user_info['name']}\n"
                f"✓ Address: {user_info['address']}\n\n"
                f"Please provide your payment method (e.g., 'Credit Card', 'Debit Card', 'PayPal')"
            )
        
        session["context"]["awaiting_purchase_info"] = True
        session["context"]["awaiting_purchase_decision"] = False
        session["context"]["user_info_prefilled"] = user_info
        
        # Store assistant message
        session["messages"].append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat()
        })
        
        return ChatResponse(
            message=response_text,
            intent="purchase_prompt",
            session_id=session_id,
            data={"product": product, "user_info": user_info}
        )
    
    elif intent == "product_selection":
        # Customer is selecting a specific product from multiple recommendations
        response_text, data = generate_response(intent, message.message, session["context"])
        
        # Update session context with selected product
        session["context"].update(data)
        if data.get("recommended_product"):
            session["context"]["recommended_product"] = data["recommended_product"]
        
        # Store assistant message
        session["messages"].append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat()
        })
        
        return ChatResponse(
            message=response_text,
            intent="product_selected",
            session_id=session_id,
            data=data
        )
    
    elif intent == "purchase_decline":
        # Customer declines the recommendation
        response_text, data = generate_response(intent, message.message, session["context"])
        
        # Update session context
        session["context"].update(data)
        
        # Store assistant message
        session["messages"].append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat()
        })
        
        return ChatResponse(
            message=response_text,
            intent="decline",
            session_id=session_id,
            data=data
        )
    
    elif intent == "purchase_info":
        # Customer provides purchase information (Name, Address, Payment)
        purchase_info = extract_purchase_info(message.message)
        product = session["context"].get("recommended_product")
        
        if not product:
            raise HTTPException(status_code=400, detail="No product selected for purchase")
        
        # Use pre-filled user info if available
        prefilled_info = session["context"].get("user_info_prefilled", {})
        if not purchase_info.get("name") and prefilled_info.get("name"):
            purchase_info["name"] = prefilled_info["name"]
        if not purchase_info.get("address") and prefilled_info.get("address"):
            purchase_info["address"] = prefilled_info["address"]
        
        # Validate that we have all required information
        missing_fields = []
        if not purchase_info.get("name"):
            missing_fields.append("name")
        if not purchase_info.get("address"):
            missing_fields.append("shipping address")
        if not purchase_info.get("payment"):
            missing_fields.append("payment method")
        
        if missing_fields:
            response_text = f"I need some more information. Please provide your {', '.join(missing_fields)}."
            session["messages"].append({
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.now().isoformat()
            })
            return ChatResponse(
                message=response_text,
                intent="purchase_prompt",
                session_id=session_id,
                data={"missing_fields": missing_fields}
            )
        
        # Check if payment method is credit/debit card and needs card details
        payment_lower = purchase_info["payment"].lower()
        if any(word in payment_lower for word in ["credit", "debit", "card"]) and not session["context"].get("card_details_provided"):
            # Ask for card details
            response_text = (
                f"Great! To complete your purchase with {purchase_info['payment']}, please provide:\n\n"
                f"🔒 **Secure Payment Information:**\n"
                f"• Card Number (16 digits)\n"
                f"• Expiry Date (MM/YY)\n"
                f"• CVV (3-4 digits)\n"
                f"• Cardholder Name\n\n"
                f"Example: 'Card: 1234 5678 9012 3456, Expiry: 12/25, CVV: 123, Name: John Doe'"
            )
            
            # Store purchase info temporarily
            session["context"]["pending_purchase_info"] = purchase_info
            session["context"]["awaiting_card_details"] = True
            session["context"]["awaiting_purchase_info"] = False
            
            session["messages"].append({
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.now().isoformat()
            })
            
            return ChatResponse(
                message=response_text,
                intent="awaiting_card_details",
                session_id=session_id,
                data={"purchase_info": purchase_info}
            )
        
        # Process the purchase - Generate order number
        order_id = str(uuid.uuid4())[:8].upper()
        orders[order_id] = {
            "product_id": product["id"],
            "product_name": product["name"],
            "price": product["price"],
            "user_id": user_id,
            "name": purchase_info["name"],
            "address": purchase_info["address"],
            "payment": purchase_info["payment"],
            "order_date": datetime.now().isoformat(),
            "status": "confirmed"
        }
        
        # Clear session context after successful purchase
        session["context"] = {}
        
        # Generate success message
        response_text = (
            f"🎉 Purchase successful! Your order has been confirmed.\n\n"
            f"**Order Number: {order_id}**\n\n"
            f"Product: {product['name']}\n"
            f"Price: ${product['price']:.2f}\n"
            f"Shipping to: {purchase_info['address']}\n\n"
            f"Thank you for your purchase! Your order will be shipped within 2-3 business days."
        )
        
        # Store assistant message
        session["messages"].append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat()
        })
        
        return ChatResponse(
            message=response_text,
            intent="purchase_complete",
            session_id=session_id,
            data={
                "order_id": order_id,
                "product": product,
                "purchase_info": purchase_info
            }
        )
    
    elif session["context"].get("awaiting_card_details"):
        # Customer is providing credit card details
        product = session["context"].get("recommended_product")
        purchase_info = session["context"].get("pending_purchase_info", {})
        
        if not product or not purchase_info:
            raise HTTPException(status_code=400, detail="Session data lost. Please start over.")
        
        # Extract card details (basic extraction - in production, use secure payment gateway)
        card_info = {}
        message_text = message.message.lower()
        
        # Check if message contains card-like information
        if re.search(r'\d{4}', message_text):  # Has some digits
            card_info["provided"] = True
        
        if not card_info.get("provided"):
            response_text = "Please provide your card details to complete the purchase."
            session["messages"].append({
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.now().isoformat()
            })
            return ChatResponse(
                message=response_text,
                intent="awaiting_card_details",
                session_id=session_id,
                data={}
            )
        
        # Process the purchase - Generate order number
        # NOTE: In production, you would validate card details with a payment gateway here
        order_id = str(uuid.uuid4())[:8].upper()
        orders[order_id] = {
            "product_id": product["id"],
            "product_name": product["name"],
            "price": product["price"],
            "user_id": user_id,
            "name": purchase_info["name"],
            "address": purchase_info["address"],
            "payment": purchase_info["payment"],
            "payment_details": "Card ending in XXXX (secured)",  # Never store full card details
            "order_date": datetime.now().isoformat(),
            "status": "confirmed"
        }
        
        # Clear session context after successful purchase
        session["context"] = {}
        
        # Generate success message
        response_text = (
            f"🎉 Payment processed successfully! Your order has been confirmed.\n\n"
            f"**Order Number: {order_id}**\n\n"
            f"Product: {product['name']}\n"
            f"Price: ${product['price']:.2f}\n"
            f"Shipping to: {purchase_info['address']}\n"
            f"Payment: {purchase_info['payment']} (secured)\n\n"
            f"✅ Your card has been charged ${product['price']:.2f}\n\n"
            f"Thank you for your purchase! Your order will be shipped within 2-3 business days."
        )
        
        # Store assistant message
        session["messages"].append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat()
        })
        
        return ChatResponse(
            message=response_text,
            intent="purchase_complete",
            session_id=session_id,
            data={
                "order_id": order_id,
                "product": product,
                "purchase_info": purchase_info
            }
        )
    
    else:  # general intent
        response_text, data = generate_response(intent, message.message, session["context"])
        
        # Store assistant message
        session["messages"].append({
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.now().isoformat()
        })
        
        return ChatResponse(
            message=response_text,
            intent="general",
            session_id=session_id,
            data=data
        )

# Get chat session history
@app.get("/chat/session/{session_id}")
def get_session(session_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get the conversation history for a specific session.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    # Verify the session belongs to the current user
    if session["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "session_id": session_id,
        "messages": session["messages"],
        "created_at": session["created_at"]
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

# ============================================
# DEPRECATED ENDPOINTS - Use /chat instead
# ============================================
# These endpoints are kept for backward compatibility but the /chat endpoint
# is the preferred way to handle recommendations and purchases

# 1. Get product recommendation (DEPRECATED - Use /chat)
@app.post("/recommend", response_model=RecommendationResponse, deprecated=True)
def get_recommendation(request: QueryRequest):
    """
    DEPRECATED: Use the /chat endpoint instead for a unified conversational experience.
    """
    recommendations = get_product_recommendations(request.query)
    if not recommendations:
        raise HTTPException(status_code=404, detail="No recommendation found")
    return {"recommended_product": recommendations[0]}

# 2. Purchase a product (DEPRECATED - Use /chat)
@app.post("/purchase", response_model=PurchaseResponse, deprecated=True)
def purchase_item(request: PurchaseRequest, current_user: dict = Depends(get_current_user)):
    """
    DEPRECATED: Use the /chat endpoint instead for a unified conversational experience.
    """
    if request.product_id not in products:
        raise HTTPException(status_code=404, detail="Product not found")

    # Generate order ID
    order_id = str(uuid.uuid4())[:8]
    orders[order_id] = {
        "product_id": request.product_id,
        "user_id": current_user["id"],
        "name": request.name,
        "address": request.shipping_address,
        "payment": request.payment_method,
    }

    # Clear the item from cart if it exists
    user_id = current_user["id"]
    if user_id in carts and request.product_id in carts[user_id]:
        del carts[user_id][request.product_id]

    return {"order_id": order_id, "status": "success"}

# Checkout entire cart
@app.post("/checkout", response_model=PurchaseResponse)
def checkout_cart(
    shipping_address: str,
    payment_method: str,
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
        "address": shipping_address,
        "payment": payment_method,
    }
    
    # Clear the cart
    carts[user_id] = {}
    
    return {"order_id": order_id, "status": "success"}
