import string, threading
import random
import models
from fastapi import Depends, FastAPI, Request, HTTPException, status, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from database import engine, get_db, Session, SessionLocal
from models import User, VerificationCode, UsersSubscription, RidesDetail, Base
from schema import UserSchema,UserUpdateSchema, RideDetailSchema, CreateUserSubscriptionAndRidesSchema,UserCreate
from datetime import datetime, timezone,timedelta
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from collections import deque




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


# Threading/Backgound Functions for multiple threads

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

########### OTP Add to the db ############
async def add_otp_to_db(phone_number,otp_number):
    try:
        db = SessionLocal()
        db_otp = VerificationCode(phone_number=phone_number, code=otp_number)
        db.add(db_otp)
        db.commit()
    finally:
        db.close()
        

########### OTP Add to the db ############
async def add_newsuser_to_db(phone_number):
    try:
        db = SessionLocal()
        new_user = User(phone_number=phone_number, name=phone_number)  # Set default values or nullable fields
        db.add(new_user)
        db.commit()
    finally:
        db.close()
        





########### OTP Generation ############
otp_queue = deque()

async def refill_otp():
    new_otps = [''.join(random.choices(string.digits, k=6)) for _ in range(20)]
    otp_queue.extend(new_otps)

#Intial Generation
refill_otp()



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


def expire_existing_subscription(user_id: int, subscription_plan: str):
    try:
        db = SessionLocal()
        existing_subscription = (
            db.query(UsersSubscription)
            .filter(
                UsersSubscription.user_id == user_id,
                UsersSubscription.subscription_plan == subscription_plan,
                UsersSubscription.subscription_status == "active"
            )
            .first()
        )
    
        if existing_subscription:
            existing_subscription.subscription_status = "expired"
            db.commit()
            db.refresh(existing_subscription)
    finally:
        db.close()



# API Endpoints

@app.get('/awake')
@limiter.limit("5/minute")
async def awake(request: Request):
    return {'message': 'I am awake'}

# Endpoint to generate and send OTP to the user
@app.post("/auth/generate-otp", response_model=None)
@limiter.limit("15/minute")
async def generate_otp(request: Request, phone_number: str, background_tasks: BackgroundTasks,  db: Session = Depends(get_db)):

    user = db.query(User).filter(User.phone_number == phone_number).first()

    if not user:
        # If the user does not exist, create a new user with default values or nullable fields
        background_tasks.add_task(add_newsuser_to_db, phone_number)

    # Generate a 6-digit OTP
    if otp_queue:
        otp = otp_queue.popleft()
    else:
        otp = ''.join(random.choices(string.digits, k=6))
    # Start otp queue refill background non thread blocking task
    background_tasks.add_task(refill_otp)
    
    background_tasks.add_task(add_otp_to_db, phone_number, otp)

    return {"otp": otp}

# Endpoint to verify OTP and return JWT token
@app.post("/auth/verify-otp")
@limiter.limit("15/minute")
def verify_otp(request: Request,phone_number: str, otp: str, db: Session = Depends(get_db)):
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

    return {"access_token": access_token}

@app.get("/get-user-details", response_model=UserSchema)
@limiter.limit("15/minute")
def get_user_details(
    request: Request,
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
@limiter.limit("15/minute")
def update_user_details(
    request: Request,
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


@app.post("/create_user_subscription_and_rides")
async def create_user_subscription_and_rides(
    payload: CreateUserSubscriptionAndRidesSchema,
    phone_number: str = Header(..., description="User's phone number"),
    token: str = Header(..., description="JWT token for authentication"),
    db: Session = Depends(get_db)
):
    

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
        else:
            # Your business logic here
            user_id = payload.user_id
            subscription_plan = payload.subscription_plan
            ride_details = payload.ride_details

            # Expire existing active subscription for the same plan
            expire_existing_subscription(db, user_id, subscription_plan)

            # Create user subscription
            user_subscription = UsersSubscription(
                user_id=user_id,
                subscription_plan=subscription_plan
            )
            db.add(user_subscription)
            db.commit()
            db.refresh(user_subscription)

            # Create ride details for each entry in ride_details
            for ride_data in ride_details:
                ride_detail = RidesDetail(
                    user_id=user_id,
                    subscription_id=user_subscription.id,
                    start_location=ride_data.pickup_address,
                    end_location=ride_data.drop_address,
                    ride_date_time=datetime.strptime(ride_data.datetime, "%Y-%m-%d %H:%M:%S"),
                    start_latitude=float(ride_data.pickup_lat),
                    start_longitude=float(ride_data.pickup_long),
                    end_latitude=float(ride_data.drop_lat),
                    end_longitude=float(ride_data.drop_long),
                )
                db.add(ride_detail)
                db.commit()
                db.refresh(ride_detail)

    except JWTError:
        raise credentials_exception
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

    return {"Subscription ID": user_subscription.id}

# Temporary

@app.post("/leadtodb", response_model=str)
async def create_user(user_create: UserCreate, db: Session = Depends(get_db)):
    db_user = User(**user_create.dict(), created_at=datetime.now(), updated_at=datetime.now())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return "User created successfully"