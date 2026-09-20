<template>
  <div class="project-list-view">
    <!-- 顶部操作栏 -->
    <el-card class="action-card" shadow="never">
      <div class="action-header">
        <div class="action-left">
          <el-input
            v-model="searchQuery"
            placeholder="搜索项目名称、Project ID 或描述..."
            clearable
            style="width: 320px"
            prefix-icon="Search"
          />
        </div>
        <div class="action-right">
          <el-button type="primary" icon="Plus" @click="openCreateDialog">
            新建项目空间
          </el-button>
          <el-button icon="Refresh" @click="fetchData" :loading="loading">
            刷新项目
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 项目卡片/表格 -->
    <div v-loading="loading" class="projects-container">
      <el-row :gutter="16">
        <el-col
          :xs="24"
          :sm="24"
          :md="12"
          :lg="8"
          v-for="project in filteredProjects"
          :key="project.id"
          class="project-col"
        >
          <el-card class="project-card" shadow="hover">
            <!-- 头部：项目名称与类型 -->
            <div class="project-card-header">
              <div class="project-name-group">
                <span class="project-title">{{ project.name }}</span>
                <el-tag size="small" :type="getTypeTag(project.type)">
                  {{ project.type || 'app' }}
                </el-tag>
              </div>
              <el-dropdown trigger="click" @command="(cmd) => handleCommand(cmd, project)">
                <el-button link icon="MoreFilled" />
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="edit">编辑规则配置</el-dropdown-item>
                    <el-dropdown-item command="test" divided>进入测试台</el-dropdown-item>
                    <el-dropdown-item command="delete" style="color: #f43f5e">删除项目</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>

            <!-- Project ID 高亮与一键复制 -->
            <div class="project-id-row">
              <span class="id-label">Project ID:</span>
              <el-tag size="small" effect="plain" class="id-value">
                {{ project.id }}
              </el-tag>
              <el-button
                link
                type="primary"
                size="small"
                icon="CopyDocument"
                @click="copyId(project.id)"
              >
                复制
              </el-button>
            </div>

            <!-- 描述 -->
            <div class="project-desc">
              {{ project.description || '暂无业务描述' }}
            </div>

            <!-- 绑定的 Guardrails 规则 -->
            <div class="rules-section">
              <div class="rules-header">
                <span class="rules-title">已绑定 Guardrail 规则</span>
                <el-badge
                  :value="getScannersCount(project)"
                  :type="getScannersCount(project) > 0 ? 'primary' : 'info'"
                />
              </div>
              <div class="rules-tags">
                <template v-if="getScannersList(project).length > 0">
                  <el-tag
                    v-for="scanner in getScannersList(project).slice(0, 4)"
                    :key="scanner.id"
                    size="small"
                    class="rule-pill"
                    :type="scanner.mode === 'block' ? 'danger' : scanner.mode === 'redact' ? 'warning' : 'primary'"
                  >
                    {{ scanner.name || getRuleNameById(scanner.id) }}
                  </el-tag>
                  <el-tag
                    v-if="getScannersList(project).length > 4"
                    size="small"
                    type="info"
                    class="rule-pill"
                  >
                    +{{ getScannersList(project).length - 4 }} 更多
                  </el-tag>
                </template>
                <div v-else class="empty-rules">尚未关联任何安全规则</div>
              </div>
            </div>

            <!-- 底部操作按钮 -->
            <div class="project-card-footer">
              <el-button
                size="small"
                icon="Edit"
                @click="openEditDialog(project)"
              >
                配置规则
              </el-button>
              <el-button
                type="primary"
                size="small"
                icon="VideoPlay"
                @click="goToPlayground(project)"
              >
                测试该项目
              </el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 创建 / 编辑项目对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? '配置项目安全护栏规则' : '创建新业务项目空间'"
      width="640px"
      destroy-on-close
    >
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="100px">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="form.name" placeholder="例如：智能金融客服 Agent" />
        </el-form-item>
        <el-form-item label="项目类型" prop="type">
          <el-select v-model="form.type" style="width: 100%">
            <el-option label="业务应用 (App)" value="app" />
            <el-option label="对话机器人 (Chat)" value="chat" />
            <el-option label="智能体工作流 (Agentic)" value="agentic" />
            <el-option label="全局防御空间 (Global)" value="global" />
          </el-select>
        </el-form-item>
        <el-form-item label="项目描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            placeholder="说明项目的业务场景及安全需求"
          />
        </el-form-item>

        <!-- 关联 Guardrails 规则选择器 -->
        <el-form-item label="关联规则" required>
          <div class="rules-selector-container">
            <div class="rules-selector-hint">
              请勾选当前项目需要启用的安全护栏规则（测试台将仅对此类规则进行评估拦截）：
            </div>
            <div class="rules-checkbox-group">
              <div
                v-for="rule in availableRules"
                :key="rule.id"
                class="rule-select-item"
                :class="{ active: isRuleSelected(rule.id) }"
              >
                <el-checkbox
                  :model-value="isRuleSelected(rule.id)"
                  @update:model-value="(val) => toggleRuleSelection(rule, val)"
                >
                  <span class="rule-name">{{ rule.name }}</span>
                </el-checkbox>
                <div class="rule-actions" v-if="isRuleSelected(rule.id)">
                  <el-select
                    v-model="getSelectedRule(rule.id).mode"
                    size="small"
                    style="width: 110px"
                  >
                    <el-option label="阻断 (Block)" value="block" />
                    <el-option label="脱敏 (Redact)" value="redact" />
                    <el-option label="标记 (Flag)" value="flag" />
                  </el-select>
                </div>
              </div>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSaveProject" :loading="submitting">
            保存配置
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getProjects, createProject, updateProject, deleteProject } from '../../api/projects'
import { getRules } from '../../api/guardrails'
import { useProjectsStore } from '../../stores/projects'
import { ElMessage, ElMessageBox } from 'element-plus'

