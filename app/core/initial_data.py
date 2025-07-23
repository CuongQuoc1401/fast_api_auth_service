# app/core/initial_data.py

# Định nghĩa các vai trò ban đầu cho hệ thống của bạn
INITIAL_ROLES = [
    {"name": "superadmin", "description": "System super administrator with all possible permissions."},
    {"name": "admin", "description": "Administrator with full management access."},
    {"name": "editor", "description": "Content editor for articles and comments."},
    {"name": "user", "description": "User who can only view content."},
    {"name": "viewer", "description": "Viewer."}
]

# Định nghĩa tất cả các quyền hạn (permissions) có thể có trong hệ thống
INITIAL_PERMISSIONS = [
    # Quyền liên quan đến Người dùng (User Management)
    {"name": "user:create", "description": "Allows creating new users."},
    {"name": "user:read_all", "description": "Allows reading all user details."},
    {"name": "user:read_own", "description": "Allows reading own user details."},
    {"name": "user:update_own", "description": "Allows updating own user details."},
    {"name": "user:update_roles", "description": "Allows updating roles of other users."}, # Quyền này dành cho Admin
    {"name": "user:disable", "description": "Allows disabling user accounts."},
    {"name": "user:delete", "description": "Allows deleting user accounts."},

    # Quyền liên quan đến Vai trò (Role Management)
    {"name": "role:create", "description": "Allows creating new roles."},
    {"name": "role:read_all", "description": "Allows reading all role details."},
    {"name": "role:update", "description": "Allows updating existing roles."},
    {"name": "role:delete", "description": "Allows deleting roles."},
    {"name": "role:assign_permission", "description": "Allows assigning individual permissions to a role."},
    {"name": "role:remove_permission", "description": "Allows removing individual permissions from a role."},
    {"name": "role:update_all_permissions", "description": "Allows setting all permissions for a role."}, 

    # Quyền liên quan đến Quyền hạn (Permission Management)
    {"name": "permission:create", "description": "Allows creating new permissions."},
    {"name": "permission:read_all", "description": "Allows reading all permission details."},
    {"name": "permission:update", "description": "Allows updating existing permissions."},
    {"name": "permission:delete", "description": "Allows deleting permissions."},

    # Ví dụ: Quyền liên quan đến Nội dung (Articles & Comments) - Tùy biến theo dự án của bạn
    {"name": "article:create", "description": "Allows creating new articles."},
    {"name": "article:read_all", "description": "Allows reading all articles."},
    {"name": "article:read_own", "description": "Allows reading own articles."},
    {"name": "article:update_own", "description": "Allows updating own articles."},
    {"name": "article:update_any", "description": "Allows updating any article."},
    {"name": "article:delete_own", "description": "Allows deleting own articles."},
    {"name": "article:delete_any", "description": "Allows deleting any article."},

    {"name": "comment:create", "description": "Allows creating new comments."},
    {"name": "comment:read_all", "description": "Allows reading all comments."},
    {"name": "comment:update_own", "description": "Allows updating own comments."},
    {"name": "comment:update_any", "description": "Allows updating any comment."},
    {"name": "comment:delete_own", "description": "Allows deleting own comments."},
    {"name": "comment:delete_any", "description": "Allows deleting any comment."},
]

# Ánh xạ các vai trò tới danh sách các quyền hạn mà chúng sẽ có
# Đây là nơi bạn định nghĩa chính sách RBAC của mình
ROLE_PERMISSIONS_MAP = {
    "superadmin": [p["name"] for p in INITIAL_PERMISSIONS], # Superadmin có TẤT CẢ quyền
    "admin": [
        "user:read_all", "user:update_roles", "user:disable", "user:delete",
        "role:create", "role:read_all", "role:update", "role:delete", 
        "role:assign_permission", "role:remove_permission", "role:update_all_permissions",
        "permission:create", "permission:read_all", "permission:update", "permission:delete",
        "article:read_all", "article:update_any", "article:delete_any",
        "comment:read_all", "comment:delete_any"
    ],
    "editor": [
        "user:read_own", "user:update_own",
        "article:create", "article:read_all", "article:update_own", "article:delete_own",
        "comment:create", "comment:read_all", "comment:update_own", "comment:delete_own"
    ],
    "viewer": [
        "user:read_own",
        "article:read_all",
        "comment:read_all"
    ]
}