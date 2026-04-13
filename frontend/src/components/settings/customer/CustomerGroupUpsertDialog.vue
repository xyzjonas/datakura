<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-full max-w-2xl">
      <div class="p-4">
        <div class="w-full flex items-center mb-4 gap-2">
          <span class="text-2xl uppercase">{{ title }}</span>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>

        <q-form class="flex flex-col gap-3" @submit="onSubmit">
          <q-input v-model.trim="form.code" outlined label="Kód" :rules="[rules.notEmpty]" />
          <q-input v-model.trim="form.name" outlined label="Název" :rules="[rules.notEmpty]" />

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
import type { CustomerGroupCreateOrUpdateSchema } from '@/client'
import { rules } from '@/utils/rules'

const showDialog = defineModel<boolean>('show', { default: false })
const form = defineModel<CustomerGroupCreateOrUpdateSchema>({ required: true })

withDefaults(
  defineProps<{
    title?: string
    submitLabel?: string
    loading?: boolean
  }>(),
  {
    title: 'Skupina zákazníků',
    submitLabel: 'uložit',
    loading: false,
  },
)

const emit = defineEmits<{
  (e: 'submit', body: CustomerGroupCreateOrUpdateSchema): void
}>()

const onSubmit = () => {
  emit('submit', { ...form.value })
}
</script>

<style scoped></style>
