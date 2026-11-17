<template>
  <small v-if="date" class="text-gray-5 text-xs">
    změněno {{ formatDateWithYear(date) }}
    <q-tooltip>{{ formatDateTimeLong(date) }}</q-tooltip>
  </small>
</template>

<script setup lang="ts">
import { formatDateTimeLong, formatDateWithYear } from '@/utils/date'

defineProps<{
  date?: string | null
}>()
</script>
