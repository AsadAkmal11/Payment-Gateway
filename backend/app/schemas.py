from pydantic import BaseModel, EmailStr, validator
from datetime import datetime
from typing import Optional
from .models import PaymentMethod, TransactionStatus

class CardDetails(BaseModel):
    card_number: str
    expiry_month: str
    expiry_year: str
    cvv: str
    cardholder_name: str

class PaymentMethodCreate(BaseModel):
    full_name: str
    email: str
    phone: str
    amount: float
    currency: str = "USD"
    payment_method: PaymentMethod
    card_details: CardDetails

class TransactionCreate(BaseModel):
    full_name: str
    email: str
    phone: str
    amount: float
    currency: str = "USD"
    payment_method: PaymentMethod
    payment_token_id: Optional[int] = None

class TransactionResponse(BaseModel):
    id: int
    transaction_id: str
    full_name: str
    email: str
    phone: str
    amount: float
    currency: str
    payment_method: PaymentMethod
    status: TransactionStatus
    security_hash: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class PaymentTokenResponse(BaseModel):
    token_id: str
    masked_card_number: str
    card_type: PaymentMethod
    expiry_month: str
    expiry_year: str
    cardholder_name: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class PaymentValidationResponse(BaseModel):
    valid: bool
    card_type: Optional[str] = None
    masked_number: Optional[str] = None
    error: Optional[str] = None

class SecurityAuditResponse(BaseModel):
    id: int
    transaction_id: str
    event_type: str
    risk_score: float
    created_at: datetime
    
    class Config:
        from_attributes = True 