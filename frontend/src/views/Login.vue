<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-header">
        <h1>财务报销审核系统</h1>
        <p>智能审核 · 高效管理</p>
      </div>
      
      <el-card class="login-card">
        <el-form :model="form" :rules="rules" ref="formRef">
          <el-form-item prop="username">
            <el-input 
              v-model="form.username" 
              placeholder="请输入用户名"
              prefix-icon="User"
              size="large"
            />
          </el-form-item>
          
          <el-form-item prop="password">
            <el-input 
              v-model="form.password" 
              type="password" 
              placeholder="请输入密码"
              prefix-icon="Lock"
              size="large"
              show-password
              @keyup.enter="handleLogin"
            />
          </el-form-item>
          
          <el-form-item>
            <el-button 
              type="primary" 
              size="large" 
              style="width: 100%"
              :loading="loading"
              @click="handleLogin"
            >
              登录
            </el-button>
          </el-form-item>
        </el-form>
        
        <div class="login-tips">
          <el-divider>默认账号</el-divider>
          <div class="account-info">
            <p><strong>管理员：</strong>admin / admin123</p>
            <p><strong>审核员：</strong>auditor / auditor123</p>
          </div>
        </div>
      </el-card>
      
      <div class="login-footer">
        <p>© 2026 财务报销智能审核系统</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const formRef = ref()
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const handleLogin = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const res = await axios.post('/api/login', form)
    
    localStorage.setItem('auditor_id', res.data.id)
    localStorage.setItem('auditor_name', res.data.name)
    localStorage.setItem('auditor_role', res.data.role)
    
    ElMessage.success(`欢迎回来，${res.data.name}！`)
    router.push('/')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-container {
  width: 400px;
}

.login-header {
  text-align: center;
  color: white;
  margin-bottom: 30px;
}

.login-header h1 {
  font-size: 28px;
  margin-bottom: 10px;
}

.login-header p {
  font-size: 14px;
  opacity: 0.8;
}

.login-card {
  padding: 20px;
  border-radius: 10px;
}

.login-tips {
  margin-top: 20px;
}

.account-info {
  background: #f5f7fa;
  padding: 15px;
  border-radius: 5px;
  font-size: 13px;
  color: #606266;
}

.account-info p {
  margin: 5px 0;
}

.login-footer {
  text-align: center;
  color: white;
  margin-top: 30px;
  font-size: 12px;
  opacity: 0.7;
}
</style>
