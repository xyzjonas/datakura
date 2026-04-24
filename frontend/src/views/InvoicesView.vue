<template>
  <div class="flex-1">
    <LargeTabs
      v-model:tab="activeTabKey"
      :items="[
        { key: 'outbound', icon: 'sym_o_call_made', title: 'Vydané Faktury' },
        { key: 'inbound', icon: 'sym_o_call_received', title: 'Přijaté Faktury' },
      ]"
      class="mb-5"
    />
    <component :is="activeTab" />
  </div>
</template>

<script setup lang="ts">
import InboundInvoicesView from '@/components/invoice/InboundInvoicesView.vue'
import OutboundInvoicesView from '@/components/invoice/OutboundInvoicesView.vue'
import LargeTabs from '@/components/LargeTabs.vue'
import { computed, type Component, shallowRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const validTabs = new Set(['inbound', 'outbound'])

const activeTabKey = computed<string>({
  get() {
    const raw = route.query.tab
    if (typeof raw === 'string' && validTabs.has(raw)) {
      return raw
    }

    return 'outbound'
  },
  set(value: string) {
    const query = { ...route.query, tab: value }
    router.push({ query })
  },
})

const activeTab = shallowRef<Component>(OutboundInvoicesView)

watch(
  activeTabKey,
  (value) => {
    if (route.query.tab !== value) {
      router.replace({ query: { ...route.query, tab: value } })
    }

    if (value === 'inbound') {
      activeTab.value = InboundInvoicesView
    } else {
      activeTab.value = OutboundInvoicesView
    }
  },
  { immediate: true },
)
</script>
