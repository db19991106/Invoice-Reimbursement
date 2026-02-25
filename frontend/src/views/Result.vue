<template>
  <div class="result-page">
    <el-button @click="$router.push('/')" class="back-button">
      <el-icon><ArrowLeft /></el-icon>
      返回仪表盘
    </el-button>

    <el-card v-if="loading" class="loading-card">
      <el-skeleton :rows="5" animated />
    </el-card>

    <template v-else-if="invoice">
      <el-row :gutter="20">
        <el-col :span="12">
          <el-card class="image-card">
            <template #header>
              <div class="card-header">发票图片</div>
            </template>
            <el-image
              :src="`/api/invoices/${invoiceId}/image`"
              :zoom-rate="1.2"
              :preview-src-list="[`/api/invoices/${invoiceId}/image`]"
              fit="contain"
              style="width: 100%"
            />
          </el-card>
        </el-col>

        <el-col :span="12">
          <el-card class="info-card">
            <template #header>
              <div class="card-header">
                <span>审核结果</span>
                <el-tag :type="getChannelType(auditResult?.channel)" style="margin-left: 10px;">
                  {{ getChannelText(auditResult?.channel) }}
                </el-tag>
              </div>
            </template>

            <div class="result-summary">
              <el-tag :type="getDecisionType(auditResult?.decision)" size="large">
                {{ getDecisionText(auditResult?.decision) }}
              </el-tag>
              <div class="risk-score">
                风险评分: {{ ((auditResult?.risk_score || 0) * 100).toFixed(1) }}%
              </div>
            </div>

            <el-divider />

            <el-descriptions :column="1" border>
              <el-descriptions-item label="发票号码">
                {{ invoice.invoice_no || 'N/A' }}
              </el-descriptions-item>
              <el-descriptions-item label="开票日期">
                {{ invoice.date || 'N/A' }}
              </el-descriptions-item>
              <el-descriptions-item label="销售方">
                {{ invoice.seller_name || 'N/A' }}
              </el-descriptions-item>
              <el-descriptions-item label="购买方">
                {{ invoice.buyer_name || 'N/A' }}
              </el-descriptions-item>
              <el-descriptions-item label="金额">
                ¥{{ invoice.amount?.toFixed(2) || '0.00' }}
              </el-descriptions-item>
              <el-descriptions-item label="税额">
                ¥{{ invoice.tax_amount?.toFixed(2) || '0.00' }}
              </el-descriptions-item>
              <el-descriptions-item label="价税合计">
                ¥{{ invoice.total_amount?.toFixed(2) || '0.00' }}
              </el-descriptions-item>
              <el-descriptions-item label="税号">
                {{ invoice.seller_tax_id || 'N/A' }}
              </el-descriptions-item>
              <el-descriptions-item label="费用类型">
                {{ getExpenseTypeText(invoice.expense_type) }}
              </el-descriptions-item>
              <el-descriptions-item label="出差目的地">
                {{ invoice.destination_city || 'N/A' }}
              </el-descriptions-item>
            </el-descriptions>
          </el-card>
        </el-col>
      </el-row>

      <el-card v-if="auditResult?.validation_items?.length > 0" class="validation-card">
        <template #header>
          <div class="card-header">
            <span>报销标准对比</span>
            <el-tag :type="getChannelType(auditResult?.channel)" size="small">
              {{ getChannelText(auditResult?.channel) }}
            </el-tag>
          </div>
        </template>

        <el-table :data="auditResult.validation_items" style="width: 100%" :row-class-name="getRowClass">
          <el-table-column prop="rule_name" label="校验项目" width="140">
            <template #default="{ row }">
              <span class="rule-name">{{ getRuleDisplayName(row.rule_name) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="发票实际值" width="150">
            <template #default="{ row }">
              <span :class="{'value-highlight': row.result === 'reject' || row.result === 'warning'}">
                {{ getActualValue(row) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="报销标准" width="150">
            <template #default="{ row }">
              <span class="standard-value">{{ getStandardValue(row) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="差额/说明" min-width="180">
            <template #default="{ row }">
              <div class="diff-cell">
                <span v-if="getDifference(row)" :class="getDiffClass(row)">
                  {{ getDifference(row) }}
                </span>
                <span v-else class="diff-normal">{{ row.message }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="result" label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="getResultTagType(row.result)" effect="dark">
                {{ getResultText(row.result) }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>

        <div class="validation-summary">
          <el-alert
            v-if="getRejectCount() > 0"
            :title="`有 ${getRejectCount()} 项不符合报销标准，请修改后重新提交`"
            type="error"
            :closable="false"
            show-icon
          />
          <el-alert
            v-else-if="getWarningCount() > 0"
            :title="`有 ${getWarningCount()} 项需要注意，可能影响报销金额`"
            type="warning"
            :closable="false"
            show-icon
          />
          <el-alert
            v-else
            title="所有校验项均通过，符合报销标准"
            type="success"
            :closable="false"
            show-icon
          />
        </div>
      </el-card>

      <el-card v-if="auditResult" class="analysis-card">
        <template #header>
          <div class="card-header">风险分析</div>
        </template>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="OCR置信度">
            {{ ((auditResult.ocr_confidence || 0) * 100).toFixed(1) }}%
          </el-descriptions-item>
          <el-descriptions-item label="签名比对分数">
            {{ auditResult.signature_score 
                ? (auditResult.signature_score * 100).toFixed(1) + '%' 
                : '未验证' }}
          </el-descriptions-item>
          <el-descriptions-item label="印章检测">
            <el-tag :type="auditResult.stamp_detected ? 'success' : 'danger'" size="small">
              {{ auditResult.stamp_detected ? '已检测到' : '未检测到' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="重复检测">
            <el-tag :type="auditResult.duplicate_checked ? 'success' : 'info'" size="small">
              {{ auditResult.duplicate_checked ? '已检测' : '未检测' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="风险等级">
            <el-tag :type="getRiskType(auditResult.risk_level)">
              {{ getRiskText(auditResult.risk_level) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="审核决策">
            <el-tag :type="getDecisionType(auditResult.decision)">
              {{ getDecisionText(auditResult.decision) }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="auditResult.risk_reasons?.length > 0" class="risk-factors">
          <h4>风险因素</h4>
          <el-tag
            v-for="(reason, index) in auditResult.risk_reasons"
            :key="index"
            type="warning"
            class="risk-tag"
          >
            {{ reason }}
          </el-tag>
        </div>
      </el-card>
    </template>

    <el-empty v-else description="未找到发票信息" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft } from '@element-plus/icons-vue'
import axios from 'axios'

const route = useRoute()
const invoiceId = parseInt(route.params.id as string)

const loading = ref(true)
const invoice = ref<any>(null)
const auditResult = ref<any>(null)

const fetchData = async () => {
  try {
    loading.value = true
    
    const invoiceRes = await axios.get(`/api/invoices/${invoiceId}`)
    invoice.value = invoiceRes.data
    
    try {
      const auditRes = await axios.get(`/api/invoices/${invoiceId}/audit`)
      auditResult.value = auditRes.data
    } catch (e) {
      console.error('No audit result yet')
    }
  } catch (e) {
    console.error('Failed to fetch invoice:', e)
  } finally {
    loading.value = false
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
    green: 'success',
    yellow: 'warning',
    red: 'danger',
    pending: 'info'
  }
  return map[channel] || 'info'
}

const getChannelText = (channel: string) => {
  const map: Record<string, string> = {
    green: '绿色通道 - 自动通过',
    yellow: '黄色通道 - 需人工复核',
    red: '红色通道 - 自动驳回',
    pending: '待审核'
  }
  return map[channel] || channel
}

const getRiskType = (level: string) => {
  const map: Record<string, string> = {
    high: 'danger',
    medium: 'warning',
    low: 'success'
  }
  return map[level] || 'info'
}

const getRiskText = (level: string) => {
  const map: Record<string, string> = {
    high: '高风险',
    medium: '中风险',
    low: '低风险'
  }
  return map[level] || level
}

const getDecisionType = (decision: string) => {
  const map: Record<string, string> = {
    approve: 'success',
    reject: 'danger',
    review: 'warning'
  }
  return map[decision] || 'info'
}

const getDecisionText = (decision: string) => {
  const map: Record<string, string> = {
    approve: '自动通过',
    reject: '自动驳回',
    review: '需要人工复核'
  }
  return map[decision] || decision
}

const getResultTagType = (result: string) => {
  const map: Record<string, string> = {
    pass: 'success',
    warning: 'warning',
    reject: 'danger'
  }
  return map[result] || 'info'
}

const getResultText = (result: string) => {
  const map: Record<string, string> = {
    pass: '通过',
    warning: '预警',
    reject: '驳回'
  }
  return map[result] || result
}

// 规则名称中文映射
const getRuleDisplayName = (ruleName: string) => {
  const map: Record<string, string> = {
    'accommodation_standard': '住宿费标准',
    'air_standard': '机票舱位',
    'train_standard': '火车席别',
    'city_transport_standard': '市内交通',
    'meal_standard': '伙食补助',
    'business_entertainment_standard': '业务招待',
    'invoice_date': '发票日期',
    'company_match': '公司抬头',
    'stamp_detection': '印章检测',
    'duplicate_check': '重复检测',
    'seller_match': '销售方验证'
  }
  return map[ruleName] || ruleName
}

// 获取发票实际值
const getActualValue = (row: any) => {
  const d = row.details || {}
  switch (row.rule_name) {
    case 'accommodation_standard':
      return d.actual_daily ? `¥${d.actual_daily.toFixed(2)}/晚` : '-'
    case 'air_standard':
      return d.seat_type || '-'
    case 'train_standard':
      return d.seat_type || '-'
    case 'city_transport_standard':
      return d.actual ? `¥${d.actual.toFixed(2)}` : '-'
    case 'meal_standard':
      return d.days ? `${d.days}天` : '-'
    case 'business_entertainment_standard':
      return d.actual_per_person ? `¥${d.actual_per_person.toFixed(2)}/人` : '-'
    case 'invoice_date':
      return d.days_diff ? `${d.days_diff}天前` : '-'
    case 'company_match':
      return '已验证'
    case 'stamp_detection':
      return d.has_stamp ? '有印章' : '无印章'
    case 'duplicate_check':
      return d.existing_id ? `重复发票 #${d.existing_id}` : '无重复'
    default:
      return '-'
  }
}

// 获取报销标准值
const getStandardValue = (row: any) => {
  const d = row.details || {}
  switch (row.rule_name) {
    case 'accommodation_standard':
      return d.daily_limit ? `≤¥${d.daily_limit.toFixed(0)}/晚` : '无限制'
    case 'air_standard':
      return d.allowed ? d.allowed.join('/') : '经济舱'
    case 'train_standard':
      return d.allowed ? d.allowed.join('/') : '二等座'
    case 'city_transport_standard':
      return d.daily_limit ? `¥${d.daily_limit}/天 × ${d.days}天` : '-'
    case 'meal_standard':
      return d.daily_limit ? `¥${d.daily_limit}/天 × ${d.days}天` : '-'
    case 'business_entertainment_standard':
      return d.per_person_limit ? `≤¥${d.per_person_limit}/人` : '-'
    case 'invoice_date':
      return d.max_days ? `≤${d.max_days}天内` : '30天内'
    case 'company_match':
      return '需匹配本公司'
    case 'stamp_detection':
      return '需有印章'
    case 'duplicate_check':
      return '不可重复'
    default:
      return '-'
  }
}

// 获取差额
const getDifference = (row: any) => {
  if (row.result === 'pass') return null
  const d = row.details || {}
  switch (row.rule_name) {
    case 'accommodation_standard':
      if (d.excess) return `超标 ¥${d.excess.toFixed(2)}/晚`
      break
    case 'city_transport_standard':
      if (d.excess) return `超标 ¥${d.excess.toFixed(2)}`
      break
    case 'business_entertainment_standard':
      if (d.actual_per_person && d.per_person_limit) {
        const diff = d.actual_per_person - d.per_person_limit
        if (diff > 0) return `人均超标 ¥${diff.toFixed(2)}`
      }
      break
    case 'invoice_date':
      if (d.days_diff && d.max_days && d.days_diff > d.max_days) {
        return `逾期 ${d.days_diff - d.max_days} 天`
      }
      break
  }
  return null
}

// 获取差额样式类
const getDiffClass = (row: any) => {
  if (row.result === 'reject') return 'diff-reject'
  if (row.result === 'warning') return 'diff-warning'
  return 'diff-normal'
}

// 表格行样式
const getRowClass = ({ row }: { row: any }) => {
  if (row.result === 'reject') return 'row-reject'
  if (row.result === 'warning') return 'row-warning'
  return ''
}

// 统计数量
const getRejectCount = () => {
  return auditResult.value?.validation_items?.filter((i: any) => i.result === 'reject').length || 0
}

const getWarningCount = () => {
  return auditResult.value?.validation_items?.filter((i: any) => i.result === 'warning').length || 0
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.result-page {
  padding: 20px;
}

.back-button {
  margin-bottom: 20px;
}

.loading-card,
.image-card,
.info-card,
.validation-card,
.analysis-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  font-size: 16px;
  font-weight: 600;
}

.result-summary {
  display: flex;
  align-items: center;
  gap: 20px;
}

.risk-score {
  font-size: 14px;
  color: #606266;
}

.risk-factors {
  margin-top: 20px;
}

.risk-factors h4 {
  margin-bottom: 10px;
}

.risk-tag {
  margin-right: 10px;
  margin-bottom: 10px;
}

/* 报销标准对比样式 */
.rule-name {
  font-weight: 500;
  color: #303133;
}

.value-highlight {
  color: #f56c6c;
  font-weight: 600;
}

.standard-value {
  color: #67c23a;
  font-weight: 500;
}

.diff-cell {
  font-size: 13px;
}

.diff-reject {
  color: #f56c6c;
  font-weight: 600;
}

.diff-warning {
  color: #e6a23c;
  font-weight: 500;
}

.diff-normal {
  color: #909399;
}

.validation-summary {
  margin-top: 16px;
}

:deep(.row-reject) {
  background-color: #fef0f0 !important;
}

:deep(.row-warning) {
  background-color: #fdf6ec !important;
}

:deep(.el-table .row-reject:hover > td) {
  background-color: #fde2e2 !important;
}

:deep(.el-table .row-warning:hover > td) {
  background-color: #faecd8 !important;
}
</style>
