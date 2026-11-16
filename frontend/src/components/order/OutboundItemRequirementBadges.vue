<template>
  <div v-if="hasAny" class="flex flex-wrap items-center gap-1" data-test="requirement-badges">
    <PackageTypeBadge v-if="packageType" :package-type="packageType" />
    <BatchBadge v-if="batchCode" :batch-code="batchCode" />
    <OriginCountryMarker
      :country="originCountry"
      :missing="missingCountry"
      tooltip="Požadovaná země původu"
    />
  </div>
</template>

<script setup lang="ts">
import { useRequiresOriginCountry } from '@/composables/use-outbound-document-api'
import { computed } from 'vue'
import OriginCountryMarker from '../OriginCountryMarker.vue'
import PackageTypeBadge from '../PackageTypeBadge.vue'
import BatchBadge from '../warehouse/BatchBadge.vue'

/** All goods requirements of an outbound item as badges (+ a warning for a missing country). */
const props = defineProps<{
  packageType?: string | null
  batchCode?: string | null
  originCountry?: string | null
}>()

const requiresCountry = useRequiresOriginCountry()
const missingCountry = computed(() => requiresCountry.value && !props.originCountry)
const hasAny = computed(
  () => !!(props.packageType || props.batchCode || props.originCountry || missingCountry.value),
)
</script>
