<template>
  <q-dialog v-model="show" persistent>
    <q-card class="max-h-[80vh] w-[min(92vw,42rem)] flex flex-col">
      <q-card-section class="border-b border-gray-200">
        <h2 v-if="showAll">CHANGELOG</h2>
        <h2 v-else>Nový release! 🚀</h2>
        <div v-if="!showAll" class="text-lg">Co je nového?</div>
        <div v-if="!showAll" class="text-xs text-muted">
          verze <strong class="text-primary">{{ APP_VERSION }}</strong>
        </div>
      </q-card-section>

      <q-card-section class="flex-1 overflow-y-auto">
        <section v-for="entry in entries" :key="entry.version" class="mb-4 last:mb-0">
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

      <span v-if="!showAll" class="text-muted text-2xs p-2 px-3"
        >Úplný seznam změn je vždy možné zobrazit v modulu nastavení aplikace</span
      >
      <q-card-actions align="right" class="shrink-0 border-t border-gray-200 bg-white py-3">
        <q-btn
          v-if="!showAll"
          flat
          color="primary"
          label="Teď neotravuj..."
          @click="show = false"
        />
        <q-btn
          v-if="!showAll"
          color="primary"
          label="Přečteno"
          unelevated
          @click="acknowledgeWhatsNew"
          padding="6px 24px"
        />
        <q-btn v-else flat color="primary" label="Zavřít" @click="show = false" />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { useVersion, CHANGELOG_ENTRIES, APP_VERSION } from '@/utils/version'
import { computed } from 'vue'

const props = defineProps<{ showAll?: boolean }>()

const show = defineModel<boolean>('show', { required: true })

const { pendingChangelogEntries, syncLatestAcknowledgedVersion } = useVersion()

const entries = computed(() => {
  if (props.showAll) {
    return CHANGELOG_ENTRIES
  } else {
    return pendingChangelogEntries.value
  }
})

const acknowledgeWhatsNew = () => {
  syncLatestAcknowledgedVersion()
  show.value = false
}
</script>
