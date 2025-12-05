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
        - product_selection: User is choosing an option from a list of recommendations (e.g., "Option 1", "I'll take the first one", "number 2").
        - purchase_accept: User agrees to purchase a suggested product.
        - purchase_decline: User declines to purchase a suggested product.
        - purchase_info: User provides purchase details like name, address, or payment method.
        - order_shipping_status: User is asking about the status of an order, shipping updates, or tracking information (e.g., "Where is my order?", "Track order #12345", "shipping status").
        - fraudulent_transaction: User is reporting a fraudulent transaction with an OCR image of their credit card statement (e.g., "I see a fraudulent charge", "This transaction is not mine", "Unauthorized charge on my card").
        - product_defect: User is reporting a product defect with an image (e.g., "I received a damaged product", "This item has a defect", "The product I got is broken").
        - damaged_shipping_box: User is reporting a damaged shipping box with an image (e.g., "The box arrived damaged", "My package box was torn", "Shipping box is damaged").
        - general: General conversation, greetings, or questions not related to products.

        ### Important Rules
        - If the user's message depends on previous context (like refining a budget, brand, or feature), treat it as **recommendation**.
        - If the user is selecting a specific option from a provided list, classify as **product_selection**.
        - If awaiting_purchase_decision is True and the user says something like "yes", "okay", or "I'll take it," classify as **purchase_accept**.
        - If awaiting_purchase_decision is True and the user says "no", "not now", or "too expensive," classify as **purchase_decline**.
        - If awaiting_purchase_info is True, classify as **purchase_info**.
        - Consider the full conversation history when determining intent.
        - If the user asks about order status, tracking, or shipping, classify as **order_shipping_status**.
        - If the user mentions fraudulent charges, unauthorized transactions, or credit card issues (especially with OCR/image context), classify as **fraudulent_transaction**.
        - If the user mentions product defects, damaged items, or issues with a received product (especially with image context), classify as **product_defect**.
        - If the user mentions damaged shipping boxes, package damage, or delivery box issues (especially with image context), classify as **damaged_shipping_box**.
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
        User: Where is my order?
        User Message: "Check status for order 12345"
        Context:
        awaiting_purchase_decision: False
        Output: order_shipping_status

        **Example 4**
        Conversation History:
        User: I see a charge I didn't make.
        User Message: "Here is my statement"
        Context:
        awaiting_purchase_decision: False
        Output: fraudulent_transaction

        **Example 5**
        Conversation History:
        User: Hello!
        User Message: "How are you?"
        Context:
        awaiting_purchase_decision: False
        Output: general
        
        **Example 6**
        Conversation History:
        Assistant: Here are 3 options: 1. iPhone, 2. Samsung, 3. Pixel.
        User Message: "Option 2"
        Context:
        awaiting_purchase_decision: True
        Output: product_selection

        **Example 7**
        Conversation History:
        User: I like the Dell XPS you showed.
        User Message: "I'll take it"
        Context:
        awaiting_purchase_decision: True
        Output: purchase_accept

        **Example 8**
        Conversation History:
        User: The phone screen is cracked.
        User Message: "Here is a picture of the crack"
        Context:
        awaiting_purchase_decision: False
        Output: product_defect

        **Example 9**
        Conversation History:
        User: The delivery box is crushed.
        User Message: "Look at this box"
        Context:
        awaiting_purchase_decision: False
        Output: damaged_shipping_box

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

def get_single_recommendation_prompt():
    return ChatPromptTemplate.from_template(
        """
        You are a friendly shopping assistant. You have found a perfect match for the user.
        Present the product and ask if they would like to purchase it.

        Product Name: {name} (${price})
        Rating: {rating}/5.0
        Description: {description}
        """
    )

def get_multiple_recommendations_prompt():
    return ChatPromptTemplate.from_template(
        """
        You are a friendly shopping assistant. You found a few great options for the user.
        Present these options and ask them to choose one.

        Options:
        {options}
        Keep the response concise and friendly.
        """
    )

def get_general_chat_prompt():
    return ChatPromptTemplate.from_template(
        """
        You are a shopping assistant.
        Conversation History:
        {chat_history}
        The user said: '{user_message}'. Respond helpfully.
        """
    )

def get_purchase_info_extraction_prompt():
    return ChatPromptTemplate.from_template(
        """
        You are an expert at extracting structured information.
        Extract the user's name, shipping address, and payment method from the message.

        Message: "{message}"
        {format_instructions}
        """
    )

