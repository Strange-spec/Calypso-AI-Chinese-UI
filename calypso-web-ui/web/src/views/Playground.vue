<template>
  <div class="playground-view">
    <!-- 头部：项目选择器与项目护栏规则态势 -->
    <el-card class="project-scope-card" shadow="never">
      <div class="project-scope-content">
        <div class="scope-left">
          <div class="scope-label">
            <el-icon class="label-icon"><Aim /></el-icon>
            <span class="label-text">测试目标业务项目 (Target Project):</span>
          </div>
          <el-select
            v-model="activeProjectId"
            placeholder="请选择需要测试的安全护栏项目"
            style="width: 320px"
            @change="handleProjectChange"
            @visible-change="handleSelectDropdownVisible"
            :loading="loadingProjects"
          >
            <el-option
              v-for="proj in projectsList"
              :key="proj.id"
              :label="`${proj.name} [${proj.type || 'app'}]`"
              :value="proj.id"
            >
              <div class="project-select-opt">
                <span class="opt-name">{{ proj.name }}</span>
                <el-tag size="small" :type="getTypeTag(proj.type)" effect="plain">
                  {{ proj.type || 'app' }}
                </el-tag>
              </div>
            </el-option>
          </el-select>

          <!-- 刷新项目列表按钮 -->
          <el-button
            icon="Refresh"
            circle
            title="刷新项目列表"
            :loading="loadingProjects"
            @click="handleManualRefreshProjects"
          />

          <!-- 应用项目参数按钮 -->
          <el-button
            type="primary"
            size="default"
            class="apply-project-btn"
            @click="applyProjectToPlayground"
          >
            <el-icon><Check /></el-icon>
            <span>应用项目参数至测试台</span>
          </el-button>

          <!-- Project ID 快捷展示与复制 -->
          <div v-if="currentProject" class="project-id-badge">
            <span class="id-title">Project ID:</span>
            <el-tag size="small" effect="plain" class="id-tag">{{ currentProject.id }}</el-tag>
            <el-button
              link
              type="primary"
              size="small"
              icon="CopyDocument"
              @click="copyProjectId"
            >
              复制
            </el-button>
          </div>
        </div>

        <div class="scope-right">
          <el-tag :type="configStore.isOnline ? 'success' : 'warning'" effect="light">
            {{ configStore.isOnline ? 'Calypso 在线集群 API' : '离线智能模拟 (Demo)' }}
          </el-tag>
        </div>
      </div>

      <!-- 当前项目生效规则徽章条 -->
      <div v-if="currentProject" class="active-rules-bar">
        <div class="rules-bar-label">
          <span>当前项目生效 Guardrails 规则 ({{ currentProjectScanners.length }}项):</span>
        </div>
        <div class="active-rules-tags">
          <template v-if="currentProjectScanners.length > 0">
            <el-tooltip
              v-for="scanner in currentProjectScanners"
              :key="scanner.id"
              :content="`模式: ${scanner.mode || 'block'} | 阻断: ${scanner.blocking !== false ? '开启' : '关闭'}`"
              placement="top"
            >
              <el-tag
                size="small"
                :type="scanner.mode === 'block' ? 'danger' : scanner.mode === 'redact' ? 'warning' : 'primary'"
                effect="light"
                class="rule-badge"
              >
                <el-icon><Check /></el-icon>
                {{ scanner.name || scanner.id }}
              </el-tag>
            </el-tooltip>
          </template>
          <div v-else class="no-rules-tip">
            <el-icon><Warning /></el-icon>
            <span>当前项目尚未绑定任何 Guardrail 规则，所有请求将直接放行至大模型！</span>
          </div>
        </div>
      </div>
    </el-card>

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

          <!-- 绑定目标项目状态指示条 -->
          <div class="target-project-status-bar">
            <div class="status-left">
              <span class="status-icon">🎯</span>
              <span class="status-label">已绑定目标业务项目:</span>
              <el-tag size="default" type="primary" effect="dark" class="proj-badge">
                {{ currentProject?.name || '默认业务项目' }}
              </el-tag>
              <span class="proj-id-code">ID: {{ boundProjectId || activeProjectId }}</span>
            </div>
            <el-tag size="small" type="success" effect="light">
              <el-icon><CircleCheckFilled /></el-icon>
              <span>参数已同步就绪</span>
            </el-tag>
          </div>

          <!-- G01~G10 用例选择器 -->
          <div class="form-item">
            <div class="item-label-row">
              <label class="item-label">预设攻防用例 (Presets):</label>
              <span v-if="selectedPresetObj" class="preset-badge">
                预期判定: 
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
              <el-icon><Aim v-if="!scanning" /><Loading v-else /></el-icon>
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
            description="暂无检测结果。请选择项目并在左侧输入 Prompt 点击「执行安全检测」"
            :image-size="120"
          >
            <div class="placeholder-tip">
              <span>系统将使用【{{ currentProject?.name || '当前项目' }}】绑定的 Guardrails 规则集执行动态拦截与脱敏评估。</span>
            </div>
          </el-empty>
        </div>

        <!-- 扫描进行中骨架屏 -->
        <div v-else-if="scanning" class="result-card loading-card">
          <div class="loading-state">
            <el-icon class="is-loading loading-icon"><Loading /></el-icon>
            <span class="loading-text">Calypso 安全流水线处理中 (Scan in progress)...</span>
            <span class="loading-sub">项目 ID: {{ activeProjectId }} | 正在匹配生效护栏规则</span>
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
                <span class="meta-label">测试目标业务项目</span>
                <span class="meta-val project-badge-text">{{ scanResult.project_name || currentProject?.name }}</span>
              </div>
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
                触发规则与威胁评估 (Triggered Scanners)
              </span>
              <div class="section-actions">
                <el-tag
                  size="small"
                  :type="scanResult.triggered_scanners?.length ? 'danger' : 'success'"
                >
                  {{ scanResult.triggered_scanners?.length ? `命中 ${scanResult.triggered_scanners.length} 个规则` : '全部规则校验通过' }}
                </el-tag>
                <el-button link type="primary" size="small" @click="openLogDrawer">
                  查看裁定报文
                </el-button>
              </div>
            </div>

            <!-- 无扫描器触发 -->
            <div v-if="!scanResult.triggered_scanners || scanResult.triggered_scanners.length === 0" class="no-scanners-box">
              <el-icon class="clean-icon"><Check /></el-icon>
              <span>未触发当前项目下的任何拦截规则，符合大模型业务放行标准。</span>
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
                    <span class="scanner-raw-id">{{ sc.name || sc.id }}</span>
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
                      :percentage="Math.round((sc.score !== undefined ? sc.score : (sc.confidence || 0.95)) * 100)"
                      :color="getProgressColor(sc.score || sc.confidence)"
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
              <el-button
                size="small"
                type="primary"
                plain
                icon="Document"
                @click="openLogDrawer"
              >
                查看 Raw 报文
              </el-button>
            </div>

            <!-- 阻断拦截状态：展示真实网关拦截报文与丢弃说明 -->
            <div v-if="scanResult.outcome === 'blocked'" class="llm-blocked-container">
              <div class="interception-banner">
                <div class="interception-header">
                  <el-icon class="interception-icon"><CircleCloseFilled /></el-icon>
                  <div class="interception-titles">
                    <span class="interception-title">安全护栏网关阻断拦截 (Blocked at Gateway)</span>
                    <span class="interception-sub">输入命中高危护栏策略，已在网关处丢弃，下游大语言模型未产生响应</span>
                  </div>
                </div>
                <div class="interception-body">
                  <div class="interception-meta-item">
                    <span class="meta-k">目标业务项目:</span>
                    <span class="meta-v">{{ scanResult.project_name || currentProject?.name }} (ID: {{ scanResult.project_id || activeProjectId }})</span>
                  </div>
                  <div class="interception-meta-item">
                    <span class="meta-k">拦截动作:</span>
                    <el-tag size="small" type="danger" effect="dark">直接丢弃请求 (Drop Request)</el-tag>
                  </div>
                  <div class="interception-meta-item" v-if="scanResult.triggered_scanners?.length">
                    <span class="meta-k">触发规则:</span>
                    <div class="interception-rules">
                      <el-tag
                        v-for="s in scanResult.triggered_scanners"
                        :key="s.id"
                        size="small"
                        type="danger"
                        effect="light"
                      >
                        {{ s.title || s.name || s.id }}
                      </el-tag>
                    </div>
                  </div>
                  <div class="interception-raw-text" v-if="scanResult.llm_response">
                    <pre>{{ scanResult.llm_response }}</pre>
                  </div>
                </div>
              </div>
            </div>

            <!-- 正常放行或脱敏后回复：展示真实大模型响应文本、Token 与思考链路 -->
            <div v-else class="llm-response-box">
              <div class="llm-model-info-bar">
                <div class="model-badge">
                  <span class="bot-avatar">🤖</span>
                  <span class="bot-name">{{ scanResult.model_name || 'LLM Model Response' }}</span>
                </div>
                <div class="model-meta-stats" v-if="scanResult.token_usage">
                  <el-tag size="small" type="info" effect="plain">
                    Token: 提问 {{ scanResult.token_usage.prompt_tokens || '-' }} / 生成 {{ scanResult.token_usage.completion_tokens || '-' }} / 总计 {{ scanResult.token_usage.total_tokens || '-' }}
                  </el-tag>
                </div>
              </div>

              <!-- 深度思考内容 (Reasoning Content) -->
              <div v-if="scanResult.reasoning_content" class="llm-reasoning-card">
                <div class="reasoning-title">
                  <el-icon><Opportunity /></el-icon>
                  <span>模型思考过程 (Reasoning Process)</span>
                </div>
                <div class="reasoning-text">{{ scanResult.reasoning_content }}</div>
              </div>

              <div class="llm-bubble">
                <div class="llm-text">
                  {{ scanResult.llm_response || '内容已通过 Calypso 安全审核并由下游模型正常响应。' }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 原始 JSON 抽屉 -->
    <el-drawer
      v-model="logDrawerVisible"
      title="Calypso 原生安全评估报文"
      size="45%"
      destroy-on-close
    >
      <div v-if="scanResult">
        <el-descriptions title="测试请求摘要" :column="2" border size="small">
          <el-descriptions-item label="测试项目">
            {{ currentProject?.name || '全局项目' }}
          </el-descriptions-item>
          <el-descriptions-item label="Project ID">
            <el-text class="mono-text">{{ scanResult.project_id || activeProjectId }}</el-text>
          </el-descriptions-item>
          <el-descriptions-item label="最终判定">
            <el-tag size="small" :type="getActionTagType(scanResult.outcome)">
              {{ formatAction(scanResult.outcome) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="耗时">
            {{ scanDurationMs }} ms
          </el-descriptions-item>
        </el-descriptions>
        <div style="margin-top: 16px;">
          <pre class="json-code"><code>{{ JSON.stringify(scanResult.raw || scanResult, null, 2) }}</code></pre>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import apiClient from '../api/client'
import { useConfigStore } from '../stores/config'
import { useProjectsStore } from '../stores/projects'
import DiffViewer from '../components/DiffViewer.vue'

const props = defineProps({
  initialProjectId: {
    type: String,
    default: ''
  }
})

const configStore = useConfigStore()
const projectsStore = useProjectsStore()

const projectsList = computed(() => projectsStore.projects)
const activeProjectId = ref(props.initialProjectId || '')
const boundProjectId = ref(props.initialProjectId || '')
const loadingProjects = computed(() => projectsStore.loading)

const presets = ref([])
const selectedPresetId = ref('')
const promptText = ref('')
const scanning = ref(false)
const scanResult = ref(null)
const scanDurationMs = ref(0)
const logDrawerVisible = ref(false)

const quickTags = [
  { id: 'G01', label: '系统指令劫持 (G01)' },
  { id: 'G03', label: 'DAN 越狱 (G03)' },
  { id: 'G05', label: 'API Key 泄露 (G05)' },
  { id: 'G07', label: 'Base64 混淆 (G07)' },
  { id: 'G08', label: '个人信息脱敏 (G08)' },
  { id: 'G10', label: '金融合规咨询 (G10)' }
]

const currentProject = computed(() => {
  const targetId = boundProjectId.value || activeProjectId.value
  return projectsStore.findProjectById(targetId) || null
})

const currentProjectScanners = computed(() => {
  return currentProject.value?.config?.scanners || []
})

const selectedPresetObj = computed(() => {
  return presets.value.find((p) => p.id === selectedPresetId.value) || null
})

import { useRoute, useRouter } from 'vue-router'
const route = useRoute()
const router = useRouter()

// 应用选中的业务项目参数至测试台
function applyProjectToPlayground() {
  if (!activeProjectId.value) {
    ElMessage.warning('请先在下拉框选择业务项目')
    return
  }
  boundProjectId.value = activeProjectId.value
  scanResult.value = null
  ElMessage.success(`已成功应用项目【${currentProject.value?.name || activeProjectId.value}】至测试台！`)
}

// 获取项目列表
async function fetchProjects(force = false) {
  try {
    await projectsStore.fetchProjects(force)
    const targetId = route.query.project_id || props.initialProjectId
    if (targetId && projectsList.value.some(p => p.id === targetId)) {
      activeProjectId.value = targetId
      boundProjectId.value = targetId
    } else if (!activeProjectId.value && projectsList.value.length > 0) {
      activeProjectId.value = projectsList.value[0].id
      boundProjectId.value = projectsList.value[0].id
    }
  } catch (err) {
    console.error('获取项目空间失败', err)
  }
}

async function handleManualRefreshProjects() {
  await fetchProjects(true)
  ElMessage.success('已刷新业务项目列表')
}

function handleSelectDropdownVisible(visible) {
  if (visible) {
    projectsStore.fetchProjects()
  }
}

watch(
  () => [route.query.project_id, props.initialProjectId],
  async ([queryId, propId]) => {
    const target = queryId || propId
    if (!target) return
    // 如果在当前项目列表中未找到目标，强制重新拉取一次最新项目列表
    if (!projectsList.value.some((p) => p.id === target)) {
      await projectsStore.fetchProjects(true)
    }
    if (projectsList.value.some((p) => p.id === target)) {
      activeProjectId.value = target
      boundProjectId.value = target
    }
  }
)

watch(
  () => configStore.mode,
  async () => {
    activeProjectId.value = ''
    boundProjectId.value = ''
    scanResult.value = null
    await fetchProjects()
  }
)

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

function handleProjectChange(val) {
  scanResult.value = null
  boundProjectId.value = val
  router.replace({ query: { ...route.query, project_id: val } })
}

function copyProjectId() {
  const pid = boundProjectId.value || activeProjectId.value
  if (pid) {
    navigator.clipboard.writeText(pid)
    ElMessage.success('已复制 Project ID: ' + pid)
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
  scanResult.value = null
}

// 执行安全检测
async function executeScan() {
  if (!promptText.value.trim()) {
    ElMessage.warning('请输入待检测的提示词文本')
    return
  }

  const targetProjectId = boundProjectId.value || activeProjectId.value || null

  scanning.value = true
  const startTime = performance.now()
  try {
    const res = await apiClient.post('/guardrails/scan', {
      prompt: promptText.value.trim(),
      project_id: targetProjectId
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

function openLogDrawer() {
  logDrawerVisible.value = true
}

// 格式转换与标签工具
function getTypeTag(type) {
  const map = { global: 'warning', chat: 'success', agentic: 'danger', app: 'primary' }
  return map[type] || 'info'
}

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
  if (!isoStr) return '-'
  try {
    const d = new Date(isoStr)
    return d.toLocaleTimeString('zh-CN', { hour12: false })
  } catch (e) {
    return isoStr
  }
}

watch(
  () => props.initialProjectId,
  (newId) => {
    if (newId) activeProjectId.value = newId
  }
)

onMounted(async () => {
  await fetchProjects()
  await fetchPresets()
})
</script>

<style scoped>
.playground-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
}

.project-scope-card {
  border-radius: 8px;
  background-color: #ffffff;
}

.project-scope-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.scope-left {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.scope-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: #0f172a;
  font-size: 14px;
}

.label-icon {
  color: #38bdf8;
}

.project-id-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  background-color: #f8fafc;
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.id-title {
  font-size: 12px;
  color: #64748b;
}

.id-tag {
  font-family: monospace;
  font-size: 12px;
}

.active-rules-bar {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed #e2e8f0;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.rules-bar-label {
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
}

.active-rules-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.rule-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
}

.no-rules-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #eab308;
  font-size: 12px;
}

.playground-layout {
  display: flex;
  gap: 16px;
  flex: 1;
  min-height: 560px;
}

.pane {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.pane-card {
  background-color: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  height: 100%;
}

.pane-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
}

.title-icon {
  color: #38bdf8;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.item-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.item-label {
  font-size: 13px;
  font-weight: 500;
  color: #334155;
}

.preset-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
}

.preset-desc-box {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
  background-color: #f8fafc;
  padding: 8px 10px;
  border-radius: 6px;
  margin-top: 4px;
}

.quick-tags-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.quick-label {
  font-size: 12px;
  color: #64748b;
}

.quick-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.quick-tag-btn {
  font-size: 11px;
  padding: 3px 8px;
  background-color: #f1f5f9;
  color: #475569;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.quick-tag-btn:hover {
  background-color: #e2e8f0;
  color: #0284c7;
}

.prompt-textarea :deep(.el-textarea__inner) {
  font-family: inherit;
  font-size: 13px;
  line-height: 1.6;
}

.submit-action-row {
  margin-top: auto;
}

.scan-btn {
  width: 100%;
}

/* 右栏结果样式 */
.result-placeholder-card,
.result-card {
  background-color: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

.result-placeholder-card {
  justify-content: center;
  align-items: center;
}

.placeholder-tip {
  font-size: 12px;
  color: #94a3b8;
  max-width: 440px;
  margin-top: 10px;
  line-height: 1.5;
}

.loading-card {
  justify-content: center;
  align-items: center;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.loading-icon {
  font-size: 32px;
  color: #38bdf8;
}

.loading-text {
  font-size: 15px;
  font-weight: 500;
  color: #0f172a;
}

.loading-sub {
  font-size: 12px;
  color: #64748b;
}

/* 决策大横幅 */
.decision-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px;
  border-radius: 8px;
  color: #ffffff;
}

.banner--cleared {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.banner--blocked {
  background: linear-gradient(135deg, #f43f5e 0%, #e11d48 100%);
}

.banner--redacted {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

.banner--flagged {
  background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%);
}

.decision-banner__left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.banner-icon-box {
  font-size: 28px;
}

.outcome-title {
  font-size: 17px;
  font-weight: 700;
}

.outcome-sub {
  font-size: 12px;
  opacity: 0.92;
  margin-top: 2px;
}

.decision-banner__meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  text-align: right;
  opacity: 0.9;
}

.meta-item {
  display: flex;
  flex-direction: column;
}

.meta-label {
  font-size: 11px;
  opacity: 0.8;
}

.meta-val {
  font-weight: 600;
}

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
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.sec-icon {
  color: #38bdf8;
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.no-scanners-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  background-color: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 6px;
  color: #166534;
  font-size: 13px;
}

.clean-icon {
  color: #16a34a;
  font-size: 16px;
}

.scanners-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.scanner-item {
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 10px 14px;
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
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.scanner-raw-id {
  font-size: 11px;
  color: #94a3b8;
  font-family: monospace;
}

.scanner-progress-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.progress-label {
  font-size: 12px;
  color: #64748b;
  width: 72px;
}

.progress-bar-wrap {
  flex: 1;
}

.scanner-reason {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 12px;
  background-color: #ffffff;
  padding: 6px 10px;
  border-radius: 4px;
}

.reason-label {
  color: #64748b;
  font-weight: 500;
}

.reason-text {
  color: #334155;
  line-height: 1.4;
}

.llm-response-box {
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 14px;
}

.llm-bubble {
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
  color: #1e293b;
  line-height: 1.6;
}

.mono-text {
  font-family: monospace;
  font-size: 12px;
}

.json-code {
  background-color: #0f172a;
  color: #38bdf8;
  padding: 12px;
  border-radius: 6px;
  font-size: 12px;
  overflow-x: auto;
  max-height: 380px;
}

.apply-project-btn {
  margin-left: 8px;
}

.target-project-status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  padding: 8px 14px;
  margin-bottom: 16px;
}

.target-project-status-bar .status-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.target-project-status-bar .status-label {
  font-size: 13px;
  font-weight: 600;
  color: #166534;
}

.target-project-status-bar .proj-id-code {
  font-size: 11px;
  color: #15803d;
  font-family: monospace;
  background: #dcfce7;
  padding: 2px 6px;
  border-radius: 4px;
}

/* 阻断拦截展示卡片 */
.llm-blocked-container {
  display: flex;
  flex-direction: column;
}

.interception-banner {
  background: #fff1f2;
  border: 1px solid #fecdd3;
  border-radius: 8px;
  overflow: hidden;
}

.interception-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #ffe4e6;
  border-bottom: 1px solid #fecdd3;
}

.interception-icon {
  font-size: 24px;
  color: #e11d48;
}

.interception-titles {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.interception-title {
  font-size: 14px;
  font-weight: 700;
  color: #9f1239;
}

.interception-sub {
  font-size: 12px;
  color: #be123c;
}

.interception-body {
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.interception-meta-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}

.interception-meta-item .meta-k {
  font-weight: 600;
  color: #475569;
  width: 90px;
}

.interception-meta-item .meta-v {
  color: #1e293b;
  font-family: monospace;
}

.interception-rules {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.interception-raw-text {
  margin-top: 6px;
  background: #ffffff;
  border: 1px solid #fda4af;
  border-radius: 6px;
  padding: 10px 14px;
  font-family: monospace;
  font-size: 12px;
  color: #9f1239;
}

.interception-raw-text pre {
  margin: 0;
  white-space: pre-wrap;
}

/* 正常放行大模型响应 */
.llm-model-info-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px dashed #cbd5e1;
}

.llm-reasoning-card {
  background: #f8fafc;
  border-left: 3px solid #8b5cf6;
  border-radius: 4px;
  padding: 10px 14px;
  margin-bottom: 12px;
}

.llm-reasoning-card .reasoning-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #7c3aed;
  margin-bottom: 4px;
}

.llm-reasoning-card .reasoning-text {
  font-size: 12px;
  color: #475569;
  line-height: 1.5;
  white-space: pre-wrap;
}

.project-select-opt {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
