<template>
  <div class="flex flex-col text-xs gap-0.5" data-test="item-margin-summary">
    <span class="text-gray-5">
      Skladová hodnota: {{ purchaseValue.toFixed(2) }} {{ currency }}
    </span>
    <span>Marže: <MarginText :margin="margin" :currency="currency" /></span>
  </div>
</template>

<script setup lang="ts">
import { calculateMargin } from '@/utils/margin'
import { computed } from 'vue'
import MarginText from './MarginText.vue'

const props = defineProps<{
  currency: string
  amount: number
  purchasePrice: number
  totalPrice: number
}>()

const purchaseValue = computed(() => props.amount * props.purchasePrice)
const margin = computed(() => calculateMargin(props.totalPrice, purchaseValue.value))
</script>
