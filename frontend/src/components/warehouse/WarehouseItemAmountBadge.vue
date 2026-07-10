<template>
  <div class="flex items-center">
    <span class="text-lg mr-2">{{ amount ?? item.amount }}</span>
    <q-badge rounded color="gray">{{ item.unit_of_measure }}</q-badge>
  </div>
</template>

<script setup lang="ts">
import type { WarehouseItemSchema } from '@/client'

defineProps<{
  item: Pick<WarehouseItemSchema, 'amount' | 'unit_of_measure'>
  amount?: number
}>()
</script>

<style lang="scss" scoped></style>
