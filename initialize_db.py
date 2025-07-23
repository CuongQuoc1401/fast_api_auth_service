# initialize_db.py

import asyncio
from datetime import datetime, timezone
from typing import List # Thêm import List

# Imports từ app.core
from app.core.database import init_mongo, close_mongo, get_database
from app.core.security import get_password_hash
from app.core.config import settings # RẤT QUAN TRỌNG: Import settings

# Imports từ app.repository
from app.repository.role import (
    create_role_db,
    get_role_by_name,
    update_role_db,
    get_all_roles_db,
)
from app.repository.permission import (
    create_permission_db,
    get_permission_by_name,
    get_all_permissions_db,
)
from app.repository.user import (
    create_user_db,
    get_user_by_username,
    get_user_by_email,
    update_user_db,
)

# Imports từ app.schemas
from app.schemas.role import RoleCreate
from app.schemas.permission import PermissionCreate
from app.schemas.user import UserCreate

# Imports từ app.models (chỉ khi cần tạo instance trực tiếp để lấy ID, nhưng thường dùng DBModel)
from app.models.role import RoleDBModel
from app.models.permission import PermissionDBModel
from app.models.user import UserDBModel

# Thêm import AsyncIOMotorClient cho hàm helper
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId # Thêm import ObjectId

# Hàm helper để set permissions cho một role (sẽ gọi update_role_db)
async def set_permissions_for_role(role_id: str, permission_ids: List[str], db: AsyncIOMotorClient):
    """
    Cập nhật danh sách quyền hạn cho một vai trò.
    """
    await update_role_db(role_id, {"permission_ids": permission_ids}, db)

