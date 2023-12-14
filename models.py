from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float, func
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, index=True, unique=True, nullable=False)
    name = Column(String, nullable=False)  # Add this field
    email = Column(String, nullable=True)
    pickup_address = Column(String, nullable=True)
    dropoff_address = Column(String, nullable=True)
    active = Column(Boolean, default=True)
    gender = Column(String, nullable=True)
    profile_photo = Column(String, nullable=True)  # Set nullable to True
    emergency_contact_name = Column(String, nullable=True)  # Set nullable to True
    emergency_contact_phone = Column(String, nullable=True)  # Set nullable to True
    created_at = Column(DateTime, default=func.now())  # Add this field
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())  # Add this field

    subscriptions = relationship("UsersSubscription", back_populates="user")
    rides = relationship("RidesDetail", back_populates="user")


class UsersSubscription(Base):
    __tablename__ = "users_subscription"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    subscription_plan = Column(String, nullable=False)
    payment_status = Column(String,default=False,nullable=False)
    subscription_status = Column(String, default="active")

    user = relationship("User", back_populates="subscriptions", remote_side="User.id")  # Set remote_side to User.id
    rides = relationship("RidesDetail", back_populates="subscription")


class RidesDetail(Base):
    __tablename__ = "rides_detail"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id")) 
    driver_id = Column(Integer, ForeignKey("drivers.id"))
    subscription_id = Column(Integer, ForeignKey("users_subscription.id"))
    start_location = Column(String)
    start_latitude = Column(Float)
    start_longitude = Column(Float)
    end_location = Column(String)
    end_latitude = Column(Float)
    end_longitude = Column(Float)
    ride_date_time = Column(DateTime, default=datetime.utcnow)
    ride_status = Column(String)
    additional_ride_details = Column(String)

    user = relationship("User", back_populates="rides")
    subscription = relationship("UsersSubscription", back_populates="rides")
    driver = relationship("Driver", back_populates="rides")


class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)

    rides = relationship("RidesDetail", back_populates="driver")

class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, nullable=False)
    code = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    status = Column(String, default="active")
