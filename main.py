import string, requests
import random
from sqlalchemy import exists, and_
from sqlalchemy import text
import pytz
from typing import Optional
from typing import List
from fastapi import Depends, FastAPI, Request, HTTPException, status, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from database import engine, get_db, Session, SessionLocal
from models import User,Price_per_trip, VerificationCode, UsersSubscription, RidesDetail, Base,Address
from schema import UserSchema,GetPriceSchema,PriceCreateSchema,UserUpdateSchema, RideDetailSchema,UpdateRideStatusSchema, GetRideDetailSchema, CreateUserSubscriptionAndRidesSchema,UserCreate,AddressCreateSchema,AddressSchema,RescheduleRideSchema, UserId
from datetime import datetime, timezone,timedelta
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from collections import deque
from sqlalchemy import func
import models as model
import schema
from datetime import datetime, timedelta



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

# Encryption function
def get_current_user(phone_number: str = Header(..., description="User's phone number"),
                      token: str = Header(..., description="JWT token for authentication")):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") != phone_number:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


def create_jwt_token(phone_number: str, expires_delta: timedelta = None):
    to_encode = {"sub": phone_number}
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def expire_existing_subscription(user_id: int, subscription_plan: str, current_date: datetime):
    try:
        db = SessionLocal()
        existing_subscription = (
            db.query(UsersSubscription)
            .filter(
                UsersSubscription.user_id == user_id,
                UsersSubscription.subscription_plan == subscription_plan,
                UsersSubscription.subscription_status == "active",
                func.date(UsersSubscription.created_at) < func.date(current_date)
            )
            .first()
        )
    
        if existing_subscription:
            existing_subscription.subscription_status = "expired"
            db.commit()
            db.refresh(existing_subscription)
    finally:
        db.close()


def expire_existing_subscriptions(db: Session):
    # try:
    #     today = datetime.now().date()
    #     last_week_start = today - timedelta(days=(today.isoweekday() + 6) % 7)
    #     last_week_end = last_week_start + timedelta(days=5)
    #
    #     print(last_week_end)
    #
    #     subscriptions_to_expire = (
    #         db.query(UsersSubscription)
    #         .filter(
    #             UsersSubscription.subscription_status == "active",
    #             UsersSubscription.payment_status == "true",
    #             UsersSubscription.created_at < last_week_start
    #         )
    #         .all()
    #     )
    #     for subscription in subscriptions_to_expire:
    #         subscription.subscription_status = "expired"
    #
    #     db.commit()
    #
    # except Exception as e:
    #     print(f"An error occurred: {str(e)}")
    # finally:
    #     db.close()

    try:
        '''
        Calculate the start and end dates of the previous week (n - 1 week).
        '''
        today = datetime.now().date()
        previous_week_start = today - timedelta(days=today.weekday() + 7)
        previous_week_end = previous_week_start + timedelta(days=6)

        '''
        Calculate the start and end dates of the upcoming week (n week).
        '''
        next_week_start = today + timedelta(days=(7 - today.weekday()))
        next_week_end = next_week_start + timedelta(days=6)

        subscriptions_to_expire = (
            db.query(UsersSubscription)
            .filter(
                UsersSubscription.subscription_status == "active",
                UsersSubscription.payment_status == "true",
                UsersSubscription.created_at >= previous_week_start,
                UsersSubscription.created_at <= previous_week_end,
                UsersSubscription.id.notin_(
                    db.query(GetRideDetailSchema.subscription_id)
                    .filter(
                        GetRideDetailSchema.ride_date_time >= next_week_start,
                        GetRideDetailSchema.ride_date_time <= next_week_end
                    )
                    .distinct()
                ),
                today.weekday() == 0
            )
            .all()
        )

        '''
        Expire subscriptions.
        '''
        for subscription in subscriptions_to_expire:
            subscription.subscription_status = "expired"

        db.commit()

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        db.rollback()  # Rollback changes in case of an error
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        # If the user does not exist, create a new user with default values or nullable fields
        #background_tasks.add_task(add_newsuser_to_db, phone_number)
    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

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
async def verify_otp(request: Request,phone_number: str, otp: str, db: Session = Depends(get_db)):
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
        decoded_payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Ensure that the phone number from the headers matches the one in the JWT token
        if decoded_payload.get("sub") != phone_number:
            raise credentials_exception
        else:
            # Your business logic here
            user_id = payload.user_id
            subscription_plan = payload.subscription_plan
            ride_details = payload.ride_details

            existing_subscription = db.query(UsersSubscription).filter(
                UsersSubscription.user_id == user_id,
                UsersSubscription.subscription_plan == subscription_plan,
                func.date(UsersSubscription.created_at) == datetime.utcnow().date(),
                UsersSubscription.subscription_status == "active"
            ).first()

            if existing_subscription:
                raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A subscription for the same plan already exists for today."
            )

            # Previous week subscriptions gets expired for the same user when a new subscription is recorded.
            expire_existing_subscription(user_id, subscription_plan, datetime.utcnow())

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
                    pickup_address=ride_data.pickup_address,
                    pickup_address_type = ride_data.pickup_address_type,
                    drop_address=ride_data.drop_address,
                    drop_address_type = ride_data.drop_address_type,
                    ride_date_time=datetime.strptime(ride_data.datetime, "%Y-%m-%d %H:%M:%S.%f"),
                    pickup_latitude=float(ride_data.pickup_lat),
                    pickup_longitude=float(ride_data.pickup_long),
                    drop_latitude=float(ride_data.drop_lat),
                    drop_longitude=float(ride_data.drop_long),
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


