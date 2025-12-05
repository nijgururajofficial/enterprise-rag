import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FiPackage, FiRefreshCw, FiClock, FiAlertCircle } from 'react-icons/fi';
import './Orders.css';

const API_URL = 'http://localhost:8000';

const Orders = () => {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchOrders = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
            setError('Please log in to view your orders.');
            setLoading(false);
            return;
        }
        
        const response = await axios.get(`${API_URL}/orders`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        // Sort orders by date descending
        const sortedOrders = response.data.sort((a, b) => 
            new Date(b.order_date) - new Date(a.order_date)
        );
        setOrders(sortedOrders);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching orders:', err);
        setError('Failed to load orders.');
        setLoading(false);
      }
    };

    fetchOrders();
  }, []);

  if (loading) {
    return (
      <div className="orders-page container">
        <div className="loading-state">Loading orders...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="orders-page container">
        <div className="error-state">
            <FiAlertCircle size={24} />
            <p>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="orders-page container">
      <h1 className="page-title">My Orders</h1>
      
      <div className="orders-content">
        <div className="orders-list-section">
            {orders.length === 0 ? (
                <div className="empty-orders">
                    <FiPackage size={48} />
                    <p>You haven't placed any orders yet.</p>
                </div>
            ) : (
                <div className="orders-list">
                {orders.map(order => (
                    <div key={order.order_id} className="order-card">
                        <div className="order-header">
                            <div className="order-info">
                                <span className="order-id">Order #{order.order_id}</span>
                                <span className="order-date">
                                    {order.order_date ? new Date(order.order_date).toLocaleDateString() : 'N/A'}
                                </span>
                            </div>
                            <span className={`status-badge status-${order.status.toLowerCase()}`}>
                                {order.status}
                            </span>
                        </div>
                        <div className="order-body">
                            <div className="order-items-count">
                                {Object.values(order.items || {}).reduce((a, b) => a + b, 0)} Items
                            </div>
                            <div className="order-total">
                                Total: ${order.total_amount?.toFixed(2)}
                            </div>
                        </div>
                    </div>
                ))}
                </div>
            )}
        </div>

        <div className="returns-section">
            <h2>Returns & Refunds</h2>
            <div className="returns-card">
                <p className="returns-intro">Need to return an item? Our AI-powered system makes it easy.</p>
                
                <div className="return-steps">
                    <div className="return-step">
                        <div className="step-icon"><FiAlertCircle /></div>
                        <div className="step-text">
                            <strong>Problem with your order?</strong>
                            <p>Defective item or damaged box?</p>
                        </div>
                    </div>
                    <div className="return-step">
                        <div className="step-icon"><FiRefreshCw /></div>
                        <div className="step-text">
                            <strong>Use the Chatbot</strong>
                            <p>Upload a photo of the issue to get an instant decision.</p>
                        </div>
                    </div>
                    <div className="return-step">
                        <div className="step-icon"><FiClock /></div>
                        <div className="step-text">
                            <strong>Quick Resolution</strong>
                            <p>Get a refund, replacement, or agent support.</p>
                        </div>
                    </div>
                </div>
                
                <div className="returns-note">
                    <small>Note: Fraudulent claims are detected using advanced AI analysis.</small>
                </div>
            </div>
        </div>
      </div>
    </div>
  );
};

export default Orders;

