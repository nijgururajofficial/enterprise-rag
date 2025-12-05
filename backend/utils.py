import os
from typing import Dict, Any, Tuple, List
from database import search_products_vector
from dotenv import load_dotenv
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from prompts import (
    get_intent_detection_prompt, 
    get_product_extraction_prompt,
    get_single_recommendation_prompt,
    get_multiple_recommendations_prompt,
    get_general_chat_prompt,
    get_purchase_info_extraction_prompt,
    get_order_id_extraction_prompt,
    get_fraud_analysis_prompt,
    get_product_defect_analysis_prompt,
    get_damaged_box_analysis_prompt
)


# Load environment variables
load_dotenv()

# --- LLM Configuration ---
# USE_GEMINI = True
# llm = None
# if USE_GEMINI:
#     try:
#         llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=os.getenv("GEMINI_API_KEY"))
#         print("Gemini initialized successfully")
#     except Exception as e:
#         print(f"Error initializing Gemini: {e}")
#         llm = None

USE_OPENAI = True
llm = None

if USE_OPENAI:
    try:
        llm = ChatOpenAI(
            model="gpt-4o-mini", 
            api_key=os.getenv("OPENAI_API_KEY")
        )
        # Vision model for image analysis
        vision_llm = ChatOpenAI(
            model="gpt-4o",  # GPT-4o supports vision
            api_key=os.getenv("OPENAI_API_KEY")
        )
        print("OpenAI LLM initialized successfully")
    except Exception as e:
        print(f"Error initializing OpenAI LLM: {e}")
        llm = None
        vision_llm = None
else:
    vision_llm = None

# ============================================
# LLM-Powered Utility Functions
# ============================================

# --- MODIFICATION: Accept and use chat_history in detect_intent ---
def detect_intent(message: str, context: Dict[str, Any] = None, chat_history: List = None) -> str:
    """Detects user intent using an LLM."""
    context = context or {}
    chat_history = chat_history or []

    if context.get("awaiting_purchase_info"):
        return "purchase_info"

    prompt = get_intent_detection_prompt()
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({
        "message": message,
        "awaiting_purchase_decision": context.get("awaiting_purchase_decision", False),
        "chat_history": "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
    })


def get_product_recommendations(user_query: str) -> List[Dict[str, Any]]:
    """Generates product recommendations by extracting criteria and filtering the database."""

    class ProductQuery(BaseModel):
        category: str = Field(
            description="The category of the product. Valid options are 'laptops', 'phones', 'monitors'."
        )
        min_price: float = Field(
            default=0, description="The minimum budget for the product."
        )
        max_price: float = Field(
            default=10000, description="The maximum budget for the product."
        )
        min_rating: float = Field(
            default=0.0, description="Minimum acceptable product rating (0.0 - 5.0)."
        )
        features: List[str] = Field(
            default_factory=list,
            description="A list of key features the user is interested in."
        )

    parser = JsonOutputParser(pydantic_object=ProductQuery)
    prompt = get_product_extraction_prompt()
    chain = prompt | llm | parser

    try:
        # Extract structured query using LLM
        extracted_query = chain.invoke({
            "query": user_query,
            "format_instructions": parser.get_format_instructions()
        })

        # Convert to dict and fill defaults
        extracted_query = extracted_query.dict() if hasattr(extracted_query, "dict") else extracted_query
        extracted_query.setdefault("min_rating", 0.0)
        extracted_query.setdefault("features", [])

        # --- STRICT FILTERING LOGIC ---
        # Using Vector Search for better semantic matching and filtering
        filter_criteria = {
            "category": extracted_query["category"],
            "min_price": extracted_query["min_price"],
            "max_price": extracted_query["max_price"],
            "min_rating": extracted_query["min_rating"]
        }
        
        # Construct a search query from features and category
        search_text = f"{extracted_query['category']} {' '.join(extracted_query['features'])}"
        
        filtered_products = search_products_vector(search_text, k=10, filter_criteria=filter_criteria)

        # Sort by rating (high to low)
        filtered_products.sort(key=lambda x: x.get("rating", 0), reverse=True)
        return filtered_products

    except Exception as e:
        print(f"Error in LLM-based recommendation: {e}")
        return []

# --- MODIFICATION: Accept and use chat_history in generate_response ---
def generate_response(intent: str, user_message: str, context: Dict[str, Any], recommendations: List[Dict[str, Any]] = None, chat_history: List = None) -> Tuple[str, Dict[str, Any]]:
    """Generates a natural language response based on the agent's state."""
    recommendations = recommendations or []
    chat_history = chat_history or []

    if intent == "recommendation":
        if not recommendations:
            return "I'm sorry, I couldn't find any products that match your criteria. Would you like to try a different search?", {}

        if len(recommendations) == 1:
            product = recommendations[0]
            prompt = get_single_recommendation_prompt()
            chain = prompt | llm | StrOutputParser()
            response = chain.invoke({
                "name": product["name"], "price": f"{product['price']:.2f}",
                "rating": product["rating"], "description": product["description"]
            })
            return response, {"product": product, "recommended_product": product, "awaiting_purchase_decision": True}
        else:
            options = "".join([f"Option {i+1}: {p['name']} (${p['price']:.2f})\n" for i, p in enumerate(recommendations[:3])])
            prompt = get_multiple_recommendations_prompt()
            chain = prompt | llm | StrOutputParser()
            response = chain.invoke({"options": options})
            return response, {"recommendations": recommendations, "multiple_recommendations": True}

    if intent == "product_selection":
        # Handle product selection from previous recommendations
        prev_recommendations = context.get("recommendations", [])
        option_num = extract_option_number(user_message)
        
        if prev_recommendations and option_num and 0 < option_num <= len(prev_recommendations):
            product = prev_recommendations[option_num - 1]
            # --- MODIFICATION: Prepare for purchase instead of declining ---
            return (
                f"Great choice! The **{product['name']}** is an excellent product. "
                f"Would you like to proceed with purchasing this item?",
                {"product": product, "recommended_product": product, "awaiting_purchase_decision": True}
            )
        else:
            return "I'm not sure which option you selected. Please say 'Option 1', 'Option 2', etc.", {}

    prompt = get_general_chat_prompt()
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({
        "user_message": user_message,
        "chat_history": "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
    })
    return response, {}


