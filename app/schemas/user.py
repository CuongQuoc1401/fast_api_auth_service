# app/schemas/user.py

from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8)
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    role_ids: Optional[List[str]] = Field(default_factory=list) # IDs của các vai trò để gán ban đầu

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    role_ids: Optional[List[str]] = None

class UserInResponse(BaseModel):
    id: str
    username: str
    email: EmailStr
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
    roles: List[str] = Field(default_factory=list)      # Tên các vai trò
    permissions: List[str] = Field(default_factory=list) # Tên các quyền hạn

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)
    
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="Token đặt lại mật khẩu nhận được qua email.")
    new_password: str = Field(..., min_length=8, description="Mật khẩu mới.")

class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="Mật khẩu hiện tại của người dùng.")
    new_password: str = Field(..., min_length=8, description="Mật khẩu mới.")

class ChangeEmailRequest(BaseModel):
    new_email: EmailStr = Field(..., description="Địa chỉ email mới.")
    password: str = Field(..., description="Mật khẩu hiện tại để xác nhận thay đổi email.")

# Có thể thêm schema cho response chung nếu muốn (ví dụ: {"message": "..."})
class MessageResponse(BaseModel):
    message: str