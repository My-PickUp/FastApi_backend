
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float, func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, index=True, unique=True, nullable=False)
    name = Column(String, nullable=False)
    address = Column(String)
    active = Column(Boolean, default=True)
    current_subscription_id = Column(Integer, ForeignKey("users_subscription.id"))

    subscriptions = relationship("UsersSubscription", back_populates="user", foreign_keys=[current_subscription_id])
    rides = relationship("RidesDetail", back_populates="user")

class UsersSubscription(Base):
    __tablename__ = "users_subscription"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subscription_plan = Column(String, nullable=False)
    subscription_start_date = Column(DateTime, default=datetime.utcnow)
    subscription_end_date = Column(DateTime)
    payment_status = Column(String)
    subscription_status = Column(String, default="active")

    user = relationship("User", back_populates="subscriptions", foreign_keys=[user_id])
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
    fare = Column(Float)
    ride_status = Column(String)
    additional_ride_details = Column(String)

    user = relationship("User", back_populates="rides")
    subscription = relationship("UsersSubscription", back_populates="rides")
    driver = relationship("Driver", back_populates="rides")

class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    # Add other driver-related fields as needed



class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, nullable=False)
    code = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    status = Column(String, default="active")  # Add this line for the status field
