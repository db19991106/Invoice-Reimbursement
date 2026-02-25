<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <el-col :span="4">
        <el-card class="stat-card">
          <div class="stat-content">
            <el-icon class="stat-icon total" :size="40"><Document /></el-icon>
            <div class="stat-info">
              <div class="stat-value">{{ stats.total }}</div>
              <div class="stat-label">总发票数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card class="stat-card">
          <div class="stat-content">
            <el-icon class="stat-icon pending" :size="40"><Clock /></el-icon>
            <div class="stat-info">
              <div class="stat-value">{{ stats.pending }}</div>
              <div class="stat-label">待审核</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card class="stat-card">
          <div class="stat-content">
            <el-icon class="stat-icon green" :size="40"><CircleCheck /></el-icon>
            <div class="stat-info">
              <div class="stat-value">{{ stats.approved }}</div>
              <div class="stat-label">绿色通道</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card class="stat-card">
          <div class="stat-content">
            <el-icon class="stat-icon yellow" :size="40"><Warning /></el-icon>
            <div class="stat-info">
              <div class="stat-value">{{ stats.review }}</div>
              <div class="stat-label">黄色通道</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card class="stat-card">
          <div class="stat-content">
            <el-icon class="stat-icon red" :size="40"><CircleClose /></el-icon>
            <div class="stat-info">
              <div class="stat-value">{{ stats.rejected }}</div>
              <div class="stat-label">红色通道</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="recent-card">
      <template #header>
        <div class="card-header">
          <span>最近上传的发票</span>
          <el-button type="primary" @click="$router.push('/upload')">
            <el-icon><Upload /></el-icon>
            上传新发票
          </el-button>
        </div>
      </template>
      
      <el-table :data="invoices" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="invoice_no" label="发票号码" width="150" />
        <el-table-column prop="seller_name" label="销售方" width="180" />
        <el-table-column prop="destination_city" label="出差地" width="100" />
        <el-table-column prop="expense_type" label="费用类型" width="120">
          <template #default="{ row }">
            {{ getExpenseTypeText(row.expense_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="金额" width="100">
          <template #default="{ row }">
            ¥{{ row.amount?.toFixed(2) || '0.00' }}
          </template>
        </el-table-column>
        <el-table-column prop="channel" label="通道" width="80">
          <template #default="{ row }">
            <el-tag :type="getChannelType(row.channel)">
              {{ getChannelText(row.channel) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewResult(row.id)">
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Document, Clock, Check, Close, Upload, CircleCheck, Warning, CircleClose } from '@element-plus/icons-vue'
import axios from 'axios'

const router = useRouter()

const stats = ref({
  total: 0,
  pending: 0,
  approved: 0,
  rejected: 0,
  review: 0
})

const invoices = ref([])

const fetchStats = async () => {
  try {
    const res = await axios.get('/api/stats')
    stats.value = res.data
  } catch (e) {
    console.error('Failed to fetch stats:', e)
  }
}

const fetchInvoices = async () => {
  try {
    const res = await axios.get('/api/invoices?limit=10')
    invoices.value = res.data
  } catch (e) {
    console.error('Failed to fetch invoices:', e)
  }
}

const getExpenseTypeText = (type: string) => {
  const map: Record<string, string> = {
    'accommodation': '住宿费',
    'transport_air': '机票',
    'transport_train': '火车票',
    'city_transport': '市内交通',
    'meal': '伙食补助',
    'business_entertainment': '业务招待'
  }
  return map[type] || type || '-'
}

const getChannelType = (channel: string) => {
  const map: Record<string, string> = {
    'green': 'success',
    'yellow': 'warning',
    'red': 'danger',
    'pending': 'info'
  }
  return map[channel] || 'info'
}

const getChannelText = (channel: string) => {
  const map: Record<string, string> = {
    'green': '绿通',
    'yellow': '黄通',
    'red': '红通',
    'pending': '待审'
  }
  return map[channel] || channel || '-'
}

const getStatusType = (status: string) => {
  const map: Record<string, string> = {
    pending: 'info',
    approve: 'success',
    reject: 'danger',
    review: 'warning'
  }
  return map[status] || 'info'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    pending: '待审核',
    approve: '已通过',
    reject: '已驳回',
    review: '需复核'
  }
  return map[status] || status
}

const viewResult = (id: number) => {
  router.push(`/result/${id}`)
}

onMounted(() => {
  fetchStats()
  fetchInvoices()
})
</script>

<style scoped>
.dashboard {
  padding: 20px;
}

.stat-card {
  margin-bottom: 20px;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 20px;
}

.stat-icon {
  padding: 10px;
  border-radius: 8px;
}

.stat-icon.total {
  background-color: #ecf5ff;
  color: #409eff;
}

.stat-icon.pending {
  background-color: #fdf6ec;
  color: #e6a23c;
}

.stat-icon.green {
  background-color: #f0f9eb;
  color: #67c23a;
}

.stat-icon.yellow {
  background-color: #fdf6ec;
  color: #e6a23c;
}

.stat-icon.red {
  background-color: #fef0f0;
  color: #f56c6c;
}

.stat-icon.approved {
  background-color: #f0f9eb;
  color: #67c23a;
}

.stat-icon.rejected {
  background-color: #fef0f0;
  color: #f56c6c;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.recent-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
