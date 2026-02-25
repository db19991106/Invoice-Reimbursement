<template>
  <div class="statistics">
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="filter-bar">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 260px;"
          @change="fetchInvoices"
        />
        <el-select v-model="filterExpenseType" placeholder="费用类型" clearable style="width: 150px; margin-left: 10px;" @change="fetchInvoices">
          <el-option label="全部" value="" />
          <el-option label="住宿费" value="accommodation" />
          <el-option label="机票" value="transport_air" />
          <el-option label="火车票" value="transport_train" />
          <el-option label="市内交通" value="city_transport" />
          <el-option label="伙食补助" value="meal" />
          <el-option label="业务招待" value="business_entertainment" />
        </el-select>
        <el-button type="primary" style="margin-left: 10px;" @click="fetchInvoices">查询</el-button>
      </div>
      <div class="export-bar">
        <el-dropdown trigger="click" @command="handleExportCommand">
          <el-button type="success">
            <el-icon><Download /></el-icon>
            导出报表
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="summary">
                <el-icon><Document /></el-icon> 导出汇总报表
              </el-dropdown-item>
              <el-dropdown-item command="detail">
                <el-icon><List /></el-icon> 导出明细报表
              </el-dropdown-item>
              <el-dropdown-item command="expense">
                <el-icon><PieChart /></el-icon> 导出费用分析
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

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
          <div class="stat-icon" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <el-icon size="28"><Warning /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.review }}</div>
            <div class="stat-label">复核中</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
            <el-icon size="28"><Clock /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.pending }}</div>
            <div class="stat-label">待审核</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20">
      <!-- 状态分布 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>审核状态分布</span>
              <el-tag type="info" size="small">共 {{ stats.total }} 张</el-tag>
            </div>
          </template>
          <div class="chart-container">
            <div class="pie-chart">
              <div class="pie-item" v-for="(item, key) in statusDistribution" :key="key">
                <div class="pie-label">{{ item.label }}</div>
                <div class="pie-bar">
                  <div class="pie-fill" :style="{ width: item.percent + '%', background: item.color }"></div>
                </div>
                <div class="pie-value">{{ item.count }} ({{ item.percent.toFixed(1) }}%)</div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <!-- 费用类型分布 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>费用类型分布</span>
              <el-tag type="info" size="small">{{ Object.keys(expenseDistribution).length }} 种类型</el-tag>
            </div>
          </template>
          <div class="chart-container">
            <div class="expense-list">
              <div class="expense-item" v-for="(item, idx) in sortedExpenseDistribution" :key="idx">
                <div class="expense-label">{{ item.label }}</div>
                <div class="expense-bar">
                  <div class="expense-fill" :style="{ width: item.percent + '%' }"></div>
                </div>
                <div class="expense-value">{{ item.count }}张 / ¥{{ formatAmount(item.amount) }}</div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 金额统计 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>金额统计</span>
              <el-tag type="warning" size="small">本期间</el-tag>
            </div>
          </template>
          <el-row :gutter="40">
            <el-col :span="6">
              <div class="amount-stat">
                <div class="amount-label">已通过金额</div>
                <div class="amount-value success">¥{{ formatAmount(amountStats.approved) }}</div>
                <div class="amount-percent">占比 {{ getPercent(amountStats.approved, amountStats.total) }}%</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="amount-stat">
                <div class="amount-label">复核中金额</div>
                <div class="amount-value warning">¥{{ formatAmount(amountStats.review) }}</div>
                <div class="amount-percent">占比 {{ getPercent(amountStats.review, amountStats.total) }}%</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="amount-stat">
                <div class="amount-label">待审核金额</div>
                <div class="amount-value info">¥{{ formatAmount(amountStats.pending) }}</div>
                <div class="amount-percent">占比 {{ getPercent(amountStats.pending, amountStats.total) }}%</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="amount-stat">
                <div class="amount-label">总金额</div>
                <div class="amount-value">¥{{ formatAmount(amountStats.total) }}</div>
                <div class="amount-percent">{{ invoices.length }} 张发票</div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>

    <!-- 通道分布 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>审核通道分布</span>
          </template>
          <div class="channel-stats">
            <div class="channel-item" v-for="item in channelDistribution" :key="item.channel">
              <div class="channel-icon" :style="{ background: item.color }">
                <el-icon v-if="item.channel === 'green'"><CircleCheck /></el-icon>
                <el-icon v-else-if="item.channel === 'yellow'"><Warning /></el-icon>
                <el-icon v-else><CircleClose /></el-icon>
              </div>
              <div class="channel-info">
                <div class="channel-name">{{ item.label }}</div>
                <div class="channel-desc">{{ item.desc }}</div>
              </div>
              <div class="channel-count">{{ item.count }}张</div>
              <el-progress :percentage="item.percent" :color="item.color" :show-text="false" style="width: 100px;" />
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>风险等级分布</span>
          </template>
          <div class="risk-stats">
            <div class="risk-item" v-for="item in riskDistribution" :key="item.level">
              <div class="risk-level" :style="{ color: item.color }">{{ item.level }}</div>
              <div class="risk-info">
                <div class="risk-bar">
                  <div class="risk-fill" :style="{ width: item.percent + '%', background: item.color }"></div>
                </div>
              </div>
              <div class="risk-count">{{ item.count }}张</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 最近审核记录 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>最近审核记录</span>
              <el-button type="primary" text @click="exportRecentAudits">
                <el-icon><Download /></el-icon>
                导出
              </el-button>
            </div>
          </template>
          <el-table :data="recentAudits" style="width: 100%">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="invoice_no" label="发票号码" width="120" />
            <el-table-column prop="seller_name" label="销售方" min-width="150" show-overflow-tooltip />
            <el-table-column prop="total_amount" label="金额" width="100">
              <template #default="{ row }">
                ¥{{ row.total_amount?.toFixed(2) || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="expense_type" label="费用类型" width="100">
              <template #default="{ row }">
                {{ getExpenseTypeText(row.expense_type) }}
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small">
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="risk_level" label="风险等级" width="80" />
            <el-table-column prop="channel" label="通道" width="80">
              <template #default="{ row }">
                <el-tag :type="getChannelType(row.channel)" size="small">
                  {{ getChannelText(row.channel) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="上传时间" width="160">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, CircleCheck, Warning, Clock, CircleClose, Download, ArrowDown, List, PieChart } from '@element-plus/icons-vue'
import axios from 'axios'

const auditorId = localStorage.getItem('auditor_id')

const dateRange = ref<[Date, Date] | null>(null)
const filterExpenseType = ref('')

const stats = reactive({
  total: 0,
  pending: 0,
  approved: 0,
  rejected: 0,
  review: 0
})

const invoices = ref<any[]>([])
const recentAudits = ref<any[]>([])

const amountStats = reactive({
  total: 0,
  approved: 0,
  review: 0,
  pending: 0
})

const expenseDistribution = reactive<Record<string, { count: number; amount: number }>>({})

const statusDistribution = computed(() => {
  const total = stats.total || 1
  return {
    approved: {
      label: '已通过',
      count: stats.approved,
      percent: (stats.approved / total) * 100,
      color: '#67C23A'
    },
    review: {
      label: '复核中',
      count: stats.review,
      percent: (stats.review / total) * 100,
      color: '#E6A23C'
    },
    pending: {
      label: '待审核',
      count: stats.pending,
      percent: (stats.pending / total) * 100,
      color: '#909399'
    }
  }
})

const sortedExpenseDistribution = computed(() => {
  const total = Object.values(expenseDistribution).reduce((sum, item) => sum + item.count, 0) || 1
  return Object.entries(expenseDistribution)
    .map(([type, data]) => ({
      type,
      label: getExpenseTypeText(type),
      count: data.count,
      amount: data.amount,
      percent: (data.count / total) * 100
    }))
    .sort((a, b) => b.amount - a.amount)
})

const channelDistribution = computed(() => {
  const total = invoices.value.length || 1
  const channels = {
    green: { count: 0, amount: 0 },
    yellow: { count: 0, amount: 0 },
    red: { count: 0, amount: 0 }
  }
  
  invoices.value.forEach(inv => {
    const channel = inv.channel || 'green'
    if (channels[channel as keyof typeof channels]) {
      channels[channel as keyof typeof channels].count++
      channels[channel as keyof typeof channels].amount += inv.total_amount || 0
    }
  })
  
  return [
    { channel: 'green', label: '绿色通道', desc: '自动通过', count: channels.green.count, percent: (channels.green.count / total) * 100, color: '#67C23A' },
    { channel: 'yellow', label: '黄色通道', desc: '需要复核', count: channels.yellow.count, percent: (channels.yellow.count / total) * 100, color: '#E6A23C' },
    { channel: 'red', label: '红色通道', desc: '建议驳回', count: channels.red.count, percent: (channels.red.count / total) * 100, color: '#F56C6C' }
  ]
})

const riskDistribution = computed(() => {
  const total = invoices.value.length || 1
  const risks: Record<string, number> = {}
  
  invoices.value.forEach(inv => {
    const level = inv.risk_level || 'low'
    risks[level] = (risks[level] || 0) + 1
  })
  
  return [
    { level: '低风险', count: risks['low'] || risks['低风险'] || 0, percent: ((risks['low'] || risks['低风险'] || 0) / total) * 100, color: '#67C23A' },
    { level: '中风险', count: risks['medium'] || risks['中风险'] || 0, percent: ((risks['medium'] || risks['中风险'] || 0) / total) * 100, color: '#E6A23C' },
    { level: '高风险', count: risks['high'] || risks['高风险'] || 0, percent: ((risks['high'] || risks['高风险'] || 0) / total) * 100, color: '#F56C6C' }
  ]
})

const getPercent = (value: number, total: number) => {
  if (!total) return 0
  return ((value / total) * 100).toFixed(1)
}

const getExpensePercent = (type: string) => {
  const total = Object.values(expenseDistribution).reduce((sum, item) => sum + item.count, 0) || 1
  return ((expenseDistribution[type]?.count || 0) / total) * 100
}

const fetchStats = async () => {
  try {
    const res = await axios.get('/api/stats')
    Object.assign(stats, res.data)
  } catch (e) {
    console.error('获取统计失败', e)
  }
}

const fetchInvoices = async () => {
  try {
    const res = await axios.get('/api/invoices?limit=500')
    let data = res.data
    
    // 日期过滤
    if (dateRange.value && dateRange.value.length === 2) {
      const startDate = dateRange.value[0].setHours(0, 0, 0, 0)
      const endDate = dateRange.value[1].setHours(23, 59, 59, 999)
      data = data.filter((inv: any) => {
        const invDate = new Date(inv.created_at).getTime()
        return invDate >= startDate && invDate <= endDate
      })
    }
    
    // 费用类型过滤
    if (filterExpenseType.value) {
      data = data.filter((inv: any) => inv.expense_type === filterExpenseType.value)
    }
    
    invoices.value = data
    
    // 计算金额统计
    amountStats.total = data.reduce((sum: number, inv: any) => sum + (inv.total_amount || 0), 0)
    amountStats.approved = data.filter((inv: any) => inv.status === 'approve').reduce((sum: number, inv: any) => sum + (inv.total_amount || 0), 0)
    amountStats.review = data.filter((inv: any) => inv.status === 'review').reduce((sum: number, inv: any) => sum + (inv.total_amount || 0), 0)
    amountStats.pending = data.filter((inv: any) => inv.status === 'pending').reduce((sum: number, inv: any) => sum + (inv.total_amount || 0), 0)
    
    // 计算费用类型分布
    const expenseCount: Record<string, { count: number; amount: number }> = {}
    data.forEach((inv: any) => {
      const type = inv.expense_type || 'other'
      if (!expenseCount[type]) {
        expenseCount[type] = { count: 0, amount: 0 }
      }
      expenseCount[type].count++
      expenseCount[type].amount += inv.total_amount || 0
    })
    Object.assign(expenseDistribution, expenseCount)
    
    // 最近审核记录
    recentAudits.value = data.slice(0, 10)
  } catch (e) {
    console.error('获取发票列表失败', e)
  }
}

const handleExportCommand = (command: string) => {
  switch (command) {
    case 'summary':
      exportSummaryReport()
      break
    case 'detail':
      exportDetailReport()
      break
    case 'expense':
      exportExpenseReport()
      break
  }
}

const exportSummaryReport = () => {
  const headers = ['统计项', '数量', '金额']
  const rows = [
    ['总发票数', stats.total, formatAmount(amountStats.total)],
    ['已通过', stats.approved, formatAmount(amountStats.approved)],
    ['复核中', stats.review, formatAmount(amountStats.review)],
    ['待审核', stats.pending, formatAmount(amountStats.pending)],
    ['已驳回', stats.rejected, formatAmount(amountStats.rejected)]
  ]
  
  downloadFile(headers, rows, '汇总报表.csv')
}

const exportDetailReport = () => {
  const headers = ['ID', '发票号码', '开票日期', '销售方', '金额', '税额', '价税合计', '费用类型', '状态', '通道', '风险等级', '上传时间']
  const rows = invoices.value.map(inv => [
    inv.id,
    inv.invoice_no || '',
    inv.date || '',
    inv.seller_name || '',
    inv.amount?.toFixed(2) || '0.00',
    inv.tax_amount?.toFixed(2) || '0.00',
    inv.total_amount?.toFixed(2) || '0.00',
    getExpenseTypeText(inv.expense_type),
    getStatusText(inv.status),
    getChannelText(inv.channel),
    inv.risk_level || '',
    formatDate(inv.created_at)
  ])
  
  downloadFile(headers, rows, '明细报表.csv')
}

const exportExpenseReport = () => {
  const headers = ['费用类型', '发票数量', '金额合计', '占比']
  const total = Object.values(expenseDistribution).reduce((sum, item) => sum + item.count, 0) || 1
  const rows = sortedExpenseDistribution.value.map(item => [
    item.label,
    item.count,
    formatAmount(item.amount),
    item.percent.toFixed(1) + '%'
  ])
  
  downloadFile(headers, rows, '费用分析报表.csv')
}

const exportRecentAudits = () => {
  const headers = ['ID', '发票号码', '销售方', '金额', '费用类型', '状态', '风险等级', '上传时间']
  const rows = recentAudits.value.map(inv => [
    inv.id,
    inv.invoice_no || '',
    inv.seller_name || '',
    inv.total_amount?.toFixed(2) || '0.00',
    getExpenseTypeText(inv.expense_type),
    getStatusText(inv.status),
    inv.risk_level || '',
    formatDate(inv.created_at)
  ])
  
  downloadFile(headers, rows, '最近审核记录.csv')
}

const downloadFile = (headers: string[], rows: any[][], filename: string) => {
  const content = [headers.join(','), ...rows.map(row => row.join(','))].join('\n')
  const blob = new Blob(['\uFEFF' + content], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  link.click()
  ElMessage.success('导出成功')
}

const formatAmount = (amount: number) => {
  if (amount >= 10000) {
    return (amount / 10000).toFixed(2) + '万'
  }
  return amount.toFixed(2)
}

const getExpenseTypeText = (type: string) => {
  const map: Record<string, string> = {
    accommodation: '住宿费',
    transport_air: '机票',
    transport_train: '火车票',
    city_transport: '市内交通',
    meal: '伙食补助',
    business_entertainment: '业务招待',
    other: '其他'
  }
  return map[type] || type || '其他'
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

const getChannelType = (channel: string) => {
  const map: Record<string, string> = {
    green: 'success',
    yellow: 'warning',
    red: 'danger'
  }
  return map[channel] || 'info'
}

const getChannelText = (channel: string) => {
  const map: Record<string, string> = {
    green: '绿色',
    yellow: '黄色',
    red: '红色'
  }
  return map[channel] || channel || '绿色'
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
  fetchInvoices()
})
</script>

<style scoped>
.statistics {
  padding: 0;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 15px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.filter-bar {
  display: flex;
  align-items: center;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  padding: 10px;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  padding: 20px;
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

.chart-container {
  padding: 10px;
}

.pie-item, .expense-item {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
}

.pie-label, .expense-label {
  width: 80px;
  font-size: 14px;
  color: #606266;
}

.pie-bar, .expense-bar, .risk-bar {
  flex: 1;
  height: 20px;
  background: #f5f7fa;
  border-radius: 10px;
  overflow: hidden;
  margin: 0 15px;
}

.pie-fill, .expense-fill, .risk-fill {
  height: 100%;
  border-radius: 10px;
  transition: width 0.3s;
}

.expense-fill {
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
}

.pie-value, .expense-value, .risk-count {
  width: 120px;
  text-align: right;
  font-size: 14px;
  color: #606266;
}

.amount-stat {
  text-align: center;
  padding: 25px;
  background: #f5f7fa;
  border-radius: 8px;
}

.amount-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 10px;
}

.amount-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.amount-value.success {
  color: #67C23A;
}

.amount-value.warning {
  color: #E6A23C;
}

.amount-value.info {
  color: #909399;
}

.amount-percent {
  font-size: 12px;
  color: #C0C4CC;
  margin-top: 8px;
}

.channel-stats {
  padding: 10px;
}

.channel-item {
  display: flex;
  align-items: center;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 12px;
}

.channel-icon {
  width: 45px;
  height: 45px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  margin-right: 15px;
}

.channel-info {
  flex: 1;
}

.channel-name {
  font-size: 15px;
  font-weight: 500;
  color: #303133;
}

.channel-desc {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.channel-count {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
  margin-right: 15px;
}

.risk-stats {
  padding: 10px;
}

.risk-item {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
}

.risk-level {
  width: 60px;
  font-size: 14px;
  font-weight: 500;
}
</style>