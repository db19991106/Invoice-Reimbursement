<template>
  <div class="invoice-detail">
    <el-page-header @back="$router.back()">
      <template #content>
        <span class="page-title">发票详情</span>
      </template>
    </el-page-header>
    
    <div class="content" v-loading="loading">
      <el-row :gutter="20">
        <!-- 左侧：发票图片 -->
        <el-col :span="12">
          <el-card>
            <template #header>
              <span>发票图片</span>
            </template>
            <div class="image-container">
              <img v-if="invoiceImage" :src="invoiceImage" style="max-width: 100%;" />
              <el-empty v-else description="暂无图片" />
            </div>
          </el-card>
        </el-col>
        
        <!-- 右侧：发票信息 -->
        <el-col :span="12">
          <!-- 审核状态卡片 -->
          <el-card class="status-card">
            <div class="status-header">
              <div class="status-info">
                <el-tag :type="getStatusType(invoice?.status)" size="large">
                  {{ getStatusText(invoice?.status) }}
                </el-tag>
                <el-tag :type="getChannelType(auditResult?.channel)" size="large" style="margin-left: 10px;">
                  {{ getChannelText(auditResult?.channel) }}
                </el-tag>
              </div>
              <div class="status-actions" v-if="invoice?.status === 'pending' || invoice?.status === 'review'">
                <el-button type="success" @click="approveInvoice">通过审核</el-button>
                <el-button type="danger" @click="showRejectDialog">驳回</el-button>
              </div>
            </div>
            <div class="risk-info" v-if="auditResult">
              <span>风险等级：{{ auditResult.risk_level }}</span>
              <span>风险评分：{{ (auditResult.risk_score * 100).toFixed(0) }}%</span>
              <span>OCR置信度：{{ (auditResult.ocr_confidence * 100).toFixed(0) }}%</span>
            </div>
          </el-card>
          
          <!-- 发票信息表单（可编辑） -->
          <el-card class="info-card">
            <template #header>
              <div class="card-header">
                <span>发票信息</span>
                <el-button v-if="!editing" type="primary" text @click="startEdit">
                  <el-icon><Edit /></el-icon>
                  编辑
                </el-button>
                <template v-else>
                  <el-button type="primary" text @click="saveEdit">保存</el-button>
                  <el-button text @click="cancelEdit">取消</el-button>
                </template>
              </div>
            </template>
            
            <el-form :model="formData" label-width="100px" :disabled="!editing">
              <el-divider content-position="left">基本信息</el-divider>
              
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="发票代码">
                    <el-input v-model="formData.invoice_code" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="发票号码">
                    <el-input v-model="formData.invoice_no" />
                  </el-form-item>
                </el-col>
              </el-row>
              
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="开票日期">
                    <el-input v-model="formData.date" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="费用类型">
                    <el-select v-model="formData.expense_type" style="width: 100%;">
                      <el-option label="住宿费" value="accommodation" />
                      <el-option label="机票" value="transport_air" />
                      <el-option label="火车票" value="transport_train" />
                      <el-option label="市内交通" value="city_transport" />
                      <el-option label="伙食补助" value="meal" />
                      <el-option label="业务招待" value="business_entertainment" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
              
              <el-divider content-position="left">金额信息</el-divider>
              
              <el-row :gutter="20">
                <el-col :span="8">
                  <el-form-item label="金额">
                    <el-input-number v-model="formData.amount" :precision="2" style="width: 100%;" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="税额">
                    <el-input-number v-model="formData.tax_amount" :precision="2" style="width: 100%;" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="价税合计">
                    <el-input-number v-model="formData.total_amount" :precision="2" style="width: 100%;" />
                  </el-form-item>
                </el-col>
              </el-row>
              
              <el-divider content-position="left">销售方信息</el-divider>
              
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="销售方名称">
                    <el-input v-model="formData.seller_name" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="纳税人识别号">
                    <el-input v-model="formData.seller_tax_id" />
                  </el-form-item>
                </el-col>
              </el-row>
              
              <el-divider content-position="left">购买方信息</el-divider>
              
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="购买方名称">
                    <el-input v-model="formData.buyer_name" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="纳税人识别号">
                    <el-input v-model="formData.buyer_tax_id" />
                  </el-form-item>
                </el-col>
              </el-row>
              
              <el-divider content-position="left">报销信息</el-divider>
              
              <el-row :gutter="20">
                <el-col :span="8">
                  <el-form-item label="目的地">
                    <el-input v-model="formData.destination_city" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="人数">
                    <el-input-number v-model="formData.person_count" :min="1" style="width: 100%;" />
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item label="天数">
                    <el-input-number v-model="formData.trip_days" :min="1" style="width: 100%;" />
                  </el-form-item>
                </el-col>
              </el-row>
            </el-form>
          </el-card>
          
          <!-- 审核结果详情 -->
          <el-card class="audit-card" v-if="auditResult">
            <template #header>
              <span>审核详情</span>
            </template>
            
            <el-collapse>
              <el-collapse-item title="风险因素" name="risk">
                <ul class="risk-list">
                  <li v-for="(reason, idx) in auditResult.risk_reasons" :key="idx">{{ reason }}</li>
                </ul>
              </el-collapse-item>
              <el-collapse-item title="校验项目" name="validation">
                <el-table :data="auditResult.validation_items" size="small">
                  <el-table-column prop="rule_name" label="校验项" />
                  <el-table-column prop="result" label="结果" width="80">
                    <template #default="{ row }">
                      <el-tag :type="row.result === 'pass' ? 'success' : row.result === 'reject' ? 'danger' : 'warning'" size="small">
                        {{ row.result === 'pass' ? '通过' : row.result === 'reject' ? '驳回' : '警告' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="message" label="说明" show-overflow-tooltip />
                </el-table>
              </el-collapse-item>
            </el-collapse>
          </el-card>
          
          <!-- 审核历史记录 -->
          <el-card class="history-card">
            <template #header>
              <span>审核历史</span>
            </template>
            
            <el-timeline v-if="auditHistory.length > 0">
              <el-timeline-item
                v-for="(record, index) in auditHistory"
                :key="index"
                :type="getTimelineType(record.action)"
                :timestamp="formatDate(record.created_at)"
                placement="top"
              >
                <div class="history-item">
                  <div class="history-header">
                    <el-tag :type="getActionType(record.action)" size="small">
                      {{ getActionText(record.action) }}
                    </el-tag>
                    <span class="history-user">{{ record.auditor_name || '系统' }}</span>
                  </div>
                  <div class="history-content" v-if="record.note || record.reason">
                    {{ record.note || record.reason }}
                  </div>
                  <div class="history-details" v-if="record.changes">
                    <div v-for="(value, key) in record.changes" :key="key" class="change-item">
                      <span class="change-label">{{ getFieldLabel(key) }}:</span>
                      <span class="change-value">{{ value.old || '空' }} → {{ value.new || '空' }}</span>
                    </div>
                  </div>
                </div>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-else description="暂无审核历史" :image-size="60" />
          </el-card>
        </el-col>
      </el-row>
    </div>
    
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
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit } from '@element-plus/icons-vue'
import axios from 'axios'

const router = useRouter()
const route = useRoute()

const auditorId = localStorage.getItem('auditor_id')
const invoiceId = route.params.id as string

const loading = ref(false)
const invoice = ref<any>(null)
const invoiceImage = ref('')
const auditResult = ref<any>(null)
const auditHistory = ref<any[]>([])
const editing = ref(false)

const formData = reactive({
  invoice_code: '',
  invoice_no: '',
  date: '',
  amount: 0,
  tax_amount: 0,
  total_amount: 0,
  seller_name: '',
  seller_tax_id: '',
  buyer_name: '',
  buyer_tax_id: '',
  expense_type: '',
  destination_city: '',
  person_count: 1,
  trip_days: 1
})

const rejectDialogVisible = ref(false)
const rejectForm = reactive({
  reason: ''
})

const fetchInvoice = async () => {
  loading.value = true
  try {
    // 获取发票详情
    const res = await axios.get(`/api/invoices/${invoiceId}`)
    invoice.value = res.data
    
    // 填充表单数据
    Object.keys(formData).forEach(key => {
      (formData as any)[key] = res.data[key] ?? (typeof (formData as any)[key] === 'number' ? 0 : '')
    })
    
    // 获取图片
    try {
      const imgRes = await axios.get(`/api/invoices/${invoiceId}/image`, {
        responseType: 'blob'
      })
      invoiceImage.value = URL.createObjectURL(new Blob([imgRes.data]))
    } catch (e) {
      invoiceImage.value = ''
    }
    
    // 获取审核结果
    try {
      const auditRes = await axios.get(`/api/invoices/${invoiceId}/audit`)
      auditResult.value = auditRes.data
    } catch (e) {
      auditResult.value = null
    }
    
    // 获取审核历史
    fetchAuditHistory()
  } catch (e) {
    ElMessage.error('获取发票详情失败')
  } finally {
    loading.value = false
  }
}

const fetchAuditHistory = async () => {
  try {
    // 获取审核历史 - 如果后端有此接口
    // const res = await axios.get(`/api/audit/invoices/${invoiceId}/history?auditor_id=${auditorId}`)
    // auditHistory.value = res.data
    
    // 模拟审核历史数据
    auditHistory.value = []
    if (invoice.value?.status !== 'pending') {
      auditHistory.value.push({
        action: 'upload',
        created_at: invoice.value?.created_at,
        auditor_name: '系统',
        note: '发票上传成功'
      })
      
      if (auditResult.value) {
        auditHistory.value.push({
          action: 'audit',
          created_at: auditResult.value.reviewed_at || invoice.value?.created_at,
          auditor_name: '系统',
          note: `自动审核完成，风险等级: ${auditResult.value.risk_level}`
        })
      }
      
      if (invoice.value?.status === 'approve') {
        auditHistory.value.push({
          action: 'approve',
          created_at: new Date().toISOString(),
          auditor_name: localStorage.getItem('auditor_name') || '审核员',
          note: '审核通过'
        })
      } else if (invoice.value?.status === 'reject') {
        auditHistory.value.push({
          action: 'reject',
          created_at: new Date().toISOString(),
          auditor_name: localStorage.getItem('auditor_name') || '审核员',
          note: '审核驳回'
        })
      }
    } else {
      auditHistory.value.push({
        action: 'upload',
        created_at: invoice.value?.created_at,
        auditor_name: '系统',
        note: '发票上传成功，等待审核'
      })
    }
  } catch (e) {
    auditHistory.value = []
  }
}

const startEdit = () => {
  editing.value = true
}

const cancelEdit = () => {
  editing.value = false
  // 恢复原始数据
  Object.keys(formData).forEach(key => {
    (formData as any)[key] = invoice.value[key] ?? (typeof (formData as any)[key] === 'number' ? 0 : '')
  })
}

const saveEdit = async () => {
  try {
    await axios.put(`/api/invoices/${invoiceId}`, formData)
    ElMessage.success('保存成功')
    editing.value = false
    fetchInvoice()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  }
}

const approveInvoice = async () => {
  try {
    await ElMessageBox.confirm('确认通过该发票？', '确认', { type: 'success' })
    
    await axios.post(`/api/invoices/${invoiceId}/approve`)
    ElMessage.success('审核通过')
    fetchInvoice()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '操作失败')
    }
  }
}

