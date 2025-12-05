import React, { useState, useRef, useEffect } from 'react';
import { FiMessageCircle, FiX, FiSend, FiShoppingCart, FiImage, FiXCircle } from 'react-icons/fi';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useSidebar } from '../App';
import { useAuth } from '../context/AuthContext';
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
  const { user } = useAuth();
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
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const fileInputRef = useRef(null);
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

  const handleImageSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      if (!file.type.startsWith('image/')) {
        alert('Please select an image file');
        return;
      }
      
      // Validate file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        alert('Image size should be less than 10MB');
        return;
      }

      setSelectedImage(file);
      
      // Create preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleRemoveImage = () => {
    setSelectedImage(null);
    setImagePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const detectImageType = (message) => {
    const messageLower = message.toLowerCase();
    if (messageLower.includes('defect') || messageLower.includes('broken') || 
        messageLower.includes('damaged product') || messageLower.includes('faulty')) {
      return 'product_defect';
    } else if (messageLower.includes('damaged box') || messageLower.includes('shipping box') || 
               messageLower.includes('package box') || messageLower.includes('delivery box')) {
      return 'damaged_shipping_box';
    } else if (messageLower.includes('fraud') || messageLower.includes('fraudulent') || 
               messageLower.includes('unauthorized') || messageLower.includes('credit card') || 
               messageLower.includes('transaction')) {
      return 'fraudulent_transaction_ocr';
    }
    return null;
  };

  const handleSendMessage = async (e, overrideMessage) => {
    if (e?.preventDefault) {
      e.preventDefault();
    }

    const messageText = (overrideMessage ?? inputMessage).trim();
    if (!messageText && !selectedImage) return;

    const userMessage = {
      id: `user-${Date.now()}`,
      text: messageText || (selectedImage ? '📷 [Image attached]' : ''),
      sender: 'user',
      timestamp: new Date(),
      image: imagePreview
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
      let response;
      const token = localStorage.getItem('token');
      const authHeaders = token ? { 'Authorization': `Bearer ${token}` } : {};
      
      // If image is selected, use form-data upload endpoint
      if (selectedImage) {
        const formData = new FormData();
        formData.append('message', messageText || '');
        formData.append('image', selectedImage);
        if (sessionId) {
          formData.append('session_id', sessionId);
        }
        
        // Auto-detect image type if not explicitly set
        const imageType = detectImageType(messageText);
        if (imageType) {
          formData.append('image_type', imageType);
        }
        
        // No need to append user_id manually if we use token
        
        response = await axios.post(
          `${API_URL}/chat/upload`,
          formData,
          {
            headers: {
              'Content-Type': 'multipart/form-data',
              ...authHeaders
            }
          }
        );
        
        // Clear image after sending
        handleRemoveImage();
      } else {
        // Regular text message
        const payload = {
            message: messageText,
            session_id: sessionId
        };
        // No need to append user_id manually if we use token

        response = await axios.post(
          `${API_URL}/chat`,
          payload,
          { headers: authHeaders }
        );
      }

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
    return (
      <div className="message-content">
        <div className="message-text">
          <ReactMarkdown 
            remarkPlugins={[remarkGfm]}
            components={{
              // Customize rendering for specific elements
              p: ({node, ...props}) => <p style={{margin: '0.5em 0'}} {...props} />,
              ul: ({node, ...props}) => <ul style={{marginLeft: '1.5em', marginTop: '0.5em'}} {...props} />,
              ol: ({node, ...props}) => <ol style={{marginLeft: '1.5em', marginTop: '0.5em'}} {...props} />,
              li: ({node, ...props}) => <li style={{marginBottom: '0.25em'}} {...props} />,
              strong: ({node, ...props}) => <strong style={{fontWeight: '600', color: 'inherit'}} {...props} />,
              em: ({node, ...props}) => <em style={{fontStyle: 'italic'}} {...props} />,
              h1: ({node, ...props}) => <h1 style={{fontSize: '1.5em', marginTop: '0.5em', marginBottom: '0.5em'}} {...props} />,
              h2: ({node, ...props}) => <h2 style={{fontSize: '1.3em', marginTop: '0.5em', marginBottom: '0.5em'}} {...props} />,
              h3: ({node, ...props}) => <h3 style={{fontSize: '1.1em', marginTop: '0.5em', marginBottom: '0.5em'}} {...props} />,
              code: ({node, inline, ...props}) => 
                inline 
                  ? <code style={{backgroundColor: 'rgba(0,0,0,0.1)', padding: '0.2em 0.4em', borderRadius: '3px'}} {...props} />
                  : <code style={{display: 'block', backgroundColor: 'rgba(0,0,0,0.1)', padding: '0.8em', borderRadius: '5px', overflowX: 'auto'}} {...props} />,
            }}
          >
            {message.text}
          </ReactMarkdown>
        </div>
        
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

        {/* Display action result cards (refund/replace/escalate) */}
        {message.data?.action && (
          <div className={`action-card action-${message.data.action}`}>
            <div className="action-header">
              {message.data.action === 'refund' && '💰 Refund Approved'}
              {message.data.action === 'replace' && '🔄 Replacement Approved'}
              {message.data.action === 'escalate' && '👤 Escalated to Support'}
              {message.data.action === 'decline' && '❌ Request Declined'}
            </div>
            {message.data.analysis && (
              <div className="action-details">
                {message.data.analysis.reason && (
                  <div className="action-reason">
                    <strong>Reason:</strong> {message.data.analysis.reason}
                  </div>
                )}
                {message.data.case_id && (
                  <div className="action-case-id">
                    <strong>Case ID:</strong> {message.data.case_id}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Display uploaded image in user messages */}
        {message.image && (
          <div className="message-image-preview">
            <img src={message.image} alt="Uploaded" />
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

          {/* Image Preview */}
          {imagePreview && (
            <div className="image-preview-container">
              <div className="image-preview">
                <img src={imagePreview} alt="Preview" />
                <button 
                  className="remove-image-btn"
                  onClick={handleRemoveImage}
                  aria-label="Remove image"
                >
                  <FiXCircle size={20} />
                </button>
              </div>
            </div>
          )}

          <form className="chatbot-input-container" onSubmit={handleSendMessage}>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleImageSelect}
              accept="image/*"
              style={{ display: 'none' }}
              id="image-upload"
            />
            <label htmlFor="image-upload" className="attach-image-btn" title="Attach image">
              <FiImage size={20} />
            </label>
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
              disabled={!inputMessage.trim() && !selectedImage}
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

