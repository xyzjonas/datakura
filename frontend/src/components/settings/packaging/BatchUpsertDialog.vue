<template>
  <q-dialog v-model="showDialog">
    <q-card class="w-full max-w-lg">
      <div class="p-4">
        <div class="w-full flex items-center mb-4 gap-2">
          <span class="text-2xl uppercase">{{ title }}</span>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>

        <q-form class="flex flex-col gap-3" @submit="onSubmit">
          <div class="flex gap-2">
            <q-input
              v-model.trim="form.barcode"
              outlined
              label="Kód šarže"
              :rules="!form.auto_generate_barcode ? [rules.notEmpty] : []"
              :disable="form.auto_generate_barcode"
              class="flex-1"
            />
            <q-btn
              flat
              dense
              :color="form.auto_generate_barcode ? 'primary' : 'grey'"
              :icon="form.auto_generate_barcode ? 'sym_o_check_box' : 'sym_o_check_box_outline_blank'"
              @click="form.auto_generate_barcode = !form.auto_generate_barcode"
              class="mt-1"
            >
              <q-tooltip>Automaticky vygenerovat kód</q-tooltip>
            </q-btn>
          </div>

          <q-input
            v-model.trim="form.description"
            outlined
            type="textarea"
            autogrow
            label="Popis"
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
import type { BatchCreateOrUpdateSchema } from '@/client'
import { rules } from '@/utils/rules'

const showDialog = defineModel<boolean>('show', { default: false })
const form = defineModel<BatchCreateOrUpdateSchema>({ required: true })

withDefaults(
  defineProps<{
    title?: string
    submitLabel?: string
    loading?: boolean
  }>(),
  {
    title: 'Šarže',
    submitLabel: 'uložit',
    loading: false,
  },
)

const emit = defineEmits<{
  (e: 'submit', body: BatchCreateOrUpdateSchema): void
}>()

const onSubmit = () => {
  emit('submit', {
    ...form.value,
    description: form.value.description?.trim() || null,
    barcode: form.value.barcode?.trim() || null,
  })
}
</script>

<style scoped></style>
