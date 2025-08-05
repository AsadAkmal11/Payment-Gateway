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

  useEffect(() => {
    // Create PaymentIntent as soon as the page loads
    createPaymentIntent();
  }, [amount]);

  const createPaymentIntent = async () => {
    try {
      const response = await axios.post(`${API_BASE_URL}/create-payment-intent`, {
        amount: amount,
        currency: 'usd'
      });
      setClientSecret(response.data.client_secret);
    } catch (error) {
      console.error('Error creating payment intent:', error);
      onError('Failed to initialize payment');
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
      }
    });

    if (error) {
      console.error('Payment failed:', error);
      onError(error.message);
      setLoading(false);
    } else {
      if (paymentIntent.status === 'succeeded') {
        // Process the successful payment on your backend
        try {
          const response = await axios.post(`${API_BASE_URL}/process-real-payment`, {
            payment_intent_id: paymentIntent.id
          });
          
          onSuccess({
            transaction_id: response.data.transaction_id,
            amount: response.data.amount,
            status: response.data.status
          });
        } catch (error) {
          console.error('Error processing payment:', error);
          onError('Payment succeeded but failed to record transaction');
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
      <div className="mb-3">
        <label className="form-label">Card Details</label>
        <div className="card-element-container">
          <CardElement options={cardElementOptions} />
        </div>
      </div>
      
      <button
        type="submit"
        disabled={!stripe || loading}
        className="btn btn-pay text-white w-100"
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