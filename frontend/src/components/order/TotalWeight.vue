<template>
  <div>
    <q-chip icon="sym_o_weight" :label="`${totalWeight.toFixed(2)}&thinsp;g`" />
  </div>
</template>

<script setup lang="ts">
import type { InboundOrderSchema } from '@/client'
import { computed } from 'vue'

const props = defineProps<{ order: InboundOrderSchema }>()
const totalWeight = computed(() => {
  return (props.order.items ?? []).reduce(
    (sum, item) => sum + item.amount * item.product.unit_weight,
    0,
  )
})
</script>

<style lang="scss" scoped></style>
