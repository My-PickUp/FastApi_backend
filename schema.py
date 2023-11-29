from pydantic import BaseModel
from typing import List

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

class UserVerify(BaseModel):
    phone_number: str
    otp: str

class Token(BaseModel):
    access_token: str
    token_type: str