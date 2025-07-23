# app/core/database.py

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from contextlib import asynccontextmanager # Thêm import này
from typing import Optional
from fastapi import FastAPI

# Biến toàn cục để lưu trữ client MongoDB
# KHÔNG NÊN KHỞI TẠO TRỰC TIẾP TẠI ĐÂY
# mongo_client: Optional[AsyncIOMotorClient] = None
# Thay thế bằng cách này để quản lý trạng thái tốt hơn
class MongoClientHolder:
    client: Optional[AsyncIOMotorClient] = None

mongo_client_holder = MongoClientHolder()


async def init_mongo():
    """Khởi tạo kết nối MongoDB."""
    print("Initializing MongoDB client...")
    try:
        mongo_client_holder.client = AsyncIOMotorClient(settings.MONGODB_URI, uuidRepresentation="standard")
        # Thử kết nối để kiểm tra
        await mongo_client_holder.client.admin.command('ping') 
        print("MongoDB client initialized successfully.")
    except Exception as e:
        print(f"Failed to initialize MongoDB client: {e}")
        raise # Rerise exception để ứng dụng không khởi động nếu DB lỗi

async def close_mongo():
    """Đóng kết nối MongoDB."""
    if mongo_client_holder.client:
        print("Closing MongoDB client...")
        mongo_client_holder.client.close()
        print("MongoDB client closed.")

async def get_database() -> AsyncIOMotorClient:
    """Dependency Injection để lấy instance database."""
    if not mongo_client_holder.client:
        raise RuntimeError("MongoDB client is not initialized. Ensure 'init_mongo()' has been called and startup event has run.")
    return mongo_client_holder.client[settings.MONGODB_DB_NAME]

# Dùng asynccontextmanager để quản lý lifespan
@asynccontextmanager
async def lifespan(app: FastAPI): # app: FastAPI là cần thiết cho lifespan
    await init_mongo()
    yield
    await close_mongo()