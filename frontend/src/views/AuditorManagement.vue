<template>
  <div class="auditor-management">
    <el-card>
      <!-- 工具栏 -->
      <div class="toolbar">
        <div class="search-bar">
          <el-input 
            v-model="searchKeyword" 
            placeholder="搜索用户名/姓名" 
            clearable 
            style="width: 200px;"
            @keyup.enter="fetchAuditors"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-select v-model="filterRole" placeholder="角色筛选" clearable style="width: 120px; margin-left: 10px;" @change="fetchAuditors">
            <el-option label="全部角色" value="" />
            <el-option label="管理员" value="admin" />
            <el-option label="审核员" value="auditor" />
          </el-select>
          <el-button type="primary" style="margin-left: 10px;" @click="fetchAuditors">搜索</el-button>
        </div>
        <div class="action-bar">
          <el-button type="success" @click="showAddDialog">
            <el-icon><Plus /></el-icon>
            添加审核员
          </el-button>
        </div>
      </div>

      <!-- 审核员列表 -->
      <el-table :data="auditors" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="email" label="邮箱" min-width="180" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'primary'">
              {{ row.role === 'admin' ? '管理员' : '审核员' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-switch 
              v-model="row.is_active" 
              @change="toggleAuditorStatus(row)"
              :disabled="row.id === currentAuditorId"
            />
          </template>
        </el-table-column>
        <el-table-column label="审核统计" width="180">
          <template #default="{ row }">
            <div class="audit-stats">
              <span class="stat-item">
                <el-icon><CircleCheck /></el-icon>
                {{ row.approved_count || 0 }}
              </span>
              <span class="stat-item">
                <el-icon><Warning /></el-icon>
                {{ row.review_count || 0 }}
              </span>
              <span class="stat-item">
                <el-icon><CircleClose /></el-icon>
                {{ row.rejected_count || 0 }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="last_login" label="最后登录" width="160">
          <template #default="{ row }">
            {{ formatDate(row.last_login) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" text size="small" @click="showEditDialog(row)">编辑</el-button>
            <el-button type="warning" text size="small" @click="showResetPasswordDialog(row)">重置密码</el-button>
            <el-button 
              type="danger" 
              text 
              size="small" 
              @click="deleteAuditor(row)"
              :disabled="row.id === currentAuditorId || row.role === 'admin'"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加/编辑审核员弹窗 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="isEdit ? '编辑审核员' : '添加审核员'" 
      width="500px"
      @close="resetForm"
    >
      <el-form :model="auditorForm" :rules="formRules" ref="formRef" label-width="100px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="auditorForm.username" placeholder="请输入用户名" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="auditorForm.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="auditorForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="auditorForm.role" placeholder="请选择角色" style="width: 100%;">
            <el-option label="审核员" value="auditor" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="密码" prop="password" v-if="!isEdit">
          <el-input v-model="auditorForm.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword" v-if="!isEdit">
          <el-input v-model="auditorForm.confirmPassword" type="password" placeholder="请确认密码" show-password />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="auditorForm.is_active" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码弹窗 -->
    <el-dialog v-model="resetPasswordVisible" title="重置密码" width="400px">
      <el-form :model="resetPasswordForm" :rules="resetPasswordRules" ref="resetPasswordRef" label-width="100px">
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="resetPasswordForm.newPassword" type="password" placeholder="请输入新密码" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="resetPasswordForm.confirmPassword" type="password" placeholder="请确认新密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetPasswordVisible = false">取消</el-button>
        <el-button type="primary" @click="resetPassword">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, CircleCheck, Warning, CircleClose } from '@element-plus/icons-vue'
import axios from 'axios'

const auditorId = localStorage.getItem('auditor_id')
const currentAuditorId = computed(() => parseInt(auditorId || '0'))

const loading = ref(false)
const submitLoading = ref(false)
const auditors = ref<any[]>([])
const searchKeyword = ref('')
const filterRole = ref('')

const dialogVisible = ref(false)
const resetPasswordVisible = ref(false)
const isEdit = ref(false)
const formRef = ref()
const resetPasswordRef = ref()

const auditorForm = reactive({
  id: 0,
  username: '',
  name: '',
  email: '',
  role: 'auditor',
  password: '',
  confirmPassword: '',
  is_active: true
})

const resetPasswordForm = reactive({
  auditorId: 0,
  newPassword: '',
  confirmPassword: ''
})

const validateConfirmPassword = (rule: any, value: string, callback: any) => {
  if (value !== auditorForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const validateResetConfirmPassword = (rule: any, value: string, callback: any) => {
  if (value !== resetPasswordForm.newPassword) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const formRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度在3到20个字符', trigger: 'blur' }
  ],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  email: [
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const resetPasswordRules = {
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateResetConfirmPassword, trigger: 'blur' }
  ]
}

const fetchAuditors = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/auditors', {
      params: { auditor_id: auditorId }
    })
    let data = res.data
    
    // 前端过滤
    if (searchKeyword.value) {
      data = data.filter((a: any) => 
        a.username?.includes(searchKeyword.value) || 
        a.name?.includes(searchKeyword.value)
      )
    }
    if (filterRole.value) {
      data = data.filter((a: any) => a.role === filterRole.value)
    }
    
    auditors.value = data
  } catch (e) {
    ElMessage.error('获取审核员列表失败')
  } finally {
    loading.value = false
  }
}

const showAddDialog = () => {
  isEdit.value = false
  resetForm()
  dialogVisible.value = true
}

const showEditDialog = (auditor: any) => {
  isEdit.value = true
  Object.assign(auditorForm, {
    id: auditor.id,
    username: auditor.username,
    name: auditor.name,
    email: auditor.email || '',
    role: auditor.role,
    is_active: auditor.is_active
  })
  dialogVisible.value = true
}

const showResetPasswordDialog = (auditor: any) => {
  resetPasswordForm.auditorId = auditor.id
  resetPasswordForm.newPassword = ''
  resetPasswordForm.confirmPassword = ''
  resetPasswordVisible.value = true
}

const resetForm = () => {
  Object.assign(auditorForm, {
    id: 0,
    username: '',
    name: '',
    email: '',
    role: 'auditor',
    password: '',
    confirmPassword: '',
    is_active: true
  })
}

const submitForm = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    if (isEdit.value) {
      await axios.put(`/api/auditors/${auditorForm.id}`, {
        name: auditorForm.name,
        email: auditorForm.email,
        role: auditorForm.role,
        is_active: auditorForm.is_active,
        auditor_id: auditorId
      })
      ElMessage.success('更新成功')
    } else {
      await axios.post('/api/auditors', { ...auditorForm, auditor_id: auditorId })
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    fetchAuditors()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    submitLoading.value = false
  }
}

