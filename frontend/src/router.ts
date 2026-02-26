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
import UserManagement from '@/views/UserManagement.vue'
import UserLogin from '@/views/UserLogin.vue'
import UserLayout from '@/views/UserLayout.vue'
import UserDashboard from '@/views/UserDashboard.vue'
import UserUpload from '@/views/UserUpload.vue'
import UserInvoices from '@/views/UserInvoices.vue'
import UserInvoiceDetail from '@/views/UserInvoiceDetail.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false, userType: 'admin' }
  },
  {
    path: '/user/login',
    name: 'UserLogin',
    component: UserLogin,
    meta: { requiresAuth: false, userType: 'user' }
  },
  {
    path: '/',
    component: Layout,
    meta: { requiresAuth: true, userType: 'admin' },
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
      },
      {
        path: 'users',
        name: 'UserManagement',
        component: UserManagement,
        meta: { title: '用户管理', requiresAdmin: true }
      }
    ]
  },
  {
    path: '/user',
    component: UserLayout,
    meta: { requiresAuth: true, userType: 'user' },
    children: [
      {
        path: '',
        name: 'UserDashboard',
        component: UserDashboard
      },
      {
        path: 'upload',
        name: 'UserUpload',
        component: UserUpload
      },
      {
        path: 'invoices',
        name: 'UserInvoices',
        component: UserInvoices
      },
      {
        path: 'invoices/:id',
        name: 'UserInvoiceDetail',
        component: UserInvoiceDetail
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const auditorId = localStorage.getItem('auditor_id')
  const auditorRole = localStorage.getItem('auditor_role')
  const userId = localStorage.getItem('user_id')
  
  const userType = to.meta.userType as string
  
  if (userType === 'admin') {
    if (to.meta.requiresAuth !== false && !auditorId) {
      next('/user/login')
      return
    }
    
    if (to.path === '/login' && auditorId) {
      next('/')
      return
    }
    
    if (to.meta.requiresAdmin && auditorRole !== 'admin') {
      next('/')
      return
    }
  }
  
  if (userType === 'user') {
    if (to.meta.requiresAuth !== false && !userId) {
      next('/user/login')
      return
    }
    
    if (to.path === '/user/login' && userId) {
      next('/user')
      return
    }
    
    if (auditorId) {
      next('/')
      return
    }
  }
  
  next()
})

export default router