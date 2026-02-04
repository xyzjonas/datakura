<template>
  <span class="text-lg mr-1">{{ amount ?? item.amount }}</span>
  <span class="text-gray-5 text-xs border-solid border-1 rounded px-[4px] py-[1px]">{{
    item.unit_of_measure
  }}</span>
</template>

<script setup lang="ts">
import type { WarehouseItemSchema } from '@/client'

defineProps<{
  item: Pick<WarehouseItemSchema, 'amount' | 'unit_of_measure'>
  amount?: number
}>()
</script>

<style lang="scss" scoped></style>
