import CustomersView from '@/views/CustomersView.vue'
import CustomerView from '@/views/CustomerView.vue'
import HomeView from '@/views/HomeView.vue'
import IncomingOrdersView from '@/views/IncomingOrdersView.vue'
import IncomingOrderView from '@/views/IncomingOrderView.vue'
import ProductsView from '@/views/ProductsView.vue'
import ProductView from '@/views/ProductView.vue'
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
      path: '/warehouse',
      name: 'warehouse',
      component: WarehouseView,
    },
    {
      path: '/products',
      name: 'products',
      component: ProductsView,
    },
    {
      path: '/products/:productCode',
      name: 'productDetail',
      component: ProductView,
      props: true,
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
  ],
})

export default router
