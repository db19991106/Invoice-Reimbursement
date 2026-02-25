<template>
  <div class="upload-page">
    <el-row :gutter="20">
      <!-- 左侧：上传表单 -->
      <el-col :span="10">
        <el-card class="upload-card">
          <template #header>
            <div class="card-header">
              <span>上传发票</span>
            </div>
          </template>
          
          <el-upload
            v-model:file-list="fileList"
            class="upload-demo"
            drag
            :auto-upload="false"
            :on-change="handleChange"
            :limit="10"
            accept="image/*,.pdf"
            multiple
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              拖拽文件到此处或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持jpg、png、jpeg、pdf格式，单个文件不超过10MB
              </div>
            </template>
          </el-upload>

          <el-form :model="form" label-width="100px" style="margin-top: 20px;" size="default">
            <el-form-item label="选择员工">
              <el-select v-model="form.employee_id" placeholder="请选择员工" clearable @change="onEmployeeChange" style="width: 100%;">
                <el-option
                  v-for="emp in employees"
                  :key="emp.id"
                  :label="`${emp.name} (${getLevelText(emp.level)})`"
                  :value="emp.id"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="费用类型">
              <el-select v-model="form.expense_type" placeholder="请选择费用类型" style="width: 100%;">
                <el-option label="住宿费" value="accommodation" />
                <el-option label="机票" value="transport_air" />
                <el-option label="火车票" value="transport_train" />
                <el-option label="市内交通" value="city_transport" />
                <el-option label="伙食补助" value="meal" />
                <el-option label="业务招待" value="business_entertainment" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="出差目的地">
              <el-select v-model="form.destination_city" placeholder="请选择出差城市" filterable style="width: 100%;">
                <el-option-group v-for="group in cityOptions" :key="group.label" :label="group.label">
                  <el-option
                    v-for="city in group.options"
                    :key="city.value"
                    :label="city.label"
                    :value="city.value"
                  />
                </el-option-group>
              </el-select>
            </el-form-item>
            
            <el-form-item label="出差天数" v-if="form.expense_type === 'accommodation' || form.expense_type === 'city_transport' || form.expense_type === 'meal'">
              <el-input-number v-model="form.trip_days" :min="1" :max="30" style="width: 100%;" />
            </el-form-item>
            
            <el-form-item label="人数" v-if="form.expense_type === 'business_entertainment'">
              <el-input-number v-model="form.person_count" :min="1" :max="20" style="width: 100%;" />
            </el-form-item>
          </el-form>

          <div class="action-buttons">
            <el-button type="primary" @click="handleSubmit" :loading="uploading">
              提交审核
            </el-button>
            <el-button @click="handleOCRVisualize" :loading="visualizing">
              OCR预览
            </el-button>
            <el-button @click="handleReset">重置</el-button>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：审核结果展示 -->
      <el-col :span="14">
        <!-- 无审核结果时的占位 -->
        <el-card v-if="results.length === 0" class="result-placeholder">
          <el-empty description="上传发票后，审核结果将在此显示">
            <template #image>
              <el-icon :size="80" color="#c0c4cc"><Document /></el-icon>
            </template>
          </el-empty>
        </el-card>

        <!-- 有审核结果时展示详情 -->
        <template v-else>
          <div v-for="(result, index) in results" :key="index" class="result-container">
            <!-- 审核状态汇总 -->
            <el-card class="result-card">
              <template #header>
                <div class="card-header">
                  <span>审核结果</span>
                  <div class="status-badges">
                    <el-tag :type="getResultType(result.status)" size="large" effect="dark">
                      {{ getResultText(result.status) }}
                    </el-tag>
                    <el-tag :type="getChannelType(result.channel)" size="large">
                      {{ getChannelText(result.channel) }}
                    </el-tag>
                  </div>
                </div>
              </template>

              <!-- 驳回原因提示 -->
              <div v-if="result.status === 'reject'" class="result-alert">
                <el-alert type="error" :closable="false" show-icon>
                  <template #title>
                    <span class="alert-title">发票已驳回，请修改后重新提交</span>
                  </template>
                  <div class="alert-reasons">
                    <div v-for="(reason, idx) in getRejectReasons(result.audit)" :key="idx" class="reason-item">
                      <el-icon color="#f56c6c"><CircleCloseFilled /></el-icon>
                      <span>{{ reason }}</span>
                    </div>
                  </div>
                </el-alert>
              </div>

              <!-- 预警原因提示 -->
              <div v-else-if="result.status === 'review'" class="result-alert">
                <el-alert type="warning" :closable="false" show-icon>
                  <template #title>
                    <span class="alert-title">发票需要人工复核，请耐心等待</span>
                  </template>
                  <div class="alert-reasons">
                    <div v-for="(reason, idx) in getWarningReasons(result.audit)" :key="idx" class="reason-item warning">
                      <el-icon color="#e6a23c"><WarningFilled /></el-icon>
                      <span>{{ reason }}</span>
                    </div>
                  </div>
                </el-alert>
              </div>

              <!-- 通过提示 -->
              <div v-else class="result-alert">
                <el-alert type="success" :closable="false" show-icon>
                  <template #title>
                    <span class="alert-title">发票审核通过，符合报销标准</span>
                  </template>
                </el-alert>
              </div>

              <!-- 发票基本信息 -->
              <el-descriptions v-if="result.audit?.invoice_data" :column="2" border class="invoice-info" size="small">
                <el-descriptions-item label="发票号码">
                  {{ result.audit.invoice_data.invoice_no || '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="开票日期">
                  {{ result.audit.invoice_data.date || '-' }}
                </el-descriptions-item>
                <el-descriptions-item label="价税合计">
                  <span class="amount">¥{{ (result.audit.invoice_data.total_amount || 0).toFixed(2) }}</span>
                </el-descriptions-item>
                <el-descriptions-item label="销售方">
                  {{ result.audit.invoice_data.seller_name || '-' }}
                </el-descriptions-item>
              </el-descriptions>
            </el-card>

            <!-- 报销标准对比表 -->
            <el-card v-if="result.audit?.validation_items?.length > 0" class="validation-card">
              <template #header>
                <div class="card-header">
                  <span>报销标准对比</span>
                </div>
              </template>

              <el-table :data="result.audit.validation_items" style="width: 100%" :row-class-name="getRowClass" size="small">
                <el-table-column prop="rule_name" label="校验项目" width="120">
                  <template #default="{ row }">
                    <span class="rule-name">{{ getRuleDisplayName(row.rule_name) }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="发票实际值" width="130">
                  <template #default="{ row }">
                    <span :class="{'value-highlight': row.result === 'reject' || row.result === 'warning'}">
                      {{ getActualValue(row) }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column label="报销标准" width="130">
                  <template #default="{ row }">
                    <span class="standard-value">{{ getStandardValue(row) }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="差额/说明" min-width="150">
                  <template #default="{ row }">
                    <div class="diff-cell">
                      <span v-if="getDifference(row)" :class="getDiffClass(row)">
                        {{ getDifference(row) }}
                      </span>
                      <span v-else class="diff-normal">{{ row.message }}</span>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column prop="result" label="状态" width="80" align="center">
                  <template #default="{ row }">
                    <el-tag :type="getValidationResultType(row.result)" effect="dark" size="small">
                      {{ getValidationResultText(row.result) }}
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>

            <!-- 风险分析 -->
            <el-card v-if="result.audit" class="risk-card">
              <template #header>
                <div class="card-header">风险分析</div>
              </template>

              <el-row :gutter="12">
                <el-col :span="6">
                  <div class="risk-stat">
                    <div class="risk-value">{{ ((result.audit.ocr_confidence || 0) * 100).toFixed(0) }}%</div>
                    <div class="risk-label">OCR置信度</div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="risk-stat">
                    <div class="risk-value" :class="getRiskClass(result.audit.risk_level)">
                      {{ getRiskText(result.audit.risk_level) }}
                    </div>
                    <div class="risk-label">风险等级</div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="risk-stat">
                    <div class="risk-value">{{ ((result.audit.risk_score || 0) * 100).toFixed(0) }}%</div>
                    <div class="risk-label">风险评分</div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="risk-stat">
                    <div class="risk-value">
                      <el-tag :type="result.audit.stamp_detected ? 'success' : 'danger'" size="small">
                        {{ result.audit.stamp_detected ? '已检测' : '未检测' }}
                      </el-tag>
                    </div>
                    <div class="risk-label">印章检测</div>
                  </div>
                </el-col>
              </el-row>

              <div v-if="result.audit.risk_reasons?.length > 0" class="risk-factors">
                <h4>风险因素</h4>
                <el-tag v-for="(reason, idx) in result.audit.risk_reasons" :key="idx" type="warning" class="risk-tag" size="small">
                  {{ reason }}
                </el-tag>
              </div>
            </el-card>
          </div>
        </template>
      </el-col>
    </el-row>

    <!-- OCR预览对话框 -->
    <el-dialog v-model="visualDialogVisible" title="OCR识别结果" width="80%">
      <div v-if="visualImage" style="text-align: center;">
        <img :src="visualImage" style="max-width: 100%;" />
      </div>
      <div v-else style="text-align: center; padding: 20px;">
        <el-empty description="暂无识别结果" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled, CircleCloseFilled, WarningFilled, Document } from '@element-plus/icons-vue'
import axios from 'axios'

const router = useRouter()

const fileList = ref([])
const uploading = ref(false)
const results = ref<any[]>([])
const visualizing = ref(false)
const visualDialogVisible = ref(false)
const visualImage = ref('')

const form = reactive({
  employee_id: null as number | null,
  expense_type: 'accommodation',
  destination_city: '北京',
  trip_days: 1,
  person_count: 1
})

const employees = ref<any[]>([])

const cityOptions = [
  {
    label: '一线城市',
    options: [
      { label: '北京', value: '北京' },
      { label: '上海', value: '上海' },
      { label: '广州', value: '广州' },
      { label: '深圳', value: '深圳' }
    ]
  },
  {
    label: '省会城市',
    options: [
      { label: '成都', value: '成都' },
      { label: '杭州', value: '杭州' },
      { label: '南京', value: '南京' },
      { label: '武汉', value: '武汉' },
      { label: '西安', value: '西安' },
      { label: '郑州', value: '郑州' },
      { label: '长沙', value: '长沙' },
      { label: '沈阳', value: '沈阳' },
      { label: '青岛', value: '青岛' },
      { label: '济南', value: '济南' },
      { label: '大连', value: '大连' },
      { label: '宁波', value: '宁波' },
      { label: '厦门', value: '厦门' },
      { label: '福州', value: '福州' }
    ]
  },
  {
    label: '其他城市',
    options: [
      { label: '苏州', value: '苏州' },
      { label: '无锡', value: '无锡' },
      { label: '东莞', value: '东莞' },
      { label: '佛山', value: '佛山' },
      { label: '天津', value: '天津' },
      { label: '重庆', value: '重庆' },
      { label: '哈尔滨', value: '哈尔滨' },
      { label: '长春', value: '长春' },
      { label: '南昌', value: '南昌' },
      { label: '贵阳', value: '贵阳' },
      { label: '太原', value: '太原' },
      { label: '石家庄', value: '石家庄' }
    ]
  }
]

const fetchEmployees = async () => {
  try {
    const res = await axios.get('/api/employees')
    employees.value = res.data
  } catch (e) {
    console.error('Failed to fetch employees:', e)
  }
}

const getLevelText = (level: number) => {
  if (level >= 11) return '管理层'
  return '普通员工'
}

const onEmployeeChange = (empId: number) => {
  const emp = employees.value.find(e => e.id === empId)
  if (emp) {
    console.log('Selected employee level:', emp.level)
  }
}

const handleChange = (file: any, files: any) => {
  fileList.value = files
}

const handleSubmit = async () => {
  if (fileList.value.length === 0) {
    ElMessage.warning('请先选择要上传的文件')
    return
  }

  uploading.value = true
  results.value = []

  try {
    for (const fileItem of fileList.value) {
      const formData = new FormData()
      formData.append('file', fileItem.raw)
      if (form.employee_id) {
        formData.append('employee_id', form.employee_id.toString())
      }
      formData.append('expense_type', form.expense_type)
      formData.append('destination_city', form.destination_city)
      formData.append('trip_days', form.trip_days.toString())
      formData.append('person_count', form.person_count.toString())

      const res = await axios.post('/api/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })

      // 获取完整审核结果 - 使用不需要认证的 /api/audit/{id} 端点
      if (res.data.file_id) {
        try {
          const auditRes = await axios.get(`/api/audit/${res.data.file_id}`)
          results.value.push({
            ...res.data,
            status: auditRes.data.decision || res.data.status,
            channel: auditRes.data.channel || 'pending',
            audit: auditRes.data
          })
        } catch (e) {
          console.error('Failed to get audit result:', e)
          results.value.push(res.data)
        }
      } else {
        results.value.push(res.data)
      }
    }

    ElMessage.success('审核完成')
    // 不再跳转，留在当前页面展示结果
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '上传失败')
  } finally {
    uploading.value = false
  }
}

const handleReset = () => {
  fileList.value = []
  form.employee_id = null
  form.expense_type = 'accommodation'
  form.destination_city = '北京'
  form.trip_days = 1
  form.person_count = 1
  results.value = []
  visualImage.value = ''
}

const handleOCRVisualize = async () => {
  if (fileList.value.length === 0) {
    ElMessage.warning('请先选择要上传的文件')
    return
  }
  
  visualizing.value = true
  visualDialogVisible.value = true
  
  try {
    const fileItem = fileList.value[0]
    const formData = new FormData()
    formData.append('file', fileItem.raw)
    
    const res = await axios.post('/api/ocr/visualize', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    
    // 后端返回 JSON: { image_url: "/api/ocr/image/xxx.jpg", image_name: "xxx.jpg" }
    // 使用 image_url 加载图片，添加时间戳防止缓存
    visualImage.value = `${res.data.image_url}?t=${Date.now()}`
    ElMessage.success('OCR识别完成')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'OCR识别失败')
  } finally {
    visualizing.value = false
  }
}

const getResultType = (status: string) => {
  const map: Record<string, string> = {
    uploaded: 'info',
    pending: 'info',
    approve: 'success',
    reject: 'danger',
    review: 'warning'
  }
  return map[status] || 'info'
}

const getResultText = (status: string) => {
  const map: Record<string, string> = {
    uploaded: '已上传',
    pending: '待审核',
    approve: '已通过',
    reject: '已驳回',
    review: '需复核'
  }
  return map[status] || status
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
    green: '绿色通道',
    yellow: '黄色通道',
    red: '红色通道',
    pending: '待审核'
  }
  return map[channel] || channel
}

// 费用类型中文
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

// 校验结果样式
const getValidationResultType = (result: string) => {
  const map: Record<string, string> = {
    pass: 'success',
    warning: 'warning',
    reject: 'danger'
  }
  return map[result] || 'info'
}

const getValidationResultText = (result: string) => {
  const map: Record<string, string> = {
    pass: '通过',
    warning: '预警',
    reject: '驳回'
  }
  return map[result] || result
}

// 获取驳回理由
const getRejectReasons = (audit: any) => {
  if (!audit?.validation_items) return []
  return audit.validation_items
    .filter((item: any) => item.result === 'reject')
    .map((item: any) => item.message)
}

// 获取预警理由
const getWarningReasons = (audit: any) => {
  if (!audit?.validation_items) return []
  return audit.validation_items
    .filter((item: any) => item.result === 'warning')
    .map((item: any) => item.message)
}

// 风险等级
const getRiskClass = (level: string) => {
  const map: Record<string, string> = {
    high: 'risk-high',
    medium: 'risk-medium',
    low: 'risk-low'
  }
  return map[level] || ''
}

const getRiskText = (level: string) => {
  const map: Record<string, string> = {
    high: '高',
    medium: '中',
    low: '低'
  }
  return map[level] || level
}

onMounted(() => {
  fetchEmployees()
})
</script>

<style scoped>
.upload-page {
  padding: 0;
}

.upload-card {
  height: 100%;
}

.card-header {
  font-size: 16px;
  font-weight: 600;
}

.action-buttons {
  margin-top: 20px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.el-upload__tip {
  color: #909399;
  margin-top: 7px;
}

/* 右侧结果区域 */
.result-placeholder {
  height: 100%;
  min-height: 600px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.result-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-card,
.validation-card,
.risk-card {
  margin: 0;
}

/* 审核结果样式 */
.status-badges {
  display: flex;
  gap: 10px;
}

.result-alert {
  margin-bottom: 16px;
}

.alert-title {
  font-weight: 600;
  font-size: 14px;
}

.alert-reasons {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.reason-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.reason-item.warning {
  color: #b88230;
}

.invoice-info {
  margin-top: 12px;
}

.amount {
  font-size: 14px;
  font-weight: 600;
  color: #409eff;
}

/* 报销标准对比样式 */
.rule-name {
  font-weight: 500;
  color: #303133;
  font-size: 13px;
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
  font-size: 12px;
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

/* 风险分析样式 */
.risk-stat {
  text-align: center;
  padding: 12px 8px;
  background: #f5f7fa;
  border-radius: 8px;
}

.risk-value {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.risk-value.risk-high {
  color: #f56c6c;
}

.risk-value.risk-medium {
  color: #e6a23c;
}

.risk-value.risk-low {
  color: #67c23a;
}

.risk-label {
  font-size: 11px;
  color: #909399;
  margin-top: 4px;
}

.risk-factors {
  margin-top: 12px;
}

.risk-factors h4 {
  margin-bottom: 8px;
  font-size: 13px;
  color: #606266;
}

.risk-tag {
  margin-right: 6px;
  margin-bottom: 6px;
}
</style>
