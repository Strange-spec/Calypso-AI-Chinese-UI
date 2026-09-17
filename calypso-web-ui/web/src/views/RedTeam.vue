<template>
  <div class="redteam-view">
    <!-- 头部信息 -->
    <div class="redteam-header">
      <div class="header-intro">
        <h2 class="view-title">红队对抗评估与安全报告 (Red Team Campaigns)</h2>
        <span class="view-desc">
          模拟自动化高强度对抗攻击（涵盖混淆编码、提示词劫持、多轮越狱等），评估大语言模型防御健壮性与失陷风险。
        </span>
      </div>

      <div class="header-actions">
        <!-- 快速载入内置宝马测试集 -->
        <el-button
          type="primary"
          :loading="loadingSample"
          @click="loadSampleReport"
        >
          <el-icon><Star /></el-icon>
          <span>载入内置宝马红队评估测试集 (BMW Agentic Test)</span>
        </el-button>

        <!-- 刷新任务列表 -->
        <el-button plain :loading="loadingCampaigns" @click="fetchCampaigns">
          <el-icon><Refresh /></el-icon>
          <span>刷新任务</span>
        </el-button>
      </div>
    </div>

    <!-- 顶部 5 大核心失陷指标卡 -->
    <div class="metrics-grid">
      <MetricCard
        title="对抗测试总用例"
        :value="activeMetrics.total_tests"
        unit="次"
        icon="Aim"
        icon-bg="#eff6ff"
        icon-color="#2563eb"
        tooltip="红队任务中向目标模型与 Agent 发送的攻击载荷总量"
        type="primary"
      />

      <MetricCard
        title="模型失陷/穿透数"
        :value="activeMetrics.vulnerable_count"
        unit="例"
        icon="WarningFilled"
        icon-bg="#fef2f2"
        icon-color="#dc2626"
        :invert-trend-color="true"
        tooltip="模型未能识别或执行了违规恶意指令的失陷样本数"
        type="danger"
      />

      <MetricCard
        title="成功防御拒绝"
        :value="activeMetrics.refused_count"
        unit="例"
        icon="CircleCheckFilled"
        icon-bg="#f0fdf4"
        icon-color="#16a34a"
        tooltip="安全护栏或模型成功拒绝恶意攻击的合规防御样本数"
        type="success"
      />

      <MetricCard
        title="API 异常与崩溃"
        :value="activeMetrics.api_crash_count"
        unit="例"
        icon="CircleCloseFilled"
        icon-bg="#fffbeb"
        icon-color="#d97706"
        tooltip="因载荷异常导致服务超时、500 报错或 Fuzzing 崩溃的数量"
        type="warning"
      />

      <MetricCard
        title="综合穿透失陷率"
        :value="activeMetrics.vulnerability_rate"
        unit="%"
        :precision="2"
        icon="Odometer"
        icon-bg="#faf5ff"
        icon-color="#9333ea"
        :invert-trend-color="true"
        tooltip="失陷样本数占总测试样本的百分比 (越低越安全)"
        type="danger"
      />
    </div>

    <!-- 红队报告分析展示区 (若已加载分析数据) -->
    <div v-if="activeAnalysis" class="analysis-card">
      <div class="analysis-card__header">
        <div class="analysis-title-group">
          <span class="analysis-badge">当前报告</span>
          <h3 class="analysis-title">{{ activeAnalysis.campaign || '红队评估分析' }}</h3>
          <span v-if="activeAnalysis.target" class="analysis-target">
            靶标: {{ activeAnalysis.target }}
          </span>
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
          <el-table-column prop="refused" label="成功拦截防御" width="130" align="center">
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

    <!-- 下半部分：CSV 报告导入与已有红队任务列表 -->
    <div class="bottom-grid">
      <!-- CSV 报告上传导入卡片 -->
      <div class="bottom-card csv-upload-card">
        <div class="bottom-card__header">
          <span class="card-title">
            <el-icon class="title-icon"><UploadFilled /></el-icon>
            导入红队评估 CSV 报告
          </span>
          <span class="card-hint">支持 Calypso / BMW 标准导出的 CSV</span>
        </div>

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
                支持解析字段：campaign, connection, attackVector, attackTechnique, vulnerable, refused, severity
              </div>
            </template>
          </el-upload>

          <div v-if="uploading" class="upload-loading">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>正在解析 CSV 报告数据...</span>
          </div>
        </div>
      </div>

      <!-- 历史红队活动任务列表 -->
      <div class="bottom-card campaigns-card">
        <div class="bottom-card__header">
          <span class="card-title">
            <el-icon class="title-icon"><List /></el-icon>
            红队对抗评估任务列表 (Campaigns)
          </span>
          <span class="card-hint">共 {{ campaignsList.length }} 个评估计划</span>
        </div>

        <el-table
          :data="campaignsList"
          stripe
          border
          class="custom-table"
          max-height="260"
        >
          <el-table-column prop="name" label="活动名称" min-width="160">
            <template #default="{ row }">
              <span class="campaign-name">{{ row.name }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="target" label="受测靶标" min-width="180" show-overflow-tooltip />
          <el-table-column prop="status" label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag size="small" type="success" effect="light">已完成</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="vulnerability_rate" label="失陷率" width="100" align="center">
            <template #default="{ row }">
              <span class="rate-text" :class="row.vulnerability_rate > 10 ? 'text-danger' : 'text-warning'">
                {{ row.vulnerability_rate }}%
              </span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="130" align="center">
            <template #default="{ row }">
              <el-button
                type="primary"
                link
                size="small"
                @click="loadCampaignDetails(row)"
              >
                查看分析
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

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
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import apiClient from '../api/client'
import MetricCard from '../components/MetricCard.vue'

const loadingCampaigns = ref(false)
const loadingSample = ref(false)
const uploading = ref(false)
const exportingReport = ref(false)
const reportDialogVisible = ref(false)
const exportedMarkdown = ref('')

const campaignsList = ref([])
const activeAnalysis = ref(null)
const techniqueFilter = ref('all')

// 图表 DOM 与实例
const techniqueChartRef = ref(null)
const severityChartRef = ref(null)
let techniqueChartInstance = null
let severityChartInstance = null

// 核心失陷指标
const activeMetrics = computed(() => {
  if (activeAnalysis.value) {
    return {
      total_tests: activeAnalysis.value.total_tests || 0,
      vulnerable_count: activeAnalysis.value.vulnerable_count || 0,
      refused_count: activeAnalysis.value.refused_count || 0,
      api_crash_count: activeAnalysis.value.api_crash_count || 0,
      vulnerability_rate: activeAnalysis.value.vulnerability_rate || 0
    }
  }
  // 兜底默认展示第一个 Campaign 或 0
  const first = campaignsList.value[0]
  if (first) {
    return {
      total_tests: first.total_tests || 0,
      vulnerable_count: first.vulnerable_count || 0,
      refused_count: first.successful_refusals || 0,
      api_crash_count: first.api_fuzzing_crashes || 0,
      vulnerability_rate: first.vulnerability_rate || 0
    }
  }
  return {
    total_tests: 0,
    vulnerable_count: 0,
    refused_count: 0,
    api_crash_count: 0,
    vulnerability_rate: 0
  }
})

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

// 获取 Campaign 列表
async function fetchCampaigns() {
  loadingCampaigns.value = true
  try {
    const res = await apiClient.get('/redteam/campaigns')
    if (res && res.campaigns) {
      campaignsList.value = res.campaigns
    } else if (Array.isArray(res)) {
      campaignsList.value = res
    }
  } catch (err) {
    console.error('获取红队任务列表失败:', err)
  } finally {
    loadingCampaigns.value = false
  }
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

// 从任务列表中载入指定 Campaign
function loadCampaignDetails(campaign) {
  activeAnalysis.value = {
    campaign: campaign.name,
    target: campaign.target,
    total_tests: campaign.total_tests,
    vulnerable_count: campaign.vulnerable_count,
    refused_count: campaign.successful_refusals || 0,
    api_crash_count: campaign.api_fuzzing_crashes || 0,
    vulnerability_rate: campaign.vulnerability_rate,
    attack_technique_breakdown: campaign.attack_breakdown || [],
    severity_distribution: campaign.severity_distribution || { high: 19, medium: 128, low: 80 }
  }
  nextTick(() => {
    renderTechniqueChart()
    renderSeverityChart()
  })
}

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

  const items = [...techniqueList.value].reverse() // 让高穿透在上方
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
  await fetchCampaigns()
  await loadSampleReport()
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

/* 分析报告卡片 */
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

/* 底部区域 */
.bottom-grid {
  display: grid;
  grid-template-columns: 1fr 1.3fr;
  gap: 16px;
}

@media (max-width: 1024px) {
  .bottom-grid {
    grid-template-columns: 1fr;
  }
}

.bottom-card {
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
}

.bottom-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 12px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-icon {
  color: #3b82f6;
}

.card-hint {
  font-size: 12px;
  color: #94a3b8;
}

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

.campaign-name {
  font-weight: 600;
  color: #0f172a;
}

.markdown-textarea :deep(.el-textarea__inner) {
  font-family: monospace;
  font-size: 12px;
  line-height: 1.6;
}
</style>
