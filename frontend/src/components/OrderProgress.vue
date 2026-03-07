<template>
  <q-linear-progress :size="props.height" :value="value" color="primary" rounded class="bg-gray-3">
    <div class="absolute-full flex items-center justify-center">
      <span class="text-light text-xs font-bold">{{ `${(value * 100).toFixed(0)}%` }}</span>
    </div>
  </q-linear-progress>
</template>

<script setup lang="ts">
import type { InboundWarehouseOrderSchema } from '@/client'
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    order: Pick<InboundWarehouseOrderSchema, 'remaining_amount' | 'total_amount'>
    height?: string
  }>(),
  { height: '24px' },
)

const value = computed(() => {
  if (props.order.total_amount === 0) {
    return 1
  }
  return 1 - props.order.remaining_amount / props.order.total_amount
})
</script>

<style lang="scss" scoped></style>
