<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-header">
        <h1>财务报销系统</h1>
        <p>上传发票 · 便捷报销</p>
      </div>
      
      <el-tabs v-model="activeTab" class="login-tabs">
        <el-tab-pane label="登录" name="login">
          <el-card class="login-card">
            <el-form :model="loginForm" :rules="loginRules" ref="loginFormRef">
              <el-form-item prop="username">
                <el-input 
                  v-model="loginForm.username" 
                  placeholder="请输入用户名"
                  prefix-icon="User"
                  size="large"
                />
              </el-form-item>
              
              <el-form-item prop="password">
                <el-input 
                  v-model="loginForm.password" 
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
          </el-card>
        </el-tab-pane>
        
        <el-tab-pane label="注册" name="register">
          <el-card class="login-card">
            <el-form :model="registerForm" :rules="registerRules" ref="registerFormRef">
              <el-form-item prop="username">
                <el-input 
                  v-model="registerForm.username" 
                  placeholder="请输入用户名"
                  prefix-icon="User"
                  size="large"
                />
              </el-form-item>
              
              <el-form-item prop="name">
                <el-input 
                  v-model="registerForm.name" 
                  placeholder="请输入真实姓名"
                  prefix-icon="UserFilled"
                  size="large"
                />
              </el-form-item>
              
              <el-form-item prop="password">
                <el-input 
                  v-model="registerForm.password" 
                  type="password" 
                  placeholder="请输入密码（至少6位）"
                  prefix-icon="Lock"
                  size="large"
                  show-password
                />
              </el-form-item>
              
              <el-form-item prop="confirmPassword">
                <el-input 
                  v-model="registerForm.confirmPassword" 
                  type="password" 
                  placeholder="请再次输入密码"
                  prefix-icon="Lock"
                  size="large"
                  show-password
                />
              </el-form-item>
              
              <el-form-item prop="email">
                <el-input 
                  v-model="registerForm.email" 
                  placeholder="请输入邮箱（可选）"
                  prefix-icon="Message"
                  size="large"
                />
              </el-form-item>
              
              <el-form-item prop="phone">
                <el-input 
                  v-model="registerForm.phone" 
                  placeholder="请输入手机号（可选）"
                  prefix-icon="Phone"
                  size="large"
                />
              </el-form-item>
              
              <el-form-item prop="department">
                <el-input 
                  v-model="registerForm.department" 
                  placeholder="请输入部门（可选）"
                  prefix-icon="OfficeBuilding"
                  size="large"
                />
              </el-form-item>
              
              <el-form-item>
                <el-button 
                  type="primary" 
                  size="large" 
                  style="width: 100%"
                  :loading="loading"
                  @click="handleRegister"
                >
                  注册
                </el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </el-tab-pane>
      </el-tabs>
      
      <div class="login-footer">
        <el-link type="primary" @click="goToAdminLogin">管理员登录</el-link>
        <span class="divider">|</span>
        <span>© 2026 财务报销系统</span>
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
const activeTab = ref('login')
const loading = ref(false)

const loginFormRef = ref()
const registerFormRef = ref()

const loginForm = reactive({
  username: '',
  password: ''
})

const registerForm = reactive({
  username: '',
  name: '',
  password: '',
  confirmPassword: '',
  email: '',
  phone: '',
  department: ''
})

const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const registerRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符', trigger: 'blur' }
  ],
  name: [{ required: true, message: '请输入真实姓名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule: any, value: string, callback: any) => {
        if (value !== registerForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const handleLogin = async () => {
  const valid = await loginFormRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const res = await axios.post('/api/user/login', loginForm)
    
    localStorage.setItem('user_id', res.data.id)
    localStorage.setItem('user_name', res.data.name)
    localStorage.setItem('user_username', res.data.username)
    localStorage.setItem('user_department', res.data.department || '')
    
    ElMessage.success(`欢迎回来，${res.data.name}！`)
    router.push('/user')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}

const handleRegister = async () => {
  const valid = await registerFormRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await axios.post('/api/user/register', {
      username: registerForm.username,
      password: registerForm.password,
      name: registerForm.name,
      email: registerForm.email || undefined,
      phone: registerForm.phone || undefined,
      department: registerForm.department || undefined
    })
    
    ElMessage.success('注册成功，请登录')
    activeTab.value = 'login'
    loginForm.username = registerForm.username
    loginForm.password = ''
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '注册失败')
  } finally {
    loading.value = false
  }
}

const goToAdminLogin = () => {
  router.push('/login')
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #409EFF 0%, #67C23A 100%);
}

.login-container {
  width: 420px;
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

.login-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
}

.login-tabs :deep(.el-tabs__item) {
  color: white;
  font-size: 16px;
}

.login-tabs :deep(.el-tabs__item.is-active) {
  color: white;
  font-weight: bold;
}

.login-tabs :deep(.el-tabs__nav-wrap::after) {
  background-color: rgba(255, 255, 255, 0.3);
}

.login-card {
  border-radius: 10px;
  padding: 10px;
}

.login-footer {
  text-align: center;
  color: white;
  margin-top: 20px;
  font-size: 12px;
  opacity: 0.8;
}

.login-footer .divider {
  margin: 0 10px;
}
</style>
