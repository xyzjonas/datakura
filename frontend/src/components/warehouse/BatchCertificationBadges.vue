<template>
  <span class="inline-flex items-center gap-1 flex-wrap" data-test="batch-certification-badges">
    <BatchBadge :batch-code="batchCode" />
    <CertificationBadge
      v-if="certification"
      link
      requires-certification
      :certification="certification"
    />
  </span>
</template>

<script setup lang="ts">
import CertificationBadge from '../certification/CertificationBadge.vue'
import BatchBadge from './BatchBadge.vue'

/** A batch together with the certification attached to it (if any). */
defineProps<{
  batchCode?: string
  certification?: { id?: number; code: string } | null
}>()
</script>
