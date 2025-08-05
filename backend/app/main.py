from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
import app.model 
from app.stripe_routes import router as stripe_router

app = FastAPI(title="Gen-Z Payment Gateway")

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Stripe routes
app.include_router(stripe_router)

# Auto-create tables
Base.metadata.create_all(bind=engine)

@app.get("/")
def home():
    return {"message": "Payment Gateway Backend Running & Tables Synced!"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "Payment Gateway is running"}
