<template>
  <div class="settings-view">
    <!-- 顶部标题栏 -->
    <div class="settings-header">
      <div class="header-intro">
        <h2 class="view-title">系统与服务连接配置 (Settings)</h2>
        <span class="view-desc">
          配置 Calypso AI 护栏服务端点连接参数、API 凭证与运行模式，支持一键切换内置智能演示与生产私有化集群。
        </span>
      </div>

      <div class="header-actions">
        <el-tag
          :type="configStore.isOnline ? (configStore.isConnected ? 'success' : 'danger') : 'warning'"
          effect="dark"
        >
          {{ configStore.isOnline ? (configStore.isConnected ? '● 在线服务已连通' : '✕ 在线服务未连通') : '● 内置演示模式 (Demo)' }}
        </el-tag>
      </div>
    </div>

    <!-- 主表单与指南卡片左右双栏布局 -->
    <div class="settings-layout">
      <!-- 左栏：核心配置表单 -->
      <div class="settings-card">
        <div class="card-header">
          <span class="card-title">
            <el-icon class="title-icon"><Tools /></el-icon>
            网关通信与凭证配置
          </span>
          <span class="card-badge">服务环境设置</span>
        </div>

        <el-form
          ref="formRef"
          :model="form"
          label-position="top"
          class="config-form"
        >
          <!-- 运行模式切换 -->
          <el-form-item label="系统运行模式 (System Mode):">
            <div class="mode-select-box">
              <el-radio-group v-model="form.mode" size="large">
                <el-radio-button label="demo">
                  <span class="mode-opt-title">内置演示模式 (Demo)</span>
                </el-radio-button>
                <el-radio-button label="online">
                  <span class="mode-opt-title">生产/私有集群模式 (Online)</span>
                </el-radio-button>
              </el-radio-group>
            </div>
            <div class="field-hint">
              <span v-if="form.mode === 'demo'">
                💡 演示模式无需配置外部 Calypso 服务，由内置 MockDataEngine 智能模拟注入、越狱、凭证及敏感脱敏等全套攻防规则。
              </span>
              <span v-else>
                🌐 在线模式将直连指定的 Calypso 集群 API，执行真实的安全策略扫描与红队评估。
              </span>
            </div>
          </el-form-item>

          <!-- 服务 Base URL -->
          <el-form-item label="Calypso API 基础地址 (Base URL):">
            <el-input
              v-model="form.baseUrl"
              placeholder="例如: https://us1.calypsoai.app 或 http://10.0.0.1:8080"
              clearable
            >
              <template #prepend>
                <el-icon><Link /></el-icon>
              </template>
            </el-input>
            <div class="field-hint">Calypso 生产网关或私有化托管集群的根 API 地址。</div>
          </el-form-item>

          <!-- API Token -->
          <el-form-item label="API 认证密钥 (Token / Key):">
            <el-input
              v-model="form.token"
              :type="showToken ? 'text' : 'password'"
              placeholder="请输入 Calypso API 访问凭据 (Bearer Token)"
              clearable
            >
              <template #prepend>
                <el-icon><Key /></el-icon>
              </template>
              <template #append>
                <el-button @click="showToken = !showToken">
                  <el-icon>
                    <View v-if="!showToken" />
                    <Hide v-else />
                  </el-icon>
                </el-button>
              </template>
            </el-input>
            <div class="field-hint">用于 HTTP 请求头 Authorization: Bearer {token} 鉴权。</div>
          </el-form-item>

          <!-- 默认关联项目 ID -->
          <el-form-item label="关联项目标识 (Project ID):">
            <el-input
              v-model="form.projectId"
              placeholder="可选，例如 proj_default_china"
              clearable
            >
              <template #prepend>
                <el-icon><Folder /></el-icon>
              </template>
            </el-input>
            <div class="field-hint">安全护栏策略归属的项目 ID，留空则使用服务端默认值。</div>
          </el-form-item>

          <!-- 操作按钮栏 -->
          <div class="form-actions-bar">
            <!-- Ping 测试连接 -->
            <el-button
              type="warning"
              plain
              :loading="testingConnection"
              @click="handleTestConnection"
            >
              <el-icon><Connection /></el-icon>
              <span>测试连接 (Ping)</span>
            </el-button>

            <!-- 保存配置 -->
            <el-button
              type="primary"
              :loading="saving"
              @click="handleSaveConfig"
            >
              <el-icon><Check /></el-icon>
              <span>保存配置</span>
            </el-button>
          </div>

          <!-- 测试连接结果反馈栏 -->
          <div v-if="pingResult" class="ping-result-box" :class="pingResult.status === 'ok' ? 'ping--success' : 'ping--error'">
            <div class="ping-header">
              <el-icon v-if="pingResult.status === 'ok'"><CircleCheckFilled /></el-icon>
              <el-icon v-else><CircleCloseFilled /></el-icon>
              <span class="ping-title">{{ pingResult.message }}</span>
              <span v-if="pingLatency !== null" class="ping-latency">响应延时: {{ pingLatency }} ms</span>
            </div>
            <div v-if="pingResult.details" class="ping-details">
              {{ JSON.stringify(pingResult.details) }}
            </div>
          </div>
        </el-form>
      </div>

      <!-- 右栏：配置指南与架构说明卡片 -->
      <div class="guide-column">
        <!-- 快速指南卡片 -->
        <div class="settings-card guide-card">
          <div class="card-header">
            <span class="card-title">
              <el-icon class="title-icon"><Notebook /></el-icon>
              Calypso API Token 获取指南
            </span>
          </div>
          <div class="guide-steps">
            <div class="step-item">
              <div class="step-num">1</div>
              <div class="step-text">
                <strong>登录控制台</strong>
                <p>登录 Calypso AI 官方平台或私有部署管理后台 (SaaS: us1.calypsoai.app)。</p>
              </div>
            </div>

            <div class="step-item">
              <div class="step-num">2</div>
              <div class="step-text">
                <strong>创建 API Key</strong>
                <p>进入 <code>Settings &gt; API Keys &gt; Generate New Key</code>，选择相应项目权限。</p>
              </div>
            </div>

            <div class="step-item">
              <div class="step-num">3</div>
              <div class="step-text">
                <strong>填入并测试连接</strong>
                <p>将生成的 Key 填入左侧 API Token 输入框，点击「测试连接」验证网络与鉴权连通性。</p>
              </div>
            </div>
          </div>
        </div>

        <!-- 架构图与网关接入机制卡片 -->
        <div class="settings-card arch-card">
          <div class="card-header">
            <span class="card-title">
              <el-icon class="title-icon"><Cpu /></el-icon>
              架构与网关拦截机制
            </span>
          </div>

          <div class="arch-content">
            <div class="arch-flow">
              <div class="flow-node node-client">客户端 / 业务 Agent</div>
              <div class="flow-arrow">➔ (HTTPS)</div>
              <div class="flow-node node-gateway">
                <span class="node-title">Calypso 网关护栏</span>
                <span class="node-sub">注入/越狱/脱敏过滤</span>
              </div>
              <div class="flow-arrow">➔ (安全放行)</div>
              <div class="flow-node node-llm">企业大模型 (LLM)</div>
            </div>

            <div class="arch-bullets">
              <div class="bullet-item">
                <el-icon class="bullet-icon"><Lock /></el-icon>
                <span><strong>首道防线拦截:</strong> 恶意载荷在到达大模型前直接被网关拦截，节约算力成本并彻底隔绝模型越狱风险。</span>
              </div>
              <div class="bullet-item">
                <el-icon class="bullet-icon"><View /></el-icon>
                <span><strong>动态敏感脱敏:</strong> 中国大陆手机号、身份证、银行卡数据在请求转发前执行高保真掩码替换，合规出境。</span>
              </div>
              <div class="bullet-item">
                <el-icon class="bullet-icon"><DocumentChecked /></el-icon>
                <span><strong>全审计存证:</strong> 每一笔判定结果与上下文全量记录审计日志，满足等保与金融合规监管要求。</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useConfigStore } from '../stores/config'


