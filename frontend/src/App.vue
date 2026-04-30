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

  <q-dialog v-model="showWhatsNewDialog" persistent>
    <q-card>
      <q-card-section class="border-b border-gray-200">
        <h2>Nový release! 🚀</h2>
        <div class="text-lg">Co je nového?</div>
        <div class="text-xs text-muted">
          verze <strong class="text-primary">{{ APP_VERSION }}</strong>
        </div>
      </q-card-section>

      <q-card-section class="flex-1 overflow-y-auto max-h-[60vh]">
        <section
          v-for="entry in pendingChangelogEntries"
          :key="entry.version"
          class="mb-4 last:mb-0"
        >
          <div class="flex items-center gap-2 mb-2">
            <h2 class="text-subtitle1 font-semibold">{{ entry.version }}</h2>

            <span class="text-muted text-xs">{{
              entry.releaseDate ?? 'Datum vydání neznámé'
            }}</span>
          </div>
          <ul class="list-disc pl-5">
            <li v-for="row in entry.rows" :key="row">
              {{ row }}
            </li>
          </ul>
        </section>
      </q-card-section>

      <q-card-actions align="right" class="shrink-0 border-t border-gray-200 bg-white py-3">
        <q-btn flat color="primary" label="Teď neotravuj..." @click="showWhatsNewDialog = false" />
        <q-btn color="primary" label="Potvrdit" unelevated @click="acknowledgeWhatsNew" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import MainLayout from './components/layout/MainLayout.vue'
import { client } from './client/client.gen'
import { getCsrfFromCookie, getCsrfToken } from './utils/csrf'
import { APP_VERSION, getPendingChangelogEntries, lastAcknowledgedVersion } from './utils/version'

const pendingChangelogEntries = computed(() =>
  getPendingChangelogEntries(lastAcknowledgedVersion.value),
)
const showWhatsNewDialog = ref(false)

const acknowledgeWhatsNew = () => {
  lastAcknowledgedVersion.value = APP_VERSION
  showWhatsNewDialog.value = false
}

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
