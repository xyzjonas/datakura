<template>
  <div v-if="hasRequirements" class="flex flex-wrap gap-1 items-center">
    <PackageTypeBadge
      v-if="item.desired_package_type_name"
      :package-type="item.desired_package_type_name"
    />
    <BatchCertificationBadges
      v-if="item.desired_batch_code"
      :batch-code="item.desired_batch_code"
      :certification="item.desired_batch_certification"
    />
    <CountryBadge
      v-if="item.required_origin_country"
      :code="item.required_origin_country"
      tooltip="Požadovaná země původu"
    />
  </div>
</template>

<script setup lang="ts">
import type { ManufacturingOrderItemSchema } from '@/client'
import CountryBadge from '@/components/CountryBadge.vue'
import PackageTypeBadge from '@/components/PackageTypeBadge.vue'
import BatchCertificationBadges from '@/components/warehouse/BatchCertificationBadges.vue'
import { computed } from 'vue'

const props = defineProps<{ item: ManufacturingOrderItemSchema }>()

const hasRequirements = computed(
  () =>
    !!props.item.desired_package_type_name ||
    !!props.item.desired_batch_code ||
    !!props.item.required_origin_country,
)
</script>
