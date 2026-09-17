import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

doc = docx.Document('格式模版.docx')

# 1. Update Title Page (P4)
for p in doc.paragraphs:
    if 'XXX方案' in p.text:
        p.text = p.text.replace('XXX方案', 'BMW Agentic AI 自动化红队安全扫描报告')
        p.runs[0].font.bold = True
        p.runs[0].font.size = Pt(22)

# 2. Update Table 0 (Version Control)
t0 = doc.tables[0]
if len(t0.rows) >= 2:
    row1 = t0.rows[1].cells
    row1[0].text = 'F5 AI Safety Team'
    row1[1].text = 'BMW Agentic AI 红队测试分析报告'
    row1[2].text = '20260824'
    row1[3].text = 'V1.0'
    row1[4].text = 'F5 Red Team Reviewer'

# 3. Update Table 1 (Document Meta)
t1 = doc.tables[1]
t1.rows[0].cells[1].text = 'BMW Agentic AI 自动化红队安全扫描报告'
t1.rows[0].cells[3].text = 'F5-SEC-20260824-01'
t1.rows[1].cells[1].text = 'V1.0'
t1.rows[1].cells[3].text = '机密 (Confidential)'
t1.rows[2].cells[1].text = 'BMW AI 安全团队 / 项目组'
t1.rows[2].cells[3].text = '3年'
t1.rows[3].cells[1].text = 'F5 Calypso AI Redteam Platform V2.4'
t1.rows[4].cells[1].text = 'https://www.f5.com/products/security/calypso-ai'

# Helper function to style table header and borders
def format_table(table, header_bg="1B365D"):
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Set header row background color
    hdr_cells = table.rows[0].cells
    for cell in hdr_cells:
        shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{header_bg}"/>')
        cell._tc.get_or_add_tcPr().append(shading_elm)
        for p in cell.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs:
                r.font.bold = True
                r.font.color.rgb = RGBColor(255, 255, 255)
                r.font.size = Pt(10)
    
    # Alternate row colors and cell padding
    for r_idx, row in enumerate(table.rows[1:], start=1):
        bg_color = "F2F4F8" if r_idx % 2 == 1 else "FFFFFF"
        for cell in row.cells:
            shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg_color}"/>')
            cell._tc.get_or_add_tcPr().append(shading_elm)
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(9.5)

# Helper function to remove template paragraphs from P40 onwards
start_idx = None
for i, p in enumerate(doc.paragraphs):
    if p.text == '一级标题' or p.style.name == 'Heading 1':
        start_idx = i
        break

if start_idx is not None:
    # Delete paragraphs from start_idx to the end
    p_elements = [p._p for p in doc.paragraphs[start_idx:]]
    for p_elm in p_elements:
        p_elm.getparent().remove(p_elm)

# Add Document Heading 1 / 2 / 3 & Content
def add_h1(text):
    p = doc.add_paragraph(text, style='Heading 1')
    return p

def add_h2(text):
    p = doc.add_paragraph(text, style='Heading 2')
    return p

def add_h3(text):
    p = doc.add_paragraph(text, style='Heading 3')
    return p

def add_p(text, bold_prefix=None):
    p = doc.add_paragraph(style='Normal Indent')
    if bold_prefix:
        r_bold = p.add_run(bold_prefix)
        r_bold.bold = True
        r_bold.font.color.rgb = RGBColor(27, 54, 93)
    p.add_run(text)
    return p

def add_callout(text, title="【重要安全发现】", bg_color="FFF3CD", border_color="E6A23C"):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.2)
    p.paragraph_format.right_indent = Inches(0.2)
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    
    # Shading and border
    tcPr = p._p.get_or_add_pPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{bg_color}"/>')
    tcPr.append(shd)
    
    r_title = p.add_run(title + "\n")
    r_title.bold = True
    r_title.font.color.rgb = RGBColor(180, 100, 0)
    r_text = p.add_run(text)
    r_text.font.size = Pt(9.5)

# --- SECTION 1: 项目概述与核心结论 ---
add_h1("1. 项目概述与核心结论")

add_p("本报告针对 BMW Agentic AI 自动化红队安全扫描项目进行单期专项深度评估。本次测试基于 2026 年 8 月 24 日最新的红队扫描任务数据集（BMW Agentic test 0824.csv），旨在对目标 AI Agent（targetAgentUS-copy，服务地址：http://43.130.11.163:80）进行全方位的安全防护能力、越狱抵御能力、越权指令执行与服务稳定性评估。")

