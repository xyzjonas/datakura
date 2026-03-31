<template>
  <div>
    <h1 class="mb-5">PRODUKTY</h1>
    <LargeTabs
      v-model:tab="activeTab"
      :items="[{ key: 'types', icon: 'sym_o_category', title: 'Typy zboží' }]"
      class="mb-5"
    />
    <component :is="activeTabComponent" />
  </div>
</template>

<script setup lang="ts">
import LargeTabs from '@/components/LargeTabs.vue'
import { useLocalStorage } from '@vueuse/core'
import { shallowRef, type Component, watch } from 'vue'
import ProductTypesTable from '@/components/settings/product/ProductTypesTable.vue'

const activeTab = useLocalStorage('settings-product-tab', 'types')
const activeTabComponent = shallowRef<Component>(ProductTypesTable)

watch(
  activeTab,
  (value: string) => {
    if (value === 'types') {
      activeTabComponent.value = ProductTypesTable
    }
  },
  { immediate: true },
)
</script>

<style lang="scss" scoped></style>
