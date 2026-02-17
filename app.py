from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
import requests

from database import get_db, User, init_db
from auth import verify_password, hash_password

# ======================
# CONFIG
# ======================

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

HF_TOKEN = os.getenv("HF_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"

headers = {
    "Authorization": f"Bearer {HF_TOKEN}"
}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ======================
# INIT
# ======================

init_db()
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_frontend():
    return FileResponse("static/index.html")

# ======================
# SCHEMAS
# ======================

class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class RepurposeRequest(BaseModel):
    content: str

# ======================
# JWT FUNCTIONS
# ======================

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication"
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()

    if user is None:
        raise credentials_exception

    return user

# ======================
# SIGNUP
# ======================

@app.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):

    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=user.email,
        password_hash=hash_password(user.password),
        plan="free",
        usage_count=0,
        is_active=True
    )

    db.add(new_user)
    db.commit()

    return {"message": "Signup successful"}

# ======================
# LOGIN
# ======================

@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):

    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token({"sub": db_user.email})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

# ======================
# HUGGINGFACE AI FUNCTION
# ======================

def generate_with_hf(prompt: str):

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 200
        }
    }

    response = requests.post(HF_API_URL, headers=headers, json=payload)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="HF API Error")

    result = response.json()

    return result[0]["generated_text"]

# ======================
# REPURPOSE
# ======================

@app.post("/repurpose")
def repurpose(
    data: RepurposeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # Free plan limit
    if current_user.plan == "free" and current_user.usage_count >= 3:
        raise HTTPException(
            status_code=403,
            detail="Free plan limit reached. Upgrade to Pro."
        )

    prompt = f"""
You are a professional content repurposing assistant.
Rewrite the following content professionally:

{data.content}
"""

    ai_output = generate_with_hf(prompt)

    # Increase usage
    if current_user.plan == "free":
        current_user.usage_count += 1
        db.commit()

    return {
        "usage": current_user.usage_count,
        "result": ai_output
    }

# ======================
# UPGRADE
# ======================

@app.post("/upgrade")
def upgrade(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):

    current_user.plan = "pro"
    current_user.usage_count = 0
    db.commit()

    return {"message": "Upgraded to Pro successfully"}

# ======================
# HEALTH
# ======================

@app.get("/health")
def health():
    return {"status": "ok"}
