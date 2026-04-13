<template>
  <div>
    <h1 class="mb-5">ZÁKAZNÍCI</h1>
    <LargeTabs
      v-model:tab="activeTab"
      :items="[{ key: 'groups', icon: 'sym_o_groups', title: 'Skupiny zákazníků' }]"
      class="mb-5"
    />
    <component :is="activeTabComponent" />
  </div>
</template>

<script setup lang="ts">
import LargeTabs from '@/components/LargeTabs.vue'
import { useLocalStorage } from '@vueuse/core'
import { shallowRef, type Component, watch } from 'vue'
import CustomerGroupsTable from '@/components/settings/customer/CustomerGroupsTable.vue'

const activeTab = useLocalStorage('settings-customer-tab', 'groups')
const activeTabComponent = shallowRef<Component>(CustomerGroupsTable)

watch(
  activeTab,
  (value: string) => {
    if (value === 'groups') {
      activeTabComponent.value = CustomerGroupsTable
    }
  },
  { immediate: true },
)
</script>

<style lang="scss" scoped></style>
