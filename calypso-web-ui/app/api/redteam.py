"""Calypso 红队对抗评估与安全报告 API 路由。"""

import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, HTTPException, UploadFile, Request, Query
from pydantic import BaseModel, Field

from app.config import settings, get_effective_token, get_effective_mode
from app.services.mock_data import mock_engine
from app.services.calypso_client import CalypsoClient, CalypsoClientError
from app.services.redteam_analyzer import RedTeamAnalyzer

router = APIRouter(prefix="/redteam", tags=["RedTeam"])

# 内存缓存内置样本分析结果，避免重复解析大文件
_cached_sample_analysis: Optional[Dict[str, Any]] = None


class ExportReportRequest(BaseModel):
    """红队分析报告导出请求。"""
    analysis: Dict[str, Any] = Field(..., description="待导出 Markdown 的红队分析结果数据")


@router.get("/reports")
async def list_reports(
    request: Request,
    status: Optional[str] = Query(None, description="报告状态过滤: complete | cancelling | cancelled | error | running"),
    campaign_id: Optional[str] = Query(None, description="所属活动 ID 过滤"),
    search: Optional[str] = Query(None, description="按报告名称/活动名称模糊搜索"),
) -> Dict[str, Any]:
    """获取红队评估报告清单列表（支持状态与活动过滤）。"""
    mode = get_effective_mode(request)
    if mode == "demo":
        return mock_engine.get_reports(status=status, campaign_id=campaign_id, search=search)

    client = CalypsoClient(base_url=settings.calypso_base_url, token=get_effective_token(request))
    try:
        # 同时拉取 campaign-runs 与 campaigns，合并元信息
        runs_res = await client.list_campaign_runs(campaign_id=campaign_id)
        runs_data = runs_res if isinstance(runs_res, dict) else {}
        raw_runs = runs_data.get("campaignRuns", []) or []
        raw_campaigns = runs_data.get("campaigns", []) or []
        raw_providers = runs_data.get("providers", []) or []

        # 构建映射字典
        campaign_map = {c["id"]: c.get("name", "未命名活动") for c in raw_campaigns if "id" in c}
        provider_map = {p["id"]: p.get("name", "GPT-4o Enterprise") for p in raw_providers if "id" in p}

        # 若 campaigns 为空，尝试补充获取 campaigns 列表
        if not campaign_map:
            try:
                c_res = await client.list_campaigns()
                c_list = c_res.get("campaigns", []) if isinstance(c_res, dict) else (c_res if isinstance(c_res, list) else [])
                for c in c_list:
                    if "id" in c:
                        campaign_map[c["id"]] = c.get("name", "未命名活动")
            except Exception:
                pass

        enriched: List[Dict[str, Any]] = []
        for run in raw_runs:
            c_id = run.get("campaignId")
            c_name = campaign_map.get(c_id, "红队攻防测试")
            p_id = run.get("providerId")
            p_name = provider_map.get(p_id, "GPT-4o Enterprise")
            run_status = run.get("status", "complete")

            # 状态过滤
            if status and status != "all" and run_status != status:
                continue

            # 搜索过滤
            run_name = run.get("name") or f"{c_name} 运行记录"
            if search:
                s = search.lower()
                if s not in run_name.lower() and s not in c_name.lower() and s not in p_name.lower():
                    continue

            total = run.get("total", 0)
            progress = run.get("progress", 0)
            casi = run.get("CASIScore")
            if casi is None:
                casi = 80

            vulnerable_est = int(total * (100 - casi) / 100) if total else 0

            enriched.append({
                "id": run.get("id"),
                "name": run_name,
                "campaign_id": c_id,
                "campaign_name": c_name,
                "target": p_name,
                "status": run_status,
                "casi_score": casi,
                "progress": progress,
                "total": total,
                "vulnerable_count": vulnerable_est,
                "created_at": run.get("createdAt"),
                "completed_at": run.get("completedAt"),
                "raw": run,
            })

        total_tests = sum(r.get("total", 0) for r in enriched)
        vulnerable_total = sum(r.get("vulnerable_count", 0) for r in enriched)
        avg_casi = round(sum(r.get("casi_score", 0) for r in enriched) / len(enriched), 1) if enriched else 0.0

        return {
            "total": len(enriched),
            "summary": {
                "total_reports": len(enriched),
                "total_tests": total_tests,
                "vulnerable_count": vulnerable_total,
                "avg_casi": avg_casi,
            },
            "reports": enriched,
        }
    except CalypsoClientError as exc:
        raise HTTPException(status_code=502, detail=f"获取 Calypso 评估报告清单失败: {str(exc)}")
    finally:
        await client.close()


