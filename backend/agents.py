import operator
import uuid
from datetime import datetime
from typing import Dict, Any, List, TypedDict, Annotated, Optional
from langgraph.graph import StateGraph, END
from database import create_complaint, get_order, get_user_orders, get_product_by_id
from utils import (
    detect_intent,
    get_product_recommendations,
    generate_response,
    extract_order_id,
    extract_purchase_info,
    extract_option_number,
    analyze_fraudulent_transaction_ocr,
    analyze_product_defect_image,
    analyze_damaged_shipping_box_image,
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
    image_url: Optional[str]
    image_type: Optional[str]
    user_id: Optional[str]
    session_id: Optional[str]

# ============================================
# Agent Logic Helpers
# ============================================

def _handle_recommendation_logic(state: AgentState) -> AgentState:
    """Helper for recommendation logic."""
    state["recommendations"] = get_product_recommendations(
        state["message"]
    )
    return state

def _handle_response_generation_logic(state: AgentState) -> AgentState:
    """Helper for generating responses."""
    response_text, data = generate_response(
        state["intent"],
        state["message"],
        state.get("context", {}),
        state.get("recommendations", []),
        state.get("chat_history", [])
    )
    state["response"] = response_text
    state["data"] = data
    return state

def _handle_purchase_processing(state: AgentState) -> AgentState:
    """Helper for purchase decision logic."""
    intent = state["intent"]
    context = state.get("context", {})
    response_text, data = "", {}

    if intent == "purchase_accept":
        product = context.get("recommended_product")
        if product:
            response_text = f"Excellent! To complete your purchase of the **{product['name']}**, please provide your full name, shipping address, and payment method."
            data = {"product": product, "awaiting_purchase_info": True, "awaiting_purchase_decision": False}
        else:
            response_text = "Please select a product first."

    elif intent == "purchase_decline":
        response_text = "No problem! What else can I help you find?"
        data = {"awaiting_purchase_decision": False}

    elif intent == "product_selection":
        recommendations = context.get("recommendations", [])
        option_num = extract_option_number(state["message"])
        if recommendations and option_num and 0 < option_num <= len(recommendations):
            product = recommendations[option_num - 1]
            response_text = f"Great choice! You've selected the **{product['name']}**. Would you like to purchase this?"
            data = {"product": product, "recommended_product": product, "awaiting_purchase_decision": True}
        else:
            response_text = "I couldn't understand that. Please say 'option 1', 'option 2', etc."

    state["response"] = response_text
    state["data"] = data
    return state

def _handle_purchase_info(state: AgentState) -> AgentState:
    """Helper for processing purchase information."""
    product = state.get("context", {}).get("recommended_product")
    if not product:
        state["response"] = "I'm sorry, I've lost track of the product. Could you select it again?"
        state["data"] = {"awaiting_purchase_info": False}
        return state

    purchase_info = extract_purchase_info(state["message"])
    missing = [field for field in ["name", "address", "payment"] if not purchase_info.get(field)]

    if missing:
        state["response"] = f"I'm missing some details. Please provide your {', '.join(missing)}."
        state["data"] = {"awaiting_purchase_info": True}
    else:
        order_id = str(uuid.uuid4())[:8].upper()
        order_details = {
            "order_id": order_id,
            "user_id": state.get("user_id"),
            "items": {product["id"]: 1},
            "total_amount": product["price"],
            "name": purchase_info["name"],
            "address": purchase_info["address"],
            "payment": purchase_info["payment"],
            "order_date": datetime.now().isoformat(),
            "status": "confirmed"
        }
        state["response"] = (
            f"🎉 Purchase successful! Your order for the **{product['name']}** is confirmed.\n"
            f"**Order Number: {order_id}**\n\nThank you for your purchase!"
        )
        state["data"] = {"order_details": order_details, "purchase_complete": True, "awaiting_purchase_info": False}
        state["intent"] = "purchase_complete"
    return state

def _handle_order_shipping_status(state: AgentState) -> AgentState:
    """Helper for order status logic."""
    message = state["message"]
    user_id = state.get("user_id")
    
    # Try to extract order ID from message
    order_id = extract_order_id(message)
    
    response_text = ""
    data = {}
    
    if order_id:
        order = get_order(order_id)
        if order:
            product_name = order.get("product_name")
            # If product_name is missing, try to resolve from items
            if not product_name and order.get("items"):
                try:
                    # Get the first product ID from the items dict
                    first_pid = list(order["items"].keys())[0]
                    product = get_product_by_id(first_pid)
                    if product:
                        product_name = product["name"]
                except Exception:
                    pass
            
            product_name = product_name or "Unknown Product"

            order_date_str = order.get("order_date")
            formatted_date = "Unknown Date"
            if order_date_str:
                try:
                    formatted_date = datetime.fromisoformat(order_date_str).strftime("%B %d, %Y")
                except ValueError:
                    formatted_date = order_date_str

            response_text = (
                f"I found your order **{order_id}**.\n"
                f"**Status:** {order['status']}\n"
                f"**Product:** {product_name}\n"
                f"**Date:** {formatted_date}\n"
            )
            data = {"order": order, "order_found": True}
        else:
            response_text = f"I couldn't find an order with ID **{order_id}**. Please check the number and try again."
            data = {"order_found": False}
    elif user_id:
        # If no specific ID, list recent orders for the user
        orders = get_user_orders(user_id)
        if orders:
            # Sort by date desc
            orders.sort(key=lambda x: x.get('order_date', ''), reverse=True)
            recent_order = orders[0]
            
            product_name = recent_order.get("product_name")
            if not product_name and recent_order.get("items"):
                try:
                    first_pid = list(recent_order["items"].keys())[0]
                    product = get_product_by_id(first_pid)
                    if product:
                        product_name = product["name"]
                except Exception:
                    pass
            product_name = product_name or "Unknown Product"

            order_date_str = recent_order.get("order_date")
            formatted_date = "Unknown Date"
            if order_date_str:
                try:
                    formatted_date = datetime.fromisoformat(order_date_str).strftime("%B %d, %Y")
                except ValueError:
                    formatted_date = order_date_str

            response_text = (
                f"Here is the status of your most recent order **{recent_order['order_id']}**:\n"
                f"**Status:** {recent_order['status']}\n"
                f"**Product:** {product_name}\n"
                f"**Date:** {formatted_date}\n\n"
                f"You can ask me about other orders by providing the Order ID."
            )
            data = {"recent_order": recent_order, "order_found": True}
        else:
            response_text = "I don't see any recent orders for your account. If you have an Order ID, please provide it."
            data = {"order_found": False}
    else:
        response_text = "I can help you check your order status. Please provide your **Order ID**."
        data = {"awaiting_order_id": True}
        
    state["response"] = response_text
    state["data"] = data
    return state

def _handle_fraudulent_transaction(state: AgentState) -> AgentState:
    """Helper for fraud transaction logic."""
    image_url = state.get("image_url")
    message = state["message"]
    
    if not image_url:
        state["response"] = "I'd be happy to help with your fraudulent transaction report. Please upload an image or OCR of your credit card statement showing the transaction so I can analyze it and determine the best resolution (Refund, Decline, or Escalate to a human agent)."
        state["data"] = {"awaiting_image": True, "issue_type": "fraudulent_transaction"}
        return state
    
    # Analyze the OCR image
    analysis_result = analyze_fraudulent_transaction_ocr(image_url, message)
    decision = analysis_result.get("decision", "escalate")
    reason = analysis_result.get("reason", "Unable to determine")
    transaction_amount = analysis_result.get("transaction_amount", "Unknown")
    confidence = analysis_result.get("confidence", "low")
    fraud_indicators = analysis_result.get("fraud_indicators", [])
    
    # Generate appropriate response based on decision
    if decision == "refund":
        case_id = str(uuid.uuid4())[:8].upper()
        create_complaint({
            "id": case_id,
            "user_id": state.get("user_id"),
            "session_id": state.get("session_id"),
            "issue_type": "fraudulent_transaction",
            "description": message,
            "status": "resolved",
            "created_at": datetime.now().isoformat(),
            "resolution": f"Refund Approved: {reason}"
        })
        state["response"] = (
            f"I've analyzed the transaction details from your credit card statement. Based on my analysis "
            f"(confidence: {confidence}), I've determined that a **refund** is the appropriate action.\n\n"
            f"**Transaction Amount:** {transaction_amount}\n"
            f"**Reason:** {reason}\n"
            f"{'**Fraud Indicators Found:** ' + ', '.join(fraud_indicators) if fraud_indicators else ''}\n\n"
            f"Your refund will be processed within 5-7 business days, and the fraudulent charge will be removed from your account. "
            f"We recommend reviewing your account security settings. Is there anything else I can help you with?"
        )
        state["data"] = {
            "action": "refund",
            "issue_type": "fraudulent_transaction",
            "analysis": analysis_result,
            "case_id": case_id,
            "resolved": True
        }
    elif decision == "decline":
        case_id = str(uuid.uuid4())[:8].upper()
        create_complaint({
            "id": case_id,
            "user_id": state.get("user_id"),
            "session_id": state.get("session_id"),
            "issue_type": "fraudulent_transaction",
            "description": message,
            "status": "resolved",
            "created_at": datetime.now().isoformat(),
            "resolution": f"Decline: {reason}"
        })
        state["response"] = (
            f"I've analyzed the transaction details from your credit card statement. Based on my analysis "
            f"(confidence: {confidence}), this appears to be a **legitimate transaction**.\n\n"
            f"**Transaction Amount:** {transaction_amount}\n"
            f"**Reason:** {reason}\n\n"
            f"If you still believe this is fraudulent, please contact our support team for further review. "
            f"Is there anything else I can help you with?"
        )
        state["data"] = {
            "action": "decline",
            "issue_type": "fraudulent_transaction",
            "analysis": analysis_result,
            "case_id": case_id,
            "resolved": True
        }
    else:  # escalate
        case_id = str(uuid.uuid4())[:8].upper()
        create_complaint({
            "id": case_id,
            "user_id": state.get("user_id"),
            "session_id": state.get("session_id"),
            "issue_type": "fraudulent_transaction",
            "description": message,
            "status": "open",
            "created_at": datetime.now().isoformat(),
            "resolution": None
        })
        state["response"] = (
            f"I've reviewed your fraudulent transaction report. This case requires additional review by our fraud investigation team.\n\n"
            f"**Transaction Amount:** {transaction_amount}\n"
            f"**Reason:** {reason}\n\n"
            f"A fraud specialist will contact you within 24 hours to investigate this matter further. "
            f"Your case reference number is: {case_id}. "
            f"In the meantime, we recommend monitoring your account and contacting your bank if needed. "
            f"Is there anything else I can help you with?"
        )
        state["data"] = {
            "action": "escalate",
            "issue_type": "fraudulent_transaction",
            "analysis": analysis_result,
            "case_id": case_id,
            "resolved": False
        }
    
    return state

def _handle_product_defect(state: AgentState) -> AgentState:
    """Helper for product defect logic."""
    image_url = state.get("image_url")
    message = state["message"]
    
    if not image_url:
        state["response"] = "I'd be happy to help with your product defect issue. Please upload an image of the defective product so I can analyze it and determine the best resolution (Refund, Replace, or Escalate to a human agent)."
        state["data"] = {"awaiting_image": True, "issue_type": "product_defect"}
        return state
    
    # Analyze the image
    analysis_result = analyze_product_defect_image(image_url, message)
    decision = analysis_result.get("decision", "escalate")
    reason = analysis_result.get("reason", "Unable to determine")
    severity = analysis_result.get("severity", "unknown")
    defect_type = analysis_result.get("defect_type", "Unknown defect")
    
    # Generate appropriate response based on decision
    if decision == "refund":
        case_id = str(uuid.uuid4())[:8].upper()
        create_complaint({
            "id": case_id,
            "user_id": state.get("user_id"),
            "session_id": state.get("session_id"),
            "issue_type": "product_defect",
            "description": message,
            "status": "resolved",
            "created_at": datetime.now().isoformat(),
            "resolution": f"Refund Approved: {reason}"
        })
        state["response"] = (
            f"I've analyzed the image of your defective product. Based on the {severity} defect ({defect_type}), "
            f"I've determined that a **refund** is the appropriate action.\n\n"
            f"**Reason:** {reason}\n\n"
            f"Your refund will be processed within 5-7 business days. Is there anything else I can help you with?"
        )
        state["data"] = {
            "action": "refund",
            "issue_type": "product_defect",
            "analysis": analysis_result,
            "case_id": case_id,
            "resolved": True
        }
    elif decision == "replace":
        case_id = str(uuid.uuid4())[:8].upper()
        create_complaint({
            "id": case_id,
            "user_id": state.get("user_id"),
            "session_id": state.get("session_id"),
            "issue_type": "product_defect",
            "description": message,
            "status": "resolved",
            "created_at": datetime.now().isoformat(),
            "resolution": f"Replacement Approved: {reason}"
        })
        state["response"] = (
            f"I've analyzed the image of your defective product. Based on the {severity} defect ({defect_type}), "
            f"I've determined that a **replacement** is the appropriate action.\n\n"
            f"**Reason:** {reason}\n\n"
            f"A replacement product will be shipped to you within 2-3 business days. You'll receive a tracking number via email. "
            f"Please return the defective item using the prepaid return label that will be included. Is there anything else I can help you with?"
        )
        state["data"] = {
            "action": "replace",
            "issue_type": "product_defect",
            "analysis": analysis_result,
            "case_id": case_id,
            "resolved": True
        }
    else:  # escalate
        case_id = str(uuid.uuid4())[:8].upper()
        create_complaint({
            "id": case_id,
            "user_id": state.get("user_id"),
            "session_id": state.get("session_id"),
            "issue_type": "product_defect",
            "description": message,
            "status": "open",
            "created_at": datetime.now().isoformat(),
            "resolution": None
        })
        state["response"] = (
            f"I've reviewed your product defect report. This case requires additional review by our human support team.\n\n"
            f"**Reason:** {reason}\n\n"
            f"A support agent will contact you within 24 hours to resolve this issue. "
            f"Your case reference number is: {case_id}. Is there anything else I can help you with?"
        )
        state["data"] = {
            "action": "escalate",
            "issue_type": "product_defect",
            "analysis": analysis_result,
            "case_id": case_id,
            "resolved": False
        }
    
    return state

def _handle_damaged_shipping_box(state: AgentState) -> AgentState:
    """Helper for damaged shipping box logic."""
    image_url = state.get("image_url")
    message = state["message"]
    
    if not image_url:
        state["response"] = "I'd be happy to help with your damaged shipping box issue. Please upload an image of the damaged box so I can analyze it and determine the best resolution (Refund, Replace, or Escalate to a human agent)."
        state["data"] = {"awaiting_image": True, "issue_type": "damaged_shipping_box"}
        return state
    
    # Analyze the image
    analysis_result = analyze_damaged_shipping_box_image(image_url, message)
    decision = analysis_result.get("decision", "escalate")
    reason = analysis_result.get("reason", "Unable to determine")
    box_damage_severity = analysis_result.get("box_damage_severity", "unknown")
    product_condition = analysis_result.get("product_condition", "unknown")
    
    # Generate appropriate response based on decision
    if decision == "refund":
        case_id = str(uuid.uuid4())[:8].upper()
        create_complaint({
            "id": case_id,
            "user_id": state.get("user_id"),
            "session_id": state.get("session_id"),
            "issue_type": "damaged_shipping_box",
            "description": message,
            "status": "resolved",
            "created_at": datetime.now().isoformat(),
            "resolution": f"Refund Approved: {reason}"
        })
        state["response"] = (
            f"I've analyzed the image of your damaged shipping box. Based on the {box_damage_severity} box damage "
            f"and the product condition ({product_condition}), I've determined that a **refund** is the appropriate action.\n\n"
            f"**Reason:** {reason}\n\n"
            f"Your refund will be processed within 5-7 business days. Is there anything else I can help you with?"
        )
        state["data"] = {
            "action": "refund",
            "issue_type": "damaged_shipping_box",
            "analysis": analysis_result,
            "case_id": case_id,
            "resolved": True
        }
    elif decision == "replace":
        case_id = str(uuid.uuid4())[:8].upper()
        create_complaint({
            "id": case_id,
            "user_id": state.get("user_id"),
            "session_id": state.get("session_id"),
            "issue_type": "damaged_shipping_box",
            "description": message,
            "status": "resolved",
            "created_at": datetime.now().isoformat(),
            "resolution": f"Replacement Approved: {reason}"
        })
        state["response"] = (
            f"I've analyzed the image of your damaged shipping box. Based on the {box_damage_severity} box damage "
            f"and the product condition ({product_condition}), I've determined that a **replacement** is the appropriate action.\n\n"
            f"**Reason:** {reason}\n\n"
            f"A replacement product will be shipped to you within 2-3 business days. You'll receive a tracking number via email. "
            f"Please return the damaged item using the prepaid return label that will be included. Is there anything else I can help you with?"
        )
        state["data"] = {
            "action": "replace",
            "issue_type": "damaged_shipping_box",
            "analysis": analysis_result,
            "case_id": case_id,
            "resolved": True
        }
    else:  # escalate
        case_id = str(uuid.uuid4())[:8].upper()
        create_complaint({
            "id": case_id,
            "user_id": state.get("user_id"),
            "session_id": state.get("session_id"),
            "issue_type": "damaged_shipping_box",
            "description": message,
            "status": "open",
            "created_at": datetime.now().isoformat(),
            "resolution": None
        })
        state["response"] = (
            f"I've reviewed your damaged shipping box report. This case requires additional review by our human support team.\n\n"
            f"**Reason:** {reason}\n\n"
            f"A support agent will contact you within 24 hours to resolve this issue. "
            f"Your case reference number is: {case_id}. Is there anything else I can help you with?"
        )
        state["data"] = {
            "action": "escalate",
            "issue_type": "damaged_shipping_box",
            "analysis": analysis_result,
            "case_id": case_id,
            "resolved": False
        }
    
    return state

# ============================================
# Agent Nodes
# ============================================

def intent_detection_node(state: AgentState) -> AgentState:
    """Node to detect user intent."""
    state["intent"] = detect_intent(state["message"], state.get("context", {}), state.get("chat_history", []))
    return state

def recommendation_agent(state: AgentState) -> AgentState:
    """Consolidated agent for recommendations and general conversation."""
    intent = state.get("intent", "")
    
    if "recommendation" in intent:
        state = _handle_recommendation_logic(state)
        state = _handle_response_generation_logic(state)
    else:
        # Generic fallback or other non-transactional intents
        state = _handle_response_generation_logic(state)
    
    return state

def purchase_agent(state: AgentState) -> AgentState:
    """Consolidated agent for purchase, shipping, and order status."""
    intent = state.get("intent", "")
    
    if any(keyword in intent for keyword in ["purchase_accept", "purchase_decline", "product_selection"]):
        state = _handle_purchase_processing(state)
    elif "purchase_info" in intent:
        state = _handle_purchase_info(state)
    elif "order_shipping_status" in intent:
        state = _handle_order_shipping_status(state)
    else:
        # Fallback if wrongly routed, or maybe handle generic purchase questions
        state = _handle_response_generation_logic(state)
        
    return state

def fraud_detection_agent(state: AgentState) -> AgentState:
    """Consolidated agent for fraud detection, defects, and damaged goods."""
    intent = state.get("intent", "")
    
    if "fraudulent_transaction" in intent:
        state = _handle_fraudulent_transaction(state)
    elif "product_defect" in intent:
        state = _handle_product_defect(state)
    elif "damaged_shipping_box" in intent:
        state = _handle_damaged_shipping_box(state)
    else:
        # Fallback
        state = _handle_response_generation_logic(state)
        
    return state

# ============================================
# Graph Router
# ============================================

def route_by_intent(state: AgentState) -> str:
    """Route to the appropriate agent based on intent."""
    intent = state["intent"]
    
    # Recommendation / General
    if "recommendation" in intent:
        return "recommendation_agent"
        
    # Purchase Related
    if any(keyword in intent for keyword in ["purchase_accept", "purchase_decline", "product_selection"]):
        return "purchase_agent"
    if "purchase_info" in intent:
        return "purchase_agent"
    if "order_shipping_status" in intent:
        return "purchase_agent"
        
    # Fraud / Claims Related
    if "fraudulent_transaction" in intent:
        return "fraud_detection_agent"
    if "product_defect" in intent:
        return "fraud_detection_agent"
    if "damaged_shipping_box" in intent:
        return "fraud_detection_agent"
        
    # Default to recommendation agent (which handles generic response generation)
    return "recommendation_agent"

# ============================================
# Build LangGraph
# ============================================

def create_agent_graph():
    """Create the LangGraph agent workflow with 3 consolidated agents."""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("intent_detection", intent_detection_node)
    workflow.add_node("recommendation_agent", recommendation_agent)
    workflow.add_node("purchase_agent", purchase_agent)
    workflow.add_node("fraud_detection_agent", fraud_detection_agent)

    # Set entry point
    workflow.set_entry_point("intent_detection")
    
    # Conditional edges from intent detection
    workflow.add_conditional_edges(
        "intent_detection",
        route_by_intent,
        {
            "recommendation_agent": "recommendation_agent",
            "purchase_agent": "purchase_agent",
            "fraud_detection_agent": "fraud_detection_agent",
        },
    )
    
    # Edges back to END
    workflow.add_edge("recommendation_agent", END)
    workflow.add_edge("purchase_agent", END)
    workflow.add_edge("fraud_detection_agent", END)
    
    return workflow.compile()

# ============================================
# Main Execution Block
# ============================================

def run_agent(message: str, context: Dict[str, Any], chat_history: List, agent_graph, image_url: Optional[str] = None, image_type: Optional[str] = None, user_id: Optional[str] = None, session_id: Optional[str] = None) -> AgentState:
    """Single entry point to run the agent for one turn."""
    initial_state = {
        "message": message,
        "context": context or {},
        "chat_history": chat_history,
        "image_url": image_url,
        "image_type": image_type,
        "user_id": user_id,
        "session_id": session_id
    }
    return agent_graph.invoke(initial_state)

if __name__ == "__main__":
    agent_graph = create_agent_graph()
    print("Chatbot initialized. Type 'quit' to exit.")
    chat_context = {}
    chat_history = []

    while True:
        user_input = input("You: ")
        if user_input.lower() == 'quit':
            break

        final_state = run_agent(user_input, chat_context, chat_history, agent_graph)
        print(f"Bot: {final_state['response']}")

        chat_context.update(final_state.get('data', {}))
        chat_history.append({"role": "user", "content": user_input})
        chat_history.append({"role": "assistant", "content": final_state['response']})
