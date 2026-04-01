<template>
  <q-select
    v-model="modelValue"
    :options="options"
    option-value="value"
    option-label="label"
    emit-value
    map-options
    :label="label"
    outlined
    dense
  >
    <template #no-option>
      <q-item>
        <q-item-section class="text-grey">Žádné příjmové lokace</q-item-section>
      </q-item>
    </template>
  </q-select>
</template>

<script setup lang="ts">
import { warehouseApiRoutesWarehouseGetWarehouseLocations } from '@/client'
import { useApi } from '@/composables/use-api'
import { ref } from 'vue'

type SelectOption = {
  value: string
  label: string
}

withDefaults(
  defineProps<{
    label?: string
  }>(),
  {
    label: 'Příjmové místo',
  },
)

const modelValue = defineModel<string | undefined>()
const options = ref<SelectOption[]>([])
const { onResponse } = useApi()

const response = await warehouseApiRoutesWarehouseGetWarehouseLocations({
  query: { page_size: 200 },
})
const data = onResponse(response)

if (data) {
  options.value = data.data
    .filter((location) => location.is_putaway)
    .map((location) => ({
      value: location.code,
      label: `${location.code} (${location.warehouse_name})`,
    }))

  if (!modelValue.value && options.value.length > 0) {
    modelValue.value = options.value[0].value
  }
}
</script>
