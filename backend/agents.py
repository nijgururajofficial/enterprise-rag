import operator
import uuid
from datetime import datetime
from typing import Dict, Any, List, TypedDict, Annotated, Optional
from langgraph.graph import StateGraph, END
from utils import (
    detect_intent,
    get_product_recommendations,
    generate_response,
    extract_purchase_info,
    extract_option_number,
    analyze_product_defect_image,
    analyze_damaged_shipping_box_image,
    analyze_fraudulent_transaction_ocr,
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

# ============================================
# Agent Nodes
# ============================================

def intent_detection_node(state: AgentState) -> AgentState:
    """Node to detect user intent."""
    # --- MODIFICATION: Pass chat_history to the intent detection function ---
    state["intent"] = detect_intent(state["message"], state.get("context", {}), state.get("chat_history", []))
    return state

def recommendation_node(state: AgentState) -> AgentState:
    """Node to generate product recommendations."""
    state["recommendations"] = get_product_recommendations(
        state["message"]
    )
    return state

def response_generation_node(state: AgentState) -> AgentState:
    """Node to generate a response for recommendations or general queries."""
    # --- MODIFICATION: Pass chat_history to the response generation function ---
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

def purchase_processing_node(state: AgentState) -> AgentState:
    """Node to handle purchase decisions."""
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

def purchase_info_node(state: AgentState) -> AgentState:
    """Node to process collected purchase information."""
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
            "order_id": order_id, "product_name": product["name"], **purchase_info,
            "order_date": datetime.now().isoformat(), "status": "confirmed"
        }
        state["response"] = (
            f"🎉 Purchase successful! Your order for the **{product['name']}** is confirmed.\n"
            f"**Order Number: {order_id}**\n\nThank you for your purchase!"
        )
        state["data"] = {"order_details": order_details, "purchase_complete": True, "awaiting_purchase_info": False}
        state["intent"] = "purchase_complete"
    return state

def product_defect_node(state: AgentState) -> AgentState:
    """Node to handle product defect reports with image analysis."""
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
            "resolved": True
        }
    elif decision == "replace":
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
            "resolved": True
        }
    else:  # escalate
        state["response"] = (
            f"I've reviewed your product defect report. This case requires additional review by our human support team.\n\n"
            f"**Reason:** {reason}\n\n"
            f"A support agent will contact you within 24 hours to resolve this issue. "
            f"Your case reference number is: {str(uuid.uuid4())[:8].upper()}. Is there anything else I can help you with?"
        )
        state["data"] = {
            "action": "escalate",
            "issue_type": "product_defect",
            "analysis": analysis_result,
            "case_id": str(uuid.uuid4())[:8].upper(),
            "resolved": False
        }
    
    return state

def damaged_shipping_box_node(state: AgentState) -> AgentState:
    """Node to handle damaged shipping box reports with image analysis."""
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
            "resolved": True
        }
    elif decision == "replace":
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
            "resolved": True
        }
    else:  # escalate
        state["response"] = (
            f"I've reviewed your damaged shipping box report. This case requires additional review by our human support team.\n\n"
            f"**Reason:** {reason}\n\n"
            f"A support agent will contact you within 24 hours to resolve this issue. "
            f"Your case reference number is: {str(uuid.uuid4())[:8].upper()}. Is there anything else I can help you with?"
        )
        state["data"] = {
            "action": "escalate",
            "issue_type": "damaged_shipping_box",
            "analysis": analysis_result,
            "case_id": str(uuid.uuid4())[:8].upper(),
            "resolved": False
        }
    
    return state

