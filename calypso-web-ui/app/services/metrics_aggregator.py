"""Calypso 指标聚合统计服务 (MetricsAggregator).

负责对安全扫描记录（Prompts）进行多维度统计聚合，
包括放行/拦截/脱敏/告警量、拦截率及扫描器规则命中分布。
"""

from collections import Counter
from typing import Any, Dict, List, Optional


class MetricsAggregator:
    """提示词安全扫描度量统计聚合器。"""

    # 扫描器英文名到中文展示名映射
    SCANNER_TITLES: Dict[str, str] = {
        "prompt_injection": "Prompt 注入防御",
        "jailbreak_classifier": "DAN 越狱分类器",
        "secrets_scanner": "凭证防泄漏",
        "obfuscation_decoder": "混淆还原与检测",
        "pii_scanner": "PII 敏感数据拦截",
        "malicious_code": "恶意代码与载荷防御",
        "toxicity": "内容毒性与侮辱检测",
        "hallucination": "幻觉检测",
    }

    @classmethod
    def aggregate(cls, prompts: List[Dict[str, Any]], timeframe: str = "24h") -> Dict[str, Any]:
        """聚合提示词扫描列表数据。

        :param prompts: 扫描记录列表
        :param timeframe: 统计时间窗口（如 "24h", "7d", "30d"）
        :return: 包含统计汇总与扫描器细分的字典
        """
        total_prompts = len(prompts)
        cleared_prompts = 0
        blocked_prompts = 0
        flagged_prompts = 0
        redacted_prompts = 0

        scanner_counter: Counter = Counter()
        scanner_titles: Dict[str, str] = dict(cls.SCANNER_TITLES)

        for p in prompts:
            # 提取判定结果状态
            outcome = (
                p.get("outcome")
                or (p.get("result", {}).get("outcome") if isinstance(p.get("result"), dict) else None)
                or (p.get("result", {}).get("status") if isinstance(p.get("result"), dict) else None)
                or p.get("status")
                or "cleared"
            )
            outcome = str(outcome).lower()

            if outcome in ("blocked", "block", "deny"):
                blocked_prompts += 1
                # 提取触发的扫描器
                scanners = []
                if "triggered_scanners" in p and isinstance(p["triggered_scanners"], list):
                    scanners = p["triggered_scanners"]
                elif isinstance(p.get("result"), dict) and "scannerResults" in p["result"]:
                    scanners = p["result"]["scannerResults"]
                elif isinstance(p.get("result"), dict) and "triggered_scanners" in p["result"]:
                    scanners = p["result"]["triggered_scanners"]
                elif "scannerResults" in p and isinstance(p["scannerResults"], list):
                    scanners = p["scannerResults"]

                for sc in scanners:
                    if not isinstance(sc, dict):
                        continue
                    action = str(sc.get("action", "blocked")).lower()
                    if action in ("blocked", "block", "deny", "flagged"):
                        sc_name = sc.get("name") or sc.get("scanner") or sc.get("id") or "unknown"
                        sc_title = sc.get("title") or cls.SCANNER_TITLES.get(sc_name, sc_name)
                        scanner_titles[sc_name] = sc_title
                        scanner_counter[sc_name] += 1
            elif outcome in ("cleared", "clear", "allowed", "pass", "passed"):
                cleared_prompts += 1
            elif outcome in ("redacted", "redact", "masked"):
                redacted_prompts += 1
            elif outcome in ("flagged", "flag", "warning"):
                flagged_prompts += 1
            else:
                # 默认归类为放行
                cleared_prompts += 1

        block_rate = round((blocked_prompts / total_prompts * 100), 2) if total_prompts > 0 else 0.0

        blocked_scanners_breakdown = []
        for name, count in scanner_counter.most_common():
            pct = round((count / blocked_prompts * 100), 2) if blocked_prompts > 0 else 0.0
            blocked_scanners_breakdown.append({
                "scanner": name,
                "title": scanner_titles.get(name, name),
                "count": count,
                "percentage": pct,
            })

        summary = {
            "timeframe": timeframe,
            "total_prompts": total_prompts,
            "cleared_prompts": cleared_prompts,
            "blocked_prompts": blocked_prompts,
            "flagged_prompts": flagged_prompts,
            "redacted_prompts": redacted_prompts,
            "block_rate_percentage": block_rate,
        }

        return {
            "timeframe": timeframe,
            "total_prompts": total_prompts,
            "cleared_prompts": cleared_prompts,
            "blocked_prompts": blocked_prompts,
            "flagged_prompts": flagged_prompts,
            "redacted_prompts": redacted_prompts,
            "block_rate_percentage": block_rate,
            "blocked_scanners_breakdown": blocked_scanners_breakdown,
            "summary": summary,
        }
