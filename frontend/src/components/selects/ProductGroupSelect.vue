<template>
  <q-select
    v-model="modelValue"
    outlined
    use-input
    fill-input
    clearable
    emit-value
    map-options
    :options="options"
    option-label="label"
    option-value="value"
    label="Skupina"
    hint="Volitelné"
    input-debounce="250"
    @filter="onFilter"
  >
    <template #no-option>
      <q-item>
        <q-item-section class="text-grey">Žádné skupiny</q-item-section>
      </q-item>
    </template>
  </q-select>
</template>

<script setup lang="ts">
import { warehouseApiRoutesGroupGetGroups, type ProductGroupSchema } from '@/client'
import { ref } from 'vue'

const modelValue = defineModel<string | null | undefined>()

type SelectOption = {
  label: string
  value: string
}

const options = ref<SelectOption[]>([])

const toOptions = (groups: ProductGroupSchema[]): SelectOption[] => {
  return groups.map((group) => ({
    label: group.name,
    value: group.name,
  }))
}

const fetchGroups = async (searchTerm?: string) => {
  const result = await warehouseApiRoutesGroupGetGroups({
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
    await fetchGroups()
    update(() => {
      options.value = [...options.value]
    })
    return
  }

  await fetchGroups(term)
  if (!options.value.length) {
    abort()
    return
  }

  update(() => {
    options.value = [...options.value]
  })
}

await fetchGroups()
</script>

<style scoped></style>
