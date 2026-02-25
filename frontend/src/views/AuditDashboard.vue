<template>
  <div class="audit-dashboard">
    <el-container>
      <el-header>
        <div class="header-content">
          <h2>财务审核系统 - 审核人工作台</h2>
          <div class="user-info">
            <span>{{ auditorName }} ({{ auditorRole === 'admin' ? '管理员' : '审核员' }})</span>
            <el-button type="danger" size="small" @click="handleLogout">退出</el-button>
          </div>
        </div>
      </el-header>
      
      <el-container>
        <el-aside width="200px">
          <el-menu :default-active="activeMenu" @select="handleMenuSelect">
            <el-menu-item index="pending">
              <el-icon><Clock /></el-icon>
              <span>待审核 ({{ stats.pending }})</span>
            </el-menu-item>
            <el-menu-item index="review">
              <el-icon><Warning /></el-icon>
              <span>复核中 ({{ stats.review }})</span>
            </el-menu-item>
            <el-menu-item index="approve">
              <el-icon><CircleCheck /></el-icon>
              <span>已通过 ({{ stats.approved }})</span>
            </el-menu-item>
            <el-menu-item index="all">
              <el-icon><List /></el-icon>
              <span>全部发票</span>
            </el-menu-item>
          </el-menu>
        </el-aside>
        
        <el-main>
          <el-card>
            <template #header>
              <div class="card-header">
                <span>{{ pageTitle }}</span>
              </div>
            </template>
            
            <el-table :data="invoices" style="width: 100%" v-loading="loading">
              <el-table-column prop="id" label="ID" width="60" />
              <el-table-column prop="invoice_no" label="发票号码" width="120" />
              <el-table-column prop="seller_name" label="销售方" min-width="180" show-overflow-tooltip />
              <el-table-column prop="amount" label="金额" width="100">
                <template #default="{ row }">
                  ¥{{ row.amount?.toFixed(2) || '-' }}
                </template>
              </el-table-column>
              <el-table-column prop="total_amount" label="价税合计" width="100">
                <template #default="{ row }">
                  ¥{{ row.total_amount?.toFixed(2) || '-' }}
                </template>
              </el-table-column>
              <el-table-column prop="date" label="开票日期" width="100" />
              <el-table-column prop="status" label="状态" width="80">
                <template #default="{ row }">
                  <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="200" fixed="right">
                <template #default="{ row }">
                  <el-button size="small" @click="showInvoiceDetail(row)">查看</el-button>
                  <el-button size="small" type="success" @click="approveInvoice(row)" 
                             v-if="row.status === 'review' || row.status === 'pending'">
                    通过
                  </el-button>
                  <el-button size="small" type="danger" @click="showRejectDialog(row)"
                             v-if="row.status === 'review' || row.status === 'pending'">
                    驳回
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            
            <div class="pagination">
              <el-pagination
                v-model:current-page="currentPage"
                :page-size="20"
                :total="totalInvoices"
                layout="prev, pager, next"
                @current-change="fetchInvoices"
              />
            </div>
          </el-card>
        </el-main>
      </el-container>
    </el-container>
    
    <!-- 发票详情弹窗 -->
    <el-dialog v-model="detailDialogVisible" title="发票详情" width="80%">
      <div v-if="currentInvoice" class="invoice-detail">
        <el-row :gutter="20">
          <el-col :span="12">
            <h4>发票图片</h4>
            <img v-if="invoiceImage" :src="invoiceImage" style="max-width: 100%;" />
          </el-col>
          <el-col :span="12">
            <h4>发票信息</h4>
            <el-descriptions :column="1" border>
              <el-descriptions-item label="发票代码">{{ currentInvoice.invoice_code }}</el-descriptions-item>
              <el-descriptions-item label="发票号码">{{ currentInvoice.invoice_no }}</el-descriptions-item>
              <el-descriptions-item label="开票日期">{{ currentInvoice.date }}</el-descriptions-item>
              <el-descriptions-item label="销售方">{{ currentInvoice.seller_name }}</el-descriptions-item>
              <el-descriptions-item label="销售方税号">{{ currentInvoice.seller_tax_id }}</el-descriptions-item>
              <el-descriptions-item label="购买方">{{ currentInvoice.buyer_name }}</el-descriptions-item>
              <el-descriptions-item label="购买方税号">{{ currentInvoice.buyer_tax_id }}</el-descriptions-item>
              <el-descriptions-item label="金额">{{ currentInvoice.amount }}</el-descriptions-item>
              <el-descriptions-item label="税额">{{ currentInvoice.tax_amount }}</el-descriptions-item>
              <el-descriptions-item label="价税合计">{{ currentInvoice.total_amount }}</el-descriptions-item>
              <el-descriptions-item label="费用类型">{{ getExpenseTypeText(currentInvoice.expense_type) }}</el-descriptions-item>
              <el-descriptions-item label="目的地">{{ currentInvoice.destination_city }}</el-descriptions-item>
            </el-descriptions>
            
            <h4 style="margin-top: 20px;">审核结果</h4>
            <el-descriptions :column="1" border v-if="auditResult">
              <el-descriptions-item label="决策">
                <el-tag :type="getStatusType(auditResult.decision)">{{ getStatusText(auditResult.decision) }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="通道">
                <el-tag :type="getChannelType(auditResult.channel)">{{ getChannelText(auditResult.channel) }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="风险等级">{{ auditResult.risk_level }}</el-descriptions-item>
              <el-descriptions-item label="风险因素">
                <ul>
                  <li v-for="(reason, idx) in auditResult.risk_reasons" :key="idx">{{ reason }}</li>
                </ul>
              </el-descriptions-item>
            </el-descriptions>
          </el-col>
        </el-row>
      </div>
    </el-dialog>
    
    <!-- 驳回弹窗 -->
    <el-dialog v-model="rejectDialogVisible" title="驳回发票" width="400px">
      <el-form :model="rejectForm" label-width="80px">
        <el-form-item label="驳回原因">
          <el-input v-model="rejectForm.reason" type="textarea" :rows="3" placeholder="请输入驳回原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="rejectInvoice">确认驳回</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Clock, Warning, CircleCheck, List } from '@element-plus/icons-vue'
import axios from 'axios'

const router = useRouter()

const auditorId = localStorage.getItem('auditor_id')
const auditorName = localStorage.getItem('auditor_name') || '审核员'
const auditorRole = localStorage.getItem('auditor_role') || 'auditor'

const activeMenu = ref('pending')
const loading = ref(false)
const invoices = ref<any[]>([])
const currentPage = ref(1)
const totalInvoices = ref(0)

const stats = reactive({
  total: 0,
  pending: 0,
  review: 0,
  approved: 0,
  rejected: 0
})

const detailDialogVisible = ref(false)
const currentInvoice = ref<any>(null)
const invoiceImage = ref('')
const auditResult = ref<any>(null)

const rejectDialogVisible = ref(false)
const rejectForm = reactive({
  invoiceId: 0,
  reason: ''
})

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    pending: '待审核发票',
    review: '复核中发票',
    approve: '已通过发票',
    all: '全部发票'
  }
  return titles[activeMenu.value] || '发票列表'
})

