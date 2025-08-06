from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.database import get_db
from app.stripe_service import StripeService
from app.models import Transaction, TransactionStatus, PaymentMethod
from app.security import create_security_hash, payment_security
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
    Create a Stripe PaymentIntent (do NOT save transaction in DB yet)
    NOW WITH ACTIVE SECURITY FEATURES
    """
    try:
        # 🔒 SECURITY STEP 1: Rate Limiting
        client_ip = client_request.client.host if client_request else "unknown"
        rate_limit_allowed, rate_limit_info = payment_security.check_rate_limit(
            client_ip, "payment_processing"
        )
        if not rate_limit_allowed:
            raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Try again in {rate_limit_info['retry_after']} seconds")
        
        # 🔒 SECURITY STEP 2: TLS/HTTPS Validation
        if not payment_security.validate_tls_request(dict(client_request.headers)):
            payment_security.log_security_event("tls_violation", {
                "ip_address": client_ip,
                "headers": dict(client_request.headers)
            })
            raise HTTPException(status_code=400, detail="HTTPS required for payment processing")
        
        # 🔒 SECURITY STEP 3: Input Sanitization
        sanitized_name = payment_security.sanitize_input(request.full_name)
        sanitized_email = payment_security.sanitize_input(request.email)
        sanitized_phone = payment_security.sanitize_input(request.phone)
        
        # 🔒 SECURITY STEP 4: Risk Assessment
        transaction_data = {
            "amount": request.amount / 100,
            "currency": request.currency,
            "email": sanitized_email,
            "full_name": sanitized_name
        }
        
        risk_assessment = payment_security.calculate_risk_score(
            transaction_data,
            client_ip=client_ip,
            user_agent=client_request.headers.get("user-agent")
        )
        
        # 🔒 SECURITY STEP 5: Log Security Event
        payment_security.log_security_event("payment_intent_creation", {
            "ip_address": client_ip,
            "user_agent": client_request.headers.get("user-agent"),
            "amount": request.amount,
            "email": sanitized_email,
            "risk_score": risk_assessment["risk_score"],
            "risk_factors": ",".join(risk_assessment["risk_factors"])
        })
        
        # 🔒 SECURITY STEP 6: High Risk Blocking
        if risk_assessment["risk_level"] == "high" and risk_assessment["recommendation"] == "block":
            raise HTTPException(status_code=400, detail="Transaction blocked due to high risk")
        
        # Create PaymentIntent with Stripe
        stripe_result = StripeService.create_payment_intent(
            amount=request.amount,
            currency=request.currency,
            metadata={
                "full_name": sanitized_name,
                "email": sanitized_email,
                "phone": sanitized_phone,
                "risk_score": risk_assessment["risk_score"],
                "risk_factors": ",".join(risk_assessment["risk_factors"])
            }
        )
        
        if not stripe_result['success']:
            raise HTTPException(status_code=400, detail=stripe_result['error'])
        
        # Do NOT save anything in DB here
        return {
            "success": True,
            "client_secret": stripe_result['client_secret'],
            "payment_intent_id": stripe_result['payment_intent_id'],
            "amount": stripe_result['amount'],
            "currency": stripe_result['currency'],
            "risk_level": risk_assessment["risk_level"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create payment intent: {str(e)}")

@router.post("/confirm-payment")
async def confirm_payment(
    request: PaymentConfirmationRequest,
    db: Session = Depends(get_db),
    client_request: Request = None
):
    """
    Confirm a PaymentIntent with a payment method
    Only save transaction in DB if payment is successful
    NOW WITH ACTIVE SECURITY FEATURES
    """
    try:
        # 🔒 SECURITY STEP 1: Rate Limiting
        client_ip = client_request.client.host if client_request else "unknown"
        rate_limit_allowed, rate_limit_info = payment_security.check_rate_limit(
            client_ip, "payment_processing"
        )
        if not rate_limit_allowed:
            raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Try again in {rate_limit_info['retry_after']} seconds")
        
        # First, check if transaction already exists (payment might have been confirmed before)
        existing_transaction = db.query(Transaction).filter(
            Transaction.stripe_payment_intent_id == request.payment_intent_id
        ).first()
        
        if existing_transaction and existing_transaction.status == TransactionStatus.COMPLETED:
            # Payment already processed successfully
            payment_security.log_security_event("payment_already_confirmed", {
                "ip_address": client_ip,
                "payment_intent_id": request.payment_intent_id,
                "transaction_id": existing_transaction.transaction_id
            })
            return {
                "success": True,
                "status": "succeeded",
                "transaction_id": existing_transaction.transaction_id,
                "amount": existing_transaction.amount,
                "currency": existing_transaction.currency,
                "message": "Payment already confirmed successfully"
            }
        
        # Confirm payment with Stripe
        stripe_result = StripeService.confirm_payment_intent(
            payment_intent_id=request.payment_intent_id,
            payment_method_id=request.payment_method_id
        )
        
        if not stripe_result['success']:
            # Check if the error is because payment is already confirmed
            if "already succeeded" in stripe_result['error']:
                # Payment succeeded but we need to check if we have the transaction
                stripe_status_result = StripeService.retrieve_payment_intent(request.payment_intent_id)
                if stripe_status_result['success']:
                    payment_intent = stripe_status_result['payment_intent']
                    if payment_intent.status == 'succeeded':
                        # Payment succeeded, check if we need to save it
                        if not existing_transaction:
                            # Extract metadata and save transaction
                            metadata = payment_intent.metadata or {}
                            full_name = metadata.get('full_name', '')
                            email = metadata.get('email', '')
                            phone = metadata.get('phone', '')
                            amount = payment_intent.amount / 100
                            currency = payment_intent.currency.upper()
                            
                            # 🔒 SECURITY STEP 3: Generate Security Hash
                            security_hash = payment_security.generate_security_hash({
                                "amount": amount,
                                "currency": currency,
                                "email": email,
                                "payment_intent_id": payment_intent.id
                            })
                            
                            transaction = Transaction(
                                full_name=full_name,
                                email=email,
                                phone=phone,
                                amount=amount,
                                currency=currency,
                                payment_method=PaymentMethod.STRIPE,
                                status=TransactionStatus.COMPLETED,
                                stripe_payment_intent_id=payment_intent.id,
                                stripe_client_secret=payment_intent.client_secret,
                                stripe_payment_method_id=request.payment_method_id,
                                security_hash=security_hash,
                                ip_address=client_ip,
                                user_agent=client_request.headers.get("user-agent") if client_request else None,
                                gateway_response=json.dumps({
                                    "status": "succeeded",
                                    "payment_intent_id": payment_intent.id,
                                    "amount": payment_intent.amount,
                                    "currency": payment_intent.currency,
                                    "risk_score": metadata.get('risk_score', 0),
                                    "risk_factors": metadata.get('risk_factors', '')
                                })
                            )
                            db.add(transaction)
                            db.commit()
                            db.refresh(transaction)
                            
                            # 🔒 SECURITY STEP 4: Log Successful Payment
                            payment_security.log_security_event("payment_successful", {
                                "ip_address": client_ip,
                                "transaction_id": transaction.transaction_id,
                                "payment_intent_id": payment_intent.id,
                                "amount": amount,
                                "email": email
                            })
                            
                            return {
                                "success": True,
                                "status": payment_intent.status,
                                "transaction_id": transaction.transaction_id,
                                "amount": payment_intent.amount,
                                "currency": payment_intent.currency,
                                "message": "Payment confirmed successfully"
                            }
                        else:
                            # Transaction already exists
                            return {
                                "success": True,
                                "status": "succeeded",
                                "transaction_id": existing_transaction.transaction_id,
                                "amount": existing_transaction.amount,
                                "currency": existing_transaction.currency,
                                "message": "Payment already confirmed successfully"
                            }
            
            # 🔒 SECURITY STEP 2: Log Failed Payment
            payment_security.log_security_event("payment_failed", {
                "ip_address": client_ip,
                "payment_intent_id": request.payment_intent_id,
                "error": stripe_result['error']
            })
            raise HTTPException(status_code=400, detail=stripe_result['error'])
        
        payment_intent = stripe_result['payment_intent']
        
        # Only save to DB if payment succeeded
        if payment_intent.status == 'succeeded':
            # Extract metadata
            metadata = payment_intent.metadata or {}
            full_name = metadata.get('full_name', '')
            email = metadata.get('email', '')
            phone = metadata.get('phone', '')
            amount = payment_intent.amount / 100
            currency = payment_intent.currency.upper()
            
            # 🔒 SECURITY STEP 3: Generate Security Hash
            security_hash = payment_security.generate_security_hash({
                "amount": amount,
                "currency": currency,
                "email": email,
                "payment_intent_id": payment_intent.id
            })
            
            transaction = Transaction(
                full_name=full_name,
                email=email,
                phone=phone,
                amount=amount,
                currency=currency,
                payment_method=PaymentMethod.STRIPE,
                status=TransactionStatus.COMPLETED,
                stripe_payment_intent_id=payment_intent.id,
                stripe_client_secret=payment_intent.client_secret,
                stripe_payment_method_id=request.payment_method_id,
                security_hash=security_hash,
                ip_address=client_ip,
                user_agent=client_request.headers.get("user-agent") if client_request else None,
                gateway_response=json.dumps({
                    "status": "succeeded",
                    "payment_intent_id": payment_intent.id,
                    "amount": payment_intent.amount,
                    "currency": payment_intent.currency,
                    "risk_score": metadata.get('risk_score', 0),
                    "risk_factors": metadata.get('risk_factors', '')
                })
            )
            db.add(transaction)
            db.commit()
            db.refresh(transaction)
            
            # 🔒 SECURITY STEP 4: Log Successful Payment
            payment_security.log_security_event("payment_successful", {
                "ip_address": client_ip,
                "transaction_id": transaction.transaction_id,
                "payment_intent_id": payment_intent.id,
                "amount": amount,
                "email": email
            })
            
            return {
                "success": True,
                "status": payment_intent.status,
                "transaction_id": transaction.transaction_id,
                "amount": payment_intent.amount,
                "currency": payment_intent.currency
            }
        else:
            # 🔒 SECURITY STEP 5: Log Non-Successful Payment
            payment_security.log_security_event("payment_not_successful", {
                "ip_address": client_ip,
                "payment_intent_id": payment_intent.id,
                "status": payment_intent.status
            })
            
            return {
                "success": False,
                "status": payment_intent.status,
                "message": "Payment not successful, nothing saved."
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

@router.post("/validate-card")
async def validate_card(
    request: Request,
    client_request: Request = None
):
    """
    Validate card details using security features
    NOW WITH ACTIVE SECURITY FEATURES
    """
    try:
        # Get request body
        body = await request.json()
        card_number = body.get('card_number', '')
        expiry_month = body.get('expiry_month', '')
        expiry_year = body.get('expiry_year', '')
        cvv = body.get('cvv', '')
        
        # 🔒 SECURITY STEP 1: Rate Limiting
        client_ip = client_request.client.host if client_request else "unknown"
        rate_limit_allowed, rate_limit_info = payment_security.check_rate_limit(
            client_ip, "card_validation"
        )
        if not rate_limit_allowed:
            raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Try again in {rate_limit_info['retry_after']} seconds")
        
        # 🔒 SECURITY STEP 2: Input Sanitization
        sanitized_card_number = payment_security.sanitize_input(card_number)
        sanitized_expiry_month = payment_security.sanitize_input(expiry_month)
        sanitized_expiry_year = payment_security.sanitize_input(expiry_year)
        sanitized_cvv = payment_security.sanitize_input(cvv)
        
        # 🔒 SECURITY STEP 3: Card Validation
        card_validation = payment_security.validate_card_number(sanitized_card_number)
        if not card_validation["valid"]:
            payment_security.log_security_event("card_validation_failed", {
                "ip_address": client_ip,
                "error": card_validation["error"],
                "card_type": "unknown"
            })
            return {"valid": False, "error": card_validation["error"]}
        
        # 🔒 SECURITY STEP 4: Expiry Validation
        expiry_validation = payment_security.validate_expiry_date(sanitized_expiry_month, sanitized_expiry_year)
        if not expiry_validation["valid"]:
            payment_security.log_security_event("card_validation_failed", {
                "ip_address": client_ip,
                "error": expiry_validation["error"],
                "card_type": card_validation["card_type"]
            })
            return {"valid": False, "error": expiry_validation["error"]}
        
        # 🔒 SECURITY STEP 5: CVV Validation
        cvv_validation = payment_security.validate_cvv(sanitized_cvv, card_validation["card_type"])
        if not cvv_validation["valid"]:
            payment_security.log_security_event("card_validation_failed", {
                "ip_address": client_ip,
                "error": cvv_validation["error"],
                "card_type": card_validation["card_type"]
            })
            return {"valid": False, "error": cvv_validation["error"]}
        
        # 🔒 SECURITY STEP 6: Log Successful Validation
        payment_security.log_security_event("card_validation_successful", {
            "ip_address": client_ip,
            "card_type": card_validation["card_type"],
            "masked_number": card_validation["masked_number"]
        })
        
        return {
            "valid": True,
            "card_type": card_validation["card_type"],
            "masked_number": card_validation["masked_number"],
            "last_four": card_validation["last_four"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Card validation failed: {str(e)}") 

@router.get("/security-status")
async def get_security_status():
    """
    Get current security status and recent events
    """
    try:
        # Get rate limiting info
        rate_limit_info = {
            "card_validation": {
                "limit": payment_security.rate_limits["card_validation"]["requests"],
                "window": payment_security.rate_limits["card_validation"]["window"]
            },
            "payment_processing": {
                "limit": payment_security.rate_limits["payment_processing"]["requests"],
                "window": payment_security.rate_limits["payment_processing"]["window"]
            }
        }
        
        # Get security configuration
        security_config = {
            "hmac_secret_configured": bool(payment_security.hmac_secret),
            "security_salt_configured": bool(payment_security.security_salt),
            "suspicious_domains_count": len(payment_security.suspicious_domains),
            "risk_weights": payment_security.risk_weights
        }
        
        return {
            "success": True,
            "security_status": {
                "rate_limiting": rate_limit_info,
                "configuration": security_config,
                "features_active": {
                    "rate_limiting": True,
                    "input_sanitization": True,
                    "risk_assessment": True,
                    "security_logging": True,
                    "tls_validation": True,
                    "card_validation": True
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get security status: {str(e)}") 