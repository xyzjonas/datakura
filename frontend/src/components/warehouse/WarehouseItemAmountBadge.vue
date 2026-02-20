<template>
  <span class="text-lg mr-2">{{ amount ?? item.amount }}</span>
  <span
    class="light:text-gray-5 dark:text-gray-3 text-xs border-solid light:border-gray-3 dark:border-gray-5 border-1 rounded px-[4px] py-[1px]"
    >{{ item.unit_of_measure }}</span
  >
</template>

<script setup lang="ts">
import type { WarehouseItemSchema } from '@/client'

defineProps<{
  item: Pick<WarehouseItemSchema, 'amount' | 'unit_of_measure'>
  amount?: number
}>()
</script>

<style lang="scss" scoped></style>
