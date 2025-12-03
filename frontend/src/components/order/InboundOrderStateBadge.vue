<template>
  <q-badge
    :icon="INBOUND_ORDER_STATES[state]?.icon"
    :color="INBOUND_ORDER_STATES[state]?.color"
    class="text-xs"
  >
    <q-icon :name="INBOUND_ORDER_STATES[state]?.icon" class="mr-1"></q-icon>
    {{ INBOUND_ORDER_STATES[state]?.label }}
  </q-badge>
</template>

<script setup lang="ts">
import { INBOUND_ORDER_STATES } from '@/constants/inbound-order'

defineProps<{ state: string }>()
</script>
