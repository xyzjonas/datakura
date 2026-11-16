<template>
  <div class="flex items-center gap-2 flex-wrap justify-between" data-test="item-requirements">
    <q-btn
      flat
      dense
      no-caps
      color="primary"
      icon="sym_o_tune"
      label="specifikovat typ zboží"
      :disable="!productCode"
      data-test="specify-requirements"
      @click="dialog = true"
    />
    <div class="flex items-center gap-1">
      <PackageTypeBadge v-if="packageTypeName" :package-type="packageTypeName" />
      <BatchBadge v-if="batchCode" :batch-code="batchCode" />
      <CountryBadge v-if="originCountry" :code="originCountry" tooltip="Požadovaná země původu" />
      <span v-if="!packageTypeName && !batchCode && !originCountry" class="text-muted text-xs"
        >Bez požadavku</span
      >
    </div>
  </div>

  <OutboundOrderItemRequirementsDialog
    v-model:show="dialog"
    :product-name="productName"
    :product-code="productCode"
    :desired-package-type-name="packageTypeName"
    :desired-batch-code="batchCode"
    :required-origin-country="originCountry"
    @save="onSave"
  />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import CountryBadge from '../CountryBadge.vue'
import PackageTypeBadge from '../PackageTypeBadge.vue'
import BatchBadge from '../warehouse/BatchBadge.vue'
import OutboundOrderItemRequirementsDialog from './OutboundOrderItemRequirementsDialog.vue'

defineProps<{
  productName: string
  productCode: string
}>()

const packageTypeName = defineModel<string | null | undefined>('packageTypeName')
const batchCode = defineModel<string | null | undefined>('batchCode')
const originCountry = defineModel<string | null | undefined>('originCountry')

/** Fired after the models were updated - lets the parent persist the change. */
const emit = defineEmits<{ (e: 'save'): void }>()

const dialog = ref(false)

const onSave = (payload: {
  desired_package_type_name: string | null
  desired_batch_code: string | null
  required_origin_country?: string | null
}) => {
  packageTypeName.value = payload.desired_package_type_name
  batchCode.value = payload.desired_batch_code
  originCountry.value = payload.required_origin_country ?? null
  emit('save')
}
</script>
