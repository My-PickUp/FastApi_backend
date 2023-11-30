import string, threading
import random
import models
from fastapi import Depends, FastAPI, Request, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from database import engine, get_db, Session, SessionLocal
from models import User, VerificationCode, UsersSubscription, RidesDetail, Base
from schema import UserSchema,UserUpdateSchema
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

# def delete_otp(phone_number: str):
#     try:
#         db = SessionLocal()
#         # Delete all OTPs for the specified phone number
#         db.query(VerificationCode).filter(
#             VerificationCode.phone_number == phone_number
#         ).delete()

#         db.commit()
#     finally:
#         db.close()


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

    user = db.query(User).filter(User.phone_number == phone_number).first()

    if not user:
        # If the user does not exist, create a new user with default values or nullable fields
        new_user = User(phone_number=phone_number, name=phone_number)  # Set default values or nullable fields
        db.add(new_user)
        db.commit()

        # Now, the user variable refers to the newly created user
        user = new_user

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

@app.get("/get-user-details", response_model=UserSchema)
def get_user_details(
    phone_number: str = Header(..., description="User's phone number"),
    token: str = Header(..., description="JWT token for authentication"),
    db: Session = Depends(get_db)
):
    # Verify the JWT token
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Ensure that the phone number from the headers matches the one in the JWT token
        if payload.get("sub") != phone_number:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Retrieve user details from the database
    user = db.query(User).filter(User.phone_number == phone_number).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return UserSchema(**user.__dict__)

@app.put("/update-user-details", response_model=UserSchema)
def update_user_details(
    update_data: UserUpdateSchema,  # Change to UserSchema
    phone_number: str = Header(..., description="User's phone number"),
    token: str = Header(..., description="JWT token for authentication"),
    db: Session = Depends(get_db)
):
    # Verify the JWT token
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Ensure that the phone number from the headers matches the one in the JWT token
        if payload.get("sub") != phone_number:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    if all(value is None or value == "string" for value in update_data.dict().values()):
        raise HTTPException(status_code=400, detail="No valid details provided for update")


    # Retrieve user from the database
    user = db.query(User).filter(User.phone_number == phone_number).first()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Update user details based on the data provided in the request
    for field, value in update_data.dict(exclude_unset=True).items():
        # If the value is not None, update the user field
        if value is not None and value != "string":
            setattr(user, field, value)

    # Update the 'updated_at' field
    user.updated_at = datetime.utcnow()

    db.commit()

    # Fetch the updated user from the database
    updated_user = db.query(User).filter(User.phone_number == phone_number).first()

    # Return the updated user details
    return UserSchema(**updated_user.__dict__)