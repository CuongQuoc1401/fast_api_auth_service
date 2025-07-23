# app/repository/permission.py

from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, List, Dict, Any
from bson import ObjectId
from datetime import datetime, timezone

from app.models.permission import PermissionDBModel # Chỉ tương tác với Database Model

async def get_permission_by_id(permission_id: str, db: AsyncIOMotorClient) -> Optional[PermissionDBModel]:
    """Lấy thông tin quyền hạn từ DB bằng ID."""
    permissions_collection = db["permissions"]
    if not ObjectId.is_valid(permission_id):
        return None
    permission_doc = await permissions_collection.find_one({"_id": ObjectId(permission_id)})
    if permission_doc:
        # Chuyển đổi ObjectId sang str trước khi validate
        doc_to_validate = {**permission_doc, "_id": str(permission_doc["_id"])}
        return PermissionDBModel.model_validate(doc_to_validate)
    return None

async def get_permission_by_name(name: str, db: AsyncIOMotorClient) -> Optional[PermissionDBModel]:
    """Lấy thông tin quyền hạn từ DB bằng tên quyền hạn."""
    permissions_collection = db["permissions"]
    permission_doc = await permissions_collection.find_one({"name": name})
    if permission_doc:
        # Chuyển đổi ObjectId sang str trước khi validate
        doc_to_validate = {**permission_doc, "_id": str(permission_doc["_id"])}
        return PermissionDBModel.model_validate(doc_to_validate)
    return None

async def create_permission_db(permission_data: Dict[str, Any], db: AsyncIOMotorClient) -> PermissionDBModel:
    """Tạo một quyền hạn mới trong DB."""
    permissions_collection = db["permissions"]
    if "_id" not in permission_data:
        permission_data["_id"] = ObjectId()
    
    now_utc = datetime.now(timezone.utc)
    permission_data.setdefault("created_at", now_utc)
    permission_data.setdefault("updated_at", now_utc)

    result = await permissions_collection.insert_one(permission_data)
    inserted_permission_doc = await permissions_collection.find_one({"_id": result.inserted_id})
    if inserted_permission_doc:
        # Chuyển đổi ObjectId sang str trước khi validate
        doc_to_validate = {**inserted_permission_doc, "_id": str(inserted_permission_doc["_id"])}
        return PermissionDBModel.model_validate(doc_to_validate)
    raise Exception("Failed to retrieve inserted permission document.") # Should not happen

async def update_permission_db(permission_id: str, update_data: Dict[str, Any], db: AsyncIOMotorClient) -> Optional[PermissionDBModel]:
    """Cập nhật thông tin quyền hạn trong DB."""
    permissions_collection = db["permissions"]
    if not ObjectId.is_valid(permission_id):
        return None
    
    update_data["updated_at"] = datetime.now(timezone.utc)

    result = await permissions_collection.update_one(
        {"_id": ObjectId(permission_id)},
        {"$set": update_data}
    )
    if result.modified_count > 0:
        updated_permission_doc = await permissions_collection.find_one({"_id": ObjectId(permission_id)})
        if updated_permission_doc:
            # Chuyển đổi ObjectId sang str trước khi validate
            doc_to_validate = {**updated_permission_doc, "_id": str(updated_permission_doc["_id"])}
            return PermissionDBModel.model_validate(doc_to_validate)
    return None

async def delete_permission_db(permission_id: str, db: AsyncIOMotorClient) -> bool:
    """Xóa quyền hạn khỏi DB."""
    permissions_collection = db["permissions"]
    if not ObjectId.is_valid(permission_id):
        return False
    result = await permissions_collection.delete_one({"_id": ObjectId(permission_id)})
    return result.deleted_count > 0

async def get_permissions_by_ids(permission_ids: List[str], db: AsyncIOMotorClient) -> List[PermissionDBModel]:
    """Lấy danh sách quyền hạn theo danh sách ID."""
    permissions_collection = db["permissions"]
    obj_ids = [ObjectId(pid) for pid in permission_ids if ObjectId.is_valid(pid)]
    if not obj_ids:
        return []
    permissions_cursor = permissions_collection.find({"_id": {"$in": obj_ids}})
    # Chuyển đổi ObjectId sang str cho mỗi tài liệu trước khi validate
    return [PermissionDBModel.model_validate({**doc, "_id": str(doc["_id"])}) async for doc in permissions_cursor]

async def get_all_permissions_db(db: AsyncIOMotorClient) -> List[PermissionDBModel]:
    """Lấy tất cả quyền hạn từ DB."""
    permissions_collection = db["permissions"]
    permissions_cursor = permissions_collection.find({})
    # Chuyển đổi ObjectId sang str cho mỗi tài liệu trước khi validate
    return [PermissionDBModel.model_validate({**doc, "_id": str(doc["_id"])}) async for doc in permissions_cursor]

async def find_roles_with_permission(permission_id: str, db: AsyncIOMotorClient) -> bool:
    """Kiểm tra xem có vai trò nào có quyền hạn này không."""
    roles_collection = db["roles"]
    if not ObjectId.is_valid(permission_id):
        return False
    # Tìm kiếm bất kỳ role nào có permission_id trong mảng permission_ids của họ
    role_with_permission = await roles_collection.find_one({"permission_ids": permission_id})
    return role_with_permission is not None