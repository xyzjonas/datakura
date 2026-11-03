<template>
  <div class="flex flex-col gap-2" data-test="certified-stock-picker">
    <q-inner-loading :showing="loading" />

    <div v-if="!loading && rows.length === 0" class="text-sm text-muted py-4 text-center">
      Pro tento produkt není skladem žádné certifikované zboží.
    </div>

    <q-markup-table v-else-if="rows.length" flat bordered dense separator="horizontal">
      <thead>
        <tr>
          <th class="text-left">Certifikát</th>
          <th class="text-left">Objednáno</th>
          <th class="text-right">Skladem</th>
          <th class="text-left">Soubor</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in rows"
          :key="row.id"
          class="cursor-pointer"
          :class="{ 'bg-blue-1': row.batch_code === modelValue }"
          data-test="certified-stock-row"
          @click="modelValue = row.batch_code"
        >
          <td class="text-left">
            <div class="font-semibold">{{ row.code }}</div>
            <div v-if="row.description" class="text-xs text-gray-6 whitespace-normal">
              {{ row.description }}
            </div>
          </td>
          <td class="text-left tabular-nums">{{ formatDate(row.ordered_date) }}</td>
          <td class="text-right tabular-nums font-semibold">{{ row.amount }}</td>
          <td class="text-left"><CertificationFileLink :attachment="row.attachment" /></td>
        </tr>
      </tbody>
    </q-markup-table>
  </div>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesCertificationsGetAvailableCertifications,
  type AvailableCertificationSchema,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { onMounted, ref, watch } from 'vue'
import CertificationFileLink from './CertificationFileLink.vue'

const { onResponse } = useApi()

const props = defineProps<{ productCode: string }>()

/** Barcode of the batch backing the selected certification. */
const modelValue = defineModel<string | null>({ default: null })

const rows = ref<AvailableCertificationSchema[]>([])
const loading = ref(false)

const fetch = async () => {
  loading.value = true
  try {
    const res = await warehouseApiRoutesCertificationsGetAvailableCertifications({
      query: { product_code: props.productCode },
    })
    rows.value = onResponse(res)?.data ?? []
  } finally {
    loading.value = false
  }
}

const formatDate = (iso: string) => new Date(iso).toLocaleDateString('cs-CZ')

onMounted(fetch)
watch(() => props.productCode, fetch)
</script>