def get_order_id_extraction_prompt():
    return ChatPromptTemplate.from_template(
        """
        Extract the Order ID from the user's message.
        Order IDs are typically 8-character alphanumeric strings (e.g., A1B2C3D4).
        If found, return ONLY the Order ID.
        If not found, return "None".
        
        Message: "{message}"
        """
    )

def get_fraud_analysis_prompt():
    return ChatPromptTemplate.from_template(
        """
        You are an expert fraud detection agent analyzing a credit card statement OCR image.
        
        CRITICAL STEP 1: IMAGE VALIDATION
        - First, determine if the image actually depicts a document, statement, receipt, or screen showing financial transactions.
        - If the image is random, black screen, blurry, unrelated, or contains no readable text, you MUST REJECT the claim.
        - Decision for invalid images: "escalate" or "decline".
        - Reason: "The provided image is not a valid financial document."

        CRITICAL STEP 2: FRAUD ANALYSIS (Only if Step 1 passes)
        Analyze the image and determine the appropriate action based on:
        1. Whether the transaction appears legitimate
        2. Transaction amount and details
        3. Evidence of fraud or unauthorized charges
        
        User's message: "{user_message}"
        
        Return a JSON response with:
        - decision: "refund", "decline", or "escalate"
        - reason: Brief explanation of your decision
        - transaction_amount: Extracted transaction amount if visible
        - transaction_date: Extracted transaction date if visible
        - fraud_indicators: List of any suspicious indicators found
        - confidence: "high", "medium", or "low" - your confidence in the decision
        
        Guidelines:
        - Refund: For clearly unauthorized transactions, confirmed fraud.
        - Decline: For legitimate transactions, insufficient evidence, or random images.
        - Escalate: For unclear cases, high-value transactions.
        
        Return only valid JSON.
        """
    )

def get_product_defect_analysis_prompt():
    return ChatPromptTemplate.from_template(
        """
        You are an expert customer service agent analyzing a product defect image.
        
        CRITICAL STEP 1: IMAGE VALIDATION
        - First, determine if the image actually depicts a consumer product (e.g., electronics, gadget, appliance).
        - If the image is random, black screen, blurry, unrelated (e.g., a landscape, selfie, animal, or abstract pattern), or does not clearly show a product, you MUST REJECT the claim.
        - Decision for invalid images: "escalate" (if unsure) or "decline" (if clearly random/irrelevant).
        - Reason: "The provided image does not show a valid product or defect."

        CRITICAL STEP 2: DEFECT ANALYSIS (Only if Step 1 passes)
        Analyze the image and determine the appropriate action based on:
        1. Severity of the defect
        2. Whether it's a manufacturing defect or user damage
        3. Product value and replacement cost
        
        User's message: "{user_message}"
        
        Return a JSON response with:
        - decision: "refund", "replace", "decline", or "escalate"
        - reason: Brief explanation of your decision
        - severity: "none", "minor", "moderate", or "severe"
        - defect_type: Description of the defect observed, or "none" if invalid image
        
        Guidelines:
        - Refund: For severe defects on valid products, high-value items with significant issues.
        - Replace: For moderate defects on valid products.
        - Escalate: For unclear cases, potential fraud, or when human judgment is needed.
        - Decline: For random images, no visible defect, or unrelated content.
        
        Return only valid JSON.
        """
    )

def get_damaged_box_analysis_prompt():
    return ChatPromptTemplate.from_template(
        """
        You are an expert customer service agent analyzing a damaged shipping box image.
        
        CRITICAL STEP 1: IMAGE VALIDATION
        - First, determine if the image actually depicts a shipping box, cardboard box, or package.
        - If the image is random, black screen, blurry, unrelated, or does not clearly show a package, you MUST REJECT the claim.
        - Decision for invalid images: "escalate" or "decline".
        - Reason: "The provided image does not show a valid shipping box."

        CRITICAL STEP 2: DAMAGE ANALYSIS (Only if Step 1 passes)
        Analyze the image and determine the appropriate action based on:
        1. Extent of box damage
        2. Likelihood of product damage inside
        3. Whether the product appears intact or damaged
        
        User's message: "{user_message}"
        
        Return a JSON response with:
        - decision: "refund", "replace", "decline", or "escalate"
        - reason: Brief explanation of your decision
        - box_damage_severity: "none", "minor", "moderate", or "severe"
        - product_condition: "likely_intact", "possibly_damaged", "likely_damaged", or "unknown"
        
        Guidelines:
        - Refund: For severe box damage with likely product damage.
        - Replace: For moderate damage where replacement is appropriate.
        - Escalate: For unclear cases, potential fraud.
        - Decline: For random images or no visible box.
        
        Return only valid JSON.
        """
    )