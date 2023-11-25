
from fastapi import Depends, FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine, get_db
from models import OfficeBooking, SchoolBooking, OTP
from schema import OfficeBookingCreate, SchoolBookingCreate,OTPRequest,OTPVerification
from datetime import datetime, timezone
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
import random
from string import digits




Base.metadata.create_all(bind=engine)
limiter = Limiter(key_func=get_remote_address)
app = FastAPI()

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


@app.get('/awake')
@limiter.limit("5/minute")
async def awake(request: Request):
    return {'message': 'I am awake'}


@app.post('/generate-otp', status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def generate_otp(request: Request, otp_request: OTPRequest, db: Session = Depends(get_db)):
    phone_number = otp_request.phone_number
    otp = ''.join(random.choice(digits) for _ in range(6))

    # Ensure the generated OTP is not present in previous OTPs
    while db.query(OTP).filter_by(otp=otp).first():
        otp = ''.join(random.choice(digits) for _ in range(6))

    otp_entry = OTP(phone_number=phone_number, otp=otp)
    db.add(otp_entry)
    db.commit()
    return {'message': 'OTP generated successfully',
            'OTP':otp}

@app.post('/verify-otp')
@limiter.limit("5/minute")
async def verify_otp(request: Request, otp_verification: OTPVerification, db: Session = Depends(get_db)):
    phone_number = otp_verification.phone_number
    otp_entered = otp_verification.otp

    # Retrieve stored OTP from the database
    otp_entry = db.query(OTP).filter_by(phone_number=phone_number, otp=otp_entered).first()

    if not otp_entry:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid OTP')

    # If OTP is valid, retrieve associated bookings
    office_bookings = db.query(OfficeBooking).filter_by(mobile=phone_number).all()
    school_bookings = db.query(SchoolBooking).filter_by(mobile=phone_number).all()

    return {'office_bookings': office_bookings, 'school_bookings': school_bookings}




@app.post('/officeBookings')
@limiter.limit("5/minute")
async def office_booking_list_create(request: Request,booking_data: OfficeBookingCreate, db: Session = Depends(get_db)):
    mobile = booking_data.mobile
    existing_booking = db.query(OfficeBooking).filter_by(mobile=mobile).first()

    if existing_booking:
        # Update existing entry
        existing_booking.name = booking_data.name
        existing_booking.pickup_location = booking_data.pickup_location
        existing_booking.drop_location = booking_data.drop_location
        existing_booking.pickup_time = booking_data.pickup_time
        existing_booking.return_time = booking_data.return_time
        existing_booking.want_return = booking_data.want_return
        existing_booking.selected_days = booking_data.selected_days  # Concatenate the days

        db.commit()
        db.refresh(existing_booking)
        return existing_booking

    else:
        
        # Create a new entry
        booking = OfficeBooking(
            name=booking_data.name,
            mobile=booking_data.mobile,
            pickup_location=booking_data.pickup_location,
            drop_location=booking_data.drop_location,
            gender=booking_data.gender,
            pickup_time=booking_data.pickup_time,
            return_time=booking_data.return_time,
            want_return=booking_data.want_return,
            created_at=datetime.now(timezone.utc),
            selected_days= ' '.join(booking_data.selected_days)# Concatenate the days
        )

        db.add(booking)
        db.commit()
        db.refresh(booking)
        return booking


@app.post('/schoolBookings')
@limiter.limit("5/minute")
async def school_booking_list_create(request: Request,booking_data: SchoolBookingCreate, db: Session = Depends(get_db)):
    mobile = booking_data.mobile
    existing_booking = db.query(SchoolBooking).filter_by(mobile=mobile).first()

    if existing_booking:
        existing_booking.name = booking_data.name
        existing_booking.pickup_location = booking_data.pickup_location
        existing_booking.drop_location = booking_data.drop_location
        existing_booking.pickup_time = booking_data.pickup_time
        existing_booking.return_time = booking_data.return_time
        existing_booking.age = booking_data.age
        existing_booking.date = booking_data.date

        db.commit()
        db.refresh(existing_booking)
        return existing_booking

    else:
        booking = SchoolBooking(
            name=booking_data.name,
            age=booking_data.age,
            mobile=booking_data.mobile,
            pickup_location=booking_data.pickup_location,
            drop_location=booking_data.drop_location,
            gender=booking_data.gender,
            pickup_time=booking_data.pickup_time,
            return_time=booking_data.return_time,
            date=booking_data.date,
            created_at=datetime.now(timezone.utc),
        )

        db.add(booking)
        db.commit()
        db.refresh(booking)
       
