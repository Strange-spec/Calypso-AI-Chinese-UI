<template>
  <div class="guardrails-center-view">
    <div class="center-header">
      <div class="header-intro">
        <h2 class="view-title">安全护栏运营中心 (Guardrails Center)</h2>
        <span class="view-desc">
          对齐 Calypso AI 原生防护架构：配置规则库 ➔ 创建业务项目空间 ➔ 关联生效规则 ➔ 在线测试有效性 ➔ 监控实时检测流水。
        </span>
      </div>
    </div>

    <!-- 顶部核心流程导航 Tabs -->
    <el-tabs v-model="activeTab" type="border-card" class="center-tabs" @tab-change="handleTabChange">
      <!-- Tab 1: 实时护栏测试台 -->
      <el-tab-pane name="playground">
        <template #label>
          <span class="tab-label">
            <el-icon><Monitor /></el-icon>
            <span>实时护栏测试台</span>
          </span>
        </template>
        <Playground :initial-project-id="targetProjectId" />
      </el-tab-pane>

      <!-- Tab 2: 项目空间与规则关联 -->
      <el-tab-pane name="projects">
        <template #label>
          <span class="tab-label">
            <el-icon><FolderOpened /></el-icon>
            <span>业务项目与规则绑定</span>
          </span>
        </template>
        <ProjectList @select-project="onSelectProjectForTesting" @select-for-testing="onSelectProjectForTesting" />
      </el-tab-pane>

      <!-- Tab 3: Guardrails 规则库 -->
      <el-tab-pane name="rules">
        <template #label>
          <span class="tab-label">
            <el-icon><Collection /></el-icon>
            <span>Guardrails 规则库</span>
          </span>
        </template>
        <RuleLibrary />
      </el-tab-pane>

      <!-- Tab 4: 护栏检测日志流 -->
      <el-tab-pane name="logs">
        <template #label>
          <span class="tab-label">
            <el-icon><Tickets /></el-icon>
            <span>护栏检测日志流</span>
          </span>
        </template>
        <GuardrailsLogs :filter-project-id="targetProjectId" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectsStore } from '../stores/projects'
import Playground from './Playground.vue'
import ProjectList from './guardrails/ProjectList.vue'
import RuleLibrary from './guardrails/RuleLibrary.vue'
import GuardrailsLogs from './guardrails/GuardrailsLogs.vue'

const route = useRoute()
const router = useRouter()
const projectsStore = useProjectsStore()

const activeTab = ref(route.query.tab || 'playground')
const targetProjectId = ref(route.query.project_id || '')

const handleTabChange = async (tabName) => {
  router.replace({ query: { ...route.query, tab: tabName } })
  if (['playground', 'projects', 'logs'].includes(tabName)) {
    await projectsStore.fetchProjects()
  }
}

const onSelectProjectForTesting = (project) => {
  targetProjectId.value = project.id
  activeTab.value = 'playground'
  router.replace({ query: { ...route.query, tab: 'playground', project_id: project.id } })
}

watch(
  () => route.query.tab,
  (newTab) => {
    if (newTab && ['playground', 'projects', 'rules', 'logs'].includes(newTab)) {
      activeTab.value = newTab
    }
  }
)

watch(
  () => route.query.project_id,
  (newProjId) => {
    if (newProjId) {
      targetProjectId.value = newProjId
    }
  }
)

onMounted(async () => {
  if (route.query.tab) {
    activeTab.value = route.query.tab
  }
  if (route.query.project_id) {
    targetProjectId.value = route.query.project_id
  }
  await projectsStore.fetchProjects()
})
</script>

<style scoped>
.guardrails-center-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.center-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.view-title {
  margin: 0 0 4px 0;
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
}

.view-desc {
  font-size: 13px;
  color: #64748b;
}

.center-tabs {
  border-radius: 8px;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
}

.center-tabs :deep(.el-tabs__header) {
  background-color: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

.center-tabs :deep(.el-tabs__item) {
  height: 46px;
  line-height: 46px;
  font-size: 14px;
  color: #475569;
}

.center-tabs :deep(.el-tabs__item.is-active) {
  font-weight: 600;
  color: #0284c7;
  background-color: #ffffff;
}

.tab-label {
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>
