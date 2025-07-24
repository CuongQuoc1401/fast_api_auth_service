# app/models/user.py

from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId # MongoDB specific

class UserDBModel(BaseModel):
    id: str = Field(alias="_id") # Map _id từ MongoDB thành id
    username: str
    email: EmailStr
    hashed_password: str # Có trong DB nhưng không có trong Schema Response
    full_name: Optional[str] = None # Bổ sung trường này
    address: Optional[str] = None # Bổ sung trường này
    phone_number: Optional[str] = None # Bổ sung trường này
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    failed_login_attempts: int = 0
    lockout_until: Optional[datetime] = None
    role_ids: List[str] = Field(default_factory=list) # List of string ObjectIds

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, from_attributes=True)