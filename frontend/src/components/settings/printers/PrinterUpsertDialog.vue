<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-full max-w-lg">
      <div class="p-4">
        <div class="w-full flex items-center mb-4 gap-2">
          <span class="text-2xl uppercase">{{ title }}</span>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>

        <q-form class="flex flex-col gap-3" @submit="onSubmit">
          <q-input
            v-model.trim="form.code"
            outlined
            label="Kód / Název"
            :rules="[rules.notEmpty]"
            hint="Jednoznačné/unikátní jméno tiskárny"
          />

          <q-input
            v-model.trim="form.description"
            outlined
            type="textarea"
            autogrow
            label="Popis"
            hint="Volitelné"
          />

          <q-input
            v-model.trim="form.ip"
            outlined
            label="IP adresa"
            hint="IP adresa tiskárny v lokální síti"
          />

          <q-input
            v-model.number="form.port"
            outlined
            type="number"
            label="Port"
            hint="Port tiskárny pro připojení ZPL (výchozí: 9100)"
          />

          <q-input
            v-model.number="form.dpi"
            outlined
            type="number"
            label="DPI"
            hint="Základní rozlišení tisku v bodech na palec"
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
import type { PrinterCreateOrUpdateSchema } from '@/client'
import { rules } from '@/utils/rules'

const showDialog = defineModel<boolean>('show', { default: false })
const form = defineModel<PrinterCreateOrUpdateSchema>({ required: true })

withDefaults(
  defineProps<{
    title?: string
    submitLabel?: string
    loading?: boolean
  }>(),
  {
    title: 'Tiskárna',
    submitLabel: 'uložit',
    loading: false,
  },
)

const emit = defineEmits<{
  (e: 'submit', body: PrinterCreateOrUpdateSchema): void
}>()

const onSubmit = () => {
  emit('submit', {
    ...form.value,
    code: form.value.code.trim(),
    description: form.value.description?.trim() || null,
  })
}
</script>
