# app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    # Cấu hình để load biến môi trường từ .env file
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # FastAPI settings
    APP_NAME: str = "Auth & RBAC Microservice"
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1" # Prefix cho tất cả các endpoints API v1

    # Security settings
    SECRET_KEY: str = Field(..., description="Secret key for JWT encoding/decoding. MUST be set in .env") # Bắt buộc phải có
    ALGORITHM: str = "HS256" # Thuật toán mã hóa JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 # Thời gian sống của Access Token (phút)
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # Thời gian sống của Refresh Token: 7 ngày (phút)

    MAX_FAILED_LOGIN_ATTEMPTS: int = 5 # Số lần đăng nhập sai tối đa trước khi khóa tài khoản
    LOCKOUT_DURATION_MINUTES: int = 15 # Thời gian tài khoản bị khóa sau khi đạt giới hạn (phút)

    # Thêm cấu hình cho token đặt lại mật khẩu và xác minh email
    RESET_PASSWORD_TOKEN_EXPIRE_MINUTES: int = 15 # Thời gian sống của token đặt lại mật khẩu (phút)
    EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES: int = 60 # Thời gian sống của token xác minh email (phút)

    # Database settings for MongoDB
    MONGODB_URI: str = Field(..., description="MongoDB connection URI. MUST be set in .env") # Bắt buộc phải có
    MONGODB_DB_NAME: str = Field(..., description="MongoDB database name. MUST be set in .env") # Bắt buộc phải có
    
    MONGODB_MAX_POOL_SIZE: int = 100 # Giá trị mặc định cho pool size của MongoDB driver

    # Email settings (Nếu có tính năng gửi email xác thực/reset mật khẩu)
    SMTP_SERVER: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: Optional[str] = None

    # Các tùy chọn khác
    DEBUG_MODE: bool = False # Bật/tắt chế độ debug

    # Tên vai trò mặc định cho người dùng mới đăng ký
    DEFAULT_USER_ROLE_NAME: str = "member"

    # Cấu hình cho Superadmin (Dùng cho script initialize_db.py)
    SUPERADMIN_USERNAME: str = "superadmin"
    SUPERADMIN_EMAIL: str = "superadmin@yourcompany.com"
    SUPERADMIN_PASSWORD: str = Field(..., description="Password for the initial superadmin. MUST be set in .env or changed immediately.")

settings = Settings()
