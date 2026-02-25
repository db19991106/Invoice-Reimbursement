<template>
  <div class="invoice-list">
    <el-card>
      <!-- 筛选条件 -->
      <div class="filter-bar">
        <el-select v-model="filters.status" placeholder="发票状态" clearable style="width: 120px;" @change="fetchInvoices">
          <el-option label="全部" value="" />
          <el-option label="待审核" value="pending" />
          <el-option label="复核中" value="review" />
          <el-option label="已通过" value="approve" />
          <el-option label="已驳回" value="reject" />
        </el-select>
        
        <el-select v-model="filters.channel" placeholder="审核通道" clearable style="width: 120px; margin-left: 10px;" @change="fetchInvoices">
          <el-option label="全部" value="" />
          <el-option label="绿色通道" value="green" />
          <el-option label="黄色通道" value="yellow" />
          <el-option label="红色通道" value="red" />
        </el-select>
        
        <el-date-picker
          v-model="filters.dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 240px; margin-left: 10px;"
          @change="fetchInvoices"
        />
        
        <el-input v-model="filters.keyword" placeholder="搜索发票号码/销售方" clearable style="width: 200px; margin-left: 10px;" @keyup.enter="fetchInvoices" />
        
        <el-button type="primary" style="margin-left: 10px;" @click="fetchInvoices">
          <el-icon><Search /></el-icon>
          搜索
        </el-button>
        
        <div style="margin-left: auto; display: flex; gap: 10px;">
          <el-dropdown trigger="click" @command="handleBatchCommand" :disabled="selectedInvoices.length === 0">
            <el-button type="warning">
              批量操作 ({{ selectedInvoices.length }})
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="approve" :disabled="!canBatchApprove">
                  <el-icon><CircleCheck /></el-icon> 批量通过
                </el-dropdown-item>
                <el-dropdown-item command="reject" :disabled="!canBatchReject">
                  <el-icon><CircleClose /></el-icon> 批量驳回
                </el-dropdown-item>
                <el-dropdown-item command="delete" divided>
                  <el-icon><Delete /></el-icon> 批量删除
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          
          <el-dropdown trigger="click" @command="handleExportCommand">
            <el-button type="info">
              <el-icon><Download /></el-icon>
              导出
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="excel">
                  <el-icon><Document /></el-icon> 导出Excel
                </el-dropdown-item>
                <el-dropdown-item command="csv">
                  <el-icon><DocumentCopy /></el-icon> 导出CSV
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          
          <el-button type="success" @click="$router.push('/upload')">
            <el-icon><Plus /></el-icon>
            上传发票
          </el-button>
        </div>
      </div>
      
      <!-- 发票列表 -->
      <el-table 
        :data="invoices" 
        style="width: 100%" 
        v-loading="loading"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="invoice_code" label="发票代码" width="120" />
        <el-table-column prop="invoice_no" label="发票号码" width="120" />
        <el-table-column prop="date" label="开票日期" width="100" />
        <el-table-column prop="seller_name" label="销售方" min-width="180" show-overflow-tooltip />
        <el-table-column prop="buyer_name" label="购买方" min-width="180" show-overflow-tooltip />
        <el-table-column prop="amount" label="金额" width="100">
          <template #default="{ row }">
            ¥{{ row.amount?.toFixed(2) || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="total_amount" label="价税合计" width="100">
          <template #default="{ row }">
            <span style="color: #E6A23C; font-weight: bold;">¥{{ row.total_amount?.toFixed(2) || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="expense_type" label="费用类型" width="100">
          <template #default="{ row }">
            {{ getExpenseTypeText(row.expense_type) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="上传时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" text size="small" @click="viewInvoice(row.id)">详情</el-button>
            <el-button type="success" text size="small" @click="approveInvoice(row)" 
                       v-if="row.status === 'pending' || row.status === 'review'">通过</el-button>
            <el-button type="danger" text size="small" @click="showRejectDialog(row)"
                       v-if="row.status === 'pending' || row.status === 'review'">驳回</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next, jumper"
          @current-change="fetchInvoices"
        />
      </div>
    </el-card>
    
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
    
    <!-- 批量驳回弹窗 -->
    <el-dialog v-model="batchRejectDialogVisible" title="批量驳回发票" width="400px">
      <el-form label-width="80px">
        <el-form-item label="驳回原因">
          <el-input v-model="batchRejectReason" type="textarea" :rows="3" placeholder="请输入驳回原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchRejectDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="batchReject">确认驳回</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, ArrowDown, CircleCheck, CircleClose, Delete, Download, Document, DocumentCopy } from '@element-plus/icons-vue'
import axios from 'axios'

const router = useRouter()
const route = useRoute()

const auditorId = localStorage.getItem('auditor_id')

const loading = ref(false)
const invoices = ref<any[]>([])
const selectedInvoices = ref<any[]>([])
const currentPage = ref(1)
const pageSize = ref(15)
const total = ref(0)

const filters = reactive({
  status: '',
  channel: '',
  keyword: '',
  dateRange: null as [Date, Date] | null
})

const rejectDialogVisible = ref(false)
const rejectForm = reactive({
  invoiceId: 0,
  reason: ''
})

// 批量操作相关
const canBatchApprove = computed(() => {
  return selectedInvoices.value.some(inv => inv.status === 'pending' || inv.status === 'review')
})

const canBatchReject = computed(() => {
  return selectedInvoices.value.some(inv => inv.status === 'pending' || inv.status === 'review')
})

const handleSelectionChange = (selection: any[]) => {
  selectedInvoices.value = selection
}

const handleBatchCommand = (command: string) => {
  switch (command) {
    case 'approve':
      batchApprove()
      break
    case 'reject':
      showBatchRejectDialog()
      break
    case 'delete':
      batchDelete()
      break
  }
}

const batchApprove = async () => {
  const toApprove = selectedInvoices.value.filter(inv => inv.status === 'pending' || inv.status === 'review')
  if (toApprove.length === 0) {
    ElMessage.warning('没有可审核的发票')
    return
  }
  
  try {
    await ElMessageBox.confirm(`确认批量通过 ${toApprove.length} 张发票？`, '确认', { type: 'success' })
    
    let successCount = 0
    for (const inv of toApprove) {
      try {
        await axios.post(`/api/invoices/${inv.id}/approve`)
        successCount++
      } catch (e) {
        console.error(`发票 ${inv.id} 通过失败`, e)
      }
    }
    
    ElMessage.success(`成功通过 ${successCount} 张发票`)
    fetchInvoices()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

const batchRejectDialogVisible = ref(false)
const batchRejectReason = ref('')

const showBatchRejectDialog = () => {
  const toReject = selectedInvoices.value.filter(inv => inv.status === 'pending' || inv.status === 'review')
  if (toReject.length === 0) {
    ElMessage.warning('没有可驳回的发票')
    return
  }
  batchRejectReason.value = ''
  batchRejectDialogVisible.value = true
}

const batchReject = async () => {
  if (!batchRejectReason.value.trim()) {
    ElMessage.warning('请输入驳回原因')
    return
  }
  
  const toReject = selectedInvoices.value.filter(inv => inv.status === 'pending' || inv.status === 'review')
  let successCount = 0
  
  for (const inv of toReject) {
    try {
      await axios.post(`/api/invoices/${inv.id}/reject?reason=${encodeURIComponent(batchRejectReason.value)}`)
      successCount++
    } catch (e) {
      console.error(`发票 ${inv.id} 驳回失败`, e)
    }
  }
  
  ElMessage.success(`成功驳回 ${successCount} 张发票`)
  batchRejectDialogVisible.value = false
  fetchInvoices()
}

const batchDelete = async () => {
  try {
    await ElMessageBox.confirm(`确认删除选中的 ${selectedInvoices.value.length} 张发票？此操作不可恢复！`, '警告', { type: 'warning' })
    
    let successCount = 0
    for (const inv of selectedInvoices.value) {
      try {
        await axios.delete(`/api/invoices/${inv.id}`)
        successCount++
      } catch (e) {
        console.error(`发票 ${inv.id} 删除失败`, e)
      }
    }
    
    ElMessage.success(`成功删除 ${successCount} 张发票`)
    fetchInvoices()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

// 导出功能
const handleExportCommand = (command: string) => {
  switch (command) {
    case 'excel':
      exportToExcel()
      break
    case 'csv':
      exportToCSV()
      break
  }
}

const exportToExcel = () => {
  const data = selectedInvoices.value.length > 0 ? selectedInvoices.value : invoices.value
  const headers = ['ID', '发票代码', '发票号码', '开票日期', '销售方', '购买方', '金额', '税额', '价税合计', '费用类型', '状态', '上传时间']
  const rows = data.map(inv => [
    inv.id,
    inv.invoice_code || '',
    inv.invoice_no || '',
    inv.date || '',
    inv.seller_name || '',
    inv.buyer_name || '',
    inv.amount?.toFixed(2) || '0.00',
    inv.tax_amount?.toFixed(2) || '0.00',
    inv.total_amount?.toFixed(2) || '0.00',
    getExpenseTypeText(inv.expense_type),
    getStatusText(inv.status),
    formatDate(inv.created_at)
  ])
  
  downloadFile(headers, rows, '发票列表.xlsx', 'excel')
}

const exportToCSV = () => {
  const data = selectedInvoices.value.length > 0 ? selectedInvoices.value : invoices.value
  const headers = ['ID', '发票代码', '发票号码', '开票日期', '销售方', '购买方', '金额', '税额', '价税合计', '费用类型', '状态', '上传时间']
  const rows = data.map(inv => [
    inv.id,
    inv.invoice_code || '',
    inv.invoice_no || '',
    inv.date || '',
    inv.seller_name || '',
    inv.buyer_name || '',
    inv.amount?.toFixed(2) || '0.00',
    inv.tax_amount?.toFixed(2) || '0.00',
    inv.total_amount?.toFixed(2) || '0.00',
    getExpenseTypeText(inv.expense_type),
    getStatusText(inv.status),
    formatDate(inv.created_at)
  ])
  
  downloadFile(headers, rows, '发票列表.csv', 'csv')
}

const downloadFile = (headers: string[], rows: any[][], filename: string, type: 'excel' | 'csv') => {
  let content = ''
  
  if (type === 'csv') {
    content = [headers.join(','), ...rows.map(row => row.join(','))].join('\n')
    const blob = new Blob(['\uFEFF' + content], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    link.click()
  } else {
    // 简单的Excel格式（实际应用中建议使用xlsx库）
    content = [headers.join('\t'), ...rows.map(row => row.join('\t'))].join('\n')
    const blob = new Blob([content], { type: 'application/vnd.ms-excel;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    link.click()
  }
  
  ElMessage.success('导出成功')
}

const fetchInvoices = async () => {
  loading.value = true
  try {
    let url = `/api/invoices?skip=${(currentPage.value - 1) * pageSize.value}&limit=${pageSize.value}`
    
    if (filters.status) {
      url += `&status=${filters.status}`
    }
    
    const res = await axios.get(url)
    invoices.value = res.data
    
    // 前端过滤
    if (filters.keyword) {
      invoices.value = invoices.value.filter((inv: any) => 
        inv.invoice_no?.includes(filters.keyword) || 
        inv.seller_name?.includes(filters.keyword)
      )
    }
    
    if (filters.channel) {
      invoices.value = invoices.value.filter((inv: any) => inv.channel === filters.channel)
    }
    
    if (filters.dateRange && filters.dateRange.length === 2) {
      const startDate = filters.dateRange[0].setHours(0, 0, 0, 0)
      const endDate = filters.dateRange[1].setHours(23, 59, 59, 999)
      invoices.value = invoices.value.filter((inv: any) => {
        const invDate = new Date(inv.created_at).getTime()
        return invDate >= startDate && invDate <= endDate
      })
    }
    
    total.value = invoices.value.length
  } catch (e) {
    ElMessage.error('获取发票列表失败')
  } finally {
    loading.value = false
  }
}

const viewInvoice = (id: number) => {
  router.push(`/invoices/${id}`)
}

const approveInvoice = async (invoice: any) => {
  try {
    await ElMessageBox.confirm('确认通过该发票？', '确认', { type: 'success' })
    
    await axios.post(`/api/invoices/${invoice.id}/approve`)
    ElMessage.success('审核通过')
    fetchInvoices()
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
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
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

const getExpenseTypeText = (type: string) => {
  const map: Record<string, string> = {
    accommodation: '住宿费',
    transport_air: '机票',
    transport_train: '火车票',
    city_transport: '市内交通',
    meal: '伙食补助',
    business_entertainment: '业务招待'
  }
  return map[type] || type || '-'
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

// 监听路由参数变化
watch(() => route.query.status, (newStatus) => {
  if (newStatus) {
    filters.status = newStatus as string
  }
  fetchInvoices()
}, { immediate: true })

onMounted(() => {
  if (route.query.status) {
    filters.status = route.query.status as string
  }
  fetchInvoices()
})
</script>

<style scoped>
.invoice-list {
  padding: 0;
}

.filter-bar {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #ebeef5;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
