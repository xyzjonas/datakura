<template>
  <div class="flex flex-1 gap-5">
    <div class="flex flex-col h-full min-w-xs">
      <q-scroll-area class="flex-1 p-2">
        <h1 class="mb-5 text-lg">NASTAVENÍ</h1>
        <q-list class="flex flex-col gap-1">
          <q-item
            v-for="item in items"
            :key="item.key"
            clickable
            v-ripple
            :active="item.key === selectedTab"
            active-class="bg-primary text-light"
            :class="{ 'rounded-md': true, uppercase: true }"
            dense
            @click="selectedTab = item.key"
          >
            <q-item-section avatar>
              <q-icon :name="item.icon" />
            </q-item-section>
            <q-item-section> {{ item.label }} </q-item-section>
          </q-item>
        </q-list>
      </q-scroll-area>
    </div>
    <q-separator vertical />
    <div class="flex-1">
      <Suspense>
        <component :is="selectedTabComponent" />
        <template #fallback>
          <div>...loading inner</div>
        </template>
      </Suspense>
    </div>
  </div>
</template>

<script setup lang="ts">
import MissingSettingsTab from '@/components/settings/MissingSettingsTab.vue'
import CustomerSettingsTab from '@/components/settings/CustomerSettingsTab.vue'
import DiscountSettingsTab from '@/components/settings/DiscountSettingsTab.vue'
import PackagingSettingsTab from '@/components/settings/PackagingSettingsTab.vue'
import PaymentSettingsTab from '@/components/settings/PaymentSettingsTab.vue'
import ProductSettingsTab from '@/components/settings/ProductSettingsTab.vue'
import { computed, shallowRef, watch, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const selectedTabComponent = shallowRef<Component>()

const validTabs = new Set([
  'location',
  'packaging',
  'products',
  'customers',
  'discounts',
  'payments',
  'users',
])

const selectedTab = computed<string>({
  get() {
    const raw = route.query.tab
    if (typeof raw === 'string' && validTabs.has(raw)) {
      return raw
    }
    return 'packaging'
  },
  set(value: string) {
    const query = { ...route.query, tab: value }
    router.push({ query })
  },
})

watch(
  selectedTab,
  (value: string) => {
    if (route.query.tab !== value) {
      router.replace({ query: { ...route.query, tab: value } })
    }

    if (value === 'packaging') {
      selectedTabComponent.value = PackagingSettingsTab
    } else if (value === 'products') {
      selectedTabComponent.value = ProductSettingsTab
    } else if (value === 'customers') {
      selectedTabComponent.value = CustomerSettingsTab
    } else if (value === 'discounts') {
      selectedTabComponent.value = DiscountSettingsTab
    } else if (value === 'payments') {
      selectedTabComponent.value = PaymentSettingsTab
    } else {
      selectedTabComponent.value = MissingSettingsTab
    }
  },
  { immediate: true },
)

const items = [
  {
    key: 'location',
    label: 'Lokace a skladová místa',
    icon: 'sym_o_home_work',
  },
  {
    key: 'packaging',
    label: 'balení',
    icon: 'sym_o_package_2',
  },
  {
    key: 'products',
    label: 'produkty',
    icon: 'sym_o_shopping_cart',
  },
  {
    key: 'customers',
    label: 'zákazníci',
    icon: 'sym_o_groups',
  },
  {
    key: 'discounts',
    label: 'slevové skupiny',
    icon: 'sym_o_percent',
  },
  {
    key: 'payments',
    label: 'platby',
    icon: 'sym_o_payments',
  },
  {
    key: 'users',
    label: 'uživatelé',
    icon: 'sym_o_group',
  },
]
</script>

<style lang="scss" scoped></style>
