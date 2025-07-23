# app/schemas/permission.py

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

class PermissionCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None

class PermissionInResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)