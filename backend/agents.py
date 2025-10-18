import os
import re
from typing import Dict, Any, Tuple, List, TypedDict, Annotated
from database import products
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import operator

# Initialize Gemini API
# Set your API key: export GEMINI_API_KEY='your-api-key-here' or set in .env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not set. Using fallback mode.")
    USE_GEMINI = False
else:
    USE_GEMINI = True
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=GEMINI_API_KEY,
        temperature=0.7,
        convert_system_message_to_human=True
    )

# ============================================
# LangGraph State Definition
# ============================================

class AgentState(TypedDict):
    """State for the agent graph"""
    message: str
    context: Dict[str, Any]
    intent: str
    recommendations: List[Dict[str, Any]]
    response: str
    data: Dict[str, Any]
    chat_history: Annotated[List, operator.add]


# ============================================
# Agent Nodes
# ============================================

def intent_detection_node(state: AgentState) -> AgentState:
    """
    Node to detect user intent using Gemini API
    """
    message = state["message"]
    context = state.get("context", {})
    
    if USE_GEMINI:
        # Use Gemini to detect intent
        system_prompt = """You are an intent classifier for an e-commerce chatbot. 
        Analyze the user's message and return ONLY ONE of these intents:
        - recommendation: User wants product recommendations
        - product_selection: User is selecting from multiple recommended products
        - purchase_accept: User accepts and wants to buy the CURRENT recommended product
        - purchase_decline: User declines the purchase
        - purchase_info: User is providing purchase information (name, address, payment)
        - general: General greeting or unclear intent
        
        IMPORTANT RULES:
        - If awaiting_purchase_decision=True:
          * Simple acceptance like "yes", "ok", "buy it", "I'll take it" → purchase_accept
          * BUT if they mention a DIFFERENT product (e.g., "I want to buy a laptop" when phone was recommended) → recommendation (NEW product request)
          * Decline words like "no", "decline" → purchase_decline
        - If multiple_recommendations=True, look for option selection → product_selection
        - If awaiting_purchase_info=True → purchase_info
        - If message mentions product categories (phone, laptop, headphones, etc.) with "buy", "want", "need" → recommendation
        
        Return ONLY the intent name, nothing else."""
        
        context_info = f"\nContext: {context}" if context else ""
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Message: {message}{context_info}")
            ]
            response = llm.invoke(messages)
            intent = response.content.strip().lower()
            
            # Validate intent
            valid_intents = ["recommendation", "product_selection", "purchase_accept", 
                           "purchase_decline", "purchase_info", "general"]
            if intent not in valid_intents:
                intent = "general"
                
        except Exception as e:
            print(f"Gemini API error in intent detection: {e}")
            intent = detect_intent_fallback(message, context)
    else:
        intent = detect_intent_fallback(message, context)
    
    state["intent"] = intent
    return state


def recommendation_node(state: AgentState) -> AgentState:
    """
    Node to generate product recommendations using Gemini API
    """
    message = state["message"]
    
    if USE_GEMINI:
        # Use Gemini to analyze query and extract preferences
        system_prompt = """You are a product recommendation expert for an electronics store.
        Analyze the user's query and extract:
        1. Product category (phone, laptop, headphones, earbuds, speaker, watch, monitor, keyboard)
        2. Budget range (if mentioned)
        3. Key preferences or features
        
        Available products:
        - Phone: iPhone 15 Pro ($999)
        - Laptop: MacBook Pro M3 ($1999)
        - Headphones: Sony WH-1000XM5 ($349)
        - Earbuds: AirPods Pro 2nd Gen ($249)
        - Speaker: HomePod Mini ($99)
        - Watch: Apple Watch Series 9 ($399)
        - Monitor: LG UltraGear 4K ($599)
        - Keyboard: Keychron K2 Mechanical ($89)
        
        Return a JSON-like response with:
        category: <detected category>
        min_budget: <number or 0>
        max_budget: <number or 10000>
        """
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"User query: {message}")
            ]
            response = llm.invoke(messages)
            
            # Parse Gemini response
            recommendations = parse_recommendations_from_gemini(response.content, message)
            
        except Exception as e:
            print(f"Gemini API error in recommendations: {e}")
            recommendations = get_product_recommendations_fallback(message)
    else:
        recommendations = get_product_recommendations_fallback(message)
    
    state["recommendations"] = recommendations
    return state


