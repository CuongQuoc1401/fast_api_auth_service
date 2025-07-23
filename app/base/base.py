# app/base/base.py

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime, timezone

# Base Model chung cho các thực thể có thời gian tạo/cập nhật và ID
class BaseDomainModel(BaseModel):
    id: Optional[str] = None # ID là tùy chọn, có thể được gán sau khi tạo
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# User Base Model
class UserBaseModel(BaseDomainModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    is_active: bool = True
    is_superuser: bool = False
    role_ids: List[str] = Field(default_factory=list) # IDs của các vai trò (string ObjectId)

# Permission Base Model
class PermissionBaseModel(BaseDomainModel):
    name: str = Field(..., min_length=3, max_length=100) # Tên quyền hạn (ví dụ: "create:user", "read:product")
    description: Optional[str] = None

# Role Base Model
class RoleBaseModel(BaseDomainModel):
    name: str = Field(..., min_length=3, max_length=100) # Tên vai trò (ví dụ: "admin", "viewer", "editor")
    description: Optional[str] = None
    permission_ids: List[str] = Field(default_factory=list) # Danh sách các ID của quyền hạn mà vai trò này có