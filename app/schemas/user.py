# app/schemas/user.py

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from app.base.base import BaseDomainModel # Import BaseDBModel

# Base Models (dùng cho logic nghiệp vụ nội bộ hoặc cho các Schema khác kế thừa)
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    full_name: Optional[str] = None # Bổ sung trường này
    address: Optional[str] = None # Bổ sung trường này
    phone_number: Optional[str] = None # Bổ sung trường này

# Schema cho việc tạo người dùng mới (input từ API)
class UserCreate(UserBase):
    password: str = Field(..., min_length=8) # Mật khẩu clear-text
    role_ids: Optional[List[str]] = None # Có thể gán vai trò khi tạo (cho admin)

# Schema cho việc cập nhật người dùng (input từ API)
class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8) # Mật khẩu clear-text (sẽ được hash trong service)
    full_name: Optional[str] = None # Bổ sung trường này
    address: Optional[str] = None # Bổ sung trường này
    phone_number: Optional[str] = None # Bổ sung trường này
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    role_ids: Optional[List[str]] = None

# Database Model (đại diện cho cấu trúc trong MongoDB)
class UserDBModel(BaseDomainModel): # Kế thừa từ BaseDBModel để có id, created_at, updated_at
    username: str
    email: EmailStr
    hashed_password: str # Mật khẩu đã hash
    is_active: bool = True
    is_superuser: bool = False
    full_name: Optional[str] = None # Bổ sung trường này
    address: Optional[str] = None # Bổ sung trường này
    phone_number: Optional[str] = None # Bổ sung trường này
    role_ids: List[str] = Field(default_factory=list) # Danh sách các ID vai trò
    
    # Các trường liên quan đến bảo mật và trạng thái
    failed_login_attempts: int = 0
    lockout_until: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    email_verified_at: Optional[datetime] = None # Thêm trường này để theo dõi xác minh email
    password_changed_at: Optional[datetime] = None # Thêm trường này để theo dõi thời gian đổi mật khẩu

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "username": "johndoe",
                "email": "john.doe@example.com",
                "hashed_password": "hashedpassword123",
                "is_active": True,
                "is_superuser": False,
                "full_name": "John Doe",
                "address": "123 Main St, Anytown, USA", # Ví dụ
                "phone_number": "+1234567890", # Ví dụ
                "role_ids": ["60d5ec49f7e3d1a4e8b8c7c1"],
                "failed_login_attempts": 0,
                "lockout_until": None,
                "last_login_at": "2023-10-27T10:00:00Z",
                "email_verified_at": "2023-10-27T09:00:00Z",
                "password_changed_at": "2023-10-27T08:00:00Z"
            }
        }

# Schema cho phản hồi API (output cho client)
class UserInResponse(BaseModel):
    id: str # ID của người dùng (từ _id của MongoDB)
    username: str
    email: EmailStr
    full_name: Optional[str] = None # Bổ sung trường này
    address: Optional[str] = None # Bổ sung trường này
    phone_number: Optional[str] = None # Bổ sung trường này
    is_active: bool
    is_superuser: bool
    roles: List[str] = Field(default_factory=list) # Tên các vai trò
    permissions: List[str] = Field(default_factory=list) # Tên các quyền hạn
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    email_verified_at: Optional[datetime] = None # Thêm trường này
    password_changed_at: Optional[datetime] = None # Thêm trường này

    class Config:
        from_attributes = True # Cho phép Pydantic đọc từ các thuộc tính của đối tượng (ví dụ: từ UserDBModel)
        json_schema_extra = {
            "example": {
                "id": "60d5ec49f7e3d1a4e8b8c7c1",
                "username": "johndoe",
                "email": "john.doe@example.com",
                "full_name": "John Doe",
                "address": "123 Main St, Anytown, USA", # Ví dụ
                "phone_number": "+1234567890", # Ví dụ
                "is_active": True,
                "is_superuser": False,
                "roles": ["member"],
                "permissions": ["user:read_own"],
                "created_at": "2023-10-27T09:00:00Z",
                "updated_at": "2023-10-27T10:00:00Z",
                "last_login_at": "2023-10-27T10:00:00Z",
                "email_verified_at": "2023-10-27T09:00:00Z",
                "password_changed_at": "2023-10-27T08:00:00Z"
            }
        }

# --- Các Schemas hiện có cho Self-Service APIs ---

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

