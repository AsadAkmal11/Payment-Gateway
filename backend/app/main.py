from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine
from app.stripe_routes import router as stripe_router
from app.user_routes import router as user_router
# from fastapi import FastAPI
# from fastapi.responses import JSONResponse
# from stripe_service import PUBLISHABLE_KEY

app = FastAPI(title="Gen-Z Payment Gateway")

# Add CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Stripe and User routes
app.include_router(stripe_router)
app.include_router(user_router)

# Auto-create tables (uncomment this line)
Base.metadata.create_all(bind=engine)


# @app.get("/config")
# def get_stripe_config():
#     return JSONResponse(content={"publishableKey": PUBLISHABLE_KEY})

@app.get("/")
def home():
    return {"message": "Payment Gateway Backend Running & Tables Synced!"}  

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "Payment Gateway is running"}