"""Calypso 多项目空间管理与 Guardrail 规则关联 API 路由。"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import settings, get_effective_token, get_effective_mode
from app.services.mock_data import mock_engine
from app.services.calypso_client import CalypsoClient, CalypsoClientError

router = APIRouter(prefix="/projects", tags=["Projects"])


class CreateProjectRequest(BaseModel):
    name: str = Field(..., description="项目名称")
    type: str = Field("app", description="项目类型: app, chat, agentic, global 等")
    description: Optional[str] = Field("", description="项目用途与描述")
    scanners: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="关联的 Guardrails 规则清单")


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = Field(None, description="项目名称")
    type: Optional[str] = Field(None, description="项目类型")
    description: Optional[str] = Field(None, description="项目用途与描述")
    scanners: Optional[List[Dict[str, Any]]] = Field(None, description="关联的 Guardrails 规则清单")


@router.get("")
async def list_projects(request: Request) -> Dict[str, Any]:
    """获取所有项目空间列表。"""
    if get_effective_mode(request) == "demo":
        projects = mock_engine.list_projects()
        return {"total": len(projects), "projects": projects}


    effective_token = get_effective_token(request)
    client = CalypsoClient(base_url=settings.calypso_base_url, token=effective_token)
    try:
        projects = await client.list_projects()
        return {"total": len(projects), "projects": projects}
    except CalypsoClientError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=f"获取项目列表失败: {exc.message}")
    finally:
        await client.close()


@router.post("")
async def create_project(req: CreateProjectRequest, request: Request) -> Dict[str, Any]:
    """创建新项目空间并绑定指定 Guardrails 规则。"""
    if not req.name or not req.name.strip():
        raise HTTPException(status_code=400, detail="项目名称不能为空")

    if get_effective_mode(request) == "demo":
        created = mock_engine.create_project(
            name=req.name,
            description=req.description or "",
            project_type=req.type,
            scanners=req.scanners,
        )
        return {"status": "ok", "project": created}

    effective_token = get_effective_token(request)
    client = CalypsoClient(base_url=settings.calypso_base_url, token=effective_token)
    try:
        created = await client.create_project(
            name=req.name,
            description=req.description or "",
            project_type=req.type,
            scanners=req.scanners,
        )
        return {"status": "ok", "project": created}
    except CalypsoClientError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=f"创建项目失败: {exc.message}")
    finally:
        await client.close()


@router.get("/{project_id}")
async def get_project(project_id: str, request: Request) -> Dict[str, Any]:
    """获取指定项目详情与关联规则配置。"""
    if get_effective_mode(request) == "demo":
        project = mock_engine.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
        return {"project": project}

    effective_token = get_effective_token(request)
    client = CalypsoClient(base_url=settings.calypso_base_url, token=effective_token)
    try:
        project = await client.get_project(project_id)
        if isinstance(project, dict) and "project" in project:
            project = project["project"]
        return {"project": project}
    except CalypsoClientError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=f"获取项目详情失败: {exc.message}")
    finally:
        await client.close()



@router.put("/{project_id}")
async def update_project(project_id: str, req: UpdateProjectRequest, request: Request) -> Dict[str, Any]:
    """更新指定项目的规则关联与属性。"""
    if get_effective_mode(request) == "demo":
        updated = mock_engine.update_project(
            project_id=project_id,
            name=req.name,
            description=req.description,
            project_type=req.type,
            scanners=req.scanners,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="项目不存在")
        return {"status": "ok", "project": updated}

    effective_token = get_effective_token(request)
    client = CalypsoClient(base_url=settings.calypso_base_url, token=effective_token)
    try:
        updated = await client.update_project(
            project_id=project_id,
            name=req.name,
            description=req.description,
            project_type=req.type,
            scanners=req.scanners,
        )
        return {"status": "ok", "project": updated}
    except CalypsoClientError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=f"更新项目失败: {exc.message}")
    finally:
        await client.close()


@router.delete("/{project_id}")
async def delete_project(project_id: str, request: Request) -> Dict[str, Any]:
    """删除指定项目。"""
    if get_effective_mode(request) == "demo":
        success = mock_engine.delete_project(project_id)
        if not success:
            raise HTTPException(status_code=404, detail="项目不存在")
        return {"status": "ok", "message": "项目已删除"}


    effective_token = get_effective_token(request)
    client = CalypsoClient(base_url=settings.calypso_base_url, token=effective_token)
    try:
        await client.delete_project(project_id)
        return {"status": "ok", "message": "项目已删除"}
    except CalypsoClientError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=f"删除项目失败: {exc.message}")
    finally:
        await client.close()
