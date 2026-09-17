<template>
  <el-config-provider :locale="zhCn">
    <div class="app-layout">
      <el-container class="main-container">
        <!-- 侧边导航栏 -->
        <el-aside width="240px" class="app-aside">
          <div class="brand-header">
            <div class="brand-logo">🛡️</div>
            <div class="brand-text">
              <div class="brand-title">Calypso AI</div>
              <div class="brand-subtitle">安全护栏运营控制台</div>
            </div>
          </div>

          <el-menu
            :default-active="activeMenu"
            router
            class="sidebar-menu"
            background-color="#0f172a"
            text-color="#94a3b8"
            active-text-color="#38bdf8"
          >
            <el-menu-item index="/dashboard">
              <el-icon><DataAnalysis /></el-icon>
              <span>态势大屏</span>
            </el-menu-item>
            <el-menu-item index="/guardrails">
              <el-icon><Monitor /></el-icon>
              <span>安全护栏运营中心</span>
            </el-menu-item>
            <el-menu-item index="/redteam">
              <el-icon><Aim /></el-icon>
              <span>红队任务与报告</span>
            </el-menu-item>
            <el-menu-item index="/audit">
              <el-icon><Document /></el-icon>
              <span>安全审计日志</span>
            </el-menu-item>
            <el-menu-item index="/settings">
              <el-icon><Setting /></el-icon>
              <span>系统与连接配置</span>
            </el-menu-item>
          </el-menu>

          <div class="aside-footer">
            <div class="version-tag">版本 v{{ configStore.version }}</div>
            <div class="copyright">Calypso AI CN Edition</div>
          </div>
        </el-aside>

        <!-- 主内容区域 -->
        <el-container class="content-container">
          <!-- 顶部状态与快捷操作栏 -->
          <el-header height="60px" class="app-header">
            <div class="header-left">
              <span class="page-title">{{ currentRouteTitle }}</span>
            </div>

            <div class="header-right">
              <!-- 当前服务地址展示 -->
              <el-tooltip :content="`目标服务 API: ${configStore.baseUrl}`" placement="bottom">
                <div class="api-tag">
                  <el-icon><Connection /></el-icon>
                  <span class="url-text">{{ shortBaseUrl }}</span>
                </div>
              </el-tooltip>

              <!-- 运行模式徽章与快捷切换 -->
              <div class="mode-badge-wrap">
                <el-tag
                  v-if="configStore.isOnline"
                  :type="configStore.isConnected ? 'success' : 'danger'"
                  effect="dark"
                  class="status-tag"
                >
                  <span class="status-dot online"></span>
                  {{ configStore.isConnected ? '在线连接' : '连接异常' }}
                </el-tag>
                <el-tag
                  v-else
                  type="warning"
                  effect="dark"
                  class="status-tag"
                >
                  <span class="status-dot demo"></span>
                  演示模式 (Demo)
                </el-tag>
              </div>

              <!-- 模式快捷切换开关 -->
              <el-tooltip content="点击快速切换在线/演示模式" placement="bottom">
                <el-button
                  size="small"
                  plain
                  :type="configStore.isOnline ? 'success' : 'warning'"
                  @click="configStore.toggleMode()"
                >
                  <el-icon><Switch /></el-icon>
                  <span>切换为{{ configStore.isOnline ? '演示模式' : '在线模式' }}</span>
                </el-button>
              </el-tooltip>

              <!-- 设置入口快捷按钮 -->
              <el-tooltip content="系统与连接配置" placement="bottom">
                <el-button circle size="small" @click="$router.push('/settings')">
                  <el-icon><Setting /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
          </el-header>

          <!-- 路由视图挂载区 -->
          <el-main class="app-main">
            <router-view />
          </el-main>
        </el-container>
      </el-container>
    </div>
  </el-config-provider>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { useConfigStore } from './stores/config'

const route = useRoute()
const configStore = useConfigStore()

const activeMenu = computed(() => {
  if (route.path.startsWith('/playground') || route.path.startsWith('/guardrails')) {
    return '/guardrails'
  }
  return route.path
})

const currentRouteTitle = computed(() => {
  return route.meta?.title || '控制台'
})

const shortBaseUrl = computed(() => {
  try {
    const url = new URL(configStore.baseUrl)
    return url.host
  } catch {
    return configStore.baseUrl || '未配置'
  }
})

onMounted(async () => {
  await configStore.fetchStatus()
})
</script>

<style>
/* 全局基础重置样式 */
html, body, #app {
  margin: 0;
  padding: 0;
  height: 100%;
  width: 100%;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color: #1e293b;
  background-color: #f8fafc;
}
</style>

<style scoped>
.app-layout {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}
.main-container {
  height: 100%;
  width: 100%;
}

/* 侧边栏样式 */
.app-aside {
  background-color: #0f172a;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.15);
  user-select: none;
}
.brand-header {
  height: 60px;
  display: flex;
  align-items: center;
  padding: 0 18px;
  gap: 12px;
  border-bottom: 1px solid #1e293b;
}
.brand-logo {
  font-size: 26px;
  line-height: 1;
}
.brand-text {
  display: flex;
  flex-direction: column;
}
.brand-title {
  color: #f8fafc;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.5px;
}
.brand-subtitle {
  color: #64748b;
  font-size: 11px;
}
.sidebar-menu {
  flex: 1;
  border-right: none;
}
:deep(.el-menu-item) {
  margin: 4px 10px;
  border-radius: 6px;
  height: 44px;
  line-height: 44px;
}
:deep(.el-menu-item.is-active) {
  background-color: #1e293b !important;
  font-weight: 600;
}
:deep(.el-menu-item:hover) {
  background-color: #1e293b88 !important;
  color: #f8fafc !important;
}
.aside-footer {
  padding: 16px;
  border-top: 1px solid #1e293b;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.version-tag {
  color: #64748b;
  font-size: 11px;
}
.copyright {
  color: #475569;
  font-size: 10px;
}

/* 主内容与顶部栏 */
.content-container {
  display: flex;
  flex-direction: column;
  background-color: #f8fafc;
  overflow: hidden;
}
.app-header {
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
}
.header-left .page-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}
.api-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #64748b;
  background: #f1f5f9;
  padding: 4px 10px;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
}
.url-text {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mode-badge-wrap {
  display: flex;
  align-items: center;
}
.status-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
}
.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  display: inline-block;
}
.status-dot.online {
  background-color: #22c55e;
  box-shadow: 0 0 6px #22c55e;
}
.status-dot.demo {
  background-color: #eab308;
  box-shadow: 0 0 6px #eab308;
}

/* 主展示区域 */
.app-main {
  padding: 20px;
  overflow-y: auto;
  box-sizing: border-box;
}
</style>
