<template>
  <div class="guardrails-logs-view">
    <!-- 筛选面板 -->
    <el-card class="filter-card" shadow="never">
      <div class="filter-bar">
        <div class="filter-inputs">
          <el-select
            v-model="selectedProjectId"
            placeholder="所属项目筛选"
            clearable
            style="width: 260px"
          >
            <el-option label="全部项目" value="" />
            <el-option
              v-for="p in projects"
              :key="p.id"
              :label="`${p.name} (${p.id.slice(0, 8)}...)`"
              :value="p.id"
            />
          </el-select>

          <el-select
            v-model="selectedOutcome"
            placeholder="检测判定结果"
            clearable
            style="width: 160px"
          >
            <el-option label="全部判定" value="" />
            <el-option label="合规通过 (Cleared)" value="cleared" />
            <el-option label="高危阻断 (Blocked)" value="blocked" />
            <el-option label="合规脱敏 (Redacted)" value="redacted" />
            <el-option label="预警标记 (Flagged)" value="flagged" />
          </el-select>
        </div>

        <div class="filter-actions">
          <el-button :icon="Refresh" @click="fetchLogs" :loading="loading">
            刷新流水
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 日志数据列表 -->
    <el-card class="table-card" shadow="never">
      <el-table
        :data="filteredLogs"
        v-loading="loading"
        style="width: 100%"
        border
        stripe
        row-key="id"
      >
        <el-table-column label="检测时间" width="170">
          <template #default="{ row }">
            <span class="time-text">{{ formatTime(row.receivedAt) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="所属项目" min-width="180">
          <template #default="{ row }">
            <div class="project-cell">
              <span class="project-name">{{ getProjectName(row.projectId) }}</span>
              <el-text class="project-id-sub" size="small" truncated>{{ row.projectId }}</el-text>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="检测裁定" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="getOutcomeTag(row.outcome)" effect="dark" size="small">
              {{ getOutcomeLabel(row.outcome) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="触发规则 / Scanners" min-width="200">
          <template #default="{ row }">
            <div class="triggered-tags" v-if="row.triggeredScanners?.length > 0">
              <el-tag
                v-for="(rule, idx) in row.triggeredScanners"
                :key="idx"
                size="small"
                type="danger"
                effect="plain"
                class="tag-item"
              >
                {{ rule }}
              </el-tag>
            </div>
            <span v-else class="text-muted">无命中 (全部规则合规放行)</span>
          </template>
        </el-table-column>

        <el-table-column label="输入提示词摘要" min-width="260" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="prompt-snippet">{{ row.input }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="110" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewDetail(row)">
              裁定详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 详情抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      title="Calypso Guardrails 检测裁定详情"
      size="50%"
      destroy-on-close
    >
      <div v-if="selectedRow" class="detail-container">
        <!-- 基本属性卡片 -->
        <el-descriptions title="基础元数据" :column="2" border size="small">
          <el-descriptions-item label="记录 ID">
            <el-text class="mono-text">{{ selectedRow.id }}</el-text>
          </el-descriptions-item>
          <el-descriptions-item label="所属项目">
            {{ getProjectName(selectedRow.projectId) }}
          </el-descriptions-item>
          <el-descriptions-item label="Project ID">
            <el-text class="mono-text">{{ selectedRow.projectId }}</el-text>
          </el-descriptions-item>
          <el-descriptions-item label="裁定动作">
            <el-tag :type="getOutcomeTag(selectedRow.outcome)" effect="dark" size="small">
              {{ getOutcomeLabel(selectedRow.outcome) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="扫描时间" :span="2">
            {{ formatTime(selectedRow.receivedAt) }}
          </el-descriptions-item>
        </el-descriptions>

        <!-- 输入与脱敏对比 -->
        <div class="section-title">提示词内容</div>
        <div class="content-box">
          <div class="box-label">原始输入 (Input):</div>
          <div class="box-content">{{ selectedRow.input }}</div>
          <div v-if="selectedRow.redactedInput && selectedRow.redactedInput !== selectedRow.input" class="redacted-wrap">
            <div class="box-label highlight">脱敏后内容 (Redacted):</div>
            <div class="box-content highlight-content">{{ selectedRow.redactedInput }}</div>
          </div>
        </div>

        <!-- 规则评估细目 -->
        <div class="section-title">规则判定明细 (Scanner Results)</div>
        <div class="scanner-results-list" v-if="getScannerResults(selectedRow).length > 0">
          <el-card
            v-for="(sr, idx) in getScannerResults(selectedRow)"
            :key="idx"
            class="scanner-card"
            shadow="never"
          >
            <div class="sr-header">
              <span class="sr-name">{{ sr.scannerVersionMeta?.name || sr.scannerName || sr.scannerId }}</span>
              <el-tag size="small" :type="sr.outcome === 'failed' ? 'danger' : 'success'">
                {{ sr.outcome === 'failed' ? '规则触发/拦截' : '规则校验通过' }}
              </el-tag>
            </div>
            <div class="sr-desc" v-if="sr.scannerVersionMeta?.description">
              {{ sr.scannerVersionMeta.description }}
            </div>
          </el-card>
        </div>
        <div v-else class="text-muted" style="padding: 10px 0;">
          无独立规则明细或未触发任何阻断。
        </div>

        <!-- 原始 JSON 数据 -->
        <div class="section-title">Calypso 原生返回报文 (Raw JSON)</div>
        <pre class="json-code"><code>{{ JSON.stringify(selectedRow, null, 2) }}</code></pre>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { getGuardrailsLogs } from '../../api/guardrails'
import { getProjects } from '../../api/projects'
import { useConfigStore } from '../../stores/config'

const props = defineProps({
  filterProjectId: {
    type: String,
    default: ''
  }
})

const configStore = useConfigStore()
const loading = ref(false)
const logs = ref([])
const projects = ref([])
const selectedProjectId = ref(props.filterProjectId || '')
const selectedOutcome = ref('')

const drawerVisible = ref(false)
const selectedRow = ref(null)

const fetchProjects = async () => {
  try {
    const res = await getProjects()
    projects.value = res.projects || []
  } catch (e) {
    console.error(e)
  }
}

const fetchLogs = async () => {
  loading.value = true
  try {
    const params = { limit: 50 }
    if (selectedProjectId.value) params.project_id = selectedProjectId.value
    if (selectedOutcome.value) params.outcomes = selectedOutcome.value
    const res = await getGuardrailsLogs(params)
    logs.value = res.logs || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

watch(
  () => [selectedProjectId.value, selectedOutcome.value],
  () => {
    fetchLogs()
  }
)

watch(
  () => props.filterProjectId,
  (newVal) => {
    selectedProjectId.value = newVal || ''
  }
)

watch(
  () => configStore.mode,
  async () => {
    await fetchProjects()
    await fetchLogs()
  }
)


const filteredLogs = computed(() => {
  return logs.value.filter((l) => {
    if (selectedProjectId.value && l.projectId !== selectedProjectId.value) return false
    if (selectedOutcome.value && l.outcome !== selectedOutcome.value) return false
    return true
  })
})

const getProjectName = (projId) => {
  const p = projects.value.find((item) => item.id === projId)
  return p ? p.name : projId ? `项目 (${projId.slice(0, 8)}...)` : '通用全局空间'
}

const getOutcomeLabel = (outcome) => {
  const map = {
    cleared: '合规通过',
    blocked: '高危阻断',
    redacted: '脱敏替换',
    flagged: '标记预警'
  }
  return map[outcome] || outcome || '未知'
}

const getOutcomeTag = (outcome) => {
  const map = {
    cleared: 'success',
    blocked: 'danger',
    redacted: 'warning',
    flagged: 'info'
  }
  return map[outcome] || 'info'
}

const formatTime = (isoString) => {
  if (!isoString) return '-'
  try {
    const d = new Date(isoString)
    return d.toLocaleString('zh-CN', { hour12: false })
  } catch (e) {
    return isoString
  }
}

const getScannerResults = (row) => {
  return row?.result?.scannerResults || []
}

const viewDetail = (row) => {
  selectedRow.value = row
  drawerVisible.value = true
}

onMounted(async () => {
  await fetchProjects()
  await fetchLogs()
})
</script>

<style scoped>
.guardrails-logs-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filter-card {
  border-radius: 8px;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.filter-inputs,
.filter-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.table-card {
  border-radius: 8px;
}

.time-text {
  font-size: 13px;
  color: #64748b;
}

.project-cell {
  display: flex;
  flex-direction: column;
}

.project-name {
  font-weight: 500;
  color: #1e293b;
}

.project-id-sub {
  font-family: monospace;
  font-size: 11px;
  color: #94a3b8;
}

.triggered-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-item {
  font-size: 11px;
}

.prompt-snippet {
  font-size: 13px;
  color: #334155;
}

.text-muted {
  color: #94a3b8;
  font-size: 12px;
}

.detail-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.mono-text {
  font-family: monospace;
  font-size: 12px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  border-left: 3px solid #38bdf8;
  padding-left: 8px;
  margin-top: 10px;
}

.content-box {
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 12px;
}

.box-label {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
  font-weight: 500;
}

.box-label.highlight {
  color: #d97706;
  margin-top: 10px;
}

.box-content {
  font-size: 13px;
  color: #1e293b;
  line-height: 1.5;
  white-space: pre-wrap;
}

.highlight-content {
  color: #b45309;
  background-color: #fef3c7;
  padding: 6px 10px;
  border-radius: 4px;
}

.scanner-results-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.scanner-card {
  border-radius: 6px;
}

.sr-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sr-name {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}

.sr-desc {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
}

.json-code {
  background-color: #0f172a;
  color: #38bdf8;
  padding: 12px;
  border-radius: 6px;
  font-size: 12px;
  overflow-x: auto;
  max-height: 260px;
}
</style>
