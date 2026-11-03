<template>
  <div v-if="batch" class="flex items-center gap-1 flex-wrap" data-test="item-batch">
    <BatchBadge :batch-code="batch.primary_barcode?.code ?? `#${batch.id}`" />
    <CertificationBadge
      link
      :requires-certification="!!batch.certification"
      :certification="batch.certification"
    />
  </div>
  <span v-else class="text-gray-5">-</span>
</template>

<script setup lang="ts">
import type { BatchSchema } from '@/client'
import CertificationBadge from '../certification/CertificationBadge.vue'
import BatchBadge from './BatchBadge.vue'

defineProps<{ batch?: BatchSchema | null }>()
</script>