async def initialize_db_data():
    # Khởi tạo kết nối MongoDB
    await init_mongo() 
    db = await get_database()

    print("Initializing database data...")

    # --- Clear existing data (Optional, for fresh start) ---
    print("Clearing existing data...")
    await db["roles"].delete_many({})
    await db["permissions"].delete_many({})
    await db["users"].delete_many({})
    print("Existing data cleared.")

    # --- Create default Roles ---
    default_roles_data = [
        {"name": "superadmin", "description": "Full access to everything"},
        {"name": "admin", "description": "Manage users and roles (excluding superadmin)"},
        {"name": "moderator", "description": "Manage content and comments"},
        {"name": "editor", "description": "Create and edit own content"},
        {"name": "user", "description": "Basic authenticated user with limited permissions"},
        {"name": settings.DEFAULT_USER_ROLE_NAME, "description": "Default user role with basic viewing permissions"}
    ]

    existing_roles = {}
    print("Creating default roles...")
    for role_data in default_roles_data:
        # Trong repository, create_role_db sẽ tự thêm _id.
        # Nếu bạn muốn tạo _id ở đây và truyền vào, bạn sẽ cần chuyển nó thành str.
        # Tuy nhiên, cách hiện tại của create_role_db là nhận dict và tự gán ObjectId.
        # Lỗi có thể nằm ở cách create_role_db trả về hoặc cách RoleDBModel validate.
        # Chúng ta sẽ kiểm tra lại hàm create_role_db trong repository.role.py
        # để đảm bảo nó trả về một dict mà RoleDBModel có thể validate.
        role_db_model = await create_role_db(role_data, db) # Hàm này trả về RoleDBModel
        existing_roles[role_db_model.name] = str(role_db_model.id) # Lấy id từ model và chuyển thành string

    print("Default roles created.")
    print(f"Existing roles: {existing_roles}")

    # --- Create default Permissions ---
    default_permissions_data = [
        # User permissions
        {"name": "user:create", "description": "Create new users"},
        {"name": "user:read_all", "description": "Read all user profiles"},
        {"name": "user:read_own", "description": "Read own user profile"},
        {"name": "user:update", "description": "Update any user profile"},
        {"name": "user:update_own", "description": "Update own user profile"},
        {"name": "user:delete", "description": "Delete any user"},
        {"name": "user:assign_roles", "description": "Assign roles to users"},
        {"name": "user:update_status", "description": "Activate/Deactivate user accounts"},
        
        # Role permissions
        {"name": "role:create", "description": "Create new roles"},
        {"name": "role:read_all", "description": "Read all roles"},
        {"name": "role:update", "description": "Update any role"},
        {"name": "role:delete", "description": "Delete any role"},

        # Permission permissions (to manage permissions themselves)
        {"name": "permission:create", "description": "Create new permissions"},
        {"name": "permission:read_all", "description": "Read all permissions"},
        {"name": "permission:update", "description": "Update any permission"},
        {"name": "permission:delete", "description": "Delete any permission"},

        # Example content permissions
        {"name": "article:create", "description": "Create articles"},
        {"name": "article:read_all", "description": "Read all articles"},
        {"name": "article:read_own", "description": "Read own articles"},
        {"name": "article:update_own", "description": "Update own articles"},
        {"name": "article:update_any", "description": "Update any article"},
        {"name": "article:delete_own", "description": "Delete own articles"},
        {"name": "article:delete_any", "description": "Delete any article"},
    ]

    existing_permissions = {}
    print("Creating default permissions...")
    for perm_data in default_permissions_data:
        perm_db_model = await create_permission_db(perm_data, db)
        existing_permissions[perm_db_model.name] = str(perm_db_model.id)

    print("Default permissions created.")
    print(f"Existing permissions: {existing_permissions}")

    # --- Assign Permissions to Roles ---
    print("Assigning permissions to roles...")

    # SuperAdmin: All permissions
    all_perm_ids = list(existing_permissions.values())
    await set_permissions_for_role(existing_roles["superadmin"], all_perm_ids, db)

    # Admin: Manage users, roles, read permissions
    admin_perms = [
        existing_permissions["user:create"],
        existing_permissions["user:read_all"],
        existing_permissions["user:update"],
        existing_permissions["user:delete"],
        existing_permissions["user:assign_roles"],
        existing_permissions["user:update_status"],

        existing_permissions["role:create"],
        existing_permissions["role:read_all"],
        existing_permissions["role:update"],
        existing_permissions["role:delete"],
        existing_permissions["permission:read_all"],
    ]
    await set_permissions_for_role(existing_roles["admin"], admin_perms, db)

    # Moderator: Manage content, comments
    moderator_perms = [
        existing_permissions["article:read_all"],
        existing_permissions["article:update_any"],
        existing_permissions["article:delete_any"],
    ]
    await set_permissions_for_role(existing_roles["moderator"], moderator_perms, db)

    # Editor: Create/edit own content, read all articles
    editor_perms = [
        existing_permissions["article:create"],
        existing_permissions["article:read_all"],
        existing_permissions["article:read_own"],
        existing_permissions["article:update_own"],
        existing_permissions["article:delete_own"],
        existing_permissions["user:read_own"],
        existing_permissions["user:update_own"],
    ]
    await set_permissions_for_role(existing_roles["editor"], editor_perms, db)

    # User: Basic read own, update own, read all articles
    user_perms = [
        existing_permissions["user:read_own"],
        existing_permissions["user:update_own"],
        existing_permissions["article:read_all"],
    ]
    await set_permissions_for_role(existing_roles["user"], user_perms, db)

    # Viewer: Chỉ quyền đọc bài viết
    viewer_perms = [
        existing_permissions["article:read_all"],
    ]
    await set_permissions_for_role(existing_roles[settings.DEFAULT_USER_ROLE_NAME], viewer_perms, db)

    print("Permissions assigned to roles.")

    # --- Create default Users ---
    print("Creating default users...")

    # SuperAdmin User (Lấy thông tin từ settings)
    existing_superadmin = await get_user_by_username(settings.SUPERADMIN_USERNAME, db)
    if not existing_superadmin:
        superadmin_hashed_password = get_password_hash(settings.SUPERADMIN_PASSWORD)
        superadmin_user_data = {
            "username": settings.SUPERADMIN_USERNAME,
            "email": settings.SUPERADMIN_EMAIL,
            "hashed_password": superadmin_hashed_password,
            "role_ids": [existing_roles["superadmin"]],
            "is_active": True,
            "is_superuser": True,
        }
        await create_user_db(superadmin_user_data, db)
        print(f"Created superadmin user: {settings.SUPERADMIN_USERNAME}")
    else:
        print(f"Superadmin user '{settings.SUPERADMIN_USERNAME}' already exists. Skipping creation.")

    # Admin User
    admin_password = "AdminPassword123!"
    admin_hashed_password = get_password_hash(admin_password)
    admin_user_data = {
        "username": "admin",
        "email": "admin@example.com",
        "hashed_password": admin_hashed_password,
        "role_ids": [existing_roles["admin"]],
        "is_active": True,
        "is_superuser": False,
    }
    await create_user_db(admin_user_data, db)
    print(f"Created admin user with password: {admin_password}")

    # Editor User
    editor_password = "EditorPassword123!"
    editor_hashed_password = get_password_hash(editor_password)
    editor_user_data = {
        "username": "editor",
        "email": "editor@example.com",
        "hashed_password": editor_hashed_password,
        "role_ids": [existing_roles["editor"]],
        "is_active": True,
        "is_superuser": False,
    }
    await create_user_db(editor_user_data, db)
    print(f"Created editor user with password: {editor_password}")

    # Regular User
    user_password = "UserPassword123!"
    user_hashed_password = get_password_hash(user_password)
    user_user_data = {
        "username": "testuser",
        "email": "user@example.com",
        "hashed_password": user_hashed_password,
        "role_ids": [existing_roles["user"]],
        "is_active": True,
        "is_superuser": False,
    }
    await create_user_db(user_user_data, db)
    print(f"Created testuser with password: {user_password}")

    print("Default users created.")
    print("\nDatabase initialization complete!")

    # Đóng kết nối MongoDB
    await close_mongo()

if __name__ == "__main__":
    asyncio.run(initialize_db_data())