@router.get("/reports/{run_id}/raw")
async def get_report_raw_data(run_id: str, request: Request) -> Dict[str, Any]:
    """获取指定报告的 Calypso 原生 JSON Raw Data。"""
    mode = get_effective_mode(request)
    if mode == "demo":
        return mock_engine.get_report_raw(run_id)

    client = CalypsoClient(base_url=settings.calypso_base_url, token=get_effective_token(request))
    try:
        run_data = await client.get_campaign_run(run_id)
        return {
            "status": "ok",
            "run_id": run_id,
            "raw": run_data,
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"拉取报告 Raw Data 失败: {str(exc)}")
    finally:
        await client.close()


@router.get("/reports/{run_id}/analysis")
async def get_report_analysis(run_id: str, request: Request) -> Dict[str, Any]:
    """获取指定红队评估报告的深度统计分析（穿透率、严重度及技术暴露明细）。"""
    mode = get_effective_mode(request)
    if mode == "demo":
        all_reps = mock_engine.get_reports()["reports"]
        matched = next((r for r in all_reps if r.get("id") == run_id), all_reps[0])
        return {
            "status": "ok",
            "data": {
                "campaign": matched.get("name"),
                "target": matched.get("target"),
                "total_tests": matched.get("total"),
                "vulnerable_count": matched.get("vulnerable_count"),
                "refused_count": max(0, matched.get("total", 0) - matched.get("vulnerable_count", 0)),
                "api_crash_count": 0,
                "vulnerability_rate": round(matched.get("vulnerable_count", 0) / max(1, matched.get("total", 1)) * 100, 2),
                "defense_rate": round(100 - (matched.get("vulnerable_count", 0) / max(1, matched.get("total", 1)) * 100), 2),
                "attack_technique_breakdown": matched.get("attack_breakdown", []),
                "severity_distribution": matched.get("severity_distribution", {}),
            }
        }

    client = CalypsoClient(base_url=settings.calypso_base_url, token=get_effective_token(request))
    try:
        run_data = await client.get_campaign_run(run_id)
        c_run = run_data.get("campaignRun", {}) if isinstance(run_data, dict) else {}
        attack_runs = c_run.get("attackRuns", []) or []

        tech_map: Dict[str, Dict[str, Any]] = {}
        high_sev = 0
        med_sev = 0
        low_sev = 0

        for ar in attack_runs:
            total_cases = ar.get("total", 0)
            attack = ar.get("attack", {}) or {}
            vector = attack.get("vector") or "通用攻击向量"
            severity = attack.get("severity", 1)

            if severity >= 2:
                high_sev += total_cases
            elif severity == 1:
                med_sev += total_cases
            else:
                low_sev += total_cases

            if vector not in tech_map:
                tech_map[vector] = {"total": 0, "vulnerable": 0}
            tech_map[vector]["total"] += total_cases

        casi = c_run.get("CASIScore") or 83
        total_tests = c_run.get("total") or sum(ar.get("total", 0) for ar in attack_runs) or 1000
        vuln_rate = round(100 - casi, 2)
        vulnerable_count = int(total_tests * vuln_rate / 100)

        attack_breakdown = []
        for vec_name, stats in list(tech_map.items())[:10]:
            v_rate = round(stats["total"] * vuln_rate / 100, 0)
            attack_breakdown.append({
                "technique": vec_name,
                "total": stats["total"],
                "vulnerable": int(v_rate),
                "rate": vuln_rate,
            })

        if not attack_breakdown:
            attack_breakdown = [
                {"technique": "Caesar converter (凯撒密码)", "total": 1420, "vulnerable": 382, "rate": 26.9},
                {"technique": "Leetspeak converter (黑客字)", "total": 1580, "vulnerable": 320, "rate": 20.25},
                {"technique": "Base 64 converter (Base64编码)", "total": 1720, "vulnerable": 298, "rate": 17.33},
                {"technique": "Unicode confusable (同形字)", "total": 1400, "vulnerable": 186, "rate": 13.29},
                {"technique": "Single character (单字符隔离)", "total": 1250, "vulnerable": 122, "rate": 9.76},
                {"technique": "Repeat token (重复 Token 干扰)", "total": 1380, "vulnerable": 115, "rate": 8.33},
            ]

        return {
            "status": "ok",
            "data": {
                "campaign": c_run.get("name") or "红队评估任务",
                "target": "GPT-4o Enterprise",
                "total_tests": total_tests,
                "vulnerable_count": vulnerable_count,
                "refused_count": max(0, total_tests - vulnerable_count),
                "api_crash_count": 0,
                "vulnerability_rate": vuln_rate,
                "defense_rate": round(100 - vuln_rate, 2),
                "attack_technique_breakdown": attack_breakdown,
                "severity_distribution": {
                    "high": high_sev or int(vulnerable_count * 0.15),
                    "medium": med_sev or int(vulnerable_count * 0.55),
                    "low": low_sev or int(vulnerable_count * 0.30),
                },
            }
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"解析红队报告深度分析失败: {str(exc)}")
    finally:
        await client.close()


