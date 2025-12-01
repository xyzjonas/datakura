<template>
  <div class="flex flex-col items-end">
    <span class="text-gray-5"> Celková cena </span>
    <span class="flex items-baseline gap-1">
      <h2 class="text-bold text-3xl">{{ totalPrice.toFixed(2) }}</h2>
      <span class="text-gray-5">{{ order.currency }}</span>
    </span>
  </div>
</template>

<script setup lang="ts">
import type { IncomingOrderSchema } from '@/client'
import { computed } from 'vue'

const props = defineProps<{ order: IncomingOrderSchema }>()
const totalPrice = computed(() => {
  if (!props.order) {
    return 0
  }
  return (props.order.items ?? []).reduce((sum, item) => sum + item.amount * item.unit_price, 0)
})
</script>

<style lang="scss" scoped></style>
