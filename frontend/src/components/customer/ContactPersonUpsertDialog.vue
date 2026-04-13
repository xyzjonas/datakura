<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-full max-w-2xl">
      <div class="p-4">
        <div class="w-full flex items-center mb-4 gap-2">
          <span class="text-2xl uppercase">{{ title }}</span>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>

        <q-form class="flex flex-col gap-3" @submit="onSubmit">
          <!-- Name components -->
          <div class="grid grid-cols-5 gap-2">
            <q-input
              v-model.trim="form.title_pre"
              outlined
              label="Tituly před"
              placeholder="Ing."
            />
            <q-input
              v-model.trim="form.first_name"
              outlined
              label="Jméno"
              :rules="[rules.notEmpty]"
            />
            <q-input v-model.trim="form.middle_name" outlined label="Prostřední jméno" />
            <q-input
              v-model.trim="form.last_name"
              outlined
              label="Příjmení"
              :rules="[rules.notEmpty]"
            />
            <q-input
              v-model.trim="form.title_post"
              outlined
              label="Tituly po"
              placeholder="Ph.D."
            />
          </div>

          <!-- Contact information -->
          <div class="grid grid-cols-3 gap-2">
            <q-input v-model.trim="form.email" outlined label="Email" type="email" />
            <q-input v-model.trim="form.phone" outlined label="Telefon" />
            <q-input v-model="form.birth_date" outlined label="Datum narození" type="date" />
          </div>

          <!-- Address -->
          <div class="grid grid-cols-2 gap-2">
            <q-input v-model.trim="form.street" outlined label="Ulice" class="col-span-2" />
            <q-input v-model.trim="form.city" outlined label="Město" />
            <q-input v-model.trim="form.postal_code" outlined label="PSČ" />
          </div>

          <!-- Additional -->
          <div class="grid grid-cols-2 gap-2">
            <q-input
              v-model.trim="form.profile_picture_url"
              outlined
              label="Profilový obrázek URL"
            />
          </div>

          <!-- Status -->
          <div class="flex gap-4">
            <q-checkbox v-model="form.is_deleted" label="Smazaný" />
          </div>

          <!-- Note -->
          <q-input v-model.trim="form.note" outlined type="textarea" rows="2" label="Poznámka" />

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
import type { ContactPersonCreateOrUpdateSchema } from '@/client'
import { rules } from '@/utils/rules'

const showDialog = defineModel<boolean>('show', { default: false })
const form = defineModel<ContactPersonCreateOrUpdateSchema>({ required: true })

withDefaults(
  defineProps<{
    title?: string
    submitLabel?: string
    loading?: boolean
  }>(),
  {
    title: 'Kontaktní osoba',
    submitLabel: 'uložit',
    loading: false,
  },
)

const emit = defineEmits<{
  (e: 'submit', body: ContactPersonCreateOrUpdateSchema): void
}>()

const onSubmit = () => {
  emit('submit', { ...form.value })
}
</script>

<style scoped></style>
