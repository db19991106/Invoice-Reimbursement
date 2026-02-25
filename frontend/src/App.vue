<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-content">
        <h1 class="title">财务报销智能审核系统</h1>
        <el-menu
          mode="horizontal"
          :router="true"
          :default-active="$route.path"
          class="header-menu"
        >
          <el-menu-item index="/">
            <el-icon><DataAnalysis /></el-icon>
            仪表盘
          </el-menu-item>
          <el-menu-item index="/upload">
            <el-icon><Upload /></el-icon>
            上传发票
          </el-menu-item>
        </el-menu>
      </div>
    </el-header>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { DataAnalysis, Upload } from '@element-plus/icons-vue'
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.app-container {
  min-height: 100vh;
  background-color: #f5f7fa;
}

.app-header {
  background-color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  padding: 0;
}

.header-content {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
  padding: 0 20px;
}

.title {
  font-size: 20px;
  color: #303133;
  font-weight: 600;
}

.header-menu {
  border-bottom: none;
}

.app-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}
</style>
