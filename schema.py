from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class UserId(BaseModel):
    UserId : str

# temporary
class UserCreate(BaseModel):
    phone_number: str
    name: str
    email: str = None
    address: str = None
    active: bool = True
    gender: str = None
    profile_photo: str = None
    emergency_contact_name: str = None
    emergency_contact_phone: str = None


class UserSchema(BaseModel):
    id: int
    phone_number: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
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
    address: Optional[str] = None
    gender: Optional[str] = None
    profile_photo: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


class RideDetailSchema(BaseModel):
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

class AddressCreateSchema(BaseModel):
    address_type: str
    address: str
    latitude: float
    longitude: float


class AddressSchema(BaseModel):
    id: int
    phone_number: str
    address_type: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class GetRideDetailSchema(BaseModel):
    id: int
    user_id: Optional[int] = None
    driver_phone: Optional[int] = None
    subscription_id: Optional[int] = None
    pickup_address: Optional[str] = None
    pickup_address_type: Optional[str] = None
    pickup_latitude: Optional[float] = None
    pickup_longitude: Optional[float] = None
    drop_address_type: Optional[str] = None
    drop_address: Optional[str] = None
    drop_latitude: Optional[float] = None
    drop_longitude: Optional[float] = None
    ride_date_time: Optional[datetime] = None
    ride_status: Optional[str] = None
    additional_ride_details: Optional[str] = None
    assigned_to_cab_fleet: Optional[str] = None

class RescheduleRideSchema(BaseModel):
    ride_id: int
    new_datetime: datetime

class UpdateRideStatusSchema(BaseModel):
    newStatus: str

class PriceCreateSchema(BaseModel):
    phone_number: str
    price_per_trip: float

class GetPriceSchema(BaseModel):
    id: int
    phone_number: str
    price_per_trip: float

class UpdatePhoneNumberSchema(BaseModel):
    phone_number: str
    
class UpdateActivityStatus(BaseModel):
    is_active: bool
    
class UpdatePaymentStatusSchema(BaseModel):
    to_active : bool
    subs_id : int
