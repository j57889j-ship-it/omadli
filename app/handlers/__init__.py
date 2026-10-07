from .admin_channel import router as admin_channel_router
from .admin_content import router as admin_content_router
from .admin_misc import router as admin_misc_router
from .admin_panel import router as admin_panel_router
from .admin_system import router as admin_system_router
from .admin_users import router as admin_users_router
from .common import router as common_router
from .user_books import router as user_books_router
from .user_navigation import router as user_navigation_router
from .user_quiz import router as user_quiz_router
from .user_start import router as user_start_router

ALL_ROUTERS = [
    common_router,
    user_start_router,
    admin_panel_router,
    admin_content_router,
    admin_users_router,
    admin_channel_router,
    admin_system_router,
    admin_misc_router,
    user_books_router,
    user_quiz_router,
    user_navigation_router,
]
