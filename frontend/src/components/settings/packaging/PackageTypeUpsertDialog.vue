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
            v-model.trim="form.description"
            outlined
            type="textarea"
            autogrow
            label="Popis"
            hint="Volitelné"
          />

          <q-input
            v-model.number="form.amount"
            outlined
            type="number"
            min="0.0001"
            step="0.0001"
            label="Množství"
            :rules="[rules.notEmpty, rules.isNumber, rules.atLeastOne]"
          />

          <UnitOfMeasureSelect v-model="form.unit" />

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
import type { PackageTypeCreateOrUpdateSchema } from '@/client'
import UnitOfMeasureSelect from '@/components/selects/UnitOfMeasureSelect.vue'
import { rules } from '@/utils/rules'

const showDialog = defineModel<boolean>('show', { default: false })
const form = defineModel<PackageTypeCreateOrUpdateSchema>({ required: true })

withDefaults(
  defineProps<{
    title?: string
    submitLabel?: string
    loading?: boolean
  }>(),
  {
    title: 'Typ balení',
    submitLabel: 'uložit',
    loading: false,
  },
)

const emit = defineEmits<{
  (e: 'submit', body: PackageTypeCreateOrUpdateSchema): void
}>()

const onSubmit = () => {
  emit('submit', {
    ...form.value,
    description: form.value.description?.trim() || null,
    unit: form.value.unit || null,
  })
}
</script>

<style scoped></style>
