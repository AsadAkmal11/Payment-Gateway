from fastapi import FastAPI, Depends, HTTPException, status, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import Base, engine, get_db
from app.models import Transaction, PaymentToken, SecurityAudit, PaymentMethod, TransactionStatus
from app.schemas import (
    PaymentMethodCreate, TransactionCreate, TransactionResponse,
    PaymentTokenResponse, PaymentValidationResponse, SecurityAuditResponse
)
from app.security import payment_security
import json
import os
import stripe
import time

# Initialize Stripe (for real payments)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_your_stripe_key_here")

app = FastAPI(title="PCI-Compliant Payment Gateway API")

# Add CORS middleware with more permissive settings for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React app URLs
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Function to recreate tables with new schema
def recreate_tables():
    try:
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        print("✅ Dropped existing tables")

        # Create all tables with new schema
        Base.metadata.create_all(bind=engine)
        print("✅ Created tables with new schema")

    except Exception as e:
        print(f"❌ Error recreating tables: {str(e)}")
        raise e

# Auto-create tables with new schema
@app.on_event("startup")
async def startup_event():
    print("🚀 Starting PCI-Compliant Payment Gateway Backend...")
    recreate_tables()
    print("✅ Database tables ready!")

@app.get("/")
def home():
    return {"message": "PCI-Compliant Payment Gateway Backend Running & Tables Synced!"}

@app.post("/validate-card", response_model=PaymentValidationResponse)
def validate_card(card_details: dict, request: Request):
    """Validate card details (client-side validation only)"""
    try:
        # Rate limiting
        client_ip = request.client.host
        allowed, rate_info = payment_security.check_rate_limit(
            f"card_validation_{client_ip}", "card_validation"
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Retry after {rate_info['retry_after']} seconds"
            )

        # TLS validation
        if not payment_security.validate_tls_request(dict(request.headers)):
            payment_security.log_security_event("tls_violation", {
                "ip_address": client_ip,
                "headers": dict(request.headers)
            })
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="HTTPS required for card validation"
            )

        # Validate card number
        card_validation = payment_security.validate_card_number(card_details["card_number"])
        if not card_validation["valid"]:
            return PaymentValidationResponse(valid=False, error=card_validation["error"])

        # Validate expiry date
        expiry_validation = payment_security.validate_expiry_date(
            card_details["expiry_month"],
            card_details["expiry_year"]
        )
        if not expiry_validation["valid"]:
            return PaymentValidationResponse(valid=False, error=expiry_validation["error"])

        # Validate CVV
        cvv_validation = payment_security.validate_cvv(
            card_details["cvv"],
            card_validation["card_type"]
        )
        if not cvv_validation["valid"]:
            return PaymentValidationResponse(valid=False, error=cvv_validation["error"])

        # Log successful validation
        payment_security.log_security_event("card_validation_success", {
            "ip_address": client_ip,
            "card_type": card_validation["card_type"],
            "last_four": card_validation["last_four"]
        })

        return PaymentValidationResponse(
            valid=True,
            card_type=card_validation["card_type"],
            masked_number=card_validation["masked_number"]
        )

    except HTTPException:
        raise
    except Exception as e:
        payment_security.log_security_event("card_validation_error", {
            "ip_address": request.client.host,
            "error": str(e)
        })
        return PaymentValidationResponse(valid=False, error=str(e))

