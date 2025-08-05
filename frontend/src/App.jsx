import React, { useState } from 'react';
import axios from 'axios';
import './styles/main.css';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, CardElement, useStripe, useElements } from '@stripe/react-stripe-js';

// Backend API URL
const API_BASE_URL = 'http://localhost:8000';

function PaymentForm({ formData, setFormData, paymentData, setPaymentData, setMessage, setMessageType, setLoading, setStep }) {
  const stripe = useStripe();
  const elements = useElements();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');
    try {
      // 1. Create payment intent
      const intentRes = await axios.post(`${API_BASE_URL}/stripe/create-payment-intent`, {
        amount: Math.round(formData.amount * 100),
        currency: 'usd',
        full_name: formData.full_name,
        email: formData.email,
        phone: formData.phone
      });
      const { client_secret, payment_intent_id } = intentRes.data;

      // 2. Create payment method with Stripe.js
      const cardElement = elements.getElement(CardElement);
      const { error: pmError, paymentMethod } = await stripe.createPaymentMethod({
        type: 'card',
        card: cardElement,
        billing_details: {
          name: formData.full_name,
          email: formData.email,
          phone: formData.phone
        }
      });
      if (pmError) {
        setMessageType('error');
        setMessage(pmError.message);
        setLoading(false);
        return;
      }

      // 3. Confirm card payment with Stripe.js
      const { error: confirmError, paymentIntent } = await stripe.confirmCardPayment(client_secret, {
        payment_method: paymentMethod.id
      });
      if (confirmError) {
        setMessageType('error');
        setMessage(confirmError.message);
        setLoading(false);
        return;
      }
      if (paymentIntent.status !== 'succeeded') {
        setMessageType('error');
        setMessage('Payment was not successful.');
        setLoading(false);
        return;
      }

      // 4. Notify backend to update transaction status
      await axios.post(`${API_BASE_URL}/stripe/confirm-payment`, {
        payment_intent_id,
        payment_method_id: paymentMethod.id
      });
      setMessageType('success');
      setMessage('Payment successful!');
      setFormData({ full_name: '', email: '', phone: '', amount: '' });
      setPaymentData({ payment_method: 'visa', card_number: '', expiry_month: '', expiry_year: '', cvv: '', cardholder_name: '' });
      setStep(1);
    } catch (error) {
      setMessageType('error');
      setMessage(error.response?.data?.detail || 'Payment failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Render CardElement and other form fields as needed */}
      <div className="mb-3">
        <label className="form-label">Card Details</label>
        <CardElement />
      </div>
      <button type="submit" className="btn btn-pay text-white" disabled={setLoading}>
        PAY NOW
      </button>
    </form>
  );
}

function App() {
  const [step, setStep] = useState(1); // 1: Basic info, 2: Payment method, 3: Card details
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    phone: '',
    amount: ''
  });
  
  const [paymentData, setPaymentData] = useState({
    payment_method: 'visa',
    card_number: '',
    expiry_month: '',
    expiry_year: '',
    cvv: '',
    cardholder_name: ''
  });
  
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('');
  const [cardValidation, setCardValidation] = useState({});

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handlePaymentInputChange = (e) => {
    const { name, value } = e.target;
    
    // Special handling for card number formatting
    if (name === 'card_number') {
      // Remove all non-digits
      const digitsOnly = value.replace(/\D/g, '');
      
      // Add spaces after every 4 digits
      const formatted = digitsOnly.replace(/(\d{4})(?=\d)/g, '$1 ');
      
      // Limit to 19 characters (16 digits + 3 spaces)
      const limited = formatted.slice(0, 19);
      
      setPaymentData(prev => ({
        ...prev,
        [name]: limited
      }));
    } else {
      setPaymentData(prev => ({
        ...prev,
        [name]: value
      }));
    }
  };

  const validateBasicInfo = () => {
    if (!formData.full_name || !formData.email || !formData.phone || !formData.amount) {
      setMessage('Please fill in all fields');
      setMessageType('error');
      return false;
    }
    if (parseFloat(formData.amount) <= 0) {
      setMessage('Amount must be greater than 0');
      setMessageType('error');
      return false;
    }
    return true;
  };

  const validateCardDetails = async () => {
    // Only validate if card details are provided
    if (!paymentData.card_number || !paymentData.expiry_month || !paymentData.expiry_year || !paymentData.cvv) {
      setMessage('Please fill in all card details');
      setMessageType('error');
      return false;
    }

    // Client-side validation first
    const cardNumber = paymentData.card_number.replace(/\s/g, '');
    if (cardNumber.length < 13 || cardNumber.length > 19) {
      setMessage('Invalid card number length');
      setMessageType('error');
      return false;
    }

    // Basic Luhn algorithm check
    const luhnCheck = (num) => {
      let arr = (num + '')
        .split('')
        .reverse()
        .map(x => parseInt(x));
      let lastDigit = arr.splice(0, 1)[0];
      let sum = arr.reduce((acc, val, i) => (i % 2 !== 0 ? acc + val : acc + ((val * 2) % 9) || 9), 0);
      sum += lastDigit;
      return sum % 10 === 0;
    };

    if (!luhnCheck(cardNumber)) {
      setMessage('Invalid card number');
      setMessageType('error');
      return false;
    }

    // Check expiry date
    const currentDate = new Date();
    const currentYear = currentDate.getFullYear();
    const currentMonth = currentDate.getMonth() + 1;
    
    const expYear = parseInt(paymentData.expiry_year);
    const expMonth = parseInt(paymentData.expiry_month);
    
    if (expYear < currentYear || (expYear === currentYear && expMonth < currentMonth)) {
      setMessage('Card has expired');
      setMessageType('error');
      return false;
    }

    // Check CVV length
    const expectedCvvLength = paymentData.payment_method === 'amex' ? 4 : 3;
    if (paymentData.cvv.length !== expectedCvvLength) {
      setMessage(`CVV must be ${expectedCvvLength} digits for ${paymentData.payment_method.toUpperCase()}`);
      setMessageType('error');
      return false;
    }

    // Try backend validation if available, but don't fail if it's not
    try {
      const response = await axios.post(`${API_BASE_URL}/validate-card`, {
        card_number: paymentData.card_number,
        expiry_month: paymentData.expiry_month,
        expiry_year: paymentData.expiry_year,
        cvv: paymentData.cvv
      }, {
        timeout: 5000 // 5 second timeout
      });

      if (response.data.valid) {
        setCardValidation(response.data);
        return true;
      } else {
        setMessage(`Card validation failed: ${response.data.error}`);
        setMessageType('error');
        return false;
      }
    } catch (error) {
      console.log('Backend validation failed, proceeding with client-side validation:', error.message);
      // If backend validation fails, proceed with client-side validation
      setCardValidation({
        valid: true,
        card_type: paymentData.payment_method,
        masked_number: `**** **** **** ${cardNumber.slice(-4)}`
      });
      return true;
    }
  };

  const handleNextStep = async () => {
    setMessage('');
    
    if (step === 1) {
      if (validateBasicInfo()) {
        setStep(2);
      }
    } else if (step === 2) {
      // Simply move to step 3 without validation - validation happens on submit
      setStep(3);
    }
  };

  const stripePromise = loadStripe(process.env.REACT_APP_STRIPE_PUBLISHABLE_KEY || 'pk_test_your_actual_publishable_key_here');

  return (
    <div className="payment-container">
      <div className="payment-card">
        <div className="payment-header">
          <h1>🔒 GenZ Payment Gateway</h1>
          <p>Your payment information is encrypted and secure</p>
        </div>

        {message && (
          <div className={`alert ${messageType === 'success' ? 'success-alert' : 'error-alert'} mb-4`}>
            {message}
          </div>
        )}

        <div className="progress-bar mb-4">
          <div className={`progress-step ${step >= 1 ? 'active' : ''}`}>1. Personal Info</div>
          <div className={`progress-step ${step >= 2 ? 'active' : ''}`}>2. Payment Method</div>
          <div className={`progress-step ${step >= 3 ? 'active' : ''}`}>3. Card Details</div>
        </div>

        {step === 1 && (
          <div className="payment-step">
            <h3>Personal Information</h3>
            <div className="mb-3">
              <label htmlFor="full_name" className="form-label">Full Name</label>
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
              <label htmlFor="email" className="form-label">Email Address</label>
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
              <label htmlFor="phone" className="form-label">Phone Number</label>
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
              <label htmlFor="amount" className="form-label">Payment Amount</label>
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
              type="button"
              className="btn btn-primary w-100"
              onClick={handleNextStep}
            >
              Continue to Payment Method
            </button>
          </div>
        )}
        {step === 2 && (
          <div className="payment-step">
            <h3>Select Payment Method</h3>
            <div className="payment-methods">
              <div className="payment-method-option">
                <input
                  type="radio"
                  id="visa"
                  name="payment_method"
                  value="visa"
                  checked={paymentData.payment_method === 'visa'}
                  onChange={handlePaymentInputChange}
                />
                <label htmlFor="visa" className="payment-method-label">
                  <span className="card-icon">💳</span>
                  <span>Visa</span>
                </label>
              </div>
              
              <div className="payment-method-option">
                <input
                  type="radio"
                  id="mastercard"
                  name="payment_method"
                  value="mastercard"
                  checked={paymentData.payment_method === 'mastercard'}
                  onChange={handlePaymentInputChange}
                />
                <label htmlFor="mastercard" className="payment-method-label">
                  <span className="card-icon">💳</span>
                  <span>Mastercard</span>
                </label>
              </div>
              
              <div className="payment-method-option">
                <input
                  type="radio"
                  id="amex"
                  name="payment_method"
                  value="amex"
                  checked={paymentData.payment_method === 'amex'}
                  onChange={handlePaymentInputChange}
                />
                <label htmlFor="amex" className="payment-method-label">
                  <span className="card-icon">💳</span>
                  <span>American Express</span>
                </label>
              </div>
              
              <div className="payment-method-option">
                <input
                  type="radio"
                  id="discover"
                  name="payment_method"
                  value="discover"
                  checked={paymentData.payment_method === 'discover'}
                  onChange={handlePaymentInputChange}
                />
                <label htmlFor="discover" className="payment-method-label">
                  <span className="card-icon">💳</span>
                  <span>Discover</span>
                </label>
              </div>
            </div>

            <div className="mt-4">
              <button
                type="button"
                className="btn btn-secondary me-2"
                onClick={() => setStep(1)}
              >
                Back
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleNextStep}
              >
                Continue to Card Details
              </button>
            </div>
          </div>
        )}
        {step === 3 && (
          <div className="payment-step">
            <h3>Card Details</h3>
            <div className="card-preview">
              <div className="card-front">
                <div className="card-type">{paymentData.payment_method.toUpperCase()}</div>
                <div className="card-number">
                  {paymentData.card_number ? 
                    `**** **** **** ${paymentData.card_number.slice(-4)}` : 
                    '**** **** **** ****'
                  }
                </div>
                <div className="card-details">
                  <span className="cardholder">{paymentData.cardholder_name || 'CARDHOLDER NAME'}</span>
                  <span className="expiry">{paymentData.expiry_month || 'MM'}/{paymentData.expiry_year || 'YY'}</span>
                </div>
              </div>
            </div>

            <Elements stripe={stripePromise}>
              <PaymentForm
                formData={formData}
                setFormData={setFormData}
                paymentData={paymentData}
                setPaymentData={setPaymentData}
                setMessage={setMessage}
                setMessageType={setMessageType}
                setLoading={setLoading}
                setStep={setStep}
              />
            </Elements>
          </div>
        )}

        {/* <div className="text-center mt-4">
          <small className="text-muted">
            🔒 PCI DSS Compliant • 256-bit SSL Encryption • Tokenized Payments
          </small>
        </div> */}
        
        {/* <div className="text-center mt-2">
          <small className="text-muted">
            Backend: {API_BASE_URL}
          </small>
        </div> */}
      </div>
    </div>
  );
}

export default App; 