def response_generation_node(state: AgentState) -> AgentState:
    """
    Node to generate natural language responses using Gemini API
    """
    intent = state["intent"]
    message = state["message"]
    context = state.get("context", {})
    recommendations = state.get("recommendations", [])
    
    if USE_GEMINI and intent in ["recommendation", "general"]:
        # Use Gemini for natural response generation
        system_prompt = """You are a friendly e-commerce shopping assistant.
        Generate a helpful, engaging response based on the intent and data provided.
        Keep responses conversational but concise.
        Use emojis sparingly (1-2 max).
        """
        
        if intent == "recommendation" and recommendations:
            product_info = "\n".join([
                f"- {p['name']}: ${p['price']:.2f}, Rating: {p['rating']}/5, {p['stock']} in stock"
                for p in recommendations[:3]
            ])
            
            prompt = f"""The user asked: "{message}"
            
            Recommended products:
            {product_info}
            
            Generate a response that:
            1. Briefly acknowledges their request
            2. Presents the product(s) with key details
            3. Asks if they want to purchase
            
            Format with clear product names in bold using **Product Name** and include price, rating, and stock.
            """
            
            try:
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=prompt)
                ]
                response = llm.invoke(messages)
                response_text = response.content.strip()
                
                # Ensure we ask about purchase
                if "purchase" not in response_text.lower() and "buy" not in response_text.lower():
                    response_text += "\n\nWould you like to purchase this product?"
                
                data = {
                    "product": recommendations[0] if len(recommendations) == 1 else None,
                    "recommendations": recommendations,
                    "awaiting_purchase_decision": len(recommendations) == 1,
                    "multiple_recommendations": len(recommendations) > 1
                }
                
                state["response"] = response_text
                state["data"] = data
                return state
                
            except Exception as e:
                print(f"Gemini API error in response generation: {e}")
    
    # Fallback or non-Gemini intents
    response_text, data = generate_response_fallback(intent, message, context, recommendations)
    state["response"] = response_text
    state["data"] = data
    return state


def purchase_processing_node(state: AgentState) -> AgentState:
    """
    Node to handle purchase acceptance and information extraction
    """
    intent = state["intent"]
    message = state["message"]
    context = state.get("context", {})
    
    if intent == "purchase_accept":
        product = context.get("recommended_product") or context.get("product")
        if product:
            response_text = (
                f"Excellent! I'll help you complete your purchase of the **{product['name']}**.\n\n"
                f"Please provide the following information in your next message:\n"
                f"1️⃣ Your full name\n"
                f"2️⃣ Shipping address\n"
                f"3️⃣ Payment method\n\n"
                f"Example format:\n"
                f"'Name: John Doe, Address: 123 Main St, City, State 12345, Payment: Credit Card'"
            )
            data = {
                "product": product,
                "recommended_product": product,
                "awaiting_purchase_info": True,
                "awaiting_purchase_decision": False,
                "multiple_recommendations": False
            }
        else:
            response_text = "Please select a product first before purchasing."
            data = {}
    
    elif intent == "purchase_decline":
        response_text = "No problem! Feel free to ask for another recommendation anytime. What else can I help you find today?"
        data = {
            "awaiting_purchase_decision": False,
            "multiple_recommendations": False
        }
    
    elif intent == "product_selection":
        recommendations = context.get("recommendations", [])
        if recommendations:
            # Extract option number using Gemini or fallback
            option_num = extract_option_number(message)
            
            if option_num and option_num <= len(recommendations):
                product = recommendations[option_num - 1]
                response_text = (
                    f"Great choice! You've selected the **{product['name']}**!\n\n"
                    f"💰 Price: ${product['price']:.2f}\n"
                    f"⭐ Rating: {product['rating']}/5.0\n\n"
                    f"Would you like to purchase this product?"
                )
                data = {
                    "product": product,
                    "recommended_product": product,
                    "awaiting_purchase_decision": True,
                    "multiple_recommendations": False
                }
            else:
                response_text = "I couldn't understand which option you'd like. Please say 'buy option 1', 'option 2', etc."
                data = {
                    "recommendations": recommendations,
                    "multiple_recommendations": True
                }
        else:
            response_text = "I don't have any recommendations to select from. Please ask for product recommendations first."
            data = {}
    
    else:
        response_text = ""
        data = {}
    
    state["response"] = response_text
    state["data"] = data
    return state


# ============================================
# Router Functions
# ============================================

def route_by_intent(state: AgentState) -> str:
    """Route to appropriate node based on intent"""
    intent = state["intent"]
    
    if intent == "recommendation":
        return "recommendation"
    elif intent in ["purchase_accept", "purchase_decline", "product_selection"]:
        return "purchase_processing"
    elif intent == "general":
        return "response_generation"
    else:
        return "response_generation"


# ============================================
# Build LangGraph
# ============================================

