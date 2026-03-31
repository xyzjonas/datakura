<template>
  <q-select
    v-model="modelValue"
    outlined
    dense
    clearable
    use-input
    fill-input
    emit-value
    map-options
    hide-hint
    option-value="code"
    :option-label="getOptionLabel"
    :options="options"
    :label="label"
    :hint="hint"
    clear-icon="sym_o_close_small"
    placeholder="...hledat podle názvu nebo kódu"
    @filter="filterFn"
  >
    <template #no-option>
      <q-item>
        <q-item-section class="text-grey">Žádné výsledky</q-item-section>
      </q-item>
    </template>
    <!-- <template #selected-item="scope">
      <q-badge>{{ scope.opt.code }}</q-badge>
    </template> -->
  </q-select>
</template>

<script setup lang="ts">
import { warehouseApiRoutesProductGetProducts, type ProductSchema } from '@/client'
import { ref } from 'vue'

withDefaults(
  defineProps<{
    label?: string
    hint?: string
  }>(),
  {
    label: 'Filtrovat podle produktu',
    hint: 'Vyhledat produkt podle názvu nebo kódu.',
  },
)

const modelValue = defineModel<string | null | undefined>()

const options = ref<ProductSchema[]>([])

const getOptionLabel = (option: ProductSchema) => `${option.code} - ${option.name}`

const filterFn = async (value: string, update: (fn: () => void) => void) => {
  if (!value) {
    update(() => {
      options.value = []
    })
    return
  }

  const result = await warehouseApiRoutesProductGetProducts({
    query: {
      search_term: value,
      page_size: 10,
    },
  })

  if (result.error) {
    return
  }

  const products = result.data?.data ?? []

  update(() => {
    options.value = products
  })
}
</script>
