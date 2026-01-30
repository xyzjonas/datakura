<template>
  <q-page padding class="grid content-center justify-center w-full">
    <foreground-panel class="md:w-xl">
      <q-form @submit="postLogin" autofocus class="text-center md:mx-10 my-25 flex flex-col">
        <h1 class="uppercase mb-3">Přihlášení</h1>
        <h2 class="mb-15 text-gray-5">Použíjte lokální účet pro přihlášení.</h2>

        <div class="flex flex-col gap-3">
          <q-input
            outlined
            label="E-mail"
            hint="Váš email"
            v-model="email"
            type="text"
            :rules="[rules.notEmpty]"
            autocomplete="username"
          />
          <q-input
            outlined
            label="Heslo"
            hint="Vaše bezpečné heslo"
            v-model="password"
            type="password"
            :rules="[rules.notEmpty]"
            autocomplete="current-password"
          />
          <q-btn
            unelevated
            color="primary"
            type="submit"
            class="w-full h-[3.5rem] mt-3"
            :loading="loading"
            >Přihlásit</q-btn
          >
        </div>
        <span v-if="loginFailed" class="text-negative mt-5 h-6">Přihlášení selhalo...</span>
        <span v-else class="h-6"></span>
      </q-form>
    </foreground-panel>
  </q-page>
</template>

<script setup lang="ts">
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import { useAuth } from '@/composables/use-auth'
import { rules } from '@/utils/rules'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const { signin } = useAuth()
const router = useRouter()
const route = useRoute()

const email = ref<string>('')
const password = ref<string>('')
const loading = ref(false)
const loginFailed = ref(false)
const postLogin = () => {
  loading.value = true
  signin(email.value, password.value)
    .then((isSuccess) => {
      if (!isSuccess) {
        loginFailed.value = true
        return
      }
      if (route.query.redirect) {
        const decodedRoute = JSON.parse(decodeURIComponent(route.query.redirect as string))
        router.push(decodedRoute)
      } else {
        router.push({ name: 'home' })
      }
    })
    .finally(() => (loading.value = false))
}
</script>
