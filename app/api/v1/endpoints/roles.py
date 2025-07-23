# app/api/v1/endpoints/roles.py

from fastapi import APIRouter, Depends, HTTPException, status, Path
from typing import List, Annotated

# Import Schemas
from app.schemas.role import RoleCreate, RoleInResponse, RoleUpdate

# Import Services
from app.services.role_service import RoleService

# Import Dependencies
from app.dependencies import (
    get_role_service,
    requires_permission,
)

# THAY ĐỔI: Định nghĩa một hàm để trả về APIRouter
def get_roles_router() -> APIRouter:
    router = APIRouter(prefix="/roles", tags=["Role Management & Assignment"])

    @router.post("/", response_model=RoleInResponse, status_code=status.HTTP_201_CREATED,
                 dependencies=[Depends(requires_permission("role:create"))]) # Yêu cầu quyền role:create
    async def create_new_role(
        role_in: RoleCreate,
        role_service: RoleService = Depends(get_role_service)
    ):
        """
        Tạo vai trò mới (chỉ dành cho người có quyền 'role:create').
        """
        return await role_service.create_new_role(role_in)

    @router.get("/", response_model=List[RoleInResponse],
                dependencies=[Depends(requires_permission("role:read_all"))]) # Yêu cầu quyền role:read_all
    async def read_all_roles(
        role_service: RoleService = Depends(get_role_service)
    ):
        """
        Lấy danh sách tất cả vai trò (chỉ dành cho người có quyền 'role:read_all').
        """
        return await role_service.get_all_roles()

    @router.get("/{role_id}", response_model=RoleInResponse,
                dependencies=[Depends(requires_permission("role:read_all"))]) # Yêu cầu quyền role:read_all
    async def read_role_by_id(
        role_id: Annotated[str, Path(description="ID của vai trò")],
        role_service: RoleService = Depends(get_role_service)
    ):
        """
        Lấy thông tin vai trò theo ID (chỉ dành cho người có quyền 'role:read_all').
        """
        return await role_service.get_role(role_id)

    @router.put("/{role_id}", response_model=RoleInResponse,
                dependencies=[Depends(requires_permission("role:update"))]) # Yêu cầu quyền role:update
    async def update_existing_role(
        role_id: Annotated[str, Path(description="ID của vai trò cần cập nhật")],
        role_update: RoleUpdate,
        role_service: RoleService = Depends(get_role_service)
    ):
        """
        Cập nhật thông tin vai trò theo ID (chỉ dành cho người có quyền 'role:update').
        """
        return await role_service.update_role(role_id, role_update)

    @router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT,
                dependencies=[Depends(requires_permission("role:delete"))]) # Yêu cầu quyền role:delete
    async def delete_existing_role(
        role_id: Annotated[str, Path(description="ID của vai trò cần xóa")],
        role_service: RoleService = Depends(get_role_service)
    ):
        """
        Xóa vai trò theo ID (chỉ dành cho người có quyền 'role:delete').
        """
        await role_service.delete_role(role_id)
        return {"message": "Vai trò đã được xóa thành công."}
    
    return router # TRẢ VỀ ĐỐI TƯỢNG ROUTER
