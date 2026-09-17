<template>
  <div class="view-container">
    <el-card shadow="never" class="header-card">
      <div class="card-title">
        <el-icon class="title-icon"><DataAnalysis /></el-icon>
        <h2>态势大屏 (Dashboard)</h2>
      </div>
      <p class="description">
        实时展示大模型调用护栏拦截态势、关键安全违规比例、扫描器触发排行及多维度安全防御指标。
      </p>
    </el-card>

    <div class="placeholder-content">
      <el-empty description="态势看板模块已挂载，数据指标将在 Task 5 接入渲染" :image-size="120" />
    </div>
  </div>
</template>

<script setup>
// Dashboard Placeholder
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
