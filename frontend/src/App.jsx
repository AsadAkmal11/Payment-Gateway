import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

// Backend API URL
const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    phone: '',
    amount: ''
  });
  
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('');

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      console.log('Sending payment data:', formData);
      
      const response = await axios.post(`${API_BASE_URL}/transactions/create`, {
        full_name: formData.full_name,
        email: formData.email,
        phone: formData.phone,
        amount: parseFloat(formData.amount)
      }, {
        headers: {
          'Content-Type': 'application/json',
        }
      });

      console.log('Payment response:', response.data);

      setMessageType('success');
      setMessage(`Payment successful! Transaction Reference: ${response.data.reference}`);
      
      // Reset form
      setFormData({
        full_name: '',
        email: '',
        phone: '',
        amount: ''
      });
    } catch (error) {
      console.error('Payment error:', error);
      setMessageType('error');
      
      if (error.response) {
        // Server responded with error
        setMessage(`Payment failed: ${error.response.data?.detail || error.response.statusText}`);
      } else if (error.request) {
        // Network error - backend not reachable
        setMessage('Cannot connect to payment server. Please check if the backend is running on http://localhost:8000');
      } else {
        // Other error
        setMessage('Payment failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="payment-container">
      <div className="payment-card">
        <div className="payment-header">
          <h1>💳 Payment Gateway</h1>
          <p>Secure and fast online payments</p>
        </div>

        {message && (
          <div className={`alert ${messageType === 'success' ? 'success-alert' : 'error-alert'} mb-4`}>
            {message}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-3">
            <label htmlFor="full_name" className="form-label">
              Full Name
            </label>
            <input
              type="text"
              className="form-control"
              id="full_name"
              name="full_name"
              value={formData.full_name}
              onChange={handleInputChange}
              required
              placeholder="Enter your full name"
            />
          </div>

          <div className="mb-3">
            <label htmlFor="email" className="form-label">
              Email Address
            </label>
            <input
              type="email"
              className="form-control"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleInputChange}
              required
              placeholder="Enter your email"
            />
          </div>

          <div className="mb-3">
            <label htmlFor="phone" className="form-label">
              Phone Number
            </label>
            <input
              type="tel"
              className="form-control"
              id="phone"
              name="phone"
              value={formData.phone}
              onChange={handleInputChange}
              required
              placeholder="Enter your phone number"
            />
          </div>

          <div className="mb-4">
            <label htmlFor="amount" className="form-label">
              Payment Amount
            </label>
            <div className="input-group">
              <span className="input-group-text">$</span>
              <input
                type="number"
                className="form-control"
                id="amount"
                name="amount"
                value={formData.amount}
                onChange={handleInputChange}
                required
                min="0.01"
                step="0.01"
                placeholder="0.00"
              />
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-pay text-white w-100"
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="loading-spinner me-2"></span>
                Processing...
              </>
            ) : (
              'Pay Now'
            )}
          </button>
        </form>

        <div className="text-center mt-4">
          <small className="text-muted">
            🔒 Your payment information is secure and encrypted
          </small>
        </div>
        
        <div className="text-center mt-2">
          <small className="text-muted">
            Backend: {API_BASE_URL}
          </small>
        </div>
      </div>
    </div>
  );
}

export default App; 