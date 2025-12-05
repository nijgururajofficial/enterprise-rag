import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiCreditCard, FiMapPin, FiUser, FiCheck } from 'react-icons/fi';
import axios from 'axios';
import { useCart } from '../context/CartContext';
import { useAuth } from '../context/AuthContext';
import { toast } from 'react-toastify';
import './Checkout.css';

const Checkout = () => {
  const [formData, setFormData] = useState({
    shippingAddress: '',
    paymentMethod: 'credit-card',
    cardNumber: '',
    expiryDate: '',
    cvv: '',
    cardName: '',
  });
  const [loading, setLoading] = useState(false);
  const [orderComplete, setOrderComplete] = useState(false);
  const [orderId, setOrderId] = useState('');

  const { cart, clearCart } = useCart();
  const { user } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!cart.items || cart.items.length === 0) {
      toast.error('Your cart is empty');
      navigate('/cart');
      return;
    }

    setLoading(true);

    try {
      // Ensure the server has the latest cart (backend is in-memory; it can reset)
      const serverCart = await axios.get('http://localhost:8000/cart');
      if (!serverCart.data?.items || serverCart.data.items.length === 0) {
        toast.error('Your server cart is empty. Please re-add items.');
        navigate('/cart');
        return;
      }

      const response = await axios.post('http://localhost:8000/checkout', {
        shipping_address: formData.shippingAddress || user?.address || '',
        payment_method: formData.paymentMethod,
      });

      setOrderId(response.data.order_id);
      setOrderComplete(true);
      clearCart();
      toast.success('Order placed successfully!');
    } catch (error) {
      console.error('Checkout error:', error);
      toast.error(error.response?.data?.detail || 'Failed to place order');
    } finally {
      setLoading(false);
    }
  };

  if (orderComplete) {
    return (
      <div className="checkout-page">
        <div className="container">
          <div className="order-success">
            <div className="success-icon">
              <FiCheck size={64} />
            </div>
            <h1 className="success-title">Order Placed Successfully!</h1>
            <p className="success-description">
              Thank you for your purchase. Your order ID is: <strong>{orderId}</strong>
            </p>
            <div className="success-actions">
              <button
                onClick={() => navigate('/products')}
                className="btn btn-primary"
              >
                Continue Shopping
              </button>
              <button
                onClick={() => navigate('/')}
                className="btn btn-outline"
              >
                Back to Home
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!cart.items || cart.items.length === 0) {
    return (
      <div className="checkout-page">
        <div className="container">
          <div className="empty-checkout">
            <h2>Your cart is empty</h2>
            <p>Add some items to your cart before checking out.</p>
            <button
              onClick={() => navigate('/products')}
              className="btn btn-primary"
            >
              Start Shopping
            </button>
          </div>
        </div>
      </div>
    );
  }

  const subtotal = cart.total;
  const tax = subtotal * 0.08;
  const total = subtotal + tax;

  return (
    <div className="checkout-page">
      <div className="container">
        <div className="checkout-header">
          <h1 className="checkout-title">Checkout</h1>
          <p className="checkout-subtitle">Complete your purchase</p>
        </div>

        <div className="checkout-content">
          <div className="checkout-form-section">
            <form onSubmit={handleSubmit} className="checkout-form">
              {/* Shipping Information */}
              <div className="form-section">
                <h3 className="form-section-title">
                  <FiMapPin size={20} />
                  Shipping Information
                </h3>
                <div className="form-group">
                  <label htmlFor="shippingAddress" className="form-label">
                    Shipping Address
                  </label>
                  <textarea
                    id="shippingAddress"
                    name="shippingAddress"
                    value={formData.shippingAddress}
                    onChange={handleChange}
                    className="form-input form-textarea"
                    placeholder={user?.address || "Enter your shipping address"}
                    rows={3}
                    required
                  />
                </div>
              </div>

              {/* Payment Information */}
              <div className="form-section">
                <h3 className="form-section-title">
                  <FiCreditCard size={20} />
                  Payment Information
                </h3>
                
                <div className="form-group">
                  <label className="form-label">Payment Method</label>
                  <div className="payment-methods">
                    <label className="payment-method">
                      <input
                        type="radio"
                        name="paymentMethod"
                        value="credit-card"
                        checked={formData.paymentMethod === 'credit-card'}
                        onChange={handleChange}
                      />
                      <span>Credit Card</span>
                    </label>
                    <label className="payment-method">
                      <input
                        type="radio"
                        name="paymentMethod"
                        value="paypal"
                        checked={formData.paymentMethod === 'paypal'}
                        onChange={handleChange}
                      />
                      <span>PayPal</span>
                    </label>
                    <label className="payment-method">
                      <input
                        type="radio"
                        name="paymentMethod"
                        value="apple-pay"
                        checked={formData.paymentMethod === 'apple-pay'}
                        onChange={handleChange}
                      />
                      <span>Apple Pay</span>
                    </label>
                  </div>
                </div>

                {formData.paymentMethod === 'credit-card' && (
                  <>
                    <div className="form-group">
                      <label htmlFor="cardName" className="form-label">
                        <FiUser size={16} />
                        Cardholder Name
                      </label>
                      <input
                        type="text"
                        id="cardName"
                        name="cardName"
                        value={formData.cardName}
                        onChange={handleChange}
                        className="form-input"
                        placeholder="John Doe"
                        required
                      />
                    </div>

                    <div className="form-group">
                      <label htmlFor="cardNumber" className="form-label">
                        Card Number
                      </label>
                      <input
                        type="text"
                        id="cardNumber"
                        name="cardNumber"
                        value={formData.cardNumber}
                        onChange={handleChange}
                        className="form-input"
                        placeholder="1234 5678 9012 3456"
                        required
                      />
                    </div>

                    <div className="form-row">
                      <div className="form-group">
                        <label htmlFor="expiryDate" className="form-label">
                          Expiry Date
                        </label>
                        <input
                          type="text"
                          id="expiryDate"
                          name="expiryDate"
                          value={formData.expiryDate}
                          onChange={handleChange}
                          className="form-input"
                          placeholder="MM/YY"
                          required
                        />
                      </div>
                      <div className="form-group">
                        <label htmlFor="cvv" className="form-label">
                          CVV
                        </label>
                        <input
                          type="text"
                          id="cvv"
                          name="cvv"
                          value={formData.cvv}
                          onChange={handleChange}
                          className="form-input"
                          placeholder="123"
                          required
                        />
                      </div>
                    </div>
                  </>
                )}
              </div>

              <button
                type="submit"
                className="place-order-btn"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <div className="spinner-small"></div>
                    Processing...
                  </>
                ) : (
                  `Place Order - $${total.toFixed(2)}`
                )}
              </button>
            </form>
          </div>

          <div className="order-summary-section">
            <div className="order-summary-card">
              <h3 className="order-summary-title">Order Summary</h3>
              
              <div className="order-items">
                {cart.items.map((item) => (
                  <div key={item.product.id} className="order-item">
                    <div className="order-item-image">
                      <img src={item.product.image} alt={item.product.name} />
                    </div>
                    <div className="order-item-details">
                      <h4 className="order-item-name">{item.product.name}</h4>
                      <p className="order-item-quantity">Qty: {item.quantity}</p>
                    </div>
                    <div className="order-item-price">
                      ${item.item_total.toFixed(2)}
                    </div>
                  </div>
                ))}
              </div>

              <div className="order-totals">
                <div className="total-row">
                  <span>Subtotal</span>
                  <span>${subtotal.toFixed(2)}</span>
                </div>
                <div className="total-row">
                  <span>Shipping</span>
                  <span>Free</span>
                </div>
                <div className="total-row">
                  <span>Tax</span>
                  <span>${tax.toFixed(2)}</span>
                </div>
                <div className="total-divider"></div>
                <div className="total-row total-final">
                  <span>Total</span>
                  <span>${total.toFixed(2)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Checkout;
