"""Calypso 安全运营大盘度量 API 路由。"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, Request

from app.config import settings, get_effective_token
from app.services.mock_data import mock_engine
from app.services.calypso_client import CalypsoClient, CalypsoClientError
from app.services.metrics_aggregator import MetricsAggregator

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/metrics")
async def get_dashboard_metrics(
    request: Request,
    timeframe: str = Query("24h", description="统计时间范围，可选 24h, 7d, 30d"),
    project_id: Optional[str] = Query(None, description="按项目筛选度量指标"),
) -> Dict[str, Any]:
    """获取大盘安全态势指标、扫描器拦截分布与趋势数据。"""
    if settings.app_mode == "demo":
        return mock_engine.get_metrics(timeframe=timeframe)

    client = CalypsoClient(base_url=settings.calypso_base_url, token=get_effective_token(request))
    try:
        resolved_project = project_id or settings.default_project_id
        res = await client.get_prompts(project_id=resolved_project, limit=100)
        prompts = []
        if isinstance(res, list):
            prompts = res
        elif isinstance(res, dict):
            prompts = res.get("prompts") or res.get("data") or res.get("items") or []

        aggregated = MetricsAggregator.aggregate(prompts, timeframe=timeframe)
        # 为前端趋势图提供基本数据点结构
        aggregated["trends"] = mock_engine.get_metrics(timeframe=timeframe).get("trends", [])
        return aggregated
    except CalypsoClientError as exc:
        raise HTTPException(status_code=502, detail=f"无法从 Calypso 服务拉取度量数据: {str(exc)}")
    finally:
        await client.close()
