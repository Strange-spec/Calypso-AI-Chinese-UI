<template>
  <div class="audit-view">
    <!-- 顶部说明条 -->
    <div class="audit-header">
      <div class="header-intro">
        <h2 class="view-title">安全合规与审计事件日志 (Audit Logs)</h2>
        <span class="view-desc">
          追溯经由 Calypso AI 护栏网关拦截与放行的每一笔大模型调用记录，包括请求 Prompt、触发策略明细、客户端信息与脱敏快照。
        </span>
      </div>

      <div class="header-actions">
        <el-button type="primary" plain :loading="loading" @click="fetchLogs">
          <el-icon><Refresh /></el-icon>
          <span>刷新日志</span>
        </el-button>
      </div>
    </div>

    <!-- 筛选搜索栏 -->
    <div class="filter-card">
      <div class="filter-row">
        <!-- 业务项目筛选 -->
        <div class="filter-item">
          <span class="filter-label">业务项目:</span>
          <el-select
            v-model="selectedProjectId"
            placeholder="全部项目"
            clearable
            style="width: 220px"
            @change="handleFilterChange"
          >
            <el-option label="全部业务项目" value="" />
            <el-option
              v-for="p in projectsList"
              :key="p.id"
              :label="`${p.name}`"
              :value="p.id"
            />
          </el-select>
        </div>

        <!-- 判定结果筛选 -->
        <div class="filter-item">
          <span class="filter-label">判定结果:</span>
          <el-radio-group v-model="filterOutcome" size="default" @change="handleFilterChange">
            <el-radio-button label="">全部记录</el-radio-button>
            <el-radio-button label="cleared">放行通过</el-radio-button>
            <el-radio-button label="blocked">阻断拦截</el-radio-button>
            <el-radio-button label="redacted">敏感脱敏</el-radio-button>
          </el-radio-group>
        </div>

        <!-- 关键词搜索 -->
        <div class="filter-item search-item">
          <el-input
            v-model="searchKeyword"
            placeholder="按 Prompt 内容、客户端 IP 或日志 ID 快速搜索..."
            clearable
            prefix-icon="Search"
            @input="handleSearch"
          />
        </div>
      </div>
    </div>

    <!-- 日志表格区 -->
    <div class="table-card">
      <el-table
        v-loading="loading"
        :data="filteredLogs"
        border
        stripe
        class="audit-table"
        row-key="id"
      >
        <el-table-column prop="timestamp" label="记录时间" width="170">
          <template #default="{ row }">
            <span class="time-col">{{ formatDateTime(row.timestamp) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="所属业务项目" min-width="160">
          <template #default="{ row }">
            <div class="project-cell">
              <span class="project-title">{{ row.project_name || getProjectName(row.project_id) }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="outcome" label="判定动作" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="getOutcomeTagType(row.outcome)" size="small" effect="light">
              {{ formatOutcome(row.outcome) }}
            </el-tag>
          </template>
        </el-table-column>


        <el-table-column prop="prompt" label="提示词内容摘要 (Prompt Snippet)" min-width="260">
          <template #default="{ row }">
            <el-tooltip :content="row.prompt" placement="top-start" :show-after="400">
              <span class="prompt-snippet">{{ row.prompt }}</span>
            </el-tooltip>
          </template>
        </el-table-column>

        <el-table-column label="触发扫描器 (Triggered Scanners)" min-width="200">
          <template #default="{ row }">
            <div v-if="row.triggered_scanners?.length" class="scanners-tag-list">
              <el-tag
                v-for="(sc, scIdx) in row.triggered_scanners"
                :key="scIdx"
                size="small"
                :type="row.outcome === 'blocked' ? 'danger' : 'warning'"
                effect="plain"
                class="scanner-tag"
              >
                {{ sc.title || sc.name }}
              </el-tag>
            </div>
            <span v-else class="text-cleared">无违规规则命中</span>
          </template>
        </el-table-column>

        <el-table-column prop="client_ip" label="客户端 IP" width="140" align="center">
          <template #default="{ row }">
            <span class="ip-text">{{ row.client_ip || '127.0.0.1' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openDetailDrawer(row)">
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 底部分页器 -->
      <div class="pagination-footer">
        <span class="page-info">共 {{ total }} 条审计记录</span>
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </div>

    <!-- 日志详情抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      title="安全审计日志详情 (Audit Log Details)"
      size="560px"
      direction="rtl"
      destroy-on-close
    >
      <div v-if="selectedLog" class="drawer-content">
        <!-- 基础元数据栏 -->
        <div class="detail-section">
          <div class="section-title">基础事件信息</div>
          <el-descriptions :column="1" border size="small" class="detail-descriptions">
            <el-descriptions-item label="日志编号 (ID)">
              <code>{{ selectedLog.id }}</code>
            </el-descriptions-item>
            <el-descriptions-item label="记录时间">
              {{ formatDateTime(selectedLog.timestamp) }}
            </el-descriptions-item>
            <el-descriptions-item label="判定动作">
              <el-tag :type="getOutcomeTagType(selectedLog.outcome)">
                {{ formatOutcome(selectedLog.outcome) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="风险等级">
              <el-tag :type="getRiskTagType(selectedLog.risk_level)">
                {{ (selectedLog.risk_level || 'low').toUpperCase() }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="客户端 IP">
              {{ selectedLog.client_ip || '127.0.0.1' }}
            </el-descriptions-item>
            <el-descriptions-item label="所属项目">
              {{ selectedLog.project_id || '默认项目' }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 原始 Prompt -->
        <div class="detail-section">
          <div class="section-title-bar">
            <span class="section-title">原始提示词 (Raw Prompt)</span>
            <el-button link type="primary" size="small" @click="copyText(selectedLog.prompt, 'Prompt 已复制')">
              <el-icon><CopyDocument /></el-icon>
              复制
            </el-button>
          </div>
          <div class="code-box prompt-box">
            {{ selectedLog.prompt }}
          </div>
        </div>

        <!-- 脱敏后文本（如果存在脱敏） -->
        <div v-if="selectedLog.redacted_prompt && selectedLog.redacted_prompt !== selectedLog.prompt" class="detail-section">
          <div class="section-title-bar">
            <span class="section-title">脱敏后文本 (Redacted Content)</span>
            <el-button link type="success" size="small" @click="copyText(selectedLog.redacted_prompt, '脱敏文本已复制')">
              <el-icon><CopyDocument /></el-icon>
              复制
            </el-button>
          </div>
          <div class="code-box redacted-box">
            {{ selectedLog.redacted_prompt }}
          </div>
        </div>

        <!-- 触发策略规则 JSON 明细 -->
        <div class="detail-section">
          <div class="section-title-bar">
            <span class="section-title">触发扫描器详细参数 (Rule Payload JSON)</span>
            <el-button link type="primary" size="small" @click="copyText(formattedJson(selectedLog.triggered_scanners), 'JSON 已复制')">
              <el-icon><CopyDocument /></el-icon>
              复制 JSON
            </el-button>
          </div>
          <pre class="json-code-block">{{ formattedJson(selectedLog.triggered_scanners || []) }}</pre>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import apiClient from '../api/client'
import { getProjects } from '../api/projects'
import { useConfigStore } from '../stores/config'

const configStore = useConfigStore()
const loading = ref(false)
const logs = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const filterOutcome = ref('')
const selectedProjectId = ref('')
const searchKeyword = ref('')
const projectsList = ref([])

const drawerVisible = ref(false)
const selectedLog = ref(null)

async function fetchProjects() {
  try {
    const res = await getProjects()
    projectsList.value = res.projects || []
  } catch (err) {
    console.error('获取项目列表失败:', err)
  }
}

function getProjectName(pid) {
  if (!pid) return '通用全局项目'
  const found = projectsList.value.find((p) => p.id === pid)
  return found ? found.name : pid.slice(0, 8) + '...'
}

// 客户端搜索过滤
const filteredLogs = computed(() => {
  if (!searchKeyword.value.trim()) return logs.value
  const kw = searchKeyword.value.trim().toLowerCase()
  return logs.value.filter((item) => {
    return (
      (item.prompt && item.prompt.toLowerCase().includes(kw)) ||
      (item.client_ip && item.client_ip.toLowerCase().includes(kw)) ||
      (item.id && item.id.toLowerCase().includes(kw))
    )
  })
})

// 获取审计日志
async function fetchLogs() {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (filterOutcome.value) {
      params.outcome = filterOutcome.value
    }
    if (selectedProjectId.value) {
      params.project_id = selectedProjectId.value
    }

    const res = await apiClient.get('/audit/logs', { params })
    if (res && res.items) {
      logs.value = res.items
      total.value = res.total || 0
    }
  } catch (err) {
    console.error('获取审计日志失败:', err)
  } finally {
    loading.value = false
  }
}

function handleFilterChange() {
  currentPage.value = 1
  fetchLogs()
}


function handleSearch() {
  // 搜索仅在前端当前页过滤，重置无需额外请求
}

function handleSizeChange(newSize) {
  pageSize.value = newSize
  currentPage.value = 1
  fetchLogs()
}

function handlePageChange(newPage) {
  currentPage.value = newPage
  fetchLogs()
}

function openDetailDrawer(row) {
  selectedLog.value = row
  drawerVisible.value = true
}

// 格式化函数
function formatDateTime(isoStr) {
  if (!isoStr) return '-'
  try {
    const d = new Date(isoStr)
    return d.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  } catch {
    return isoStr
  }
}

function formatOutcome(outcome) {
  const map = {
    blocked: '阻断拦截',
    cleared: '放行通过',
    redacted: '敏感脱敏',
    flagged: '标记审计'
  }
  return map[outcome] || outcome || '未知'
}

function getOutcomeTagType(outcome) {
  const map = {
    blocked: 'danger',
    cleared: 'success',
    redacted: 'warning',
    flagged: 'info'
  }
  return map[outcome] || 'info'
}

function getRiskTagType(risk) {
  const map = {
    high: 'danger',
    medium: 'warning',
    low: 'success'
  }
  return map[risk] || 'info'
}

function formattedJson(data) {
  try {
    return JSON.stringify(data, null, 2)
  } catch {
    return String(data)
  }
}

function copyText(text, successMsg = '已复制') {
  if (!text) return
  navigator.clipboard.writeText(text).then(() => {
    ElMessage.success(successMsg)
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

onMounted(async () => {
  await fetchProjects()
  await fetchLogs()
})

watch(
  () => configStore.mode,
  async () => {
    selectedProjectId.value = ''
    await fetchProjects()
    await fetchLogs()
  }
)
</script>


<style scoped>
.audit-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.audit-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #ffffff;
  padding: 16px 20px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
}

.header-intro {
  display: flex;
  flex-direction: column;
  gap: 4px;
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
}

/* 过滤栏 */
.filter-card {
  background: #ffffff;
  padding: 14px 20px;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
}

.filter-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.filter-label {
  font-size: 13px;
  font-weight: 500;
  color: #475569;
  white-space: nowrap;
}

.search-item {
  flex: 1;
  max-width: 400px;
}

/* 表格卡片 */
.table-card {
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.time-col {
  font-size: 12px;
  color: #64748b;
  font-family: monospace;
}

.prompt-snippet {
  font-size: 13px;
  color: #1e293b;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.5;
}

.scanners-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.scanner-tag {
  font-size: 11px;
}

.text-cleared {
  font-size: 12px;
  color: #10b981;
}

.ip-text {
  font-family: monospace;
  font-size: 12px;
  color: #64748b;
}

.pagination-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 10px;
  border-top: 1px solid #f1f5f9;
}

.page-info {
  font-size: 13px;
  color: #64748b;
}

/* 详情抽屉 */
.drawer-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.detail-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-title-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}

.code-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 12px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 180px;
  overflow-y: auto;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
}

.prompt-box {
  color: #1e293b;
}

.redacted-box {
  color: #b45309;
  background-color: #fefce8;
  border-color: #fef08a;
}

.json-code-block {
  margin: 0;
  padding: 12px;
  background: #0f172a;
  color: #f8fafc;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.5;
  overflow-x: auto;
  max-height: 240px;
  font-family: Consolas, Monaco, "Courier New", monospace;
}
</style>
