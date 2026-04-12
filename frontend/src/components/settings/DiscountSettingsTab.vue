<template>
  <div>
    <h1 class="mb-5">SLEVOVÉ SKUPINY</h1>
    <LargeTabs
      v-model:tab="activeTab"
      :items="[{ key: 'groups', icon: 'sym_o_percent', title: 'Slevové skupiny' }]"
      class="mb-5"
    />
    <component :is="activeTabComponent" />
  </div>
</template>

<script setup lang="ts">
import LargeTabs from '@/components/LargeTabs.vue'
import DiscountGroupsTable from '@/components/settings/discount/DiscountGroupsTable.vue'
import { useLocalStorage } from '@vueuse/core'
import { shallowRef, type Component, watch } from 'vue'

const activeTab = useLocalStorage('settings-discounts-tab', 'groups')
const activeTabComponent = shallowRef<Component>(DiscountGroupsTable)

watch(
  activeTab,
  (value: string) => {
    if (value === 'groups') {
      activeTabComponent.value = DiscountGroupsTable
    }
  },
  { immediate: true },
)
</script>
