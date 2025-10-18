# ElectroStore - Electronics Retail Application

A full-stack electronics retail application built with FastAPI (backend) and React (frontend), featuring **LangGraph + Gemini AI agents** for intelligent product recommendations, conversational commerce, user authentication, shopping cart, and checkout functionality.

## 🌟 Key Highlights

### 🤖 AI-Powered Shopping Experience
- **LangGraph Agent Framework**: Modular, graph-based agent architecture
- **Google Gemini API**: Advanced natural language understanding
- **Conversational Commerce**: Chat-based product discovery and purchase
- **Intelligent Recommendations**: Context-aware product suggestions

## Features

### Backend (FastAPI + LangGraph + Gemini)
- **AI Agents**: LangGraph-based conversational agents powered by Gemini
- **Intent Detection**: Understands user queries naturally
- **Smart Recommendations**: Context-aware product suggestions
- **Product Management**: Browse and search electronics products
- **User Authentication**: JWT-based login and registration
- **Shopping Cart**: Add, remove, and update cart items
- **Order Processing**: Complete checkout and order management
- **Conversational Interface**: Natural language chat for shopping
- **RESTful API**: Well-documented endpoints with automatic OpenAPI docs

### Frontend (React)
- **Modern UI**: Beautiful, responsive design with mobile-first approach
- **Product Showcase**: Featured products carousel and detailed product pages
- **User Authentication**: Login and registration with form validation
- **Shopping Cart**: Real-time cart updates and management
- **Checkout Process**: Secure payment form and order confirmation
- **Search & Filter**: Product search and filtering capabilities
- **Responsive Design**: Optimized for desktop, tablet, and mobile devices

## Tech Stack

### Backend
- **LangGraph**: Graph-based agent framework for AI workflows
- **Google Gemini API**: Advanced language model (gemini-1.5-flash)
- **LangChain**: Agent orchestration and LLM integration
- **FastAPI**: Modern, fast web framework for building APIs
- **Pydantic**: Data validation using Python type annotations
- **JWT**: JSON Web Tokens for secure authentication
- **Python**: Core programming language

### Frontend
- **React 18**: Modern React with hooks and functional components
- **React Router**: Client-side routing
- **Axios**: HTTP client for API calls
- **React Icons**: Beautiful icon library
- **React Toastify**: Toast notifications
- **CSS3**: Modern styling with Flexbox and Grid

## Project Structure

```
├── backend/
│   ├── main.py              # FastAPI application and routes
│   ├── models.py            # Pydantic models for request/response
│   ├── database.py          # Mock database with sample data
│   ├── agents.py            # LangGraph + Gemini AI agents
│   ├── requirements.txt     # Python dependencies
│   ├── test_recommendation_agent.py  # Agent testing suite
│   ├── visualize_graph.py   # Graph structure visualization
│   ├── install.bat/sh       # Quick installation scripts
│   ├── README.md            # Backend documentation
│   └── SETUP.md             # Detailed setup guide
├── frontend/
│   ├── public/
│   │   └── index.html       # HTML template
│   ├── src/
│   │   ├── components/      # Reusable React components
│   │   ├── context/         # React context for state management
│   │   ├── pages/           # Page components
│   │   ├── App.js           # Main App component
│   │   └── index.js         # React entry point
│   └── package.json         # Node.js dependencies
└── README.md                # This file
```

## Setup Instructions

