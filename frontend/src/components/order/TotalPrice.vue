<template>
  <div class="flex flex-col items-end">
    <span class="text-gray-5"> Celková cena </span>
    <span :class="['flex', 'items-baseline', 'gap-1', negative ? 'text-positive' : '']">
      <h2 class="text-bold text-3xl">{{ negative ? '-' : '' }}{{ formatNumber(totalPrice) }}</h2>
      <span class="text-gray-5">{{ order.currency }}</span>
    </span>
  </div>
</template>

<script setup lang="ts">
import { formatNumber } from '@/utils/format-number'
import { computed } from 'vue'

type Props = {
  negative?: boolean
  order: {
    currency: string
    items?: {
      amount: number
      unit_price: number
    }[]
  }
}

//  & Record<string, unknown>

const props = defineProps<Props>()
const totalPrice = computed(() => {
  if (!props.order) {
    return 0
  }
  return (props.order.items ?? []).reduce((sum, item) => sum + item.amount * item.unit_price, 0)
})
</script>

<style lang="scss" scoped></style>
