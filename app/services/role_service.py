# app/services/role_service.py

from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorClient

# Imports từ tầng repository
from app.repository.role import (
    get_role_by_id,
    get_role_by_name,
    create_role_db,
    update_role_db,
    delete_role_db,
    get_all_roles_db,
    find_users_with_role # Thêm vào để kiểm tra khi xóa role
)
from app.repository.permission import get_permissions_by_ids # Để lấy chi tiết quyền hạn từ IDs

# Imports từ tầng models
from app.models.role import RoleDBModel
from app.models.permission import PermissionDBModel

# Imports từ tầng schemas
from app.schemas.role import RoleCreate, RoleInResponse, RoleUpdate
from app.schemas.permission import PermissionInResponse # Để nhúng chi tiết permission vào RoleInResponse


class RoleService:
    def __init__(self, db: AsyncIOMotorClient):
        self.db = db

    async def _populate_role_permissions_response(self, role_db_model: RoleDBModel) -> RoleInResponse:
        """
        Helper function để chuyển đổi RoleDBModel thành RoleInResponse và populate
        các trường `permissions` dựa trên IDs.
        """
        permissions_in_response: List[PermissionInResponse] = []
        if role_db_model.permission_ids:
            # Lấy thông tin chi tiết của các quyền hạn từ DB
            permissions_db_models = await get_permissions_by_ids(role_db_model.permission_ids, self.db)
            # Ánh xạ từ PermissionDBModel sang PermissionInResponse Schema
            permissions_in_response = [PermissionInResponse.model_validate(p) for p in permissions_db_models]
        
        role_response = RoleInResponse.model_validate(role_db_model)
        role_response.permissions = permissions_in_response
        return role_response

    async def create_new_role(self, role_in: RoleCreate) -> RoleInResponse:
        """
        Logic nghiệp vụ để tạo vai trò mới.
        - Kiểm tra trùng lặp tên vai trò.
        - Xác thực các permission IDs.
        - Lưu vào DB.
        """
        existing_role = await get_role_by_name(role_in.name, self.db)
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tên vai trò đã tồn tại."
            )
        
        # Validate permission_ids: Đảm bảo tất cả các ID quyền hạn đều tồn tại trong DB
        if role_in.permission_ids:
            found_permissions = await get_permissions_by_ids(role_in.permission_ids, self.db)
            if len(found_permissions) != len(set(role_in.permission_ids)): # Kiểm tra số lượng duy nhất
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Một hoặc nhiều ID quyền hạn không hợp lệ."
                )

        role_data_for_db = role_in.model_dump() # Chuyển đổi RoleCreate sang dict
        new_role_db_model = await create_role_db(role_data_for_db, self.db)
        return await self._populate_role_permissions_response(new_role_db_model)

    async def get_role(self, role_id: str) -> RoleInResponse:
        """
        Lấy thông tin vai trò theo ID.
        """
        role_db_model = await get_role_by_id(role_id, self.db)
        if not role_db_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vai trò không tìm thấy.")
        return await self._populate_role_permissions_response(role_db_model)

    async def get_role_by_name(self, name: str) -> Optional[RoleInResponse]:
        """
        Lấy thông tin vai trò theo tên.
        Trả về None nếu không tìm thấy (để hàm gọi xử lý).
        """
        role_db_model = await get_role_by_name(name, self.db)
        if not role_db_model:
            return None
        return await self._populate_role_permissions_response(role_db_model)

    async def update_role(self, role_id: str, role_update: RoleUpdate) -> RoleInResponse:
        """
        Cập nhật thông tin vai trò.
        - Xác thực các permission IDs nếu có.
        - Lưu vào DB.
        """
        role_db_model = await get_role_by_id(role_id, self.db)
        if not role_db_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vai trò không tìm thấy.")

        update_data = role_update.model_dump(exclude_unset=True) # Chỉ lấy các trường được set trong request

        # Validate permission_ids khi cập nhật
        if "permission_ids" in update_data and update_data["permission_ids"] is not None:
            if update_data["permission_ids"]:
                found_permissions = await get_permissions_by_ids(update_data["permission_ids"], self.db)
                if len(found_permissions) != len(set(update_data["permission_ids"])):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Một hoặc nhiều ID quyền hạn không hợp lệ trong dữ liệu cập nhật."
                    )
            # Nếu permission_ids là list rỗng, nó vẫn sẽ cập nhật để xóa tất cả quyền

        updated_role_db_model = await update_role_db(role_id, update_data, self.db)
        if not updated_role_db_model:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Không thể cập nhật vai trò.")
        
        return await self._populate_role_permissions_response(updated_role_db_model)

    async def delete_role(self, role_id: str) -> bool:
        """
        Xóa vai trò.
        - Kiểm tra xem có người dùng nào đang gán vai trò này không.
        - Xóa khỏi DB.
        """
        role_db_model = await get_role_by_id(role_id, self.db)
        if not role_db_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vai trò không tìm thấy.")
        
        # Kiểm tra xem có người dùng nào đang gán vai trò này không
        # Đây là một bước quan trọng để đảm bảo tính toàn vẹn dữ liệu
        if await find_users_with_role(role_id, self.db): # Hàm này được thêm vào role_repository.py
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, # Conflict
                detail="Không thể xóa vai trò vì có người dùng đang được gán vai trò này."
            )
        
        deleted = await delete_role_db(role_id, self.db)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Không thể xóa vai trò.")
        return deleted

    async def get_all_roles(self) -> List[RoleInResponse]:
        """
        Lấy tất cả vai trò.
        """
        all_roles_db = await get_all_roles_db(self.db)
        roles_in_response = []
        for role_db in all_roles_db:
            roles_in_response.append(await self._populate_role_permissions_response(role_db))
        return roles_in_response