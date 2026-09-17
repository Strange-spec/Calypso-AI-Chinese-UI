<template>
  <div class="diff-viewer">
    <!-- 头部工具栏 -->
    <div class="diff-viewer__toolbar">
      <div class="diff-viewer__status">
        <span class="status-indicator"></span>
        <span class="toolbar-title">数据敏感度比对 (PII Redaction Diff)</span>
        <el-tag v-if="statsCount > 0" type="warning" size="small" effect="plain" class="stats-tag">
          发现 {{ statsCount }} 处敏感项已脱敏替换
        </el-tag>
      </div>

      <div class="diff-viewer__actions">
        <!-- 切换视图模式 -->
        <el-radio-group v-model="viewMode" size="small">
          <el-radio-button label="side-by-side">并排对比</el-radio-button>
          <el-radio-button label="stacked">上下分栏</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <!-- 主体对比区 -->
    <div class="diff-viewer__content" :class="`mode--${viewMode}`">
      <!-- 原始输入栏 -->
      <div class="diff-pane diff-pane--original">
        <div class="pane-header">
          <span class="pane-title">
            <span class="pane-badge badge--original">原始输入 (Raw Prompt)</span>
          </span>
          <el-button
            link
            size="small"
            type="primary"
            @click="copyText(original, '原始文本已复制')"
          >
            <el-icon><CopyDocument /></el-icon>
            复制
          </el-button>
        </div>
        <div class="pane-body">
          <div class="text-content text-original">{{ original || '（无输入文本）' }}</div>
        </div>
      </div>

      <!-- 脱敏后输出栏 -->
      <div class="diff-pane diff-pane--redacted">
        <div class="pane-header">
          <span class="pane-title">
            <span class="pane-badge badge--redacted">安全脱敏结果 (Redacted Output)</span>
          </span>
          <el-button
            link
            size="small"
            type="success"
            @click="copyText(redacted, '脱敏文本已复制')"
          >
            <el-icon><CopyDocument /></el-icon>
            复制
          </el-button>
        </div>
        <div class="pane-body">
          <div class="text-content text-redacted" v-html="highlightedRedactedHtml"></div>
        </div>
      </div>
    </div>

    <!-- 敏感实体明细展示 -->
    <div v-if="maskedItems && maskedItems.length > 0" class="masked-tags-bar">
      <span class="tags-label">脱敏实体捕获:</span>
      <div class="tags-list">
        <el-tag
          v-for="(item, idx) in maskedItems"
          :key="idx"
          size="small"
          type="warning"
          effect="light"
          class="masked-tag"
        >
          <span class="tag-type">{{ formatType(item.type) }}:</span>
          <span class="tag-match">{{ item.match }}</span>
          <el-icon class="arrow-icon"><Right /></el-icon>
          <span class="tag-rep">{{ item.replacement }}</span>
        </el-tag>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  original: {
    type: String,
    default: ''
  },
  redacted: {
    type: String,
    default: ''
  },
  maskedItems: {
    type: Array,
    default: () => []
  },
  defaultMode: {
    type: String,
    default: 'side-by-side' // 'side-by-side' | 'stacked'
  }
})

const viewMode = ref(props.defaultMode)

// 敏感项统计
const statsCount = computed(() => {
  if (props.maskedItems && props.maskedItems.length > 0) {
    return props.maskedItems.length
  }
  // 如果没有 maskedItems 数组，通过正则统计 [...] 标签数量
  if (props.redacted) {
    const matches = props.redacted.match(/\[.*?脱敏.*?\]/g)
    return matches ? matches.length : 0
  }
  return 0
})

function formatType(type) {
  const map = {
    phone: '手机号',
    id_card: '身份证',
    bank_card: '银行卡',
    email: '电子邮箱',
    secrets: '访问凭证'
  }
  return map[type] || type || '敏感信息'
}

// 转义 HTML 字符
function escapeHtml(text) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

// 高亮渲染脱敏文本中的标签
const highlightedRedactedHtml = computed(() => {
  if (!props.redacted) return '（无脱敏输出文本）'

  const escaped = escapeHtml(props.redacted)
  // 将形如 [手机号脱敏], [身份证脱敏], [银行卡脱敏], [已脱敏处理] 等匹配高亮为样式徽章
  const regex = /\[([^\]]*?脱敏[^\]]*?)\]/g
  return escaped.replace(regex, (match) => {
    return `<span class="highlight-badge"><span class="badge-icon">🔒</span>${match}</span>`
  })
})

function copyText(text, successMsg = '已复制到剪贴板') {
  if (!text) return
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => {
      ElMessage.success(successMsg)
    }).catch(() => {
      fallbackCopy(text, successMsg)
    })
  } else {
    fallbackCopy(text, successMsg)
  }
}

function fallbackCopy(text, successMsg) {
  const textarea = document.createElement('textarea')
  textarea.value = text
  document.body.appendChild(textarea)
  textarea.select()
  try {
    document.execCommand('copy')
    ElMessage.success(successMsg)
  } catch {
    ElMessage.error('复制失败，请手动选择复制')
  } finally {
    document.body.removeChild(textarea)
  }
}
</script>

<style scoped>
.diff-viewer {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background-color: #ffffff;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.diff-viewer__toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background-color: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.diff-viewer__status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #f59e0b;
}

.toolbar-title {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}

.stats-tag {
  font-weight: 500;
}

.diff-viewer__content {
  display: flex;
  min-height: 140px;
}

/* 并排对比模式 */
.mode--side-by-side {
  flex-direction: row;
}

.mode--side-by-side .diff-pane {
  flex: 1;
  min-width: 0;
}

.mode--side-by-side .diff-pane--original {
  border-right: 1px solid #e2e8f0;
}

/* 上下分栏模式 */
.mode--stacked {
  flex-direction: column;
}

.mode--stacked .diff-pane--original {
  border-bottom: 1px solid #e2e8f0;
}

.diff-pane {
  display: flex;
  flex-direction: column;
}

.pane-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 14px;
  background-color: #f1f5f9;
  border-bottom: 1px solid #e2e8f0;
}

.pane-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}

.badge--original {
  background-color: #e2e8f0;
  color: #475569;
}

.badge--redacted {
  background-color: #fef3c7;
  color: #b45309;
}

.pane-body {
  padding: 12px 14px;
  flex: 1;
  overflow-y: auto;
  max-height: 280px;
}

.text-content {
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
}

.text-original {
  color: #475569;
}

.text-redacted {
  color: #0f172a;
}

:deep(.highlight-badge) {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  background-color: #fef3c7;
  color: #b45309;
  border: 1px solid #fde68a;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
  margin: 0 2px;
}

:deep(.badge-icon) {
  font-size: 11px;
}

.masked-tags-bar {
  padding: 8px 14px;
  background-color: #fafaf9;
  border-top: 1px solid #f1f5f9;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.tags-label {
  font-size: 12px;
  color: #78716c;
  font-weight: 500;
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.masked-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.tag-type {
  font-weight: 600;
}

.tag-match {
  text-decoration: line-through;
  opacity: 0.7;
}

.arrow-icon {
  font-size: 10px;
}

.tag-rep {
  font-weight: 600;
  color: #d97706;
}
</style>