### Prerequisites
- Python 3.8+ 
- Node.js 14+
- npm or yarn
- **Google Gemini API Key** ([Get free key here](https://makersuite.google.com/app/apikey))

### Backend Setup

#### Quick Setup (Recommended)

**Windows:**
```bash
cd backend
install.bat
```

**Linux/Mac:**
```bash
cd backend
chmod +x install.sh
./install.sh
```

#### Manual Setup

1. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Gemini API Key** (Required for AI features):
   
   **Windows (PowerShell):**
   ```powershell
   $env:GOOGLE_API_KEY="your_gemini_api_key_here"
   ```
   
   **Windows (CMD):**
   ```cmd
   set GOOGLE_API_KEY=your_gemini_api_key_here
   ```
   
   **Linux/Mac:**
   ```bash
   export GOOGLE_API_KEY="your_gemini_api_key_here"
   ```
   
   > **Note**: Without API key, the system uses fallback rule-based agents

5. **Run the FastAPI server**:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

   The API will be available at `http://localhost:8000`
   
   API documentation will be available at `http://localhost:8000/docs`

6. **Test the AI agents** (Optional):
   ```bash
   python test_recommendation_agent.py
   ```

7. **Visualize agent graph** (Optional):
   ```bash
   python visualize_graph.py
   ```

### Frontend Setup

1. **Navigate to frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start the development server**:
   ```bash
   npm start
   ```

   The application will be available at `http://localhost:3000`

## Usage

### Demo Account
For testing purposes, you can use the following demo account:
- **Email**: john@example.com
- **Password**: hashed_password_123

### Key Features to Test

1. **AI Chat Interface**: Try conversational product recommendations
   - "I need a laptop for programming"
   - "Show me wireless headphones under $300"
   - "Looking for a budget phone"
2. **Browse Products**: Visit the home page to see featured products
3. **Product Search**: Use the search functionality on the products page
4. **User Registration**: Create a new account or use the demo account
5. **Shopping Cart**: Add products to cart and manage quantities
6. **Checkout**: Complete a purchase with the checkout flow
7. **Conversational Purchase**: Buy products through chat interface

## API Endpoints

### 🤖 AI Chat Interface (Main)
- `POST /chat` - **Unified conversational interface** (handles recommendations, purchases, questions)
- `GET /chat/session/{session_id}` - Get conversation history

### Authentication
- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login user

### Products
- `GET /products` - Get all products (with optional featured filter)
- `GET /products/{id}` - Get specific product details

### Cart (Authenticated)
- `GET /cart` - Get user's cart
- `POST /cart/add` - Add item to cart
- `PUT /cart/update/{product_id}` - Update cart item quantity
- `DELETE /cart/remove/{product_id}` - Remove item from cart

### Orders (Authenticated)
- `POST /checkout` - Checkout entire cart
- `POST /purchase` - Purchase single product (deprecated - use /chat)

### Recommendations (Legacy)
- `POST /recommend` - Get product recommendations (deprecated - use /chat)

## Development

### Backend Development
- **AI Agents**: LangGraph-based architecture with Gemini API
- **Agent Nodes**: Intent detection, recommendation, purchase processing, response generation
- **Fallback System**: Rule-based agents when API unavailable
- **State Management**: Maintains conversation context across interactions
- The backend uses FastAPI with automatic API documentation
- Mock data is stored in `database.py` for development
- JWT tokens are used for authentication
- CORS is configured to allow frontend requests

### Agent Architecture

```
User Message
    ↓
Intent Detection (Gemini)
    ↓
┌───┴──────────────┐
│                  │
Recommendation   Purchase
    ↓                ↓
Response Generation
    ↓
User Response
```

For detailed architecture, see `backend/README.md` or run `python visualize_graph.py`

### Frontend Development
- React context is used for state management (Auth and Cart)
- Components are organized by feature
- CSS modules provide scoped styling
- Responsive design ensures mobile compatibility

## Production Considerations

For production deployment, consider:

1. **Backend**:
   - **Secure API keys**: Use environment variables and secret management
   - **Rate limiting**: Protect Gemini API usage and prevent abuse
   - Use a real database (PostgreSQL, MongoDB, etc.)
   - Implement proper password hashing (bcrypt)
   - Add security middleware
   - Implement proper logging and monitoring
   - Cache Gemini responses to reduce API calls
   - Add fallback mechanisms for API failures

2. **Frontend**:
   - Build optimized production bundle
   - Configure proper environment variables
   - Add error boundaries
   - Implement proper SEO optimization
   - Add analytics and monitoring

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is for educational purposes. Feel free to use and modify as needed.
