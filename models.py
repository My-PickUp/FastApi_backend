from sqlalchemy import Column, Float, Integer, String, Boolean, ForeignKey, DateTime, create_engine
from sqlalchemy.orm import relationship, declarative_base, Session
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.sql import func
from sqlalchemy.dialects.sqlite import DATETIME

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, index=True, unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    address = Column(String)
    email = Column(String)
    active = Column(Boolean, default=True)
    current_subscription_id = Column(Integer, ForeignKey("users_subscription.id"), nullable=True)

    subscriptions = relationship("UsersSubscription", back_populates="user")
    rides = relationship("RidesDetail", back_populates="user")

class UsersSubscription(Base):
    __tablename__ = "users_subscription"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subscription_plan = Column(String, nullable=False)
    subscription_start_date = Column(DATETIME, server_default=func.now())
    subscription_end_date = Column(DATETIME)
    payment_status = Column(String)
    subscription_status = Column(String, default="active")

    user = relationship("User", back_populates="subscriptions")
    rides = relationship("RidesDetail", back_populates="subscription")

class RidesDetail(Base):
    __tablename__ = "rides_detail"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    driver_id = Column(Integer, ForeignKey("drivers.id"))
    subscription_id = Column(Integer, ForeignKey("users_subscription.id"))
    start_location = Column(String)
    start_latitude = Column(Float)  # New column for pickup latitude
    start_longitude = Column(Float)  # New column for pickup longitude
    end_location = Column(String)
    end_latitude = Column(Float)  # New column for drop latitude
    end_longitude = Column(Float)  # New column for drop longitude
    ride_date_time = Column(DATETIME, server_default=func.now())
    fare = Column(Float)
    ride_status = Column(String)
    additional_ride_details = Column(String)

    user = relationship("User", back_populates="rides")
    subscription = relationship("UsersSubscription", back_populates="rides")
    driver = relationship("Driver", back_populates="rides")


class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, nullable=False)
    code = Column(String, nullable=False)
    created_at = Column(DATETIME, server_default=func.now())
    status = Column(String, default="active")  # Add this line for the status field
