"""Calypso 安全护栏与实时扫描 API 路由。"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.services.mock_data import mock_engine
from app.services.calypso_client import CalypsoClient, CalypsoClientError

router = APIRouter(prefix="/guardrails", tags=["Guardrails"])


class ScanRequest(BaseModel):
    """提示词安全扫描请求体。"""
    prompt: str = Field(..., description="待检测的提示词文本内容")
    project_id: Optional[str] = Field(None, description="安全护栏所属项目 ID")
    policy: Optional[Dict[str, Any]] = Field(None, description="自定义安全策略")


@router.get("/presets")
async def get_guardrail_presets() -> List[Dict[str, Any]]:
    """获取 G01~G10 预设攻防测试用例。"""
    return mock_engine.get_presets()


@router.post("/scan")
async def scan_prompt(req: ScanRequest) -> Dict[str, Any]:
    """对输入提示词进行实时安全评估与过滤。

    支持注入、越狱、凭证泄露、编码混淆及 PII 数据脱敏拦截。
    在 demo 模式下由 MockDataEngine 智能模拟，在 online 模式下调用 CalypsoClient 原生接口。
    """
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="提示词内容不能为空")

    # Demo 离线模式
    if settings.app_mode == "demo":
        project_id = req.project_id or settings.default_project_id or "proj_default_china"
        return mock_engine.scan_prompt(prompt=req.prompt, project_id=project_id)

    # Online 在线模式
    client = CalypsoClient(base_url=settings.calypso_base_url, token=settings.calypso_api_token)
    try:
        resolved_project = req.project_id or settings.default_project_id
        if not resolved_project:
            try:
                projects = await client.list_projects()
                if projects and isinstance(projects, list) and len(projects) > 0:
                    first_p = projects[0]
                    resolved_project = first_p.get("id") or first_p.get("projectId")
            except Exception:
                pass

        raw_res = await client.scan_prompt(prompt=req.prompt, project_id=resolved_project)
        now = datetime.now(timezone.utc).isoformat()

        # 规范化 Calypso API 返回结构
        outcome = (
            raw_res.get("outcome")
            or (raw_res.get("result", {}).get("outcome") if isinstance(raw_res.get("result"), dict) else None)
            or (raw_res.get("result", {}).get("status") if isinstance(raw_res.get("result"), dict) else None)
            or raw_res.get("status")
            or "cleared"
        )
        redacted = raw_res.get("redacted_prompt") or req.prompt
        triggered = []
        if "triggered_scanners" in raw_res:
            triggered = raw_res["triggered_scanners"]
        elif isinstance(raw_res.get("result"), dict) and "scannerResults" in raw_res["result"]:
            triggered = raw_res["result"]["scannerResults"]

        llm_resp = raw_res.get("llm_response")
        if not llm_resp and outcome == "cleared":
            llm_resp = "内容已通过 Calypso 安全审核并由模型正常响应。"

        return {
            "outcome": outcome,
            "prompt": req.prompt,
            "redacted_prompt": redacted,
            "project_id": project_id,
            "timestamp": now,
            "triggered_scanners": triggered,
            "llm_response": llm_resp,
            "raw": raw_res,
        }
    except CalypsoClientError as exc:
        raise HTTPException(status_code=502, detail=f"Calypso 扫描接口通信失败: {str(exc)}")
    finally:
        await client.close()
