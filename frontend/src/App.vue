<template>
  <router-view />
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