const emit = defineEmits(['select-project'])
const projectsStore = useProjectsStore()

const loading = ref(false)
const submitting = ref(false)
const projectsList = computed(() => projectsStore.projects)
const availableRules = ref([])
const searchQuery = ref('')

const dialogVisible = ref(false)
const isEditing = ref(false)
const editingId = ref(null)
const formRef = ref(null)

const form = ref({
  name: '',
  type: 'app',
  description: '',
  scanners: []
})

const formRules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }]
}

const fetchData = async () => {
  loading.value = true
  try {
    const [_, ruleRes] = await Promise.all([projectsStore.fetchProjects(true), getRules()])
    availableRules.value = ruleRes.rules || []
  } catch (err) {
    console.error('获取项目与规则失败', err)
  } finally {
    loading.value = false
  }
}

const filteredProjects = computed(() => {
  if (!searchQuery.value) return projectsList.value
  const q = searchQuery.value.toLowerCase()
  return projectsList.value.filter(
    (p) =>
      p.name?.toLowerCase().includes(q) ||
      p.id?.toLowerCase().includes(q) ||
      p.description?.toLowerCase().includes(q)
  )
})

const getTypeTag = (type) => {
  const map = { global: 'warning', chat: 'success', agentic: 'danger', app: 'primary' }
  return map[type] || 'info'
}

const getScannersList = (project) => {
  return project.config?.scanners || []
}

const getScannersCount = (project) => {
  return getScannersList(project).length
}

const getRuleNameById = (id) => {
  const r = availableRules.value.find((item) => item.id === id)
  return r ? r.name : id
}

const isRuleSelected = (ruleId) => {
  return form.value.scanners.some((s) => s.id === ruleId)
}

const getSelectedRule = (ruleId) => {
  return form.value.scanners.find((s) => s.id === ruleId) || {}
}

const toggleRuleSelection = (rule, isChecked) => {
  if (isChecked) {
    if (!form.value.scanners.some((s) => s.id === rule.id)) {
      form.value.scanners.push({
        id: rule.id,
        name: rule.name,
        mode: rule.default_mode || 'block',
        blocking: rule.default_mode === 'block',
        enabled: true
      })
    }
  } else {
    form.value.scanners = form.value.scanners.filter((s) => s.id !== rule.id)
  }
}

const copyId = (id) => {
  navigator.clipboard.writeText(id)
  ElMessage.success('已复制 Project ID 到剪贴板')
}

