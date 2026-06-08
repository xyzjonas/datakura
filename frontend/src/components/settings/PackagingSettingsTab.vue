<template>
  <div>
    <h1 class="mb-5">BALENÍ</h1>
    <LargeTabs
      v-model:tab="activeTab"
      :items="[
        { key: 'packageTypes', icon: 'sym_o_package_2', title: 'Typy Balení' },
        { key: 'batches', icon: 'sym_o_barcode', title: 'Šarže' },
        { key: 'units', icon: 'sym_o_straighten', title: 'Jednotky' },
      ]"
      class="mb-5"
    />
    <component :is="activeTabComponent" />
  </div>
</template>

<script setup lang="ts">
import LargeTabs from '@/components/LargeTabs.vue'
import { useLocalStorage } from '@vueuse/core'
import { shallowRef, type Component, watch } from 'vue'
import BatchesTable from './packaging/BatchesTable.vue'
import PackageTypesTable from './packaging/PackageTypesTable.vue'
import UnitsOfMeasureTable from './packaging/UnitsOfMeasureTable.vue'

const activeTab = useLocalStorage('settings-packaging-tab', 'packageTypes')
const activeTabComponent = shallowRef<Component>(PackageTypesTable)

watch(
  activeTab,
  (value: string) => {
    if (value === 'units') {
      activeTabComponent.value = UnitsOfMeasureTable
    } else if (value === 'batches') {
      activeTabComponent.value = BatchesTable
    } else {
      activeTabComponent.value = PackageTypesTable
    }
  },
  { immediate: true },
)
</script>

<style lang="scss" scoped></style>
