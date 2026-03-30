<template>
  <q-dialog v-model="showDialog">
    <q-card class="w-full max-w-lg">
      <div class="p-4">
        <div class="w-full flex items-center mb-4 gap-2">
          <span class="text-2xl uppercase">{{ title }}</span>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>

        <q-form class="flex flex-col gap-3" @submit="onSubmit">
          <q-input v-model.trim="form.name" outlined label="Název" :rules="[rules.notEmpty]" />

          <q-input
            v-model.number="form.amount_of_base_uom"
            outlined
            type="number"
            min="0"
            step="0.0001"
            label="Množství v základní jednotce"
            hint="Volitelné"
          />

          <q-select
            v-model="form.base_uom"
            outlined
            clearable
            emit-value
            map-options
            option-label="label"
            option-value="value"
            :options="baseUomOptions"
            label="Základní jednotka"
            hint="Volitelné"
          />

          <div class="mt-2 flex justify-end">
            <q-btn
              type="submit"
              unelevated
              color="primary"
              :loading="loading"
              :label="submitLabel"
              class="h-[3rem] min-w-[10rem]"
            />
          </div>
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesPackagingGetUnits,
  type UnitOfMeasureCreateOrUpdateSchema,
  type UnitOfMeasureSchema,
} from '@/client'
import { rules } from '@/utils/rules'
import { ref, watch } from 'vue'

const showDialog = defineModel<boolean>('show', { default: false })
const form = defineModel<UnitOfMeasureCreateOrUpdateSchema>({ required: true })

withDefaults(
  defineProps<{
    title?: string
    submitLabel?: string
    loading?: boolean
  }>(),
  {
    title: 'Jednotka',
    submitLabel: 'uložit',
    loading: false,
  },
)

const emit = defineEmits<{
  (e: 'submit', body: UnitOfMeasureCreateOrUpdateSchema): void
}>()

const baseUomOptions = ref<Array<{ label: string; value: string }>>([])

const toOptions = (items: UnitOfMeasureSchema[]) => {
  return items.map((item) => ({
    label: item.name,
    value: item.name,
  }))
}

const fetchBaseUoms = async () => {
  const result = await warehouseApiRoutesPackagingGetUnits({
    query: { page: 1, page_size: 200 },
  })
  if (result.error) {
    return
  }
  baseUomOptions.value = toOptions(result.data?.data ?? [])
}

watch(
  showDialog,
  (visible) => {
    if (visible) {
      fetchBaseUoms()
    }
  },
  { immediate: true },
)

const onSubmit = () => {
  emit('submit', { ...form.value })
}
</script>

<style scoped></style>
