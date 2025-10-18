# E-Commerce Backend with LangGraph + Gemini AI Agents

An intelligent e-commerce backend powered by **LangGraph** and **Google's Gemini API**, featuring conversational AI agents for product recommendations and purchase assistance.

## 🚀 Features

### 🤖 AI-Powered Agents
- **Intent Detection Agent**: Understands user intentions using Gemini
- **Recommendation Agent**: Suggests products based on preferences and context
- **Purchase Agent**: Guides users through the buying process
- **Response Generation Agent**: Creates natural, conversational responses

### 🔄 LangGraph Architecture
- **Graph-based workflow**: Modular, maintainable agent design
- **State management**: Maintains conversation context across interactions
- **Conditional routing**: Intelligent flow control based on intent
- **Extensible**: Easy to add new nodes and capabilities

### 💬 Conversational Commerce
- Natural language product search
- Context-aware recommendations
- Multi-turn conversations
- Intelligent information extraction

### 🛡️ Robust & Reliable
- Fallback mechanism (works without API key)
- Graceful degradation
- JWT authentication
- Session management

## 📋 Prerequisites

- Python 3.8+
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

## 🔧 Installation

### Quick Install (Windows)
```bash
install.bat
```

### Quick Install (Linux/Mac)
```bash
chmod +x install.sh
./install.sh
```

### Manual Installation

1. **Create/activate virtual environment**:
```bash
# Create (if not exists)
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Set Gemini API key**:

**Windows (PowerShell)**:
```powershell
$env:GOOGLE_API_KEY="your_api_key_here"
```

**Windows (CMD)**:
```cmd
set GOOGLE_API_KEY=your_api_key_here
```

**Linux/Mac**:
```bash
export GOOGLE_API_KEY="your_api_key_here"
```

4. **Start the server**:
```bash
uvicorn main:app --reload
```

Server runs at: `http://localhost:8000`

## 🧪 Testing

### Run test suite:
```bash
python test_recommendation_agent.py
```

### Visualize graph structure:
```bash
python visualize_graph.py
```

### Interactive API docs:
Visit `http://localhost:8000/docs` after starting the server

## 📚 API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user

### Chat (AI Agent Interface)
- `POST /chat` - Main conversational endpoint
- `GET /chat/session/{session_id}` - Get conversation history

### Products
- `GET /products` - List all products
- `GET /products/{product_id}` - Get product details

### Cart
- `GET /cart` - View cart
- `POST /cart/add` - Add item to cart
- `DELETE /cart/remove/{product_id}` - Remove from cart
- `PUT /cart/update/{product_id}` - Update quantity

### Checkout
- `POST /checkout` - Complete purchase

## 💡 Usage Examples

### Example 1: Product Recommendation
```python
import requests

# Login
response = requests.post(
    "http://localhost:8000/auth/login",
    json={"email": "user@example.com", "password": "password"}
)
token = response.json()["access_token"]

# Chat with AI
headers = {"Authorization": f"Bearer {token}"}
response = requests.post(
    "http://localhost:8000/chat",
    headers=headers,
    json={"message": "I need a laptop for programming"}
)

print(response.json()["message"])
# AI recommends suitable laptop with details
```

### Example 2: Complete Purchase Flow
```python
# 1. Get recommendation
response = requests.post(
    "http://localhost:8000/chat",
    headers=headers,
    json={"message": "Show me wireless headphones"}
)
session_id = response.json()["session_id"]

# 2. Accept purchase
response = requests.post(
    "http://localhost:8000/chat",
    headers=headers,
    json={
        "message": "Yes, I want to buy them",
        "session_id": session_id
    }
)

# 3. Provide information
response = requests.post(
    "http://localhost:8000/chat",
    headers=headers,
    json={
        "message": "Name: John Doe, Address: 123 Main St, Payment: Visa",
        "session_id": session_id
    }
)

print(response.json()["data"]["order_id"])
# Returns order confirmation
```

## 🏗️ Architecture

### LangGraph Flow
```
User Input → Intent Detection → [Recommendation|Purchase|Response] → Output
```

### Agent Nodes

1. **Intent Detection Node**
   - Classifies user messages
   - Uses Gemini for context understanding
   - Routes to appropriate handler

2. **Recommendation Node**
   - Analyzes product requirements
   - Matches to product catalog
   - Considers budget and preferences

