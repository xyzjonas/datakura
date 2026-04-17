<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-lg">
      <div class="p-4 flex flex-col gap-4">
        <div class="flex items-start gap-2">
          <div class="flex flex-col">
            <span class="text-2xl uppercase">Požadavek na výdej</span>
            <span class="text-gray-5 text-sm">{{ productName }}</span>
          </div>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>

        <q-form class="flex flex-col gap-3" @submit="submit">
          <q-select
            v-model="mode"
            outlined
            label="Typ požadavku"
            :options="modeOptions"
            emit-value
            map-options
          />

          <PackageTypeSearchSelect v-if="mode === 'package'" v-model="selectedPackage" />

          <q-input
            v-else
            v-model="batchCode"
            outlined
            label="Kód šarže"
            hint="Nechte prázdné pro smazání požadavku na šarži"
          />

          <div class="flex gap-2 justify-end pt-2">
            <q-btn flat color="negative" label="vymazat" @click="clearRequirements" />
            <q-btn unelevated color="primary" label="uložit" type="submit" />
          </div>
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import type { PackageTypeSchema } from '@/client'
import { ref, watch } from 'vue'
import PackageTypeSearchSelect from '../selects/PackageTypeSearchSelect.vue'

type RequirementMode = 'package' | 'batch'

const props = defineProps<{
  productName: string
  initialMode?: RequirementMode
  desiredPackageTypeName?: string | null
  desiredBatchCode?: string | null
}>()

const emit = defineEmits<{
  (
    e: 'save',
    payload: { desired_package_type_name: string | null; desired_batch_code: string | null },
  ): void
}>()

const showDialog = defineModel<boolean>('show', { default: false })

const modeOptions = [
  { label: 'Typ balení', value: 'package' },
  { label: 'Šarže', value: 'batch' },
] satisfies { label: string; value: RequirementMode }[]

const mode = ref<RequirementMode>(props.initialMode ?? 'package')
const selectedPackage = ref<PackageTypeSchema>()
const batchCode = ref('')

watch(
  () => showDialog.value,
  (opened) => {
    if (!opened) {
      return
    }
    mode.value = props.initialMode ?? (props.desiredBatchCode ? 'batch' : 'package')
    batchCode.value = props.desiredBatchCode ?? ''
    selectedPackage.value = props.desiredPackageTypeName
      ? ({ name: props.desiredPackageTypeName } as PackageTypeSchema)
      : undefined
  },
)

const submit = () => {
  emit('save', {
    desired_package_type_name:
      mode.value === 'package' ? (selectedPackage.value?.name ?? null) : null,
    desired_batch_code: mode.value === 'batch' ? batchCode.value || null : null,
  })
  showDialog.value = false
}

const clearRequirements = () => {
  emit('save', {
    desired_package_type_name: null,
    desired_batch_code: null,
  })
  showDialog.value = false
}
</script>
