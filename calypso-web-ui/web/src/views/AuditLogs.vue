<template>
  <div class="view-container">
    <el-card shadow="never" class="header-card">
      <div class="card-title">
        <el-icon class="title-icon"><Document /></el-icon>
        <h2>安全审计日志 (Audit Logs)</h2>
      </div>
      <p class="description">
        记录大模型每次交互的安全判定流水、输入输出脱敏留痕、触发扫描器类型及响应耗时，满足合规审计要求。
      </p>
    </el-card>

    <div class="placeholder-content">
      <el-empty description="审计日志模块已挂载，日志检索与分页导出将在 Task 5 接入渲染" :image-size="120" />
    </div>
  </div>
</template>

<script setup>
// AuditLogs Placeholder
</script>

<style scoped>
.view-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.header-card {
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
.placeholder-content {
  background: #ffffff;
  border-radius: 8px;
  padding: 40px;
  display: flex;
  justify-content: center;
}
</style>
