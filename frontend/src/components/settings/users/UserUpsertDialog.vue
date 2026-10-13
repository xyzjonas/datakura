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
            v-model.trim="form.username"
            outlined
            label="Uživatelské jméno"
            autocomplete="off"
            :rules="[rules.notEmpty]"
          />

          <q-input
            v-model="form.password"
            outlined
            type="password"
            label="Heslo"
            autocomplete="new-password"
            :rules="editing ? [] : [rules.notEmpty]"
            :hint="editing ? 'Vyplňte pouze pro nastavení nového hesla' : undefined"
          />

          <div class="flex gap-3">
            <q-input v-model.trim="form.first_name" outlined label="Jméno" class="flex-1" />
            <q-input v-model.trim="form.last_name" outlined label="Příjmení" class="flex-1" />
          </div>

          <q-input v-model.trim="form.email" outlined type="email" label="E-mail" />

          <q-toggle
            v-model="form.is_superuser"
            label="Administrátor (správa uživatelů)"
            :disable="isSelf"
          />
          <q-toggle v-model="form.is_active" label="Aktivní účet" :disable="isSelf" />
          <p v-if="isSelf" class="text-xs text-muted">
            Vlastní účet nelze deaktivovat ani odebrat administrátorská práva.
          </p>

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
import { rules } from '@/utils/rules'
import type { UserFormData } from './user-form'

const showDialog = defineModel<boolean>('show', { default: false })
const form = defineModel<UserFormData>({ required: true })

withDefaults(
  defineProps<{
    title?: string
    submitLabel?: string
    loading?: boolean
    editing?: boolean
    isSelf?: boolean
  }>(),
  {
    title: 'Uživatel',
    submitLabel: 'uložit',
    loading: false,
    editing: false,
    isSelf: false,
  },
)

const emit = defineEmits<{
  (e: 'submit', body: UserFormData): void
}>()

const onSubmit = () => {
  emit('submit', { ...form.value, username: form.value.username.trim() })
}
</script>
