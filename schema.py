from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserSchema(BaseModel):
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