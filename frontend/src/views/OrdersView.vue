<template>
  <div class="flex-1">
    <LargeTabs
      v-model:tab="activeTabKey"
      :items="[
        { key: 'outbound', icon: 'sym_o_call_made', title: 'Přijaté Objednávky' },
        { key: 'inbound', icon: 'sym_o_call_received', title: 'Vydané Objednávky' },
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

const activeTab = shallowRef<Component>(InboundOrdersView)

watch(
  activeTabKey,
  (value) => {
    if (route.query.tab !== value) {
      router.replace({ query: { ...route.query, tab: value } })
    }

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
