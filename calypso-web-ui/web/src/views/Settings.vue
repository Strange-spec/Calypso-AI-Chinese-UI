<template>
  <div class="view-container">
    <el-card shadow="never" class="header-card">
      <div class="card-title">
        <el-icon class="title-icon"><Setting /></el-icon>
        <h2>系统与连接配置 (Settings)</h2>
      </div>
      <p class="description">
        配置 Calypso AI 原生后端 API 接口地址、认证 Token、运行模式（演示 / 在线），并提供网络连通性探测。
      </p>
    </el-card>

    <el-card shadow="never" class="form-card">
      <template #header>
        <div class="section-title">
          <span>Calypso 连接与环境参数</span>
          <el-tag :type="configStore.isOnline ? 'success' : 'warning'" effect="dark">
            {{ configStore.isOnline ? '在线连接模式' : '离线演示模式 (Demo)' }}
          </el-tag>
        </div>
      </template>

      <el-form :model="form" label-width="140px" label-position="left">
        <el-form-item label="系统运行模式">
          <el-radio-group v-model="form.mode">
            <el-radio-button label="demo">演示模式 (离线数据引擎)</el-radio-button>
            <el-radio-button label="online">在线模式 (连接 Calypso API)</el-radio-button>
          </el-radio-group>
          <div class="form-hint">
            演示模式使用内置的预设攻击样本与模拟评估引擎；在线模式通过 BFF 代理实时连接 Calypso 服务端。
          </div>
        </el-form-item>

        <el-form-item label="Calypso API 地址">
          <el-input
            v-model="form.baseUrl"
            placeholder="例如: https://us1.calypsoai.app"
            clearable
          />
          <div class="form-hint">
            Calypso AI 实例的根 URL，无需在末尾附加 /v1 或其他路径。
          </div>
        </el-form-item>

        <el-form-item label="API Token">
          <el-input
            v-model="form.token"
            type="password"
            show-password
            placeholder="输入 Calypso 个人访问令牌 (API Key)"
            clearable
          />
          <div class="form-hint">
            用于向 Calypso 后端发起鉴权请求，若为空则在演示模式下运行。
          </div>
        </el-form-item>

        <el-form-item label="默认项目 ID">
          <el-input
            v-model="form.projectId"
            placeholder="可选: 如 default 或特定的 Project UUID"
            clearable
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="configStore.loading"
            @click="handleSave"
          >
            保存配置
          </el-button>
          <el-button
            :loading="configStore.loading"
            @click="handleTestConnection"
          >
            测试连通性
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, watch } from 'vue'
import { useConfigStore } from '../stores/config'

const configStore = useConfigStore()

const form = reactive({
  baseUrl: configStore.baseUrl,
  token: configStore.token,
  projectId: configStore.projectId,
  mode: configStore.mode
})

watch(
  () => [configStore.baseUrl, configStore.token, configStore.projectId, configStore.mode],
  ([newBaseUrl, newToken, newProjectId, newMode]) => {
    form.baseUrl = newBaseUrl
    form.token = newToken
    form.projectId = newProjectId
    form.mode = newMode
  }
)

async function handleSave() {
  await configStore.updateConfig({
    base_url: form.baseUrl,
    token: form.token,
    project_id: form.projectId,
    mode: form.mode,
    test_connection: form.mode === 'online'
  })
}

async function handleTestConnection() {
  await configStore.testConnection(form.baseUrl, form.token)
}
</script>

<style scoped>
.view-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.header-card, .form-card {
  border-radius: 8px;
  background: #ffffff;
}
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.card-title h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}
.title-icon {
  font-size: 20px;
  color: #2563eb;
}
.description {
  margin: 8px 0 0 0;
  font-size: 13px;
  color: #64748b;
}
.section-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  font-size: 15px;
  color: #1e293b;
}
.form-hint {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}
</style>
