<template>
  <q-badge
    :icon="OUTBOUND_ORDER_STATES[state]?.icon"
    :color="OUTBOUND_ORDER_STATES[state]?.color"
    class="text-xs"
  >
    <q-icon :name="OUTBOUND_ORDER_STATES[state]?.icon" class="mr-1"></q-icon>
    {{ OUTBOUND_ORDER_STATES[state]?.label }}
  </q-badge>
</template>

<script setup lang="ts">
import { OUTBOUND_ORDER_STATES } from '@/constants/outbound-order'

defineProps<{ state: string }>()
</script>
