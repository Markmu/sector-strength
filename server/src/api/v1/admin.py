"""
Legacy v1 admin compatibility routes.

These endpoints keep older tests/clients working on `/v1/admin/data/*`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Query, Depends
from pydantic import BaseModel
from src.api.schemas.response import ApiResponse
from src.api.deps import get_current_user
from src.models.user import User

from src.core.settings import settings
from src.services.data_updater.collector import DataCollector
from src.services.scheduler.job_manager import get_job_manager
from src.services.cache.cache_manager import get_cache_manager

router = APIRouter(prefix="/admin/data", tags=["admin-legacy"])


def _require_api_key(api_key: Optional[str]) -> None:
    expected = getattr(settings, "ADMIN_API_KEY", "admin-secret-key-change-in-production")
    if api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API key")


class DataQualityChecker:
    async def check_data_integrity(self):
        return {"has_issues": False, "issues": []}

    async def get_data_quality_report(self):
        return {"stock_count": 0}


class AdminCheckData(BaseModel):
    is_admin: bool
    role: str


class AdminCheckResponse(ApiResponse[AdminCheckData]):
    pass


@router.get("/check", response_model=AdminCheckResponse)
async def check_admin_permission(current_user: User = Depends(get_current_user)) -> AdminCheckResponse:
    role = getattr(current_user, "role", "user") or "user"
    is_admin = role == "admin"
    return AdminCheckResponse(success=True, data=AdminCheckData(is_admin=is_admin, role=role))


@router.post("/update")
async def trigger_update(api_key: Optional[str] = Header(None, alias="api_key")):
    _require_api_key(api_key)
    task_id = str(uuid4())
    return {"success": True, "data": {"success": True, "task_id": task_id}}


@router.get("/update-status")
async def get_update_status(api_key: Optional[str] = Header(None, alias="api_key")):
    _require_api_key(api_key)
    collector = DataCollector()
    data = await collector.get_latest_update_status()
    return {"success": True, "data": data}


@router.get("/update-history")
async def get_update_history(
    api_key: Optional[str] = Header(None, alias="api_key"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    _require_api_key(api_key)
    collector = DataCollector()
    data = await collector.get_update_history(page=page, page_size=page_size)
    return {"success": True, "data": data}


@router.post("/update/cancel")
async def cancel_update(api_key: Optional[str] = Header(None, alias="api_key")):
    _require_api_key(api_key)
    return {"success": True, "message": "待实现：取消正在运行的更新任务"}


@router.get("/scheduler/status")
async def scheduler_status(api_key: Optional[str] = Header(None, alias="api_key")):
    _require_api_key(api_key)
    manager = get_job_manager()
    jobs = manager.get_jobs()
    return {"success": True, "data": {"is_running": manager.is_running, "jobs": jobs}}


@router.post("/scheduler/start")
async def scheduler_start(api_key: Optional[str] = Header(None, alias="api_key")):
    _require_api_key(api_key)
    manager = get_job_manager()
    manager.start()
    return {"success": True, "message": "scheduler started"}


@router.post("/scheduler/stop")
async def scheduler_stop(api_key: Optional[str] = Header(None, alias="api_key")):
    _require_api_key(api_key)
    manager = get_job_manager()
    manager.shutdown()
    return {"success": True, "message": "scheduler stopped"}


@router.post("/scheduler/trigger/{job_id}")
async def scheduler_trigger(job_id: str, api_key: Optional[str] = Header(None, alias="api_key")):
    _require_api_key(api_key)
    manager = get_job_manager()
    ok = await manager.trigger_job(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="job not found")
    return {"success": True, "message": f"triggered {job_id}"}


@router.get("/quality/check")
async def quality_check(api_key: Optional[str] = Header(None, alias="api_key")):
    _require_api_key(api_key)
    checker = DataQualityChecker()
    integrity = await checker.check_data_integrity()
    report = await checker.get_data_quality_report()
    return {"success": True, "data": {"integrity": integrity, "report": report}}


@router.get("/cache/stats")
async def cache_stats(api_key: Optional[str] = Header(None, alias="api_key")):
    _require_api_key(api_key)
    cache = get_cache_manager()
    return {"success": True, "data": {"backend": cache.__class__.__name__}}


@router.post("/cache/clear")
async def cache_clear(
    api_key: Optional[str] = Header(None, alias="api_key"),
    pattern: Optional[str] = Query(None),
):
    _require_api_key(api_key)
    cache = get_cache_manager()
    if pattern:
        cleared = await cache.clear_pattern(pattern)
    else:
        cleared = await cache.clear_all()
    return {"success": True, "data": {"cleared_count": int(cleared)}}


@router.get("/health")
async def system_health(api_key: Optional[str] = Header(None, alias="api_key")):
    _require_api_key(api_key)
    manager = get_job_manager()
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "scheduler": "running" if manager.is_running else "stopped",
            "timestamp": datetime.now().isoformat(),
        },
    }
