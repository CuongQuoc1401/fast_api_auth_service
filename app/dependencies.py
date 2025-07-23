# app/dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from motor.motor_asyncio import AsyncIOMotorClient
from jose import JWTError # Thêm import này

from app.core.database import get_database
from app.core.security import decode_token # Hàm để giải mã JWT
from app.core.config import settings # Để lấy SECRET_KEY
from app.schemas.token import TokenData # Để xử lý dữ liệu từ token
from app.schemas.user import UserInResponse # Để trả về thông tin user đã xác thực

from app.services.user_service import UserService
from app.services.role_service import RoleService
from app.services.permission_service import PermissionService

# Khởi tạo OAuth2PasswordBearer để tự động trích xuất token từ Header Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login") # tokenUrl là endpoint để lấy token

# Dependencies cho Service Layer
def get_user_service(db: AsyncIOMotorClient = Depends(get_database)) -> UserService:
    return UserService(db)

def get_role_service(db: AsyncIOMotorClient = Depends(get_database)) -> RoleService:
    return RoleService(db)

def get_permission_service(db: AsyncIOMotorClient = Depends(get_database)) -> PermissionService:
    return PermissionService(db)


# Dependencies cho Xác thực và Ủy quyền

async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> str:
    """
    Dependency để lấy ID người dùng từ Access Token.
    Ném HTTPException nếu token không hợp lệ hoặc hết hạn.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không thể xác thực thông tin đăng nhập",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token, settings.SECRET_KEY)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        # Bạn có thể thêm kiểm tra is_active, is_superuser ở đây nếu muốn kiểm tra nhanh từ token payload
        # hoặc để Service layer làm việc đó sau khi lấy user từ DB.
        return user_id
    except JWTError: # Bao gồm lỗi giải mã hoặc hết hạn
        raise credentials_exception

async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service)
) -> UserInResponse:
    """
    Dependency để lấy thông tin chi tiết của người dùng hiện tại từ DB.
    Kiểm tra trạng thái active của người dùng.
    """
    user = await user_service.get_user_profile(user_id) # user_service sẽ populate roles/permissions
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Người dùng không hoạt động hoặc không tìm thấy.")
    return user

async def get_current_active_user(current_user: UserInResponse = Depends(get_current_user)) -> UserInResponse:
    """
    Dependency để đảm bảo người dùng hiện tại đang hoạt động.
    (Đã được kiểm tra trong get_current_user, nhưng có thể dùng để rõ ràng hơn trong API).
    """
    return current_user

async def get_current_active_superuser(current_user: UserInResponse = Depends(get_current_user)) -> UserInResponse:
    """
    Dependency để đảm bảo người dùng hiện tại là Superuser.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có đủ quyền để thực hiện hành động này."
        )
    return current_user

# Dependency để kiểm tra quyền hạn cụ thể
# Ví dụ: requires_permission("admin:create_users")
def requires_permission(permission_name: str):
    async def permission_checker(current_user: UserInResponse = Depends(get_current_user)):
        # Kiểm tra xem người dùng có quyền này không
        # Lưu ý: current_user.permissions đã được populate bởi UserService
        if permission_name not in current_user.permissions and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Bạn không có quyền '{permission_name}'."
            )
        return current_user
    return permission_checker