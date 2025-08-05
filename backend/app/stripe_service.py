import stripe
import os
from dotenv import load_dotenv
from typing import Dict, Any, Optional

load_dotenv()

# Initialize Stripe with secret key
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

class StripeService:
    @staticmethod
    def create_payment_intent(amount: int, currency: str = 'usd', metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Create a PaymentIntent with Stripe
        amount: Amount in cents (e.g., 1000 for $10.00)
        currency: Currency code (default: 'usd')
        metadata: Optional metadata to attach to the payment
        """
        try:
            payment_intent_data = {
                'amount': amount,
                'currency': currency,
            }
            
            if metadata:
                payment_intent_data['metadata'] = metadata
            
            payment_intent = stripe.PaymentIntent.create(**payment_intent_data)
            
            return {
                'success': True,
                'client_secret': payment_intent.client_secret,
                'payment_intent_id': payment_intent.id,
                'amount': payment_intent.amount,
                'currency': payment_intent.currency,
                'status': payment_intent.status
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }
    
    @staticmethod
    def retrieve_payment_intent(payment_intent_id: str) -> Dict[str, Any]:
        """
        Retrieve a PaymentIntent from Stripe
        """
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                'success': True,
                'payment_intent': payment_intent
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def confirm_payment_intent(payment_intent_id: str, payment_method_id: str) -> Dict[str, Any]:
        """
        Confirm a PaymentIntent with a payment method
        """
        try:
            payment_intent = stripe.PaymentIntent.confirm(
                payment_intent_id,
                payment_method=payment_method_id
            )
            return {
                'success': True,
                'payment_intent': payment_intent
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def create_refund(payment_intent_id: str, amount: Optional[int] = None) -> Dict[str, Any]:
        """
        Create a refund for a payment
        """
        try:
            refund_data = {'payment_intent': payment_intent_id}
            if amount:
                refund_data['amount'] = amount
            
            refund = stripe.Refund.create(**refund_data)
            return {
                'success': True,
                'refund': refund
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_payment_method(payment_method_id: str) -> Dict[str, Any]:
        """
        Retrieve a payment method
        """
        try:
            payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
            return {
                'success': True,
                'payment_method': payment_method
            }
        except stripe.error.StripeError as e:
            return {
                'success': False,
                'error': str(e)
            } 