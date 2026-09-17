<template>
  <div class="playground-view">
    <!-- 头部说明条 -->
    <div class="playground-header">
      <div class="header-intro">
        <h2 class="view-title">实时安全护栏测试台 (Playground)</h2>
        <span class="view-desc">
          输入任意测试提示词或选用 G01~G10 经典对抗案例，实时评估 Calypso 防护网关的拦截判定、置信度得分及 PII 脱敏效果。
        </span>
      </div>
      <div class="header-status">
        <el-tag :type="configStore.isOnline ? 'success' : 'warning'" effect="light">
          当前模式: {{ configStore.isOnline ? '在线集群 API' : '内置智能模拟 (Demo)' }}
        </el-tag>
      </div>
    </div>

    <!-- 主体左右双栏布局 -->
    <div class="playground-layout">
      <!-- 左栏：输入与配置 -->
      <div class="pane pane-input">
        <div class="pane-card">
          <div class="pane-card__header">
            <span class="card-title">
              <el-icon class="title-icon"><Edit /></el-icon>
              测试输入与用例配置
            </span>
            <el-button link size="small" type="info" @click="handleClear">
              <el-icon><Delete /></el-icon>
              清空输入
            </el-button>
          </div>

          <!-- G01~G10 用例选择器 -->
          <div class="form-item">
            <div class="item-label-row">
              <label class="item-label">预设攻防用例 (Presets):</label>
              <span v-if="selectedPresetObj" class="preset-badge">
                预期动作: 
                <el-tag size="small" :type="getActionTagType(selectedPresetObj.expected_action)">
                  {{ formatAction(selectedPresetObj.expected_action) }}
                </el-tag>
              </span>
            </div>

            <el-select
              v-model="selectedPresetId"
              placeholder="选择 G01~G10 攻防测试典型样本"
              class="w-full"
              filterable
              @change="handleSelectPreset"
            >
              <el-option
                v-for="item in presets"
                :key="item.id"
                :label="`[${item.id}] ${item.name} (${formatCategory(item.category)})`"
                :value="item.id"
              >
                <div class="preset-option-item">
                  <span class="preset-opt-id">{{ item.id }}</span>
                  <span class="preset-opt-name">{{ item.name }}</span>
                  <el-tag size="small" :type="getActionTagType(item.expected_action)" effect="plain">
                    {{ formatAction(item.expected_action) }}
                  </el-tag>
                </div>
              </el-option>
            </el-select>

            <div v-if="selectedPresetObj?.description" class="preset-desc-box">
              <el-icon><InfoFilled /></el-icon>
              <span>{{ selectedPresetObj.description }}</span>
            </div>
          </div>

          <!-- 快捷测试标签栏 -->
          <div class="quick-tags-row">
            <span class="quick-label">快速填充:</span>
            <div class="quick-tags">
              <span
                v-for="tag in quickTags"
                :key="tag.id"
                class="quick-tag-btn"
                @click="applyQuickTag(tag.id)"
              >
                {{ tag.label }}
              </span>
            </div>
          </div>

          <!-- 提示词输入框 -->
          <div class="form-item flex-1">
            <label class="item-label">测试提示词 (Prompt):</label>
            <el-input
              v-model="promptText"
              type="textarea"
              :rows="9"
              placeholder="请输入需要送入大模型或经由安全护栏检测的 Prompt 内容..."
              maxlength="3000"
              show-word-limit
              resize="none"
              class="prompt-textarea"
            />
          </div>

          <!-- 提交动作栏 -->
          <div class="submit-action-row">
            <el-button
              type="primary"
              size="large"
              class="scan-btn"
              :loading="scanning"
              :disabled="!promptText.trim()"
              @click="executeScan"
            >
              <el-icon><ShieldCheck v-if="!scanning" /><Loading v-else /></el-icon>
              <span>{{ scanning ? '正在深度安全扫描...' : '执行安全检测 (Scan Prompt)' }}</span>
            </el-button>
          </div>
        </div>
      </div>

      <!-- 右栏：安全判定结果与深度解读 -->
      <div class="pane pane-result">
        <!-- 未检测状态引导 -->
        <div v-if="!scanResult && !scanning" class="result-placeholder-card">
          <el-empty
            description="暂无检测结果。请在左侧输入 Prompt 或选择预设用例后点击「执行安全检测」"
            :image-size="120"
          >
            <div class="placeholder-tip">
              <span>支持多维威胁拦截：提示词注入防御、DAN越狱检测、凭证防泄漏、代码/Base64混淆还原、中国合规 PII 敏感脱敏。</span>
            </div>
          </el-empty>
        </div>

        <!-- 扫描进行中骨架屏 -->
        <div v-else-if="scanning" class="result-card loading-card">
          <div class="loading-state">
            <el-icon class="is-loading loading-icon"><Loading /></el-icon>
            <span class="loading-text">Calypso 安全流水线处理中 (Scan in progress)...</span>
            <span class="loading-sub">执行策略匹配、置信度推断与敏感掩码转换</span>
          </div>
        </div>

        <!-- 检测结果展示 -->
        <div v-else class="result-card">
          <!-- 判定结果大徽章横幅 -->
          <div class="decision-banner" :class="`banner--${scanResult.outcome}`">
            <div class="decision-banner__left">
              <div class="banner-icon-box">
                <el-icon v-if="scanResult.outcome === 'cleared'"><CircleCheckFilled /></el-icon>
                <el-icon v-else-if="scanResult.outcome === 'blocked'"><CircleCloseFilled /></el-icon>
                <el-icon v-else-if="scanResult.outcome === 'redacted'"><WarningFilled /></el-icon>
                <el-icon v-else><HelpFilled /></el-icon>
              </div>
              <div class="banner-text">
                <div class="outcome-title">{{ getOutcomeLabel(scanResult.outcome) }}</div>
                <div class="outcome-sub">{{ getOutcomeDescription(scanResult.outcome) }}</div>
              </div>
            </div>

            <div class="decision-banner__meta">
              <div class="meta-item">
                <span class="meta-label">检测耗时</span>
                <span class="meta-val">{{ scanDurationMs }} ms</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">响应时间戳</span>
                <span class="meta-val">{{ formatTimestamp(scanResult.timestamp) }}</span>
              </div>
            </div>
          </div>

          <!-- 触发扫描器列表卡片 -->
          <div class="result-section">
            <div class="section-title-row">
              <span class="section-title">
                <el-icon class="sec-icon"><Aim /></el-icon>
                触发扫描器与置信度 (Triggered Scanners)
              </span>
              <el-tag
                size="small"
                :type="scanResult.triggered_scanners?.length ? 'danger' : 'success'"
              >
                {{ scanResult.triggered_scanners?.length ? `触发 ${scanResult.triggered_scanners.length} 个规则` : '全部规则校验通过' }}
              </el-tag>
            </div>

            <!-- 无扫描器触发 -->
            <div v-if="!scanResult.triggered_scanners || scanResult.triggered_scanners.length === 0" class="no-scanners-box">
              <el-icon class="clean-icon"><Check /></el-icon>
              <span>未触发任何安全风险拦截规则，符合大模型业务放行标准。</span>
            </div>

            <!-- 扫描器列表 -->
            <div v-else class="scanners-list">
              <div
                v-for="(sc, sIdx) in scanResult.triggered_scanners"
                :key="sIdx"
                class="scanner-item"
              >
                <div class="scanner-item__head">
                  <div class="scanner-title-wrap">
                    <span class="scanner-name">{{ sc.title || sc.name }}</span>
                    <span class="scanner-raw-id">{{ sc.name }}</span>
                  </div>
                  <el-tag size="small" :type="getActionTagType(sc.action || scanResult.outcome)">
                    {{ formatAction(sc.action || scanResult.outcome) }}
                  </el-tag>
                </div>

                <!-- 风险置信度进度条 -->
                <div class="scanner-progress-row">
                  <span class="progress-label">威胁置信度:</span>
                  <div class="progress-bar-wrap">
                    <el-progress
                      :percentage="Math.round((sc.score !== undefined ? sc.score : 0.95) * 100)"
                      :color="getProgressColor(sc.score)"
                      :stroke-width="8"
                      :text-inside="false"
                    />
                  </div>
                </div>

                <!-- 风险解读说明 -->
                <div v-if="sc.reason" class="scanner-reason">
                  <span class="reason-label">解读:</span>
                  <span class="reason-text">{{ sc.reason }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- PII 脱敏比对区 (若为 redacted 或有替换文本) -->
          <div
            v-if="scanResult.outcome === 'redacted' || (scanResult.redacted_prompt && scanResult.redacted_prompt !== scanResult.prompt)"
            class="result-section"
          >
            <div class="section-title-row">
              <span class="section-title">
                <el-icon class="sec-icon"><Lock /></el-icon>
                敏感信息脱敏对比 (Redaction Diff)
              </span>
            </div>
            <DiffViewer
              :original="scanResult.prompt"
              :redacted="scanResult.redacted_prompt"
              :masked-items="scanResult.masked_items || []"
            />
          </div>

          <!-- 大模型流式 / 最终响应卡片 -->
          <div class="result-section">
            <div class="section-title-row">
              <span class="section-title">
                <el-icon class="sec-icon"><ChatDotRound /></el-icon>
                后端大模型处理结果 (LLM Gateway Response)
              </span>
            </div>

            <!-- 阻断拦截状态 -->
            <div v-if="scanResult.outcome === 'blocked'" class="llm-blocked-alert">
              <el-alert
                title="网关直接阻断拦截 (Blocked at Gateway)"
                type="error"
                description="该输入已命中高危风险策略并在网关层丢弃，未透传至后端大语言模型，有效防止模型越狱、系统指令泄露及潜在资源滥用。"
                show-icon
                :closable="false"
              />
            </div>

            <!-- 正常放行或脱敏后回复 -->
            <div v-else class="llm-response-box">
              <div class="llm-bubble">
                <div class="llm-role">
                  <span class="bot-avatar">🤖</span>
                  <span class="bot-name">LLM Model Response</span>
                </div>
                <div class="llm-text">
                  {{ scanResult.llm_response || '内容已通过 Calypso 安全审核并由模型正常响应。' }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import apiClient from '../api/client'
import { useConfigStore } from '../stores/config'
import DiffViewer from '../components/DiffViewer.vue'

const configStore = useConfigStore()

const presets = ref([])
const selectedPresetId = ref('')
const promptText = ref('')
const scanning = ref(false)
const scanResult = ref(null)
const scanDurationMs = ref(0)

const quickTags = [
  { id: 'G01', label: '系统指令劫持 (G01)' },
  { id: 'G03', label: 'DAN 越狱 (G03)' },
  { id: 'G05', label: 'API Key 泄露 (G05)' },
  { id: 'G07', label: 'Base64 混淆 (G07)' },
  { id: 'G08', label: '个人信息脱敏 (G08)' },
  { id: 'G10', label: '金融合规咨询 (G10)' }
]

const selectedPresetObj = computed(() => {
  return presets.value.find((p) => p.id === selectedPresetId.value) || null
})

// 加载 G01~G10 预设用例
async function fetchPresets() {
  try {
    const res = await apiClient.get('/guardrails/presets')
    if (Array.isArray(res)) {
      presets.value = res
    }
  } catch (err) {
    console.error('获取预设用例列表失败:', err)
  }
}

// 选择预设用例后自动填入 Prompt
function handleSelectPreset(presetId) {
  const match = presets.value.find((p) => p.id === presetId)
  if (match) {
    promptText.value = match.prompt
  }
}

// 点击快速填充按钮
function applyQuickTag(presetId) {
  selectedPresetId.value = presetId
  handleSelectPreset(presetId)
}

// 清空输入
function handleClear() {
  promptText.value = ''
  selectedPresetId.value = ''
}

// 执行安全检测
async function executeScan() {
  if (!promptText.value.trim()) {
    ElMessage.warning('请输入待检测的提示词文本')
    return
  }

  scanning.value = true
  const startTime = performance.now()
  try {
    const res = await apiClient.post('/guardrails/scan', {
      prompt: promptText.value.trim(),
      project_id: configStore.projectId || null
    })
    const endTime = performance.now()
    scanDurationMs.value = Math.max(12, Math.round(endTime - startTime))
    scanResult.value = res
  } catch (err) {
    console.error('扫描提示词失败:', err)
  } finally {
    scanning.value = false
  }
}

// 格式转换与标签工具
function formatCategory(cat) {
  const map = {
    prompt_injection: '提示词注入',
    jailbreak: '越狱攻击',
    secrets: '凭证泄露',
    obfuscation: '指令混淆',
    pii: '隐私数据',
    benign: '良性业务'
  }
  return map[cat] || cat || '通用'
}

function formatAction(action) {
  const map = {
    blocked: '阻断拦截',
    cleared: '安全放行',
    redacted: '敏感脱敏',
    masked: '敏感脱敏',
    flagged: '标记告警'
  }
  return map[action] || action || '未知'
}

function getActionTagType(action) {
  const map = {
    blocked: 'danger',
    cleared: 'success',
    redacted: 'warning',
    masked: 'warning',
    flagged: 'warning'
  }
  return map[action] || 'info'
}

function getOutcomeLabel(outcome) {
  if (outcome === 'cleared') return '放行通过 (Cleared)'
  if (outcome === 'blocked') return '阻断拦截 (Blocked)'
  if (outcome === 'redacted' || outcome === 'masked') return '敏感脱敏 (Redacted)'
  return '标记审计 (Flagged)'
}

function getOutcomeDescription(outcome) {
  if (outcome === 'cleared') return '提示词未发现攻击载荷或敏感信息，已由网关安全放行至大语言模型。'
  if (outcome === 'blocked') return '命中高危对抗策略或系统凭证泄露规则，网关已实施阻断并拒绝透传。'
  if (outcome === 'redacted' || outcome === 'masked') return '检测到个人隐私身份证、银行卡或手机号，网关已完成动态掩码脱敏后转交模型。'
  return '命中低危审计策略，已做告警标记。'
}

function getProgressColor(score) {
  const val = (score !== undefined ? score : 0.95) * 100
  if (val >= 90) return '#ef4444'
  if (val >= 70) return '#f97316'
  return '#eab308'
}

function formatTimestamp(isoStr) {
  if (!isoStr) return new Date().toLocaleTimeString()
  try {
    const d = new Date(isoStr)
    return d.toLocaleTimeString()
  } catch {
    return isoStr
  }
}

onMounted(() => {
  fetchPresets()
})
</script>

<style scoped>
.playground-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.playground-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #ffffff;
  padding: 16px 20px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
}

.view-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.view-desc {
  font-size: 13px;
  color: #64748b;
  margin-top: 4px;
  display: block;
}

/* 左右分栏 */
.playground-layout {
  display: grid;
  grid-template-columns: 1fr 1.25fr;
  gap: 16px;
  align-items: start;
}

@media (max-width: 1100px) {
  .playground-layout {
    grid-template-columns: 1fr;
  }
}

.pane-card, .result-card, .result-placeholder-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
}

