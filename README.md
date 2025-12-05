# ElectroStore - Smart Electronics Retail Application

A full-stack electronics retail application built with **FastAPI** (backend) and **React** (frontend), featuring a **LangGraph** intelligent agent system for conversational shopping, product recommendations, and automated support.

## 🚀 Key Features

*   **Intelligent Chat Assistant**: A unified chat interface that understands user intent and routes requests to specialized agents.
*   **Smart Product Search**: Semantic search and filtering for finding the perfect product.
*   **Visual Analysis**: Ability to analyze images for:
    *   **Fraud Detection**: Reads transaction receipts/statements using OCR (via Vision LLM).
    *   **Product Defects**: Analyzes images of defective products for refund/replacement decisions.
    *   **Shipping Damage**: Assesses damaged shipping boxes.
*   **Full E-commerce Flow**: User registration, login, product browsing, cart management, and checkout.

## 🧠 AI Agent Architecture (LangGraph)

The backend uses a graph-based agent system (`backend/agents.py`) consolidated into three main specialized agents to handle different user needs efficiently:

1.  **Intent Detection Node**: The entry point that analyzes the user's message to decide which agent should handle it.
2.  **Recommendation Agent**:
    *   Handles general conversation.
    *   Provides product recommendations based on user criteria (price, category, features).
3.  **Purchase Agent**:
    *   Manages the purchase flow (accept/decline recommendations).
    *   Collects shipping and payment information.
    *   Checks order status and shipping updates.
4.  **Fraud Detection Agent**:
    *   Handles "post-purchase" issues.
    *   Analyzes uploaded images for fraud claims, product defects, or shipping damage.
    *   Makes automated decisions (Refund, Replace, or Escalate) based on visual analysis.

## 🛠️ Tech Stack

### Backend
*   **FastAPI**: High-performance web framework.
*   **LangGraph**: For orchestrating the stateful multi-agent workflow.
*   **LangChain**: For LLM interactions and prompt management.
*   **OpenAI GPT-4o**: Powers the intelligence, including Vision capabilities for OCR and image analysis.
*   **ChromaDB**: Vector database for semantic product search.
*   **SQLite**: Relational database for users, orders, and products.

### Frontend
*   **React 18**: Modern UI with hooks.
*   **Tailwind CSS**: For styling (if applicable, otherwise standard CSS).
*   **Axios**: For API communication.

## 📦 Project Structure

```
├── backend/
│   ├── agents.py            # LangGraph agent definitions (Recommendation, Purchase, Fraud)
│   ├── utils.py             # LLM helper functions (OCR, Intent Detection, etc.)
│   ├── main.py              # FastAPI application endpoints
│   ├── database.py          # Database interactions (SQLite + ChromaDB)
│   ├── prompts.py           # Centralized prompt templates
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/                 # React source code
│   └── public/              # Static assets
└── README.md                # This file
```

## 🚀 Quick Start

### Prerequisites
*   Python 3.8+
*   Node.js 14+
*   OpenAI API Key

### 1. Backend Setup
```bash
cd backend
python -m venv venv
# Activate venv: venv\Scripts\activate (Windows) or source venv/bin/activate (Mac/Linux)
pip install -r requirements.txt

# Create a .env file in /backend
# OPENAI_API_KEY=your_key_here
```
Run the server:
```bash
uvicorn main:app --reload
```
*Backend runs at: http://localhost:8000*

### 2. Frontend Setup
```bash
cd frontend
npm install
npm start
```
*Frontend runs at: http://localhost:3000*

## 📝 Usage Guide

1.  **Register/Login**: Create an account to start shopping.
2.  **Chat**: Use the chat interface to:
    *   "Find me a gaming laptop under $1500." (Recommendation Agent)
    *   "I want to buy this." (Purchase Agent)
    *   "Where is my order #12345?" (Purchase Agent)
    *   *Upload an image of a broken screen* -> "My product arrived damaged." (Fraud Detection Agent)
3.  **Checkout**: You can also use the traditional cart and checkout flow.
