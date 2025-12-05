import React, { useState, useRef, useEffect } from 'react';
import { FiMessageCircle, FiX, FiSend, FiShoppingCart } from 'react-icons/fi';
import axios from 'axios';
import { useSidebar } from '../App';
import './Chatbot.css';

const API_URL = 'http://localhost:8000';

const CATEGORY_SHORTCUTS = [
  { key: 'phones', label: 'Phones', prompt: 'Show me the latest phones' },
  { key: 'laptops', label: 'Laptops', prompt: 'Recommend laptops for work' },
  { key: 'monitors', label: 'Monitors', prompt: 'Find monitors around $500' },
];

const CATEGORY_LABELS = CATEGORY_SHORTCUTS.reduce((acc, item) => {
  acc[item.key] = item.label;
  return acc;
}, {});

const Chatbot = ({ onRecommendations }) => {
  const { isSidebarOpen, setIsSidebarOpen } = useSidebar();
  const [messages, setMessages] = useState([
    {
      id: 1,
      text: "👋 Hello! I'm your AI shopping assistant. I can help you find the perfect product!\n\nTry asking for:\n• 'Show me the latest phones'\n• 'Recommend laptops for work'\n• 'Find monitors around $500'\n• 'Suggest useful accessories'\n\nNeed a shortcut? Tap a category below to get started!",
      sender: 'bot',
      timestamp: new Date()
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [categoryStats, setCategoryStats] = useState({});
  const messagesEndRef = useRef(null);

  const handleCategoryClick = (prompt) => {
    handleSendMessage(null, prompt);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(e);
    }
  };

  const handleInputChange = (e) => {
    setInputMessage(e.target.value);
    
    // Auto-resize textarea
    const textarea = e.target;
    textarea.style.height = 'auto';
    const newHeight = Math.min(textarea.scrollHeight, 120);
    textarea.style.height = newHeight + 'px';
  };

  const handleSendMessage = async (e, overrideMessage) => {
    if (e?.preventDefault) {
      e.preventDefault();
    }

    const messageText = (overrideMessage ?? inputMessage).trim();
    if (!messageText) return;

    const userMessage = {
      id: `user-${Date.now()}`,
      text: messageText,
      sender: 'user',
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsTyping(true);
    
    // Reset textarea height
    const textarea = document.querySelector('.chatbot-input');
    if (textarea) {
      textarea.style.height = 'auto';
    }

    try {
      // Call the unified /chat endpoint
      const response = await axios.post(
        `${API_URL}/chat`,
        {
          message: messageText,
          session_id: sessionId
        }
      );

      const data = response.data;
      
      // Store session ID for future messages
      if (data.session_id && !sessionId) {
        setSessionId(data.session_id);
      }

      if (data.data?.recommendations?.length) {
        const counts = {};
        data.data.recommendations.forEach((product) => {
          const normalized = CATEGORY_LABELS[product.category] ? product.category : 'accessories';
          counts[normalized] = (counts[normalized] || 0) + 1;
        });
        setCategoryStats(counts);
        
        // Update the main page with recommended products
        if (onRecommendations) {
          onRecommendations(data.data.recommendations);
        }
      } else if (data.data?.product) {
        // Handle single product recommendation
        if (onRecommendations) {
          onRecommendations([data.data.product]);
        }
      } else {
        setCategoryStats({});
        // Clear recommendations if no products are returned
        if (onRecommendations) {
          onRecommendations([]);
        }
      }

      // Create bot response with product info if available
      const botMessage = {
        id: `bot-${Date.now()}`,
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
      
      if (error.response?.data?.detail) {
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
    <>
      {/* Toggle Button */}
      <button 
        className={`chatbot-toggle ${isSidebarOpen ? 'open' : ''}`}
        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
        aria-label="Toggle chat sidebar"
      >
        {isSidebarOpen ? <FiX size={24} /> : <FiMessageCircle size={24} />}
      </button>

      {/* Sidebar */}
      <div className={`chatbot-container ${isSidebarOpen ? 'open' : 'closed'}`}>
        <div className="chatbot-window">
          <div className="chatbot-category-strip">
            {CATEGORY_SHORTCUTS.map((item) => (
              <button
                key={item.key}
                className="category-chip"
                type="button"
                onClick={() => handleCategoryClick(item.prompt)}
              >
                <span className="category-label">{item.label}</span>
                {categoryStats[item.key] && (
                  <span className="category-count">{categoryStats[item.key]}</span>
                )}
              </button>
            ))}
          </div>
          <div className="chatbot-header">
            <div className="chatbot-header-content">
              <FiMessageCircle size={20} />
              <div>
                <h3>🤖 AI Shopping Assistant</h3>
                <span className="status-indicator">
                  ✓ Ready to help
                </span>
              </div>
            </div>
            <button 
              className="close-btn"
              onClick={() => setIsSidebarOpen(false)}
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
            <textarea
              placeholder="Type your message... (Shift+Enter for new line)"
              value={inputMessage}
              onChange={handleInputChange}
              onKeyPress={handleKeyPress}
              className="chatbot-input"
              rows="1"
            />
            <button 
              type="submit"
              className="send-btn"
              disabled={!inputMessage.trim()}
              aria-label="Send message"
            >
              <FiSend size={18} />
            </button>
          </form>
        </div>
      </div>
    </>
  );
};

export default Chatbot;

