<template>
  <div class="view-container">
    <el-card shadow="never" class="header-card">
      <div class="card-title">
        <el-icon class="title-icon"><Monitor /></el-icon>
        <h2>实时护栏测试台 (Playground)</h2>
      </div>
      <p class="description">
        提供提示词注入、越狱、PII 泄漏、毒性言论等常见攻击用例测试，直观查看护栏阻断、脱敏前后文本对比与扫描器打分。
      </p>
    </el-card>

    <div class="placeholder-content">
      <el-empty description="护栏测试台已挂载，实时交互与脱敏对比将在 Task 5 接入渲染" :image-size="120" />
    </div>
  </div>
</template>

<script setup>
// Playground Placeholder
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
