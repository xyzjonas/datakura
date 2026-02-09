<template>
  <div class="flex gap-2 flex-nowrap">
    <div class="flex flex-col items-end flex-nowrap">
      <span class="light:text-primary font-bold dark:text-light capitalize">{{
        user.username
      }}</span>
      <span class="text-xs text-gray-5 capitalize">{{ user.group ?? 'Anonym' }}</span>
    </div>
    <!-- <q-avatar rounded size="36px" class="rounded-full">
      <img
        src="https://static.vecteezy.com/system/resources/thumbnails/029/640/896/small_2x/side-view-of-a-handsome-young-man-face-on-white-background-generative-ai-free-photo.jpeg"
      />
    </q-avatar> -->
    <q-btn size="small" flat dense icon="sym_o_more_vert">
      <q-menu>
        <q-list>
          <q-item clickable v-close-popup @click="signout">
            <q-item-section avatar><q-icon name="logout"></q-icon></q-item-section>
            <q-item-section>Odhlásit</q-item-section>
          </q-item>
          <q-item clickable v-close-popup href="/admin">
            <q-item-section avatar
              ><q-icon name="sym_o_admin_panel_settings"></q-icon
            ></q-item-section>
            <q-item-section>Administrace</q-item-section>
          </q-item>
        </q-list>
      </q-menu>
    </q-btn>
  </div>
</template>

<script setup lang="ts">
import { useAuth } from '@/composables/use-auth'

const { user, signout } = useAuth()
</script>

<style lang="scss" scoped></style>
