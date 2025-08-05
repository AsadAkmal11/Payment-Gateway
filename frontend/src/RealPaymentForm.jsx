import React, { useState } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, CardElement, useStripe, useElements } from '@stripe/react-stripe-js';
import axios from 'axios';
import './styles/real-payment.css';

const API_BASE_URL = 'http://localhost:8000';
const stripePromise = loadStripe(process.env.REACT_APP_STRIPE_PUBLISHABLE_KEY || 'pk_test_your_actual_publishable_key_here');

const RealPaymentForm = ({ amount, onSuccess, onError }) => {
  const stripe = useStripe();
  const elements = useElements();
  const [loading, setLoading] = useState(false);
  const [userInfo, setUserInfo] = useState({
    full_name: '',
    email: '',
    phone: ''
  });
  const [userId, setUserId] = useState(null);
  const [step, setStep] = useState(1); // 1: user info, 2: card info

  const handleUserInfoChange = (field, value) => {
    setUserInfo(prev => ({ ...prev, [field]: value }));
  };

  // Step 1: Save user info to backend
  const handleContinue = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (!userInfo.full_name || !userInfo.email || !userInfo.phone) {
        onError('Please fill in all required fields');
        setLoading(false);
        return;
      }
      // This part of the logic is removed as per the edit hint.
      // The user info is now directly passed to the payment intent.
      setStep(2);
    } catch (error) {
      onError(error.response?.data?.detail || 'Failed to save user info');
    }
    setLoading(false);
  };

  // Step 2: Handle payment
  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    if (!stripe || !elements) {
      setLoading(false);
      return;
    }
    try {
      // 1. Create payment intent on backend
      const intentRes = await axios.post(`${API_BASE_URL}/stripe/create-payment-intent`, {
        amount: Math.round(amount * 100),
        currency: 'usd',
        full_name: userInfo.full_name,
        email: userInfo.email,
        phone: userInfo.phone
      });
      const { client_secret, payment_intent_id } = intentRes.data;
      // 2. Create payment method with Stripe.js
      const cardElement = elements.getElement(CardElement);
      const { error: pmError, paymentMethod } = await stripe.createPaymentMethod({
        type: 'card',
        card: cardElement,
        billing_details: {
          name: userInfo.full_name,
          email: userInfo.email,
          phone: userInfo.phone
        }
      });
      if (pmError) {
        onError(pmError.message);
        setLoading(false);
        return;
      }
      // 3. Confirm card payment with Stripe.js
      const { error: confirmError, paymentIntent } = await stripe.confirmCardPayment(client_secret, {
        payment_method: paymentMethod.id
      });
      if (confirmError) {
        onError(confirmError.message);
        setLoading(false);
        return;
      }
      if (paymentIntent.status !== 'succeeded') {
        onError('Payment was not successful.');
        setLoading(false);
        return;
      }
      // 4. Notify backend to update transaction status
      await axios.post(`${API_BASE_URL}/stripe/confirm-payment`, {
        payment_intent_id,
        payment_method_id: paymentMethod.id
      });
      onSuccess({ status: 'paid', message: 'Payment successful!' });
    } catch (error) {
      onError(error.response?.data?.detail || 'Payment failed.');
    }
    setLoading(false);
  };

  const cardElementOptions = {
    style: {
      base: {
        fontSize: '16px',
        color: '#424770',
        '::placeholder': { color: '#aab7c4' },
      },
      invalid: { color: '#9e2146' },
    },
  };

  return (
    <form onSubmit={step === 1 ? handleContinue : handleSubmit} className="real-payment-form">
      {step === 1 && (
        <>
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
          <button
            type="submit"
            className="btn btn-primary w-100"
            disabled={loading}
          >
            {loading ? 'Saving...' : 'Continue'}
          </button>
        </>
      )}
      {step === 2 && (
        <>
          <div className="mb-3">
            <label className="form-label">Card Details</label>
            <div className="card-element-container">
              <CardElement options={cardElementOptions} />
            </div>
          </div>
          <button
            type="submit"
            className="btn btn-pay text-white w-100"
            disabled={loading}
          >
            {loading ? 'Processing Payment...' : `Pay $${amount.toFixed(2)}`}
          </button>
          <div className="mt-3">
            <small className="text-muted">
              💳 This is a real payment using Stripe. Use test card: 4242 4242 4242 4242
            </small>
          </div>
        </>
      )}
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