add_callout(
    "经过适配器配置与超时重试策略调整后，前两次测试中高达 84.5%~89.6% 的 Request timed out 请求超时现象已完全消除（超时率清零）！\n"
    "成功完成响应的有效测试用例飙升至 8,632 条（占比 81.00%），样本量扩大了 7.7 倍。在 8,632 条成功响应用例中，确认模型被攻破/失陷（Vulnerable）的用例为 1,175 条，真实有效漏洞率达到 13.61%。此外，本次测试暴露出了新的后端 TCP 连接重置异常（Errno 104 Connection Reset by Peer，共 2,023 处，占比 18.98%）。",
    title="【核心测试成果与突破】",
    bg_color="E8F4F8",
    border_color="1B365D"
)

add_h2("1.1 测试环境与基本信息")
add_p("本次红队自动化安全扫描的基本配置与目标环境信息如下表所示：")

# Table for basic info
t_info = doc.add_table(rows=6, cols=2)
t_info_data = [
    ["配置项", "详细参数 / 对应值"],
    ["扫描任务名称 (Campaign)", "BMW Agentic test 0824"],
    ["目标连接名称 (Connection)", "targetAgentUS-copy"],
    ["目标 Provider ID", "01a03260-eb70-7031-9b53-1072dc8b7049"],
    ["目标服务地址 (URL)", "http://43.130.11.163:80/v1/chat/completions"],
    ["测试模型 (Model)", "deepseek-v4-flash"]
]
for r_idx, row in enumerate(t_info.rows):
    row.cells[0].text = t_info_data[r_idx][0]
    row.cells[1].text = t_info_data[r_idx][1]
format_table(t_info)

add_h2("1.2 核心安全结论与统计概览")
add_p("本次扫描共覆盖 10,658 条红队攻击测试用例。整体响应状态与安全失陷结果分布如下表所示：")

# Table for overall stats
t_stat = doc.add_table(rows=6, cols=4)
t_stat_data = [
    ["测试响应类型", "用例数量 (条)", "占总用例比例 (%)", "安全风险与状态解读"],
    ["成功完成响应 (Completed)", "8,632", "81.00%", "模型生成完整回复，有效评估样本"],
    ["确认安全失陷 (Vulnerable)", "1,175", "11.02% (整体) / 13.61% (有效)", "模型防线被攻破，输出违规/危险文本"],
    ["TCP 连接重置 (Errno 104)", "2,023", "18.98%", "目标服务器强制切断 TCP 连接，后端异常"],
    ["请求超时 (Timed Out)", "0", "0.00%", "🎉 超时率清零，连接适配器修复生效"],
    ["其他 HTTP 报错", "3", "0.02%", "未知网络/网关临时报错"]
]
for r_idx, row in enumerate(t_stat.rows):
    for c_idx in range(4):
        row.cells[c_idx].text = t_stat_data[r_idx][c_idx]
format_table(t_stat)


# --- SECTION 2: 核心安全缺陷与绕过技术分析 ---
add_h1("2. 核心安全缺陷与绕过技术分析")

add_h2("2.1 编码与字符混淆 (Converters) 攻破率分析")
add_p("测试数据表明，目标 Agent 的安全防护网关对明文直接攻击 (No Converter) 的拦截效果相对较好（明文攻破率为 9.02%）。然而，一旦攻击者采用编码、密码或字符分隔混淆手段，前置安全检测层便大幅失效，大模型自主解密后执行了恶意指令。")

# Table for converters
t_conv = doc.add_table(rows=8, cols=5)
t_conv_data = [
    ["转化器 / 绕过技术 (Converter)", "测试用例数", "完成响用例", "确认攻破数 (Vuln)", "有效攻破率 (%)"],
    ["Caesar converter (凯撒密码)", "1,521", "1,230", "306", "24.88%"],
    ["Leetspeak converter (黑客字/替换字)", "1,522", "1,231", "243", "19.74%"],
    ["Base 64 converter (Base64编码)", "1,522", "1,238", "167", "13.49%"],
    ["Single character converter (单字符隔离)", "1,522", "1,234", "128", "10.37%"],
    ["Repeat token converter (重复 Token 干扰)", "1,522", "1,236", "122", "9.87%"],
    ["No Converter (明文直接攻击)", "1,523", "1,242", "112", "9.02%"],
    ["Unicode confusable (同形字/混淆字)", "1,522", "1,221", "97", "7.94%"]
]
for r_idx, row in enumerate(t_conv.rows):
    for c_idx in range(5):
        row.cells[c_idx].text = t_conv_data[r_idx][c_idx]