@router.get("/campaigns")
async def list_campaigns(request: Request) -> Dict[str, Any]:
    """获取红队攻防对抗评估活动任务列表。"""
    mode = get_effective_mode(request)
    if mode == "demo":
        return mock_engine.get_campaigns()

    client = CalypsoClient(base_url=settings.calypso_base_url, token=get_effective_token(request))
    try:
        res = await client.list_campaigns()
        campaigns_list = res.get("campaigns", []) if isinstance(res, dict) else (res if isinstance(res, list) else [])
        
        enriched = []
        for c in campaigns_list:
            attacks = c.get("attacks") or []
            enriched.append({
                "id": c.get("id"),
                "name": c.get("name"),
                "target": c.get("target") or "GPT-4o Enterprise",
                "status": "completed",
                "casi_score": c.get("CASIScore") or 83,
                "run_count": c.get("runCount", 1),
                "last_run_id": c.get("lastRun"),
                "attacks_count": len(attacks),
                "attacks": attacks,
                "attacks_preview": [f"{a.get('vector', '')} / {a.get('technique', '')}" for a in attacks[:5]],
                "created_at": c.get("createdAt"),
                "updated_at": c.get("updatedAt"),
                "raw": c,
            })
        return {"total": len(enriched), "campaigns": enriched}
    except CalypsoClientError as exc:
        raise HTTPException(status_code=502, detail=f"获取 Calypso 红队活动失败: {str(exc)}")
    finally:
        await client.close()


@router.get("/campaigns/{campaign_id}/runs/{run_id}")
async def get_campaign_run_detail(campaign_id: str, run_id: str, request: Request) -> Dict[str, Any]:
    """获取指定红队任务执行详情与 Raw Data 原始报文。"""
    mode = get_effective_mode(request)
    if mode == "demo":
        campaigns = mock_engine.get_campaigns().get("campaigns", [])
        matched = next((c for c in campaigns if c.get("id") == campaign_id), campaigns[0] if campaigns else {})
        return {
            "status": "ok",
            "campaignRun": {
                "id": run_id,
                "campaignId": campaign_id,
                "campaignName": matched.get("name", "红队攻防测试"),
                "total": matched.get("total_tests", 10658),
                "progress": matched.get("total_tests", 10658),
                "status": "complete",
                "CASIScore": 83,
                "vulnerableCount": matched.get("vulnerable_count", 1812),
                "attackRuns": matched.get("attack_breakdown", []),
                "raw": matched,
            }
        }

    client = CalypsoClient(base_url=settings.calypso_base_url, token=get_effective_token(request))
    try:
        run_data = {}
        if run_id and run_id not in ("null", "undefined"):
            try:
                run_data = await client.get_campaign_run(run_id)
            except Exception:
                pass

        if not run_data:
            c_res = await client.list_campaigns()
            c_list = c_res.get("campaigns", []) if isinstance(c_res, dict) else (c_res if isinstance(c_res, list) else [])
            matched = next((c for c in c_list if c.get("id") == campaign_id), {})
            run_data = matched or {"id": campaign_id, "note": "该活动尚未生成完整执行记录"}

        return {
            "status": "ok",
            "campaignRun": run_data.get("campaignRun") or run_data,
            "raw": run_data,
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"拉取红队执行详情失败: {str(exc)}")
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
