# app/models/permission.py

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId

class PermissionDBModel(BaseModel):
    id: str = Field(alias="_id") # Map _id từ MongoDB thành id
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, from_attributes=True)