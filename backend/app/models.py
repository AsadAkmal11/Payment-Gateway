from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base
import uuid

class PaymentMethod(enum.Enum):
    VISA = "visa"
    MASTERCARD = "mastercard"
    AMEX = "amex"
    DISCOVER = "discover"
    STRIPE = "stripe"  # Added Stripe as a payment method

class TransactionStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DECLINED = "declined"
    REQUIRES_PAYMENT_METHOD = "requires_payment_method"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    REQUIRES_ACTION = "requires_action"
    CANCELED = "canceled"

class PaymentToken(Base):
    __tablename__ = "payment_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token_id = Column(String(255), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    masked_card_number = Column(String(20), nullable=False)  # Last 4 digits only
    card_type = Column(Enum(PaymentMethod), nullable=False)
    expiry_month = Column(String(2), nullable=False)
    expiry_year = Column(String(4), nullable=False)
    cardholder_name = Column(String(100), nullable=False)
    encrypted_data = Column(Text, nullable=False)  # Encrypted sensitive data
    is_active = Column(String(1), default="Y")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(DateTime(timezone=True), onupdate=func.now())

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(255), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    payment_token_id = Column(Integer, ForeignKey("payment_tokens.id"), nullable=True)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    gateway_response = Column(Text, nullable=True)  # Encrypted gateway response
    security_hash = Column(String(255), nullable=False)  # Transaction integrity hash
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Stripe-specific fields
    stripe_payment_intent_id = Column(String(255), nullable=True, unique=True)
    stripe_client_secret = Column(String(255), nullable=True)
    stripe_payment_method_id = Column(String(255), nullable=True)
    stripe_charge_id = Column(String(255), nullable=True)
    stripe_refund_id = Column(String(255), nullable=True)
    
    # Relationship
    payment_token = relationship("PaymentToken", backref="transactions")

class SecurityAudit(Base):
    __tablename__ = "security_audit"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(255), nullable=False)
    event_type = Column(String(50), nullable=False)  # card_validation, encryption, etc.
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    risk_score = Column(Float, default=0.0)
    details = Column(Text, nullable=True)  # Encrypted audit details
    created_at = Column(DateTime(timezone=True), server_default=func.now()) 