# Stripe Integration Setup Guide

## 🚀 Quick Start

### 1. Get Your Stripe Keys

1. Go to [Stripe Dashboard](https://dashboard.stripe.com/)
2. Sign up or log in to your account
3. Navigate to **Developers > API keys**
4. Copy your **Publishable key** and **Secret key**

### 2. Configure Environment Variables

Create a `.env` file in the `backend/` directory with your Stripe keys:

```env
# Database Configuration
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=localhost
DB_NAME=payment_gateway

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_your_actual_secret_key_here
STRIPE_PUBLISHABLE_KEY=pk_test_your_actual_publishable_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
```

### 3. Update Frontend Stripe Key

In `frontend/src/RealPaymentForm.jsx`, replace the placeholder with your publishable key:

```javascript
const stripePromise = loadStripe('pk_test_your_actual_publishable_key_here');
```

### 4. Install Dependencies

**Backend:**
```bash
cd backend
pip install -r requirements.txt
```

**Frontend:**
```bash
cd frontend
npm install
```

### 5. Start the Application

**Backend:**
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd frontend
npm start
```

## 🔧 API Endpoints

### Stripe Payment Endpoints

- `POST /stripe/create-payment-intent` - Create a new payment intent
- `POST /stripe/confirm-payment` - Confirm a payment with payment method
- `GET /stripe/payment-status/{payment_intent_id}` - Get payment status
- `POST /stripe/refund` - Create a refund
- `GET /stripe/transactions/{transaction_id}` - Get transaction details

### Example Usage

**Create Payment Intent:**
```bash
curl -X POST "http://localhost:8000/stripe/create-payment-intent" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 1000,
    "currency": "usd",
    "full_name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890"
  }'
```

## 🧪 Testing

### Test Card Numbers

Use these test card numbers for testing:

- **Success:** `4242 4242 4242 4242`
- **Decline:** `4000 0000 0000 0002`
- **Requires Authentication:** `4000 0025 0000 3155`

### Test Scenarios

1. **Successful Payment:**
   - Use card: `4242 4242 4242 4242`
   - Any future expiry date
   - Any 3-digit CVC

2. **Declined Payment:**
   - Use card: `4000 0000 0000 0002`
   - Will be declined by Stripe

3. **3D Secure Authentication:**
   - Use card: `4000 0025 0000 3155`
   - Will require additional authentication

## 🔒 Security Features

### PCI Compliance
- No card data is stored on your servers
- All sensitive data is handled by Stripe
- Stripe is PCI DSS Level 1 compliant

### Security Measures
- All API calls use HTTPS
- Stripe keys are stored in environment variables
- Transaction integrity hashing
- IP address and user agent logging

## 📊 Database Schema

### Transaction Table
- `stripe_payment_intent_id` - Stripe's payment intent ID
- `stripe_client_secret` - Client secret for frontend
- `stripe_payment_method_id` - Payment method ID
- `stripe_charge_id` - Charge ID (if applicable)
- `stripe_refund_id` - Refund ID (if applicable)

## 🚨 Error Handling

### Common Errors

1. **Invalid API Key:**
   - Check your Stripe secret key in `.env`
   - Ensure you're using test keys for development

2. **CORS Errors:**
   - Backend is configured to allow `localhost:3000`
   - Check if frontend is running on correct port

3. **Database Connection:**
   - Ensure MySQL is running
   - Check database credentials in `.env`

## 🔄 Webhooks (Optional)

For production, set up webhooks to handle payment events:

1. Go to Stripe Dashboard > Webhooks
2. Add endpoint: `https://your-domain.com/stripe/webhook`
3. Select events: `payment_intent.succeeded`, `payment_intent.payment_failed`
4. Copy webhook secret to `.env`

## 📈 Monitoring

### Stripe Dashboard
- Monitor payments in real-time
- View transaction logs
- Set up alerts for failed payments

### Application Logs
- Check backend logs for API errors
- Monitor database for transaction status changes

## 🎯 Next Steps

1. **Production Deployment:**
   - Use live Stripe keys
   - Set up proper SSL certificates
   - Configure production database

2. **Additional Features:**
   - Implement webhook handling
   - Add subscription support
   - Create admin dashboard

3. **Testing:**
   - Run integration tests
   - Test error scenarios
   - Validate security measures

## 📞 Support

- **Stripe Documentation:** https://stripe.com/docs
- **Stripe Support:** https://support.stripe.com/
- **API Reference:** https://stripe.com/docs/api

---

**⚠️ Important:** Never commit your actual Stripe keys to version control. Always use environment variables and keep your `.env` file in `.gitignore`. 