<template>
  <div class="employee-management">
    <el-card>
      <!-- 工具栏 -->
      <div class="toolbar">
        <div class="search-bar">
          <el-input 
            v-model="searchKeyword" 
            placeholder="搜索员工姓名/部门" 
            clearable 
            style="width: 200px;"
            @keyup.enter="fetchEmployees"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-select v-model="filterDepartment" placeholder="部门筛选" clearable style="width: 150px; margin-left: 10px;" @change="fetchEmployees">
            <el-option label="全部部门" value="" />
            <el-option v-for="dept in departments" :key="dept" :label="dept" :value="dept" />
          </el-select>
          <el-button type="primary" style="margin-left: 10px;" @click="fetchEmployees">搜索</el-button>
        </div>
        <div class="action-bar">
          <el-button type="success" @click="showAddDialog">
            <el-icon><Plus /></el-icon>
            添加员工
          </el-button>
          <el-button type="danger" :disabled="selectedEmployees.length === 0" @click="batchDelete">
            <el-icon><Delete /></el-icon>
            批量删除
          </el-button>
        </div>
      </div>

      <!-- 员工列表 -->
      <el-table 
        :data="employees" 
        style="width: 100%" 
        v-loading="loading"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="department" label="部门" width="120" />
        <el-table-column prop="level" label="职级" width="100">
          <template #default="{ row }">
            <el-tag :type="getLevelType(row.level)">{{ getLevelText(row.level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="credit_score" label="信用评分" width="100">
          <template #default="{ row }">
            <el-progress 
              :percentage="row.credit_score" 
              :color="getCreditColor(row.credit_score)"
              :stroke-width="15"
              :text-inside="true"
            />
          </template>
        </el-table-column>
        <el-table-column prop="signature_path" label="签名" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.signature_path" type="success" size="small">已上传</el-tag>
            <el-tag v-else type="info" size="small">未上传</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="报销统计" width="180">
          <template #default="{ row }">
            <div class="expense-stats">
              <span class="stat-item">
                <el-icon><Document /></el-icon>
                {{ row.invoice_count || 0 }}张
              </span>
              <span class="stat-item">
                <el-icon><Money /></el-icon>
                ¥{{ formatAmount(row.total_expense || 0) }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" text size="small" @click="showEditDialog(row)">编辑</el-button>
            <el-button type="info" text size="small" @click="viewEmployeeDetail(row)">详情</el-button>
            <el-button type="danger" text size="small" @click="deleteEmployee(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @current-change="fetchEmployees"
          @size-change="fetchEmployees"
        />
      </div>
    </el-card>

    <!-- 添加/编辑员工弹窗 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="isEdit ? '编辑员工' : '添加员工'" 
      width="500px"
      @close="resetForm"
    >
      <el-form :model="employeeForm" :rules="formRules" ref="formRef" label-width="100px">
        <el-form-item label="姓名" prop="name">
          <el-input v-model="employeeForm.name" placeholder="请输入员工姓名" />
        </el-form-item>
        <el-form-item label="部门" prop="department">
          <el-select v-model="employeeForm.department" placeholder="请选择部门" style="width: 100%;" filterable allow-create>
            <el-option v-for="dept in departments" :key="dept" :label="dept" :value="dept" />
          </el-select>
        </el-form-item>
        <el-form-item label="职级" prop="level">
          <el-select v-model="employeeForm.level" placeholder="请选择职级" style="width: 100%;">
            <el-option label="普通员工" value="staff" />
            <el-option label="部门经理" value="manager" />
            <el-option label="总监" value="director" />
            <el-option label="副总裁" value="vp" />
            <el-option label="总裁" value="ceo" />
          </el-select>
        </el-form-item>
        <el-form-item label="信用评分" prop="credit_score">
          <el-slider v-model="employeeForm.credit_score" :min="0" :max="100" show-input />
        </el-form-item>
        <el-form-item label="签名文件">
          <el-upload
            class="signature-uploader"
            :action="`/api/employees/${employeeForm.id || 'new'}/signature`"
            :show-file-list="false"
            :on-success="handleSignatureSuccess"
            :before-upload="beforeSignatureUpload"
            accept="image/*"
          >
            <img v-if="signaturePreview" :src="signaturePreview" class="signature-preview" />
            <el-icon v-else class="signature-uploader-icon"><Plus /></el-icon>
          </el-upload>
          <div class="upload-tip">支持 jpg、png 格式，建议尺寸 200x100</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>

    <!-- 员工详情弹窗 -->
    <el-dialog v-model="detailDialogVisible" title="员工详情" width="700px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="员工ID">{{ currentEmployee?.id }}</el-descriptions-item>
        <el-descriptions-item label="姓名">{{ currentEmployee?.name }}</el-descriptions-item>
        <el-descriptions-item label="部门">{{ currentEmployee?.department }}</el-descriptions-item>
        <el-descriptions-item label="职级">{{ getLevelText(currentEmployee?.level) }}</el-descriptions-item>
        <el-descriptions-item label="信用评分">
          <el-progress 
            :percentage="currentEmployee?.credit_score || 0" 
            :color="getCreditColor(currentEmployee?.credit_score || 0)"
          />
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(currentEmployee?.created_at) }}</el-descriptions-item>
      </el-descriptions>

      <el-divider content-position="left">报销记录</el-divider>
      
      <el-table :data="employeeInvoices" style="width: 100%" max-height="300">
        <el-table-column prop="invoice_no" label="发票号码" width="120" />
        <el-table-column prop="total_amount" label="金额" width="100">
          <template #default="{ row }">
            ¥{{ row.total_amount?.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="date" label="开票日期" width="100" />
        <el-table-column prop="seller_name" label="销售方" show-overflow-tooltip />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Delete, Document, Money } from '@element-plus/icons-vue'
import axios from 'axios'

const auditorId = localStorage.getItem('auditor_id')

const loading = ref(false)
const submitLoading = ref(false)
const employees = ref<any[]>([])
const selectedEmployees = ref<any[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchKeyword = ref('')
const filterDepartment = ref('')
const departments = ref<string[]>(['技术部', '市场部', '财务部', '人事部', '运营部', '产品部', '设计部', '行政部'])

const dialogVisible = ref(false)
const detailDialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref()
const signaturePreview = ref('')
const currentEmployee = ref<any>(null)
const employeeInvoices = ref<any[]>([])

const employeeForm = reactive({
  id: 0,
  name: '',
  department: '',
  level: 'staff',
  credit_score: 80,
  signature_path: ''
})

const formRules = {
  name: [{ required: true, message: '请输入员工姓名', trigger: 'blur' }],
  department: [{ required: true, message: '请选择部门', trigger: 'change' }],
  level: [{ required: true, message: '请选择职级', trigger: 'change' }]
}

const fetchEmployees = async () => {
  loading.value = true
  try {
    let url = `/api/employees?skip=${(currentPage.value - 1) * pageSize.value}&limit=${pageSize.value}`
    
    const res = await axios.get(url)
    let data = res.data
    
    // 前端过滤
    if (searchKeyword.value) {
      data = data.filter((emp: any) => 
        emp.name?.includes(searchKeyword.value) || 
        emp.department?.includes(searchKeyword.value)
      )
    }
    if (filterDepartment.value) {
      data = data.filter((emp: any) => emp.department === filterDepartment.value)
    }
    
    employees.value = data
    total.value = data.length
  } catch (e) {
    ElMessage.error('获取员工列表失败')
  } finally {
    loading.value = false
  }
}

const handleSelectionChange = (selection: any[]) => {
  selectedEmployees.value = selection
}

const showAddDialog = () => {
  isEdit.value = false
  resetForm()
  dialogVisible.value = true
}

const showEditDialog = (employee: any) => {
  isEdit.value = true
  Object.assign(employeeForm, {
    id: employee.id,
    name: employee.name,
    department: employee.department,
    level: employee.level || 'staff',
    credit_score: employee.credit_score || 80,
    signature_path: employee.signature_path || ''
  })
  if (employee.signature_path) {
    signaturePreview.value = `/api/upload/employees/${employee.id}/signature`
  }
  dialogVisible.value = true
}

const resetForm = () => {
  Object.assign(employeeForm, {
    id: 0,
    name: '',
    department: '',
    level: 'staff',
    credit_score: 80,
    signature_path: ''
  })
  signaturePreview.value = ''
}

const submitForm = async () => {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    if (isEdit.value) {
      await axios.put(`/api/employees/${employeeForm.id}`, employeeForm)
      ElMessage.success('更新成功')
    } else {
      await axios.post('/api/employees', employeeForm)
      ElMessage.success('添加成功')
    }
    dialogVisible.value = false
    fetchEmployees()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    submitLoading.value = false
  }
}

const deleteEmployee = async (employee: any) => {
  try {
    await ElMessageBox.confirm(`确定要删除员工"${employee.name}"吗？`, '确认删除', { type: 'warning' })
    
    await axios.delete(`/api/employees/${employee.id}`)
    ElMessage.success('删除成功')
    fetchEmployees()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}

const batchDelete = async () => {
  try {
    await ElMessageBox.confirm(`确定要删除选中的 ${selectedEmployees.value.length} 名员工吗？`, '确认删除', { type: 'warning' })
    
    for (const emp of selectedEmployees.value) {
      await axios.delete(`/api/employees/${emp.id}`)
    }
    ElMessage.success('批量删除成功')
    fetchEmployees()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  }
}

const viewEmployeeDetail = async (employee: any) => {
  currentEmployee.value = employee
  detailDialogVisible.value = true
  
  // 获取员工的报销记录
  try {
    const res = await axios.get(`/api/invoices?employee_id=${employee.id}`)
    employeeInvoices.value = res.data.slice(0, 10)
  } catch (e) {
    employeeInvoices.value = []
  }
}

const beforeSignatureUpload = (file: any) => {
  const isImage = file.type.startsWith('image/')
  const isLt2M = file.size / 1024 / 1024 < 2

  if (!isImage) {
    ElMessage.error('只能上传图片文件!')
    return false
  }
  if (!isLt2M) {
    ElMessage.error('图片大小不能超过 2MB!')
    return false
  }
  return true
}

const handleSignatureSuccess = (response: any) => {
  signaturePreview.value = response.signature_path
  employeeForm.signature_path = response.signature_path
  ElMessage.success('签名上传成功')
}

const getLevelType = (level: string) => {
  const map: Record<string, string> = {
    staff: '',
    manager: 'success',
    director: 'warning',
    vp: 'danger',
    ceo: 'danger'
  }
  return map[level] || ''
}

const getLevelText = (level: string) => {
  const map: Record<string, string> = {
    staff: '普通员工',
    manager: '部门经理',
    director: '总监',
    vp: '副总裁',
    ceo: '总裁'
  }
  return map[level] || level || '普通员工'
}

const getCreditColor = (score: number) => {
  if (score >= 80) return '#67C23A'
  if (score >= 60) return '#E6A23C'
  return '#F56C6C'
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

const formatAmount = (amount: number) => {
  if (amount >= 10000) {
    return (amount / 10000).toFixed(2) + '万'
  }
  return amount.toFixed(2)
}

onMounted(() => {
  fetchEmployees()
})
</script>

<style scoped>
.employee-management {
  padding: 0;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #ebeef5;
}

.search-bar {
  display: flex;
  align-items: center;
}

.action-bar {
  display: flex;
  gap: 10px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.expense-stats {
  display: flex;
  gap: 15px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 5px;
  color: #606266;
  font-size: 13px;
}

.signature-uploader {
  border: 1px dashed #d9d9d9;
  border-radius: 6px;
  cursor: pointer;
  position: relative;
  overflow: hidden;
  width: 200px;
  height: 100px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.signature-uploader:hover {
  border-color: #409EFF;
}

.signature-uploader-icon {
  font-size: 28px;
  color: #8c939d;
}

.signature-preview {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.upload-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 7px;
}
</style>