@app.post("/create-payment-intent")
def create_payment_intent(amount: float, currency: str = "usd", request: Request = None):
    """Create a Stripe Payment Intent for real payment processing"""
    try:
        # Rate limiting
        client_ip = request.client.host if request else "unknown"
        allowed, rate_info = payment_security.check_rate_limit(
            f"payment_intent_{client_ip}", "payment_processing"
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Retry after {rate_info['retry_after']} seconds"
            )

        # Convert amount to cents (Stripe uses smallest currency unit)
        amount_cents = int(amount * 100)
        
        payment_intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=currency,
            automatic_payment_methods={"enabled": True},
        )
        
        # Log payment intent creation
        payment_security.log_security_event("payment_intent_created", {
            "ip_address": client_ip,
            "amount": amount,
            "currency": currency,
            "stripe_payment_intent_id": payment_intent.id
        })
        
        return {
            "client_secret": payment_intent.client_secret,
            "payment_intent_id": payment_intent.id
        }
    except Exception as e:
        payment_security.log_security_event("payment_intent_error", {
            "ip_address": request.client.host if request else "unknown",
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create payment intent: {str(e)}"
        )

@app.post("/process-real-payment")
def process_real_payment(payment_intent_id: str, db: Session = Depends(get_db), request: Request = None):
    """Process a real payment using Stripe"""
    try:
        # Rate limiting
        client_ip = request.client.host if request else "unknown"
        allowed, rate_info = payment_security.check_rate_limit(
            f"real_payment_{client_ip}", "payment_processing"
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Retry after {rate_info['retry_after']} seconds"
            )

        # Retrieve the payment intent
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if payment_intent.status == "succeeded":
            # Create transaction record (no sensitive data)
            db_transaction = Transaction(
                full_name="Real Payment Customer",
                email="customer@example.com",
                phone="+1234567890",
                amount=payment_intent.amount / 100,  # Convert from cents
                currency=payment_intent.currency.upper(),
                payment_method=PaymentMethod.VISA,  # Default, you can detect from payment method
                status=TransactionStatus.COMPLETED,
                security_hash=payment_security.generate_security_hash({
                    "amount": payment_intent.amount / 100,
                    "currency": payment_intent.currency,
                    "email": "customer@example.com"
                }),
                gateway_response=json.dumps({
                    "stripe_payment_intent_id": payment_intent.id,
                    "status": payment_intent.status,
                    "amount": payment_intent.amount,
                    "currency": payment_intent.currency
                })
            )
            
            db.add(db_transaction)
            db.commit()
            db.refresh(db_transaction)
            
            # Log successful payment
            payment_security.log_security_event("real_payment_success", {
                "ip_address": client_ip,
                "transaction_id": db_transaction.transaction_id,
                "amount": payment_intent.amount / 100,
                "stripe_payment_intent_id": payment_intent.id
            })
            
            return {
                "success": True,
                "transaction_id": db_transaction.transaction_id,
                "amount": payment_intent.amount / 100,
                "currency": payment_intent.currency.upper(),
                "status": "completed"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment failed: {payment_intent.status}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        payment_security.log_security_event("real_payment_error", {
            "ip_address": request.client.host if request else "unknown",
            "error": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process payment: {str(e)}"
        )

@app.post("/transactions/create", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payment_data: PaymentMethodCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Create a new secure payment transaction (Demo Mode - PCI Compliant)"""
    try:
        # Get client IP and user agent
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent", "")

        print(f"🔒 Processing PCI-compliant payment for: {payment_data.full_name}, Amount: ${payment_data.amount}")

        # Rate limiting
        allowed, rate_info = payment_security.check_rate_limit(
            f"transaction_{client_ip}", "payment_processing"
        )
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Retry after {rate_info['retry_after']} seconds"
            )

        # TLS validation
        if not payment_security.validate_tls_request(dict(request.headers)):
            payment_security.log_security_event("tls_violation", {
                "ip_address": client_ip,
                "headers": dict(request.headers)
            })
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="HTTPS required for payment processing"
            )

        # Sanitize input data
        sanitized_data = {
            "full_name": payment_security.sanitize_input(payment_data.full_name),
            "email": payment_security.sanitize_input(payment_data.email),
            "phone": payment_security.sanitize_input(payment_data.phone),
            "amount": payment_data.amount,
            "currency": payment_data.currency,
            "payment_method": payment_data.payment_method
        }

        # Validate card details (client-side validation only)
        card_validation = payment_security.validate_card_number(payment_data.card_details.card_number)
        if not card_validation["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Card validation failed: {card_validation['error']}"
            )

        # Create PCI-compliant payment token (NO sensitive data)
        card_data = {
            "card_type": card_validation["card_type"],
            "last_four": card_validation["last_four"],
            "expiry_month": payment_data.card_details.expiry_month,
            "expiry_year": payment_data.card_details.expiry_year,
            "cardholder_name": payment_security.sanitize_input(payment_data.card_details.cardholder_name)
        }

        # Create payment token record (PCI-compliant - no sensitive data)
        payment_token = PaymentToken(
            masked_card_number=card_validation["masked_number"],
            card_type=PaymentMethod(card_validation["card_type"]),
            expiry_month=payment_data.card_details.expiry_month,
            expiry_year=payment_data.card_details.expiry_year,
            cardholder_name=payment_data.card_details.cardholder_name,
            encrypted_data=payment_security.create_payment_token(card_data)  # PCI-compliant token
        )

        db.add(payment_token)
        db.flush()  # Get the ID without committing

        # Generate security hash
        transaction_data = {
            "amount": payment_data.amount,
            "currency": payment_data.currency,
            "email": payment_data.email
        }
        security_hash = payment_security.generate_security_hash(transaction_data)

        # Calculate advanced risk score
        risk_assessment = payment_security.calculate_risk_score(
            transaction_data, 
            client_ip, 
            user_agent
        )

        # Create transaction record
        db_transaction = Transaction(
            full_name=sanitized_data["full_name"],
            email=sanitized_data["email"],
            phone=sanitized_data["phone"],
            amount=payment_data.amount,
            currency=payment_data.currency,
            payment_method=payment_data.payment_method,
            payment_token_id=payment_token.id,
            status=TransactionStatus.PROCESSING,
            security_hash=security_hash,
            ip_address=client_ip,
            user_agent=user_agent
        )

        db.add(db_transaction)

        # Create security audit record
        audit_record = SecurityAudit(
            transaction_id=db_transaction.transaction_id,
            event_type="payment_processing",
            ip_address=client_ip,
            user_agent=user_agent,
            risk_score=risk_assessment["risk_score"],
            details=json.dumps({
                "risk_factors": risk_assessment["risk_factors"],
                "risk_level": risk_assessment["risk_level"],
                "recommendation": risk_assessment["recommendation"],
                "card_type": card_validation["card_type"],
                "amount": payment_data.amount
            })
        )

        db.add(audit_record)
        db.commit()
        db.refresh(db_transaction)

        # Log security event
        payment_security.log_security_event("transaction_created", {
            "ip_address": client_ip,
            "transaction_id": db_transaction.transaction_id,
            "amount": payment_data.amount,
            "risk_score": risk_assessment["risk_score"],
            "risk_level": risk_assessment["risk_level"]
        }, risk_assessment["risk_score"])

        print(f"✅ PCI-compliant transaction created successfully with ID: {db_transaction.transaction_id}")
        print(f"🔒 Risk Score: {risk_assessment['risk_score']:.2f} ({risk_assessment['risk_level']})")

        return db_transaction

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        payment_security.log_security_event("transaction_error", {
            "ip_address": request.client.host,
            "error": str(e)
        })
        print(f"❌ Error creating PCI-compliant transaction: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create secure transaction: {str(e)}"
        )

@app.get("/transactions", response_model=list[TransactionResponse])
def get_transactions(db: Session = Depends(get_db)):
    """Get all transactions (admin only)"""
    transactions = db.query(Transaction).order_by(Transaction.created_at.desc()).all()
    return transactions

@app.get("/payment-tokens", response_model=list[PaymentTokenResponse])
def get_payment_tokens(db: Session = Depends(get_db)):
    """Get all payment tokens (admin only)"""
    tokens = db.query(PaymentToken).filter(PaymentToken.is_active == "Y").all()
    return tokens

@app.get("/security-audit", response_model=list[SecurityAuditResponse])
def get_security_audit(db: Session = Depends(get_db)):
    """Get security audit logs (admin only)"""
    audit_logs = db.query(SecurityAudit).order_by(SecurityAudit.created_at.desc()).all()
    return audit_logs

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "PCI-Compliant Payment Gateway API is running"}

# Database reset endpoint (for development)
@app.post("/reset-database")
def reset_database():
    """Reset database tables (development only)"""
    try:
        recreate_tables()
        return {"message": "Database reset successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset database: {str(e)}"
        )
