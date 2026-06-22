<template>
  <q-select
    ref="itemSelect"
    :dense="dense"
    outlined
    :label="label"
    :hint="hint"
    :disable="disable"
    v-model="modelValue"
    :options="options"
    option-label="name"
    use-input
    clearable
    :multiple="false"
    @filter="filterFn"
    @abort="abortFilterFn"
    :autofocus="autofocus"
    @update:model-value="onSelectChange"
    clear-icon="sym_o_close_small"
    :rules="required ? [rules.notEmpty] : []"
  >
    <template v-slot:no-option>
      <q-item>
        <q-item-section class="text-grey"> Žádné Výsledky </q-item-section>
      </q-item>
    </template>
  </q-select>
</template>

<script setup lang="ts">
import { warehouseApiRoutesCustomerGetCustomers, type CustomerBaseSchema } from '@/client'
import { rules } from '@/utils/rules'
import type { QSelect } from 'quasar'
import { nextTick, ref } from 'vue'

const MAX_LEN = 5

withDefaults(
  defineProps<{
    label?: string
    hint?: string
    required?: boolean
    disable?: boolean
    dense?: boolean
    autofocus?: boolean
  }>(),
  {
    label: 'Vyhledat zákazníka',
    hint: undefined,
    required: true,
    disable: false,
    dense: false,
    autofocus: true,
  },
)

const modelValue = defineModel<CustomerBaseSchema>()

const options = ref<CustomerBaseSchema[]>([])
async function filterFn(val: string, update: (fn: () => void) => void, abort: () => void) {
  if (!val) {
    abort()
    return
  }

  const result = await warehouseApiRoutesCustomerGetCustomers({ query: { search_term: val } })
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
