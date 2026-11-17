<template>
  <div class="flex flex-col text-xs gap-0.5" data-test="item-margin-summary">
    <span class="text-gray-5">
      Skladová hodnota: {{ purchaseValue.toFixed(2) }} {{ currency }}
    </span>
    <span>Marže: <MarginPercent :margin="margin" :danger="belowMinimum" /></span>
    <span>Přirážka: <MarginPercent :margin="margin" markup :danger="belowMinimum" /></span>
    <span>Zisk: <MarginText :margin="margin" :currency="currency" :danger="belowMinimum" /></span>
  </div>
</template>

<script setup lang="ts">
import { useMinimumProfit } from '@/composables/use-minimum-profit'
import { calculateMargin } from '@/utils/margin'
import { isBelowMinimumProfit } from '@/utils/minimum-profit'
import { computed } from 'vue'
import MarginPercent from './MarginPercent.vue'
import MarginText from './MarginText.vue'

const props = defineProps<{
  currency: string
  amount: number
  purchasePrice: number
  totalPrice: number
}>()

const purchaseValue = computed(() => props.amount * props.purchasePrice)
const margin = computed(() => calculateMargin(props.totalPrice, purchaseValue.value))
const { minimumMarkupPercent } = useMinimumProfit()
const belowMinimum = computed(() =>
  isBelowMinimumProfit(props.totalPrice, purchaseValue.value, minimumMarkupPercent.value),
)
</script>
