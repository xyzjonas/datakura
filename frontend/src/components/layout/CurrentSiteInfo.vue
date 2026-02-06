<template>
  <q-select v-model="activeSite" :options="['Centrála', 'Nosek']" outlined dense>
    <template #prepend>
      <q-icon name="sym_o_home_work" />
    </template>
  </q-select>
</template>

<script setup lang="ts">
import { useAuth } from '@/composables/use-auth'
import { ref, watch } from 'vue'

const { user, switchSite } = useAuth()

const activeSite = ref<string | undefined | null>(user.value.active_site)

watch(activeSite, async (value) => {
  await switchSite(value ?? undefined)
})
</script>

<style lang="scss" scoped></style>
