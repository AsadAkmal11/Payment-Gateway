from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.database import Base, engine, get_db
from app.model import Transaction
from app.schemas import TransactionCreate, TransactionResponse

app = FastAPI(title="Payment Gateway API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React app URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auto-create tables
Base.metadata.create_all(bind=engine)

@app.get("/")
def home():
    return {"message": "Payment Gateway Backend Running & Tables Synced!"}

@app.post("/transactions/create", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(transaction: TransactionCreate, db: Session = Depends(get_db)):
    """Create a new transaction"""
    try:
        db_transaction = Transaction(
            full_name=transaction.full_name,
            email=transaction.email,
            phone=transaction.phone,
            amount=transaction.amount
        )
        
        db.add(db_transaction)
        db.commit()
        db.refresh(db_transaction)
        
        return db_transaction
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create transaction: {str(e)}"
        )

@app.get("/transactions", response_model=list[TransactionResponse])
def get_transactions(db: Session = Depends(get_db)):
    """Get all transactions"""
    transactions = db.query(Transaction).order_by(Transaction.created_at.desc()).all()
    return transactions
