<template>
  <q-badge :color="config?.color" class="text-xs">
    <q-icon :name="config?.icon" class="mr-1"></q-icon>
    {{ config?.label }}
  </q-badge>
</template>

<script setup lang="ts">
import { OUTBOUND_CALCULATION_STATES, OUTBOUND_ORDER_STATES } from '@/constants/outbound-order'
import { computed } from 'vue'

const props = defineProps<{ state: string }>()

// serves both orders and calculations (their state names never overlap)
const config = computed(
  () => OUTBOUND_ORDER_STATES[props.state] ?? OUTBOUND_CALCULATION_STATES[props.state],
)
</script>
