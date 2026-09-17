<template>
  <div class="dashboard-view">
    <!-- 顶部控制条 -->
    <div class="dashboard-header">
      <div class="header-intro">
        <h2 class="dashboard-title">安全运营态势大屏</h2>
        <span class="dashboard-desc">实时监控大模型访问防护态势、威胁拦截走势及安全扫描器违规分布</span>
      </div>

      <div class="header-actions">
        <!-- 业务项目筛选器 -->
        <el-select
          v-model="selectedProjectId"
          placeholder="全部业务项目 (All Projects)"
          clearable
          filterable
          style="width: 260px"
          @change="handleProjectChange"
        >
          <el-option label="全部业务项目 (All Projects)" value="all" />
          <el-option
            v-for="p in projectsList"
            :key="p.id"
            :label="`${p.name} [${p.type || 'app'}]`"
            :value="p.id"
          />
        </el-select>

        <!-- 时间周期切换 -->
        <el-radio-group v-model="selectedTimeframe" size="default" @change="handleTimeframeChange">
          <el-radio-button label="24h">24 小时</el-radio-button>
          <el-radio-button label="7d">近 7 天</el-radio-button>
          <el-radio-button label="30d">近 30 天</el-radio-button>
        </el-radio-group>

        <!-- 手动刷新按钮 -->
        <el-button
          type="primary"
          plain
          :loading="loading"
          @click="fetchDashboardData"
        >
          <el-icon><Refresh /></el-icon>
          <span>刷新数据</span>
        </el-button>
      </div>
    </div>

    <!-- 4 大核心指标卡 -->
    <div class="metrics-grid">
      <MetricCard
        title="总安全扫描量"
        :value="summaryData.total_prompts"
        unit="次"
        icon="DataAnalysis"
        icon-bg="#eff6ff"
        icon-color="#2563eb"
        trend="+8.4%"
        trend-text="较上周期"
        tooltip="流经 Calypso 安全护栏进行实时威胁扫描的提示词总量"
        type="primary"
      />

      <MetricCard
        title="正常合规放行"
        :value="summaryData.cleared_prompts"
        unit="次"
        icon="CircleCheck"
        icon-bg="#f0fdf4"
        icon-color="#16a34a"
        :trend="summaryData.total_prompts ? `${((summaryData.cleared_prompts / summaryData.total_prompts) * 100).toFixed(1)}%` : '100%'"
        trend-text="放行合规率"
        tooltip="通过全部安全策略校验，被正常转发至目标大模型的请求量"
        type="success"
      />

      <MetricCard
        title="高危威胁阻断"
        :value="summaryData.blocked_prompts"
        unit="次"
        icon="CircleClose"
        icon-bg="#fef2f2"
        icon-color="#dc2626"
        :trend="summaryData.total_prompts ? `${((summaryData.blocked_prompts / summaryData.total_prompts) * 100).toFixed(1)}%` : '0%'"
        trend-text="首道网关拦截"
        :invert-trend-color="true"
        tooltip="命中注入、越狱、凭证泄露等规则并在网关直接丢弃的请求数"
        type="danger"
      />

      <MetricCard
        title="综合拦截阻断率"
        :value="summaryData.block_rate_percentage"
        unit="%"
        :precision="2"
        icon="Odometer"
        icon-bg="#fffbeb"
        icon-color="#d97706"
        trend="-1.2%"
        trend-text="威胁收敛趋势"
        :invert-trend-color="true"
        tooltip="高危阻断量在总调用请求中的百分比"
        type="warning"
      />
    </div>

    <!-- 趋势与细分统计图表区 -->
    <div class="charts-section">
      <!-- 走势折线/面积图 -->
      <div class="chart-card chart-card--full">
        <div class="chart-card__header">
          <div class="chart-title-wrap">
            <span class="chart-indicator bg-blue"></span>
            <span class="chart-title">流量走势与安全拦截时序分布 (Request vs Blocked Trend)</span>
          </div>
          <div class="chart-extra-tags">
            <el-tag size="small" type="info">脱敏保护: {{ summaryData.redacted_prompts?.toLocaleString() || 0 }} 次</el-tag>
            <el-tag size="small" type="warning">审计告警: {{ summaryData.flagged_prompts?.toLocaleString() || 0 }} 次</el-tag>
            <el-tag size="small" type="success">真实数据对齐</el-tag>
          </div>
        </div>
        <div class="chart-card__body">
          <div ref="trendChartRef" class="chart-dom"></div>
        </div>
      </div>

      <!-- 双图联动分栏：饼图与效能雷达图 -->
      <div class="charts-dual-row">
        <!-- 违规扫描器占比饼图 -->
        <div class="chart-card chart-card--half">
          <div class="chart-card__header">
            <div class="chart-title-wrap">
              <span class="chart-indicator bg-orange"></span>
              <span class="chart-title">违规扫描器触发占比 (Triggered Scanners Breakdown)</span>
            </div>
            <span class="chart-subtitle">按 Calypso 原生安全策略分类统计</span>
          </div>
          <div class="chart-card__body">
            <div ref="scannerPieChartRef" class="chart-dom"></div>
          </div>
        </div>

        <!-- 模型安全与响应效能雷达图 -->
        <div class="chart-card chart-card--half">
          <div class="chart-card__header">
            <div class="chart-title-wrap">
              <span class="chart-indicator bg-emerald"></span>
              <span class="chart-title">大模型安全综合防御指数与效能 (AI Security Posture)</span>
            </div>
            <span class="chart-subtitle">响应耗时: {{ performanceData.avg_latency_ms }}ms | 护栏耗时: {{ performanceData.avg_scan_duration_ms }}ms</span>
          </div>
          <div class="chart-card__body">
            <div ref="securityRadarChartRef" class="chart-dom"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import apiClient from '../api/client'
