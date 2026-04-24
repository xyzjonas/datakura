<template>
  <div>
    <h1 class="mb-5">APLIKACE</h1>
    <q-list bordered separator class="rounded-xl overflow-hidden max-w-lg">
      <q-item tag="label">
        <q-item-section>
          <q-item-label>Režim čtečky (scanner mode)</q-item-label>
          <q-item-label caption>
            Optimalizuje výběr skladové položky pro Zebra / ruční čtečku čárových kódů
          </q-item-label>
        </q-item-section>
        <q-item-section side>
          <q-toggle v-model="scannerMode" color="primary" />
        </q-item-section>
      </q-item>
    </q-list>
    <div class="mt-3 ml-3 text-caption text-muted">
      Aktuální režim:
      <q-badge :color="scannerMode ? 'secondary' : 'primary'">
        {{ scannerMode ? 'čtečka' : 'webové rozhraní' }}
      </q-badge>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAppSettings } from '@/composables/use-app-settings'

const { scannerMode } = useAppSettings()
</script>
