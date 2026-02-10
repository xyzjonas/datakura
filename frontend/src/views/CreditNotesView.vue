<template>
  <div class="flex-1">
    <div class="flex gap-2 mb-8">
      <ForegroundPanel
        class="flex-1"
        @click="activeTabKey = 'inbound'"
        :active="activeTabKey === 'inbound'"
        clickable
      >
        <q-icon name="sym_o_call_received" size="24px"></q-icon>
        <div>
          <h5 class="font-bold uppercase">Vydané Dobropisy</h5>
        </div>
      </ForegroundPanel>
      <ForegroundPanel
        class="flex-1"
        @click="activeTabKey = 'outbound'"
        :active="activeTabKey === 'outbound'"
        clickable
      >
        <q-icon name="sym_o_call_made" size="24px"></q-icon>
        <div>
          <h5 class="font-bold uppercase">Dobropisy</h5>
        </div>
      </ForegroundPanel>
    </div>
    <component :is="activeTab" />
  </div>
</template>

<script setup lang="ts">
import CreditNotesToSupplierView from '@/components/credit/CreditNotesToSupplierView.vue'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import InboundOrdersView from '@/components/order/InboundOrdersView.vue'
import OutboundOrdersView from '@/components/order/OutboundOrdersView.vue'
import { useLocalStorage } from '@vueuse/core'
import { type Component, shallowRef, watch } from 'vue'

const activeTabKey = useLocalStorage('selected-credit-notes-tab', 'inbound')
const activeTab = shallowRef<Component>(InboundOrdersView)

watch(
  activeTabKey,
  (value) => {
    if (value === 'inbound') {
      activeTab.value = CreditNotesToSupplierView
    } else {
      activeTab.value = OutboundOrdersView
    }
  },
  { immediate: true },
)
</script>

<style lang="scss" scoped></style>
