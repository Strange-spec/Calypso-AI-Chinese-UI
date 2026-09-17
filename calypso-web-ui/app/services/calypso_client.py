"""Calypso AI 核心 API 客户端 (HTTPX 异步适配器).

封装与 Calypso AI 原生后端 / 私有化部署平台的异步通信，
包含认证鉴权、超时控制与中文友好异常处理。
"""

import logging
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)


class CalypsoClientError(Exception):
    """Calypso 客户端基础异常。"""
    pass


class CalypsoConnectionError(CalypsoClientError):
    """Calypso 服务网络连接异常。"""
    pass


class CalypsoTimeoutError(CalypsoClientError):
    """Calypso API 调用超时异常。"""
    pass


class CalypsoAPIError(CalypsoClientError):
    """Calypso API 返回 HTTP 业务错误状态。"""

    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class CalypsoClient:
    """基于 HTTPX 的 Calypso AI 异步适配器客户端。"""

    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """初始化 CalypsoClient。

        :param base_url: Calypso 服务 API 基础路径，如 https://us1.calypsoai.app
        :param token: API Bearer Token
        :param timeout: 请求超时时间（秒），默认 30.0
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
        )

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
    ) -> Any:
        """统一底层异步 HTTP 请求封装，负责错误转换。"""
        try:
            response = await self._client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json,
            )
            response.raise_for_status()
            if response.status_code == 204:
                return {}
            return response.json()
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            msg = f"无法连接到 Calypso API 服务 ({self.base_url})：网络不可达或目标服务未启动。"
            logger.error(f"{msg} 详情: {exc}")
            raise CalypsoConnectionError(msg) from exc
        except httpx.TimeoutException as exc:
            msg = f"Calypso API 请求超时（超过 {self.timeout} 秒）：远程服务未在预期时间内响应。"
            logger.error(f"{msg} 详情: {exc}")
            raise CalypsoTimeoutError(msg) from exc
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            try:
                error_body = exc.response.json()
            except Exception:
                error_body = exc.response.text

            msg = f"Calypso API 返回错误状态 [HTTP {status_code}]：{error_body}"
            logger.error(msg)
            raise CalypsoAPIError(msg, status_code=status_code, response_data=error_body) from exc
        except httpx.RequestError as exc:
            msg = f"Calypso API 请求通信失败：{str(exc)}"
            logger.error(msg)
            raise CalypsoClientError(msg) from exc

    async def test_connection(self) -> Dict[str, Any]:
        """测试与 Calypso API 服务的连通性。"""
        try:
            return await self._request("GET", "/backend/v1/projects")
        except CalypsoAPIError as exc:
            # 部分私有化部署环境尝试探测 /backend/v1/env
            if exc.status_code in (401, 403, 404):
                try:
                    return await self._request("GET", "/backend/v1/env")
                except Exception:
                    raise exc
            raise exc

    async def list_projects(self) -> List[Dict[str, Any]]:
        """获取所有项目列表。"""
        res = await self._request("GET", "/backend/v1/projects")
        if isinstance(res, list):
            return res
        if isinstance(res, dict):
            if "projects" in res and isinstance(res["projects"], list):
                return res["projects"]
            if "data" in res and isinstance(res["data"], list):
                return res["data"]
        return [res] if res else []

    async def get_project(self, project_id: str) -> Dict[str, Any]:
        """获取指定项目详细信息与关联配置。"""
        return await self._request("GET", f"/backend/v1/projects/{project_id}")

    async def create_project(
        self,
        name: str,
        description: str = "",
        project_type: str = "app",
        scanners: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """在 Calypso 原生集群中创建新项目并绑定规则。"""
        payload: Dict[str, Any] = {
            "name": name,
            "type": project_type,
            "description": description,
            "config": {
                "scanners": scanners or [],
                "providers": [],
            },
        }
        return await self._request("POST", "/backend/v1/projects", json=payload)

    async def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        project_type: Optional[str] = None,
        scanners: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """更新指定项目的规则配置或基本信息。"""
        try:
            existing = await self.get_project(project_id)
        except Exception:
            existing = {}
        config = existing.get("config", {}) if isinstance(existing, dict) else {}
        if scanners is not None:
            config["scanners"] = scanners

        payload: Dict[str, Any] = {
            "name": name or (existing.get("name") if isinstance(existing, dict) else "Project"),
            "config": config,
        }
        if description is not None:
            payload["description"] = description
        if project_type is not None:
            payload["type"] = project_type

        return await self._request("PUT", f"/backend/v1/projects/{project_id}", json=payload)

    async def delete_project(self, project_id: str) -> Dict[str, Any]:
        """删除指定项目。"""
        return await self._request("DELETE", f"/backend/v1/projects/{project_id}")

    async def list_all_scanners(self) -> List[Dict[str, Any]]:
        """获取系统级所有可用扫描器规则库（内置及自定义）。"""
        res = await self._request("GET", "/backend/v1/scanners")
        if isinstance(res, dict) and "scanners" in res:
            return res["scanners"]
        if isinstance(res, list):
            return res
        return []

    async def create_scanner(
        self,
        name: str,
        direction: str = "both",
        input_data: str = "",
        scanner_type: str = "custom",
    ) -> Dict[str, Any]:
        """在 Calypso 原生集群中新建自定义安全扫描规则。"""
        payload = {
            "name": name,
            "direction": direction,
            "config": {
                "type": scanner_type,
                "input": input_data,
                "scanContext": "directional",
            },
        }
        return await self._request("POST", "/backend/v1/scanners", json=payload)

    async def list_scanners(self, project_id: str) -> List[Dict[str, Any]]:
        """获取指定项目关联的安全扫描器配置列表。"""
        res = await self._request("GET", f"/backend/v1/projects/{project_id}/scanners")
        if isinstance(res, list):
            return res
        if isinstance(res, dict):
            if "scanners" in res and isinstance(res["scanners"], list):
                return res["scanners"]
            if "data" in res and isinstance(res["data"], list):
                return res["data"]
        return [res] if res else []

    async def scan_prompt(self, prompt: str, project_id: Optional[str] = None) -> Dict[str, Any]:
        """调用 Calypso 原生提示词护栏与网关路由接口对输入进行安全评估与 LLM 交互。"""
        # Calypso SaaS 原生护栏与模型路由入口为 /backend/v1/prompts
        # 入参为 {"input": prompt, "project": project_id}
        payload: Dict[str, Any] = {"input": prompt}
        if project_id:
            payload["project"] = project_id
            payload["projectId"] = project_id

        try:
            return await self._request("POST", "/backend/v1/prompts", json=payload)
        except CalypsoAPIError as exc:
            if exc.status_code in (404, 405):
                # 兼容旧版本扫描接口
                return await self._request("POST", "/backend/v1/scans", json={"input": prompt})
            raise exc

    async def query_metrics(self, requests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """调用 Calypso 原生指标与度量聚合接口 POST /backend/v1/metrics。"""
        return await self._request("POST", "/backend/v1/metrics", json={"requests": requests})

    async def get_prompts(
        self,
        project_id: Optional[str] = None,
        outcomes: Optional[List[str]] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """查询历史提示词扫描审计记录。"""
        # Calypso upstream API 严格限制单次查询 limit <= 100
        safe_limit = min(max(1, limit), 100) if limit else 100
        params: Dict[str, Any] = {"limit": safe_limit}
        if project_id:
            params["projectId"] = project_id
            params["project_id"] = project_id
        if outcomes:
            params["outcomes"] = ",".join(outcomes) if isinstance(outcomes, (list, tuple)) else str(outcomes)
        if after:
            params["after"] = after
        if before:
            params["before"] = before
        return await self._request("GET", "/backend/v1/prompts", params=params)

    async def get_audit_events(self, limit: int = 50) -> Dict[str, Any]:
        """获取系统操作安全合规与审计事件。"""
        safe_limit = min(max(1, limit), 100) if limit else 50
        return await self._request("GET", "/backend/v1/audit", params={"limit": safe_limit})

    async def list_campaigns(self) -> Dict[str, Any]:
        """获取红队测试活动（Campaigns）列表。"""
        return await self._request("GET", "/backend/v1/campaigns")

    async def list_campaign_runs(self, campaign_id: Optional[str] = None) -> Dict[str, Any]:
        """获取红队测试任务执行记录（Campaign Runs）列表。"""
        params = {}
        if campaign_id:
            params["campaign_id"] = campaign_id
        return await self._request("GET", "/backend/v1/campaign-runs", params=params if params else None)

    async def get_campaign_run(self, run_id: str) -> Dict[str, Any]:
        """获取单个红队测试执行详情及 Raw Data。"""
        return await self._request("GET", f"/backend/v1/campaign-runs/{run_id}")

    async def close(self) -> None:
        """关闭底层 HTTP 连接池。"""
        await self._client.aclose()

    async def __aenter__(self) -> "CalypsoClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
