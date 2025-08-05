from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.database import get_db
from app.stripe_service import StripeService
from app.models import Transaction, TransactionStatus, PaymentMethod
from app.security import create_security_hash
import json
import os
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/stripe", tags=["stripe"])

class PaymentIntentRequest(BaseModel):
    amount: int  # Amount in cents
    currency: str = "usd"
    full_name: str
    email: str
    phone: str
    metadata: Optional[Dict[str, Any]] = None

class PaymentConfirmationRequest(BaseModel):
    payment_intent_id: str
    payment_method_id: str

class RefundRequest(BaseModel):
    payment_intent_id: str
    amount: Optional[int] = None  # Amount in cents, if None refunds full amount

@router.post("/create-payment-intent")
async def create_payment_intent(
    request: PaymentIntentRequest,
    db: Session = Depends(get_db),
    client_request: Request = None
):
    """
    Create a Stripe PaymentIntent and store transaction in database
    """
    try:
        # Create PaymentIntent with Stripe
        stripe_result = StripeService.create_payment_intent(
            amount=request.amount,
            currency=request.currency,
            metadata=request.metadata
        )
        
        if not stripe_result['success']:
            raise HTTPException(status_code=400, detail=stripe_result['error'])
        
        # Create transaction record in database
        transaction = Transaction(
            full_name=request.full_name,
            email=request.email,
            phone=request.phone,
            amount=request.amount / 100,  # Convert cents to dollars
            currency=request.currency.upper(),
            payment_method=PaymentMethod.STRIPE,
            status=TransactionStatus.PENDING,
            stripe_payment_intent_id=stripe_result['payment_intent_id'],
            stripe_client_secret=stripe_result['client_secret'],
            security_hash=create_security_hash(request.amount, request.email),
            ip_address=client_request.client.host if client_request else None,
            user_agent=client_request.headers.get("user-agent") if client_request else None
        )
        
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        
        return {
            "success": True,
            "client_secret": stripe_result['client_secret'],
            "payment_intent_id": stripe_result['payment_intent_id'],
            "transaction_id": transaction.transaction_id,
            "amount": stripe_result['amount'],
            "currency": stripe_result['currency']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create payment intent: {str(e)}")

@router.post("/confirm-payment")
async def confirm_payment(
    request: PaymentConfirmationRequest,
    db: Session = Depends(get_db)
):
    """
    Confirm a PaymentIntent with a payment method
    """
    try:
        # Find transaction by payment intent ID
        transaction = db.query(Transaction).filter(
            Transaction.stripe_payment_intent_id == request.payment_intent_id
        ).first()
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Confirm payment with Stripe
        stripe_result = StripeService.confirm_payment_intent(
            payment_intent_id=request.payment_intent_id,
            payment_method_id=request.payment_method_id
        )
        
        if not stripe_result['success']:
            # Update transaction status to failed
            transaction.status = TransactionStatus.FAILED
            transaction.gateway_response = json.dumps({"error": stripe_result['error']})
            db.commit()
            raise HTTPException(status_code=400, detail=stripe_result['error'])
        
        payment_intent = stripe_result['payment_intent']
        
        # Update transaction based on payment intent status
        if payment_intent.status == 'succeeded':
            transaction.status = TransactionStatus.COMPLETED
            transaction.stripe_payment_method_id = request.payment_method_id
            transaction.gateway_response = json.dumps({
                "status": "succeeded",
                "payment_intent_id": payment_intent.id,
                "amount": payment_intent.amount,
                "currency": payment_intent.currency
            })
        elif payment_intent.status == 'requires_action':
            transaction.status = TransactionStatus.REQUIRES_ACTION
        elif payment_intent.status == 'requires_confirmation':
            transaction.status = TransactionStatus.REQUIRES_CONFIRMATION
        else:
            transaction.status = TransactionStatus.FAILED
        
        db.commit()
        
        return {
            "success": True,
            "status": payment_intent.status,
            "transaction_id": transaction.transaction_id,
            "amount": payment_intent.amount,
            "currency": payment_intent.currency
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to confirm payment: {str(e)}")

@router.get("/payment-status/{payment_intent_id}")
async def get_payment_status(
    payment_intent_id: str,
    db: Session = Depends(get_db)
):
    """
    Get the status of a payment intent
    """
    try:
        # Get payment intent from Stripe
        stripe_result = StripeService.retrieve_payment_intent(payment_intent_id)
        
        if not stripe_result['success']:
            raise HTTPException(status_code=404, detail="Payment intent not found")
        
        # Get transaction from database
        transaction = db.query(Transaction).filter(
            Transaction.stripe_payment_intent_id == payment_intent_id
        ).first()
        
        payment_intent = stripe_result['payment_intent']
        
        return {
            "success": True,
            "stripe_status": payment_intent.status,
            "transaction_id": transaction.transaction_id if transaction else None,
            "amount": payment_intent.amount,
            "currency": payment_intent.currency,
            "created": payment_intent.created,
            "last_payment_error": payment_intent.last_payment_error
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get payment status: {str(e)}")

@router.post("/refund")
async def create_refund(
    request: RefundRequest,
    db: Session = Depends(get_db)
):
    """
    Create a refund for a payment
    """
    try:
        # Find transaction by payment intent ID
        transaction = db.query(Transaction).filter(
            Transaction.stripe_payment_intent_id == request.payment_intent_id
        ).first()
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Create refund with Stripe
        stripe_result = StripeService.create_refund(
            payment_intent_id=request.payment_intent_id,
            amount=request.amount
        )
        
        if not stripe_result['success']:
            raise HTTPException(status_code=400, detail=stripe_result['error'])
        
        refund = stripe_result['refund']
        
        # Update transaction with refund information
        transaction.stripe_refund_id = refund.id
        transaction.gateway_response = json.dumps({
            "refund_id": refund.id,
            "refund_amount": refund.amount,
            "refund_status": refund.status
        })
        
        db.commit()
        
        return {
            "success": True,
            "refund_id": refund.id,
            "amount": refund.amount,
            "currency": refund.currency,
            "status": refund.status,
            "transaction_id": transaction.transaction_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create refund: {str(e)}")

@router.get("/transactions/{transaction_id}")
async def get_transaction(
    transaction_id: str,
    db: Session = Depends(get_db)
):
    """
    Get transaction details by transaction ID
    """
    try:
        transaction = db.query(Transaction).filter(
            Transaction.transaction_id == transaction_id
        ).first()
        
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        return {
            "success": True,
            "transaction": {
                "transaction_id": transaction.transaction_id,
                "full_name": transaction.full_name,
                "email": transaction.email,
                "amount": transaction.amount,
                "currency": transaction.currency,
                "status": transaction.status.value,
                "payment_method": transaction.payment_method.value,
                "stripe_payment_intent_id": transaction.stripe_payment_intent_id,
                "created_at": transaction.created_at.isoformat(),
                "updated_at": transaction.updated_at.isoformat() if transaction.updated_at else None
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get transaction: {str(e)}") 