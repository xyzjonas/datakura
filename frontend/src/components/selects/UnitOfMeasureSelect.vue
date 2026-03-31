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
    label="Měrná jednotka"
    hint="Jednotka, ve které se produkt skladuje (např. ks, kg, m)"
    input-debounce="250"
    hide-selected
    @filter="onFilter"
  >
    <template #no-option>
      <q-item>
        <q-item-section class="text-grey">Žádné jednotky</q-item-section>
      </q-item>
    </template>
  </q-select>
</template>

<script setup lang="ts">
import { warehouseApiRoutesPackagingGetUnits, type UnitOfMeasureSchema } from '@/client'
import { ref } from 'vue'

const modelValue = defineModel<string | null | undefined>()

type SelectOption = {
  label: string
  value: string
}

const options = ref<SelectOption[]>([])

const toOptions = (units: UnitOfMeasureSchema[]): SelectOption[] => {
  return units.map((unit) => ({
    label: unit.name,
    value: unit.name,
  }))
}

const fetchUnits = async (searchTerm?: string) => {
  const result = await warehouseApiRoutesPackagingGetUnits({
    query: {
      page: 1,
      page_size: 20,
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

  if (!term) {
    await fetchUnits()
    update(() => {
      options.value = [...options.value]
    })
    return
  }

  await fetchUnits(term)
  if (!options.value.length) {
    abort()
    return
  }

  update(() => {
    options.value = [...options.value]
  })
}

await fetchUnits()
</script>

<style scoped></style>
