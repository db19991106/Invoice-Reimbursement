<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
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
    
    <!-- 快捷操作 -->
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
            <el-table-column prop="invoice_no" label="发票号码" width="120" />
            <el-table-column prop="seller_name" label="销售方" min-width="150" show-overflow-tooltip />
            <el-table-column prop="total_amount" label="金额" width="100">
              <template #default="{ row }">
                ¥{{ row.total_amount?.toFixed(2) || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
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
          </div>
          
          <el-divider />
          
          <div class="system-info">
            <h4>系统信息</h4>
            <p><strong>当前用户：</strong>{{ auditorName }}</p>
            <p><strong>用户角色：</strong>{{ auditorRole === 'admin' ? '管理员' : '审核员' }}</p>
            <p><strong>系统版本：</strong>v2.0.0</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Document, Clock, CircleCheck, Warning, Upload, TrendCharts } from '@element-plus/icons-vue'
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

const recentInvoices = ref<any[]>([])

const fetchStats = async () => {
  try {
    const res = await axios.get('/api/stats')
    Object.assign(stats, res.data)
  } catch (e) {
    console.error('获取统计失败', e)
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
  font-size: 28px;
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
  gap: 15px;
}

.action-buttons .el-button {
  width: 100%;
  justify-content: flex-start;
}

.system-info h4 {
  margin: 0 0 10px 0;
  color: #303133;
}

.system-info p {
  margin: 8px 0;
  color: #606266;
  font-size: 14px;
}
</style>
