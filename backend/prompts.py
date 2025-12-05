from langchain_core.prompts import ChatPromptTemplate

def get_intent_detection_prompt():
    """
    Returns a few-shot ChatPromptTemplate for e-commerce chatbot intent detection.
    It handles follow-up messages like 'how about under $300' by considering
    conversation history and context.
    """
    prompt = ChatPromptTemplate.from_template(
        """
        You are an expert intent detection AI for an e-commerce chatbot.
        Your task is to classify the user's message into one of the following intents:

        - recommendation: User is asking for a product suggestion, looking for a product, or refining their request (e.g., follow-ups like 'how about under $300').
        - product_selection: User is choosing an option from a list of recommendations.
        - purchase_accept: User agrees to purchase a suggested product.
        - purchase_decline: User declines to purchase a suggested product.
        - product_defect: User is reporting a product defect with an image (e.g., "I received a damaged product", "This item has a defect", "The product I got is broken").
        - damaged_shipping_box: User is reporting a damaged shipping box with an image (e.g., "The box arrived damaged", "My package box was torn", "Shipping box is damaged").
        - fraudulent_transaction: User is reporting a fraudulent transaction with an OCR image of their credit card statement (e.g., "I see a fraudulent charge", "This transaction is not mine", "Unauthorized charge on my card").
        - general: General conversation, greetings, or questions not related to products.

        ### Important Rules
        - If the user's message depends on previous context (like refining a budget, brand, or feature), treat it as **recommendation**.
        - Consider the full conversation history when determining intent.
        - If awaiting_purchase_decision is True and the user says something like "yes", "okay", or "I'll take it," classify as **purchase_accept**.
        - If awaiting_purchase_decision is True and the user says "no", "not now", or "too expensive," classify as **purchase_decline**.
        - If the user mentions product defects, damaged items, or issues with a received product (especially with image context), classify as **product_defect**.
        - If the user mentions damaged shipping boxes, package damage, or delivery box issues (especially with image context), classify as **damaged_shipping_box**.
        - If the user mentions fraudulent charges, unauthorized transactions, or credit card issues (especially with OCR/image context), classify as **fraudulent_transaction**.
        - Otherwise, classify based on message meaning.

        ### Examples

        **Example 1**
        Conversation History:
        User: I want a new laptop
        Assistant: Sure! What’s your budget?
        User Message: "how about under $300"
        Context:
        awaiting_purchase_decision: False
        Output: recommendation

        **Example 2**
        Conversation History:
        User: Can you recommend a phone with a great camera?
        User Message: "Maybe something from Samsung"
        Context:
        awaiting_purchase_decision: False
        Output: recommendation

        **Example 3**
        Conversation History:
        User: I like the Dell XPS you showed.
        User Message: "I'll take it"
        Context:
        awaiting_purchase_decision: True
        Output: purchase_accept

        **Example 4**
        Conversation History:
        User: That monitor seems pricey.
        User Message: "No thanks"
        Context:
        awaiting_purchase_decision: True
        Output: purchase_decline

        **Example 5**
        Conversation History:
        User: Hello!
        User Message: "How are you?"
        Context:
        awaiting_purchase_decision: False
        Output: general

        Now classify the intent for this case:

        Conversation History:
        {chat_history}

        Context:
        - awaiting_purchase_decision: {awaiting_purchase_decision}
        User Message: "{message}"

        Return only the intent name.
        """
    )
    return prompt

def get_product_extraction_prompt():
    """
    Returns a refined few-shot ChatPromptTemplate for extracting structured
    product requirements from user queries.
    Includes category mapping, rating extraction, and default budget handling.
    """
    prompt = ChatPromptTemplate.from_template(
        """
        You are a helpful product recommendation assistant.
        Your job is to extract structured product requirements from the user's message.

        **Valid categories:** "laptops", "phones", "monitors"

        **Category mapping examples:**
        - If the user says "mobile", "cellphone", or "smartphone" → use "phones"
        - If the user says "notebook", "macbook", or "gaming laptop" → use "laptops"
        - If the user says "display", "screen", or "monitor" → use "monitors"

        If no category is mentioned, infer it logically from context.
        If no budget is specified, default to a range of 300–2000.
        If no rating is mentioned, set min_rating to 0.0.

        Always return the output in **strict JSON format** with:
        - category
        - min_price
        - max_price
        - min_rating
        - features (list of short keywords)

        ### Examples

        **Example 1**
        User Query: "I’m looking for a good labtop under 1200 with long battery life"
        Output:
        {{
            "category": "laptops",
            "min_price": 0,
            "max_price": 1200,
            "min_rating": 0.0,
            "features": ["long battery life"]
        }}

        **Example 2**
        User Query: "Need a phone for gaming and good camera"
        Output:
        {{
            "category": "phones",
            "min_price": 300,
            "max_price": 2000,
            "min_rating": 0.0,
            "features": ["gaming", "good camera"]
        }}

        **Example 3**
        User Query: "Looking for a high-resolution monitor around 400 bucks, rated above 4.5"
        Output:
        {{
            "category": "monitors",
            "min_price": 0,
            "max_price": 400,
            "min_rating": 4.5,
            "features": ["high-resolution"]
        }}

        Now extract requirements for this user query:

        User Query: "{query}"
        {format_instructions}
        """
    )
    return prompt