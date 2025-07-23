# app/api/v1/endpoints/permissions.py

from fastapi import APIRouter, Depends, HTTPException, status, Path
from typing import List, Annotated

# Import Schemas
from app.schemas.permission import PermissionCreate, PermissionInResponse

# Import Services
from app.services.permission_service import PermissionService

# Import Dependencies
from app.dependencies import (
    get_permission_service,
    requires_permission,
)

# THAY ĐỔI: Định nghĩa một hàm để trả về APIRouter
def get_permissions_router() -> APIRouter:
    router = APIRouter(prefix="/permissions", tags=["Permission Management"])

    @router.post("/", response_model=PermissionInResponse, status_code=status.HTTP_201_CREATED,
                 dependencies=[Depends(requires_permission("permission:create"))]) # Yêu cầu quyền permission:create
    async def create_new_permission(
        permission_in: PermissionCreate,
        permission_service: PermissionService = Depends(get_permission_service)
    ):
        """
        Tạo quyền hạn mới (chỉ dành cho người có quyền 'permission:create').
        """
        return await permission_service.create_new_permission(permission_in)

    @router.get("/", response_model=List[PermissionInResponse],
                dependencies=[Depends(requires_permission("permission:read_all"))]) # Yêu cầu quyền permission:read_all
    async def read_all_permissions(
        permission_service: PermissionService = Depends(get_permission_service)
    ):
        """
        Lấy danh sách tất cả quyền hạn (chỉ dành cho người có quyền 'permission:read_all').
        """
        return await permission_service.get_all_permissions()

    @router.get("/{permission_id}", response_model=PermissionInResponse,
                dependencies=[Depends(requires_permission("permission:read_all"))]) # Yêu cầu quyền permission:read_all
    async def read_permission_by_id(
        permission_id: Annotated[str, Path(description="ID của quyền hạn")],
        permission_service: PermissionService = Depends(get_permission_service)
    ):
        """
        Lấy thông tin quyền hạn theo ID (chỉ dành cho người có quyền 'permission:read_all').
        """
        return await permission_service.get_permission(permission_id)

    @router.put("/{permission_id}", response_model=PermissionInResponse,
                dependencies=[Depends(requires_permission("permission:update"))]) # Yêu cầu quyền permission:update
    async def update_existing_permission(
        permission_id: Annotated[str, Path(description="ID của quyền hạn cần cập nhật")],
        permission_in: PermissionCreate, # Dùng PermissionCreate vì nó có name và description
        permission_service: PermissionService = Depends(get_permission_service)
    ):
        """
        Cập nhật thông tin quyền hạn theo ID (chỉ dành cho người có quyền 'permission:update').
        """
        # Chuyển đổi PermissionCreate sang dict để truyền vào service
        update_data = permission_in.model_dump(exclude_unset=True)
        return await permission_service.update_permission(permission_id, update_data)

    @router.delete("/{permission_id}", status_code=status.HTTP_204_NO_CONTENT,
                dependencies=[Depends(requires_permission("permission:delete"))]) # Yêu cầu quyền permission:delete
    async def delete_existing_permission(
        permission_id: Annotated[str, Path(description="ID của quyền hạn cần xóa")],
        permission_service: PermissionService = Depends(get_permission_service)
    ):
        """
        Xóa quyền hạn theo ID (chỉ dành cho người có quyền 'permission:delete').
        """
        await permission_service.delete_permission(permission_id)
        return {"message": "Quyền hạn đã được xóa thành công."}
    
    return router # TRẢ VỀ ĐỐI TƯỢNG ROUTER
