# app/repository/role.py

from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, List, Dict, Any
from bson import ObjectId
from datetime import datetime, timezone

from app.models.role import RoleDBModel # Chỉ tương tác với Database Model

async def get_role_by_id(role_id: str, db: AsyncIOMotorClient) -> Optional[RoleDBModel]:
    """Lấy thông tin vai trò từ DB bằng ID."""
    roles_collection = db["roles"]
    if not ObjectId.is_valid(role_id):
        return None
    role_doc = await roles_collection.find_one({"_id": ObjectId(role_id)})
    if role_doc:
        # Chuyển đổi ObjectId sang str trước khi validate
        doc_to_validate = {**role_doc, "_id": str(role_doc["_id"])}
        return RoleDBModel.model_validate(doc_to_validate)
    return None

async def get_role_by_name(name: str, db: AsyncIOMotorClient) -> Optional[RoleDBModel]:
    """Lấy thông tin vai trò từ DB bằng tên vai trò."""
    roles_collection = db["roles"]
    role_doc = await roles_collection.find_one({"name": name})
    if role_doc:
        # Chuyển đổi ObjectId sang str trước khi validate
        doc_to_validate = {**role_doc, "_id": str(role_doc["_id"])}
        return RoleDBModel.model_validate(doc_to_validate)
    return None

async def create_role_db(role_data: Dict[str, Any], db: AsyncIOMotorClient) -> RoleDBModel:
    """Tạo một vai trò mới trong DB."""
    roles_collection = db["roles"]
    if "_id" not in role_data:
        role_data["_id"] = ObjectId()
    
    now_utc = datetime.now(timezone.utc)
    role_data.setdefault("created_at", now_utc)
    role_data.setdefault("updated_at", now_utc)

    result = await roles_collection.insert_one(role_data)
    inserted_role_doc = await roles_collection.find_one({"_id": result.inserted_id})
    if inserted_role_doc:
        # Chuyển đổi ObjectId sang str trước khi validate
        doc_to_validate = {**inserted_role_doc, "_id": str(inserted_role_doc["_id"])}
        return RoleDBModel.model_validate(doc_to_validate)
    raise Exception("Failed to retrieve inserted role document.") # Should not happen

async def update_role_db(role_id: str, update_data: Dict[str, Any], db: AsyncIOMotorClient) -> Optional[RoleDBModel]:
    """Cập nhật thông tin vai trò trong DB."""
    roles_collection = db["roles"]
    if not ObjectId.is_valid(role_id):
        return None
    
    update_data["updated_at"] = datetime.now(timezone.utc)

    result = await roles_collection.update_one(
        {"_id": ObjectId(role_id)},
        {"$set": update_data}
    )
    if result.modified_count > 0:
        updated_role_doc = await roles_collection.find_one({"_id": ObjectId(role_id)})
        if updated_role_doc:
            # Chuyển đổi ObjectId sang str trước khi validate
            doc_to_validate = {**updated_role_doc, "_id": str(updated_role_doc["_id"])}
            return RoleDBModel.model_validate(doc_to_validate)
    return None

async def delete_role_db(role_id: str, db: AsyncIOMotorClient) -> bool:
    """Xóa vai trò khỏi DB."""
    roles_collection = db["roles"]
    if not ObjectId.is_valid(role_id):
        return False
    result = await roles_collection.delete_one({"_id": ObjectId(role_id)})
    return result.deleted_count > 0

async def get_roles_by_ids(role_ids: List[str], db: AsyncIOMotorClient) -> List[RoleDBModel]:
    """Lấy danh sách vai trò theo danh sách ID."""
    roles_collection = db["roles"]
    obj_ids = [ObjectId(rid) for rid in role_ids if ObjectId.is_valid(rid)]
    if not obj_ids:
        return []
    roles_cursor = roles_collection.find({"_id": {"$in": obj_ids}})
    # Chuyển đổi ObjectId sang str cho mỗi tài liệu trước khi validate
    return [RoleDBModel.model_validate({**doc, "_id": str(doc["_id"])}) async for doc in roles_cursor]

async def get_all_roles_db(db: AsyncIOMotorClient) -> List[RoleDBModel]:
    """Lấy tất cả vai trò từ DB."""
    roles_collection = db["roles"]
    roles_cursor = roles_collection.find({})
    # Chuyển đổi ObjectId sang str cho mỗi tài liệu trước khi validate
    return [RoleDBModel.model_validate({**doc, "_id": str(doc["_id"])}) async for doc in roles_cursor]

async def find_users_with_role(role_id: str, db: AsyncIOMotorClient) -> bool:
    """Kiểm tra xem có người dùng nào được gán vai trò này không."""
    users_collection = db["users"]
    if not ObjectId.is_valid(role_id):
        return False
    # Tìm kiếm bất kỳ user nào có role_id trong mảng role_ids của họ
    user_with_role = await users_collection.find_one({"role_ids": role_id})
    return user_with_role is not None