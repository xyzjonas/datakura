<template>
  <q-select
    v-model="modelValue"
    outlined
    use-input
    clearable
    clear-icon="sym_o_close_small"
    :options="options"
    option-label="name"
    option-value="id"
    :label="label"
    :hint="hint"
    :rules="required ? [rules.notEmpty] : []"
    input-debounce="250"
    @filter="onFilter"
    @input-value="onInput"
  >
    <template #no-option>
      <q-item v-if="!canCreate">
        <q-item-section class="text-grey">Žádné typy dopravy</q-item-section>
      </q-item>
    </template>

    <!-- rendered after the options as well as the "no-option" content -->
    <template v-if="canCreate" #after-options>
      <q-item clickable data-testid="shipping-type-create" @click="createType">
        <q-item-section avatar><q-icon name="sym_o_add" color="primary" /></q-item-section>
        <q-item-section>
          Vytvořit typ dopravy <strong>„{{ typedName }}“</strong>
        </q-item-section>
      </q-item>
    </template>
  </q-select>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesShippingTypesCreateShippingType,
  warehouseApiRoutesShippingTypesGetShippingTypes,
  type ShippingTypeSchema,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { rules } from '@/utils/rules'
import { computed, ref } from 'vue'

const modelValue = defineModel<ShippingTypeSchema | null>({ default: null })

withDefaults(
  defineProps<{
    label?: string
    hint?: string
    required?: boolean
  }>(),
  {
    label: 'Typ dopravy',
    hint: undefined,
    required: false,
  },
)

const { onResponse } = useApi()

const options = ref<ShippingTypeSchema[]>([])
const typedName = ref('')

// offer the creation only for a non-empty text that matches no existing type exactly
const canCreate = computed(() => {
  const name = typedName.value.trim().toLowerCase()
  return !!name && !options.value.some((option) => option.name.toLowerCase() === name)
})

const onInput = (value: string) => {
  typedName.value = value
}

const fetchTypes = async (searchTerm?: string) => {
  const result = await warehouseApiRoutesShippingTypesGetShippingTypes({
    query: { page: 1, page_size: 20, search_term: searchTerm },
  })
  if (!result.error) {
    options.value = result.data?.data ?? []
  }
}

const onFilter = async (val: string, update: (callbackFn: () => void) => void) => {
  await fetchTypes(val.trim() || undefined)
  update(() => {
    options.value = [...options.value]
  })
}

const createType = async () => {
  const name = typedName.value.trim()
  if (!name) {
    return
  }
  const response = onResponse(
    await warehouseApiRoutesShippingTypesCreateShippingType({ body: { name } }),
  )
  if (response?.data) {
    options.value = [response.data, ...options.value.filter((o) => o.id !== response.data.id)]
    modelValue.value = response.data
    typedName.value = ''
  }
}
</script>
