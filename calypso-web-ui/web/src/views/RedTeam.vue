<template>
  <div class="redteam-view">
    <!-- 头部信息 -->
    <div class="redteam-header">
      <div class="header-intro">
        <h2 class="view-title">红队对抗评估与安全报告 (Red Team Campaigns & Reports)</h2>
        <span class="view-desc">
          自动化攻防对抗评估，追踪评估报告生命周期状态、测试进度、CASI 安全得分及 Calypso 原生 Raw Data 原始报文。
        </span>
      </div>

      <div class="header-actions">
        <!-- 载入内置宝马测试集 -->
        <el-button
          type="primary"
          :loading="loadingSample"
          @click="loadSampleReport"
        >
          <el-icon><Star /></el-icon>
          <span>载入宝马评估样本 (BMW Agentic Test)</span>
        </el-button>

        <!-- 导入 CSV 报告 -->
        <el-button plain @click="csvDialogVisible = true">
          <el-icon><UploadFilled /></el-icon>
          <span>导入评估 CSV</span>
        </el-button>

        <!-- 刷新报告列表 -->
        <el-button plain :loading="loadingReports" @click="fetchReports">
          <el-icon><Refresh /></el-icon>
          <span>刷新报告</span>
        </el-button>
      </div>
    </div>

    <!-- 顶部 5 大核心红队态势指标卡 -->
    <div class="metrics-grid">
      <MetricCard
        title="评估报告总数"
        :value="summaryMetrics.total_reports"
        unit="份"
        icon="Document"
        icon-bg="#eff6ff"
        icon-color="#2563eb"
        tooltip="当前模式下已执行或正在执行的红队攻防对抗评估报告总数"
        type="primary"
      />

      <MetricCard
        title="对抗测试总用例"
        :value="summaryMetrics.total_tests"
        unit="次"
        icon="Aim"
        icon-bg="#f0fdf4"
        icon-color="#16a34a"
        tooltip="红队任务中向受测模型发送的测试载荷与攻击用例总量"
        type="success"
      />

      <MetricCard
        title="平均 CASI 安全得分"
        :value="summaryMetrics.avg_casi"
        unit="分"
        :precision="1"
        icon="Odometer"
        icon-bg="#faf5ff"
        icon-color="#9333ea"
        tooltip="Calypso 对抗安全指数 (0-100 分，分值越高表示模型抵御对抗越安全)"
        type="primary"
      />

      <MetricCard
        title="模型失陷穿透数"
        :value="summaryMetrics.vulnerable_count"
        unit="例"
        icon="WarningFilled"
        icon-bg="#fef2f2"
        icon-color="#dc2626"
        :invert-trend-color="true"
        tooltip="未能成功防御恶意越狱或违规诱导的失陷样本总量"
        type="danger"
      />

      <MetricCard
        title="综合穿透失陷率"
        :value="summaryMetrics.vulnerability_rate"
        unit="%"
        :precision="2"
        icon="CircleCloseFilled"
        icon-bg="#fffbeb"
        icon-color="#d97706"
        :invert-trend-color="true"
        tooltip="失陷样本数占总测试样本比例 (越低越安全)"
        type="warning"
      />
    </div>

    <!-- 核心主体一：红队对抗评估报告清单 (Evaluation Reports List) -->
    <div class="reports-section-card">
      <div class="reports-section__header">
        <div class="header-left">
          <div class="section-title">
            <el-icon class="title-icon"><List /></el-icon>
            <span>红队对抗评估报告清单 (Evaluation Reports)</span>
          </div>
          <span class="report-count-tag">共 {{ filteredReports.length }} 份报告</span>
        </div>

        <div class="header-filters">
          <!-- 所属活动过滤 -->
          <el-select
            v-model="selectedCampaignFilter"
            placeholder="所属红队活动"
            clearable
            size="default"
            style="width: 180px;"
            @change="handleFilterChange"
          >
            <el-option label="全部活动" value="" />
            <el-option
              v-for="c in uniqueCampaigns"
              :key="c.id"
              :label="c.name"
              :value="c.id"
            />
          </el-select>

          <!-- 关键字搜索 -->
          <el-input
            v-model="searchKeyword"
            placeholder="搜索报告名称 / 靶标..."
            clearable
            size="default"
            style="width: 200px;"
            :prefix-icon="Search"
            @input="handleFilterChange"
          />
        </div>
      </div>

      <!-- 状态筛选切换栏 -->
      <div class="status-tabs-row">
        <el-radio-group v-model="selectedStatusFilter" size="small" @change="handleFilterChange">
          <el-radio-button label="all">全部报告</el-radio-button>
          <el-radio-button label="complete">
            <span class="status-tab-text status-tab-text--complete">已完成 (Complete)</span>
          </el-radio-button>
          <el-radio-button label="running">
            <span class="status-tab-text status-tab-text--running">运行中 (Running)</span>
          </el-radio-button>
          <el-radio-button label="cancelling">
            <span class="status-tab-text status-tab-text--cancelling">正在取消 (Cancelling)</span>
          </el-radio-button>
          <el-radio-button label="cancelled">
            <span class="status-tab-text status-tab-text--cancelled">已取消 (Cancelled)</span>
          </el-radio-button>
          <el-radio-button label="error">
            <span class="status-tab-text status-tab-text--error">执行异常 (Error)</span>
          </el-radio-button>
        </el-radio-group>
      </div>

      <!-- 核心报告表格 -->
      <el-table
        :data="filteredReports"
        v-loading="loadingReports"
        border
        stripe
        class="custom-table reports-table"
        highlight-current-row
        @current-change="handleRowClick"
      >
        <el-table-column prop="name" label="评估报告名称" min-width="210">
          <template #default="{ row }">
            <div class="report-name-cell">
              <el-icon class="report-icon"><Document /></el-icon>
              <div class="report-name-meta">
                <span class="report-main-name">{{ row.name }}</span>
                <span class="report-id-sub">ID: {{ row.id }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="campaign_name" label="所属红队活动" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="campaign-tag-text">{{ row.campaign_name || '红队评估活动' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="target" label="受测靶标" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <el-tag size="small" effect="plain" type="info">{{ row.target || 'GPT-4o Enterprise' }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="评估状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusTagType(row.status)" size="small" effect="light">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="casi_score" label="CASI 得分" width="110" align="center">
          <template #default="{ row }">
            <el-tag
              :type="row.casi_score >= 80 ? 'success' : (row.casi_score >= 65 ? 'warning' : 'danger')"
              size="small"
              effect="dark"
              class="casi-score-tag"
            >
              {{ row.casi_score || 0 }} 分
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="progress" label="测试用例进度" min-width="190">
          <template #default="{ row }">
            <div class="progress-cell">
              <div class="progress-text">
                <span>{{ (row.progress || 0).toLocaleString() }} / {{ (row.total || 0).toLocaleString() }}</span>
                <span class="progress-percent">{{ calculatePercent(row.progress, row.total) }}%</span>
              </div>
              <el-progress
                :percentage="calculatePercent(row.progress, row.total)"
                :status="row.status === 'error' ? 'exception' : (row.status === 'cancelling' ? 'warning' : 'success')"
                :stroke-width="6"
                :show-text="false"
              />
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="生成时间" width="160" align="center">
          <template #default="{ row }">
            <span class="timestamp-text">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="220" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              link
              size="small"
              :icon="DataAnalysis"
              @click.stop="selectReportForAnalysis(row)"
            >
              查看分析
            </el-button>
            <el-button
              type="warning"
              link
              size="small"
              :icon="Document"
              @click.stop="viewReportRawData(row)"
            >
              查看 Raw Data
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 核心主体二：选定报告深度分析看板 (Deep-Dive Analysis) -->
    <div v-if="activeAnalysis" class="analysis-card">
      <div class="analysis-card__header">
        <div class="analysis-title-group">
          <span class="analysis-badge">深度分析看板</span>
          <h3 class="analysis-title">{{ activeAnalysis.campaign || '选定报告对抗评估分析' }}</h3>
          <span v-if="activeAnalysis.target" class="analysis-target">
            靶标: {{ activeAnalysis.target }}
          </span>
          <el-tag v-if="activeAnalysis.status" :type="getStatusTagType(activeAnalysis.status)" size="small">
            {{ getStatusLabel(activeAnalysis.status) }}
          </el-tag>
        </div>

        <div class="analysis-actions">
          <el-button
            type="success"
            plain
            size="default"
            :loading="exportingReport"
            @click="exportReportMarkdown"
          >
            <el-icon><Download /></el-icon>
            <span>导出中文分析报告 (Markdown)</span>
          </el-button>
        </div>
      </div>

      <!-- 图表双栏：手法穿透率排行柱状图 + 严重度分布/饼图 -->
      <div class="analysis-charts-row">
        <!-- 穿透手法水平柱状图 -->
        <div class="chart-box chart-box--bar">
          <div class="chart-box__title">
            <el-icon class="chart-icon"><Histogram /></el-icon>
            <span>攻击向量与对抗手法穿透率排行 (Penetration Rate %)</span>
          </div>
          <div ref="techniqueChartRef" class="echart-container"></div>
        </div>

        <!-- 漏洞严重度饼图 -->
        <div class="chart-box chart-box--pie">
          <div class="chart-box__title">
            <el-icon class="chart-icon"><PieChart /></el-icon>
            <span>失陷威胁严重度分布 (Severity Breakdown)</span>
          </div>
          <div ref="severityChartRef" class="echart-container"></div>
        </div>
      </div>

      <!-- 易受攻击手法明细表格 -->
      <div class="techniques-table-wrap">
        <div class="table-header-row">
          <div class="table-title">
            <span>对抗技术暴露明细 (Techniques Breakdown)</span>
            <span class="table-count">共 {{ techniqueList.length }} 种手法</span>
          </div>
          <div class="table-filters">
            <el-radio-group v-model="techniqueFilter" size="small">
              <el-radio-button label="all">全部手法</el-radio-button>
              <el-radio-button label="vulnerable">仅查看有穿透 (失陷 > 0)</el-radio-button>
            </el-radio-group>
          </div>
        </div>

        <el-table
          :data="filteredTechniques"
          border
          stripe
          class="custom-table"
          max-height="320"
        >
          <el-table-column prop="technique" label="攻击手法 / 混淆转换器" min-width="220">
            <template #default="{ row }">
              <span class="tech-name">{{ row.technique || row.converter || row.vector }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="total" label="测试用例数" width="130" align="center">
            <template #default="{ row }">
              <span>{{ row.total?.toLocaleString() }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="vulnerable" label="失陷穿透数" width="130" align="center">
            <template #default="{ row }">
              <el-tag :type="row.vulnerable > 0 ? 'danger' : 'success'" size="small">
                {{ row.vulnerable?.toLocaleString() }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="refused" label="成功防御" width="130" align="center">
            <template #default="{ row }">
              <span class="text-success">{{ row.refused?.toLocaleString() || '-' }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="rate" label="穿透失陷率" width="160" align="center">
            <template #default="{ row }">
              <div class="table-rate-bar">
                <el-progress
                  :percentage="Math.min(100, Math.round(row.rate || 0))"
                  :status="row.rate > 15 ? 'exception' : (row.rate > 5 ? 'warning' : 'success')"
                  :stroke-width="6"
                />
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 报告 Raw Data 抽屉 (全高展示 Calypso 原生完整数据) -->
    <el-drawer
      v-model="rawDrawerVisible"
      title="Calypso 评估报告 Raw Data 原始数据"
      size="55%"
      destroy-on-close
    >
      <div v-if="selectedRawReport" class="drawer-content-wrap">
        <el-descriptions title="报告运行概要 (Report Run Summary)" :column="2" border size="small">
          <el-descriptions-item label="报告名称">
            <strong>{{ selectedRawReport.name }}</strong>
          </el-descriptions-item>
          <el-descriptions-item label="运行 ID">
            <el-text class="mono-text">{{ selectedRawReport.id }}</el-text>
          </el-descriptions-item>
          <el-descriptions-item label="所属活动">
            {{ selectedRawReport.campaign_name || '红队评估' }}
          </el-descriptions-item>
          <el-descriptions-item label="受测靶标">
            {{ selectedRawReport.target || 'GPT-4o Enterprise' }}
          </el-descriptions-item>
          <el-descriptions-item label="评估状态">
            <el-tag :type="getStatusTagType(selectedRawReport.status)" size="small">
              {{ getStatusLabel(selectedRawReport.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="CASI 安全得分">
            <el-tag size="small" type="success" effect="dark">{{ selectedRawReport.casi_score || 80 }} 分</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="用例总数">
            {{ (selectedRawReport.total || 0).toLocaleString() }} 题
          </el-descriptions-item>
          <el-descriptions-item label="完成进度">
            {{ (selectedRawReport.progress || 0).toLocaleString() }} 题
          </el-descriptions-item>
        </el-descriptions>

        <div class="raw-actions-bar">
          <span class="raw-bar-title">Calypso 原生 JSON 原始报文 (Raw Payload)</span>
          <div class="raw-btn-group">
            <el-button size="small" type="primary" link icon="CopyDocument" @click="copyRawData">
              复制原始 JSON
            </el-button>
            <el-button size="small" type="success" link icon="Download" @click="downloadRawJson">
              下载 JSON 文件
            </el-button>
          </div>
        </div>

        <div class="json-code-container" v-loading="loadingRaw">
          <pre class="json-code"><code>{{ JSON.stringify(selectedRawData, null, 2) }}</code></pre>
        </div>
      </div>
    </el-drawer>

    <!-- 导入 CSV 报告 对话框 -->
    <el-dialog
      v-model="csvDialogVisible"
      title="导入红队评估 CSV 报告"
      width="560px"
      destroy-on-close
    >
      <div class="upload-area-wrap">
        <el-upload
          class="csv-uploader"
          drag
          action="#"
          :auto-upload="false"
          :show-file-list="false"
          :on-change="handleFileChange"
          accept=".csv"
        >
          <el-icon class="upload-icon"><DocumentAdd /></el-icon>
          <div class="upload-text">
            将红队评估 CSV 拖至此处，或<em>点击上传</em>
          </div>
          <template #tip>
            <div class="upload-tip">
              支持 Calypso / BMW 标准导出的 CSV，自动识别 campaign, connection, attackVector, attackTechnique, vulnerable, refused, severity 等字段。
            </div>
          </template>
        </el-upload>

        <div v-if="uploading" class="upload-loading">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>正在解析 CSV 报告数据...</span>
        </div>
      </div>
    </el-dialog>

    <!-- 报告预览与下载对话框 -->
    <el-dialog
      v-model="reportDialogVisible"
      title="中文红队对抗安全评估报告 (Markdown)"
      width="70%"
      destroy-on-close
    >
      <div class="markdown-preview-box">
        <el-input
          v-model="exportedMarkdown"
          type="textarea"
          :rows="16"
          readonly
          class="markdown-textarea"
        />
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="copyReport">
            <el-icon><CopyDocument /></el-icon>
            复制全文
          </el-button>
          <el-button type="primary" @click="downloadReportFile">
            <el-icon><Download /></el-icon>
            下载 .md 报告文件
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import {
  Search,
  Document,
  DataAnalysis,
  Star,
  UploadFilled,
  Refresh,
  Aim,
  WarningFilled,
  CircleCheckFilled,
  CircleCloseFilled,
  Odometer,
  List,
  Download,
  Histogram,
  PieChart,
  DocumentAdd,
  Loading,
  CopyDocument
} from '@element-plus/icons-vue'
import apiClient from '../api/client'
import { useConfigStore } from '../stores/config'
import MetricCard from '../components/MetricCard.vue'

const configStore = useConfigStore()

// 状态与加载指示
const loadingReports = ref(false)
const loadingSample = ref(false)
const uploading = ref(false)
const exportingReport = ref(false)
const reportDialogVisible = ref(false)
const csvDialogVisible = ref(false)
const exportedMarkdown = ref('')

// Raw Data 抽屉状态
const rawDrawerVisible = ref(false)
const selectedRawReport = ref(null)
const selectedRawData = ref(null)
const loadingRaw = ref(false)

// 报告清单与筛选
const reportsList = ref([])
const activeAnalysis = ref(null)
const selectedStatusFilter = ref('all')
const selectedCampaignFilter = ref('')
const searchKeyword = ref('')
const techniqueFilter = ref('all')

// 图表 DOM 与实例
const techniqueChartRef = ref(null)
const severityChartRef = ref(null)
let techniqueChartInstance = null
let severityChartInstance = null

// 计算顶部 5 大指标统计
const summaryMetrics = computed(() => {
  const list = reportsList.value || []
  const totalReports = list.length
  let totalTests = 0
  let vulnerableCount = 0
  let refusedCount = 0
  let casiSum = 0

  list.forEach((r) => {
    totalTests += r.total || 0
    vulnerableCount += r.vulnerable_count || Math.round((r.total || 0) * (r.vulnerability_rate || 0) / 100)
    refusedCount += r.refused_count || ((r.total || 0) - (r.vulnerable_count || 0))
    casiSum += r.casi_score || 0
  })

  const avgCasi = totalReports > 0 ? (casiSum / totalReports) : 80
  const overallRate = totalTests > 0 ? ((vulnerableCount / totalTests) * 100) : 0

  return {
    total_reports: totalReports,
    total_tests: totalTests,
    avg_casi: avgCasi,
    vulnerable_count: vulnerableCount,
    refused_count: refusedCount,
    vulnerability_rate: overallRate
  }
})

// 提取唯一活动列表
const uniqueCampaigns = computed(() => {
  const map = new Map()
  reportsList.value.forEach((r) => {
    if (r.campaign_id && !map.has(r.campaign_id)) {
      map.set(r.campaign_id, { id: r.campaign_id, name: r.campaign_name || r.campaign_id })
    }
  })
  return Array.from(map.values())
})

// 过滤后的报告列表
const filteredReports = computed(() => {
  return reportsList.value.filter((r) => {
    // 状态过滤
    if (selectedStatusFilter.value !== 'all' && r.status !== selectedStatusFilter.value) {
      return false
    }
    // 活动过滤
    if (selectedCampaignFilter.value && r.campaign_id !== selectedCampaignFilter.value) {
      return false
    }
    // 关键字搜索
    if (searchKeyword.value) {
      const q = searchKeyword.value.toLowerCase().trim()
      const matchName = (r.name || '').toLowerCase().includes(q)
      const matchTarget = (r.target || '').toLowerCase().includes(q)
      const matchCampaign = (r.campaign_name || '').toLowerCase().includes(q)
      if (!matchName && !matchTarget && !matchCampaign) return false
    }
    return true
  })
})

// 状态标签映射
function getStatusTagType(status) {
  switch (status) {
    case 'complete': return 'success'
    case 'running': return 'primary'
    case 'cancelling': return 'warning'
    case 'cancelled': return 'info'
    case 'error': return 'danger'
    default: return 'info'
  }
}

function getStatusLabel(status) {
  switch (status) {
    case 'complete': return '已完成'
    case 'running': return '运行中'
    case 'cancelling': return '正在取消'
    case 'cancelled': return '已取消'
    case 'error': return '执行异常'
    default: return status || '未知'
  }
}

function calculatePercent(progress, total) {
  if (!total || total <= 0) return 0
  return Math.min(100, Math.round(((progress || 0) / total) * 100))
}

function formatTime(isoStr) {
  if (!isoStr) return '-'
  try {
    const d = new Date(isoStr)
    if (isNaN(d.getTime())) return isoStr
    return d.toLocaleString('zh-CN', { hour12: false })
  } catch (e) {
    return isoStr
  }
}

// 技术手法列表
const techniqueList = computed(() => {
  if (!activeAnalysis.value) return []
  return (
    activeAnalysis.value.attack_technique_breakdown ||
    activeAnalysis.value.attack_vector_breakdown ||
    activeAnalysis.value.converter_breakdown ||
    []
  )
})

// 过滤手法
const filteredTechniques = computed(() => {
  if (techniqueFilter.value === 'vulnerable') {
    return techniqueList.value.filter((t) => (t.vulnerable || 0) > 0)
  }
  return techniqueList.value
})

function handleResize() {
  if (techniqueChartInstance) techniqueChartInstance.resize()
  if (severityChartInstance) severityChartInstance.resize()
}

function handleFilterChange() {
  // 筛选发生改变时可做响应
}

function handleRowClick(row) {
  if (row) {
    selectReportForAnalysis(row)
  }
}

// 获取报告列表 (生产/演示自适应)
async function fetchReports() {
  loadingReports.value = true
  try {
    const res = await apiClient.get('/redteam/reports')
    if (res && res.reports) {
      reportsList.value = res.reports
      // 默认选中第一个报告并渲染分析看板
      if (res.reports.length > 0 && !activeAnalysis.value) {
        selectReportForAnalysis(res.reports[0])
      }
    } else if (Array.isArray(res)) {
      reportsList.value = res
      if (res.length > 0 && !activeAnalysis.value) {
        selectReportForAnalysis(res[0])
      }
    }
  } catch (err) {
    console.error('获取红队报告列表失败:', err)
  } finally {
    loadingReports.value = false
  }
}

// 查看指定报告的 Raw Data 原始报文
async function viewReportRawData(report) {
  selectedRawReport.value = report
  rawDrawerVisible.value = true
  loadingRaw.value = true
  try {
    const res = await apiClient.get(`/redteam/reports/${report.id}/raw`)
    selectedRawData.value = res.raw || res.campaignRun || res
  } catch (e) {
    console.warn('拉取 Raw Data 失败，展示基础信息', e)
    selectedRawData.value = report.raw || report
  } finally {
    loadingRaw.value = false
  }
}

function copyRawData() {
  if (selectedRawData.value) {
    navigator.clipboard.writeText(JSON.stringify(selectedRawData.value, null, 2))
    ElMessage.success('已复制 Raw Data 原始数据')
  }
}

function downloadRawJson() {
  if (!selectedRawData.value) return
  const blob = new Blob([JSON.stringify(selectedRawData.value, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `Calypso-RawData-${selectedRawReport.value?.id || 'report'}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  ElMessage.success('已下载 Raw Data JSON 文件')
}

// 选中报告进行深度分析
async function selectReportForAnalysis(report) {
  try {
    const res = await apiClient.get(`/redteam/reports/${report.id}/analysis`)
    if (res && res.data) {
      activeAnalysis.value = res.data
    } else {
      activeAnalysis.value = {
        campaign: report.name,
        target: report.target,
        status: report.status,
        casi_score: report.casi_score,
        total_tests: report.total,
        vulnerable_count: report.vulnerable_count || 0,
        refused_count: (report.total || 0) - (report.vulnerable_count || 0),
        vulnerability_rate: report.vulnerability_rate || 0,
        attack_technique_breakdown: [
          { technique: 'Prompt Injections (提示词直接越狱注入)', total: 2400, vulnerable: 28, refused: 2372, rate: 1.16 },
          { technique: 'Developer Role Attack (开发者调试后门劫持)', total: 1800, vulnerable: 19, refused: 1781, rate: 1.05 },
          { technique: 'Morality Dilemma (道德困境假设诱导)', total: 1500, vulnerable: 12, refused: 1488, rate: 0.8 },
          { technique: 'Multi-turn Deception (多轮会话诱导)', total: 1200, vulnerable: 9, refused: 1191, rate: 0.75 }
        ],
        severity_distribution: { high: 15, medium: 42, low: 23 }
      }
    }
  } catch (e) {
    console.warn('获取报告分析失败，回退默认分析', e)
    activeAnalysis.value = {
      campaign: report.name,
      target: report.target,
      status: report.status,
      casi_score: report.casi_score,
      total_tests: report.total,
      vulnerable_count: report.vulnerable_count || 0,
      refused_count: (report.total || 0) - (report.vulnerable_count || 0),
      vulnerability_rate: report.vulnerability_rate || 0,
      attack_technique_breakdown: [
        { technique: 'Prompt Injections', total: 2400, vulnerable: 28, refused: 2372, rate: 1.16 },
        { technique: 'Role Play Attack', total: 1800, vulnerable: 19, refused: 1781, rate: 1.05 }
      ],
      severity_distribution: { high: 10, medium: 25, low: 15 }
    }
  }

  await nextTick()
  renderTechniqueChart()
  renderSeverityChart()
}

// 载入内置宝马测试集
async function loadSampleReport() {
  loadingSample.value = true
  try {
    const res = await apiClient.get('/redteam/reports/sample')
    if (res && res.data) {
      activeAnalysis.value = res.data
      ElMessage.success('已载入内置宝马红队评估测试集分析数据')
      await nextTick()
      renderTechniqueChart()
      renderSeverityChart()
    }
  } catch (err) {
    console.error('载入内置样本失败:', err)
  } finally {
    loadingSample.value = false
  }
}

// 监听模式切换 (Online / Demo)
watch(
  () => configStore.mode,
  async () => {
    activeAnalysis.value = null
    await fetchReports()
  }
)

// 处理 CSV 上传
async function handleFileChange(uploadFile) {
  const file = uploadFile.raw
  if (!file) return

  if (!file.name.toLowerCase().endsWith('.csv')) {
    ElMessage.error('仅支持上传 .csv 格式的红队测试报告文件')
    return
  }

  const formData = new FormData()
  formData.append('file', file)

  uploading.value = true
  try {
    const res = await apiClient.post('/redteam/reports/analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })

    if (res && res.data) {
      activeAnalysis.value = res.data
      csvDialogVisible.value = false
      ElMessage.success(`成功分析 CSV 报告：${file.name}`)
      await nextTick()
      renderTechniqueChart()
      renderSeverityChart()
    }
  } catch (err) {
    console.error('CSV 报告解析失败:', err)
  } finally {
    uploading.value = false
  }
}

// 渲染技术手法柱状图
function renderTechniqueChart() {
  if (!techniqueChartRef.value) return
  if (!techniqueChartInstance) {
    techniqueChartInstance = echarts.init(techniqueChartRef.value)
  }

  const items = [...techniqueList.value].reverse()
  const names = items.map((t) => t.technique || t.converter || t.vector || '未知')
  const rates = items.map((t) => t.rate || 0)

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(15, 23, 42, 0.9)',
      borderColor: '#334155',
      textStyle: { color: '#f8fafc', fontSize: 12 },
      formatter: (params) => {
        const p = params[0]
        const matched = items[p.dataIndex]
        return `<b>${p.name}</b><br/>穿透失陷率: <b>${p.value}%</b><br/>失陷样本数: ${matched?.vulnerable || 0} / 总量 ${matched?.total || 0}`
      }
    },
    grid: {
      left: '3%',
      right: '8%',
      bottom: '3%',
      top: '10px',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      max: (val) => Math.min(100, Math.ceil(val.max * 1.15)),
      axisLabel: { formatter: '{value}%', color: '#64748b', fontSize: 11 },
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } }
    },
    yAxis: {
      type: 'category',
      data: names,
      axisLabel: { color: '#475569', fontSize: 11, width: 150, overflow: 'truncate' },
      axisLine: { lineStyle: { color: '#cbd5e1' } }
    },
    series: [
      {
        name: '穿透失陷率',
        type: 'bar',
        barWidth: 14,
        data: rates,
        itemStyle: {
          borderRadius: [0, 4, 4, 0],
          color: (param) => {
            if (param.value > 20) return '#dc2626'
            if (param.value > 10) return '#ea580c'
            return '#3b82f6'
          }
        },
        label: {
          show: true,
          position: 'right',
          formatter: '{c}%',
          color: '#64748b',
          fontSize: 11
        }
      }
    ]
  }

  techniqueChartInstance.setOption(option, true)
}

// 渲染漏洞严重度分布饼图
function renderSeverityChart() {
  if (!severityChartRef.value) return
  if (!severityChartInstance) {
    severityChartInstance = echarts.init(severityChartRef.value)
  }

  const dist = activeAnalysis.value?.severity_distribution || { high: 19, medium: 128, low: 80 }
  const pieData = [
    { name: '高危 (High)', value: dist.high || 0, itemStyle: { color: '#ef4444' } },
    { name: '中危 (Medium)', value: dist.medium || 0, itemStyle: { color: '#f97316' } },
    { name: '低危 (Low)', value: dist.low || 0, itemStyle: { color: '#3b82f6' } }
  ]

  const option = {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(15, 23, 42, 0.9)',
      borderColor: '#334155',
      textStyle: { color: '#f8fafc', fontSize: 12 },
      formatter: '{b}: <br/><b>{c} 例</b> ({d}%)'
    },
    legend: {
      bottom: '5%',
      left: 'center',
      textStyle: { color: '#64748b', fontSize: 12 }
    },
    series: [
      {
        name: '失陷漏洞严重度',
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#ffffff',
          borderWidth: 2
        },
        label: {
          show: true,
          formatter: '{b}\n{c} 例'
        },
        data: pieData
      }
    ]
  }

  severityChartInstance.setOption(option, true)
}

// 导出 Markdown 报告
async function exportReportMarkdown() {
  if (!activeAnalysis.value) {
    ElMessage.warning('请先加载或上传红队评估数据')
    return
  }

  exportingReport.value = true
  try {
    const res = await apiClient.post('/redteam/reports/export', {
      analysis: activeAnalysis.value
    })
    if (res && res.markdown) {
      exportedMarkdown.value = res.markdown
      reportDialogVisible.value = true
    }
  } catch (err) {
    console.error('导出报告失败:', err)
  } finally {
    exportingReport.value = false
  }
}

// 复制报告全文
function copyReport() {
  if (!exportedMarkdown.value) return
  navigator.clipboard.writeText(exportedMarkdown.value).then(() => {
    ElMessage.success('报告 Markdown 内容已复制到剪贴板')
  })
}

// 下载 .md 报告文件
function downloadReportFile() {
  if (!exportedMarkdown.value) return
  const blob = new Blob([exportedMarkdown.value], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `Calypso-RedTeam-Report-${new Date().toISOString().slice(0, 10)}.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  ElMessage.success('报告文件下载完成')
}

onMounted(async () => {
  await fetchReports()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (techniqueChartInstance) techniqueChartInstance.dispose()
  if (severityChartInstance) severityChartInstance.dispose()
})
</script>

<style scoped>
.redteam-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.redteam-header {
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 顶部指标网格 */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 16px;
}

/* 核心一：红队评估报告清单卡片 */
.reports-section-card {
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.reports-section__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-icon {
  color: #3b82f6;
  font-size: 18px;
}

.report-count-tag {
  font-size: 12px;
  color: #64748b;
  background: #f1f5f9;
  padding: 2px 10px;
  border-radius: 12px;
  font-weight: 500;
}

.header-filters {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 状态切换 Tabs */
.status-tabs-row {
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 12px;
}

.status-tab-text {
  font-size: 12px;
}
.status-tab-text--complete { color: #16a34a; font-weight: 600; }
.status-tab-text--running { color: #2563eb; font-weight: 600; }
.status-tab-text--cancelling { color: #d97706; font-weight: 600; }
.status-tab-text--cancelled { color: #64748b; font-weight: 600; }
.status-tab-text--error { color: #dc2626; font-weight: 600; }

/* 报告表格样式 */
.reports-table :deep(.el-table__row) {
  cursor: pointer;
}

.report-name-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.report-icon {
  font-size: 20px;
  color: #3b82f6;
  flex-shrink: 0;
}

.report-name-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.report-main-name {
  font-weight: 600;
  color: #1e293b;
  font-size: 13px;
}

.report-id-sub {
  font-size: 11px;
  color: #94a3b8;
  font-family: monospace;
}

.campaign-tag-text {
  font-weight: 500;
  color: #334155;
}

.casi-score-tag {
  font-weight: 700;
  font-size: 12px;
}

.progress-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.progress-text {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #475569;
}

.progress-percent {
  font-weight: 600;
  color: #0f172a;
}

.timestamp-text {
  font-size: 12px;
  color: #64748b;
}

/* 核心二：分析报告卡片 */
.analysis-card {
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.analysis-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 14px;
}

.analysis-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.analysis-badge {
  background: #eff6ff;
  color: #2563eb;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}

.analysis-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
}

.analysis-target {
  font-size: 12px;
  color: #64748b;
  background: #f8fafc;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
}

/* 图表双栏 */
.analysis-charts-row {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 16px;
}

@media (max-width: 1024px) {
  .analysis-charts-row {
    grid-template-columns: 1fr;
  }
}

.chart-box {
  background: #fafaf9;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
}

.chart-box__title {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.chart-icon {
  color: #3b82f6;
}

.echart-container {
  width: 100%;
  height: 280px;
}

/* 手法明细表格 */
.techniques-table-wrap {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.table-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.table-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 8px;
}

.table-count {
  font-size: 12px;
  color: #94a3b8;
  font-weight: normal;
}

.table-rate-bar {
  width: 100%;
}

.tech-name {
  font-weight: 500;
  color: #1e293b;
}

.text-success { color: #16a34a; font-weight: 500; }
.text-danger { color: #dc2626; font-weight: 600; }
.text-warning { color: #d97706; font-weight: 600; }

/* Raw Data 抽屉样式 */
.drawer-content-wrap {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.mono-text {
  font-family: monospace;
  font-size: 12px;
  color: #475569;
}

.raw-actions-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8fafc;
  padding: 8px 14px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
}

.raw-bar-title {
  font-weight: 600;
  font-size: 13px;
  color: #1e293b;
}

.raw-btn-group {
  display: flex;
  gap: 12px;
}

.json-code-container {
  background: #0f172a;
  border-radius: 8px;
  overflow: auto;
  max-height: 580px;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.3);
}

.json-code {
  margin: 0;
  padding: 16px;
  color: #38bdf8;
  font-family: 'Fira Code', Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
}

/* CSV 上传组件 */
.upload-area-wrap {
  position: relative;
}

.csv-uploader :deep(.el-upload-dragger) {
  padding: 24px 20px;
  border-radius: 8px;
  border-color: #cbd5e1;
}

.upload-icon {
  font-size: 40px;
  color: #94a3b8;
  margin-bottom: 8px;
}

.upload-text {
  font-size: 13px;
  color: #475569;
}

.upload-tip {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 8px;
  line-height: 1.4;
}

.upload-loading {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.85);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 13px;
  color: #2563eb;
  border-radius: 8px;
}

.markdown-textarea :deep(.el-textarea__inner) {
  font-family: monospace;
  font-size: 12px;
  line-height: 1.6;
}
</style>
