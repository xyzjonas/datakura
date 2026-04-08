<template>
  <q-badge
    :icon="OUTBOUND_WAREHOUSE_ORDER_STATES[state]?.icon"
    :color="OUTBOUND_WAREHOUSE_ORDER_STATES[state]?.color"
    class="text-xs"
  >
    <q-icon :name="OUTBOUND_WAREHOUSE_ORDER_STATES[state]?.icon" class="mr-1"></q-icon>
    {{ OUTBOUND_WAREHOUSE_ORDER_STATES[state]?.label ?? state }}
  </q-badge>
</template>

<script setup lang="ts">
import { OUTBOUND_WAREHOUSE_ORDER_STATES } from '@/constants/outbound-warehouse-order'

defineProps<{ state: string }>()
</script>
