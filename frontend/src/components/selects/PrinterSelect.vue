<template>
  <q-select
    v-model="modelValue"
    outlined
    use-input
    fill-input
    clearable
    clear-icon="sym_o_close_small"
    hide-dropdown-icon
    emit-value
    map-options
    :options="options"
    option-label="label"
    option-value="value"
    :label="label"
    :hint="hint"
    input-debounce="250"
    hide-selected
    @filter="onFilter"
  >
    <template #no-option>
      <q-item>
        <q-item-section class="text-grey">Žádné tiskárny</q-item-section>
      </q-item>
    </template>
  </q-select>
</template>

<script setup lang="ts">
import { warehouseApiRoutesPrintersGetPrinters, type PrinterSchema } from '@/client'
import { ref } from 'vue'

const modelValue = defineModel<string | null | undefined>()

withDefaults(
  defineProps<{
    label?: string
    hint?: string
  }>(),
  {
    label: 'Tiskárna',
    hint: 'Vyberte dostupnou tiskárnu podle kódu',
  },
)

type SelectOption = {
  label: string
  value: string
}

const options = ref<SelectOption[]>([])

const toOptions = (printers: PrinterSchema[]): SelectOption[] => {
  return printers.map((printer) => ({
    label: printer.description ? `${printer.code} - ${printer.description}` : printer.code,
    value: printer.code,
  }))
}

const fetchPrinters = async (searchTerm?: string) => {
  const result = await warehouseApiRoutesPrintersGetPrinters({
    query: {
      search_term: searchTerm,
    },
  })

  if (result.error) {
    return
  }

  options.value = toOptions(result.data?.data ?? [])
}

const onFilter = async (
  val: string,
  update: (callbackFn: () => void) => void,
  abort: () => void,
) => {
  const term = val.trim()

  await fetchPrinters(term || undefined)
  if (term && !options.value.length) {
    abort()
    return
  }

  update(() => {
    options.value = [...options.value]
  })
}

await fetchPrinters()
</script>