const showRejectDialog = () => {
  rejectForm.reason = ''
  rejectDialogVisible.value = true
}

const rejectInvoice = async () => {
  if (!rejectForm.reason.trim()) {
    ElMessage.warning('请输入驳回原因')
    return
  }
  
  try {
    await axios.post(`/api/invoices/${invoiceId}/reject?reason=${encodeURIComponent(rejectForm.reason)}`)
    ElMessage.success('已驳回')
    rejectDialogVisible.value = false
    router.back()
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

const getTimelineType = (action: string) => {
  const map: Record<string, string> = {
    upload: 'primary',
    audit: 'info',
    approve: 'success',
    reject: 'danger',
    edit: 'warning'
  }
  return map[action] || 'info'
}

const getActionType = (action: string) => {
  const map: Record<string, string> = {
    upload: '',
    audit: 'info',
    approve: 'success',
    reject: 'danger',
    edit: 'warning'
  }
  return map[action] || ''
}

const getActionText = (action: string) => {
  const map: Record<string, string> = {
    upload: '上传',
    audit: '审核',
    approve: '通过',
    reject: '驳回',
    edit: '编辑'
  }
  return map[action] || action
}

const getFieldLabel = (field: string) => {
  const map: Record<string, string> = {
    invoice_code: '发票代码',
    invoice_no: '发票号码',
    amount: '金额',
    tax_amount: '税额',
    total_amount: '价税合计',
    seller_name: '销售方',
    buyer_name: '购买方',
    expense_type: '费用类型',
    status: '状态'
  }
  return map[field] || field
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
  fetchInvoice()
})
</script>

<style scoped>
.invoice-detail {
  padding: 0;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
}

.content {
  margin-top: 20px;
}

.image-container {
  text-align: center;
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-card {
  margin-bottom: 20px;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-actions {
  display: flex;
  gap: 10px;
}

.risk-info {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #ebeef5;
  display: flex;
  gap: 20px;
  color: #606266;
}

.info-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.audit-card {
  margin-bottom: 20px;
}

.risk-list {
  margin: 0;
  padding-left: 20px;
}

.risk-list li {
  margin: 8px 0;
  color: #606266;
}

.history-card {
  margin-bottom: 20px;
}

.history-item {
  padding: 5px 0;
}

.history-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.history-user {
  color: #909399;
  font-size: 13px;
}

.history-content {
  color: #606266;
  font-size: 13px;
  margin-bottom: 8px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.history-details {
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 4px;
}

.change-item {
  margin: 4px 0;
  font-size: 13px;
}

.change-label {
  color: #909399;
  margin-right: 8px;
}

.change-value {
  color: #606266;
}
</style>
