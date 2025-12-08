<template>
  <q-select
    ref="itemSelect"
    outlined
    :label="modelValue ? modelValue.code : 'Vyhledat položku'"
    hint="Vyhledat položku podle názvu nebo kódu."
    v-model="modelValue"
    :options="options"
    option-label="name"
    use-input
    clearable
    :multiple="false"
    @filter="filterFn"
    @abort="abortFilterFn"
    autofocus
    @update:model-value="onSelectChange"
    clear-icon="sym_o_close_small"
    :rules="[rules.notEmpty]"
  >
    <template v-slot:no-option>
      <q-item>
        <q-item-section class="text-grey"> Žádné Výsledky </q-item-section>
      </q-item>
    </template>
    <!-- <template v-slot:selected-item :props="opt">
      <q-item class="p-0">
        <q-item-section>{{ modelValue?.name }}</q-item-section>
      </q-item>
    </template> -->
  </q-select>
</template>

<script setup lang="ts">
import { warehouseApiRoutesProductGetProducts, type ProductSchema } from '@/client'
import { rules } from '@/utils/rules'
import type { QSelect } from 'quasar'
import { nextTick, ref } from 'vue'

const MAX_LEN = 5

const modelValue = defineModel<ProductSchema>()

const options = ref<ProductSchema[]>([])
async function filterFn(val: string, update: (fn: () => void) => void, abort: () => void) {
  if (!val) {
    abort()
    return
  }

  const result = await warehouseApiRoutesProductGetProducts({ query: { search_term: val } })
  if (result.error) {
    return
  }
  const items = result.data?.data ?? []
  // const items = await searchItems(val)
  if (items.length > MAX_LEN) {
    items.length = MAX_LEN
  }

  update(() => {
    options.value = items
  })
}

function abortFilterFn() {
  // console.log('delayed filter aborted')
}

const itemSelect = ref<QSelect | null>(null)
function onSelectChange() {
  // Blur the select after selection
  nextTick(() => {
    // Defensive: make sure the ref exists
    if (itemSelect.value?.blur) {
      itemSelect.value.blur()
    }
  })
}
</script>

<style lang="css" scoped></style>
