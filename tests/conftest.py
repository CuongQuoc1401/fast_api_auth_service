# tests/conftest.py

import pytest
import asyncio
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta, timezone
from typing import Dict # Thêm import Dict

# Import các thành phần của ứng dụng
from main import app # Import ứng dụng FastAPI chính của bạn
from app.core.config import settings
# SỬA ĐỔI DÒNG NÀY: Bỏ 'client as mongo_client_instance'
from app.core.database import get_database, close_mongo 
from app.core.security import get_password_hash, create_access_token, create_refresh_token
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserInResponse

# Đảm bảo pytest-asyncio được cấu hình đúng
@pytest.fixture(scope="session")
def event_loop():
    """Tạo một event loop riêng cho các bài kiểm thử bất đồng bộ."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_db_client():
    """
    Fixture cung cấp một client MongoDB riêng cho kiểm thử.
    Sử dụng một database riêng để tránh ảnh hưởng đến database phát triển.
    """
    # Thay đổi tên database để sử dụng cho kiểm thử
    original_db_name = settings.MONGO_DB_NAME # Lưu tên gốc
    settings.MONGO_DB_NAME = settings.MONGO_DB_NAME + "_test"
    print(f"\nUsing test database: {settings.MONGO_DB_NAME}")

    # Khởi tạo một client mới cho test
    test_client = AsyncIOMotorClient(settings.MONGO_CONNECTION_STRING, uuidRepresentation="standard")
    
    # Đảm bảo database client được đóng sau khi tất cả các test hoàn tất
    yield test_client
    
    # Dọn dẹp database kiểm thử sau khi tất cả các test session kết thúc
    print(f"\nDropping test database: {settings.MONGO_DB_NAME}")
    await test_client.drop_database(settings.MONGO_DB_NAME)
    test_client.close()
    settings.MONGO_DB_NAME = original_db_name # Reset lại tên DB sau khi test xong

@pytest.fixture(scope="function", autouse=True)
async def clear_test_db(test_db_client: AsyncIOMotorClient):
    """
    Fixture tự động dọn dẹp tất cả các collections trong database kiểm thử
    trước mỗi bài kiểm thử.
    """
    db = test_db_client[settings.MONGO_DB_NAME]
    print("\nClearing test database collections...")
    for collection_name in await db.list_collection_names():
        if collection_name not in ["system.indexes"]: # Tránh xóa các collection hệ thống
            await db[collection_name].delete_many({})
            print(f"  Cleared collection: {collection_name}")
    yield
    print("Test database collections cleared.")

@pytest.fixture(scope="function")
async def test_app_client(test_db_client: AsyncIOMotorClient):
    """
    Fixture cung cấp một client HTTP bất đồng bộ cho ứng dụng FastAPI.
    Nó ghi đè dependency get_database để sử dụng test_db_client.
    """
    # Ghi đè dependency get_database để nó trả về test_db_client
    # Đảm bảo rằng get_database trả về một đối tượng database cụ thể từ client
    async def override_get_database():
        return test_db_client[settings.MONGO_DB_NAME]

    app.dependency_overrides[get_database] = override_get_database
    
    # Sử dụng httpx.AsyncClient để thực hiện các request HTTP đến ứng dụng
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    # Xóa ghi đè dependency sau khi test hoàn tất
    app.dependency_overrides.clear()

# --- Fixtures cho người dùng và xác thực ---

@pytest.fixture(scope="function")
async def register_test_user(test_app_client: AsyncClient) -> UserInResponse:
    """Fixture để đăng ký một người dùng kiểm thử cơ bản."""
    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        password="TestPassword123!"
    )
    response = await test_app_client.post("/api/v1/auth/register", json=user_data.model_dump())
    assert response.status_code == status.HTTP_201_CREATED
    return UserInResponse.model_validate(response.json())

@pytest.fixture(scope="function")
async def get_test_user_token(test_app_client: AsyncClient, register_test_user: UserInResponse) -> Token:
    """Fixture để lấy token cho người dùng kiểm thử cơ bản."""
    login_data = {
        "username": register_test_user.username,
        "password": "TestPassword123!"
    }
    response = await test_app_client.post(
        "/api/v1/auth/login",
        data={"username": login_data["username"], "password": login_data["password"]},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == status.HTTP_200_OK
    return Token.model_validate(response.json())

@pytest.fixture(scope="function")
async def register_superadmin_user(test_app_client: AsyncClient) -> UserInResponse:
    """Fixture để đăng ký một người dùng superadmin kiểm thử."""
    superadmin_data = UserCreate(
        username=settings.SUPERADMIN_USERNAME,
        email=settings.SUPERADMIN_EMAIL,
        password=settings.SUPERADMIN_PASSWORD,
        is_superuser=True # Đảm bảo là superuser
    )
    response = await test_app_client.post("/api/v1/auth/register", json=superadmin_data.model_dump())
    assert response.status_code == status.HTTP_201_CREATED
    return UserInResponse.model_validate(response.json())

@pytest.fixture(scope="function")
async def get_superadmin_token(test_app_client: AsyncClient, register_superadmin_user: UserInResponse) -> Token:
    """Fixture để lấy token cho người dùng superadmin kiểm thử."""
    login_data = {
        "username": register_superadmin_user.username,
        "password": settings.SUPERADMIN_PASSWORD
    }
    response = await test_app_client.post(
        "/api/v1/auth/login",
        data={"username": login_data["username"], "password": login_data["password"]},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == status.HTTP_200_OK
    return Token.model_validate(response.json())

@pytest.fixture(scope="function")
async def superadmin_auth_headers(get_superadmin_token: Token) -> Dict[str, str]:
    """Fixture cung cấp headers xác thực cho superadmin."""
    return {"Authorization": f"Bearer {get_superadmin_token.access_token}"}

@pytest.fixture(scope="function")
async def test_user_auth_headers(get_test_user_token: Token) -> Dict[str, str]:
    """Fixture cung cấp headers xác thực cho người dùng cơ bản."""
    return {"Authorization": f"Bearer {get_test_user_token.access_token}"}

