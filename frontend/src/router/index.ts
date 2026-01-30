import { useAuth } from '@/composables/use-auth'
import { useGlobalLoading } from '@/composables/use-global-loading'
import CustomersView from '@/views/CustomersView.vue'
import CustomerView from '@/views/CustomerView.vue'
import HomeView from '@/views/HomeView.vue'
import IncomingOrdersView from '@/views/IncomingOrdersView.vue'
import IncomingOrderView from '@/views/IncomingOrderView.vue'
import LoginView from '@/views/LoginView.vue'
import ProductsView from '@/views/ProductsView.vue'
import ProductView from '@/views/ProductView.vue'
import SettingsView from '@/views/SettingsView.vue'
import WarehouseInboundOrdersView from '@/views/WarehouseInboundOrdersView.vue'
import WarehouseInboundOrderView from '@/views/WarehouseInboundOrderView.vue'
import WarehouseView from '@/views/WarehouseView.vue'
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/warehouse/inbound-orders/:code',
      name: 'warehouseInboundOrderDetail',
      component: WarehouseInboundOrderView,
      props: true,
    },
    {
      path: '/warehouse/inbound-orders',
      name: 'warehouseInboundOrders',
      component: WarehouseInboundOrdersView,
    },
    {
      path: '/warehouses',
      name: 'warehouses',
      component: WarehouseView,
    },
    {
      path: '/products/:productCode',
      name: 'productDetail',
      component: ProductView,
      props: true,
    },
    {
      path: '/products',
      name: 'products',
      component: ProductsView,
    },
    {
      path: '/customers',
      name: 'customers',
      component: CustomersView,
    },
    {
      path: '/customers/:customerCode',
      name: 'customerDetail',
      component: CustomerView,
      props: true,
    },
    {
      path: '/incoming-orders',
      name: 'incomingOrders',
      component: IncomingOrdersView,
    },
    {
      path: '/incoming-orders/:code',
      name: 'incomingOrderDetail',
      component: IncomingOrderView,
      props: true,
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView,
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: {
        disableLayout: true,
      },
    },
  ],
})

router.beforeEach(async (to, from, next) => {
  if (to.name === 'login') {
    next()
    return
  }

  const { isLoading } = useGlobalLoading()
  const { whoami, loginVerified } = useAuth()

  if (loginVerified.value) {
    next()
    return
  }

  try {
    isLoading.value = true
    const user = await whoami()
    if (user) {
      next()
    } else {
      next({ name: 'login' })
    }
  } catch {
    next({ name: 'login' })
  } finally {
    isLoading.value = false
  }
})

export default router
