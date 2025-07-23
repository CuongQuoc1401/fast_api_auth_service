# app/services/user_service.py

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorClient
from jose import jwt, JWTError # Thêm JWTError để bắt lỗi giải mã token

# Imports từ tầng core
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    TokenData,
    decode_token,
)
from app.core.config import settings

# Imports từ tầng repository
from app.repository.user import (
    get_user_by_username,
    get_user_by_email,
    get_user_by_id,
    create_user_db,
    update_user_db,
    clear_user_lockout_and_attempts,
    increment_failed_login_attempts,
    set_user_lockout,
    update_last_login_at,
    get_all_users_db
)
from app.repository.role import get_roles_by_ids
from app.repository.permission import get_permissions_by_ids

# Imports từ tầng models (Database Models)
from app.models.user import UserDBModel
from app.models.role import RoleDBModel
from app.models.permission import PermissionDBModel

# Imports từ tầng schemas (API Input/Output)
from app.schemas.user import (
    UserCreate,
    UserInResponse,
    UserUpdate,
    ForgotPasswordRequest, # Mới
    ResetPasswordRequest,  # Mới
    ChangePasswordRequest, # Mới
    ChangeEmailRequest,    # Mới
    MessageResponse        # Mới
)
from app.schemas.token import Token


class UserService:
    def __init__(self, db: AsyncIOMotorClient):
        self.db = db

    async def _get_populated_user_response(self, user_db_model: UserDBModel) -> UserInResponse:
        """
        Helper function để chuyển đổi UserDBModel thành UserInResponse và populate
        các trường `roles` và `permissions` dựa trên IDs.
        """
        roles_db_models: List[RoleDBModel] = []
        permissions_db_models: List[PermissionDBModel] = []

        if user_db_model.role_ids:
            roles_db_models = await get_roles_by_ids(user_db_model.role_ids, self.db)
            
            all_permission_ids = []
            for role in roles_db_models:
                all_permission_ids.extend(role.permission_ids)
            
            if all_permission_ids:
                unique_permission_ids = list(set(all_permission_ids))
                permissions_db_models = await get_permissions_by_ids(unique_permission_ids, self.db)

        roles_in_response = [role.name for role in roles_db_models]
        permissions_in_response = [permission.name for permission in permissions_db_models]

        user_response = UserInResponse.model_validate(user_db_model)
        user_response.roles = roles_in_response
        user_response.permissions = permissions_in_response
        
        return user_response

    async def register_new_user(self, user_in: UserCreate) -> UserInResponse:
        """Logic nghiệp vụ để đăng ký người dùng mới."""
        existing_user_by_username = await get_user_by_username(user_in.username, self.db)
        if existing_user_by_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tên người dùng đã tồn tại."
            )
        existing_user_by_email = await get_user_by_email(user_in.email, self.db)
        if existing_user_by_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email đã được đăng ký."
            )

        hashed_password = get_password_hash(user_in.password)

        user_data_for_db = user_in.model_dump()
        user_data_for_db["hashed_password"] = hashed_password
        user_data_for_db.pop("password", None)

        if not user_data_for_db.get("role_ids"):
            default_role = await self.db["roles"].find_one({"name": settings.DEFAULT_USER_ROLE_NAME})
            if default_role:
                user_data_for_db["role_ids"] = [str(default_role["_id"])]
            else:
                print(f"Cảnh báo: Vai trò mặc định '{settings.DEFAULT_USER_ROLE_NAME}' không tìm thấy trong DB.")

        new_user_db_model = await create_user_db(user_data_for_db, self.db)
        return await self._get_populated_user_response(new_user_db_model)

    async def authenticate_user(self, username: str, password: str) -> UserInResponse:
        """Logic nghiệp vụ để xác thực người dùng."""
        user = await get_user_by_username(username, self.db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tên người dùng hoặc mật khẩu không đúng.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if user.lockout_until and user.lockout_until > datetime.now(timezone.utc):
            lockout_remaining = user.lockout_until - datetime.now(timezone.utc)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tài khoản bị khóa đến {user.lockout_until.isoformat()} UTC ({int(lockout_remaining.total_seconds())} giây còn lại). Vui lòng thử lại sau.",
            )

        if not verify_password(password, user.hashed_password):
            await increment_failed_login_attempts(str(user.id), self.db)
            
            updated_user = await get_user_by_username(username, self.db) 
            
            if updated_user and updated_user.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
                lockout_duration = timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)
                lockout_until = datetime.now(timezone.utc) + lockout_duration
                await set_user_lockout(str(updated_user.id), lockout_until, self.db)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Tài khoản của bạn đã bị khóa trong {settings.LOCKOUT_DURATION_MINUTES} phút do quá nhiều lần đăng nhập sai.",
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tên người dùng hoặc mật khẩu không đúng.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        await clear_user_lockout_and_attempts(str(user.id), self.db)
        await update_last_login_at(str(user.id), self.db)
        
        return await self._get_populated_user_response(user)

    async def create_auth_tokens(self, user_db_model: UserDBModel) -> Token:
        """Logic nghiệp vụ để tạo Access Token và Refresh Token."""
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
        
        access_token_payload = {
            "sub": str(user_db_model.id), 
            "username": user_db_model.username, 
            "is_superuser": user_db_model.is_superuser
        }
        
        refresh_token_payload = {"sub": str(user_db_model.id)}
        
        access_token = create_access_token(
            data=access_token_payload, expires_delta=access_token_expires
        )
        refresh_token = create_refresh_token(
            data=refresh_token_payload, expires_delta=refresh_token_expires
        )
        return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")

    async def refresh_access_token(self, refresh_token: str) -> Token:
        """Logic nghiệp vụ để làm mới Access Token bằng Refresh Token."""
        try:
            payload = decode_token(refresh_token, settings.SECRET_KEY)
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token không hợp lệ (thiếu user ID)."
                )
            token_data = TokenData(user_id=user_id)

        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token không hợp lệ hoặc đã hết hạn.",
            )

        user = await get_user_by_id(token_data.user_id, self.db)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Người dùng không tồn tại hoặc không hoạt động.",
            )
        
        return await self.create_auth_tokens(user)

    async def get_user_profile(self, user_id: str) -> UserInResponse:
        """Lấy thông tin profile người dùng."""
        user_db_model = await get_user_by_id(user_id, self.db)
        if not user_db_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tìm thấy.")
        
        return await self._get_populated_user_response(user_db_model)

    async def update_user_profile(self, user_id: str, user_update: UserUpdate) -> UserInResponse:
        """Cập nhật thông tin profile người dùng."""
        user_db_model = await get_user_by_id(user_id, self.db)
        if not user_db_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tìm thấy.")
        
        update_data = user_update.model_dump(exclude_unset=True)

        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

        if "role_ids" in update_data and update_data["role_ids"] is not None:
            if update_data["role_ids"]:
                found_roles = await get_roles_by_ids(update_data["role_ids"], self.db)
                if len(found_roles) != len(set(update_data["role_ids"])):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Một hoặc nhiều ID vai trò không hợp lệ trong dữ liệu cập nhật."
                    )

        updated_user_db_model = await update_user_db(user_id, update_data, self.db)
        if not updated_user_db_model:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Không thể cập nhật người dùng.")
        
        return await self._get_populated_user_response(updated_user_db_model)

    async def get_all_users(self) -> List[UserInResponse]:
        """Lấy tất cả người dùng."""
        all_users_db = await get_all_users_db(self.db)
        
        users_in_response = []
        for user_db in all_users_db:
            users_in_response.append(await self._get_populated_user_response(user_db))
        return users_in_response

    async def delete_user(self, user_id: str) -> bool:
        """Xóa người dùng."""
        user_db_model = await get_user_by_id(user_id, self.db)
        if not user_db_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tìm thấy.")
        
        deleted = await delete_user_db(user_id, self.db)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Không thể xóa người dùng.")
        return deleted

    # --- Các hàm Service mới cho Self-Service APIs ---

    async def request_password_reset(self, request: ForgotPasswordRequest) -> MessageResponse:
        """
        Xử lý yêu cầu đặt lại mật khẩu: tạo token và gửi email.
        """
        user = await get_user_by_email(request.email, self.db)
        
        # Luôn trả về thông báo chung để tránh tiết lộ email tồn tại
        if not user:
            return MessageResponse(message="Nếu email tồn tại trong hệ thống, hướng dẫn đặt lại mật khẩu đã được gửi.")

        # Tạo token đặt lại mật khẩu (JWT)
        reset_token_payload = {
            "sub": str(user.id),
            "type": "password_reset",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.RESET_PASSWORD_TOKEN_EXPIRE_MINUTES)
        }
        reset_token = jwt.encode(reset_token_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        # TODO: Gửi email chứa reset_token đến user.email
        # Đây là nơi bạn tích hợp dịch vụ gửi email của mình.
        # Ví dụ: send_email(user.email, "Đặt lại mật khẩu", f"Sử dụng token này: {reset_token}")
        print(f"DEBUG: Gửi token đặt lại mật khẩu đến {user.email}: {reset_token}") # Chỉ để debug

        return MessageResponse(message="Nếu email tồn tại trong hệ thống, hướng dẫn đặt lại mật khẩu đã được gửi.")

    async def reset_password(self, request: ResetPasswordRequest) -> MessageResponse:
        """
        Đặt lại mật khẩu bằng token.
        """
        try:
            payload = jwt.decode(request.token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            token_type = payload.get("type")

            if not user_id or token_type != "password_reset":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token đặt lại mật khẩu không hợp lệ."
                )
            
            # Kiểm tra thời gian hết hạn của token đã được JWTError xử lý

        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token đặt lại mật khẩu không hợp lệ hoặc đã hết hạn."
            )

        user = await get_user_by_id(user_id, self.db)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tìm thấy.")

        hashed_new_password = get_password_hash(request.new_password)
        
        update_data = {
            "hashed_password": hashed_new_password,
            "password_changed_at": datetime.now(timezone.utc),
            "failed_login_attempts": 0, # Reset attempts
            "lockout_until": None # Clear lockout
        }
        updated_user = await update_user_db(str(user.id), update_data, self.db)
        
        if not updated_user:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Không thể đặt lại mật khẩu.")
        
        return MessageResponse(message="Mật khẩu đã được đặt lại thành công.")

    async def change_password(self, current_user_id: str, request: ChangePasswordRequest) -> MessageResponse:
        """
        Thay đổi mật khẩu cho người dùng đã đăng nhập.
        """
        user = await get_user_by_id(current_user_id, self.db)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tìm thấy.")

        if not verify_password(request.old_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mật khẩu cũ không đúng.")

        hashed_new_password = get_password_hash(request.new_password)
        
        update_data = {
            "hashed_password": hashed_new_password,
            "password_changed_at": datetime.now(timezone.utc)
        }
        updated_user = await update_user_db(str(user.id), update_data, self.db)

        if not updated_user:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Không thể thay đổi mật khẩu.")
        
        return MessageResponse(message="Mật khẩu đã được thay đổi thành công.")

    async def deactivate_account(self, current_user_id: str) -> MessageResponse:
        """
        Vô hiệu hóa tài khoản của người dùng đã đăng nhập.
        """
        user = await get_user_by_id(current_user_id, self.db)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tìm thấy.")
        
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tài khoản đã bị vô hiệu hóa.")

        update_data = {"is_active": False}
        updated_user = await update_user_db(str(user.id), update_data, self.db)

        if not updated_user:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Không thể vô hiệu hóa tài khoản.")
        
        return MessageResponse(message="Tài khoản đã được vô hiệu hóa thành công.")

    async def reactivate_account(self, username: str, password: str) -> MessageResponse:
        """
        Kích hoạt lại tài khoản bằng cách đăng nhập.
        """
        user = await get_user_by_username(username, self.db)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tên người dùng hoặc mật khẩu không đúng.",
            )
        
        if user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tài khoản đã hoạt động.")

        if not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Tên người dùng hoặc mật khẩu không đúng.",
            )
        
        update_data = {"is_active": True}
        updated_user = await update_user_db(str(user.id), update_data, self.db)

        if not updated_user:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Không thể kích hoạt lại tài khoản.")
        
        return MessageResponse(message="Tài khoản đã được kích hoạt lại thành công.")

    async def request_email_verification(self, current_user_id: str) -> MessageResponse:
        """
        Gửi yêu cầu xác minh email cho người dùng đã đăng nhập.
        """
        user = await get_user_by_id(current_user_id, self.db)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tìm thấy.")

        if user.email_verified_at:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email đã được xác minh.")

        # Tạo token xác minh email (JWT)
        verification_token_payload = {
            "sub": str(user.id),
            "type": "email_verification",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES)
        }
        verification_token = jwt.encode(verification_token_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        # TODO: Gửi email chứa verification_token đến user.email
        print(f"DEBUG: Gửi token xác minh email đến {user.email}: {verification_token}") # Chỉ để debug

        return MessageResponse(message="Email xác minh đã được gửi. Vui lòng kiểm tra hộp thư của bạn.")

    async def verify_email(self, token: str) -> MessageResponse:
        """
        Xác minh email bằng token.
        """
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            token_type = payload.get("type")

            if not user_id or token_type != "email_verification":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token xác minh email không hợp lệ."
                )
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token xác minh email không hợp lệ hoặc đã hết hạn."
            )

        user = await get_user_by_id(user_id, self.db)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tìm thấy.")

        if user.email_verified_at:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email đã được xác minh trước đó.")
        
        update_data = {"email_verified_at": datetime.now(timezone.utc)}
        updated_user = await update_user_db(str(user.id), update_data, self.db)

        if not updated_user:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Không thể xác minh email.")
        
        return MessageResponse(message="Email đã được xác minh thành công.")

    async def change_email(self, current_user_id: str, request: ChangeEmailRequest) -> MessageResponse:
        """
        Thay đổi địa chỉ email của người dùng đã đăng nhập.
        """
        user = await get_user_by_id(current_user_id, self.db)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tìm thấy.")

        # Xác minh mật khẩu hiện tại của người dùng
        if not verify_password(request.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mật khẩu không đúng.")
        
        # Kiểm tra email mới có trùng với email hiện tại không
        if request.new_email == user.email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email mới không được trùng với email hiện tại.")

        # Kiểm tra email mới đã tồn tại với người dùng khác chưa
        existing_user_with_new_email = await get_user_by_email(request.new_email, self.db)
        if existing_user_with_new_email and str(existing_user_with_new_email.id) != current_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email mới đã được sử dụng bởi tài khoản khác.")

        update_data = {
            "email": request.new_email,
            "email_verified_at": None # Đặt lại trạng thái xác minh email
        }
        updated_user = await update_user_db(str(user.id), update_data, self.db)

        if not updated_user:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Không thể thay đổi email.")
        
        # TODO: Gửi email xác minh đến địa chỉ email mới
        print(f"DEBUG: Gửi email xác minh đến địa chỉ email mới: {request.new_email}") # Chỉ để debug

        return MessageResponse(message="Email của bạn đã được cập nhật. Vui lòng kiểm tra email mới để xác minh.")
