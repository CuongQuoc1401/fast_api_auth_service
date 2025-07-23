# tests/test_auth.py

import pytest
from httpx import AsyncClient
from fastapi import status
from typing import Dict

from app.schemas.user import UserInResponse

# Các fixtures từ conftest.py sẽ tự động được phát hiện và sử dụng

@pytest.mark.asyncio
async def test_register_user_success(test_app_client: AsyncClient):
    """
    Kiểm thử đăng ký người dùng thành công.
    """
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "NewUserPassword123!"
    }
    response = await test_app_client.post("/api/v1/auth/register", json=user_data)
    
    assert response.status_code == status.HTTP_201_CREATED
    response_json = response.json()
    assert response_json["username"] == "newuser"
    assert response_json["email"] == "newuser@example.com"
    assert "id" in response_json
    assert "roles" in response_json
    assert "permissions" in response_json
    assert response_json["is_active"] is True
    assert response_json["is_superuser"] is False

@pytest.mark.asyncio
async def test_register_user_duplicate_username(test_app_client: AsyncClient, register_test_user: UserInResponse):
    """
    Kiểm thử đăng ký người dùng với username đã tồn tại.
    """
    user_data = {
        "username": register_test_user.username, # Username đã tồn tại
        "email": "another@example.com",
        "password": "Password123!"
    }
    response = await test_app_client.post("/api/v1/auth/register", json=user_data)
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Tên người dùng đã tồn tại."

@pytest.mark.asyncio
async def test_register_user_duplicate_email(test_app_client: AsyncClient, register_test_user: UserInResponse):
    """
    Kiểm thử đăng ký người dùng với email đã tồn tại.
    """
    user_data = {
        "username": "another_user",
        "email": register_test_user.email, # Email đã tồn tại
        "password": "Password123!"
    }
    response = await test_app_client.post("/api/v1/auth/register", json=user_data)
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Email đã được đăng ký."

@pytest.mark.asyncio
async def test_login_success(test_app_client: AsyncClient, register_test_user: UserInResponse):
    """
    Kiểm thử đăng nhập thành công.
    """
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
    response_json = response.json()
    assert "access_token" in response_json
    assert "refresh_token" in response_json
    assert response_json["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_invalid_credentials(test_app_client: AsyncClient):
    """
    Kiểm thử đăng nhập với thông tin không hợp lệ.
    """
    login_data = {
        "username": "nonexistent",
        "password": "wrongpassword"
    }
    response = await test_app_client.post(
        "/api/v1/auth/login",
        data={"username": login_data["username"], "password": login_data["password"]},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Tên người dùng hoặc mật khẩu không đúng."

@pytest.mark.asyncio
async def test_get_me_protected_endpoint(test_app_client: AsyncClient, test_user_auth_headers: Dict[str, str]):
    """
    Kiểm thử truy cập endpoint /me với Access Token hợp lệ.
    """
    response = await test_app_client.get("/api/v1/auth/me", headers=test_user_auth_headers)
    
    assert response.status_code == status.HTTP_200_OK
    response_json = response.json()
    assert response_json["username"] == "testuser"
    assert response_json["email"] == "test@example.com"
    assert "roles" in response_json
    assert "permissions" in response_json

@pytest.mark.asyncio
async def test_get_me_unauthorized(test_app_client: AsyncClient):
    """
    Kiểm thử truy cập endpoint /me không có Access Token.
    """
    response = await test_app_client.get("/api/v1/auth/me")
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Không thể xác thực thông tin đăng nhập"

@pytest.mark.asyncio
async def test_refresh_token_success(test_app_client: AsyncClient, get_test_user_token: Token):
    """
    Kiểm thử làm mới token thành công.
    """
    # Refresh token được gửi qua Authorization header
    headers = {"Authorization": f"Bearer {get_test_user_token.refresh_token}"}
    response = await test_app_client.post("/api/v1/auth/refresh-token", headers=headers)

    assert response.status_code == status.HTTP_200_OK
    response_json = response.json()
    assert "access_token" in response_json
    assert "refresh_token" in response_json
    assert response_json["token_type"] == "bearer"
    # Access token mới phải khác token cũ (thường là vậy)
    assert response_json["access_token"] != get_test_user_token.access_token

@pytest.mark.asyncio
async def test_refresh_token_invalid(test_app_client: AsyncClient):
    """
    Kiểm thử làm mới token với refresh token không hợp lệ.
    """
    headers = {"Authorization": "Bearer invalid.token.string"}
    response = await test_app_client.post("/api/v1/auth/refresh-token", headers=headers)
    
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Refresh token không hợp lệ hoặc đã hết hạn."
