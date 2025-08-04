from fastapi import FastAPI, Depends, HTTPException, status, Request
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

app = FastAPI(title="Secure Payment Gateway API")

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
    print("🚀 Starting Secure Payment Gateway Backend...")
    recreate_tables()
    print("✅ Database tables ready!")

@app.get("/")
def home():
    return {"message": "Secure Payment Gateway Backend Running & Tables Synced!"}

@app.post("/validate-card", response_model=PaymentValidationResponse)
def validate_card(card_details: dict):
    """Validate card details before processing payment"""
    try:
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
        
        return PaymentValidationResponse(
            valid=True,
            card_type=card_validation["card_type"],
            masked_number=card_validation["masked_number"]
        )
        
    except Exception as e:
        return PaymentValidationResponse(valid=False, error=str(e))

@app.post("/transactions/create", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payment_data: PaymentMethodCreate, 
    request: Request,
    db: Session = Depends(get_db)
):
    """Create a new secure payment transaction"""
    try:
        # Get client IP and user agent
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent", "")
        
        print(f"🔒 Processing secure payment for: {payment_data.full_name}, Amount: ${payment_data.amount}")
        
        # Sanitize input data
        sanitized_data = {
            "full_name": payment_security.sanitize_input(payment_data.full_name),
            "email": payment_security.sanitize_input(payment_data.email),
            "phone": payment_security.sanitize_input(payment_data.phone),
            "amount": payment_data.amount,
            "currency": payment_data.currency,
            "payment_method": payment_data.payment_method
        }
        
        # Validate card details
        card_validation = payment_security.validate_card_number(payment_data.card_details.card_number)
        if not card_validation["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Card validation failed: {card_validation['error']}"
            )
        
        # Create payment token
        card_data = {
            "card_type": card_validation["card_type"],
            "masked_number": card_validation["masked_number"],
            "expiry_month": payment_data.card_details.expiry_month,
            "expiry_year": payment_data.card_details.expiry_year,
            "cardholder_name": payment_security.sanitize_input(payment_data.card_details.cardholder_name)
        }
        
        encrypted_card_data = payment_security.encrypt_sensitive_data({
            "card_number": payment_data.card_details.card_number,
            "cvv": payment_data.card_details.cvv,
            "expiry_month": payment_data.card_details.expiry_month,
            "expiry_year": payment_data.card_details.expiry_year,
            "cardholder_name": payment_data.card_details.cardholder_name
        })
        
        # Create payment token record
        payment_token = PaymentToken(
            masked_card_number=card_validation["masked_number"],
            card_type=PaymentMethod(card_validation["card_type"]),
            expiry_month=payment_data.card_details.expiry_month,
            expiry_year=payment_data.card_details.expiry_year,
            cardholder_name=payment_data.card_details.cardholder_name,
            encrypted_data=encrypted_card_data
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
        
        # Calculate risk score
        risk_score = payment_security.calculate_risk_score(transaction_data, client_ip)
        
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
            risk_score=risk_score,
            details=payment_security.encrypt_sensitive_data({
                "card_type": card_validation["card_type"],
                "amount": payment_data.amount,
                "risk_factors": ["amount", "email_domain", "ip_address"] if risk_score > 0 else []
            })
        )
        
        db.add(audit_record)
        db.commit()
        db.refresh(db_transaction)
        
        print(f"✅ Secure transaction created successfully with ID: {db_transaction.transaction_id}")
        print(f"🔒 Risk Score: {risk_score:.2f}")
        
        return db_transaction
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating secure transaction: {str(e)}")
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
    return {"status": "healthy", "message": "Secure Payment Gateway API is running"}

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
