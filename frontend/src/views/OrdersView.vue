<template>
  <div class="flex-1">
    <div class="flex gap-2 mb-8">
      <ForegroundPanel
        class="flex-1"
        @click="activeTabKey = 'inbound'"
        :active="activeTabKey === 'inbound'"
        clickable
      >
        <div class="flex items-center gap-5">
          <q-icon name="sym_o_call_received" size="24px"></q-icon>
          <div>
            <h2 class="">12</h2>
            <h5 class="font-bold uppercase">Vydaných Objednávek</h5>
          </div>
        </div>
      </ForegroundPanel>
      <ForegroundPanel
        class="flex-1"
        @click="activeTabKey = 'outbound'"
        :active="activeTabKey === 'outbound'"
        clickable
      >
        <div class="flex items-center gap-5">
          <q-icon name="sym_o_call_made" size="24px"></q-icon>
          <div>
            <h2 class="">0</h2>
            <h5 class="font-bold uppercase">Objednávek</h5>
          </div>
        </div>
      </ForegroundPanel>
    </div>
    <component :is="activeTab" />
  </div>
</template>

<script setup lang="ts">
import ForegroundPanel from '@/components/ForegroundPanel.vue'
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
