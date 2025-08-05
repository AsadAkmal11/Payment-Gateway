from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models import User
from app.stripe_service import StripeService
from typing import Optional

router = APIRouter(prefix="/api", tags=["user"])

# Remove the /save-user-temp and /verify-and-save endpoints and their logic