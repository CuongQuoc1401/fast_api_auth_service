# app/api/v1/endpoints/auth.py

from fastapi import APIRouter, Depends, HTTPException, status, Path
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated # Dùng cho typing hints

# Import Schemas
from app.schemas.user import (
    UserCreate,
    UserInResponse,
    ForgotPasswordRequest, # Mới
    ResetPasswordRequest,  # Mới
    ChangePasswordRequest, # Mới
    ChangeEmailRequest,    # Mới
    MessageResponse        # Mới
)
from app.schemas.token import Token

# Import Services
from app.services.user_service import UserService

# Import Dependencies
from app.dependencies import (
    get_user_service,
    get_current_user,
    get_current_active_user,
    get_current_user_id,
)

# THAY ĐỔI: Định nghĩa một hàm để trả về APIRouter
def get_auth_router() -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["Authentication & User Profile"])

    @router.post("/register", response_model=UserInResponse, status_code=status.HTTP_201_CREATED)
    async def register_user(
        user_in: UserCreate,
        user_service: UserService = Depends(get_user_service)
    ):
        """
        Đăng ký người dùng mới vào hệ thống.
        """
        return await user_service.register_new_user(user_in)

    @router.post("/login", response_model=Token)
    async def login_for_access_token(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
        user_service: UserService = Depends(get_user_service)
    ):
        """
        Đăng nhập người dùng và cấp Access Token cùng Refresh Token.
        """
        user_db_model = await user_service.authenticate_user(form_data.username, form_data.password)
        return await user_service.create_auth_tokens(user_db_model)

    @router.post("/refresh-token", response_model=Token)
    async def refresh_access_token(
        user_id: str = Depends(get_current_user_id),
        user_service: UserService = Depends(get_user_service)
    ):
        """
        Làm mới Access Token bằng Refresh Token.
        """
        user_db_model = await user_service.get_user_profile(user_id)
        return await user_service.create_auth_tokens(user_db_model)

    @router.get("/me", response_model=UserInResponse)
    async def read_users_me(
        current_user: Annotated[UserInResponse, Depends(get_current_active_user)]
    ):
        """
        Lấy thông tin hồ sơ của người dùng hiện tại.
        """
        return current_user
    
    # --- Các API mới cho Self-Service ---

    @router.post("/forgot-password", response_model=MessageResponse)
    async def forgot_password(
        request: ForgotPasswordRequest,
        user_service: UserService = Depends(get_user_service)
    ):
        """
        Yêu cầu đặt lại mật khẩu. Gửi email chứa liên kết/token đặt lại.
        """
        return await user_service.request_password_reset(request)

    @router.post("/reset-password", response_model=MessageResponse)
    async def reset_password(
        request: ResetPasswordRequest,
        user_service: UserService = Depends(get_user_service)
    ):
        """
        Đặt lại mật khẩu bằng token nhận được qua email.
        """
        return await user_service.reset_password(request)

    @router.put("/change-password", response_model=MessageResponse)
    async def change_password(
        request: ChangePasswordRequest,
        current_user: Annotated[UserInResponse, Depends(get_current_active_user)],
        user_service: UserService = Depends(get_user_service)
    ):
        """
        Thay đổi mật khẩu cho người dùng đã đăng nhập.
        """
        return await user_service.change_password(current_user.id, request)

    @router.put("/deactivate-account", response_model=MessageResponse)
    async def deactivate_account(
        current_user: Annotated[UserInResponse, Depends(get_current_active_user)],
        user_service: UserService = Depends(get_user_service)
    ):
        """
        Vô hiệu hóa tài khoản của người dùng đã đăng nhập.
        """
        return await user_service.deactivate_account(current_user.id)

    @router.post("/reactivate-account", response_model=MessageResponse)
    async def reactivate_account(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()], # Sử dụng form data như login
        user_service: UserService = Depends(get_user_service)
    ):
        """
        Kích hoạt lại tài khoản đã bị vô hiệu hóa bằng cách đăng nhập lại.
        """
        # Endpoint này có thể là một biến thể của login, hoặc gọi một hàm riêng
        # Tái sử dụng logic authenticate_user để xác thực và kích hoạt lại nếu cần
        try:
            # Thử xác thực người dùng. Nếu thành công và tài khoản không active, service sẽ kích hoạt.
            await user_service.reactivate_account(form_data.username, form_data.password)
            return MessageResponse(message="Tài khoản đã được kích hoạt lại thành công.")
        except HTTPException as e:
            # Nếu xác thực thất bại, hoặc tài khoản đã active, hoặc bị lockout
            raise e


    @router.post("/request-email-verification", response_model=MessageResponse)
    async def request_email_verification(
        current_user: Annotated[UserInResponse, Depends(get_current_active_user)],
        user_service: UserService = Depends(get_user_service)
    ):
        """
        Gửi yêu cầu xác minh email đến địa chỉ email của người dùng đã đăng nhập.
        """
        return await user_service.request_email_verification(current_user.id)

    @router.get("/verify-email/{token}", response_model=MessageResponse)
    async def verify_email(
        token: Annotated[str, Path(description="Token xác minh email")],
        user_service: UserService = Depends(get_user_service)
    ):
        """
        Xác minh email của người dùng bằng token.
        """
        return await user_service.verify_email(token)

    @router.put("/change-email", response_model=MessageResponse)
    async def change_email(
        request: ChangeEmailRequest,
        current_user: Annotated[UserInResponse, Depends(get_current_active_user)],
        user_service: UserService = Depends(get_user_service)
    ):
        """
        Thay đổi địa chỉ email của người dùng đã đăng nhập.
        """
        return await user_service.change_email(current_user.id, request)

    return router
