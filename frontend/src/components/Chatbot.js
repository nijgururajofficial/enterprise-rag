import React, { useState, useRef, useEffect } from 'react';
import { FiMessageCircle, FiX, FiSend, FiShoppingCart } from 'react-icons/fi';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import './Chatbot.css';

const API_URL = 'http://localhost:8000';

const Chatbot = () => {
  const { token, isAuthenticated } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: 1,
      text: "👋 Hello! I'm your AI shopping assistant. I can help you find the perfect product!\n\nJust tell me what you're looking for, for example:\n• 'I want to buy a phone'\n• 'Show me laptops under $1000'\n• 'Looking for wireless headphones'\n• 'Need a gaming monitor'\n\nWhat can I help you find today?",
      sender: 'bot',
      timestamp: new Date()
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim()) return;

    // Check if user is authenticated
    if (!isAuthenticated) {
      const botMessage = {
        id: messages.length + 1,
        text: "⚠️ Please log in to use the shopping assistant. You can log in from the navigation menu.",
        sender: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, botMessage]);
      return;
    }

    const userMessage = {
      id: messages.length + 1,
      text: inputMessage,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    const messageText = inputMessage;
    setInputMessage('');
    setIsTyping(true);

    try {
      // Call the unified /chat endpoint
      const response = await axios.post(
        `${API_URL}/chat`,
        {
          message: messageText,
          session_id: sessionId
        },
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      const data = response.data;
      
      // Store session ID for future messages
      if (data.session_id && !sessionId) {
        setSessionId(data.session_id);
      }

      // Create bot response with product info if available
      const botMessage = {
        id: messages.length + 2,
        text: data.message,
        sender: 'bot',
        timestamp: new Date(),
        intent: data.intent,
        data: data.data
      };

      setMessages(prev => [...prev, botMessage]);
      setIsTyping(false);
    } catch (error) {
      console.error('Chat error:', error);
      
      let errorMessage = "Sorry, I encountered an error. Please try again.";
      
      if (error.response?.status === 401) {
        errorMessage = "⚠️ Your session has expired. Please log in again.";
      } else if (error.response?.data?.detail) {
        errorMessage = `Error: ${error.response.data.detail}`;
      }

      const botMessage = {
        id: messages.length + 2,
        text: errorMessage,
        sender: 'bot',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, botMessage]);
      setIsTyping(false);
    }
  };

  const formatTime = (timestamp) => {
    return timestamp.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    });
  };

  const renderMessageContent = (message) => {
    // Format message text with line breaks
    const formattedText = message.text.split('\n').map((line, idx) => (
      <React.Fragment key={idx}>
        {line}
        {idx < message.text.split('\n').length - 1 && <br />}
      </React.Fragment>
    ));

    return (
      <div className="message-content">
        <div className="message-text">{formattedText}</div>
        
        {/* Display product information if available */}
        {message.data?.product && (
          <div className="product-card">
            <img src={message.data.product.image} alt={message.data.product.name} />
            <div className="product-info">
              <h4>{message.data.product.name}</h4>
              <div className="product-details">
                <span className="price">${message.data.product.price.toFixed(2)}</span>
                <span className="rating">⭐ {message.data.product.rating}/5.0</span>
              </div>
              <p className="product-desc">{message.data.product.description}</p>
              <div className="product-stock">
                📦 {message.data.product.stock} units available
              </div>
            </div>
          </div>
        )}

        {/* Display order confirmation if available */}
        {message.data?.order_id && (
          <div className="order-confirmation">
            <div className="order-header">
              <FiShoppingCart size={20} />
              <span>Order Confirmed!</span>
            </div>
            <div className="order-number">
              Order #{message.data.order_id}
            </div>
          </div>
        )}
        
        <span className="message-time">{formatTime(message.timestamp)}</span>
      </div>
    );
  };

  return (
    <div className="chatbot-container">
      {/* Chat Toggle Button */}
      <button 
        className={`chatbot-toggle ${isOpen ? 'open' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Toggle chat"
      >
        {isOpen ? <FiX size={24} /> : <FiMessageCircle size={24} />}
        {!isAuthenticated && (
          <span className="auth-badge">Login Required</span>
        )}
      </button>

      {/* Chat Window */}
      {isOpen && (
        <div className="chatbot-window">
          <div className="chatbot-header">
            <div className="chatbot-header-content">
              <FiMessageCircle size={20} />
              <div>
                <h3>🤖 AI Shopping Assistant</h3>
                <span className="status-indicator">
                  {isAuthenticated ? '✓ Authenticated' : '⚠️ Login Required'}
                </span>
              </div>
            </div>
            <button 
              className="close-btn"
              onClick={() => setIsOpen(false)}
              aria-label="Close chat"
            >
              <FiX size={20} />
            </button>
          </div>

          <div className="chatbot-messages">
            {messages.map((message) => (
              <div 
                key={message.id}
                className={`message ${message.sender === 'user' ? 'user-message' : 'bot-message'}`}
              >
                {renderMessageContent(message)}
              </div>
            ))}
            {isTyping && (
              <div className="message bot-message">
                <div className="message-content">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form className="chatbot-input-container" onSubmit={handleSendMessage}>
            <input
              type="text"
              placeholder={isAuthenticated ? "Type your message..." : "Please login to chat..."}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              className="chatbot-input"
              disabled={!isAuthenticated}
            />
            <button 
              type="submit"
              className="send-btn"
              disabled={!inputMessage.trim() || !isAuthenticated}
              aria-label="Send message"
            >
              <FiSend size={18} />
            </button>
          </form>
        </div>
      )}
    </div>
  );
};

export default Chatbot;