def fraudulent_transaction_node(state: AgentState) -> AgentState:
    """Node to handle fraudulent transaction reports with OCR image analysis."""
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
            "resolved": True
        }
    elif decision == "decline":
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
            "resolved": True
        }
    else:  # escalate
        state["response"] = (
            f"I've reviewed your fraudulent transaction report. This case requires additional review by our fraud investigation team.\n\n"
            f"**Transaction Amount:** {transaction_amount}\n"
            f"**Reason:** {reason}\n\n"
            f"A fraud specialist will contact you within 24 hours to investigate this matter further. "
            f"Your case reference number is: {str(uuid.uuid4())[:8].upper()}. "
            f"In the meantime, we recommend monitoring your account and contacting your bank if needed. "
            f"Is there anything else I can help you with?"
        )
        state["data"] = {
            "action": "escalate",
            "issue_type": "fraudulent_transaction",
            "analysis": analysis_result,
            "case_id": str(uuid.uuid4())[:8].upper(),
            "resolved": False
        }
    
    return state

# ============================================
# Graph Router
# ============================================

def route_by_intent(state: AgentState) -> str:
    """Route to the appropriate node based on intent."""
    intent = state["intent"]
    if "recommendation" in intent:
        return "recommendation"
    if any(keyword in intent for keyword in ["purchase_accept", "purchase_decline", "product_selection"]):
        return "purchase_processing"
    if "purchase_info" in intent:
        return "purchase_info"
    if "product_defect" in intent:
        return "product_defect"
    if "damaged_shipping_box" in intent:
        return "damaged_shipping_box"
    if "fraudulent_transaction" in intent:
        return "fraudulent_transaction"
    return "response_generation"

# ============================================
# Build LangGraph
# ============================================

def create_agent_graph():
    """Create the LangGraph agent workflow."""
    workflow = StateGraph(AgentState)
    workflow.add_node("intent_detection", intent_detection_node)
    workflow.add_node("recommendation", recommendation_node)
    workflow.add_node("response_generation", response_generation_node)
    workflow.add_node("purchase_processing", purchase_processing_node)
    workflow.add_node("purchase_info", purchase_info_node)
    workflow.add_node("product_defect", product_defect_node)
    workflow.add_node("damaged_shipping_box", damaged_shipping_box_node)
    workflow.add_node("fraudulent_transaction", fraudulent_transaction_node)

    workflow.set_entry_point("intent_detection")
    workflow.add_conditional_edges(
        "intent_detection",
        route_by_intent,
        {
            "recommendation": "recommendation",
            "purchase_processing": "purchase_processing",
            "purchase_info": "purchase_info",
            "product_defect": "product_defect",
            "damaged_shipping_box": "damaged_shipping_box",
            "fraudulent_transaction": "fraudulent_transaction",
            "response_generation": "response_generation",
        },
    )
    workflow.add_edge("recommendation", "response_generation")
    workflow.add_edge("purchase_processing", END)
    workflow.add_edge("purchase_info", END)
    workflow.add_edge("product_defect", END)
    workflow.add_edge("damaged_shipping_box", END)
    workflow.add_edge("fraudulent_transaction", END)
    workflow.add_edge("response_generation", END)
    return workflow.compile()

# ============================================
# Main Execution Block
# ============================================

# --- MODIFICATION: Pass chat_history to the run_agent function ---
def run_agent(message: str, context: Dict[str, Any], chat_history: List, agent_graph, image_url: Optional[str] = None, image_type: Optional[str] = None) -> AgentState:
    """Single entry point to run the agent for one turn."""
    initial_state = {
        "message": message,
        "context": context or {},
        "chat_history": chat_history,
        "image_url": image_url,
        "image_type": image_type
    }
    return agent_graph.invoke(initial_state)

if __name__ == "__main__":
    agent_graph = create_agent_graph()
    print("Chatbot initialized. Type 'quit' to exit.")
    chat_context = {}
    # --- MODIFICATION: Initialize and manage chat_history in the main loop ---
    chat_history = []

    while True:
        user_input = input("You: ")
        if user_input.lower() == 'quit':
            break

        final_state = run_agent(user_input, chat_context, chat_history, agent_graph)
        print(f"Bot: {final_state['response']}")

        chat_context.update(final_state.get('data', {}))
        # --- MODIFICATION: Append user and bot messages to the history ---
        chat_history.append({"role": "user", "content": user_input})
        chat_history.append({"role": "assistant", "content": final_state['response']})