<template>
  <q-select
    ref="itemSelect"
    outlined
    :label="modelValue ? modelValue.name : 'Vyhledat typ balení'"
    hint="Vyberte typ balení"
    v-model="modelValue"
    :options="options"
    option-label="name"
    use-input
    clearable
    :multiple="false"
    :loading="loading"
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
import { warehouseApiRoutesPackagingGetPackageTypes, type PackageTypeSchema } from '@/client'
import { useApi } from '@/composables/use-api'
import { rules } from '@/utils/rules'
import type { QSelect } from 'quasar'
import { nextTick, onMounted, ref } from 'vue'

const { onResponse } = useApi()

const modelValue = defineModel<PackageTypeSchema>()

const options = ref<PackageTypeSchema[]>([])
const loading = ref(false)
const fetch = async () => {
  loading.value = true
  const result = await warehouseApiRoutesPackagingGetPackageTypes()
  const data = onResponse(result)
  if (data) {
    options.value = data.data
  }
  loading.value = false
}

onMounted(fetch)

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
