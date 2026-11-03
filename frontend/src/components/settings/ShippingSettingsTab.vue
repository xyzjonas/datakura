<template>
  <div>
    <h1 class="mb-5">DOPRAVA</h1>
    <LargeTabs
      v-model:tab="activeTab"
      :items="[{ key: 'types', icon: 'sym_o_local_shipping', title: 'Typy dopravy' }]"
      class="mb-5"
    />
    <component :is="activeTabComponent" />
  </div>
</template>

<script setup lang="ts">
import LargeTabs from '@/components/LargeTabs.vue'
import { useLocalStorage } from '@vueuse/core'
import { shallowRef, type Component, watch } from 'vue'
import ShippingTypesTable from './shipping/ShippingTypesTable.vue'

const activeTab = useLocalStorage('settings-shipping-tab', 'types')
const activeTabComponent = shallowRef<Component>(ShippingTypesTable)

watch(
  activeTab,
  (value: string) => {
    if (value === 'types') {
      activeTabComponent.value = ShippingTypesTable
    }
  },
  { immediate: true },
)
</script>
