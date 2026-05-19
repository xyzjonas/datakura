<template>
  <q-select
    ref="batchSelect"
    outlined
    :label="modelValue ? (modelValue.primary_barcode?.code || `Šarže #${modelValue.id}`) : 'Vyhledat šarži'"
    hint="Vyberte existující šarži"
    v-model="modelValue"
    :options="options"
    :option-label="(opt) => opt.primary_barcode?.code || `Šarže #${opt.id}`"
    use-input
    clearable
    :multiple="false"
    :loading="loading"
    autofocus
    @update:model-value="onSelectChange"
    clear-icon="sym_o_close_small"
  >
    <template v-slot:no-option>
      <q-item>
        <q-item-section class="text-grey"> Žádné Výsledky </q-item-section>
      </q-item>
    </template>
    <template v-slot:option="scope">
      <q-item v-bind="scope.itemProps">
        <q-item-section>
          <q-item-label>{{ scope.opt.primary_barcode?.code || `Šarže #${scope.opt.id}` }}</q-item-label>
          <q-item-label caption v-if="scope.opt.description">{{ scope.opt.description }}</q-item-label>
        </q-item-section>
      </q-item>
    </template>
  </q-select>
</template>

<script setup lang="ts">
import { warehouseApiRoutesPackagingGetBatches, type BatchSchema } from '@/client'
import { useApi } from '@/composables/use-api'
import type { QSelect } from 'quasar'
import { nextTick, onMounted, ref, watch } from 'vue'

const { onResponse } = useApi()

const modelValue = defineModel<BatchSchema>()

const options = ref<BatchSchema[]>([])
const loading = ref(false)
const searchTerm = ref('')

const fetch = async () => {
  loading.value = true
  const result = await warehouseApiRoutesPackagingGetBatches({
    query: { search_term: searchTerm.value || undefined },
  })
  const data = onResponse(result)
  if (data) {
    options.value = data.data || []
  }
  loading.value = false
}

onMounted(fetch)

watch(searchTerm, () => {
  fetch()
})

const batchSelect = ref<QSelect | null>(null)
function onSelectChange() {
  // Blur the select after selection
  nextTick(() => {
    // Defensive: make sure the ref exists
    if (batchSelect.value?.blur) {
      batchSelect.value.blur()
    }
  })
}
</script>

<style lang="css" scoped></style>
