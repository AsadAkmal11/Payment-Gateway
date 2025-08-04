from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class TransactionCreate(BaseModel):
    full_name: str
    email: str
    phone: str
    amount: float

class TransactionResponse(BaseModel):
    id: int
    full_name: str
    email: str
    phone: str
    amount: float
    reference: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True 