def create_agent_graph():
    """Create the LangGraph agent workflow"""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("intent_detection", intent_detection_node)
    workflow.add_node("recommendation", recommendation_node)
    workflow.add_node("response_generation", response_generation_node)
    workflow.add_node("purchase_processing", purchase_processing_node)
    
    # Set entry point
    workflow.set_entry_point("intent_detection")
    
    # Add conditional edges from intent_detection
    workflow.add_conditional_edges(
        "intent_detection",
        route_by_intent,
        {
            "recommendation": "recommendation",
            "purchase_processing": "purchase_processing",
            "response_generation": "response_generation"
        }
    )
    
    # Add edges
    workflow.add_edge("recommendation", "response_generation")
    workflow.add_edge("purchase_processing", END)
    workflow.add_edge("response_generation", END)
    
    return workflow.compile()


# Create the graph instance
agent_graph = create_agent_graph()


# ============================================
# Public API Functions (for main.py compatibility)
# ============================================

def detect_intent(message: str, context: Dict[str, Any] = None) -> str:
    """
    Detect the intent of the user's message.
    Returns: recommendation, purchase_accept, purchase_decline, purchase_info, general, product_selection
    """
    initial_state = {
        "message": message,
        "context": context or {},
        "intent": "",
        "recommendations": [],
        "response": "",
        "data": {},
        "chat_history": []
    }
    
    result = agent_graph.invoke(initial_state)
    return result["intent"]


def get_product_recommendations(user_query: str) -> List[Dict[str, Any]]:
    """
    AI Recommendation Agent - Returns multiple product recommendations based on query.
    Analyzes user preferences, budget, and use case to suggest best products.
    """
    initial_state = {
        "message": user_query,
        "context": {},
        "intent": "recommendation",
        "recommendations": [],
        "response": "",
        "data": {},
        "chat_history": []
    }
    
    result = agent_graph.invoke(initial_state)
    return result.get("recommendations", [products["p2"]])


def extract_purchase_info(message: str) -> Dict[str, str]:
    """
    Extract name, shipping address, and payment information from user message.
    Uses Gemini API for intelligent extraction.
    """
    if USE_GEMINI:
        system_prompt = """You are an information extraction expert.
        Extract the following from the user's message:
        - name: Full name
        - address: Complete shipping address
        - payment: Payment method
        
        Return ONLY in this format (one per line):
        name: <extracted name or NONE>
        address: <extracted address or NONE>
        payment: <extracted payment or NONE>
        """
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Extract information from: {message}")
            ]
            response = llm.invoke(messages)
            
            # Parse response
            info = {}
            for line in response.content.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    if value and value.upper() != "NONE":
                        info[key] = value
            
            return info
            
        except Exception as e:
            print(f"Gemini API error in info extraction: {e}")
    
    # Fallback regex extraction
    return extract_purchase_info_fallback(message)