3. **Purchase Processing Node**
   - Handles purchase decisions
   - Extracts user information
   - Manages order flow

4. **Response Generation Node**
   - Creates natural responses
   - Formats product details
   - Maintains conversation flow

### State Management
```python
AgentState = {
    "message": str,           # Current message
    "context": dict,          # Conversation context
    "intent": str,            # Detected intent
    "recommendations": list,  # Products
    "response": str,          # Generated response
    "data": dict,            # Additional data
    "chat_history": list     # Message history
}
```

## 🔑 Configuration

### Environment Variables
- `GOOGLE_API_KEY` - Your Gemini API key (required for AI features)

### Model Settings (in agents.py)
```python
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",  # Fast, efficient
    temperature=0.7,            # Balanced creativity
    convert_system_message_to_human=True
)
```

## 📊 Database Structure

### Products
- In-memory product catalog (database.py)
- 8 featured electronics products
- Categories: phones, laptops, headphones, etc.

### Users
- In-memory user storage
- JWT-based authentication
- Password storage (hash in production!)

### Orders & Carts
- In-memory session storage
- Session-based cart management
- Order tracking

## 🛠️ Development

### Project Structure
```
backend/
├── agents.py              # LangGraph + Gemini agents
├── main.py               # FastAPI endpoints
├── models.py             # Pydantic models
├── database.py           # Data storage
├── requirements.txt      # Dependencies
├── test_recommendation_agent.py  # Tests
├── visualize_graph.py    # Graph visualization
├── install.bat          # Windows installer
├── install.sh           # Unix installer
├── SETUP.md            # Setup guide
└── README.md           # This file
```

### Adding New Products
Edit `database.py`:
```python
products["p9"] = {
    "id": "p9",
    "name": "Product Name",
    "price": 299.99,
    "category": "electronics",
    "description": "Product description",
    "image": "url",
    "stock": 50,
    "featured": True,
    "rating": 4.5
}
```

### Extending Agents
Add new nodes in `agents.py`:
```python
def new_agent_node(state: AgentState) -> AgentState:
    # Your agent logic
    state["custom_field"] = process(state["message"])
    return state

# Add to graph
workflow.add_node("new_agent", new_agent_node)
workflow.add_edge("intent_detection", "new_agent")
```

## 🐛 Troubleshooting

### "GOOGLE_API_KEY not set" Warning
- System uses fallback mode (rule-based)
- Set API key and restart server
- Check key is valid

### Import Errors
```bash
pip install --upgrade langchain langgraph langchain-google-genai
```

### Port Already in Use
```bash
# Use different port
uvicorn main:app --reload --port 8001
```

### Connection Refused
- Check server is running
- Verify URL: `http://localhost:8000`
- Check firewall settings

## 🔒 Security Notes

⚠️ **Important for Production**:
- Hash passwords (use bcrypt)
- Use environment variables for secrets
- Enable HTTPS
- Implement rate limiting
- Add input validation
- Use proper database (PostgreSQL, MongoDB)
- Add CORS restrictions
- Implement API key rotation

## 📈 Performance

- **With Gemini API**: ~1-2 seconds response time
- **Fallback mode**: <100ms response time
- **Concurrent sessions**: Supports multiple users
- **Memory usage**: ~200MB (with LangChain)

## 🎯 Future Enhancements

- [ ] Vector database for semantic search
- [ ] Product review analysis
- [ ] Multi-language support
- [ ] Voice interface
- [ ] Advanced analytics
- [ ] Recommendation personalization
- [ ] Inventory management
- [ ] Payment gateway integration

## 📝 License

This project is for educational purposes.

## 🤝 Contributing

Contributions welcome! Areas to improve:
- Additional agent nodes
- Better product matching algorithms
- Enhanced conversation flows
- Testing coverage
- Documentation

## 📞 Support

For issues or questions:
1. Check SETUP.md for detailed configuration
2. Run `python visualize_graph.py` to understand flow
3. Review test cases in test_recommendation_agent.py
4. Check API docs at `/docs` endpoint

## 🎓 Learning Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Gemini API Guide](https://ai.google.dev/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangChain Concepts](https://python.langchain.com/docs/get_started/introduction)

---

**Built with ❤️ using LangGraph + Gemini AI**

