<template>
  <div class="flex flex-col items-end">
    <span class="text-gray-5"> Celková cena </span>
    <span :class="['flex', 'items-baseline', 'gap-1', negative ? 'text-positive' : '']">
      <h2 class="text-bold text-3xl">{{ negative ? '-' : '' }}{{ formattedTotalPrice }}</h2>
      <span class="text-gray-5">{{ order.currency }}</span>
    </span>
    <div v-if="orderMargin" class="flex flex-col items-end text-sm" data-test="order-margin">
      <span class="text-gray-5">
        Hodnota ve skladové ceně: {{ formattedPurchaseValue }}
        {{ order.currency }}
      </span>
      <span>Marže: <MarginText :margin="orderMargin" :currency="order.currency" /></span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useOrderTotals, type OrderTotalsSource } from '@/composables/use-order-totals'
import MarginText from './MarginText.vue'

type Props = {
  negative?: boolean
  order: OrderTotalsSource
}

const props = defineProps<Props>()
const { formattedTotalPrice, formattedPurchaseValue, orderMargin } = useOrderTotals(
  () => props.order,
)
</script>