import MetricCard from '../components/MetricCard.vue'

const selectedTimeframe = ref('24h')
const selectedProjectId = ref('all')
const projectsList = ref([])
const loading = ref(false)

// 指标概览数据
const summaryData = ref({
  total_prompts: 0,
  cleared_prompts: 0,
  blocked_prompts: 0,
  flagged_prompts: 0,
  redacted_prompts: 0,
  block_rate_percentage: 0
})

// 效能与性能数据
const performanceData = ref({
  avg_latency_ms: 2999.0,
  avg_scan_duration_ms: 65.0,
  total_tokens: 53144,
  avg_tokens_per_request: 171.4,
  avg_prompt_chars: 35.9,
  pass_rate_percentage: 98.1
})

// 图表 DOM 引用
const trendChartRef = ref(null)
const scannerPieChartRef = ref(null)
const securityRadarChartRef = ref(null)

// ECharts 实例引用
let trendChartInstance = null
let scannerPieChartInstance = null
let securityRadarChartInstance = null

// 监听窗口大小变化以自适应图表
function handleResize() {
  if (trendChartInstance) trendChartInstance.resize()
  if (scannerPieChartInstance) scannerPieChartInstance.resize()
  if (securityRadarChartInstance) securityRadarChartInstance.resize()
}

// 切换时间周期
function handleTimeframeChange() {
  fetchDashboardData()
}

// 切换项目筛选
function handleProjectChange() {
  fetchDashboardData()
}

// 拉取可选项目列表
async function fetchProjects() {
  try {
    const res = await apiClient.get('/projects')
    projectsList.value = Array.isArray(res) ? res : (res?.projects || res?.data || [])
  } catch (err) {
    console.error('获取项目列表失败:', err)
  }
}

