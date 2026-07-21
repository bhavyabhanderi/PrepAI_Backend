from fastapi import APIRouter, Depends
from typing import Any
from app.models.user import User
from app.auth.dependencies import get_current_admin
from app.schemas.analytics import AdminDashboardStats
from app.services.admin_service import AdminService

router = APIRouter()

@router.get("/dashboard", response_model=AdminDashboardStats)
async def get_dashboard_stats(
    current_admin: User = Depends(get_current_admin)
) -> Any:
    """
    Get aggregated dashboard statistics. Only accessible by Admins.
    """
    stats = await AdminService.get_dashboard_stats()
    return stats