const fetchStats = async () => {
  try {
    const res = await axios.get('/api/stats')
    Object.assign(stats, res.data)
  } catch (e) {
    console.error('获取统计失败', e)
  }
}

const fetchInvoices = async () => {
  loading.value = true
  try {
    const status = activeMenu.value === 'all' ? '' : activeMenu.value
    const res = await axios.get(`/api/invoices?status=${status}&skip=${(currentPage.value - 1) * 20}`)
    invoices.value = res.data
  } catch (e) {
    ElMessage.error('获取发票列表失败')
  } finally {
    loading.value = false
  }
}

const handleMenuSelect = (index: string) => {
  activeMenu.value = index
  currentPage.value = 1
  fetchInvoices()
}

const showInvoiceDetail = async (invoice: any) => {
  currentInvoice.value = invoice
  detailDialogVisible.value = true
  
  // 加载图片
  try {
    const res = await axios.get(`/api/invoices/${invoice.id}/image`, {
      responseType: 'blob'
    })
    invoiceImage.value = URL.createObjectURL(new Blob([res.data]))
  } catch (e) {
    invoiceImage.value = ''
  }
  
  // 加载审核结果
  try {
    const res = await axios.get(`/api/invoices/${invoice.id}/audit`)
    auditResult.value = res.data
  } catch (e) {
    auditResult.value = null
  }
}

const approveInvoice = async (invoice: any) => {
  try {
    await ElMessageBox.confirm('确认通过该发票？', '确认', { type: 'success' })
    
    await axios.post(`/api/invoices/${invoice.id}/approve`)
    ElMessage.success('审核通过')
    fetchInvoices()
    fetchStats()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '操作失败')
    }
  }
}

const showRejectDialog = (invoice: any) => {
  rejectForm.invoiceId = invoice.id
  rejectForm.reason = ''
  rejectDialogVisible.value = true
}

const rejectInvoice = async () => {
  if (!rejectForm.reason.trim()) {
    ElMessage.warning('请输入驳回原因')
    return
  }
  
  try {
    await axios.post(`/api/invoices/${rejectForm.invoiceId}/reject?reason=${encodeURIComponent(rejectForm.reason)}`)
    ElMessage.success('已驳回')
    rejectDialogVisible.value = false
    fetchInvoices()
    fetchStats()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

const handleLogout = () => {
  localStorage.removeItem('auditor_id')
  localStorage.removeItem('auditor_name')
  localStorage.removeItem('auditor_role')
  router.push('/audit/login')
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
    green: '绿色通道',
    yellow: '黄色通道',
    red: '红色通道'
  }
  return map[channel] || channel
}

const getExpenseTypeText = (type: string) => {
  const map: Record<string, string> = {
    accommodation: '住宿费',
    transport_air: '机票',
    transport_train: '火车票',
    city_transport: '市内交通',
    meal: '伙食补助',
    business_entertainment: '业务招待'
  }
  return map[type] || type
}

onMounted(() => {
  if (!auditorId) {
    router.push('/audit/login')
    return
  }
  fetchStats()
  fetchInvoices()
})
</script>

<style scoped>
.audit-dashboard {
  height: 100vh;
}

.el-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 100%;
}

.header-content h2 {
  margin: 0;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 15px;
}

.el-aside {
  background: #fff;
  border-right: 1px solid #e4e7ed;
}

.el-main {
  background: #f5f7fa;
}

.card-header {
  font-size: 16px;
  font-weight: 600;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.invoice-detail h4 {
  margin-bottom: 15px;
  color: #303133;
}

.invoice-detail ul {
  margin: 0;
  padding-left: 20px;
}

.invoice-detail li {
  margin: 5px 0;
  color: #606266;
}
</style>