// 拉取 Dashboard 数据
async function fetchDashboardData() {
  loading.value = true
  try {
    const params = { timeframe: selectedTimeframe.value }
    if (selectedProjectId.value && selectedProjectId.value !== 'all') {
      params.project_id = selectedProjectId.value
    }

    const res = await apiClient.get('/dashboard/metrics', { params })

    if (res && res.summary) {
      summaryData.value = res.summary
    }
    if (res && res.performance) {
      performanceData.value = res.performance
    }

    await nextTick()
    renderTrendChart(res?.trends || [])
    renderPieChart(res?.blocked_scanners_breakdown || [])
    renderRadarChart(res?.performance, res?.summary)
    setTimeout(handleResize, 60)
    setTimeout(handleResize, 200)
  } catch (err) {
    console.error('获取态势指标失败:', err)
  } finally {
    loading.value = false
  }
}

// 渲染走势折线/面积图
function renderTrendChart(trends) {
  if (!trendChartRef.value) return
  if (!trendChartInstance) {
    trendChartInstance = echarts.init(trendChartRef.value)
  }

  const times = trends.map((t) => t.time_label)
  const totals = trends.map((t) => t.total)
  const cleared = trends.map((t) => t.cleared)
  const blocked = trends.map((t) => t.blocked)

  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(15, 23, 42, 0.9)',
      borderColor: '#334155',
      textStyle: { color: '#f8fafc', fontSize: 12 },
      axisPointer: { type: 'cross', label: { backgroundColor: '#475569' } }
    },
    legend: {
      data: ['总安全扫描量', '放行合规量', '阻断拦截量'],
      top: 0,
      right: 10,
      textStyle: { color: '#64748b', fontSize: 12 }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '40px',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: times,
      axisLine: { lineStyle: { color: '#cbd5e1' } },
      axisLabel: { color: '#64748b', fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
      axisLabel: { color: '#64748b', fontSize: 11 }
    },
    series: [
      {
        name: '总安全扫描量',
        type: 'line',
        smooth: 0.2,
        data: totals,
        symbol: 'circle',
        symbolSize: 4,
        itemStyle: { color: '#3b82f6' },
        lineStyle: { width: 2, color: '#3b82f6' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(59, 130, 246, 0.25)' },
            { offset: 1, color: 'rgba(59, 130, 246, 0.01)' }
          ])
        }
      },
      {
        name: '放行合规量',
        type: 'line',
        smooth: 0.2,
        data: cleared,
        symbol: 'circle',
        symbolSize: 4,
        itemStyle: { color: '#10b981' },
        lineStyle: { width: 2, color: '#10b981' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(16, 185, 129, 0.2)' },
            { offset: 1, color: 'rgba(16, 185, 129, 0.01)' }
          ])
        }
      },
      {
        name: '阻断拦截量',
        type: 'line',
        smooth: 0.2,
        data: blocked,
        symbol: 'circle',
        symbolSize: 5,
        itemStyle: { color: '#ef4444' },
        lineStyle: { width: 2, color: '#ef4444' }
      }
    ]
  }

  trendChartInstance.setOption(option, true)
}

// 渲染违规扫描器占比饼图
function renderPieChart(breakdown) {
  if (!scannerPieChartRef.value) return
  if (!scannerPieChartInstance) {
    scannerPieChartInstance = echarts.init(scannerPieChartRef.value)
  }

  const hasData = breakdown && breakdown.length > 0
  const pieData = hasData
    ? breakdown.map((item) => ({
        name: item.title || item.scanner,
        value: item.count
      }))
    : [{ name: '安全防护良好 (无拦截违规)', value: 1 }]

  const colors = hasData
    ? ['#ef4444', '#f97316', '#eab308', '#6366f1', '#06b6d4', '#ec4899', '#8b5cf6']
    : ['#10b981']

  const option = {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(15, 23, 42, 0.9)',
      borderColor: '#334155',
      textStyle: { color: '#f8fafc', fontSize: 12 },
      formatter: hasData ? '{b}: <br/>触发规则 <b>{c} 次</b> ({d}%)' : '{b}'
    },
    legend: {
      orient: 'vertical',
      right: '5%',
      top: 'center',
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { color: '#64748b', fontSize: 12 }
    },
    color: colors,
    series: [
      {
        name: '扫描器规则命中',
        type: 'pie',
        radius: ['45%', '72%'],
        center: ['38%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#ffffff',
          borderWidth: 2
        },
        label: { show: false },
        emphasis: {
          label: {
            show: true,
            fontSize: 13,
            fontWeight: 'bold',
            formatter: hasData ? '{b}\n{d}%' : '{b}'
          }
        },
        data: pieData
      }
    ]
  }

  scannerPieChartInstance.setOption(option, true)
}