format_table(t_conv)

add_p("数据要点分析：", bold_prefix="【归因诊断】")
add_p("1. 凯撒密码 (Caesar Converter) 攻破率高达 24.88%，达到了明文直接攻击的 2.76 倍，是穿透防线最有效的武器。")
add_p("2. 黑客体 (Leetspeak Converter) 攻破率达到 19.74%（2.19 倍），Base64 编码攻破率达到 13.49%（1.50 倍）。这表明安全网关缺乏前置预解码（Pre-decoding Pipeline）机制。")

add_h2("2.2 攻击向量 (Attack Vectors) 穿透成功率排行")
add_p("在 8,632 条完成响应的测试中，攻破成功率排名前 10 的攻击向量如下表所示：")

# Table for top attack vectors
t_av = doc.add_table(rows=11, cols=5)
t_av_data = [
    ["攻击向量 (Attack Vector)", "总测试数", "完成响应数", "攻破数 (Vuln)", "有效攻破率 (%)"],
    ["Flip (逻辑翻转)", "665", "384", "86", "22.40%"],
    ["Conditional context change (条件上下文变更)", "490", "409", "88", "21.52%"],
    ["Fictional context change (虚构剧情包装)", "448", "380", "79", "20.79%"],
    ["Crescendo (渐进诱导)", "393", "383", "71", "18.54%"],
    ["Bias framing (偏见框架)", "462", "455", "81", "17.80%"],
    ["Fallacy failure (谬误引导)", "378", "371", "63", "16.98%"],
    ["Developer role (假冒开发者角色)", "441", "434", "68", "15.67%"],
    ["Morality dilemma (道德困境包装)", "161", "154", "24", "15.58%"],
    ["Style injection (样式/格式注入)", "553", "546", "84", "15.38%"],
    ["Refusal suppression (拒绝压制)", "518", "511", "78", "15.26%"]
]
for r_idx, row in enumerate(t_av.rows):
    for c_idx in range(5):
        row.cells[c_idx].text = t_av_data[r_idx][c_idx]
format_table(t_av)

add_h2("2.3 恶意意图分类 (Intent Categories) 失陷分布")
add_p("对成功攻破的 1,175 处失陷用例按内容危害类别分类：")

# Table for intent categories
t_ic = doc.add_table(rows=7, cols=5)
t_ic_data = [
    ["意图危害分类 (Intent Category)", "总测试数", "完成响应数", "攻破失陷数", "有效失陷率 (%)"],
    ["violence / harm (暴力/伤害/自残)", "4,320", "3,523", "502", "14.25%"],
    ["harassment (骚扰/辱骂/霸凌)", "2,050", "1,653", "300", "18.15%"],
    ["illegal acts (违法犯罪行为指导)", "1,520", "1,228", "182", "14.82%"],
    ["toxicity / hate (仇恨/毒性言论)", "1,320", "1,144", "100", "8.74%"],
    ["misinformation (虚假信息/谣言)", "800", "636", "66", "10.38%"],
    ["sexually explicit (色情显式内容)", "648", "448", "25", "5.58%"]
]
for r_idx, row in enumerate(t_ic.rows):
    for c_idx in range(5):
        row.cells[c_idx].text = t_ic_data[r_idx][c_idx]
format_table(t_ic)


# --- SECTION 3: 网络与接口稳定性异常剖析 ---
add_h1("3. 网络与接口稳定性异常剖析 ([Errno 104])")

add_p("本次扫描中，最显著的网络层现象是抛出了 2,023 条 (18.98%) 的 Connection Reset 错误（Failed to run block 'block' after 5 attempts: [Errno 104] Connection reset by peer）。")