const openCreateDialog = () => {
  isEditing.value = false
  editingId.value = null
  // 默认勾选核心规则
  const defaultScanners = availableRules.value
    .filter((r) => r.is_system)
    .map((r) => ({
      id: r.id,
      name: r.name,
      mode: r.default_mode || 'block',
      blocking: r.default_mode === 'block',
      enabled: true
    }))
  form.value = {
    name: '',
    type: 'app',
    description: '',
    scanners: defaultScanners
  }
  dialogVisible.value = true
}

const openEditDialog = (project) => {
  isEditing.value = true
  editingId.value = project.id
  const currentScanners = (project.config?.scanners || []).map((s) => ({
    id: s.id,
    name: s.name || getRuleNameById(s.id),
    mode: s.mode || (s.blocking ? 'block' : 'flag'),
    blocking: s.blocking !== false,
    enabled: s.enabled !== false
  }))
  form.value = {
    name: project.name,
    type: project.type || 'app',
    description: project.description || '',
    scanners: currentScanners
  }
  dialogVisible.value = true
}

const handleSaveProject = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      if (isEditing.value) {
        await updateProject(editingId.value, {
          name: form.value.name,
          type: form.value.type,
          description: form.value.description,
          scanners: form.value.scanners
        })
        ElMessage.success('项目与护栏规则更新成功')
      } else {
        await createProject({
          name: form.value.name,
          type: form.value.type,
          description: form.value.description,
          scanners: form.value.scanners
        })
        ElMessage.success('项目空间创建成功')
      }
      dialogVisible.value = false
      await fetchData()
    } catch (err) {
      console.error(err)
    } finally {
      submitting.value = false
    }
  })
}

const handleCommand = async (cmd, project) => {
  if (cmd === 'edit') {
    openEditDialog(project)
  } else if (cmd === 'test') {
    goToPlayground(project)
  } else if (cmd === 'delete') {
    try {
      await ElMessageBox.confirm(
        `确定删除项目【${project.name}】吗？删除后关联规则与检测历史将无法恢复。`,
        '风险提示',
        { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' }
      )
      await deleteProject(project.id)
      ElMessage.success('项目已删除')
      await fetchData()
    } catch (e) {
      // 取消
    }
  }
}

const goToPlayground = (project) => {
  emit('select-project', project)
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.project-list-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.action-card {
  border-radius: 8px;
}

.action-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.action-left,
.action-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.projects-container {
  min-height: 200px;
}

.project-col {
  margin-bottom: 16px;
}

.project-card {
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  height: 100%;
  transition: all 0.25s ease;
}

.project-card:hover {
  transform: translateY(-2px);
  border-color: #38bdf8;
}

.project-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}

.project-name-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.project-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.project-id-row {
  display: flex;
  align-items: center;
  gap: 6px;
  background-color: #f8fafc;
  padding: 6px 10px;
  border-radius: 6px;
  margin-bottom: 12px;
}

.id-label {
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
}

.id-value {
  font-family: monospace;
  font-size: 12px;
  color: #334155;
  background-color: #ffffff;
  border: 1px solid #e2e8f0;
  max-width: 170px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-desc {
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
  margin-bottom: 14px;
  min-height: 38px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.rules-section {
  background-color: #f1f5f9;
  border-radius: 6px;
  padding: 10px;
  margin-bottom: 16px;
}

.rules-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.rules-title {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.rules-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-height: 24px;
}

.rule-pill {
  font-size: 11px;
}

.empty-rules {
  font-size: 12px;
  color: #94a3b8;
  font-style: italic;
}

.project-card-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: auto;
  border-top: 1px solid #f1f5f9;
  padding-top: 12px;
}

/* 规则关联勾选面板 */
.rules-selector-container {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 12px;
  background-color: #f8fafc;
  max-height: 280px;
  overflow-y: auto;
  width: 100%;
}

.rules-selector-hint {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 10px;
}

.rules-checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rule-select-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  background-color: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
}

.rule-select-item.active {
  border-color: #38bdf8;
  background-color: #f0f9ff;
}

.rule-name {
  font-weight: 500;
  color: #1e293b;
}
</style>