def extract_purchase_info(message: str) -> Dict[str, str]:
    """Extracts purchase information from a message using an LLM."""
    class PurchaseInfo(BaseModel):
        name: str = Field(description="The full name of the customer.")
        address: str = Field(description="The complete shipping address.")
        payment: str = Field(description="The payment method (e.g., 'Credit Card', 'PayPal').")

    parser = JsonOutputParser(pydantic_object=PurchaseInfo)
    prompt = get_purchase_info_extraction_prompt()
    chain = prompt | llm | parser
    try:
        return chain.invoke({"message": message, "format_instructions": parser.get_format_instructions()})
    except Exception as e:
        print(f"Error in LLM-based info extraction: {e}")
        return {}


def extract_order_id(message: str) -> str:
    """Extracts an order ID from the user's message."""
    prompt = get_order_id_extraction_prompt()
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({"message": message}).strip()
    return None if result == "None" else result

# ============================================
# Helper Functions
# ============================================

def extract_option_number(message: str) -> int:
    """Extracts a number from a user's selection message."""
    message_lower = message.lower()
    for num_str, num_val in [('1', 1), ('2', 2), ('3', 3), ('one', 1), ('two', 2), ('three', 3)]:
        if num_str in message_lower:
            return num_val
    # Fallback to simple digit extraction
    import re
    digits = re.findall(r'\d+', message)
    if digits:
        return int(digits[0])
    return None

# ============================================
# Image Analysis Functions
# ============================================


def analyze_fraudulent_transaction_ocr(image_url: str, user_message: str) -> Dict[str, Any]:
    """
    Analyzes an OCR image of a credit card statement and determines the appropriate action:
    Refund, Decline, or Escalate to Human-Agent.
    """
    if not vision_llm:
        return {"decision": "escalate", "reason": "Vision model not available"}
    
    prompt = get_fraud_analysis_prompt()
    
    try:
        if image_url.startswith("data:image"):
            image_content = image_url
        elif image_url.startswith("http"):
            image_content = image_url
        else:
            image_content = f"data:image/jpeg;base64,{image_url}"
        
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt.format(user_message=user_message)},
                {"type": "image_url", "image_url": {"url": image_content}}
            ]
        )
        
        parser = JsonOutputParser()
        chain = vision_llm | parser
        result = chain.invoke([message])
        return result
    except Exception as e:
        print(f"Error analyzing fraudulent transaction OCR: {e}")
        return {"decision": "escalate", "reason": f"Error analyzing image: {str(e)}"}

def analyze_product_defect_image(image_url: str, user_message: str) -> Dict[str, Any]:
    """
    Analyzes an image of a product defect and determines the appropriate action:
    Refund, Replace, or Escalate to Human-Agent.
    """
    if not vision_llm:
        return {"decision": "escalate", "reason": "Vision model not available"}
    
    prompt = get_product_defect_analysis_prompt()
    
    try:
        # Handle base64 or URL images
        if image_url.startswith("data:image"):
            # Base64 encoded image
            image_content = image_url
        elif image_url.startswith("http"):
            # URL - we'll pass it as is
            image_content = image_url
        else:
            # Assume base64 without data URI prefix
            image_content = f"data:image/jpeg;base64,{image_url}"
        
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt.format(user_message=user_message)},
                {"type": "image_url", "image_url": {"url": image_content}}
            ]
        )
        
        parser = JsonOutputParser()
        chain = vision_llm | parser
        result = chain.invoke([message])
        return result
    except Exception as e:
        print(f"Error analyzing product defect image: {e}")
        return {"decision": "escalate", "reason": f"Error analyzing image: {str(e)}"}

def analyze_damaged_shipping_box_image(image_url: str, user_message: str) -> Dict[str, Any]:
    """
    Analyzes an image of a damaged shipping box and determines the appropriate action:
    Refund, Replace, or Escalate to Human-Agent.
    """
    if not vision_llm:
        return {"decision": "escalate", "reason": "Vision model not available"}
    
    prompt = get_damaged_box_analysis_prompt()
    
    try:
        if image_url.startswith("data:image"):
            image_content = image_url
        elif image_url.startswith("http"):
            image_content = image_url
        else:
            image_content = f"data:image/jpeg;base64,{image_url}"
        
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt.format(user_message=user_message)},
                {"type": "image_url", "image_url": {"url": image_content}}
            ]
        )
        
        parser = JsonOutputParser()
        chain = vision_llm | parser
        result = chain.invoke([message])
        return result
    except Exception as e:
        print(f"Error analyzing damaged shipping box image: {e}")
        return {"decision": "escalate", "reason": f"Error analyzing image: {str(e)}"}
