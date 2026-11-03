<template>
  <q-select
    :model-value="modelValue"
    outlined
    use-input
    clearable
    clear-icon="sym_o_close_small"
    :options="displayedOptions"
    :option-label="optionLabel"
    option-value="id"
    :label="label"
    :hint="hint"
    input-debounce="250"
    @update:model-value="onSelect"
    @filter="onFilter"
    @input-value="onInput"
  >
    <template #option="{ opt, itemProps }">
      <q-item v-bind="itemProps" :data-testid="opt.isCreate ? 'shipping-type-create' : undefined">
        <q-item-section v-if="opt.isCreate" avatar>
          <q-icon name="sym_o_add" color="primary" />
        </q-item-section>
        <q-item-section :class="{ 'text-primary': opt.isCreate }">
          {{ optionLabel(opt) }}
        </q-item-section>
      </q-item>
    </template>
    <template #no-option>
      <q-item>
        <q-item-section class="text-grey">Žádné typy dopravy</q-item-section>
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
import { computed, ref } from 'vue'

const modelValue = defineModel<ShippingTypeSchema | null>({ default: null })

withDefaults(
  defineProps<{
    label?: string
    hint?: string
  }>(),
  {
    label: 'Typ dopravy',
    hint: undefined,
  },
)

const { onResponse } = useApi()

type TypeOption = ShippingTypeSchema & { isCreate?: boolean }

const CREATE_OPTION_ID = -1

const options = ref<ShippingTypeSchema[]>([])
const typedName = ref('')

// offer the creation only for a non-empty text that matches no existing type exactly
const canCreate = computed(() => {
  const name = typedName.value.trim().toLowerCase()
  return !!name && !options.value.some((option) => option.name.toLowerCase() === name)
})

// "create" is the last option of the list, so it works without any slot tricks
const displayedOptions = computed<TypeOption[]>(() =>
  canCreate.value
    ? [
        ...options.value,
        {
          id: CREATE_OPTION_ID,
          name: typedName.value.trim(),
          created: '',
          changed: '',
          isCreate: true,
        },
      ]
    : options.value,
)

const optionLabel = (option: TypeOption) =>
  option.isCreate ? `Vytvořit typ dopravy „${option.name}“` : option.name

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

const createType = async (name: string) => {
  const response = onResponse(
    await warehouseApiRoutesShippingTypesCreateShippingType({ body: { name } }),
  )
  if (response?.data) {
    options.value = [response.data, ...options.value.filter((o) => o.id !== response.data.id)]
    modelValue.value = response.data
    typedName.value = ''
  }
}

const onSelect = async (value: TypeOption | null) => {
  if (value?.isCreate) {
    await createType(value.name)
    return
  }
  modelValue.value = value
}
</script>
