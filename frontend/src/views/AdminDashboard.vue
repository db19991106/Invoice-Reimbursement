<template>
  <div class="dashboard">
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
            <el-icon size="28"><Document /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.total }}</div>
            <div class="stat-label">总发票数</div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <el-icon size="28"><Clock /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.pending }}</div>
            <div class="stat-label">待审核</div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
            <el-icon size="28"><CircleCheck /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.approved }}</div>
            <div class="stat-label">已通过</div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
            <el-icon size="28"><Warning /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.review }}</div>
            <div class="stat-label">复核中</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="stats-row">
      <el-col :span="8">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
            <el-icon size="28"><Money /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">¥{{ (amountStats.totalAmount || 0).toFixed(2) }}</div>
            <div class="stat-label">报销总额</div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);">
            <el-icon size="28"><SuccessFilled /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">¥{{ (amountStats.approvedAmount || 0).toFixed(2) }}</div>
            <div class="stat-label">已通过金额</div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);">
            <el-icon size="28"><CircleCloseFilled /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">¥{{ (amountStats.rejectedAmount || 0).toFixed(2) }}</div>
            <div class="stat-label">已驳回金额</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" class="quick-actions">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>最近发票</span>
              <el-button type="primary" text @click="$router.push('/invoices')">
                查看全部
              </el-button>
            </div>
          </template>
          
          <el-table :data="recentInvoices" style="width: 100%">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="invoice_no" label="发票号码" width="150" />
            <el-table-column prop="seller_name" label="销售方" min-width="150" show-overflow-tooltip />
            <el-table-column prop="total_amount" label="金额" width="120">
              <template #default="{ row }">
                <span class="amount">¥{{ row.total_amount?.toFixed(2) || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small">
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="上传时间" width="160">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button type="primary" text size="small" @click="viewInvoice(row.id)">
                  查看
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card style="margin-top: 20px;">
          <template #header>
            <div class="card-header">
              <span>报销类型分布</span>
            </div>
          </template>
          <div class="type-distribution">
            <div v-for="item in typeDistribution" :key="item.type" class="type-item">
              <div class="type-info">
                <span class="type-name">{{ item.name }}</span>
                <span class="type-count">{{ item.count }} 张</span>
              </div>
              <el-progress 
                :percentage="item.percentage" 
                :color="item.color"
                :stroke-width="10"
              />
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>快捷操作</span>
          </template>
          
          <div class="action-buttons">
            <el-button type="primary" size="large" @click="$router.push('/upload')">
              <el-icon><Upload /></el-icon>
              上传发票
            </el-button>
            <el-button type="warning" size="large" @click="$router.push('/invoices?status=pending')">
              <el-icon><Clock /></el-icon>
              待审核 ({{ stats.pending }})
            </el-button>
            <el-button type="info" size="large" @click="$router.push('/statistics')">
              <el-icon><TrendCharts /></el-icon>
              统计分析
            </el-button>
            <el-button type="success" size="large" @click="$router.push('/auditors')">
              <el-icon><UserFilled /></el-icon>
              审核员管理
            </el-button>
            <el-button type="danger" size="large" @click="$router.push('/employees')">
              <el-icon><OfficeBuilding /></el-icon>
              员工管理
            </el-button>
          </div>
        </el-card>

        <el-card style="margin-top: 20px;">
          <template #header>
            <span>系统概览</span>
          </template>
          
          <div class="system-info">
            <div class="info-item">
              <el-icon><User /></el-icon>
              <span class="info-label">当前用户：</span>
              <span class="info-value">{{ auditorName }}</span>
            </div>
            <div class="info-item">
              <el-icon><Avatar /></el-icon>
              <span class="info-label">用户角色：</span>
              <el-tag :type="auditorRole === 'admin' ? 'danger' : 'primary'" size="small">
                {{ auditorRole === 'admin' ? '管理员' : '审核员' }}
              </el-tag>
            </div>
            <div class="info-item">
              <el-icon><Calendar /></el-icon>
              <span class="info-label">今日待办：</span>
              <span class="info-value">{{ stats.pending }} 张发票</span>
            </div>
            <div class="info-item">
              <el-icon><Monitor /></el-icon>
              <span class="info-label">系统版本：</span>
              <span class="info-value">v2.0.0</span>
            </div>
          </div>
        </el-card>

        <el-card style="margin-top: 20px;">
          <template #header>
            <div class="card-header">
              <span>审核员工作量</span>
            </div>
          </template>
          <div v-if="auditorStats.length > 0" class="auditor-workload">
            <div v-for="auditor in auditorStats" :key="auditor.id" class="auditor-item">
              <div class="auditor-info">
                <el-avatar :size="32" style="background: #409eff;">{{ auditor.name?.charAt(0) || 'U' }}</el-avatar>
                <span class="auditor-name">{{ auditor.name }}</span>
              </div>
              <div class="auditor-stats">
                <span class="stat-pass">{{ auditor.approved_count || 0 }}</span>
                <span class="stat-divider">/</span>
                <span class="stat-review">{{ auditor.review_count || 0 }}</span>
                <span class="stat-divider">/</span>
                <span class="stat-reject">{{ auditor.rejected_count || 0 }}</span>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无审核员数据" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Document, Clock, CircleCheck, Warning, Upload, TrendCharts, Money, SuccessFilled, CircleCloseFilled, UserFilled, OfficeBuilding, User, Avatar, Calendar, Monitor } from '@element-plus/icons-vue'
import axios from 'axios'

const router = useRouter()

const auditorName = localStorage.getItem('auditor_name') || '用户'
const auditorRole = localStorage.getItem('auditor_role') || 'auditor'
const auditorId = localStorage.getItem('auditor_id')

const stats = reactive({
  total: 0,
  pending: 0,
  approved: 0,
  rejected: 0,
  review: 0
})

const amountStats = reactive({
  totalAmount: 0,
  approvedAmount: 0,
  rejectedAmount: 0
})

const recentInvoices = ref<any[]>([])
const auditorStats = ref<any[]>([])

const typeDistribution = ref<any[]>([
  { type: 'accommodation', name: '住宿费', count: 0, percentage: 0, color: '#409eff' },
  { type: 'transport_air', name: '机票', count: 0, percentage: 0, color: '#67c23a' },
  { type: 'transport_train', name: '火车票', count: 0, percentage: 0, color: '#e6a23c' },
  { type: 'city_transport', name: '市内交通', count: 0, percentage: 0, color: '#f56c6c' },
  { type: 'meal', name: '伙食补助', count: 0, percentage: 0, color: '#909399' },
  { type: 'business_entertainment', name: '业务招待', count: 0, percentage: 0, color: '#c55a00' }
])

const fetchStats = async () => {
  try {
    const res = await axios.get('/api/stats')
    Object.assign(stats, res.data)
  } catch (e) {
    console.error('获取统计失败', e)
  }
}

const fetchAmountStats = async () => {
  try {
    const res = await axios.get('/api/stats/amount')
    Object.assign(amountStats, res.data)
  } catch (e) {
    console.error('获取金额统计失败', e)
  }
}

const fetchRecentInvoices = async () => {
  try {
    const res = await axios.get('/api/invoices?limit=5')
    recentInvoices.value = res.data
  } catch (e) {
    console.error('获取发票列表失败', e)
  }
}

const fetchAuditorStats = async () => {
  try {
    const res = await axios.get('/api/auditors')
    auditorStats.value = res.data.filter((a: any) => a.role === 'auditor').slice(0, 5)
  } catch (e) {
    console.error('获取审核员统计失败', e)
  }
}

const fetchTypeDistribution = async () => {
  try {
    const res = await axios.get('/api/stats/type-distribution')
    const total = res.data.reduce((sum: number, item: any) => sum + item.count, 0)
    const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#c55a00']
    typeDistribution.value = res.data.map((item: any, index: number) => ({
      ...item,
      percentage: total > 0 ? Math.round((item.count / total) * 100) : 0,
      color: colors[index] || '#409eff'
    }))
  } catch (e) {
    console.error('获取类型分布失败', e)
  }
}

const viewInvoice = (id: number) => {
  router.push(`/invoices/${id}`)
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
    review: '复核中'
  }
  return map[status] || status
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
  fetchStats()
  fetchRecentInvoices()
  if (auditorRole === 'admin') {
    fetchAuditorStats()
    fetchTypeDistribution()
  }
})
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 10px;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  width: 100%;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  margin-right: 15px;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 5px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.quick-actions {
  margin-top: 0;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.action-buttons .el-button {
  width: 100%;
  justify-content: flex-start;
}

.system-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.info-item .el-icon {
  color: #409eff;
  font-size: 16px;
}

.info-label {
  color: #909399;
}

.info-value {
  color: #303133;
  font-weight: 500;
}

.amount {
  color: #409eff;
  font-weight: 600;
}

.type-distribution {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.type-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.type-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.type-name {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.type-count {
  font-size: 13px;
  color: #909399;
}

.auditor-workload {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.auditor-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.auditor-item:last-child {
  border-bottom: none;
}

.auditor-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.auditor-name {
  font-size: 14px;
  color: #303133;
}

.auditor-stats {
  font-size: 13px;
  font-family: monospace;
}

.stat-pass {
  color: #67c23a;
  font-weight: 600;
}

.stat-review {
  color: #e6a23c;
  font-weight: 600;
}

.stat-reject {
  color: #f56c6c;
  font-weight: 600;
}

.stat-divider {
  color: #dcdfe6;
  margin: 0 2px;
}
</style>
