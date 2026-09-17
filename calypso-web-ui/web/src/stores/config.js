import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '../api/client'
import { ElMessage, ElMessageBox } from 'element-plus'

export const useConfigStore = defineStore('config', () => {
  // 状态变量
  const baseUrl = ref(localStorage.getItem('calypso_base_url') || 'https://us1.calypsoai.app')
  const token = ref(localStorage.getItem('calypso_api_token') || '')
  const projectId = ref(localStorage.getItem('calypso_project_id') || '')
  const mode = ref(localStorage.getItem('calypso_mode') || 'demo') // 'demo' | 'online'
  const isConnected = ref(true) // demo 模式默认连通
  const loading = ref(false)
  const appName = ref('Calypso AI 中文安全运营控制台')
  const version = ref('1.0.0')

  // 计算属性
  const isDemo = computed(() => mode.value === 'demo')
  const isOnline = computed(() => mode.value === 'online')

  // 初始化与获取系统状态
  async function fetchStatus() {
    loading.value = true
    try {
      const data = await apiClient.get('/system/status')
      if (data && data.status === 'ok') {
        if (data.mode) mode.value = data.mode
        if (data.base_url) baseUrl.value = data.base_url
        if (data.app_name) appName.value = data.app_name
        if (data.version) version.value = data.version
        if (data.project_id) projectId.value = data.project_id
        
        // 保持 localStorage 同步
        localStorage.setItem('calypso_mode', mode.value)
        localStorage.setItem('calypso_base_url', baseUrl.value)
        if (projectId.value) localStorage.setItem('calypso_project_id', projectId.value)
      }
      return data
    } catch (err) {
      console.warn('获取系统状态失败，保留本地缓存配置', err)
    } finally {
      loading.value = false
    }
  }

  // 更新配置并与后端同步
  async function updateConfig({
    base_url = null,
    token: newToken = null,
    project_id = null,
    mode: newMode = null,
    test_connection = false
  } = {}) {
    loading.value = true
    try {
      const payload = {
        base_url: base_url !== null ? base_url : baseUrl.value,
        token: newToken !== null ? newToken : token.value,
        project_id: project_id !== null ? project_id : projectId.value,
        mode: newMode !== null ? newMode : mode.value,
        test_connection
      }

      const res = await apiClient.post('/system/config', payload)
      if (res && res.status === 'ok') {
        if (payload.base_url) {
          baseUrl.value = payload.base_url
          localStorage.setItem('calypso_base_url', payload.base_url)
        }
        if (newToken !== null) {
          token.value = newToken
          if (newToken) {
            localStorage.setItem('calypso_api_token', newToken)
          } else {
            localStorage.removeItem('calypso_api_token')
          }
        }
        if (payload.project_id !== null) {
          projectId.value = payload.project_id
          localStorage.setItem('calypso_project_id', payload.project_id)
        }
        if (payload.mode) {
          mode.value = payload.mode
          localStorage.setItem('calypso_mode', payload.mode)
        }

        if (res.connection_test) {
          isConnected.value = res.connection_test.status === 'ok'
        }

        ElMessage.success(res.message || '配置更新成功')
      }
      return res
    } catch (err) {
      ElMessage.error('更新系统配置失败')
      throw err
    } finally {
      loading.value = false
    }
  }

  // 连通性测试
  async function testConnection(targetUrl = null, targetToken = null) {
    loading.value = true
    try {
      const payload = {
        base_url: targetUrl !== null ? targetUrl : baseUrl.value,
        token: targetToken !== null ? targetToken : token.value
      }
      const res = await apiClient.post('/system/test-connection', payload)
      isConnected.value = res.status === 'ok'
      if (res.status === 'ok') {
        ElMessage.success(res.message || '服务连接正常')
      } else {
        ElMessage.warning(res.message || '连接失败，请检查配置')
      }
      return res
    } catch (err) {
      isConnected.value = false
      throw err
    } finally {
      loading.value = false
    }
  }

  // 切换运行模式（演示 / 在线）- 从 Online 切换到 Demo 必须二次确认
  async function toggleMode() {
    const nextMode = mode.value === 'demo' ? 'online' : 'demo'
    if (mode.value === 'online' && nextMode === 'demo') {
      try {
        await ElMessageBox.confirm(
          '当前处于生产/私有集群在线模式 (Online)。切换为内置演示模式 (Demo) 将仅展示静态模拟数据，断开与 Calypso AI 实时集群的同步。确定要切换为演示模式吗？',
          '切换运行模式二次确认',
          {
            confirmButtonText: '确认切换为演示模式',
            cancelButtonText: '取消',
            type: 'warning',
            confirmButtonClass: 'el-button--danger'
          }
        )
      } catch {
        return false
      }
    }
    await updateConfig({ mode: nextMode, test_connection: nextMode === 'online' })
    return true
  }


  return {
    baseUrl,
    token,
    projectId,
    mode,
    isConnected,
    loading,
    appName,
    version,
    isDemo,
    isOnline,
    fetchStatus,
    updateConfig,
    testConnection,
    toggleMode
  }
})
