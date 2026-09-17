"""Calypso 系统状态与配置管理 API 路由。"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.services.calypso_client import CalypsoClient, CalypsoClientError

router = APIRouter(prefix="/system", tags=["System"])


class ConfigUpdateRequest(BaseModel):
    """系统运行时配置更新请求模型。"""
    base_url: Optional[str] = Field(None, description="Calypso 服务 API 地址")
    token: Optional[str] = Field(None, description="Calypso API 认证 Token")
    project_id: Optional[str] = Field(None, description="默认关联项目 ID")
    mode: Optional[str] = Field(None, description="系统运行模式: demo 或 online")
    test_connection: Optional[bool] = Field(False, description="更新后是否立即触发连通性测试")


class ConnectionTestRequest(BaseModel):
    """网络连通性测试请求模型。"""
    base_url: Optional[str] = Field(None, description="测试的目标 API 地址")
    token: Optional[str] = Field(None, description="测试的认证 Token")


@router.get("/status")
async def get_system_status() -> Dict[str, Any]:
    """获取当前系统状态、运行模式与配置概要。"""
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "version": settings.version,
        "mode": settings.app_mode,
        "base_url": settings.calypso_base_url,
        "has_token": bool(settings.calypso_api_token),
        "project_id": settings.default_project_id,
    }


@router.post("/config")
async def update_system_config(req: ConfigUpdateRequest) -> Dict[str, Any]:
    """更新内存中的系统配置，并可选触发连通性测试。"""
    if req.base_url is not None:
        settings.calypso_base_url = req.base_url.strip()
    if req.token is not None:
        settings.calypso_api_token = req.token.strip() if req.token.strip() else None
    if req.project_id is not None:
        settings.default_project_id = req.project_id.strip() if req.project_id.strip() else None
    if req.mode is not None:
        mode_val = req.mode.strip().lower()
        if mode_val in ("demo", "online"):
            settings.app_mode = mode_val
        else:
            raise HTTPException(status_code=400, detail="无效的运行模式，仅支持 'demo' 或 'online'")

    conn_result: Optional[Dict[str, Any]] = None
    if req.test_connection:
        if settings.app_mode == "demo":
            conn_result = {
                "status": "ok",
                "mode": "demo",
                "message": "Demo 演示模式：模拟服务连接正常",
            }
        else:
            try:
                client = CalypsoClient(base_url=settings.calypso_base_url, token=settings.calypso_api_token)
                test_data = await client.test_connection()
                await client.close()
                conn_result = {
                    "status": "ok",
                    "mode": "online",
                    "message": "已成功连通 Calypso 原生服务",
                    "details": test_data,
                }
            except CalypsoClientError as exc:
                conn_result = {
                    "status": "failed",
                    "mode": "online",
                    "message": str(exc),
                }

    return {
        "status": "ok",
        "message": "系统配置已成功更新",
        "config": {
            "base_url": settings.calypso_base_url,
            "has_token": bool(settings.calypso_api_token),
            "project_id": settings.default_project_id,
            "mode": settings.app_mode,
        },
        "connection_test": conn_result,
    }


@router.post("/test-connection")
async def test_connection(req: Optional[ConnectionTestRequest] = None) -> Dict[str, Any]:
    """测试指定或当前配置的 Calypso API 连通性。"""
    target_url = (req.base_url if req and req.base_url else settings.calypso_base_url) or ""
    target_token = (req.token if req and req.token is not None else settings.calypso_api_token)

    # 若系统处于 demo 模式且未传入外部特定 URL，直接返回模拟成功
    if settings.app_mode == "demo" and (not req or not req.base_url):
        return {
            "status": "ok",
            "mode": "demo",
            "message": "Demo 模式连通性验证正常（虚拟通道就绪）",
        }

    try:
        client = CalypsoClient(base_url=target_url, token=target_token, timeout=10.0)
        res = await client.test_connection()
        await client.close()
        return {
            "status": "ok",
            "mode": "online",
            "message": "服务连通性测试成功",
            "details": res,
        }
    except CalypsoClientError as exc:
        return {
            "status": "failed",
            "mode": "online",
            "message": str(exc),
        }
