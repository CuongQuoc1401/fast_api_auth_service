# app/api/v1/endpoints/users.py

from fastapi import APIRouter, Depends, HTTPException, status, Path
from typing import List, Annotated

# Import Schemas
from app.schemas.user import UserCreate, UserUpdate, UserInResponse

# Import Services
from app.services.user_service import UserService

# Import Dependencies
from app.dependencies import (
    get_user_service,
    get_current_active_superuser, # Chỉ superuser mới có quyền quản lý users
    requires_permission, # Dùng cho kiểm tra quyền hạn chi tiết
)

# THAY ĐỔI: Định nghĩa một hàm để trả về APIRouter
def get_users_router() -> APIRouter:
    router = APIRouter(prefix="/users", tags=["User Management"])

    @router.post("/", response_model=UserInResponse, status_code=status.HTTP_201_CREATED,
                 dependencies=[Depends(requires_permission("user:create"))]) # Yêu cầu quyền user:create
    async def create_new_user(
        user_in: UserCreate,
        user_service: UserService = Depends(get_user_service)
    ):
        """
        Tạo người dùng mới (chỉ dành cho người có quyền 'user:create').
        """
        return await user_service.register_new_user(user_in) # Tái sử dụng logic đăng ký

    @router.get("/", response_model=List[UserInResponse],
                dependencies=[Depends(requires_permission("user:read_all"))]) # Yêu cầu quyền user:read_all
    async def read_all_users(
        user_service: UserService = Depends(get_user_service)
    ):
        """
        Lấy danh sách tất cả người dùng (chỉ dành cho người có quyền 'user:read_all').
        """
        return await user_service.get_all_users()

    @router.get("/{user_id}", response_model=UserInResponse,
                dependencies=[Depends(requires_permission("user:read_all"))]) # Yêu cầu quyền user:read_all
    async def read_user_by_id(
        user_id: Annotated[str, Path(description="ID của người dùng")],
        user_service: UserService = Depends(get_user_service)
    ):
        """
        Lấy thông tin người dùng theo ID (chỉ dành cho người có quyền 'user:read_all').
        """
        return await user_service.get_user_profile(user_id)

    @router.put("/{user_id}", response_model=UserInResponse,
                dependencies=[Depends(requires_permission("user:update"))]) # Yêu cầu quyền user:update
    async def update_existing_user(
        user_id: Annotated[str, Path(description="ID của người dùng cần cập nhật")],
        user_update: UserUpdate,
        user_service: UserService = Depends(get_user_service)
    ):
        """
        Cập nhật thông tin người dùng theo ID (chỉ dành cho người có quyền 'user:update').
        """
        return await user_service.update_user_profile(user_id, user_update)

    @router.put("/{user_id}/roles", response_model=UserInResponse,
                dependencies=[Depends(requires_permission("user:assign_roles"))]) # Yêu cầu quyền user:assign_roles
    async def update_user_role_ids(
        user_id: Annotated[str, Path(description="ID của người dùng cần cập nhật vai trò")],
        role_ids: List[str], # Nhận danh sách role IDs mới
        user_service: UserService = Depends(get_user_service)
    ):
        """
        Cập nhật danh sách vai trò cho người dùng theo ID (chỉ dành cho người có quyền 'user:assign_roles').
        """
        # Tạo một UserUpdate object chỉ với role_ids để truyền vào service
        user_update_data = UserUpdate(role_ids=role_ids)
        return await user_service.update_user_profile(user_id, user_update_data)

    @router.put("/{user_id}/status", response_model=UserInResponse,
                dependencies=[Depends(requires_permission("user:update_status"))]) # Yêu cầu quyền user:update_status
    async def update_user_status(
        user_id: Annotated[str, Path(description="ID của người dùng cần cập nhật trạng thái")],
        is_active: bool, # Trạng thái hoạt động mới
        user_service: UserService = Depends(get_user_service)
    ):
        """
        Cập nhật trạng thái hoạt động (kích hoạt/vô hiệu hóa) của người dùng (chỉ dành cho người có quyền 'user:update_status').
        """
        user_update_data = UserUpdate(is_active=is_active)
        return await user_service.update_user_profile(user_id, user_update_data)


    @router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT,
                dependencies=[Depends(requires_permission("user:delete"))]) # Yêu cầu quyền user:delete
    async def delete_user_account(
        user_id: Annotated[str, Path(description="ID của người dùng cần xóa")],
        user_service: UserService = Depends(get_user_service)
    ):
        """
        Xóa người dùng theo ID (chỉ dành cho người có quyền 'user:delete').
        """
        await user_service.delete_user(user_id)
        return {"message": "Người dùng đã được xóa thành công."}
    
    return router # TRẢ VỀ ĐỐI TƯỢNG ROUTER
