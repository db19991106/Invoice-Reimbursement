<template>
  <div class="invoices-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>我的发票</span>
          <el-button type="primary" @click="$router.push('/user/upload')">
            <el-icon><Upload /></el-icon>
            上传发票
          </el-button>
        </div>
      </template>
      
      <el-form :inline="true" :model="queryForm" class="search-form">
        <el-form-item label="状态">
          <el-select v-model="queryForm.status" placeholder="全部" clearable>
            <el-option label="待审核" value="pending" />
            <el-option label="处理中" value="processing" />
            <el-option label="已通过" value="approve" />
            <el-option label="已驳回" value="reject" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchInvoices">搜索</el-button>
          <el-button @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
      
      <el-table :data="invoices" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="invoice_no" label="发票号码" width="150" />
        <el-table-column prop="invoice_code" label="发票代码" width="130" />
        <el-table-column prop="total_amount" label="金额" width="100">
          <template #default="{ row }">
            ¥{{ row.total_amount?.toFixed(2) || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="seller_name" label="销售方" min-width="150" />
        <el-table-column prop="date" label="开票日期" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="上传时间" width="170">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewDetail(row.id)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        style="margin-top: 20px; justify-content: flex-end"
        @size-change="fetchInvoices"
        @current-change="fetchInvoices"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Upload } from '@element-plus/icons-vue'
import axios from 'axios'

const router = useRouter()
const userId = localStorage.getItem('user_id')

const loading = ref(false)
const invoices = ref([])

const queryForm = reactive({
  status: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const fetchInvoices = async () => {
  loading.value = true
  try {
    const res = await axios.get('/api/user/invoices', {
      params: {
        user_id: userId,
        status: queryForm.status || undefined,
        skip: (pagination.page - 1) * pagination.pageSize,
        limit: pagination.pageSize
      }
    })
    invoices.value = res.data
    pagination.total = res.data.length
  } catch (e) {
    console.error('获取发票列表失败', e)
  } finally {
    loading.value = false
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

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const viewDetail = (id: number) => {
  router.push(`/user/invoices/${id}`)
}

const resetQuery = () => {
  queryForm.status = ''
  pagination.page = 1
  fetchInvoices()
}

onMounted(() => {
  fetchInvoices()
})
</script>

<style scoped>
.invoices-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-form {
  margin-bottom: 20px;
}
</style>
