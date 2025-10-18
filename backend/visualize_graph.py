"""
Visualize the LangGraph Agent Structure

This script demonstrates the agent graph flow without requiring API keys.
It shows how messages flow through different nodes based on intent.
"""

def print_graph_structure():
    """Print the agent graph structure"""
    print("\n" + "="*80)
    print("LANGGRAPH AGENT ARCHITECTURE")
    print("="*80)
    
    print("""
┌─────────────────────────────────────────────────────────────────────────┐
│                           USER MESSAGE INPUT                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     INTENT DETECTION NODE (Gemini)                       │
│                                                                           │
│  Classifies message into:                                                │
│  • recommendation    - User wants product suggestions                    │
│  • product_selection - User selecting from options                       │
│  • purchase_accept   - User agrees to buy                                │
│  • purchase_decline  - User declines purchase                            │
│  • purchase_info     - User provides payment info                        │
│  • general          - Greeting or unclear                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
                    ▼               ▼               ▼
        ┌──────────────┐  ┌─────────────────┐  ┌──────────────┐
        │ RECOMMENDA-  │  │   PURCHASE      │  │   RESPONSE   │
        │  TION NODE   │  │  PROCESSING     │  │  GENERATION  │
        │   (Gemini)   │  │     NODE        │  │     NODE     │
        │              │  │                 │  │   (Gemini)   │
        └──────────────┘  └─────────────────┘  └──────────────┘
                │                   │                    │
                └──────────┬────────┘                    │
                           ▼                             ▼
                ┌──────────────────────┐         ┌──────────────┐
                │  RESPONSE GENERATION │         │     END      │
                │        NODE          │         └──────────────┘
                │      (Gemini)        │
                └──────────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │     END      │
                    └──────────────┘
    """)
    
    print("="*80)
    print("\nNODE DESCRIPTIONS:")
    print("="*80)
    
    nodes = {
        "1. Intent Detection Node": [
            "• Uses Gemini to understand user intent",
            "• Considers conversation context",
            "• Routes to appropriate handler"
        ],
        "2. Recommendation Node": [
            "• Analyzes user query with Gemini",
            "• Extracts product preferences",
            "• Matches to available products",
            "• Considers budget constraints"
        ],
        "3. Purchase Processing Node": [
            "• Handles purchase acceptance/decline",
            "• Manages product selection from options",
            "• Extracts purchase information"
        ],
        "4. Response Generation Node": [
            "• Creates natural language responses",
            "• Uses Gemini for conversational replies",
            "• Formats product information",
            "• Maintains friendly tone"
        ]
    }
    
    for node_name, features in nodes.items():
        print(f"\n{node_name}")
        print("-" * 40)
        for feature in features:
            print(f"  {feature}")
    
    print("\n" + "="*80)


def demonstrate_flow():
    """Demonstrate message flow through the graph"""
    print("\n" + "="*80)
    print("EXAMPLE MESSAGE FLOWS")
    print("="*80)
    
    examples = [
        {
            "user": "I want to buy a laptop",
            "flow": [
                "1. Intent Detection: 'recommendation'",
                "2. → Recommendation Node: Analyzes 'laptop' + preferences",
                "3. → Response Generation: Creates friendly product suggestion",
                "4. → End: Returns recommendation with purchase question"
            ]
        },
        {
            "user": "Yes, I'll buy it",
            "flow": [
                "1. Intent Detection: 'purchase_accept'",
                "2. → Purchase Processing: Requests user information",
                "3. → End: Returns info request message"
            ]
        },
        {
            "user": "Name: John, Address: 123 Main St, Payment: Visa",
            "flow": [
                "1. Intent Detection: 'purchase_info'",
                "2. → (Handled in main.py): Extracts info with Gemini",
                "3. → Creates order",
                "4. → End: Returns order confirmation"
            ]
        },
        {
            "user": "Hello",
            "flow": [
                "1. Intent Detection: 'general'",
                "2. → Response Generation: Friendly greeting",
                "3. → End: Returns welcome message"
            ]
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n📝 Example {i}: User says '{example['user']}'")
        print("-" * 70)
        for step in example["flow"]:
            print(f"   {step}")
    
    print("\n" + "="*80)


def show_state_structure():
    """Show the agent state structure"""
    print("\n" + "="*80)
    print("AGENT STATE STRUCTURE")
    print("="*80)
    
    print("""
The state flows through all nodes and accumulates information:

AgentState = {
    "message": str,              # Current user message
    "context": dict,             # Conversation context
    "intent": str,               # Detected intent
    "recommendations": list,     # Product recommendations
    "response": str,             # Generated response
    "data": dict,                # Additional data (product, order, etc.)
    "chat_history": list         # Previous messages
}

Each node reads from and writes to this state, enabling:
• Context awareness across conversation
• Multi-turn interactions
• Personalized responses
• Order tracking
    """)
    
    print("="*80)


def show_fallback_mechanism():
    """Show how fallback works without API key"""
    print("\n" + "="*80)
    print("FALLBACK MECHANISM")
    print("="*80)
    
    print("""
The system includes intelligent fallback when Gemini API is unavailable:

WITH GEMINI API:
├─ Natural language understanding
├─ Context-aware responses
├─ Flexible information extraction
└─ Conversational tone

WITHOUT GEMINI API (Fallback):
├─ Rule-based intent detection
├─ Keyword matching for products
├─ Regex information extraction
└─ Template-based responses

Benefits:
✓ System always functional
✓ Graceful degradation
✓ No service interruption
✓ Same API endpoints
    """)
    
    print("="*80)


def show_integration_points():
    """Show how this integrates with main.py"""
    print("\n" + "="*80)
    print("INTEGRATION WITH MAIN.PY")
    print("="*80)
    
    print("""
The agent functions are called from main.py endpoints:

/chat endpoint flow:
1. Receives user message
2. Calls detect_intent(message, context)
   └─ LangGraph: intent_detection_node
3. Based on intent, calls generate_response()
   └─ LangGraph: recommendation_node → response_generation_node
4. Returns response to user

Key functions exposed to main.py:
├─ detect_intent(message, context) → str
├─ get_product_recommendations(query) → List[Dict]
├─ extract_purchase_info(message) → Dict
└─ generate_response(intent, message, context) → Tuple[str, Dict]

✓ All endpoints remain unchanged
✓ No modifications needed to main.py
✓ Backward compatible
✓ Drop-in replacement
    """)
    
    print("="*80)


if __name__ == "__main__":
    print("\n🤖 LANGGRAPH + GEMINI AI AGENT VISUALIZATION\n")
    
    print_graph_structure()
    demonstrate_flow()
    show_state_structure()
    show_fallback_mechanism()
    show_integration_points()
    
    print("\n" + "="*80)
    print("✅ READY TO USE")
    print("="*80)
    print("""
To start using the agents:

1. Install dependencies:
   pip install -r requirements.txt

2. Set your Gemini API key:
   Windows: set GOOGLE_API_KEY=your_key_here
   Linux/Mac: export GOOGLE_API_KEY=your_key_here

3. Start the server:
   uvicorn main:app --reload

4. Test the agents:
   python test_recommendation_agent.py
    """)
    print("="*80 + "\n")

