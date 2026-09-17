<template>
  <div class="rule-library-view">
    <!-- 头部搜索与操作 -->
    <el-card class="filter-card" shadow="never">
      <div class="filter-header">
        <div class="filter-left">
          <el-input
            v-model="searchQuery"
            placeholder="搜索规则名称、分类或描述..."
            clearable
            style="width: 320px"
            prefix-icon="Search"
          />
          <el-select v-model="filterCategory" placeholder="规则分类" clearable style="width: 180px">
            <el-option label="全部类别" value="" />
            <el-option label="提示词注入" value="prompt_injection" />
            <el-option label="模型越狱" value="jailbreak" />
            <el-option label="凭证防泄露" value="secrets" />
            <el-option label="对抗混淆" value="obfuscation" />
            <el-option label="PII脱敏" value="pii" />
            <el-option label="自定义规则" value="custom" />
          </el-select>
        </div>
        <div class="filter-right">
          <el-button type="primary" icon="Plus" @click="openCreateDialog">
            新建自定义规则
          </el-button>
          <el-button icon="Refresh" @click="fetchRules" :loading="loading">
            刷新规则库
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 规则表格 -->
    <el-card class="table-card" shadow="never">
      <el-table
        :data="filteredRules"
        v-loading="loading"
        style="width: 100%"
        border
        stripe
        row-key="id"
      >
        <el-table-column label="规则名称" min-width="220">
          <template #default="{ row }">
            <div class="rule-name-cell">
              <span class="rule-title">{{ row.name }}</span>
              <el-tag
                size="small"
                :type="row.is_system ? 'info' : 'success'"
                effect="plain"
                class="rule-type-tag"
              >
                {{ row.is_system ? '系统核心' : '自定义' }}
              </el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="category" label="分类" width="140">
          <template #default="{ row }">
            <el-tag size="small" :type="getCategoryTagType(row.category)">
              {{ getCategoryLabel(row.category) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="direction" label="检测方向" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">
              {{ row.direction === 'request' ? '输入端 (Prompt)' : row.direction === 'response' ? '输出端 (Response)' : '双向检测' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="default_mode" label="默认处理动作" width="130" align="center">
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="row.default_mode === 'block' ? 'danger' : row.default_mode === 'redact' ? 'warning' : 'primary'"
            >
              {{ row.default_mode === 'block' ? '直接阻断' : row.default_mode === 'redact' ? '脱敏替换' : '审计标记' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="description" label="防护规则描述" min-width="280" show-overflow-tooltip />

        <el-table-column label="规则标识 ID" width="220">
          <template #default="{ row }">
            <el-tooltip :content="row.id" placement="top">
              <el-text class="id-mono" truncated>{{ row.id }}</el-text>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建规则对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="新建自定义 Guardrail 规则"
      width="560px"
      destroy-on-close
    >
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="110px">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="form.name" placeholder="例如：商业机密保护规则" />
        </el-form-item>
        <el-form-item label="规则分类" prop="category">
          <el-select v-model="form.category" style="width: 100%">
            <el-option label="自定义业务拦截" value="custom" />
            <el-option label="提示词注入" value="prompt_injection" />
            <el-option label="越狱诱导" value="jailbreak" />
            <el-option label="合规与敏感词" value="compliance" />
          </el-select>
        </el-form-item>
        <el-form-item label="检测方向" prop="direction">
          <el-radio-group v-model="form.direction">
            <el-radio label="both">双向检测</el-radio>
            <el-radio label="request">输入端 (Prompt)</el-radio>
            <el-radio label="response">输出端 (Response)</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="响应动作" prop="default_mode">
          <el-radio-group v-model="form.default_mode">
            <el-radio label="block">直接阻断 (Block)</el-radio>
            <el-radio label="flag">标记预警 (Flag)</el-radio>
            <el-radio label="redact">脱敏替换 (Redact)</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="匹配条件/关键词" prop="input_data">
          <el-input
            v-model="form.input_data"
            type="textarea"
            :rows="3"
            placeholder="输入触发该扫描器规则的关键词或模式定义（多个可用换行或逗号分隔）"
          />
        </el-form-item>
        <el-form-item label="规则描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            placeholder="说明此规则的防护目标及业务背景"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleCreateRule" :loading="submitting">
            保存规则
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getRules, createRule } from '../../api/guardrails'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const submitting = ref(false)
const rulesList = ref([])
const searchQuery = ref('')
const filterCategory = ref('')

const dialogVisible = ref(false)
const formRef = ref(null)
const form = ref({
  name: '',
  category: 'custom',
  direction: 'both',
  default_mode: 'block',
  input_data: '',
  description: ''
})

const formRules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  category: [{ required: true, message: '请选择规则分类', trigger: 'change' }]
}

const fetchRules = async () => {
  loading.value = true
  try {
    const res = await getRules()
    rulesList.value = res.rules || []
  } catch (err) {
    console.error('获取规则库失败', err)
  } finally {
    loading.value = false
  }
}

const filteredRules = computed(() => {
  return rulesList.value.filter((r) => {
    const matchesSearch =
      !searchQuery.value ||
      r.name?.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      r.description?.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      r.id?.toLowerCase().includes(searchQuery.value.toLowerCase())
    const matchesCat = !filterCategory.value || r.category === filterCategory.value
    return matchesSearch && matchesCat
  })
})

const getCategoryLabel = (cat) => {
  const map = {
    prompt_injection: '提示词注入',
    jailbreak: '模型越狱',
    secrets: '凭证防泄露',
    obfuscation: '对抗混淆',
    pii: '个人隐私脱敏',
    custom: '自定义扩展'
  }
  return map[cat] || cat || '其他'
}

const getCategoryTagType = (cat) => {
  const map = {
    prompt_injection: 'danger',
    jailbreak: 'danger',
    secrets: 'warning',
    obfuscation: 'info',
    pii: 'success',
    custom: 'primary'
  }
  return map[cat] || 'info'
}

const openCreateDialog = () => {
  form.value = {
    name: '',
    category: 'custom',
    direction: 'both',
    default_mode: 'block',
    input_data: '',
    description: ''
  }
  dialogVisible.value = true
}

const handleCreateRule = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      await createRule(form.value)
      ElMessage.success('自定义规则创建成功')
      dialogVisible.value = false
      await fetchRules()
    } catch (err) {
      console.error(err)
    } finally {
      submitting.value = false
    }
  })
}

onMounted(() => {
  fetchRules()
})
</script>

<style scoped>
.rule-library-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filter-card {
  border-radius: 8px;
}

.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.filter-left,
.filter-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.table-card {
  border-radius: 8px;
}

.rule-name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rule-title {
  font-weight: 600;
  color: #1e293b;
}

.id-mono {
  font-family: monospace;
  font-size: 12px;
  color: #64748b;
}
</style>
