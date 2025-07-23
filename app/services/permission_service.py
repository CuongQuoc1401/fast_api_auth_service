# app/services/permission_service.py

from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorClient

# Imports từ tầng repository
from app.repository.permission import (
    get_permission_by_id,
    get_permission_by_name,
    create_permission_db,
    update_permission_db,
    delete_permission_db,
    get_all_permissions_db,
    find_roles_with_permission # Thêm vào để kiểm tra khi xóa permission
)

# Imports từ tầng models
from app.models.permission import PermissionDBModel

# Imports từ tầng schemas
from app.schemas.permission import PermissionCreate, PermissionInResponse


class PermissionService:
    def __init__(self, db: AsyncIOMotorClient):
        self.db = db

    async def create_new_permission(self, permission_in: PermissionCreate) -> PermissionInResponse:
        """
        Logic nghiệp vụ để tạo quyền hạn mới.
        - Kiểm tra trùng lặp tên quyền hạn.
        - Lưu vào DB.
        """
        existing_permission = await get_permission_by_name(permission_in.name, self.db)
        if existing_permission:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tên quyền hạn đã tồn tại."
            )
        
        permission_data_for_db = permission_in.model_dump()
        new_permission_db_model = await create_permission_db(permission_data_for_db, self.db)
        return PermissionInResponse.model_validate(new_permission_db_model)

    async def get_permission(self, permission_id: str) -> PermissionInResponse:
        """
        Lấy thông tin quyền hạn theo ID.
        """
        permission_db_model = await get_permission_by_id(permission_id, self.db)
        if not permission_db_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quyền hạn không tìm thấy.")
        return PermissionInResponse.model_validate(permission_db_model)

    async def get_permission_by_name(self, name: str) -> Optional[PermissionInResponse]:
        """
        Lấy thông tin quyền hạn theo tên.
        """
        permission_db_model = await get_permission_by_name(name, self.db)
        if not permission_db_model:
            return None # Trả về None nếu không tìm thấy
        return PermissionInResponse.model_validate(permission_db_model)

    async def update_permission(self, permission_id: str, update_data: Dict[str, Any]) -> PermissionInResponse:
        """
        Cập nhật thông tin quyền hạn.
        """
        permission_db_model = await get_permission_by_id(permission_id, self.db)
        if not permission_db_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quyền hạn không tìm thấy.")
        
        # Thêm logic kiểm tra nếu cần (ví dụ: không cho phép đổi tên nếu đã có tên đó)
        if "name" in update_data and update_data["name"] != permission_db_model.name:
            existing_by_new_name = await get_permission_by_name(update_data["name"], self.db)
            if existing_by_new_name and str(existing_by_new_name.id) != permission_id:
                 raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tên quyền hạn mới đã tồn tại."
                )

        updated_permission_db_model = await update_permission_db(permission_id, update_data, self.db)
        if not updated_permission_db_model:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Không thể cập nhật quyền hạn.")
        
        return PermissionInResponse.model_validate(updated_permission_db_model)

    async def delete_permission(self, permission_id: str) -> bool:
        """
        Xóa quyền hạn.
        - Kiểm tra xem có vai trò nào đang gán quyền hạn này không.
        - Xóa khỏi DB.
        """
        permission_db_model = await get_permission_by_id(permission_id, self.db)
        if not permission_db_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quyền hạn không tìm thấy.")
        
        # Kiểm tra xem có vai trò nào đang sử dụng quyền hạn này không
        if await find_roles_with_permission(permission_id, self.db): # Hàm này được thêm vào permission_repository.py
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Không thể xóa quyền hạn vì có vai trò đang được gán quyền hạn này."
            )

        deleted = await delete_permission_db(permission_id, self.db)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Không thể xóa quyền hạn.")
        return deleted

    async def get_all_permissions(self) -> List[PermissionInResponse]:
        """
        Lấy tất cả quyền hạn.
        """
        all_permissions_db = await get_all_permissions_db(self.db)
        return [PermissionInResponse.model_validate(p) for p in all_permissions_db]