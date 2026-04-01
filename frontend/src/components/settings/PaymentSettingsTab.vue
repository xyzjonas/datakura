<template>
  <div>
    <h1 class="mb-5">PLATBY</h1>
    <LargeTabs
      v-model:tab="activeTab"
      :items="[{ key: 'methods', icon: 'sym_o_payments', title: 'Platební metody' }]"
      class="mb-5"
    />
    <component :is="activeTabComponent" />
  </div>
</template>

<script setup lang="ts">
import LargeTabs from '@/components/LargeTabs.vue'
import { useLocalStorage } from '@vueuse/core'
import { shallowRef, type Component, watch } from 'vue'
import PaymentMethodsTable from './payment/PaymentMethodsTable.vue'

const activeTab = useLocalStorage('settings-payment-tab', 'methods')
const activeTabComponent = shallowRef<Component>(PaymentMethodsTable)

watch(
  activeTab,
  (value: string) => {
    if (value === 'methods') {
      activeTabComponent.value = PaymentMethodsTable
    }
  },
  { immediate: true },
)
</script>
