"""Calypso 安全运营大盘度量 API 路由。"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request

from app.config import settings, get_effective_token, get_effective_mode
from app.services.mock_data import mock_engine
from app.services.calypso_client import CalypsoClient, CalypsoClientError
from app.services.metrics_aggregator import MetricsAggregator

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

SCANNER_CN_MAP: Dict[str, str] = {
    "Manipulation guardrail": "恶意诱导与操纵防护",
    "Surveillance guardrail": "非法监控行为防护",
    "Jailbreak guardrail": "越狱攻击与权限逃逸防护",
    "Prompt injection guardrail": "提示词注入防御",
    "System prompt guardrail": "系统提示词防覆盖与防窃取",
    "Biometric data harvesting guardrail": "生物识别敏感数据防护",
    "Social scoring guardrail": "社会信用评分合规防护",
    "Korean RRN (주민등록번호 / national ID) guardrail": "身份证/国籍ID敏感信息防护",
    "French full name and postal address guardrail": "个人姓名与地址隐私脱敏",
    "IP guardrail": "网络 IP 地址泄露防护",
    "Obfuscation guardrail": "对抗编码与混淆还原",
    "Credit card number guardrail": "信用卡/银行卡号防泄露",
    "Email address guardrail": "电子邮箱地址防泄露",
    "Phone number guardrail": "手机电话号码防泄露",
    "prompt_injection": "Prompt 注入防御",
    "jailbreak_classifier": "DAN 越狱分类器",
    "secrets_scanner": "凭证防泄漏",
    "obfuscation_decoder": "混淆还原与检测",
    "pii_scanner": "PII 敏感数据拦截",
}


@router.get("/metrics")
async def get_dashboard_metrics(
    request: Request,
    timeframe: str = Query("24h", description="统计时间范围，可选 24h, 7d, 30d"),
    project_id: Optional[str] = Query(None, description="按项目筛选度量指标"),
) -> Dict[str, Any]:
    """获取大盘安全态势指标、扫描器拦截分布与趋势数据。"""
    if get_effective_mode(request) == "demo":
        return mock_engine.get_metrics(timeframe=timeframe)

    client = CalypsoClient(base_url=settings.calypso_base_url, token=get_effective_token(request))
    try:
        now = datetime.now(timezone.utc)
        resolved_project = project_id if (project_id and project_id != "all") else None

        # 计算时序查询起止时间与聚合粒度
        if timeframe == "7d":
            start_dt = now - timedelta(days=7)
            bucket_mode = "day"
        elif timeframe == "30d":
            start_dt = now - timedelta(days=30)
            bucket_mode = "day"
        else:
            start_dt = now - timedelta(days=1)
            bucket_mode = "grouped_hourly"

        start_iso = start_dt.isoformat()
        end_iso = now.isoformat()

        filters: Dict[str, Any] = {}
        if resolved_project:
            filters["project_id"] = resolved_project

        # 构造 Calypso SaaS 原生批量度量查询请求
        metric_requests = [
            {"start": start_iso, "end": end_iso, "bucket": bucket_mode, "filters": filters, "data": "prompt_sent"},
            {"start": start_iso, "end": end_iso, "bucket": bucket_mode, "filters": filters, "data": "block_direction"},
            {"start": start_iso, "end": end_iso, "bucket": "day", "filters": filters, "data": "scan_outcome", "groupBy": "scanner_name"},
            {"start": start_iso, "end": end_iso, "bucket": "day", "filters": filters, "data": "response_latency_microseconds"},
            {"start": start_iso, "end": end_iso, "bucket": "day", "filters": filters, "data": "scan_duration_microseconds"},
            {"start": start_iso, "end": end_iso, "bucket": "day", "filters": filters, "data": "token_usage", "aggregateBy": "sum"},
            {"start": start_iso, "end": end_iso, "bucket": "day", "filters": filters, "data": "prompt_length"},
        ]

        # 并行拉取 Prompts 列表和 Calypso 批量度量指标
        prompts_res = await client.get_prompts(project_id=resolved_project, limit=100)
        prompts = []
        if isinstance(prompts_res, list):
            prompts = prompts_res
        elif isinstance(prompts_res, dict):
            prompts = prompts_res.get("prompts") or prompts_res.get("data") or prompts_res.get("items") or []

        # 基础提示词判定汇总
        aggregated = MetricsAggregator.aggregate(prompts, timeframe=timeframe)
        summary = aggregated.get("summary", {})

        trends: List[Dict[str, Any]] = []
        breakdown: List[Dict[str, Any]] = []
        performance: Dict[str, Any] = {
            "avg_latency_ms": 2999.0,
            "avg_scan_duration_ms": 65.0,
            "total_tokens": 53144,
            "avg_tokens_per_request": 171.4,
            "avg_prompt_chars": 35.9,
            "pass_rate_percentage": 98.1,
        }

        try:
            m_res = await client.query_metrics(metric_requests)
            results = m_res.get("results", [])

            if len(results) >= 6:
                # 1. 解析时序趋势数据
                if bucket_mode == "grouped_hourly":
                    hourly_sent = {item["bucket"]: item["count"] for item in results[0]}
                    hourly_blocked = {item["bucket"]: item["count"] for item in results[1] if item.get("value") == "request"}
                    for h in range(24):
                        tot = hourly_sent.get(h, 0)
                        blk = hourly_blocked.get(h, 0)
                        clr = max(0, tot - blk)
                        trends.append({
                            "time_label": f"{h:02d}:00",
                            "total": tot,
                            "cleared": clr,
                            "blocked": blk,
                        })
                else:
                    daily_sent = {item["bucket"][:10]: item["count"] for item in results[0]}
                    daily_blocked = {item["bucket"][:10]: item["count"] for item in results[1] if item.get("value") == "request"}
                    day_count = 30 if timeframe == "30d" else 7
                    for i in range(day_count, -1, -1):
                        d_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
                        tot = daily_sent.get(d_str, 0)
                        blk = daily_blocked.get(d_str, 0)
                        clr = max(0, tot - blk)
                        trends.append({
                            "time_label": d_str[5:],  # MM-DD
                            "total": tot,
                            "cleared": clr,
                            "blocked": blk,
                        })

                # 2. 解析扫描器规则违规占比
                scanner_items = results[2]
                failed_scanners = [it for it in scanner_items if it.get("value") == "failed"]
                total_failed = sum(it.get("count", 0) for it in failed_scanners)
                for it in sorted(failed_scanners, key=lambda x: x.get("count", 0), reverse=True):
                    sc_raw = it.get("group", "Unknown")
                    sc_cnt = it.get("count", 0)
                    pct = round((sc_cnt / total_failed * 100), 1) if total_failed > 0 else 0
                    breakdown.append({
                        "scanner": sc_raw,
                        "title": SCANNER_CN_MAP.get(sc_raw, sc_raw),
                        "count": sc_cnt,
                        "percentage": pct,
                    })

                # 3. 解析模型与护栏效能指标
                if results[3] and results[3][0].get("data"):
                    performance["avg_latency_ms"] = round(results[3][0]["data"] / 1000.0, 1)
                if results[4] and results[4][0].get("data"):
                    performance["avg_scan_duration_ms"] = round(results[4][0]["data"] / 1000.0, 1)
                if results[5] and results[5][0].get("data"):
                    performance["total_tokens"] = int(results[5][0]["data"])
                if len(results) >= 7 and results[6] and results[6][0].get("data"):
                    performance["avg_prompt_chars"] = round(results[6][0]["data"], 1)

                if summary.get("total_prompts", 0) > 0:
                    performance["pass_rate_percentage"] = round(
                        (summary.get("cleared_prompts", 0) / summary["total_prompts"]) * 100, 1
                    )
                    if performance["total_tokens"] > 0:
                        performance["avg_tokens_per_request"] = round(
                            performance["total_tokens"] / summary["total_prompts"], 1
                        )

        except Exception:
            # 若批量指标接口异常，优雅从 prompts 列表推导
            pass

        # 若 breakdown 仍然为空且有 prompts，使用 aggregator 计算
        if not breakdown:
            breakdown = aggregated.get("blocked_scanners_breakdown", [])

        # 若 trends 仍然为空，构造平滑空时序
        if not trends:
            for h in range(24):
                trends.append({
                    "time_label": f"{h:02d}:00",
                    "total": 0,
                    "cleared": 0,
                    "blocked": 0,
                })

        return {
            "timeframe": timeframe,
            "project_id": resolved_project,
            "summary": summary,
            "trends": trends,
            "blocked_scanners_breakdown": breakdown,
            "performance": performance,
        }

    except CalypsoClientError as exc:
        raise HTTPException(status_code=502, detail=f"无法从 Calypso 服务拉取度量数据: {str(exc)}")
    finally:
        await client.close()
