<template>
  <span :class="['font-medium', margin.amount >= 0 ? 'text-green-600' : 'text-red']">
    {{ markup ? formatMarkupPercent(margin) : formatMarginPercent(margin) }}
  </span>
</template>

<script setup lang="ts">
import { formatMarginPercent, formatMarkupPercent, type Margin } from '@/utils/margin'

/** Shows marže (% of selling price) by default, přirážka (% on top of purchase price) with `markup`. */
defineProps<{
  margin: Margin
  markup?: boolean
}>()
</script>
