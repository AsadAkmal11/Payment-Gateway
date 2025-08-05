import React, { useState, useEffect } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, CardElement, useStripe, useElements } from '@stripe/react-stripe-js';
import axios from 'axios';
import './styles/real-payment.css';

// Backend API URL
const API_BASE_URL = 'http://localhost:8000';

// Load Stripe (replace with your publishable key)
const stripePromise = loadStripe('pk_test_your_publishable_key_here');

const RealPaymentForm = ({ amount, onSuccess, onError }) => {
  const stripe = useStripe();
  const elements = useElements();
  const [loading, setLoading] = useState(false);
  const [clientSecret, setClientSecret] = useState('');
  const [userInfo, setUserInfo] = useState({
    full_name: '',
    email: '',
    phone: ''
  });

  const handleUserInfoChange = (field, value) => {
    setUserInfo(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const createPaymentIntent = async () => {
    try {
      // Validate user information
      if (!userInfo.full_name || !userInfo.email || !userInfo.phone) {
        onError('Please fill in all required fields');
        return;
      }

      const response = await axios.post(`${API_BASE_URL}/stripe/create-payment-intent`, {
        amount: Math.round(amount * 100), // Convert to cents
        currency: 'usd',
        full_name: userInfo.full_name,
        email: userInfo.email,
        phone: userInfo.phone
      });

      if (response.data.success) {
        setClientSecret(response.data.client_secret);
      } else {
        onError('Failed to initialize payment');
      }
    } catch (error) {
      console.error('Error creating payment intent:', error);
      onError(error.response?.data?.detail || 'Failed to initialize payment');
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);

    if (!stripe || !elements) {
      return;
    }

    const { error, paymentIntent } = await stripe.confirmCardPayment(clientSecret, {
      payment_method: {
        card: elements.getElement(CardElement),
        billing_details: {
          name: userInfo.full_name,
          email: userInfo.email,
          phone: userInfo.phone
        }
      }
    });

    if (error) {
      console.error('Payment failed:', error);
      onError(error.message);
      setLoading(false);
    } else {
      if (paymentIntent.status === 'succeeded') {
        // Get transaction details from our backend
        try {
          const response = await axios.get(`${API_BASE_URL}/stripe/transactions/${paymentIntent.metadata.transaction_id || 'unknown'}`);
          
          onSuccess({
            transaction_id: response.data.transaction?.transaction_id || paymentIntent.id,
            amount: response.data.transaction?.amount || amount,
            status: response.data.transaction?.status || 'completed',
            stripe_payment_intent_id: paymentIntent.id
          });
        } catch (error) {
          console.error('Error getting transaction details:', error);
          onSuccess({
            transaction_id: paymentIntent.id,
            amount: amount,
            status: 'completed',
            stripe_payment_intent_id: paymentIntent.id
          });
        }
      }
      setLoading(false);
    }
  };

  const cardElementOptions = {
    style: {
      base: {
        fontSize: '16px',
        color: '#424770',
        '::placeholder': {
          color: '#aab7c4',
        },
      },
      invalid: {
        color: '#9e2146',
      },
    },
  };

  return (
    <form onSubmit={handleSubmit} className="real-payment-form">
      {/* User Information Fields */}
      <div className="mb-3">
        <label className="form-label">Full Name *</label>
        <input
          type="text"
          className="form-control"
          value={userInfo.full_name}
          onChange={(e) => handleUserInfoChange('full_name', e.target.value)}
          required
        />
      </div>
      
      <div className="mb-3">
        <label className="form-label">Email *</label>
        <input
          type="email"
          className="form-control"
          value={userInfo.email}
          onChange={(e) => handleUserInfoChange('email', e.target.value)}
          required
        />
      </div>
      
      <div className="mb-3">
        <label className="form-label">Phone *</label>
        <input
          type="tel"
          className="form-control"
          value={userInfo.phone}
          onChange={(e) => handleUserInfoChange('phone', e.target.value)}
          required
        />
      </div>

      <div className="mb-3">
        <label className="form-label">Card Details</label>
        <div className="card-element-container">
          <CardElement options={cardElementOptions} />
        </div>
      </div>
      
      <button
        type="submit"
        disabled={!stripe || loading || !clientSecret}
        className="btn btn-pay text-white w-100"
        onClick={createPaymentIntent}
      >
        {loading ? (
          <>
            <span className="loading-spinner me-2"></span>
            Processing Payment...
          </>
        ) : (
          `Pay $${amount.toFixed(2)}`
        )}
      </button>
      
      <div className="mt-3">
        <small className="text-muted">
          💳 This is a real payment using Stripe. Use test card: 4242 4242 4242 4242
        </small>
      </div>
    </form>
  );
};

const RealPaymentWrapper = ({ amount, onSuccess, onError }) => {
  return (
    <Elements stripe={stripePromise}>
      <RealPaymentForm 
        amount={amount} 
        onSuccess={onSuccess} 
        onError={onError} 
      />
    </Elements>
  );
};

export default RealPaymentWrapper; 