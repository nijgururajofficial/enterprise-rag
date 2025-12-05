import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FiAlertCircle, FiClock, FiCheckCircle, FiXCircle } from 'react-icons/fi';
import './Orders.css'; // Reuse Orders CSS for consistency

const API_URL = 'http://localhost:8000';

const Complaints = () => {
  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchComplaints = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
            setError('Please log in to view your complaints.');
            setLoading(false);
            return;
        }
        
        const response = await axios.get(`${API_URL}/complaints`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        // Sort by date descending
        const sorted = response.data.sort((a, b) => 
            new Date(b.created_at) - new Date(a.created_at)
        );
        setComplaints(sorted);
        setLoading(false);
      } catch (err) {
        console.error('Error fetching complaints:', err);
        setError('Failed to load complaints.');
        setLoading(false);
      }
    };

    fetchComplaints();
  }, []);

  const getStatusBadge = (status) => {
    switch (status?.toLowerCase()) {
      case 'resolved':
        return <span className="status-badge status-confirmed"><FiCheckCircle /> Resolved</span>;
      case 'escalated':
      case 'open':
        return <span className="status-badge status-pending"><FiClock /> In Progress</span>;
      case 'declined':
        return <span className="status-badge status-cancelled"><FiXCircle /> Closed</span>;
      default:
        return <span className="status-badge">{status}</span>;
    }
  };

  if (loading) {
    return <div className="orders-page container"><div className="loading-state">Loading cases...</div></div>;
  }

  if (error) {
    return <div className="orders-page container"><div className="error-state"><FiAlertCircle /> {error}</div></div>;
  }

  return (
    <div className="orders-page container">
      <h1 className="page-title">My Support Cases</h1>
      
      <div className="orders-content">
        <div className="orders-list-section">
            {complaints.length === 0 ? (
                <div className="empty-orders">
                    <FiAlertCircle size={48} />
                    <p>You don't have any active support cases.</p>
                </div>
            ) : (
                <div className="orders-list">
                {complaints.map(ticket => (
                    <div key={ticket.id} className="order-card">
                        <div className="order-header">
                            <div className="order-info">
                                <span className="order-id">Case #{ticket.id}</span>
                                <span className="order-date">
                                    {new Date(ticket.created_at).toLocaleDateString()} • {new Date(ticket.created_at).toLocaleTimeString()}
                                </span>
                            </div>
                            {getStatusBadge(ticket.status)}
                        </div>
                        <div className="order-body" style={{display: 'block'}}>
                            <div className="order-items-count" style={{marginBottom: '0.5rem'}}>
                                <strong>Issue:</strong> {ticket.issue_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                            </div>
                            <div className="ticket-description" style={{color: '#4a5568', fontSize: '0.95rem'}}>
                                {ticket.description}
                            </div>
                            {ticket.resolution && (
                                <div className="ticket-resolution" style={{marginTop: '1rem', padding: '0.75rem', background: '#f7fafc', borderRadius: '4px'}}>
                                    <strong>Resolution:</strong> {ticket.resolution}
                                </div>
                            )}
                        </div>
                    </div>
                ))}
                </div>
            )}
        </div>

        <div className="returns-section">
            <h2>Support Center</h2>
            <div className="returns-card">
                <p className="returns-intro">Track the status of your support requests here.</p>
                <div className="return-steps">
                    <div className="return-step">
                        <div className="step-icon"><FiClock /></div>
                        <div className="step-text">
                            <strong>Response Time</strong>
                            <p>We typically respond to escalated cases within 24 hours.</p>
                        </div>
                    </div>
                    <div className="return-step">
                        <div className="step-icon"><FiAlertCircle /></div>
                        <div className="step-text">
                            <strong>Need Help?</strong>
                            <p>Use the chatbot to report new issues or check status.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
      </div>
    </div>
  );
};

export default Complaints;
