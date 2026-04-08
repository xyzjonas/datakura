import { useAuth } from '@/composables/use-auth'
import { useGlobalLoading } from '@/composables/use-global-loading'
import CreditNotesView from '@/views/CreditNotesView.vue'
import CreditNoteToSupplierView from '@/views/CreditNoteToSupplierView.vue'
import CustomersView from '@/views/CustomersView.vue'
import CustomerView from '@/views/CustomerView.vue'
import GroupsView from '@/views/GroupsView.vue'
import HomeView from '@/views/HomeView.vue'
import InboundOrderView from '@/views/InboundOrderView.vue'
import OutboundOrderView from '@/views/OutboundOrderView.vue'
import LoginView from '@/views/LoginView.vue'
import OrdersView from '@/views/OrdersView.vue'
import ProductsView from '@/views/ProductsView.vue'
import ProductView from '@/views/ProductView.vue'
import SettingsView from '@/views/SettingsView.vue'
import WarehouseInboundOrdersView from '@/views/WarehouseInboundOrdersView.vue'
import WarehouseInboundOrderView from '@/views/WarehouseInboundOrderView.vue'
import WarehouseOutboundOrdersView from '@/views/WarehouseOutboundOrdersView.vue'
import WarehouseOutboundOrderView from '@/views/WarehouseOutboundOrderView.vue'
import WarehouseItemView from '@/views/WarehouseItemView.vue'
import WarehouseView from '@/views/WarehouseView.vue'
import { createRouter, createWebHistory } from 'vue-router'
import { useDrawer } from '@/composables/use-drawer'
import { useQuasar } from 'quasar'

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
      path: '/warehouse/outbound-orders',
      name: 'warehouseOutboundOrders',
      component: WarehouseOutboundOrdersView,
    },
    {
      path: '/warehouse/outbound-orders/:code',
      name: 'warehouseOutboundOrderDetail',
      component: WarehouseOutboundOrderView,
      props: true,
    },
    {
      path: '/warehouses',
      name: 'warehouses',
      component: WarehouseView,
    },
    {
      path: '/warehouse/warehouse-items/:itemId',
      name: 'warehouseItemDetail',
      component: WarehouseItemView,
      props: true,
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
      path: '/groups',
      name: 'productGroups',
      component: GroupsView,
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
      path: '/orders',
      name: 'orders',
      component: OrdersView,
    },
    {
      path: '/credit-notes',
      name: 'creditNotes',
      component: CreditNotesView,
    },
    {
      path: '/credit-notes/supplier/:code',
      name: 'creditNoteToSupplier',
      component: CreditNoteToSupplierView,
      props: true,
    },
    {
      path: '/inbound-orders/:code',
      name: 'inboundOrderDetail',
      component: InboundOrderView,
      props: true,
    },
    {
      path: '/outbound-orders/:code',
      name: 'outboundOrderDetail',
      component: OutboundOrderView,
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

router.afterEach(() => {
  const { close } = useDrawer()
  const $q = useQuasar()
  if ($q.screen.lt.md) {
    close()
  }
})

export default router
