"""Calypso 安全审计与事件日志 API 路由。"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request

from app.config import settings, get_effective_token
from app.services.mock_data import mock_engine
from app.services.calypso_client import CalypsoClient, CalypsoClientError

router = APIRouter(prefix="/audit", tags=["Audit"])


def _generate_demo_audit_logs() -> List[Dict[str, Any]]:
    """生成离线演示模式下的高质量安全审计事件日志。"""
    presets = mock_engine.get_presets()
    base_time = datetime.now(timezone.utc)
    logs = []

    # 循环结合预设用例生成多样化审计日志
    for i in range(40):
        preset = presets[i % len(presets)]
        event_time = (base_time - timedelta(minutes=i * 18 + 5)).isoformat()
        outcome = preset["expected_action"]
        risk_level = "high" if outcome == "blocked" else ("medium" if outcome == "redacted" else "low")

        scanner_name = preset.get("category", "guardrail")
        scanners = []
        if outcome != "cleared":
            scanners.append({
                "name": scanner_name,
                "title": preset["name"],
                "action": outcome,
                "score": 0.95 if outcome == "blocked" else 0.88,
            })

        logs.append({
            "id": f"log_sec_{1000 + i}",
            "timestamp": event_time,
            "project_id": settings.default_project_id or "proj_default_china",
            "prompt": preset["prompt"],
            "redacted_prompt": preset["prompt"] if outcome != "redacted" else "客户个人信息及卡号 [已脱敏处理]",
            "outcome": outcome,
            "risk_level": risk_level,
            "category": preset.get("category"),
            "client_ip": f"192.168.1.{10 + (i % 30)}",
            "triggered_scanners": scanners,
        })
    return logs


@router.get("/logs")
async def get_audit_logs(
    request: Request,
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    outcome: Optional[str] = Query(None, description="按判定结果筛选: blocked, cleared, redacted, flagged"),
    project_id: Optional[str] = Query(None, description="按项目 ID 筛选"),
) -> Dict[str, Any]:
    """获取系统安全防护与审计事件日志列表，支持分页与条件筛选。"""
    if settings.app_mode == "demo":
        all_logs = _generate_demo_audit_logs()
        if outcome:
            outcome_norm = outcome.strip().lower()
            all_logs = [log for log in all_logs if log.get("outcome") == outcome_norm]
        if project_id:
            all_logs = [log for log in all_logs if log.get("project_id") == project_id]

        total = len(all_logs)
        start = (page - 1) * page_size
        end = start + page_size
        paged_items = all_logs[start:end]

        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "items": paged_items,
        }

    # 在线模式调用 Calypso 原生 Prompts 接口
    client = CalypsoClient(base_url=settings.calypso_base_url, token=get_effective_token(request))
    try:
        outcomes_list = [outcome] if outcome else None
        res = await client.get_prompts(
            project_id=project_id or settings.default_project_id,
            outcomes=outcomes_list,
            limit=min(page_size * page, 100),
        )
        items = []
        if isinstance(res, list):
            items = res
        elif isinstance(res, dict):
            items = res.get("prompts") or res.get("data") or res.get("items") or []

        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        paged_items = items[start:end]
        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "items": paged_items,
        }
    except CalypsoClientError as exc:
        raise HTTPException(status_code=502, detail=f"拉取 Calypso 审计日志失败: {str(exc)}")
    finally:
        await client.close()