const configStore = useConfigStore()

const showToken = ref(false)
const saving = ref(false)
const testingConnection = ref(false)
const pingResult = ref(null)
const pingLatency = ref(null)

const form = reactive({
  mode: 'demo',
  baseUrl: '',
  token: '',
  projectId: ''
})

function syncFromStore() {
  form.mode = configStore.mode || 'demo'
  form.baseUrl = configStore.baseUrl || 'https://us1.calypsoai.app'
  form.token = configStore.token || ''
  form.projectId = configStore.projectId || ''
}

// 测试连通性
async function handleTestConnection() {
  testingConnection.value = true
  pingResult.value = null
  pingLatency.value = null

  const startTime = performance.now()
  try {
    const res = await configStore.testConnection(form.baseUrl, form.token)
    const endTime = performance.now()
    pingLatency.value = Math.max(8, Math.round(endTime - startTime))
    pingResult.value = res
  } catch (err) {
    const endTime = performance.now()
    pingLatency.value = Math.round(endTime - startTime)
    pingResult.value = {
      status: 'failed',
      message: err.response?.data?.detail || err.message || '连接失败，请检查网络或地址'
    }
  } finally {
    testingConnection.value = false
  }
}

// 保存配置
async function handleSaveConfig() {
  if (configStore.mode === 'online' && form.mode === 'demo') {
    try {
      await ElMessageBox.confirm(
        '当前系统处于生产/私有集群在线模式 (Online)。切换为内置演示模式 (Demo) 将仅展示静态模拟数据，断开与 Calypso AI 实时集群的同步。确定要切换为演示模式吗？',
        '切换运行模式二次确认',
        {
          confirmButtonText: '确认切换为演示模式',
          cancelButtonText: '取消',
          type: 'warning',
          confirmButtonClass: 'el-button--danger'
        }
      )
    } catch {
      form.mode = 'online'
      return
    }
  }

  saving.value = true
  try {
    await configStore.updateConfig({
      base_url: form.baseUrl,
      token: form.token,
      project_id: form.projectId,
      mode: form.mode,
      test_connection: form.mode === 'online'
    })
    ElMessage.success('系统配置已成功保存')
  } catch (err) {

    console.error('保存配置失败:', err)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await configStore.fetchStatus()
  syncFromStore()
})
</script>

