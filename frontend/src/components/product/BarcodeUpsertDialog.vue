<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-full max-w-2xl">
      <div class="p-4">
        <div class="w-full flex items-center mb-4 gap-2">
          <span class="text-2xl uppercase">{{ title }}</span>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>

        <q-form class="flex flex-col gap-2" @submit="onSubmit">
          <div class="flex gap-2 flex-wrap">
            <q-input
              v-model.trim="form.code"
              outlined
              label="Jedinečný kód čárového kódu"
              :rules="[rules.notEmpty]"
              class="flex-[2] min-w-[250px]"
              hide-bottom-space
            />
            <q-btn
              outline
              color="primary"
              icon="sym_o_auto_awesome"
              label="Generovat"
              :loading="generating"
              @click="generateBarcode"
              class="flex-1"
            />
          </div>

          <q-select
            v-model="form.barcode_type"
            outlined
            label="Typ čárového kódu"
            :options="barcodeTypeOptions"
            emit-value
            map-options
            hide-bottom-space
            :rules="[rules.notEmpty]"
          />

          <q-toggle v-model="form.is_primary" color="primary" label="Nastavit jako primární" />
          <div class="text-sm text-muted -mt-1">
            Primární čárový kód bude použit jako výchozí pro tento produkt (např. při tisku štítků).
          </div>

          <q-separator />
          <div class="md:col-span-2 mt-2 flex justify-end">
            <q-btn
              type="submit"
              unelevated
              color="primary"
              :loading="loading"
              :label="submitLabel"
              class="h-[3rem] min-w-[10rem]"
            />
          </div>
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { warehouseApiRoutesProductGenerateBarcode } from '@/client'
import { useApi } from '@/composables/use-api'
import { rules } from '@/utils/rules'
import { useQuasar } from 'quasar'
import { ref, watch } from 'vue'

const showDialog = defineModel<boolean>('show', { default: false })

interface BarcodeFormData {
  code: string
  barcode_type: string
  is_primary: boolean
}

const form = defineModel<BarcodeFormData>({
  required: true,
})

withDefaults(
  defineProps<{
    title?: string
    submitLabel?: string
    loading?: boolean
  }>(),
  {
    title: 'Čárový kód',
    submitLabel: 'uložit',
    loading: false,
  },
)

const emit = defineEmits<{
  (e: 'submit', body: BarcodeFormData): void
}>()

const $q = useQuasar()
const generating = ref(false)

const { onResponse } = useApi()
const generateBarcode = async () => {
  try {
    generating.value = true
    const response = await warehouseApiRoutesProductGenerateBarcode({
      body: {
        barcode_type: form.value.barcode_type || 'EAN13',
      },
    })

    const data = onResponse(response)
    if (data?.data) {
      form.value.code = data.data.code
      $q.notify({
        type: 'positive',
        message: 'Čárový kód byl vygenerován',
        position: 'top',
      })
    }
  } finally {
    generating.value = false
  }
}

const barcodeTypeOptions = [
  { label: 'EAN-13', value: 'EAN13' },
  { label: 'EAN-8', value: 'EAN8' },
  { label: 'UPC', value: 'UPC' },
  { label: 'GS1-128', value: 'GS1_128' },
  { label: 'QR Code', value: 'QR' },
  { label: 'Serial Number', value: 'SERIAL' },
  { label: 'SSCC', value: 'SSCC' },
  { label: 'Custom', value: 'CUSTOM' },
]

watch(showDialog, (visible) => {
  if (visible) {
    form.value.is_primary ??= false
    form.value.barcode_type ??= 'EAN13'
  }
})

const onSubmit = () => {
  emit('submit', { ...form.value })
}
</script>

<style scoped></style>
