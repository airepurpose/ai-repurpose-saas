from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from database import get_db, User, init_db
from auth import verify_password,hash_password
from ai_engine import generate_content

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from auth_utils import decode_token
from auth_utils import create_access_token
from fastapi.staticfiles import StaticFiles

security = HTTPBearer()

# ======================
# INIT
# ======================

init_db()
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

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
# SIGNUP
# ======================

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db, User
from auth import hash_password


class UserCreate(BaseModel):
    email: str
    password: str


@app.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    # 1. Check if email already exists
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. Hash password (IMPORTANT FIX)
    hashed_password = hash_password(user.password)

    # 3. Create user
    new_user = User(
        email=user.email,
        password_hash=hashed_password,
        plan="free",
        usage_count=0,
        is_active=True
    )

    # 4. Save to database
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "Signup successful",
        "email": new_user.email,
        "plan": new_user.plan
    }

# ======================
# LOGIN
# ======================

@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()

    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # ✅ CREATE TOKEN
    access_token = create_access_token(
        data={"sub": db_user.email}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.post("/repurpose")
def repurpose(
    data: RepurposeRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    # 1. Decode token
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    email = payload.get("sub")

    # 2. Get user from DB
    db_user = db.query(User).filter(User.email == email).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # 3. Usage limit (FREE = 3)
    if db_user.plan == "free" and db_user.usage_count >= 3:
        raise HTTPException(
        status_code=403,
        detail="Free plan limit reached. Upgrade to Pro."
    )

    # 4. Increase usage
    if db_user.plan == "free":
       db_user.usage_count += 1

    db.commit()

    # 5. Generate content
    result = generate_content(
    text=data.content,
    targets=["twitter"]
)


    return {
        "usage": db_user.usage_count,
        "result": result
    }

@app.post("/upgrade")
def upgrade_to_pro(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    payload = decode_token(credentials.credentials)
    email = payload.get("sub")

    user = db.query(User).filter(User.email == email).first()

    user.plan = "pro"          # 🔥 THIS WAS MISSING
    user.usage_count = 0       # reset usage

    db.commit()

    return {"message": "Upgraded to Pro successfully"}

# ======================
# HEALTH
# ======================
@app.get("/health")
def health():
    return {"status": "ok"}


