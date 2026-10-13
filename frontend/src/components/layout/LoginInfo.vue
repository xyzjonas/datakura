<template>
  <div class="flex gap-2 flex-nowrap">
    <div class="flex flex-col items-end flex-nowrap">
      <span class="light:text-primary font-bold dark:text-light capitalize">{{
        user.username
      }}</span>
      <span class="text-xs text-muted">{{ roleLabel(user.group) }}</span>
    </div>
    <UserAvatar :username="user.username" :url="user.avatar_url" />
    <q-btn size="small" flat dense icon="sym_o_more_vert">
      <q-menu>
        <q-list>
          <q-item>
            <q-item-section>
              <div class="flex flex-col">
                <span class="text-xs text-gray-5">Přihlášení vyprší</span>
                <span>{{ expiryDate ? formatDateTimeLong(expiryDate) : 'N/A' }}</span>
              </div>
            </q-item-section>
          </q-item>
          <q-separator></q-separator>
          <q-item
            v-for="link in settingsLinks"
            :key="link.tab"
            clickable
            v-close-popup
            :to="{ name: 'settings', query: { tab: link.tab } }"
            class="light:text-dark dark:text-light"
          >
            <q-item-section avatar><q-icon :name="link.icon"></q-icon></q-item-section>
            <q-item-section>{{ link.label }}</q-item-section>
          </q-item>
          <q-separator></q-separator>
          <q-item clickable v-close-popup href="/admin">
            <q-item-section avatar
              ><q-icon name="sym_o_admin_panel_settings"></q-icon
            ></q-item-section>
            <q-item-section>Administrace</q-item-section>
          </q-item>
          <q-item clickable v-close-popup @click="signout">
            <q-item-section avatar><q-icon name="logout"></q-icon></q-item-section>
            <q-item-section>Odhlásit</q-item-section>
          </q-item>
        </q-list>
      </q-menu>
    </q-btn>
  </div>
</template>

<script setup lang="ts">
import { useAuth } from '@/composables/use-auth'
import UserAvatar from '@/components/user/UserAvatar.vue'
import { formatDateTimeLong } from '@/utils/date'
import { roleLabel } from '@/utils/role-label'
import { computed } from 'vue'

const { user, expiryDate, signout } = useAuth()

const settingsLinks = computed(() => [
  { tab: 'account', label: 'Můj profil', icon: 'sym_o_account_circle' },
  ...(user.value.is_superuser
    ? [{ tab: 'users', label: 'Správa uživatelů', icon: 'sym_o_manage_accounts' }]
    : []),
  { tab: 'app', label: 'Přizpůsobení aplikace', icon: 'sym_o_settings' },
])
</script>

<style lang="scss" scoped></style>
