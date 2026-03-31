<template>
  <q-select
    v-model="modelValue"
    outlined
    use-input
    fill-input
    clearable
    emit-value
    map-options
    clear-icon="sym_o_close_small"
    hide-dropdown-icon
    hide-selected
    :options="options"
    option-label="label"
    option-value="value"
    :label="label"
    input-debounce="250"
    @filter="onFilter"
  >
    <template #no-option>
      <q-item>
        <q-item-section class="text-grey">Žádné typy zboží</q-item-section>
      </q-item>
    </template>
  </q-select>
</template>

<script setup lang="ts">
import { warehouseApiRoutesProductGetTypes, type ProductTypeSchema } from '@/client'
import { ref } from 'vue'

const modelValue = defineModel<string | null | undefined>()

withDefaults(
  defineProps<{
    label?: string
    hint?: string | undefined | null
  }>(),
  {
    label: 'Typ zboží',
    hint: 'Typ zboží, který určuje kategorii produktu pro lepší organizaci a filtrování produktů',
  },
)

type SelectOption = {
  label: string
  value: string
}

const options = ref<SelectOption[]>([])

const toOptions = (types: ProductTypeSchema[]): SelectOption[] => {
  return types.map((type) => ({
    label: type.name,
    value: type.name,
  }))
}

const fetchTypes = async (searchTerm?: string) => {
  const result = await warehouseApiRoutesProductGetTypes({
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
    await fetchTypes()
    update(() => {
      options.value = [...options.value]
    })
    return
  }

  await fetchTypes(term)
  if (!options.value.length) {
    abort()
    return
  }

  update(() => {
    options.value = [...options.value]
  })
}

await fetchTypes()
</script>

<style scoped></style>
