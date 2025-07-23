# app/repository/user.py

from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, List, Dict, Any
from bson import ObjectId
from datetime import datetime, timezone

from app.models.user import UserDBModel # Chỉ tương tác với Database Model

async def get_user_by_id(user_id: str, db: AsyncIOMotorClient) -> Optional[UserDBModel]:
    """Lấy thông tin người dùng từ DB bằng ID."""
    users_collection = db["users"]
    if not ObjectId.is_valid(user_id):
        return None
    user_doc = await users_collection.find_one({"_id": ObjectId(user_id)})
    if user_doc:
        # Chuyển đổi ObjectId sang str trước khi validate
        doc_to_validate = {**user_doc, "_id": str(user_doc["_id"])}
        return UserDBModel.model_validate(doc_to_validate)
    return None

async def get_user_by_username(username: str, db: AsyncIOMotorClient) -> Optional[UserDBModel]:
    """Lấy thông tin người dùng từ DB bằng username."""
    users_collection = db["users"]
    user_doc = await users_collection.find_one({"username": username})
    if user_doc:
        # Chuyển đổi ObjectId sang str trước khi validate
        doc_to_validate = {**user_doc, "_id": str(user_doc["_id"])}
        return UserDBModel.model_validate(doc_to_validate)
    return None

async def get_user_by_email(email: str, db: AsyncIOMotorClient) -> Optional[UserDBModel]:
    """Lấy thông tin người dùng từ DB bằng email."""
    users_collection = db["users"]
    user_doc = await users_collection.find_one({"email": email})
    if user_doc:
        # Chuyển đổi ObjectId sang str trước khi validate
        doc_to_validate = {**user_doc, "_id": str(user_doc["_id"])}
        return UserDBModel.model_validate(doc_to_validate)
    return None

async def create_user_db(user_data: Dict[str, Any], db: AsyncIOMotorClient) -> UserDBModel:
    """
    Tạo một người dùng mới trong DB.
    Nhận vào dict dữ liệu đã được chuẩn bị sẵn, bao gồm cả hashed_password và các trường DB khác.
    """
    users_collection = db["users"]
    
    # Let MongoDB assign the _id, or if assigned, ensure it's ObjectId
    if "_id" not in user_data:
        user_data["_id"] = ObjectId()
    
    now_utc = datetime.now(timezone.utc)
    user_data.setdefault("created_at", now_utc)
    user_data.setdefault("updated_at", now_utc)
    user_data.setdefault("last_login_at", None)
    user_data.setdefault("failed_login_attempts", 0)
    user_data.setdefault("lockout_until", None)

    result = await users_collection.insert_one(user_data)
    inserted_user_doc = await users_collection.find_one({"_id": result.inserted_id})
    if inserted_user_doc:
        # Chuyển đổi ObjectId sang str trước khi validate
        doc_to_validate = {**inserted_user_doc, "_id": str(inserted_user_doc["_id"])}
        return UserDBModel.model_validate(doc_to_validate)
    raise Exception("Failed to retrieve inserted user document.") # Should not happen

async def update_user_db(user_id: str, update_data: Dict[str, Any], db: AsyncIOMotorClient) -> Optional[UserDBModel]:
    """
    Cập nhật thông tin người dùng trong DB.
    Nhận vào dict các trường cần cập nhật.
    """
    users_collection = db["users"]
    if not ObjectId.is_valid(user_id):
        return None
    
    update_data["updated_at"] = datetime.now(timezone.utc) # Tự động cập nhật timestamp

    result = await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_data}
    )
    if result.modified_count > 0:
        updated_user_doc = await users_collection.find_one({"_id": ObjectId(user_id)})
        if updated_user_doc:
            # Chuyển đổi ObjectId sang str trước khi validate
            doc_to_validate = {**updated_user_doc, "_id": str(updated_user_doc["_id"])}
            return UserDBModel.model_validate(doc_to_validate)
    return None

async def delete_user_db(user_id: str, db: AsyncIOMotorClient) -> bool:
    """Xóa người dùng khỏi DB."""
    users_collection = db["users"]
    if not ObjectId.is_valid(user_id):
        return False
    result = await users_collection.delete_one({"_id": ObjectId(user_id)})
    return result.deleted_count > 0

async def update_last_login_at(user_id: str, db: AsyncIOMotorClient) -> None:
    """Cập nhật thời gian đăng nhập cuối cùng cho người dùng."""
    users_collection = db["users"]
    if not ObjectId.is_valid(user_id):
        return
    await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"last_login_at": datetime.now(timezone.utc)}}
    )

async def increment_failed_login_attempts(user_id: str, db: AsyncIOMotorClient) -> None:
    """Tăng số lần đăng nhập thất bại của người dùng."""
    users_collection = db["users"]
    if not ObjectId.is_valid(user_id):
        return
    await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$inc": {"failed_login_attempts": 1}}
    )

async def set_user_lockout(user_id: str, lockout_until: datetime, db: AsyncIOMotorClient) -> None:
    """Đặt thời gian khóa tài khoản cho người dùng."""
    users_collection = db["users"]
    if not ObjectId.is_valid(user_id):
        return
    await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"lockout_until": lockout_until}}
    )

async def clear_user_lockout_and_attempts(user_id: str, db: AsyncIOMotorClient) -> None:
    """Xóa thời gian khóa tài khoản và reset số lần đăng nhập thất bại."""
    users_collection = db["users"]
    if not ObjectId.is_valid(user_id):
        return
    await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"lockout_until": None, "failed_login_attempts": 0}}
    )

async def get_all_users_db(db: AsyncIOMotorClient) -> List[UserDBModel]:
    """Lấy tất cả người dùng từ DB."""
    users_collection = db["users"]
    users_cursor = users_collection.find({})
    # Chuyển đổi ObjectId sang str cho mỗi tài liệu trước khi validate
    return [UserDBModel.model_validate({**doc, "_id": str(doc["_id"])}) async for doc in users_cursor]