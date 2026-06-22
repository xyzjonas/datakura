<template>
  <q-badge
    :icon="MANUFACTURING_ORDER_STATES[state]?.icon"
    :color="MANUFACTURING_ORDER_STATES[state]?.color"
    class="text-xs"
  >
    <q-icon :name="MANUFACTURING_ORDER_STATES[state]?.icon" class="mr-1"></q-icon>
    {{ MANUFACTURING_ORDER_STATES[state]?.label }}
  </q-badge>
</template>

<script setup lang="ts">
import { MANUFACTURING_ORDER_STATES } from '@/constants/manufacturing-order'

defineProps<{ state: string }>()
</script>
