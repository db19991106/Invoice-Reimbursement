<template>
  <div class="upload-page">
    <el-row :gutter="20">
      <el-col :span="14">
        <el-card>
          <template #header>
            <span>上传发票</span>
          </template>
          
          <el-upload
            ref="uploadRef"
            class="upload-area"
            drag
            :action="uploadUrl"
            :data="uploadData"
            :auto-upload="false"
            :on-change="handleFileChange"
            :on-success="handleSuccess"
            :on-error="handleError"
            :on-progress="handleProgress"
            :limit="1"
            accept=".png,.jpg,.jpeg,.bmp,.gif,.pdf"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              拖拽文件到此处，或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 PNG、JPG、BMP、GIF、PDF 格式，单个文件大小不超过 10MB
              </div>
            </template>
          </el-upload>
          
          <el-form :model="form" label-width="100px" style="margin-top: 20px">
            <el-form-item label="费用类型">
              <el-select v-model="form.expense_type" placeholder="请选择费用类型">
                <el-option label="住宿费" value="accommodation" />
                <el-option label="航空票" value="transport_air" />
                <el-option label="火车票" value="transport_train" />
                <el-option label="城市交通" value="city_transport" />
                <el-option label="餐饮费" value="meal" />
                <el-option label="业务招待" value="business_entertainment" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="出差城市">
              <el-input v-model="form.destination_city" placeholder="请输入出差目的地城市" />
            </el-form-item>
            
            <el-form-item label="人数">
              <el-input-number v-model="form.person_count" :min="1" :max="100" />
            </el-form-item>
            
            <el-form-item label="出差天数">
              <el-input-number v-model="form.trip_days" :min="1" :max="365" />
            </el-form-item>
            
            <el-form-item label="报销人">
              <el-select v-model="form.employee_id" placeholder="请选择报销人" clearable filterable>
                <el-option
                  v-for="emp in employees"
                  :key="emp.id"
                  :label="`${emp.name} - ${emp.department || ''}`"
                  :value="emp.id"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="submitUpload" :loading="uploading">
                <el-icon><Upload /></el-icon>
                提交上传
              </el-button>
              <el-button @click="resetForm">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      
      <el-col :span="10">
        <el-card v-if="uploadResult">
          <template #header>
            <div class="card-header">
              <span>上传结果</span>
              <div>
                <el-tag :type="getDecisionType(invoiceData?.decision)" style="margin-right: 8px">
                  {{ getDecisionText(invoiceData?.decision) }}
                </el-tag>
                <el-tag :type="getChannelType(invoiceData?.channel)">
                  {{ getChannelText(invoiceData?.channel) }}
                </el-tag>
              </div>
            </div>
          </template>
          
          <div class="result-content">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="发票号码">
                {{ invoiceData?.invoice_no || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="发票代码">
                {{ invoiceData?.invoice_code || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="金额">
                ¥{{ invoiceData?.total_amount?.toFixed(2) || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="开票日期">
                {{ invoiceData?.date || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="销售方" :span="2">
                {{ invoiceData?.seller_name || '-' }}
              </el-descriptions-item>
            </el-descriptions>
            
            <!-- 标准对比表格 -->
            <div v-if="invoiceData?.validation_items?.length" style="margin-top: 20px">
              <h4 class="section-title">报销标准对比</h4>
              <el-table :data="invoiceData.validation_items" style="width: 100%" size="small">
                <el-table-column label="检查项目" width="80">
                  <template #default="{ row }">
                    <span>{{ getRuleName(row.rule_name) }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="实际值" width="100">
                  <template #default="{ row }">
                    <span>{{ getActualValue(row) }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="标准值" width="90">
                  <template #default="{ row }">
                    <span>{{ getStandardValue(row) }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="结果" width="60">
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
            
            <!-- 风险因素 -->
            <div v-if="invoiceData?.risk_reasons?.length" style="margin-top: 16px">
              <h4 class="section-title">风险因素</h4>
              <el-tag 
                v-for="(reason, index) in invoiceData.risk_reasons" 
                :key="index"
                type="warning"
                style="margin-right: 8px; margin-bottom: 4px"
              >
                {{ reason }}
              </el-tag>
            </div>
            
            <div style="margin-top: 20px">
              <el-button type="primary" @click="viewInvoice">
                查看详情
              </el-button>
              <el-button @click="resetForm">
                继续上传
              </el-button>
            </div>
          </div>
        </el-card>
        
        <el-card v-if="!uploadResult && !uploading">
          <template #header>
            <span>操作提示</span>
          </template>
          <div class="tips">
            <p>1. 请上传发票图片或PDF文件</p>
            <p>2. 选择正确的费用类型</p>
            <p>3. 填写出差相关信息（如适用）</p>
            <p>4. 选择报销人（可选）</p>
            <p>5. 点击"提交上传"按钮</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import axios from 'axios'

const router = useRouter()
const userId = localStorage.getItem('user_id')

const uploadRef = ref()
const uploading = ref(false)
const uploadResult = ref(false)
const invoiceData = ref<any>(null)
const selectedFile = ref<File | null>(null)

const form = reactive({
  expense_type: 'accommodation',
  destination_city: '北京',
  person_count: 1,
  trip_days: 1,
  employee_id: null as number | null
})

const employees = ref<any[]>([])

const uploadUrl = '/api/user/upload'

const uploadData = computed(() => ({
  user_id: userId,
  expense_type: form.expense_type,
  destination_city: form.destination_city,
  person_count: form.person_count,
  trip_days: form.trip_days,
  employee_id: form.employee_id || undefined
}))

const fetchEmployees = async () => {
  try {
    const res = await axios.get('/api/user/employees', {
      params: { user_id: userId }
    })
    employees.value = res.data
  } catch (e) {
    console.error('获取员工列表失败', e)
  }
}

const handleFileChange = (file: any) => {
  selectedFile.value = file.raw
}

const submitUpload = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请选择要上传的文件')
    return
  }
  
  uploading.value = true
  uploadResult.value = false
  
  const formData = new FormData()
  formData.append('file', selectedFile.value)
  formData.append('expense_type', form.expense_type)
  formData.append('destination_city', form.destination_city)
  formData.append('person_count', String(form.person_count))
  formData.append('trip_days', String(form.trip_days))
  if (form.employee_id) {
    formData.append('employee_id', String(form.employee_id))
  }
  
  try {
    // 设置超时时间为 5 分钟，因为 OCR 和 LLM 处理耗时较长
    const res = await axios.post('/api/user/upload', formData, {
      params: { user_id: userId },
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000  // 5分钟超时
    })
    
    invoiceData.value = res.data
    uploadResult.value = true
    
    ElMessage.success('上传成功')
  } catch (e: any) {
    if (e.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请稍后刷新页面查看结果')
    } else {
      ElMessage.error(e.response?.data?.detail || '上传失败')
    }
  } finally {
    uploading.value = false
  }
}

const handleSuccess = (response: any) => {
  invoiceData.value = response
  uploadResult.value = true
  ElMessage.success('上传成功')
}

const handleError = (error: any) => {
  ElMessage.error(error.message || '上传失败')
}

const handleProgress = () => {
  uploading.value = true
}

const viewInvoice = () => {
  if (invoiceData.value) {
    router.push(`/user/invoices/${invoiceData.value.file_id}`)
  }
}

const resetForm = () => {
  selectedFile.value = null
  uploadResult.value = false
  invoiceData.value = null
  form.expense_type = 'accommodation'
  form.destination_city = '北京'
  form.person_count = 1
  form.trip_days = 1
  form.employee_id = null
  uploadRef.value?.clearFiles()
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
  return texts[decision] || decision || '处理中'
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
  return texts[channel] || channel || '-'
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

onMounted(() => {
  fetchEmployees()
})
</script>

<style scoped>
.upload-page {
  padding: 20px;
}

.upload-area {
  text-align: center;
}

.el-icon--upload {
  font-size: 67px;
  color: #409EFF;
  margin-bottom: 10px;
}

.tips p {
  color: #606266;
  line-height: 2;
  margin: 0;
}

.result-content {
  text-align: left;
}

.section-title {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
