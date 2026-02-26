<template>
  <div class="detail-page" v-loading="loading">
    <el-button @click="$router.back()" style="margin-bottom: 20px">
      <el-icon><ArrowLeft /></el-icon>
      返回
    </el-button>
    
    <el-row :gutter="20" v-if="invoice">
      <el-col :span="14">
        <el-card>
          <template #header>
            <span>发票预览</span>
          </template>
          <div class="image-container">
            <el-image 
              :src="imageUrl" 
              :zoom-rate="1.2"
              :preview-src-list="[imageUrl]"
              fit="contain"
              style="width: 100%; max-height: 600px"
            >
              <template #error>
                <div class="image-error">
                  <el-icon :size="50"><PictureFilled /></el-icon>
                  <p>无法加载图片</p>
                </div>
              </template>
            </el-image>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="10">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>发票信息</span>
              <el-tag :type="getStatusType(invoice.status)">
                {{ getStatusText(invoice.status) }}
              </el-tag>
            </div>
          </template>
          
          <el-descriptions :column="1" border>
            <el-descriptions-item label="发票ID">{{ invoice.id }}</el-descriptions-item>
            <el-descriptions-item label="发票代码">{{ invoice.invoice_code || '-' }}</el-descriptions-item>
            <el-descriptions-item label="发票号码">{{ invoice.invoice_no || '-' }}</el-descriptions-item>
            <el-descriptions-item label="开票日期">{{ invoice.date || '-' }}</el-descriptions-item>
            <el-descriptions-item label="金额（不含税）">
              ¥{{ invoice.amount?.toFixed(2) || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="税额">
              ¥{{ invoice.tax_amount?.toFixed(2) || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="价税合计">
              ¥{{ invoice.total_amount?.toFixed(2) || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="销售方">{{ invoice.seller_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="销售方税号">{{ invoice.seller_tax_id || '-' }}</el-descriptions-item>
            <el-descriptions-item label="购买方">{{ invoice.buyer_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="购买方税号">{{ invoice.buyer_tax_id || '-' }}</el-descriptions-item>
            <el-descriptions-item label="费用类型">{{ getExpenseType(invoice.expense_type) }}</el-descriptions-item>
            <el-descriptions-item label="出差城市">{{ invoice.destination_city || '-' }}</el-descriptions-item>
            <el-descriptions-item label="人数">{{ invoice.person_count }}</el-descriptions-item>
            <el-descriptions-item label="出差天数">{{ invoice.trip_days }}</el-descriptions-item>
            <el-descriptions-item label="上传时间">{{ formatDate(invoice.created_at) }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
        
        <!-- 审核结果卡片 -->
        <el-card style="margin-top: 20px" v-if="invoice.audit_record">
          <template #header>
            <div class="card-header">
              <span>审核结果</span>
              <div>
                <el-tag :type="getDecisionType(invoice.audit_record.decision)" style="margin-right: 8px">
                  {{ getDecisionText(invoice.audit_record.decision) }}
                </el-tag>
                <el-tag :type="getChannelType(invoice.audit_record.channel)">
                  {{ getChannelText(invoice.audit_record.channel) }}
                </el-tag>
              </div>
            </div>
          </template>
          
          <!-- 标准对比 -->
          <div v-if="invoice.audit_record.validation_items?.length" class="validation-section">
            <h4 class="section-title">报销标准对比</h4>
            <el-table :data="invoice.audit_record.validation_items" style="width: 100%" size="small">
              <el-table-column label="检查项目" width="120">
                <template #default="{ row }">
                  <span>{{ getRuleName(row.rule_name) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="实际值" width="120">
                <template #default="{ row }">
                  <span>{{ getActualValue(row) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="标准值" width="120">
                <template #default="{ row }">
                  <span>{{ getStandardValue(row) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="结果" width="80">
                <template #default="{ row }">
                  <el-tag :type="getResultType(row.result)" size="small">
                    {{ getResultText(row.result) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="说明">
                <template #default="{ row }">
                  <span>{{ row.message }}</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
          
          <!-- 风险分析 -->
          <div class="risk-section" style="margin-top: 16px">
            <h4 class="section-title">风险分析</h4>
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="OCR置信度">
                <el-progress 
                  :percentage="(invoice.audit_record.ocr_confidence || 0) * 100" 
                  :stroke-width="10"
                  :color="getConfidenceColor(invoice.audit_record.ocr_confidence)"
                />
              </el-descriptions-item>
              <el-descriptions-item label="风险等级">
                <el-tag :type="getRiskLevelType(invoice.audit_record.risk_level)">
                  {{ invoice.audit_record.risk_level || '-' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="风险评分">
                <el-progress 
                  :percentage="(invoice.audit_record.risk_score || 0) * 100" 
                  :stroke-width="10"
                  :color="getRiskScoreColor(invoice.audit_record.risk_score)"
                />
              </el-descriptions-item>
              <el-descriptions-item label="印章检测">
                <el-tag :type="invoice.audit_record.stamp_detected ? 'success' : 'warning'" size="small">
                  {{ invoice.audit_record.stamp_detected ? '已检测到印章' : '未检测到印章' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="重复检测">
                <el-tag :type="invoice.audit_record.duplicate_checked ? 'success' : 'info'" size="small">
                  {{ invoice.audit_record.duplicate_checked ? '已通过' : '未检测' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="公司匹配">
                <el-tag :type="invoice.audit_record.company_matched === 'true' ? 'success' : 'warning'" size="small">
                  {{ invoice.audit_record.company_matched === 'true' ? '匹配' : '不匹配' }}
                </el-tag>
              </el-descriptions-item>
            </el-descriptions>
            
            <!-- 风险因素 -->
            <div v-if="invoice.audit_record.risk_reasons?.length" style="margin-top: 12px">
              <h5 style="margin-bottom: 8px; color: #606266">风险因素</h5>
              <el-tag 
                v-for="(reason, index) in invoice.audit_record.risk_reasons" 
                :key="index"
                type="warning"
                style="margin-right: 8px; margin-bottom: 4px"
              >
                {{ reason }}
              </el-tag>
            </div>
          </div>
          
          <div style="margin-top: 12px; color: #909399; font-size: 12px">
            审核时间: {{ formatDate(invoice.audit_record.reviewed_at) }}
          </div>
        </el-card>
        
        <el-card style="margin-top: 20px" v-if="modifyRecords.length > 0">
          <template #header>
            <span>修改记录</span>
          </template>
          
          <el-timeline>
            <el-timeline-item
              v-for="record in modifyRecords"
              :key="record.id"
              :timestamp="formatDate(record.created_at)"
              placement="top"
            >
              <p><strong>{{ record.user_name }}</strong> 修改了发票信息</p>
              <p v-if="record.modify_reason">修改原因: {{ record.modify_reason }}</p>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft, PictureFilled } from '@element-plus/icons-vue'
import axios from 'axios'

const route = useRoute()
const userId = localStorage.getItem('user_id')

const loading = ref(false)
const invoice = ref<any>(null)
const modifyRecords = ref<any[]>([])

const invoiceId = computed(() => route.params.id)

const imageUrl = computed(() => {
  if (!invoice.value) return ''
  return `/api/user/invoices/${invoiceId.value}/image?user_id=${userId}`
})

const fetchInvoice = async () => {
  loading.value = true
  try {
    const res = await axios.get(`/api/user/invoices/${invoiceId.value}`, {
      params: { user_id: userId }
    })
    invoice.value = res.data
  } catch (e) {
    console.error('获取发票详情失败', e)
  } finally {
    loading.value = false
  }
}

const fetchModifyRecords = async () => {
  try {
    const res = await axios.get(`/api/user/invoices/${invoiceId.value}/history`, {
      params: { user_id: userId }
    })
    modifyRecords.value = res.data
  } catch (e) {
    console.error('获取修改记录失败', e)
  }
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

const getExpenseType = (type: string) => {
  const types: Record<string, string> = {
    accommodation: '住宿费',
    transport_air: '航空票',
    transport_train: '火车票',
    city_transport: '城市交通',
    meal: '餐饮费',
    business_entertainment: '业务招待'
  }
  return types[type] || type || '-'
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

// 审核结果相关方法
const getDecisionType = (decision: string) => {
  const types: Record<string, string> = {
    approve: 'success',
    review: 'warning',
    reject: 'danger'
  }
  return types[decision] || 'info'
}

const getDecisionText = (decision: string) => {
  const texts: Record<string, string> = {
    approve: '通过',
    review: '需复核',
    reject: '驳回'
  }
  return texts[decision] || decision
}

const getChannelType = (channel: string) => {
  const types: Record<string, string> = {
    green: 'success',
    yellow: 'warning',
    red: 'danger'
  }
  return types[channel] || 'info'
}

const getChannelText = (channel: string) => {
  const texts: Record<string, string> = {
    green: '绿色通道',
    yellow: '黄色通道',
    red: '红色通道'
  }
  return texts[channel] || channel
}

const getRuleName = (ruleName: string) => {
  const names: Record<string, string> = {
    accommodation_standard: '住宿费标准',
    air_standard: '机票舱位',
    train_standard: '火车席别',
    city_transport_standard: '市内交通',
    meal_standard: '伙食补助',
    business_entertainment_standard: '业务招待',
    invoice_date: '发票日期',
    company_match: '公司抬头',
    stamp_detection: '印章检测',
    duplicate_check: '重复检测',
    seller_match: '销售方验证'
  }
  return names[ruleName] || ruleName
}

const getResultType = (result: string) => {
  const types: Record<string, string> = {
    pass: 'success',
    warning: 'warning',
    reject: 'danger'
  }
  return types[result] || 'info'
}

const getResultText = (result: string) => {
  const texts: Record<string, string> = {
    pass: '通过',
    warning: '警告',
    reject: '驳回'
  }
  return texts[result] || result
}

const getActualValue = (row: any) => {
  const d = row.details || {}
  switch (row.rule_name) {
    case 'accommodation_standard':
      return d.actual_daily ? `¥${d.actual_daily.toFixed(2)}/晚` : '-'
    case 'air_standard':
    case 'train_standard':
      return d.seat_type || '-'
    case 'city_transport_standard':
      return d.actual ? `¥${d.actual.toFixed(2)}` : '-'
    case 'business_entertainment_standard':
      return d.actual_per_person ? `¥${d.actual_per_person.toFixed(2)}/人` : '-'
    case 'invoice_date':
      return d.days_diff ? `${d.days_diff}天前` : '-'
    case 'stamp_detection':
      return d.has_stamp ? '有印章' : '无印章'
    case 'duplicate_check':
      return d.existing_id ? `重复发票 #${d.existing_id}` : '无重复'
    case 'company_match':
      return '已验证'
    default:
      return '-'
  }
}

const getStandardValue = (row: any) => {
  const d = row.details || {}
  switch (row.rule_name) {
    case 'accommodation_standard':
      return d.daily_limit ? `≤¥${d.daily_limit}/晚` : '-'
    case 'air_standard':
    case 'train_standard':
      return d.allowed ? d.allowed.join('/') : '-'
    case 'city_transport_standard':
      return d.daily_limit ? `¥${d.daily_limit}/天 × ${d.days || 1}天` : '-'
    case 'business_entertainment_standard':
      return d.per_person_limit ? `≤¥${d.per_person_limit}/人` : '-'
    case 'invoice_date':
      return `≤${d.max_days || 30}天内`
    case 'stamp_detection':
      return '需有印章'
    case 'duplicate_check':
      return '不可重复'
    case 'company_match':
      return '需匹配本公司'
    default:
      return '-'
  }
}

const getConfidenceColor = (confidence: number) => {
  if (confidence >= 0.8) return '#67c23a'
  if (confidence >= 0.6) return '#e6a23c'
  return '#f56c6c'
}

const getRiskLevelType = (level: string) => {
  const types: Record<string, string> = {
    low: 'success',
    medium: 'warning',
    high: 'danger'
  }
  return types[level] || 'info'
}

const getRiskScoreColor = (score: number) => {
  if (score <= 0.3) return '#67c23a'
  if (score <= 0.6) return '#e6a23c'
  return '#f56c6c'
}

onMounted(() => {
  fetchInvoice()
  fetchModifyRecords()
})
</script>

<style scoped>
.detail-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.image-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
  background: #f5f7fa;
}

.image-error {
  text-align: center;
  color: #909399;
}

.section-title {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.validation-section {
  margin-bottom: 16px;
}

.risk-section {
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
}
</style>