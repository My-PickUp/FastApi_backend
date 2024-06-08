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
    address = Column(String, nullable=True)
    active = Column(Boolean, default=True)
    gender = Column(String, nullable=True)
    profile_photo = Column(String, nullable=True)  # Set nullable to True
    emergency_contact_name = Column(String, nullable=True)  # Set nullable to True
    emergency_contact_phone = Column(String, nullable=True)  # Set nullable to True
    created_at = Column(DateTime, default=func.now())  # Add this field
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())  # Add this field

    subscriptions = relationship("UsersSubscription", back_populates="user")
    addresses = relationship("Address", back_populates="user")
    rides = relationship("RidesDetail", back_populates="user")
    price = relationship("Price_per_trip", back_populates="user")


class UsersSubscription(Base):
    __tablename__ = "users_subscription"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    subscription_plan = Column(String, nullable=False)
    payment_status = Column(String,default=False,nullable=True)
    subscription_status = Column(String, default="active")
    created_at = Column(DateTime, default=func.now())
    subscription_cost  = Column(Float, nullable=True)

    user = relationship("User", back_populates="subscriptions", remote_side="User.id")  # Set remote_side to User.id
    rides = relationship("RidesDetail", back_populates="subscription")


class RidesDetail(Base):
    __tablename__ = "users_rides_detail"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id")) 
    driver_phone = Column(String)
    subscription_id = Column(Integer, ForeignKey("users_subscription.id"))
    pickup_address = Column(String)
    pickup_address_type = Column(String)
    pickup_latitude = Column(Float)
    pickup_longitude = Column(Float)
    drop_address_type = Column(String)
    drop_address = Column(String)
    drop_latitude = Column(Float)
    drop_longitude = Column(Float)
    ride_date_time = Column(DateTime, default=datetime.utcnow)
    ride_status = Column(String, default="Upcoming")
    additional_ride_details = Column(String)
    # assigned_to_cab_fleet = Column(String)

    user = relationship("User", back_populates="rides")
    subscription = relationship("UsersSubscription", back_populates="rides")

class Address(Base):
    __tablename__ = "users_addresses"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, ForeignKey("users.phone_number"), index=True)
    address_type = Column(String, nullable=False)
    address = Column(String, nullable=False)
    latitude = Column(Float, nullable=True)  
    longitude = Column(Float, nullable=True) 

    user = relationship("User", back_populates="addresses")  # Added this line


class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, nullable=False)
    code = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    status = Column(String, default="active")

class Price_per_trip(Base):
    __tablename__ = "users_pricing"
    
    id = Column(Integer, primary_key=True, index=True)
    price_per_trip = Column(Float, nullable=False,default=0.0)
    phone_number = Column(String, ForeignKey("users.phone_number"), index=True)

    user = relationship("User", back_populates="price")
