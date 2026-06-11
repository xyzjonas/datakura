<template>
  <q-select
    v-model="modelValue"
    outlined
    clearable
    use-input
    fill-input
    emit-value
    map-options
    hide-hint
    option-value="code"
    option-label="label"
    :options="options"
    :label="label"
    :dense="dense"
    clear-icon="sym_o_close_small"
    placeholder="...hledat místo"
    @filter="filterFn"
  >
    <template #no-option>
      <q-item>
        <q-item-section class="text-grey">Žádná místa</q-item-section>
      </q-item>
    </template>
  </q-select>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesWarehouseGetWarehouseLocations,
  type WarehouseLocationSchema,
} from '@/client'
import { ref } from 'vue'

withDefaults(
  defineProps<{
    label?: string
    dense?: boolean
  }>(),
  {
    label: 'Cílové místo',
    dense: true,
  },
)

const modelValue = defineModel<string | null | undefined>()

type SelectOption = { code: string; label: string }
const options = ref<SelectOption[]>([])
let allLocations: WarehouseLocationSchema[] = []

const load = async () => {
  const result = await warehouseApiRoutesWarehouseGetWarehouseLocations({
    query: { page_size: 500 },
  })
  allLocations = result.data?.data ?? []
  options.value = allLocations.map((l) => ({
    code: l.code,
    label: `${l.code} (${l.warehouse_name})`,
  }))
}

load()

const filterFn = (value: string, update: (fn: () => void) => void) => {
  const q = value.toLowerCase()
  update(() => {
    options.value = allLocations
      .filter((l) => l.code.toLowerCase().includes(q))
      .map((l) => ({ code: l.code, label: `${l.code} (${l.warehouse_name})` }))
  })
}
</script>
