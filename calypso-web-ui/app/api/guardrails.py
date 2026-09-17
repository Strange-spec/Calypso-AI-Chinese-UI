"""Calypso 安全护栏与实时扫描 API 路由。"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.config import settings, get_effective_token, get_effective_mode
from app.services.mock_data import mock_engine, RULES_LIBRARY
from app.services.calypso_client import CalypsoClient, CalypsoClientError

router = APIRouter(prefix="/guardrails", tags=["Guardrails"])


class ScanRequest(BaseModel):
    """提示词安全扫描请求体。"""
    prompt: str = Field(..., description="待检测的提示词文本内容")
    project_id: Optional[str] = Field(None, description="安全护栏所属项目 ID")
    policy: Optional[Dict[str, Any]] = Field(None, description="自定义安全策略")


class CreateRuleRequest(BaseModel):
    """创建自定义安全扫描规则请求体。"""
    name: str = Field(..., description="规则名称")
    direction: str = Field("both", description="扫描方向: request, response, both")
    category: str = Field("custom", description="规则分类")
    default_mode: str = Field("block", description="默认动作: block, flag, redact")
    description: Optional[str] = Field("", description="规则说明")
    input_data: Optional[str] = Field("", description="规则关键词或匹配条件")


@router.get("/presets")
async def get_guardrail_presets() -> List[Dict[str, Any]]:
    """获取 G01~G10 预设攻防测试用例。"""
    return mock_engine.get_presets()


@router.get("/rules")
async def get_guardrail_rules(request: Request) -> Dict[str, Any]:
    """获取全量可用 Guardrail 规则库列表（内置核心规则 + 自定义规则）。"""
    mode = get_effective_mode(request)
    if mode == "demo":
        rules = mock_engine.list_rules()
        return {"total": len(rules), "rules": rules}


    effective_token = get_effective_token(request)
    client = CalypsoClient(base_url=settings.calypso_base_url, token=effective_token)
    try:
        # 在线模式整合内置规则与 Calypso 集群动态拉取的自定义规则
        online_scanners = await client.list_all_scanners()
        builtin_rules = [dict(r) for r in RULES_LIBRARY if r.get("is_system")]
        
        # 转换并合并
        seen_ids = {r["id"] for r in builtin_rules}
        custom_rules = []
        for s in online_scanners:
            s_id = s.get("id")
            if s_id not in seen_ids:
                custom_rules.append({
                    "id": s_id,
                    "key": s.get("name", s_id),
                    "name": s.get("name", "自定义规则"),
                    "category": "custom",
                    "direction": s.get("direction", "both"),
                    "default_mode": "block",
                    "description": s.get("config", {}).get("input", "") or "Calypso 远端自定义规则",
                    "is_system": False,
                    "enabled": True,
                })
                seen_ids.add(s_id)
        
        all_rules = builtin_rules + custom_rules
        return {"total": len(all_rules), "rules": all_rules}
    except Exception as exc:
        # 降级返回内置规则
        rules = mock_engine.list_rules()
        return {"total": len(rules), "rules": rules}
    finally:
        await client.close()


@router.post("/rules")
async def create_guardrail_rule(req: CreateRuleRequest, request: Request) -> Dict[str, Any]:
    """创建新的自定义 Guardrail 规则。"""
    if not req.name or not req.name.strip():
        raise HTTPException(status_code=400, detail="规则名称不能为空")

    if get_effective_mode(request) == "demo":
        new_rule = mock_engine.create_rule(
            name=req.name,
            category=req.category,
            direction=req.direction,
            default_mode=req.default_mode,
            description=req.description or "",
            input_data=req.input_data or "",
        )
        return {"status": "ok", "rule": new_rule}

    effective_token = get_effective_token(request)
    client = CalypsoClient(base_url=settings.calypso_base_url, token=effective_token)
    try:
        res = await client.create_scanner(
            name=req.name,
            direction=req.direction,
            input_data=req.input_data or "",
        )
        return {"status": "ok", "rule": res}
    except CalypsoClientError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=f"创建规则失败: {exc.message}")
    finally:
        await client.close()


@router.post("/scan")
async def scan_prompt(req: ScanRequest, request: Request) -> Dict[str, Any]:
    """对输入提示词进行实时安全评估与过滤。

    支持注入、越狱、凭证泄露、编码混淆及 PII 数据脱敏拦截。
    严格基于用户选中的具体业务项目及其绑定的扫描规则执行裁决。
    """
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="提示词内容不能为空")

    mode = get_effective_mode(request)
    # Demo 离线模式：由 MockDataEngine 针对指定项目及其规则进行裁定
    if mode == "demo":
        return mock_engine.scan_prompt(prompt=req.prompt, project_id=req.project_id)

    # Online 在线模式：调用 Calypso 原生接口并严格对齐选中业务项目的安全规则
    effective_token = get_effective_token(request)
    client = CalypsoClient(base_url=settings.calypso_base_url, token=effective_token)
    try:
        resolved_project = req.project_id or settings.default_project_id
        project_name = "在线业务空间"
        project_scanners = []

        # 严格获取目标业务项目的真实配置与绑定规则
        if resolved_project:
            try:
                p_detail = await client.get_project(resolved_project)
                if p_detail and isinstance(p_detail, dict):
                    proj_obj = p_detail.get("project", p_detail)
                    project_name = proj_obj.get("name") or project_name
                    project_scanners = (proj_obj.get("config", {}) or {}).get("scanners", [])
            except Exception:
                pass

        else:
            try:
                projects = await client.list_projects()
                if projects and isinstance(projects, list) and len(projects) > 0:
                    first_p = projects[0]
                    resolved_project = first_p.get("id") or first_p.get("projectId")
                    project_name = first_p.get("name") or project_name
                    project_scanners = first_p.get("config", {}).get("scanners", [])
            except Exception:
                pass

        # 针对目标业务项目执行真实安全扫描
        raw_res = await client.scan_prompt(prompt=req.prompt, project_id=resolved_project)
        now = datetime.now(timezone.utc).isoformat()

        # 规范化 Calypso API 返回结构
        res_data = raw_res.get("result") if isinstance(raw_res.get("result"), dict) else {}
        scanner_results = res_data.get("scannerResults") or []

        # 如果项目配置了规则列表，则根据当前项目启用的规则进行严格对齐与过滤
        enabled_scanner_ids = {s.get("id"): s for s in project_scanners if s.get("enabled", True)}

        triggered = []
        evaluated = []

        for s in scanner_results:
            s_outcome = s.get("outcome") or s.get("status")
            meta = s.get("scannerVersionMeta") or {}
            s_id = s.get("scannerId") or s.get("id")
            s_name = meta.get("name") or s.get("name", "安全规则")

            # 若项目明确指定了生效规则且此规则未在该项目启用，则不纳入该项目的触发判定
            if enabled_scanner_ids and s_id not in enabled_scanner_ids:
                continue

            evaluated.append({
                "id": s_id,
                "name": s_name,
                "outcome": "failed" if s_outcome in ("blocked", "failed") else "passed"
            })

            if s_outcome in ("blocked", "failed", "redacted", "flagged"):
                triggered.append({
                    "id": s_id,
                    "title": s_name,
                    "action": s_outcome,
                    "confidence": s.get("confidence") or 0.95,
                    "reason": meta.get("description") or f"业务项目【{project_name}】防护规则拦截: {s_name}",
                })

        # 提取 Calypso 原生判定动作
        native_outcome = res_data.get("outcome") or raw_res.get("outcome")
        if native_outcome:
            outcome = str(native_outcome).lower()
        elif any(t.get("action") in ("blocked", "failed") for t in triggered):
            outcome = "blocked"
        elif any(t.get("action") in ("redacted", "masked") for t in triggered):
            outcome = "redacted"
        elif any(t.get("action") == "flagged" for t in triggered):
            outcome = "flagged"
        else:
            outcome = "cleared"

        redacted = raw_res.get("redactedInput") or raw_res.get("redacted_prompt") or req.prompt

        # 解析真实 LLM 响应正文与元数据
        llm_resp = res_data.get("response") or res_data.get("providerResult", {}).get("data") or raw_res.get("llm_response")
        model_name = "LLM Model"
        reasoning_content = None
        token_usage = None
        provider_status = res_data.get("providerResult", {}).get("statusCode")

        # 从 response.json 附件深入解析详细大模型 Completion 报文
        for f in res_data.get("files", []):
            if isinstance(f, dict) and (f.get("name") == "response.json" or "json" in f.get("contentType", "")):
                try:
                    f_data = f.get("data")
                    if isinstance(f_data, str):
                        import json
                        parsed_llm = json.loads(f_data)
                        model_name = parsed_llm.get("model") or model_name
                        token_usage = parsed_llm.get("usage")
                        choices = parsed_llm.get("choices") or []
                        if choices and isinstance(choices[0], dict):
                            msg = choices[0].get("message") or {}
                            if not llm_resp:
                                llm_resp = msg.get("content")
                            reasoning_content = msg.get("reasoning_content")
                except Exception:
                    pass

        # 针对阻断与放行场景提供精确报文
        if outcome == "blocked":
            failed_names = [t.get("title") or t.get("id") for t in triggered]
            reason_str = "、".join(failed_names) if failed_names else "高危提示词注入/越狱攻击防护"
            interception_msg = (
                f"【安全护栏网关阻断】\n"
                f"业务项目：{project_name} (ID: {resolved_project})\n"
                f"拦截动作：网关直接丢弃 (Drop Request)\n"
                f"触发规则：命中 {len(triggered)} 项安全策略（{reason_str}）\n"
                f"处理说明：依据当前业务项目的安全合规基线，该请求已被拦截阻断，未透传至后端大语言模型。"
            )
            if not llm_resp:
                llm_resp = interception_msg
        elif not llm_resp:
            if outcome == "cleared":
                llm_resp = f"【{project_name}】业务安全网关审核通过，已安全转发至模型响应。"
            elif outcome == "redacted":
                llm_resp = f"【{project_name}】业务安全网关已脱敏敏感数据并转发至模型。"

        # 确保 raw 报文包含目标业务项目归属信息，以便抽屉展示
        raw_res["projectId"] = resolved_project
        raw_res["projectName"] = project_name

        result_payload = {
            "outcome": outcome,
            "prompt": req.prompt,
            "redacted_prompt": redacted,
            "project_id": resolved_project,
            "project_name": project_name,
            "timestamp": now,
            "triggered_scanners": triggered,
            "evaluated_scanners": evaluated,
            "llm_response": llm_resp,
            "model_name": model_name,
            "reasoning_content": reasoning_content,
            "token_usage": token_usage,
            "provider_status": provider_status,
            "raw": raw_res,
        }

        # 写入实时审计记录供日志流检索
        mock_engine.audit_logs.insert(0, {
            "id": raw_res.get("id") or f"scan_{int(datetime.now().timestamp()*1000)}",
            "projectId": resolved_project,
            "projectName": project_name,
            "input": req.prompt,
            "redactedInput": redacted,
            "outcome": outcome,
            "receivedAt": now,
            "result": res_data,
            "triggeredScanners": [t.get("title") or t.get("name") for t in triggered],
        })

        return result_payload
    except CalypsoClientError as exc:
        raise HTTPException(status_code=502, detail=f"Calypso 扫描接口通信失败: {str(exc)}")
    finally:
        await client.close()


@router.get("/logs")
async def get_guardrail_logs(
    request: Request,
    limit: int = Query(50, ge=1, le=100, description="单页条数，最大100"),
    project_id: Optional[str] = Query(None, description="按项目 ID 筛选"),
    outcomes: Optional[str] = Query(None, description="判定动作过滤，多个逗号分隔"),
) -> Dict[str, Any]:
    """查询 Calypso Guardrails 检测与扫描审计流水日志。"""
    outcomes_list = [o.strip() for o in outcomes.split(",")] if outcomes else None
    mode = get_effective_mode(request)

    if mode == "demo":
        logs = mock_engine.get_audit_logs(limit=limit, project_id=project_id, outcomes=outcomes_list)
        return {"total": len(logs), "logs": logs}

    effective_token = get_effective_token(request)
    client = CalypsoClient(base_url=settings.calypso_base_url, token=effective_token)
    try:
        # 获取已知项目信息以补全项目名称
        project_map = {}
        try:
            projs = await client.list_projects()
            for p in projs:
                p_id = p.get("id") or p.get("projectId")
                if p_id:
                    project_map[p_id] = p.get("name", p_id)
        except Exception:
            pass

        res = await client.get_prompts(project_id=project_id, outcomes=outcomes_list, limit=limit)
        prompts = res.get("prompts", []) if isinstance(res, dict) else (res if isinstance(res, list) else [])

        # 格式化流水记录
        logs = []
        for p in prompts:
            p_result = p.get("result") or {}
            p_outcome = p_result.get("outcome") or p.get("outcome") or "cleared"
            p_pid = p.get("projectId") or p.get("project_id") or "019f273c-1a5a-705a-9638-2798dbf3eb1e"

            # 若指定了 project_id 过滤且不匹配，跳过
            if project_id and p_pid != project_id:
                continue

            scanner_results = p_result.get("scannerResults") or []
            triggered_names = []
            for sr in scanner_results:
                if sr.get("outcome") in ("failed", "blocked", "flagged"):
                    meta = sr.get("scannerVersionMeta") or {}
                    triggered_names.append(meta.get("name") or sr.get("scannerId"))

            logs.append({
                "id": p.get("id"),
                "projectId": p_pid,
                "projectName": project_map.get(p_pid) or p_pid[:8],
                "input": p.get("input", ""),
                "redactedInput": p.get("redactedInput") or p.get("input", ""),
                "outcome": p_outcome,
                "receivedAt": p.get("receivedAt") or p.get("createdAt"),
                "result": p_result,
                "triggeredScanners": triggered_names,
            })

        # 同时合并内存中刚刚在目标业务项目下执行的扫描测试日志
        local_logs = mock_engine.get_audit_logs(limit=limit, project_id=project_id, outcomes=outcomes_list)
        seen_ids = {l["id"] for l in logs}
        for ll in local_logs:
            if ll["id"] not in seen_ids:
                logs.append(ll)
                seen_ids.add(ll["id"])

        logs.sort(key=lambda x: x.get("receivedAt", ""), reverse=True)
        return {"total": len(logs[:limit]), "logs": logs[:limit]}
    except CalypsoClientError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=f"获取检测日志失败: {exc.message}")
    finally:
        await client.close()

