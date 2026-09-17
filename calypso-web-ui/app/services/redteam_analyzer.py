"""Calypso 红队对抗评估与 CSV 数据分析服务 (RedTeamAnalyzer).

提供对红队自动化评估报告（如 BMW RedTeam 测试集 CSV）的深度解析、
指标统计、攻击向量/技术细分以及中文 Markdown 安全报告导出。
"""

import io
from typing import Any, Dict, List, Optional, Union
import pandas as pd


class RedTeamAnalyzer:
    """红队 CSV 报告解析与安全评估分析器。"""

    @staticmethod
    def _is_true(val: Any) -> bool:
        """判定值是否为 True（兼容布尔与常见字符串）。"""
        if pd.isna(val):
            return False
        if isinstance(val, bool):
            return val
        s = str(val).strip().lower()
        return s in ("true", "1", "t", "yes", "y")

    @staticmethod
    def _is_error(val: Any) -> bool:
        """判定值是否表示错误/崩溃/超时。"""
        if pd.isna(val):
            return False
        s = str(val).strip()
        if not s or s.lower() in ("nan", "none", "false", "0", "null", "no"):
            return False
        return True

    @classmethod
    def analyze_csv(cls, content: Union[str, bytes]) -> Dict[str, Any]:
        """解析红队测试报告 CSV 内容并生成统计分析指标。

        支持字段：campaign, connection, providerId, attackVector,
                 attackTechnique, severity, converter, prompt, response,
                 vulnerable, refused, error。

        :param content: CSV 文本字符串或二进制字节
        :return: 包含各项关键度量和分组统计的字典
        """
        if isinstance(content, bytes):
            try:
                df = pd.read_csv(io.BytesIO(content))
            except Exception:
                df = pd.read_csv(io.BytesIO(content), encoding="latin1")
        elif isinstance(content, str):
            df = pd.read_csv(io.StringIO(content))
        else:
            raise ValueError("CSV 内容类型错误，仅支持 str 或 bytes")

        df.columns = df.columns.str.strip()
        total_tests = len(df)

        if total_tests == 0:
            return {
                "campaign": "未知活动",
                "target": "",
                "total_tests": 0,
                "vulnerable_count": 0,
                "refused_count": 0,
                "api_crash_count": 0,
                "vulnerability_rate": 0.0,
                "defense_rate": 0.0,
                "attack_vector_breakdown": [],
                "attack_technique_breakdown": [],
                "converter_breakdown": [],
                "severity_distribution": {"high": 0, "medium": 0, "low": 0},
            }

        campaign_name = str(df["campaign"].iloc[0]) if "campaign" in df else "红队安全评估"
        target_name = str(df["connection"].iloc[0]) if "connection" in df else ""

        # 计算布尔标记
        vulnerable_mask = df["vulnerable"].apply(cls._is_true) if "vulnerable" in df else pd.Series([False] * total_tests)
        refused_mask = df["refused"].apply(cls._is_refused if hasattr(cls, "_is_refused") else cls._is_true) if "refused" in df else pd.Series([False] * total_tests)
        error_mask = df["error"].apply(cls._is_error) if "error" in df else pd.Series([False] * total_tests)

        vulnerable_count = int(vulnerable_mask.sum())
        refused_count = int(refused_mask.sum())
        api_crash_count = int(error_mask.sum())

        vulnerability_rate = round((vulnerable_count / total_tests * 100), 2)
        defense_rate = round((refused_count / total_tests * 100), 2)

        df["_is_vulnerable"] = vulnerable_mask
        df["_is_refused"] = refused_mask
        df["_is_error"] = error_mask

        # 按 attackVector 分组统计
        attack_vector_breakdown: List[Dict[str, Any]] = []
        if "attackVector" in df:
            vec_groups = df.groupby("attackVector")
            for vec_name, group in vec_groups:
                g_total = len(group)
                g_vuln = int(group["_is_vulnerable"].sum())
                g_ref = int(group["_is_refused"].sum())
                g_rate = round((g_vuln / g_total * 100), 2) if g_total > 0 else 0.0
                attack_vector_breakdown.append({
                    "vector": str(vec_name),
                    "total": g_total,
                    "vulnerable": g_vuln,
                    "refused": g_ref,
                    "rate": g_rate,
                })
            attack_vector_breakdown.sort(key=lambda x: x["vulnerable"], reverse=True)

        # 按 attackTechnique 分组统计
        attack_technique_breakdown: List[Dict[str, Any]] = []
        if "attackTechnique" in df:
            tech_groups = df.groupby("attackTechnique")
            for tech_name, group in tech_groups:
                g_total = len(group)
                g_vuln = int(group["_is_vulnerable"].sum())
                g_ref = int(group["_is_refused"].sum())
                g_rate = round((g_vuln / g_total * 100), 2) if g_total > 0 else 0.0
                attack_technique_breakdown.append({
                    "technique": str(tech_name),
                    "total": g_total,
                    "vulnerable": g_vuln,
                    "refused": g_ref,
                    "rate": g_rate,
                })
            attack_technique_breakdown.sort(key=lambda x: x["vulnerable"], reverse=True)

        # 按 converter（混淆转换器）分组统计（针对混淆攻击评估）
        converter_breakdown: List[Dict[str, Any]] = []
        if "converter" in df:
            df["converter_clean"] = df["converter"].fillna("No Converter (直连明文)")
            conv_groups = df.groupby("converter_clean")
            for conv_name, group in conv_groups:
                g_total = len(group)
                g_vuln = int(group["_is_vulnerable"].sum())
                g_ref = int(group["_is_refused"].sum())
                g_rate = round((g_vuln / g_total * 100), 2) if g_total > 0 else 0.0
                converter_breakdown.append({
                    "converter": str(conv_name),
                    "total": g_total,
                    "vulnerable": g_vuln,
                    "refused": g_ref,
                    "rate": g_rate,
                })
            converter_breakdown.sort(key=lambda x: x["rate"], reverse=True)

        # 严重度分布
        severity_dist = {"high": 0, "medium": 0, "low": 0}
        if "severity" in df:
            sev_counts = df[df["_is_vulnerable"]]["severity"].value_counts().to_dict()
            for k, v in sev_counts.items():
                k_str = str(k).lower()
                if "1" in k_str or "high" in k_str:
                    severity_dist["high"] += int(v)
                elif "2" in k_str or "med" in k_str:
                    severity_dist["medium"] += int(v)
                else:
                    severity_dist["low"] += int(v)

        return {
            "campaign": campaign_name,
            "target": target_name,
            "total_tests": total_tests,
            "vulnerable_count": vulnerable_count,
            "refused_count": refused_count,
            "api_crash_count": api_crash_count,
            "vulnerability_rate": vulnerability_rate,
            "defense_rate": defense_rate,
            "attack_vector_breakdown": attack_vector_breakdown,
            "attack_technique_breakdown": attack_technique_breakdown,
            "converter_breakdown": converter_breakdown,
            "severity_distribution": severity_dist,
        }

    @classmethod
    def export_markdown(cls, analysis: Dict[str, Any]) -> str:
        """根据分析结果导出中文 Markdown 安全评估报告。

        :param analysis: analyze_csv 返回的结构化字典
        :return: 格式化中文 Markdown 报告文本
        """
        campaign = analysis.get("campaign", "红队对抗评估")
        target = analysis.get("target", "未知目标")
        total = analysis.get("total_tests", 0)
        vuln = analysis.get("vulnerable_count", 0)
        refused = analysis.get("refused_count", 0)
        crash = analysis.get("api_crash_count", 0)
        vuln_rate = analysis.get("vulnerability_rate", 0.0)
        defense_rate = analysis.get("defense_rate", 0.0)

        lines = [
            f"# Calypso AI 红队安全对抗评估报告",
            f"",
            f"**评估活动**: {campaign}  ",
            f"**受测靶标**: {target}  ",
            f"**生成时间**: 自动生成  ",
            f"",
            f"---",
            f"",
            f"## 一、 核心评估度量摘要",
            f"",
            f"| 度量指标 | 统计数值 | 占比 / 评价 |",
            f"| :--- | :--- | :--- |",
            f"| **总对抗测试用例** | {total:,} 次 | 100.0% |",
            f"| **失陷/穿透样本 (Vulnerable)** | <font color='red'>**{vuln:,}**</font> 次 | **{vuln_rate}%** (风险暴露) |",
            f"| **成功防御拒绝 (Refused)** | <font color='green'>**{refused:,}**</font> 次 | {defense_rate}% (安全合规) |",
            f"| **API 异常/超时崩溃 (Crashes)** | <font color='orange'>**{crash:,}**</font> 次 | 系统健壮性待加固 |",
            f"",
        ]

        # 攻击向量表格
        vectors = analysis.get("attack_vector_breakdown", [])
        if vectors:
            lines.extend([
                f"## 二、 攻击向量 (Attack Vectors) 暴露分布",
                f"",
                f"| 攻击向量类别 | 测试总量 | 失陷穿透数 | 防御拦截数 | 穿透失陷率 |",
                f"| :--- | :--- | :--- | :--- | :--- |",
            ])
            for v in vectors:
                lines.append(
                    f"| {v.get('vector')} | {v.get('total'):,} | {v.get('vulnerable'):,} | {v.get('refused'):,} | {v.get('rate')}% |"
                )
            lines.append("")

        # 攻击技术表格
        techniques = analysis.get("attack_technique_breakdown", [])
        if techniques:
            lines.extend([
                f"## 三、 攻击技术 (Attack Techniques) 统计",
                f"",
                f"| 攻击技术方式 | 测试用例数 | 失陷穿透数 | 穿透失陷率 |",
                f"| :--- | :--- | :--- | :--- |",
            ])
            for t in techniques:
                lines.append(
                    f"| {t.get('technique')} | {t.get('total'):,} | {t.get('vulnerable'):,} | {t.get('rate')}% |"
                )
            lines.append("")

        # 混淆转换器表格
        converters = analysis.get("converter_breakdown", [])
        if converters:
            lines.extend([
                f"## 四、 混淆绕过转换器 (Obfuscation Converters) 分析",
                f"",
                f"| 混淆转换器 | 测试样本 | 失陷样本 | 穿透率 |",
                f"| :--- | :--- | :--- | :--- |",
            ])
            for c in converters:
                lines.append(
                    f"| {c.get('converter')} | {c.get('total'):,} | {c.get('vulnerable'):,} | {c.get('rate')}% |"
                )
            lines.append("")

        # 安全加固建议
        lines.extend([
            f"## 五、 安全加固与防御建议",
            f"",
            f"1. **强化混淆编码动态解码**: 针对高穿透率的凯撒密码 (Caesar)、Leetspeak 及 Base64 编码攻击，建议全面开启 Calypso AI 混淆还原与解码扫描器。",
            f"2. **提示词指令层级与边界隔离**: 在系统提示词层级部署防注入护栏，防止道德困境及角色扮演绕过策略。",
            f"3. **增强 API 健壮性与异常兜底**: 针对 {crash} 例调用超时或异常，需优化模型网关超时配置，避免攻击载荷造成服务拒绝服务 (DoS)。",
            f"",
            f"---",
            f"*报告由 Calypso AI 中文安全运营控制台自动生成*",
        ])

        return "\n".join(lines)
