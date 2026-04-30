<template>
  <MainLayout>
    <RouterView v-slot="{ Component }" :key="$route.path">
      <Suspense>
        <div class="flex flex-1">
          <component :is="Component" />
        </div>
        <template #fallback>
          <span>...loading</span>
        </template>
      </Suspense>
    </RouterView>
  </MainLayout>

  <ReleaseNotesDialog v-model:show="showWhatsNewDialog" />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import MainLayout from './components/layout/MainLayout.vue'
import { client } from './client/client.gen'
import { getCsrfFromCookie, getCsrfToken } from './utils/csrf'
import ReleaseNotesDialog from '@/components/ReleaseNotesDialog.vue'
import { useVersion } from './utils/version'

const showWhatsNewDialog = ref(false)
const { pendingChangelogEntries } = useVersion()

onMounted(() => {
  showWhatsNewDialog.value = pendingChangelogEntries.value.length > 0

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

.list-enter-active,
.list-leave-active {
  transition: all 0.4s ease;
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateX(100px);
}
</style>
