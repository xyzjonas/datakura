<template>
  <CountryBadge v-if="country" :code="country" :tooltip="tooltip" />
  <q-badge v-else-if="missing" color="negative" outline data-test="missing-origin-country">
    <q-icon name="sym_o_public_off" class="mr-1" size="14px" />
    chybí země původu
  </q-badge>
</template>

<script setup lang="ts">
import CountryBadge from './CountryBadge.vue'

/** Country badge, or a warning when the country is required but missing. */
withDefaults(
  defineProps<{
    country?: string | null
    missing?: boolean
    tooltip?: string
  }>(),
  { country: null, missing: false, tooltip: undefined },
)
</script>
