<template>
  <MainLayout>
    <RouterView v-slot="{ Component }" :key="$route.path">
      <Suspense>
        <div class="flex flex-1">
          <component :is="Component" />
        </div>
        <template #fallback>
          <div class="grid justify-center content-center text-center flex-1">
            <q-spinner size="86px" :thickness="2" color="primary"></q-spinner>
          </div>
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
import { useRouter } from 'vue-router'

const showWhatsNewDialog = ref(false)
const { pendingChangelogEntries } = useVersion()
const { currentRoute } = useRouter()

const showOrNotToShow = () => {
  if (currentRoute.value.name === 'logout' || currentRoute.value.name === 'login') {
    // Don't show the dialog if we're already on the release notes page
    showWhatsNewDialog.value = false
    return
  }
  showWhatsNewDialog.value = pendingChangelogEntries.value.length > 0
}

onMounted(() => {
  setTimeout(showOrNotToShow, 2000)

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
