<template>
  <div class="flex-1">
    <LargeTabs
      v-model:tab="activeTabKey"
      :items="[
        { key: 'inbound', icon: 'sym_o_call_received', title: 'Vydané Objednávky' },
        { key: 'outbound', icon: 'sym_o_call_made', title: 'Objednávky' },
      ]"
      class="mb-5"
    />
    <component :is="activeTab" />
  </div>
</template>

<script setup lang="ts">
import LargeTabs from '@/components/LargeTabs.vue'
import InboundOrdersView from '@/components/order/InboundOrdersView.vue'
import OutboundOrdersView from '@/components/order/OutboundOrdersView.vue'
import { useLocalStorage } from '@vueuse/core'
import { type Component, shallowRef, watch } from 'vue'

const activeTabKey = useLocalStorage('selected-orders-tab', 'inbound')
const activeTab = shallowRef<Component>(InboundOrdersView)

watch(
  activeTabKey,
  (value) => {
    if (value === 'inbound') {
      activeTab.value = InboundOrdersView
    } else {
      activeTab.value = OutboundOrdersView
    }
  },
  { immediate: true },
)
</script>

<style lang="scss" scoped></style>
