<template>
  <q-select
    v-model="selected"
    outlined
    use-input
    fill-input
    clearable
    clear-icon="sym_o_close_small"
    hide-dropdown-icon
    input-debounce="250"
    :options="options"
    option-label="label"
    option-value="id"
    :label="label"
    :hint="hint"
    @filter="onFilter"
  >
    <template #no-option>
      <q-item>
        <q-item-section class="text-grey">Žádné normy</q-item-section>
      </q-item>
    </template>
  </q-select>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesNormsGetNorm,
  warehouseApiRoutesNormsGetNorms,
  type NormRefSchema,
} from '@/client'
import { ref, watch } from 'vue'

/** id of the selected norm from the catalogue */
const modelValue = defineModel<number | null | undefined>()

withDefaults(defineProps<{ label?: string; hint?: string }>(), {
  label: 'Norma',
  hint: 'Norma produktu z katalogu (DIN, ISO, ČSN)',
})

const options = ref<NormRefSchema[]>([])
const selected = ref<NormRefSchema | null>(null)

const search = async (term?: string) => {
  const result = await warehouseApiRoutesNormsGetNorms({ query: { search_term: term } })
  options.value = result.error ? [] : (result.data?.data ?? [])
}

const loadSelected = async (id: number) => {
  const result = await warehouseApiRoutesNormsGetNorm({ path: { norm_id: id } })
  selected.value = result.data?.data ?? null
}

watch(
  modelValue,
  (id) => {
    if (id == null) {
      selected.value = null
    } else if (selected.value?.id !== id) {
      void loadSelected(id)
    }
  },
  { immediate: true },
)

watch(selected, (norm) => {
  modelValue.value = norm?.id ?? null
})

const onFilter = async (val: string, update: (fn: () => void) => void) => {
  await search(val.trim() || undefined)
  update(() => {})
}
</script>