<style scoped>
.settings-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.settings-header {
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

/* 左右分栏布局 */
.settings-layout {
  display: grid;
  grid-template-columns: 1.25fr 1fr;
  gap: 20px;
  align-items: start;
}

@media (max-width: 1024px) {
  .settings-layout {
    grid-template-columns: 1fr;
  }
}

.settings-card {
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 14px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-icon {
  color: #3b82f6;
}

.card-badge {
  font-size: 12px;
  color: #94a3b8;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.mode-select-box {
  width: 100%;
}

.mode-opt-title {
  font-weight: 600;
  padding: 0 4px;
}

.field-hint {
  font-size: 12px;
  color: #64748b;
  margin-top: 6px;
  line-height: 1.5;
}

.form-actions-bar {
  display: flex;
  gap: 12px;
  margin-top: 10px;
  padding-top: 16px;
  border-top: 1px solid #f1f5f9;
}

.ping-result-box {
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 13px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ping--success {
  background-color: #f0fdf4;
  border: 1px solid #86efac;
  color: #166534;
}

.ping--error {
  background-color: #fef2f2;
  border: 1px solid #fca5a5;
  color: #991b1b;
}

.ping-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.ping-latency {
  font-size: 11px;
  background: rgba(0, 0, 0, 0.05);
  padding: 1px 6px;
  border-radius: 4px;
  margin-left: auto;
}

.ping-details {
  font-size: 11px;
  font-family: monospace;
  opacity: 0.85;
}

/* 右栏指南卡片 */
.guide-column {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.guide-steps {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.step-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.step-num {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #eff6ff;
  color: #2563eb;
  font-weight: 700;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}

.step-text {
  font-size: 13px;
  color: #334155;
  line-height: 1.5;
}

.step-text p {
  margin: 2px 0 0 0;
  color: #64748b;
  font-size: 12px;
}

.step-text code {
  background: #f1f5f9;
  padding: 1px 4px;
  border-radius: 4px;
  font-family: monospace;
}

/* 架构流展示 */
.arch-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.arch-flow {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
  padding: 14px 10px;
  border-radius: 8px;
  border: 1px dashed #cbd5e1;
  font-size: 11px;
}

.flow-node {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 8px 10px;
  text-align: center;
  font-weight: 600;
  color: #1e293b;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.node-gateway {
  border-color: #3b82f6;
  background: #eff6ff;
  color: #1d4ed8;
  display: flex;
  flex-direction: column;
}

.node-sub {
  font-size: 9px;
  font-weight: normal;
  color: #2563eb;
}

.flow-arrow {
  color: #94a3b8;
  font-weight: bold;
}

.arch-bullets {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.bullet-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 12px;
  line-height: 1.5;
  color: #475569;
}

.bullet-icon {
  color: #3b82f6;
  font-size: 14px;
  margin-top: 2px;
  flex-shrink: 0;
}
</style>
