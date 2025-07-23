# main.py

from fastapi import FastAPI
from app.core.config import settings
from app.core.database import lifespan # Import lifespan từ database.py
from fastapi.middleware.cors import CORSMiddleware

# THAY ĐỔI: Import các hàm get_router từ mỗi file endpoint
from app.api.v1.endpoints.auth import get_auth_router
from app.api.v1.endpoints.users import get_users_router # Đã sửa để import hàm
from app.api.v1.endpoints.roles import get_roles_router # Đã sửa để import hàm
from app.api.v1.endpoints.permissions import get_permissions_router # Đã sửa để import hàm

print("--- main.py: Starting FastAPI app initialization ---")

app = FastAPI(
    title=settings.APP_NAME,
    description="Microservice for user authentication and dynamic role-based access control.",
    version=settings.APP_VERSION,
    lifespan=lifespan # Sử dụng lifespan để quản lý startup/shutdown events
)

# Cấu hình CORS
origins = [
    "http://localhost:3000", # Nếu frontend của bạn chạy ở localhost
    "https://ten_mien_trang_web_frontend_cua_ban.com", # Thay thế bằng tên miền thực tế
    # Thêm các tên miền khác nếu có
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # Cho phép các nguồn gốc này
    allow_credentials=True,         # Cho phép gửi cookie/authentication headers
    allow_methods=["*"],            # Cho phép tất cả các phương thức HTTP (GET, POST, PUT, DELETE...)
    allow_headers=["*"],            # Cho phép tất cả các headers
)

# THAY ĐỔI: Gọi hàm để lấy đối tượng router và sau đó include nó
auth_router_instance = get_auth_router()
app.include_router(auth_router_instance, prefix=f"{settings.API_V1_STR}", tags=["Authentication & User Profile"])

# Áp dụng tương tự cho các router khác:
users_router_instance = get_users_router() # Gọi hàm get_users_router()
app.include_router(users_router_instance, prefix=f"{settings.API_V1_STR}", tags=["User Management"])

roles_router_instance = get_roles_router() # Gọi hàm get_roles_router()
app.include_router(roles_router_instance, prefix=f"{settings.API_V1_STR}", tags=["Role Management & Assignment"])

permissions_router_instance = get_permissions_router() # Gọi hàm get_permissions_router()
app.include_router(permissions_router_instance, prefix=f"{settings.API_V1_STR}", tags=["Permission Management"])

@app.get("/health", tags=["Health Check"])
async def health_check():
    """
    Endpoint kiểm tra trạng thái sức khỏe của dịch vụ.
    """
    return {"status": "ok", "service": "Auth & RBAC Microservice"}

print("--- main.py: FastAPI app initialization complete ---")
