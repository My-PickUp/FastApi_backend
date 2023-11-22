from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Boolean, ARRAY, func
from database import Base

class OfficeBooking(Base):
    __tablename__ = 'office_bookings'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    mobile = Column(String, unique=True)
    pickup_location = Column(String)
    drop_location = Column(String)
    gender = Column(String)
    pickup_time = Column(String)
    return_time = Column(String, nullable=True)
    want_return = Column(Boolean)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    selected_days = Column(String) 

class SchoolBooking(Base):
    __tablename__ = 'school_bookings'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    age = Column(Integer)
    mobile = Column(String, unique=True)
    pickup_location = Column(String)
    drop_location = Column(String)
    gender = Column(String)
    pickup_time = Column(String)
    return_time = Column(String, nullable=True)
    date = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