@app.post("/create-address")
def create_address(
    phone_number: str,
    address_data: AddressCreateSchema,
    db: Session = Depends(get_db)
):
    # Check if the address already exists in the database
    existing_address = db.query(Address).filter(
        Address.phone_number == phone_number,
        Address.address_type == address_data.address_type
    ).first()

    if existing_address:
        return {
            "error": f"Address with type {address_data.address_type} already exists for phone number {phone_number}"}

    # Create address in the database
    address = Address(
        phone_number=phone_number,
        address_type=address_data.address_type,
        address=address_data.address,
        latitude=address_data.latitude,
        longitude=address_data.longitude
    )

    db.add(address)
    db.commit()
    db.refresh(address)

    # Return a success message as a string
    success_message = f"Successfully added address for phone number: {phone_number}"
    return success_message

@app.get("/get-addresses", response_model=List[AddressSchema])
@limiter.limit("15/minute")
def get_addresses(
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

    # Retrieve addresses from the database for the specified phone number
    addresses = db.query(Address).filter(Address.phone_number == phone_number).all()

    return [AddressSchema(**address.__dict__) for address in addresses]


@app.get("/get-user-subscriptions-and-rides")
def get_user_subscriptions_and_rides(
    phone_number: str = Header(..., description="User's phone number"),
    token: str = Header(..., description="JWT token for authentication"),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") != phone_number:
            raise credentials_exception

        user = db.query(User).filter(User.phone_number == phone_number).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get active subscriptions
        active_subscriptions = (
            db.query(UsersSubscription)
            .filter(
                UsersSubscription.user_id == user.id,
                UsersSubscription.subscription_status == "active"
            )
            .all()
        )
        
        # Collect upcoming rides for active subscriptions
        active_subscription_rides = []
        for subscription in active_subscriptions:
            print(subscription.id)
            rides = (
                db.query(RidesDetail)
                .filter(
                    RidesDetail.subscription_id == subscription.id,
                    # RidesDetail.ride_status == "Upcoming",
                    # RidesDetail.ride_date_time >=  datetime.utcnow()  # Filter upcoming rides
                )
                .all()
            )
             
            active_subscription_rides.extend(rides)
        
        

        # Count non-active subscription rides
        non_active_subscriptions = (
            db.query(UsersSubscription)
            .filter(
                UsersSubscription.user_id == user.id,
                UsersSubscription.subscription_status == "expired"
            )
            .all()
        )

        non_active_subscription_ride_count = sum(
            db.query(RidesDetail)
            .filter(RidesDetail.subscription_id == subscription.id)
            .count()
            for subscription in non_active_subscriptions
        )

        return {
            "user_id": user.id,
            "active_subscriptions": len(active_subscriptions),
            "active_subscription_rides": [GetRideDetailSchema(**ride_detail.__dict__) for ride_detail in active_subscription_rides],
            "non_active_subscription_ride_count": non_active_subscription_ride_count
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    

@app.put("/request-reschedule-ride")
async def reschedule_ride(
    reschedule_data: RescheduleRideSchema,
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
        if payload.get("sub") != phone_number:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Retrieve the ride from the database
    ride = db.query(RidesDetail).filter(RidesDetail.id == reschedule_data.ride_id).first()

    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")

    # Check if the ride is associated with the user
    if ride.user.phone_number != phone_number:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Mark the ride status as "Rescheduled"
    ride.ride_status = "Rescheduled"
    ride.additional_ride_details = str(reschedule_data.new_datetime)

    # # Append the new reschedule datetime to additional_ride_details
    # if not ride.additional_ride_details:
    #     ride.additional_ride_details = str(reschedule_data.new_datetime)
    # else:
    #     ride.additional_ride_details += f", {reschedule_data.new_datetime}"

    db.commit()
    db.refresh(ride)

    return GetRideDetailSchema(**ride.__dict__)

@app.put("/cancel-ride/{ride_id}")
def cancel_ride(
    ride_id: int,
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
        if payload.get("sub") != phone_number:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Retrieve the ride from the database
    ride = db.query(RidesDetail).filter(RidesDetail.id == ride_id).first()

    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")

    # Check if the ride is associated with the user
    if ride.user.phone_number != phone_number:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Mark the ride status as "Cancelled"
    # Make a request to the other endpoint
    cancel_customer_ride_url = 'https://driverappbackend.onrender.com/api/cancelCustomerRide/'
    # # cancel_customer_ride_url = 'http://127.0.0.1:8000/api/cancelCustomerRide/'
    data = {"customer_ride_id": ride_id}
    # print(data)
    #
    # headers = {
    #     'Content-Type': 'application/json',
    #     'Authorization': f'Bearer {token}'  # Assuming your token is used for authentication
    # }
    #
    response = requests.post(cancel_customer_ride_url, json=data)
    #
    # Check the response status code
    if response.status_code != 200:

        raise HTTPException(status_code=500, detail="Failed to cancel customer ride from driver backend side")

    ride.ride_status = "Cancelled"

    db.commit()
    db.refresh(ride)

    return f"Ride with Ride ID {ride_id} Cancelled"


# Api for Admin Dashboard
@app.get("/getUserRides")
def get_user_subscriptions_and_rides(
    phone_number: str ,
    db: Session = Depends(get_db)
):
    
    try:

        user = db.query(User).filter(User.phone_number == phone_number).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get active subscriptions
        active_subscriptions = (
            db.query(UsersSubscription)
            .filter(
                UsersSubscription.user_id == user.id,
                UsersSubscription.subscription_status == "active"
            )
            .all()
        )
        
        # Collect upcoming rides for active subscriptions
        active_subscription_rides = []
        for subscription in active_subscriptions:
            print(subscription.id)
            rides = (
                db.query(RidesDetail)
                .filter(
                    RidesDetail.subscription_id == subscription.id,
                    RidesDetail.ride_status == "Upcoming",
                    # RidesDetail.ride_date_time >=  datetime.utcnow()  # Filter upcoming rides
                )
                .all()
            )
             
            active_subscription_rides.extend(rides)


        return {
            "user_id": user.id,
            "active_subscription_rides": [GetRideDetailSchema(**ride_detail.__dict__) for ride_detail in active_subscription_rides],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.put("/edit_ride_driver_phone/{ride_id}")
def edit_ride_driver_phone(ride_id: int, driver_phone: str, db: Session = Depends(get_db)):
    """
    Edit the driver phone for a specific ride.
    """
    ride = db.query(RidesDetail).filter(RidesDetail.id == ride_id).first()
    if ride is None:
        raise HTTPException(status_code=404, detail="Ride not found")
    
    ride.driver_phone = driver_phone
    db.commit()
    db.refresh(ride)
    
    return {"message": f"Driver Phone updated successfully for Ride ID: {ride_id} to {driver_phone}"}


@app.put("/reschedule_ride/")
# @limiter.limit("50/minute")
async def reschedule_ride(request: Request, reschedule_data: RescheduleRideSchema, db: Session = Depends(get_db)):
    """
    Reschedule the date and time for a specific ride.
    """
    ride = db.query(RidesDetail).filter(RidesDetail.id == reschedule_data.ride_id).first()
    if ride is None:
        raise HTTPException(status_code=404, detail="Ride not found")
    
    new_datetime = reschedule_data.new_datetime

    
    # Make an internal request to the specified URL
    ride.ride_date_time = new_datetime
    ride.ride_status = "Upcoming"
    
    db.commit()

    return {"message": f"Ride Datetime updated successfully for Ride ID: {reschedule_data.ride_id} to {new_datetime}"}


@app.put("/approve_reschedule_ride/")
# @limiter.limit("50/minute")
async def approve_reschedule_ride(request: Request, reschedule_data: RescheduleRideSchema, db: Session = Depends(get_db)):
    """
    Reschedule the date and time for a specific ride.
    """
    ride = db.query(RidesDetail).filter(RidesDetail.id == reschedule_data.ride_id).first()
    if ride is None:
        raise HTTPException(status_code=404, detail="Ride not found")

    new_datetime = reschedule_data.new_datetime

    '''
    Make an internal request to the specified URL.
    '''
    ride.ride_date_time = new_datetime
    ride.ride_status = "Upcoming"
    ride.additional_ride_details = "Approved"

    db.commit()

    return {"message": f"Ride Datetime updated successfully for Ride ID: {reschedule_data.ride_id} to {new_datetime}"}


@app.put("/reject_reschedule_ride/")
@limiter.limit("50/minute")
async def reject_reschedule_ride(request: Request, reschedule_data: RescheduleRideSchema, db: Session = Depends(get_db)):
    """
    Reschedule the date and time for a specific ride.
    """
    ride = db.query(RidesDetail).filter(RidesDetail.id == reschedule_data.ride_id).first()
    if ride is None:
        raise HTTPException(status_code=404, detail="Ride not found")


    '''
    Reject flow for a reschedule ride.
    '''

    ride.ride_status = "Upcoming"
    ride.additional_ride_details = "Reject"

    db.commit()

    return {"message": f"Ride is rejected for Ride ID: {reschedule_data.ride_id}"}



@app.get("/get-last-subscription-details")
@limiter.limit("15/minute")
async def get_latest_subscription(
    request: Request,
    user_id: int,
    subscription_plan: str,
    db: Session = Depends(get_db)
):

    expire_existing_subscriptions(db)
    
    try:
        # Query the database to get the most recent subscriptions with the specified criteria
        latest_subscriptions = (
            db.query(UsersSubscription)
            .filter(
                UsersSubscription.user_id == user_id,
                UsersSubscription.subscription_plan.ilike(f"%{subscription_plan}%")
            )
            .order_by(UsersSubscription.created_at.desc())
            .limit(2)  # Limit to the top 2 subscriptions
            .all()
        )

        # if not latest_subscriptions:
        #     return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matching subscription found")
        #
        # if len(latest_subscriptions) == 1:
        #     # Only one subscription, return the message
        #     return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Second latest subscription does not exist")

        if len(latest_subscriptions) < 2:
            '''
            If there are less than 2 subscriptions, return an empty response.
            '''
            return None

        second_latest_subscription = latest_subscriptions[1]

        subscription_rides = (
            db.query(RidesDetail)
            .filter(RidesDetail.subscription_id == second_latest_subscription.id, model.RidesDetail.driver_phone.isnot(None))
            .all()
        )

        if not subscription_rides:
            return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No rides found for the second-latest subscription")

        canceled_rides = 0
        completed_rides = 0

        for ride in subscription_rides:
            if ride.ride_status == "Cancelled":
                canceled_rides += 1
            elif ride.ride_status == "Completed":
                completed_rides += 1

        ride_stats = {
            "subscription_date": second_latest_subscription.created_at,
            "total_rides": len(subscription_rides),
            "canceled_rides": canceled_rides,
            "completed_rides": completed_rides
        }

        return ride_stats

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")

    

@app.put("/updateRideStatus")
async def update_ride_status(
    ride_id: int,
    update_data: UpdateRideStatusSchema,
    db: Session = Depends(get_db)
):
    try:
        # Query the database to get the ride with the specified ride_id
        ride = db.query(RidesDetail).filter(RidesDetail.id == ride_id).first()

        if not ride:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ride not found")

        # Update the ride status based on the provided data
        new_status = update_data.newStatus  # Assuming newStatus is a string (e.g., "completed", "cancelled", "upcoming")
        if new_status not in ["Completed", "Cancelled", "Ongoing","Upcoming", "Rejected"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ride status")

        ride.ride_status = new_status
        db.commit()
        db.refresh(ride)

        return GetRideDetailSchema(**ride.__dict__)

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")


@app.post("/create-user-price")
def create_address(
    price_data: PriceCreateSchema,
    db: Session = Depends(get_db)
):
    # Create address in the database
    price = Price_per_trip(
        phone_number=price_data.phone_number,
        price_per_trip=price_data.price_per_trip
    )

    db.add(price)
    db.commit()

    # Return a success message as a string
    success_message = f"Successfully added price for phone number: {price_data.phone_number}"
    return success_message

@app.post("/update-user-price")
async def update_price_per_trip(
    price_data: PriceCreateSchema,
    db: Session = Depends(get_db)
):
    try:
        price_per_trip = db.query(Price_per_trip).filter(Price_per_trip.phone_number == price_data.phone_number).first()

        if not price_per_trip:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Price per trip not found")

        # Update the price data
        for key, value in price_data.dict().items():
            setattr(price_per_trip, key, value)

        db.commit()


        return f"Successfully Updated price for phone number: {price_data.phone_number}"

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")
    
@app.get("/get-price/{phone_number}", response_model=GetPriceSchema)
async def get_price_by_phone_number(phone_number: str, db: Session = Depends(get_db)):
    price = db.query(Price_per_trip).filter(Price_per_trip.phone_number == phone_number).first()
    if not price:
        raise HTTPException(status_code=404, detail=f"Price for phone number {phone_number} not found")
    
    return price

@app.get("/payment_status_of_latest_Subs/")
def get_payment_status(user_id : str,
                        token: str = Header(..., description="JWT token for authentication"),
                       phone_number: str = Header(..., description="User's phone number"),
                       db: Session = Depends(get_db)):
    
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
    #Res- payment status of the user_id of the latest subscription-Boolean
    subquery = (
        db.query(func.max(model.UsersSubscription.created_at))
        .filter(model.UsersSubscription.user_id == user_id)
        .scalar()
    )
    
    payment_status = db.query(model.UsersSubscription.payment_status).filter(
            model.UsersSubscription.user_id == user_id).filter(
            model.UsersSubscription.subscription_status == "active").filter(
            model.UsersSubscription.created_at == subquery).scalar()

    subscription_id = db.query(model.UsersSubscription.id).filter(
            model.UsersSubscription.user_id == user_id).filter(
            model.UsersSubscription.subscription_status == "active").filter(
            model.UsersSubscription.created_at == subquery).scalar()
    
    return {"payment_status" : payment_status,
            "subscription_id" : subscription_id}


@app.get("/Latest_subscription_ride_count/")
def get_ride_count_status(user_id: Optional[str] = None,
                          token: str = Header(..., description="JWT token for authentication"),
                          phone_number: str = Header(..., description="User's phone number"),
                          db: Session = Depends(get_db)):
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

    '''
    Handling of null string to None
    '''

    if user_id == 'null':
        user_id = None


    '''
    count of no of rides in the latest subscription
    '''

    subscription_ids = (
        db.query(model.UsersSubscription.id)
        .join(model.RidesDetail, model.UsersSubscription.id == model.RidesDetail.subscription_id)
        .filter(
            model.UsersSubscription.user_id == user_id,
            model.UsersSubscription.subscription_status == "active",
            model.UsersSubscription.payment_status == "false"
        )
        .all()
    )

    '''
    Now fetching only those active user's rides where driver_phone is attached.
    The query also Filter for rides where driver_phone is assigned.
    '''

    # subscription_ids = (
    #     db.query(model.UsersSubscription.id)
    #     .join(model.RidesDetail, model.UsersSubscription.id == model.RidesDetail.subscription_id)
    #     .filter(
    #         model.UsersSubscription.user_id == user_id,
    #         model.UsersSubscription.subscription_status == "active",
    #         model.RidesDetail.driver_phone.isnot(None)
    #     )
    #     .all()
    # )

    # total_count = len(subscription_ids)

    total_count = 0

    for i in subscription_ids:
        count = (db.query(func.count())
                .filter(model.RidesDetail.subscription_id == i.id)
                .filter(model.RidesDetail.driver_phone.isnot(None))
                .scalar())
        total_count = count

    return total_count

@app.put("/change-address-of-user/")
def change_address_of_user( user_id : int, old_address_type : str ,new_address : AddressCreateSchema, db: Session = Depends(get_db)):
    
    user = db.query(User).filter(User.id == user_id).first()
    
    # Check if the user exists
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    phone_number = user.__dict__['phone_number']

    # Update the address
    updat_address = db.query(Address).filter(Address.phone_number == phone_number).filter(Address.address_type == old_address_type).first()
    print(updat_address)
    
    if updat_address == None:
        return(f"Address for id {user_id} is not present, add this user in user address")
    
    updat_address.address = new_address.address
    updat_address.address_type = new_address.address_type
    updat_address.latitude = new_address.latitude
    updat_address.longitude = new_address.longitude

    db.commit()
    
    return {"message" : f"{new_address}"}

#Make an api to change the phone number of user
@app.put('/update_phone_number/')
def update_phone_number(user_id: int, phone_number_data: schema.UpdatePhoneNumberSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Extract the phone_number value from the schema
    new_phone_number = phone_number_data.phone_number

    # Check if the new phone number is different from the existing one
    if user.phone_number != new_phone_number:
        user.phone_number = new_phone_number
        db.commit()
        return {"message": f"Phone number updated to {new_phone_number}"}
    else:
        return {"message": "Phone number is already set to the provided value"}

#Make an api to change the status of user - active or inactive
@app.put('/update_active_status/')
def update_active_status(user_id : int, activity : schema.UpdateActivityStatus, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    activity = activity.is_active
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if activity == True:
        user.active = True
    elif activity == False:
        user.active = False
    else:
        return {"Error":"Invalid data sent."}
    
    db.commit()
    
    return {"message" : f"for user {user} the activity status has been changed to  {activity}"}

#Make an api to change the payment_status
@app.put('/update_payment_status/')
def update_active_status(user_id : int, act_st : schema.UpdatePaymentStatusSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sub_id = act_st.subs_id
    act = act_st.to_active
    sub_cost = act_st.subs_cost
    
    subscription = db.query(UsersSubscription).filter(UsersSubscription.id == sub_id).first()

    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    if act in [True,False]:
        subscription.payment_status = act
        subscription.subscription_cost = sub_cost

        db.commit()
        return {"status": "success", "message": "Subscription updated successfully"}
    else:
        return {"Error": "Invalid data sent."}

@app.get("/rescheduled-rides", response_model=List[GetRideDetailSchema])
def get_rescheduled_rides(
    db: Session = Depends(get_db)
):

    rescheduled_rides = db.query(RidesDetail).filter(RidesDetail.ride_status == "Rescheduled").all()

    # Convert the rides to the response model
    rescheduled_rides_schema = [GetRideDetailSchema(**ride.__dict__) for ride in rescheduled_rides]

    return rescheduled_rides_schema


@app.get("/getRidesCountByUser/{user_id}")
def get_rides_count_by_user(user_id: int, db: Session = Depends(get_db)):
    user_exists = db.query(exists().where(RidesDetail.user_id == user_id)).scalar()
    if not user_exists:
        raise HTTPException(status_code=404, detail="Invalid user_id or user does not exist")

    now_ist = datetime.now(pytz.timezone('Asia/Kolkata'))
    start_of_prev_week = now_ist - timedelta(days=now_ist.weekday() + 7)
    start_of_prev_week, end_of_prev_week = set_start_end_times(start_of_prev_week)
    start_of_prev_prev_week = now_ist - timedelta(days=now_ist.weekday() + 7)
    start_of_prev_prev_week, end_of_prev_prev_week = set_start_end_times(start_of_prev_prev_week)
    start_of_current_week = now_ist - timedelta(days=now_ist.weekday())
    start_of_current_week, end_of_current_week = set_start_end_times(start_of_current_week)

    findSecondLastCreatedAt = find_second_last_created_at(db, user_id)
    previousWeekCustomerNotSubscribed = is_customer_not_subscribed(db, user_id, start_of_current_week,
                                                                   end_of_current_week, None)

    if previousWeekCustomerNotSubscribed:
        return get_rides_info_from_last_created_at(db, user_id, findSecondLastCreatedAt)


    previousWeekPaidSubscribedCustomers = is_customer_subscribed(db, user_id, start_of_prev_week, end_of_prev_week, 'true')
    previousWeekNotPaidSubscribedCustomers = is_customer_subscribed(db, user_id, start_of_prev_week, end_of_prev_week, 'false')
    currentWeekNotPaidSubscribedCustomers = is_customer_subscribed(db, user_id, start_of_current_week, end_of_current_week, 'false')


    if previousWeekPaidSubscribedCustomers:
        return get_rides_info(db, user_id, start_of_prev_week, end_of_prev_week)

    if previousWeekNotPaidSubscribedCustomers:
        return get_rides_info(db, user_id, start_of_prev_prev_week, end_of_prev_prev_week)

    if currentWeekNotPaidSubscribedCustomers:
        return get_rides_info(db, user_id, start_of_prev_week, end_of_prev_week)

    return {"message": "No data found for the user in the specified weeks"}

def find_second_last_created_at(db, user_id):

    max_created_at_subquery = db.query(func.max(UsersSubscription.created_at)).filter(
        UsersSubscription.user_id == user_id
    ).scalar_subquery()

    # Query to find the second maximum created_at
    second_max_created_at = db.query(func.max(UsersSubscription.created_at)).filter(
        UsersSubscription.user_id == user_id,
        UsersSubscription.created_at < max_created_at_subquery
    ).scalar()

    return second_max_created_at


def set_start_end_times(start_time):
    start_time = start_time.replace(hour=0, minute=1, second=0)
    end_time = start_time + timedelta(days=6)
    end_time = end_time.replace(hour=23, minute=0, second=0)
    return start_time, end_time

def is_customer_subscribed(db, user_id, start_time, end_time, status):
    return db.query(UsersSubscription).filter(
        UsersSubscription.user_id == user_id,
        UsersSubscription.payment_status == status,
        UsersSubscription.created_at >= start_time,
        UsersSubscription.created_at <= end_time
    ).first() is not None

def is_customer_not_subscribed(db, user_id, start_time, end_time, status):
    return db.query(UsersSubscription).filter(
        UsersSubscription.user_id == user_id,
        UsersSubscription.payment_status == status,
        UsersSubscription.created_at >= start_time,
        UsersSubscription.created_at <= end_time
    ).first() is None

def get_rides_info_from_last_created_at(db, user_id, last_created_at):
    start_time = last_created_at
    print(start_time)
    end_time = datetime.now(pytz.timezone('Asia/Kolkata'))
    print(end_time)
    return get_rides_info(db, user_id, start_time, end_time)

def get_rides_info(db, user_id, start_time, end_time):
    cancelled_rides_count = db.query(func.count(RidesDetail.id)).filter(
        RidesDetail.user_id == user_id,
        RidesDetail.ride_status == "Cancelled",
        RidesDetail.ride_date_time >= start_time,
        RidesDetail.ride_date_time <= end_time
    ).scalar()



    completed_rides_count = db.query(func.count(RidesDetail.id)).filter(
        RidesDetail.user_id == user_id,
        RidesDetail.ride_status == "Completed",
        RidesDetail.ride_date_time >= start_time,
        RidesDetail.ride_date_time <= end_time
    ).scalar()

    total_rides_count = completed_rides_count + cancelled_rides_count

    return {
        "cancelled_rides_count": cancelled_rides_count,
        "completed_rides_count": completed_rides_count,
        "total_rides_count": total_rides_count
    }
@app.post("/assignRidesToCabFleet")
def assign_rides_to_cab_fleet(ride_ids: List[int], db: Session = Depends(get_db)):
    try:
        for ride_id in ride_ids:

            ride = db.query(RidesDetail).filter(RidesDetail.id == ride_id).first()

            if ride and ride.ride_status == "Upcoming":
                ride.additional_ride_details = "cab_assigned"
                response = requests.post('https://driverappbackend.onrender.com/api/triggerRideCategory/',
                                         json={"customer_cab_ride_id": ride_id})
                response.raise_for_status()
            else:
                raise HTTPException(status_code=404,
                                    detail=f"Ride with ID {ride_id} not found or not in 'Upcoming' status")

        db.commit()

        return {"message": f"Tags successfully attached to rides {ride_ids}"}


    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            return {"error": "Bad request: Invalid data sent to driver app API"}
        else:
            return {"error": f"HTTPError: {e.response.status_code} - {e.response.reason}"}












