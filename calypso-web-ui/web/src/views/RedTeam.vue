<template>
  <div class="view-container">
    <el-card shadow="never" class="header-card">
      <div class="card-title">
        <el-icon class="title-icon"><Aim /></el-icon>
        <h2>红队任务与报告 (Red Team)</h2>
      </div>
      <p class="description">
        管理大模型红蓝对抗评测任务，支持导入与解析对抗攻击 CSV 测试集，统计攻击穿透率与脆弱性分布。
      </p>
    </el-card>

    <div class="placeholder-content">
      <el-empty description="红队任务模块已挂载，报告解析与对抗任务将在 Task 5 接入渲染" :image-size="120" />
    </div>
  </div>
</template>

<script setup>
// RedTeam Placeholder
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
