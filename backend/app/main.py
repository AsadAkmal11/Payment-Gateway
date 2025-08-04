from fastapi import FastAPI
from app.database import Base, engine
import app.model 

app = FastAPI(title="Gen-Z Payment Gateway")

# Auto-create tables
Base.metadata.create_all(bind=engine)

@app.get("/")
def home():
    return {"message": "Payment Gateway Backend Running & Tables Synced!"}