def generate_response(intent: str, user_message: str, context: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
    """
    Generate appropriate response based on intent.
    Returns: (response_message, data_dict)
    """
    initial_state = {
        "message": user_message,
        "context": context or {},
        "intent": intent,
        "recommendations": [],
        "response": "",
        "data": {},
        "chat_history": []
    }
    
    result = agent_graph.invoke(initial_state)
    return result["response"], result["data"]


# ============================================
# Fallback Functions (when Gemini API unavailable)
# ============================================

def detect_intent_fallback(message: str, context: Dict[str, Any] = None) -> str:
    """Fallback intent detection using rules"""
    message_lower = message.lower()
    context = context or {}
    
    if context.get("multiple_recommendations") and any(word in message_lower for word in ["option", "number", "choose", "select", "1", "2", "3"]):
        return "product_selection"
    
    # Check if message contains product category keywords (new product request)
    product_categories = [
        "headphone", "headset", "earbud", "airpod", "phone", "smartphone", "mobile",
        "laptop", "notebook", "computer", "speaker", "watch", "smartwatch",
        "monitor", "display", "keyboard", "mouse", "tablet", "ipad"
    ]
    has_product_category = any(cat in message_lower for cat in product_categories)
    
    if context.get("awaiting_purchase_decision"):
        # If message mentions a product category, it's a NEW recommendation request, not accepting current one
        if has_product_category:
            return "recommendation"
        
        # Simple acceptance without mentioning other products
        if any(word in message_lower for word in ["yes", "accept", "ok", "sure", "i'll take it", "want it"]) and len(message_lower.split()) < 5:
            return "purchase_accept"
        elif "buy" in message_lower or "purchase" in message_lower:
            # Check if it's a simple "buy it" or mentions a different product
            if len(message_lower.split()) < 4 and not has_product_category:
                return "purchase_accept"
            elif has_product_category:
                return "recommendation"  # They want to buy a different product
        elif any(word in message_lower for word in ["no", "decline", "don't", "skip", "not interested"]):
            return "purchase_decline"
    
    if context.get("awaiting_purchase_info"):
        return "purchase_info"
    
    recommendation_keywords = ["recommend", "need", "looking for", "want", "buy", "suggest", "show", "find", "search"]
    if any(keyword in message_lower for keyword in recommendation_keywords):
        return "recommendation"
    
    return "general"


def extract_budget(query: str) -> Tuple[float, float]:
    """Extract budget range from user query"""
    query_lower = query.lower()
    
    under_match = re.search(r'(?:under|less than|below)\s*\$?\s*(\d+)', query_lower)
    if under_match:
        return 0, float(under_match.group(1))
    
    over_match = re.search(r'(?:over|more than|above)\s*\$?\s*(\d+)', query_lower)
    if over_match:
        return float(over_match.group(1)), 10000
    
    between_match = re.search(r'between\s*\$?\s*(\d+)\s*(?:and|to|-)\s*\$?\s*(\d+)', query_lower)
    if between_match:
        return float(between_match.group(1)), float(between_match.group(2))
    
    if any(word in query_lower for word in ["cheap", "affordable", "budget"]):
        return 0, 300
    elif any(word in query_lower for word in ["premium", "high-end", "expensive", "best"]):
        return 500, 10000
    
    return 0, 10000


def get_product_recommendations_fallback(user_query: str) -> List[Dict[str, Any]]:
    """Fallback product recommendation using rules"""
    user_query_lower = user_query.lower()
    recommendations = []
    
    min_budget, max_budget = extract_budget(user_query)
    
    matched_category = None
    
    if any(word in user_query_lower for word in ["headphone", "headset"]):
        matched_category = "headphones"
    elif any(word in user_query_lower for word in ["earbud", "airpod", "in-ear"]):
        matched_category = "earbuds"
    elif any(word in user_query_lower for word in ["phone", "smartphone", "mobile", "iphone"]):
        matched_category = "phone"
    elif any(word in user_query_lower for word in ["laptop", "notebook", "macbook"]):
        matched_category = "laptop"
    elif any(word in user_query_lower for word in ["speaker"]):
        matched_category = "speaker"
    elif any(word in user_query_lower for word in ["watch", "smartwatch", "fitness tracker"]):
        matched_category = "watch"
    elif any(word in user_query_lower for word in ["monitor", "display"]) and "phone" not in user_query_lower:
        matched_category = "monitor"
    elif any(word in user_query_lower for word in ["keyboard", "keys"]) and "phone" not in user_query_lower:
        matched_category = "keyboard"
    
    # Map products to categories
    category_map = {
        "phone": "p5",
        "laptop": "p7",
        "headphones": "p1",
        "earbuds": "p8",
        "speaker": "p6",
        "watch": "p2",
        "monitor": "p3",
        "keyboard": "p4"
    }
    
    if matched_category and matched_category in category_map:
        product_id = category_map[matched_category]
        product = products[product_id]
        if min_budget <= product["price"] <= max_budget:
            recommendations.append(product)
        else:
            recommendations.append(product)  # Include anyway if no budget match
    
    if not recommendations:
        recommendations = [p for p in products.values() 
                         if p.get("featured", False) and min_budget <= p["price"] <= max_budget]
    
    if not recommendations:
        recommendations = [products["p2"]]
    
    recommendations.sort(key=lambda x: x.get("rating", 0), reverse=True)
    return recommendations


def parse_recommendations_from_gemini(gemini_response: str, original_query: str) -> List[Dict[str, Any]]:
    """Parse Gemini's response and match to actual products"""
    # Extract category from Gemini response
    gemini_lower = gemini_response.lower()
    
    category_map = {
        "phone": "p5",
        "laptop": "p7",
        "headphones": "p1",
        "headphone": "p1",
        "earbuds": "p8",
        "earbud": "p8",
        "speaker": "p6",
        "watch": "p2",
        "monitor": "p3",
        "keyboard": "p4"
    }
    
    for category, product_id in category_map.items():
        if category in gemini_lower:
            return [products[product_id]]
    
    # Fallback
    return get_product_recommendations_fallback(original_query)


def extract_purchase_info_fallback(message: str) -> Dict[str, str]:
    """Fallback purchase info extraction using regex - more flexible patterns"""
    info = {}
    message_lower = message.lower()
    
    # Extract name - multiple patterns
    # Pattern 1: With label "Name: John Doe"
    name_match = re.search(r'(?:name|my name is|i am|i\'m)\s*[:=]\s*([A-Za-z\s]+?)(?:\s*[,]|\s+address|\s+ship|\s+payment|$)', message, re.IGNORECASE)
    if name_match:
        info["name"] = name_match.group(1).strip()
    # Pattern 2: Name at beginning before "Address:"
    elif re.search(r'address\s*:', message_lower):
        before_address = re.split(r'\s+address\s*:', message, flags=re.IGNORECASE)[0]
        # Clean up any trailing commas or whitespace
        potential_name = before_address.strip().rstrip(',').strip()
        # Check if it looks like a name (2-4 words, starts with capital letters)
        words = potential_name.split()
        if 2 <= len(words) <= 4 and words[0][0].isupper():
            info["name"] = potential_name
    # Pattern 3: Just a name (2-4 words with capital letters, no other keywords)
    elif "address" not in message_lower and "payment" not in message_lower and "card" not in message_lower:
        words = message.split()
        if 2 <= len(words) <= 4 and all(word[0].isupper() if word else False for word in words[:3]):
            info["name"] = message.strip()
    
    # Extract address - more flexible
    address_patterns = [
        r'(?:address|ship to|shipping)\s*[:=]\s*(.+?)(?:\s*[,]?\s*payment|\s*[,]?\s*pay\b|$)',
    ]
    for pattern in address_patterns:
        address_match = re.search(pattern, message, re.IGNORECASE)
        if address_match:
            addr = address_match.group(1).strip()
            # Remove trailing commas and clean up
            addr = addr.rstrip(',').strip()
            # Remove any "payment" or "card" at the end if captured
            addr = re.sub(r'\s*(payment|pay|card).*$', '', addr, flags=re.IGNORECASE).strip()
            if addr:
                info["address"] = addr
                break
    
    # Extract payment - more flexible
    payment_patterns = [
        r'(?:payment|pay with|paying with|pay|paying)\s*[:=]?\s*(.+?)$',
        r'\b(card|credit card|debit card|visa|mastercard|amex|paypal|cash)\b',
    ]
    for pattern in payment_patterns:
        payment_match = re.search(pattern, message, re.IGNORECASE)
        if payment_match:
            payment = payment_match.group(1).strip().rstrip(',').strip()
            if payment:
                info["payment"] = payment.capitalize()
                break
    
    return info


def generate_response_fallback(intent: str, user_message: str, context: Dict[str, Any], 
                               recommendations: List[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
    """Fallback response generation"""
    context = context or {}
    recommendations = recommendations or []
    
    if intent == "recommendation" and recommendations:
        if len(recommendations) == 1:
            product = recommendations[0]
            response = (
                f"🎯 Based on your needs, I recommend the **{product['name']}**!\n\n"
                f"💰 Price: ${product['price']:.2f}\n"
                f"⭐ Rating: {product['rating']}/5.0\n"
                f"📦 Stock: {product['stock']} units available\n\n"
                f"{product['description']}\n\n"
                f"Would you like to purchase this product?"
            )
            return response, {
                "product": product,
                "recommendations": recommendations,
                "awaiting_purchase_decision": True
            }
        else:
            response = f"🎯 I found {len(recommendations)} great option(s) for you:\n\n"
            for idx, product in enumerate(recommendations[:3], 1):
                response += (
                    f"**Option {idx}: {product['name']}**\n"
                    f"💰 ${product['price']:.2f} | ⭐ {product['rating']}/5.0 | 📦 {product['stock']} in stock\n"
                    f"{product['description']}\n\n"
                )
            response += "Reply with 'buy option 1' (or 2, 3...) to purchase, or ask me for more details!"
            
            return response, {
                "recommendations": recommendations,
                "multiple_recommendations": True
            }
    
    elif intent == "general":
        response = (
            "👋 Hello! I'm your AI shopping assistant. I can help you find the perfect product!\n\n"
            "Just tell me what you're looking for, for example:\n"
            "• 'I want to buy a phone'\n"
            "• 'Show me laptops under $1000'\n"
            "• 'Looking for wireless headphones'\n"
            "• 'Need a gaming monitor'\n\n"
            "What can I help you find today?"
        )
        return response, {}
    
    return "I'm here to help! What can I assist you with today?", {}


def extract_option_number(message: str) -> int:
    """Extract option number from message"""
    message_lower = message.lower()
    for num in ['1', '2', '3', 'one', 'two', 'three']:
        if num in message_lower:
            return {'1': 1, '2': 2, '3': 3, 'one': 1, 'two': 2, 'three': 3}.get(num)
    return None
