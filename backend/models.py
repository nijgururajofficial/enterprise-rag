from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# Unified Chat Message Models
class ChatMessage(BaseModel):
    message: str
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None  # For maintaining conversation context

class ChatResponse(BaseModel):
    message: str
    intent: str  # recommendation, purchase_prompt, purchase_complete, decline, general
    session_id: str
    data: Optional[Dict[str, Any]] = None  # For product details, order info, etc.
    
# Legacy models (keeping for backward compatibility if needed)
class QueryRequest(BaseModel):
    query: str

# Recommendation response
class RecommendationResponse(BaseModel):
    recommended_product: dict

# Purchase request
class PurchaseRequest(BaseModel):
    product_id: str
    name: str
    shipping_address: str
    payment_method: str

# Purchase response
class PurchaseResponse(BaseModel):
    order_id: str
    status: str

# User authentication models
class UserLogin(BaseModel):
    email: str
    password: str

class UserRegister(BaseModel):
    email: str
    password: str
    name: str
    address: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    address: Optional[str] = None

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Cart models
class CartItem(BaseModel):
    product_id: str
    quantity: int

class CartResponse(BaseModel):
    items: List[dict]
    total: float

class AddToCartRequest(BaseModel):
    product_id: str
    quantity: int = 1

# Product models
class ProductResponse(BaseModel):
    id: str
    name: str
    price: float
    category: str
    description: str
    image: str
    stock: int
    featured: bool
    rating: float
