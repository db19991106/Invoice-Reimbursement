<template>
  <div class="user-management-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <el-button type="primary" @click="fetchUsers">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>
      
      <el-table :data="users" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="email" label="邮箱" width="180" />
        <el-table-column prop="phone" label="手机号" width="120" />
        <el-table-column prop="department" label="部门" width="120" />
        <el-table-column prop="invoice_count" label="上传发票数" width="100">
          <template #default="{ row }">
            <el-link type="primary" @click="viewUserInvoices(row.id, row.name)">
              {{ row.invoice_count }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'">
              {{ row.is_active ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="170">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="last_login" label="最后登录" width="170">
          <template #default="{ row }">
            {{ row.last_login ? formatDate(row.last_login) : '-' }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <el-dialog v-model="invoicesDialogVisible" title="用户上传的发票" width="90%">
      <el-table :data="userInvoices" v-loading="invoicesLoading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="invoice_no" label="发票号码" width="150" />
        <el-table-column prop="total_amount" label="金额" width="100">
          <template #default="{ row }">
            ¥{{ row.total_amount?.toFixed(2) || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="seller_name" label="销售方" min-width="150" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="上传时间" width="170">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewInvoiceDetail(row.id)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const router = useRouter()
const auditorId = localStorage.getItem('auditor_id')

const loading = ref(false)
const users = ref<any[]>([])

const invoicesDialogVisible = ref(false)
const invoicesLoading = ref(false)
const userInvoices = ref<any[]>([])
const selectedUserId = ref<number | null>(null)
const selectedUserName = ref('')

const fetchUsers = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/users', {
      params: { auditor_id: auditorId }
    })
    users.value = res.data
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '获取用户列表失败')
  } finally {
    loading.value = false
  }
}

const viewUserInvoices = async (userId: number, userName: string) => {
  selectedUserId.value = userId
  selectedUserName.value = userName
  invoicesDialogVisible.value = true
  invoicesLoading.value = true
  
  try {
    const res = await axios.get(`/api/users/${userId}/invoices`, {
      params: { auditor_id: auditorId }
    })
    userInvoices.value = res.data
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '获取发票列表失败')
  } finally {
    invoicesLoading.value = false
  }
}

const viewInvoiceDetail = (id: number) => {
  invoicesDialogVisible.value = false
  router.push(`/invoices/${id}`)
}

const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    pending: 'warning',
    processing: 'info',
    approve: 'success',
    reject: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    pending: '待审核',
    processing: '处理中',
    approve: '已通过',
    reject: '已驳回'
  }
  return texts[status] || status
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  fetchUsers()
})
</script>

<style scoped>
.user-management-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
