# app/schemas/token.py

from typing import Optional
from pydantic import BaseModel

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[str] = None # ID người dùng
    username: Optional[str] = None # Tên người dùng (có thể đưa vào nếu muốn, nhưng sub là đủ)
    is_superuser: Optional[bool] = False # Cờ siêu quản trị viên (có thể đưa vào token để kiểm tra nhanh)