const resetPassword = async () => {
  const valid = await resetPasswordRef.value.validate().catch(() => false)
  if (!valid) return

  try {
    await axios.post(`/api/auditors/${resetPasswordForm.auditorId}/reset-password`, {
      new_password: resetPasswordForm.newPassword,
      auditor_id: auditorId
    })
    ElMessage.success('密码重置成功')
    resetPasswordVisible.value = false
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '密码重置失败')
  }
}

const toggleAuditorStatus = async (auditor: any) => {
  try {
    await axios.put(`/api/auditors/${auditor.id}`, {
      is_active: auditor.is_active,
      auditor_id: auditorId
    })
    ElMessage.success(auditor.is_active ? '已启用' : '已禁用')
  } catch (e: any) {
    auditor.is_active = !auditor.is_active
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

const deleteAuditor = async (auditor: any) => {
  try {
    await ElMessageBox.confirm(`确定要删除审核员"${auditor.name}"吗？`, '确认删除', { type: 'warning' })
    
    await axios.delete(`/api/auditors/${auditor.id}`, {
      params: { auditor_id: auditorId }
    })
    ElMessage.success('删除成功')
    fetchAuditors()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(() => {
  fetchAuditors()
})
</script>

<style scoped>
.auditor-management {
  padding: 0;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #ebeef5;
}

.search-bar {
  display: flex;
  align-items: center;
}

.action-bar {
  display: flex;
  gap: 10px;
}

.audit-stats {
  display: flex;
  gap: 15px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #606266;
  font-size: 13px;
}

.stat-item .el-icon {
  color: #909399;
}

.stat-item:first-child .el-icon {
  color: #67C23A;
}

.stat-item:last-child .el-icon {
  color: #F56C6C;
}
</style>
