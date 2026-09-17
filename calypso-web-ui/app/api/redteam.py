"""Calypso 红队对抗评估与安全报告 API 路由。"""

import os
from typing import Any, Dict, Optional
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.config import settings
from app.services.mock_data import mock_engine
from app.services.calypso_client import CalypsoClient, CalypsoClientError
from app.services.redteam_analyzer import RedTeamAnalyzer

router = APIRouter(prefix="/redteam", tags=["RedTeam"])

# 内存缓存内置样本分析结果，避免重复解析大文件
_cached_sample_analysis: Optional[Dict[str, Any]] = None


class ExportReportRequest(BaseModel):
    """红队分析报告导出请求。"""
    analysis: Dict[str, Any] = Field(..., description="待导出 Markdown 的红队分析结果数据")


@router.get("/campaigns")
async def list_campaigns() -> Dict[str, Any]:
    """获取红队攻防对抗评估活动任务列表。"""
    if settings.app_mode == "demo":
        return mock_engine.get_campaigns()

    client = CalypsoClient(base_url=settings.calypso_base_url, token=settings.calypso_api_token)
    try:
        res = await client.list_campaigns()
        if isinstance(res, list):
            return {"total": len(res), "campaigns": res}
        return res
    except CalypsoClientError as exc:
        raise HTTPException(status_code=502, detail=f"获取 Calypso 红队活动失败: {str(exc)}")
    finally:
        await client.close()


@router.post("/reports/analyze")
async def analyze_redteam_csv(file: UploadFile = File(...)) -> Dict[str, Any]:
    """上传红队评估 CSV 报告并进行结构化统计分析。"""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="请上传有效的 CSV 文件 (.csv)")

    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="上传的文件内容为空")
        analysis = RedTeamAnalyzer.analyze_csv(content)
        return {
            "status": "ok",
            "filename": file.filename,
            "data": analysis,
        }
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"CSV 解析失败: {str(exc)}")


@router.get("/reports/sample")
async def get_sample_report() -> Dict[str, Any]:
    """获取内置宝马红队评估测试集分析结果（开箱即用演示）。"""
    global _cached_sample_analysis
    if _cached_sample_analysis is not None:
        return {
            "status": "ok",
            "source": "BMW test.csv (cached)",
            "data": _cached_sample_analysis,
        }

    # 尝试定位本地真实 BMW test.csv 路径
    possible_paths = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../BMW test.csv")),
        os.path.abspath("BMW test.csv"),
        os.path.abspath("../BMW test.csv"),
    ]

    for p in possible_paths:
        if os.path.isfile(p):
            try:
                with open(p, "rb") as f:
                    content = f.read()
                analysis = RedTeamAnalyzer.analyze_csv(content)
                _cached_sample_analysis = analysis
                return {
                    "status": "ok",
                    "source": "BMW test.csv",
                    "data": analysis,
                }
            except Exception:
                pass

    # 若未找到 CSV 文件，回退至内置宝马测试集数据结构
    fallback = mock_engine.get_campaigns()["campaigns"][0]
    return {
        "status": "ok",
        "source": "mock_data",
        "data": {
            "campaign": fallback["name"],
            "target": fallback["target"],
            "total_tests": fallback["total_tests"],
            "vulnerable_count": fallback["vulnerable_count"],
            "refused_count": fallback["successful_refusals"],
            "api_crash_count": fallback["api_fuzzing_crashes"],
            "vulnerability_rate": fallback["vulnerability_rate"],
            "defense_rate": round(fallback["successful_refusals"] / fallback["total_tests"] * 100, 2),
            "attack_technique_breakdown": fallback["attack_breakdown"],
            "attack_vector_breakdown": [],
            "converter_breakdown": [],
            "severity_distribution": fallback.get("severity_distribution", {}),
        },
    }


@router.post("/reports/export")
async def export_redteam_report(body: Dict[str, Any]) -> Dict[str, Any]:
    """根据分析数据导出中文 Markdown 红队评估报告。"""
    data = body.get("analysis") if "analysis" in body and isinstance(body["analysis"], dict) else body
    if not data:
        raise HTTPException(status_code=400, detail="缺少 analysis 报告分析数据")
    markdown_content = RedTeamAnalyzer.export_markdown(data)
    return {
        "status": "ok",
        "markdown": markdown_content,
    }
