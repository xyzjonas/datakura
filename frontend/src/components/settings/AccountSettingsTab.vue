<template>
  <div>
    <h1 class="mb-2">MŮJ ÚČET</h1>
    <p class="mb-5 text-muted max-w-3xl">Informace o vašem účtu a změna hesla.</p>

    <div class="flex flex-col gap-5">
      <section class="p-4">
        <h2 class="text-lg font-semibold uppercase mb-3">Profilový obrázek</h2>
        <AvatarEditor />
      </section>

      <div class="flex gap-3">
        <ForegroundPanel class="mb-5 flex-[2]">
          <h2 class="text-lg font-semibold uppercase mb-3">Informace o účtu</h2>
          <q-list separator class="rounded overflow-hidden">
            <q-item v-for="row in info" :key="row.label">
              <q-item-section>
                <q-item-label caption>{{ row.label }}</q-item-label>
                <q-item-label>{{ row.value }}</q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </ForegroundPanel>

        <ForegroundPanel class="mb-5 flex-1">
          <h2 class="text-lg font-semibold uppercase mb-3">Změna hesla</h2>
          <ChangePasswordForm />
        </ForegroundPanel>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAuth } from '@/composables/use-auth'
import AvatarEditor from '@/components/user/AvatarEditor.vue'
import { formatDateTimeLong } from '@/utils/date'
import { roleLabel } from '@/utils/role-label'
import { computed } from 'vue'
import ChangePasswordForm from './account/ChangePasswordForm.vue'
import ForegroundPanel from '../ForegroundPanel.vue'

const { user } = useAuth()

const formatDate = (value?: string | null) => (value ? formatDateTimeLong(new Date(value)) : '-')

const info = computed(() => [
  { label: 'Uživatelské jméno', value: user.value.username ?? '-' },
  {
    label: 'Jméno',
    value: `${user.value.first_name ?? ''} ${user.value.last_name ?? ''}`.trim() || '-',
  },
  { label: 'E-mail', value: user.value.email || '-' },
  { label: 'Role', value: roleLabel(user.value.group) },
  { label: 'Účet vytvořen', value: formatDate(user.value.date_joined) },
  { label: 'Poslední přihlášení', value: formatDate(user.value.last_login) },
])
</script>
