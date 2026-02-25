<template>
  <el-container class="layout-container">
    <el-aside width="220px" class="sidebar">
      <div class="logo">
        <h2>财务审核系统</h2>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        class="sidebar-menu"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
        router
      >
        <el-menu-item index="/">
          <el-icon><DataAnalysis /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        
        <el-menu-item index="/invoices">
          <el-icon><Document /></el-icon>
          <span>发票管理</span>
        </el-menu-item>
        
        <el-menu-item index="/upload">
          <el-icon><Upload /></el-icon>
          <span>上传发票</span>
        </el-menu-item>
        
        <el-menu-item index="/statistics">
          <el-icon><TrendCharts /></el-icon>
          <span>统计分析</span>
        </el-menu-item>
        
        <el-menu-item index="/employees">
          <el-icon><User /></el-icon>
          <span>员工管理</span>
        </el-menu-item>
        
        <el-menu-item index="/auditors" v-if="auditorRole === 'admin'">
          <el-icon><Setting /></el-icon>
          <span>审核员管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <h3>{{ pageTitle }}</h3>
        </div>
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-icon><User /></el-icon>
              <span>{{ auditorName }}</span>
              <el-tag size="small" type="warning" v-if="auditorRole === 'admin'">管理员</el-tag>
              <el-tag size="small" v-else>审核员</el-tag>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人信息</el-dropdown-item>
                <el-dropdown-item command="password">修改密码</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
    
    <!-- 修改密码弹窗 -->
    <el-dialog v-model="passwordDialogVisible" title="修改密码" width="400px">
      <el-form :model="passwordForm" :rules="passwordRules" ref="passwordFormRef" label-width="80px">
        <el-form-item label="旧密码" prop="old_password">
          <el-input v-model="passwordForm.old_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="passwordForm.new_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input v-model="passwordForm.confirm_password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="changePassword">确定</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DataAnalysis, Document, Upload, TrendCharts, User, Setting } from '@element-plus/icons-vue'
import axios from 'axios'

const router = useRouter()
const route = useRoute()

const auditorName = localStorage.getItem('auditor_name') || '用户'
const auditorRole = localStorage.getItem('auditor_role') || 'auditor'
const auditorId = localStorage.getItem('auditor_id')

const activeMenu = computed(() => route.path)

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    '/': '仪表盘',
    '/invoices': '发票管理',
    '/upload': '上传发票',
    '/statistics': '统计分析',
    '/employees': '员工管理',
    '/auditors': '审核员管理'
  }
  return titles[route.path] || '财务审核系统'
})

const passwordDialogVisible = ref(false)
const passwordFormRef = ref()
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const passwordRules = {
  old_password: [{ required: true, message: '请输入旧密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { 
      validator: (rule: any, value: string, callback: any) => {
        if (value !== passwordForm.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const handleCommand = (command: string) => {
  switch (command) {
    case 'profile':
      ElMessage.info('个人信息功能开发中')
      break
    case 'password':
      passwordDialogVisible.value = true
      break
    case 'logout':
      ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        type: 'warning'
      }).then(() => {
        localStorage.removeItem('auditor_id')
        localStorage.removeItem('auditor_name')
        localStorage.removeItem('auditor_role')
        router.push('/login')
      }).catch(() => {})
      break
  }
}

const changePassword = async () => {
  const valid = await passwordFormRef.value.validate().catch(() => false)
  if (!valid) return
  
  try {
    await axios.post('/api/change-password', {
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password
    })
    ElMessage.success('密码修改成功')
    passwordDialogVisible.value = false
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '密码修改失败')
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.sidebar {
  background-color: #304156;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  border-bottom: 1px solid #3a4a5d;
}

.logo h2 {
  font-size: 16px;
  margin: 0;
}

.sidebar-menu {
  border-right: none;
}

.header {
  background: white;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
}

.header-left h3 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 4px;
}

.user-info:hover {
  background: #f5f7fa;
}

.main {
  background: #f5f7fa;
  padding: 20px;
}
</style>
