from fastapi import FastAPI
from jose import JWTError,jwt
from pydantic import BaseModel
from datetime import datetime, timedelta
SECRET_KEY="ni-batao-ga"
ALGORITHM = "HS256"

app=FastAPI(title="Gen-Z Payment")
def loginRequest(BaseModel):
    username: str   
    passsword:str

def createAccessToken(data: dict , expires_delta: timedelta | None= None):
    to_encode= data.copy()
    

@app.get("/")
def home():
    return {"message":"Backend running!"}
