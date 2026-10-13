<template>
  <q-form class="flex flex-col gap-3" @submit="onSubmit">
    <q-input
      v-model="currentPassword"
      outlined
      type="password"
      label="Současné heslo"
      autocomplete="current-password"
      :rules="[rules.notEmpty]"
    />
    <q-input
      v-model="newPassword"
      outlined
      type="password"
      label="Nové heslo"
      autocomplete="new-password"
      :rules="[rules.notEmpty]"
    />
    <q-input
      v-model="newPasswordRepeat"
      outlined
      type="password"
      label="Nové heslo znovu"
      autocomplete="new-password"
      :rules="[rules.notEmpty, (val: string) => val === newPassword || 'Hesla se neshodují']"
    />
    <div class="flex justify-end">
      <q-btn
        type="submit"
        unelevated
        color="primary"
        label="změnit heslo"
        :loading="saving"
        class="h-[3rem] min-w-[10rem]"
      />
    </div>
  </q-form>
</template>

<script setup lang="ts">
import { warehouseApiRoutesAuthChangePassword } from '@/client'
import { useApi } from '@/composables/use-api'
import { rules } from '@/utils/rules'
import { useQuasar } from 'quasar'
import { ref } from 'vue'

const { onResponse } = useApi()
const $q = useQuasar()

const currentPassword = ref('')
const newPassword = ref('')
const newPasswordRepeat = ref('')
const saving = ref(false)

const onSubmit = async () => {
  saving.value = true
  try {
    const result = await warehouseApiRoutesAuthChangePassword({
      body: { current_password: currentPassword.value, new_password: newPassword.value },
    })
    if (onResponse(result)) {
      $q.notify({ message: 'Heslo bylo změněno', type: 'positive' })
      currentPassword.value = ''
      newPassword.value = ''
      newPasswordRepeat.value = ''
    }
  } finally {
    saving.value = false
  }
}
</script>
