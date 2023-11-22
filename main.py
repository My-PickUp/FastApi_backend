
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine, SessionLocal
from schema import OfficeBooking, SchoolBooking
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import List
from slowapi.errors import RateLimitExceeded
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address




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

class OfficeBookingCreate(BaseModel):
    name: str
    mobile: str
    pickup_location: str
    drop_location: str
    gender: str
    pickup_time: str
    return_time: str = None
    want_return: bool
    selected_days: List[str]

class SchoolBookingCreate(BaseModel):
    name: str
    age: int
    mobile: str
    pickup_location: str
    drop_location: str
    gender: str
    pickup_time: str
    return_time: str = None
    date: str


@app.get('/awake')
@limiter.limit("5/minute")
async def awake(request: Request):
    return {'message': 'I am awake'}


@app.post('/officeBookings')
@limiter.limit("5/minute")
async def office_booking_list_create(request: Request,booking_data: OfficeBookingCreate):
    db = SessionLocal()
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
async def school_booking_list_create(request: Request,booking_data: SchoolBookingCreate):
    db = SessionLocal()
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
       
