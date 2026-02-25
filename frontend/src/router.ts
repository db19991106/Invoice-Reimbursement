import { createRouter, createWebHistory } from 'vue-router'
import Login from '@/views/Login.vue'
import Layout from '@/views/Layout.vue'
import Dashboard from '@/views/AdminDashboard.vue'
import InvoiceList from '@/views/InvoiceList.vue'
import InvoiceDetail from '@/views/InvoiceDetail.vue'
import Upload from '@/views/AdminUpload.vue'
import Statistics from '@/views/Statistics.vue'
import EmployeeManagement from '@/views/EmployeeManagement.vue'
import AuditorManagement from '@/views/AuditorManagement.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: Layout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: Dashboard
      },
      {
        path: 'invoices',
        name: 'InvoiceList',
        component: InvoiceList
      },
      {
        path: 'invoices/:id',
        name: 'InvoiceDetail',
        component: InvoiceDetail
      },
      {
        path: 'upload',
        name: 'Upload',
        component: Upload
      },
      {
        path: 'statistics',
        name: 'Statistics',
        component: Statistics
      },
      {
        path: 'employees',
        name: 'EmployeeManagement',
        component: EmployeeManagement,
        meta: { title: '员工管理' }
      },
      {
        path: 'auditors',
        name: 'AuditorManagement',
        component: AuditorManagement,
        meta: { title: '审核员管理', requiresAdmin: true }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const auditorId = localStorage.getItem('auditor_id')
  const auditorRole = localStorage.getItem('auditor_role')
  
  // 检查是否需要登录
  if (to.meta.requiresAuth !== false && !auditorId) {
    next('/login')
    return
  }
  
  // 已登录不允许访问登录页
  if (to.path === '/login' && auditorId) {
    next('/')
    return
  }
  
  // 检查是否需要管理员权限
  if (to.meta.requiresAdmin && auditorRole !== 'admin') {
    next('/')
    return
  }
  
  next()
})

export default router