# app/schemas/role.py

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.schemas.permission import PermissionInResponse # Import để nhúng permission details vào response

class RoleCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    permission_ids: List[str] = Field(default_factory=list) # Các ID của quyền hạn

class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = None
    permission_ids: Optional[List[str]] = None

class RoleInResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    permissions: List[PermissionInResponse] = Field(default_factory=list) # Danh sách các đối tượng PermissionInResponse
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)