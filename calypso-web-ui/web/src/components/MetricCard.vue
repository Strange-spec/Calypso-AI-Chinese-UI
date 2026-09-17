<template>
  <div class="metric-card" :class="[`metric-card--${type}`, { 'has-hover': hoverable }]">
    <div class="metric-card__header">
      <div class="metric-card__title-wrap">
        <span class="metric-card__title">{{ title }}</span>
        <el-tooltip v-if="tooltip" :content="tooltip" placement="top">
          <el-icon class="metric-card__tip-icon"><InfoFilled /></el-icon>
        </el-tooltip>
      </div>
      <div v-if="icon || $slots.icon" class="metric-card__icon-box" :style="iconBoxStyle">
        <slot name="icon">
          <component :is="getIconComponent(icon)" v-if="getIconComponent(icon)" />
          <span v-else class="metric-card__icon-char">{{ icon }}</span>
        </slot>
      </div>
    </div>

    <div class="metric-card__body">
      <div class="metric-card__value-row">
        <span class="metric-card__value">{{ formattedValue }}</span>
        <span v-if="unit" class="metric-card__unit">{{ unit }}</span>
      </div>

      <div v-if="trend !== null && trend !== undefined" class="metric-card__footer">
        <div class="metric-card__trend" :class="trendClass">
          <el-icon class="metric-card__trend-icon">
            <Top v-if="isTrendUp" />
            <Bottom v-else-if="isTrendDown" />
            <Minus v-else />
          </el-icon>
          <span class="metric-card__trend-value">{{ formattedTrend }}</span>
        </div>
        <span v-if="trendText" class="metric-card__trend-text">{{ trendText }}</span>
        <slot name="footer" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  value: {
    type: [Number, String],
    default: 0
  },
  unit: {
    type: String,
    default: ''
  },
  icon: {
    type: [String, Object, Function],
    default: null
  },
  iconBg: {
    type: String,
    default: ''
  },
  iconColor: {
    type: String,
    default: ''
  },
  trend: {
    type: [Number, String],
    default: null
  },
  trendText: {
    type: String,
    default: ''
  },
  // true: 上升为积极(绿) 下降为消极(红)；false: 反之(如拦截率/漏洞率，下降为绿)
  invertTrendColor: {
    type: Boolean,
    default: false
  },
  tooltip: {
    type: String,
    default: ''
  },
  type: {
    type: String,
    default: 'default', // 'default' | 'primary' | 'success' | 'warning' | 'danger'
    validator: (v) => ['default', 'primary', 'success', 'warning', 'danger'].includes(v)
  },
  precision: {
    type: Number,
    default: -1
  },
  hoverable: {
    type: Boolean,
    default: true
  }
})

import * as ElementPlusIconsVue from '@element-plus/icons-vue'

function getIconComponent(item) {
  if (!item) return null
  if (typeof item === 'object' || typeof item === 'function') return item
  if (typeof item === 'string' && ElementPlusIconsVue[item]) return ElementPlusIconsVue[item]
  return null
}

// 格式化千分位数值
const formattedValue = computed(() => {
  if (props.value === null || props.value === undefined) return '-'
  const num = Number(props.value)
  if (isNaN(num)) return props.value

  if (props.precision >= 0) {
    return num.toLocaleString('zh-CN', {
      minimumFractionDigits: props.precision,
      maximumFractionDigits: props.precision
    })
  }
  return num.toLocaleString('zh-CN')
})

const numericTrend = computed(() => {
  if (props.trend === null || props.trend === undefined) return 0
  const parsed = parseFloat(String(props.trend).replace('%', ''))
  return isNaN(parsed) ? 0 : parsed
})

const isTrendUp = computed(() => numericTrend.value > 0)
const isTrendDown = computed(() => numericTrend.value < 0)

const formattedTrend = computed(() => {
  if (props.trend === null || props.trend === undefined) return ''
  const str = String(props.trend)
  if (str.includes('%')) return str
  const val = numericTrend.value
  return `${val > 0 ? '+' : ''}${val}%`
})

const trendClass = computed(() => {
  if (numericTrend.value === 0) return 'trend--neutral'
  const isPositiveDirection = isTrendUp.value
  const isGood = props.invertTrendColor ? !isPositiveDirection : isPositiveDirection
  return isGood ? 'trend--positive' : 'trend--negative'
})

const iconBoxStyle = computed(() => {
  const styles = {}
  if (props.iconBg) styles.backgroundColor = props.iconBg
  if (props.iconColor) styles.color = props.iconColor
  return styles
})
</script>

<style scoped>
.metric-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px 22px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  position: relative;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.metric-card.has-hover:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
  border-color: #cbd5e1;
}

.metric-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.metric-card__title-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
}

.metric-card__title {
  font-size: 14px;
  font-weight: 500;
  color: #64748b;
  letter-spacing: 0.2px;
}

.metric-card__tip-icon {
  font-size: 14px;
  color: #94a3b8;
  cursor: pointer;
  transition: color 0.15s;
}
.metric-card__tip-icon:hover {
  color: #64748b;
}

.metric-card__icon-box {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  background-color: #f1f5f9;
  color: #3b82f6;
  flex-shrink: 0;
}

.metric-card__icon-char {
  font-size: 18px;
}

.metric-card__value-row {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 8px;
}

.metric-card__value {
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.1;
  font-feature-settings: "tnum";
  font-variant-numeric: tabular-nums;
}

.metric-card__unit {
  font-size: 13px;
  font-weight: 500;
  color: #64748b;
}

.metric-card__footer {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

.metric-card__trend {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-weight: 600;
  border-radius: 4px;
  padding: 1px 4px;
}

.trend--positive {
  color: #16a34a;
  background-color: #dcfce7;
}

.trend--negative {
  color: #dc2626;
  background-color: #fee2e2;
}

.trend--neutral {
  color: #64748b;
  background-color: #f1f5f9;
}

.metric-card__trend-icon {
  font-size: 12px;
}

.metric-card__trend-text {
  color: #64748b;
}

/* 预设卡片类型微调 */
.metric-card--primary .metric-card__icon-box {
  background-color: #eff6ff;
  color: #2563eb;
}
.metric-card--success .metric-card__icon-box {
  background-color: #f0fdf4;
  color: #16a34a;
}
.metric-card--warning .metric-card__icon-box {
  background-color: #fffbeb;
  color: #d97706;
}
.metric-card--danger .metric-card__icon-box {
  background-color: #fef2f2;
  color: #dc2626;
}
</style>
