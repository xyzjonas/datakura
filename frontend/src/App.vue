<template>
  <MainLayout>
    <RouterView v-slot="{ Component }" :key="$route.path">
      <Suspense>
        <component :is="Component" />
        <template #fallback>
          <span>...loading</span>
        </template>
      </Suspense>
    </RouterView>
  </MainLayout>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import MainLayout from './components/layout/MainLayout.vue'
import { client } from './client/client.gen'
import { getCsrfFromCookie, getCsrfToken } from './utils/csrf'

onMounted(() => {
  let csrfToken
  if (import.meta.env.MODE === 'development') {
    console.warn('Getting CSRF token from the cookie - should not happen in production!')
    csrfToken = getCsrfFromCookie()
    console.info(`CSRF token (from cookie): ${csrfToken}`)
  } else {
    csrfToken = getCsrfToken()
    console.debug(`CSRF token (SSR): ${csrfToken ? 'YES' : 'MISSING!'}`)
  }

  client.setConfig({
    headers: {
      'X-CSRFToken': csrfToken ?? 'not-set',
    },
  })
})
</script>

<style lang="scss">
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
