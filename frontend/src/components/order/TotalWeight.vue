<template>
  <div>
    <q-chip icon="sym_o_weight" :label="`${formattedWeight} g`" />
  </div>
</template>

<script setup lang="ts">
import type { InboundOrderSchema, OutboundOrderSchema } from '@/client'
import { computed } from 'vue'

const props = defineProps<{ order: InboundOrderSchema | OutboundOrderSchema }>()
const totalWeight = computed(() => {
  return (props.order.items ?? []).reduce(
    (sum, item) => sum + item.amount * (item.product.unit_weight ?? 0),
    0,
  )
})
const formattedWeight = computed(() => {
  // Avoid binary float rounding errors (e.g. 3 * 0.575 = 1.7249... → "1.72" instead of "1.73")
  return (Math.round((totalWeight.value + Number.EPSILON) * 100) / 100).toFixed(2)
})
</script>

<style lang="scss" scoped></style>