.pane-card {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.pane-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 12px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-icon {
  color: #3b82f6;
  font-size: 16px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.item-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.item-label {
  font-size: 13px;
  font-weight: 500;
  color: #475569;
}

.preset-desc-box {
  background: #f8fafc;
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 12px;
  color: #64748b;
  display: flex;
  align-items: center;
  gap: 6px;
  border: 1px dashed #cbd5e1;
}

.quick-tags-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.quick-label {
  font-size: 12px;
  color: #94a3b8;
}

.quick-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.quick-tag-btn {
  font-size: 11px;
  background-color: #f1f5f9;
  color: #475569;
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
  border: 1px solid #e2e8f0;
  transition: all 0.15s;
}

.quick-tag-btn:hover {
  background-color: #e0f2fe;
  color: #0369a1;
  border-color: #7dd3fc;
}

.prompt-textarea :deep(.el-textarea__inner) {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
  font-size: 13px;
  line-height: 1.6;
  border-radius: 8px;
}

.submit-action-row {
  margin-top: 4px;
}

.scan-btn {
  width: 100%;
  font-weight: 600;
  letter-spacing: 0.5px;
}

/* 结果栏样式 */
.result-placeholder-card {
  padding: 48px 24px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.placeholder-tip {
  max-width: 480px;
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.6;
  margin-top: 8px;
}

.loading-card {
  padding: 60px 20px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.loading-icon {
  font-size: 32px;
  color: #3b82f6;
}

.loading-text {
  font-size: 15px;
  font-weight: 600;
  color: #334155;
}

.loading-sub {
  font-size: 12px;
  color: #94a3b8;
}

.result-card {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 决策横幅 */
.decision-banner {
  border-radius: 8px;
  padding: 16px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.banner--cleared {
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
  border: 1px solid #86efac;
}
.banner--cleared .banner-icon-box { color: #16a34a; }
.banner--cleared .outcome-title { color: #15803d; }

.banner--blocked {
  background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
  border: 1px solid #fca5a5;
}
.banner--blocked .banner-icon-box { color: #dc2626; }
.banner--blocked .outcome-title { color: #b91c1c; }

.banner--redacted {
  background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
  border: 1px solid #fde68a;
}
.banner--redacted .banner-icon-box { color: #d97706; }
.banner--redacted .outcome-title { color: #b45309; }

.decision-banner__left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.banner-icon-box {
  font-size: 36px;
  display: flex;
  align-items: center;
}

.outcome-title {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.2;
}

.outcome-sub {
  font-size: 12px;
  color: #475569;
  margin-top: 4px;
}

.decision-banner__meta {
  display: flex;
  gap: 16px;
  text-align: right;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.meta-label {
  font-size: 11px;
  color: #64748b;
}

.meta-val {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}

/* 结果分区 */
.result-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 6px;
}

.sec-icon {
  color: #3b82f6;
}

.no-scanners-box {
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 6px;
  padding: 12px 16px;
  font-size: 13px;
  color: #16a34a;
  display: flex;
  align-items: center;
  gap: 8px;
}

.clean-icon {
  font-size: 16px;
}

.scanners-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.scanner-item {
  background: #fafaf9;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.scanner-item__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.scanner-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.scanner-name {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.scanner-raw-id {
  font-size: 11px;
  color: #94a3b8;
  background: #f1f5f9;
  padding: 1px 6px;
  border-radius: 4px;
}

.scanner-progress-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-label {
  font-size: 12px;
  color: #64748b;
  width: 70px;
}

.progress-bar-wrap {
  flex: 1;
}

.scanner-reason {
  font-size: 12px;
  background: #ffffff;
  border: 1px solid #f1f5f9;
  padding: 6px 10px;
  border-radius: 4px;
  color: #475569;
  display: flex;
  gap: 6px;
}

.reason-label {
  font-weight: 600;
  color: #dc2626;
}

/* 大模型回复卡片 */
.llm-bubble {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.llm-role {
  display: flex;
  align-items: center;
  gap: 6px;
}

.bot-avatar {
  font-size: 16px;
}

.bot-name {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.llm-text {
  font-size: 13px;
  line-height: 1.6;
  color: #0f172a;
  white-space: pre-wrap;
  word-break: break-word;
}

.preset-option-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
.preset-opt-id {
  font-weight: 700;
  color: #2563eb;
  margin-right: 6px;
}
.preset-opt-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 8px;
}
</style>