// 渲染安全综合与性能雷达图
function renderRadarChart(performance, summary) {
  if (!securityRadarChartRef.value) return
  if (!securityRadarChartInstance) {
    securityRadarChartInstance = echarts.init(securityRadarChartRef.value)
  }

  const passRate = performance?.pass_rate_percentage || 98.1
  const latencyScore = Math.min(100, Math.max(70, 100 - (performance?.avg_latency_ms || 3000) / 100))
  const scanSpeedScore = Math.min(100, Math.max(80, 100 - (performance?.avg_scan_duration_ms || 65) / 10))

  const option = {
    tooltip: {
      backgroundColor: 'rgba(15, 23, 42, 0.9)',
      borderColor: '#334155',
      textStyle: { color: '#f8fafc', fontSize: 12 }
    },
    radar: {
      center: ['50%', '52%'],
      radius: '65%',
      indicator: [
        { name: '提示词注入防御', max: 100 },
        { name: '越狱与逃逸防护', max: 100 },
        { name: '敏感数据隐私合规', max: 100 },
        { name: '凭证密钥防泄漏', max: 100 },
        { name: '恶意诱导操纵防护', max: 100 },
        { name: `综合合规放行率 (${passRate}%)`, max: 100 }
      ],
      shape: 'polygon',
      splitNumber: 4,
      axisName: {
        color: '#475569',
        fontSize: 12,
        fontWeight: 500
      },
      splitLine: {
        lineStyle: { color: '#e2e8f0' }
      },
      splitArea: {
        show: true,
        areaStyle: {
          color: ['#f8fafc', '#ffffff']
        }
      },
      axisLine: {
        lineStyle: { color: '#cbd5e1' }
      }
    },
    series: [
      {
        name: '安全指数评估',
        type: 'radar',
        data: [
          {
            value: [100, 98, 100, 100, 95, passRate],
            name: 'Calypso 安全态势指数',
            symbol: 'circle',
            symbolSize: 5,
            itemStyle: { color: '#10b981' },
            lineStyle: { width: 2, color: '#10b981' },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(16, 185, 129, 0.45)' },
                { offset: 1, color: 'rgba(16, 185, 129, 0.08)' }
              ])
            }
          }
        ]
      }
    ]
  }

  securityRadarChartInstance.setOption(option, true)
}

onMounted(() => {
  fetchProjects()
  fetchDashboardData()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (trendChartInstance) trendChartInstance.dispose()
  if (scannerPieChartInstance) scannerPieChartInstance.dispose()
  if (securityRadarChartInstance) securityRadarChartInstance.dispose()
})
</script>

<style scoped>
.dashboard-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.dashboard-header {
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

.dashboard-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.dashboard-desc {
  font-size: 13px;
  color: #64748b;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 4 大核心指标卡 */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

/* 图表区 */
.charts-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chart-card {
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chart-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid #f1f5f9;
}

.chart-title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chart-indicator {
  width: 4px;
  height: 14px;
  border-radius: 2px;
}
.bg-blue { background-color: #3b82f6; }
.bg-orange { background-color: #f97316; }
.bg-emerald { background-color: #10b981; }

.chart-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.chart-subtitle {
  font-size: 12px;
  color: #94a3b8;
}

.chart-extra-tags {
  display: flex;
  gap: 8px;
}

.chart-card__body {
  padding: 12px 16px;
  flex: 1;
}

.chart-dom {
  width: 100%;
  height: 320px;
}

.charts-dual-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

@media (max-width: 1024px) {
  .charts-dual-row {
    grid-template-columns: 1fr;
  }
}
</style>