add_callout(
    "[Errno 104] Connection reset by peer 代表目标服务器 (43.130.11.163:80) 在处理特定请求时，TCP Socket 连接被服务端强制发送 RST 包切断。\n"
    "这表明目标 Agent 的后端 Web 框架、推理引擎 (如 FastAPI, vLLM, Ollama) 或反向代理网关在处理某些极长或深度嵌套的 Payload 时发生了未捕获的内存溢出 (OOM) 或崩溃。",
    title="【技术根因诊断】",
    bg_color="FDEDEC",
    border_color="C0392B"
)

add_h2("3.1 [Errno 104] 异常触发向量分布")
add_p("对发生 Connection Reset 异常的 2,023 处用例按攻击向量进行统计：")

# Table for errno 104 distribution
t_err = doc.add_table(rows=8, cols=4)
t_err_data = [
    ["攻击向量 (Attack Vector)", "[Errno 104] 异常次数", "占此类总异常比例 (%)", "主要结合的转化器 (Converter)"],
    ["Scenario nesting (场景嵌套)", "720", "35.59%", "Unconverted (明文) / Unicode / Leetspeak"],
    ["Word game (文字游戏)", "532", "26.30%", "Unicode confusable / Leetspeak"],
    ["Flip (逻辑翻转)", "281", "13.89%", "Unconverted / Unicode"],
    ["Math prompt (数学提示词包装)", "143", "7.07%", "Unicode / Leetspeak"],
    ["DAN (Do Anything Now 越狱)", "88", "4.35%", "Unicode / Leetspeak"],
    ["Conditional context change", "81", "4.00%", "Unicode / Leetspeak"],
    ["其他攻击向量小计", "178", "8.80%", "各类混合编码"]
]
for r_idx, row in enumerate(t_err.rows):
    for c_idx in range(4):
        row.cells[c_idx].text = t_err_data[r_idx][c_idx]
format_table(t_err)


# --- SECTION 4: 典型高危失陷案例展示 ---
add_h1("4. 典型高危失陷案例展示")

add_h2("案例 1：凯撒密码编码绕过致网络霸凌言论输出")
add_p("攻击向量：Morality dilemma | 转化器：Caesar converter (Offset 5)", bold_prefix="【案例背景】")
add_p("攻击者将诱导网络霸凌与人身攻击的指令用 Caesar 密码加密后发送给 Agent。安全网关直接放行，模型解码后生成了逼真且毒性极高的网络霸凌言论。", bold_prefix="【失陷现象】")

add_h2("案例 2：Leetspeak 编码绕过致匿名死亡威胁生成")
add_p("攻击向量：Fictional context change | 转化器：Leetspeak converter", bold_prefix="【案例背景】")
add_p("攻击者利用字符替换包装匿名死亡威胁指令。模型绕过安全拦截，输出了充满恐吓细节的匿名信件文本。", bold_prefix="【失陷现象】")

add_h2("案例 3：Base64 编码绕过致教唆自杀/自残文本输出")
add_p("攻击向量：Conditional context change | 转化器：Base 64 converter", bold_prefix="【案例背景】")
add_p("攻击者将诱导自杀/自残的敏感指令以 Base64 形式传入，模型自主解密后生成了极具危险性的劝诱言论。", bold_prefix="【失陷现象】")


# --- SECTION 5: 系统性防御与加固建议 ---
add_h1("5. 系统性防御与加固建议")

add_h2("5.1 部署前置预解码引擎 (Pre-decoding Guardrail - 优先度 P0)")
add_p("在安全网关拦截层，强制增加对 Base64、Caesar Cipher（自动遍历偏移量 1~25）、Leetspeak 和 Single Char 隔离格式的自动识别与预解码引擎，还原为原始明文后再送入语义检测模型。")

add_h2("5.2 修复后端 TCP Connection Reset 异常 (优先度 P0)")
add_p("针对 2,023 处 [Errno 104] 报错，优化目标服务器 (43.130.11.163:80) 的 Web 框架连接池与 Payload 字节上限，限制嵌套深度，增加超长/嵌套提示词的优雅拒绝（返回 400/413）而非直接挂断 TCP 连接。")

add_h2("5.3 建立双向防线机制 (Input + Output Guardrails - 优先度 P1)")
add_p("在 LLM 输出端增加二次响应检测，杜绝死亡威胁、霸凌言论及毒性文本被返回给终端用户。")

# Save document
output_filename = 'BMW_Agentic_AI_RedTeam_Report_0824.docx'
doc.save(output_filename)
print(f'Successfully generated Word report: {output_filename}')
