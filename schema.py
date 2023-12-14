from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# temporary
class UserCreate(BaseModel):
    phone_number: str
    name: str
    email: str = None
    pickup_address: Optional[str] = None
    dropoff_address: Optional[str] = None
    active: bool = True
    gender: str = None
    profile_photo: str = None
    emergency_contact_name: str = None
    emergency_contact_phone: str = None


class UserSchema(BaseModel):
    phone_number: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    pickup_address: Optional[str] = None
    dropoff_address: Optional[str] = None
    active: Optional[bool] = True
    gender: Optional[str] = None
    profile_photo: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    created_at: Optional[datetime] = None 
    updated_at: Optional[datetime] = None 

class UserUpdateSchema(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    pickup_address: Optional[str] = None
    dropoff_address: Optional[str] = None
    gender: Optional[str] = None
    profile_photo: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


class RideDetailSchema(BaseModel):
    driver_id: str
    pickup_address: str
    pickup_address_type: str
    drop_address: str
    drop_address_type: str
    datetime: str
    pickup_lat: float
    pickup_long: float
    drop_lat: float
    drop_long: float

class CreateUserSubscriptionAndRidesSchema(BaseModel):
    user_id: int
    subscription_plan: str
    ride_details: List[RideDetailSchema]