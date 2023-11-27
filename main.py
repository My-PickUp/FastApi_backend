
import string, threading
import random
from fastapi import Depends, FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine, get_db, Session, SessionLocal
from models import User, VerificationCode
# from schema import 
from datetime import datetime, timezone,timedelta
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt




Base.metadata.create_all(bind=engine)
limiter = Limiter(key_func=get_remote_address)
app = FastAPI()


SECRET_KEY = "@@_tge=7tux=#o-@hn_%ri2q#7qcs-q^qul!)&4tegy6j4&+=x"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 14400 # 10 days

#Rate limit
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)



# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Threading Functions for multiple threads

def delete_otp(phone_number: str):
    try:
        db = SessionLocal()
        # Delete all OTPs for the specified phone number
        db.query(VerificationCode).filter(
            VerificationCode.phone_number == phone_number
        ).delete()

        db.commit()
    finally:
        db.close()


# Helper functions
def create_jwt_token(phone_number: str, expires_delta: timedelta = None):
    to_encode = {"sub": phone_number}
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# API Endpoints

@app.get('/awake')
@limiter.limit("5/minute")
async def awake(request: Request):
    return {'message': 'I am awake'}

# Endpoint to generate and send OTP to the user
@app.post("/auth/generate-otp", response_model=None)
def generate_otp(phone_number: str, db: Session = Depends(get_db)):

    thread = threading.Thread(target=delete_otp, args=(phone_number))
    thread.start()
 
    user = db.query(User).filter(User.phone_number == phone_number).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Generate a 6-digit OTP
    otp = ''.join(random.choices(string.digits, k=6))

    # Store the OTP in the database
    db_otp = VerificationCode(phone_number=phone_number, code=otp)
    db.add(db_otp)
    db.commit()

    # Send OTP to the user (replace with your actual implementation)
    # send_otp(phone_number, otp)

    return {"otp": otp}

# Endpoint to verify OTP and return JWT token
@app.post("/auth/verify-otp", response_model=str)
def verify_otp(phone_number: str, otp: str, db: Session = Depends(get_db)):
    stored_otp = db.query(VerificationCode).filter(
        VerificationCode.phone_number == phone_number,
        VerificationCode.code == otp,
        VerificationCode.status == "active"
    ).first()

    if not stored_otp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid OTP",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Update OTP status to "expired" after successful verification
    stored_otp.status = "expired"
    db.commit()

    # Generate JWT token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_jwt_token(phone_number, expires_delta=access_token_expires)

    return access_token