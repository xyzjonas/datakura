<template>
  <span :class="['font-medium', margin.amount >= 0 ? 'text-green-600' : 'text-red']">
    {{ formatMargin(margin) }}<template v-if="currency"> {{ currency }}</template>
  </span>
</template>

<script setup lang="ts">
import { formatMargin, type Margin } from '@/utils/margin'

defineProps<{
  margin: Margin
  currency?: string
}>()
</script>
