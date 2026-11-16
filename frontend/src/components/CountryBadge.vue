<template>
  <q-badge v-if="code" color="primary" data-test="country-badge">
    <span class="mr-1">{{ countryFlag(code) }}</span>
    {{ countryName(code) }}
    <q-tooltip>{{ tooltip }}</q-tooltip>
  </q-badge>
</template>

<script setup lang="ts">
import { countryFlag, countryName } from '@/utils/countries'

withDefaults(defineProps<{ code?: string | null; tooltip?: string }>(), {
  code: null,
  tooltip: 'Země původu',
})
</script>
