<template>
  <section class="flex flex-col gap-3">
    <h2 class="text-lg font-semibold uppercase">Normy a celní nomenklatura</h2>
    <p class="text-muted max-w-3xl">
      Doplní produktům normu (DIN, ISO, ČSN) a celní nomenklaturu z importovaných atributů. Při více
      normách se jako hlavní použije DIN, ostatní se uloží jako ekvivalenty. Již vyplněné hodnoty se
      nepřepisují, takže spuštění lze bezpečně opakovat.
    </p>

    <div class="flex items-center gap-4">
      <q-btn
        color="primary"
        unelevated
        icon="sym_o_rule_settings"
        label="doplnit normy"
        data-test="norm-backfill-start"
        :loading="running"
        :disable="running"
        @click="start"
      />
      <q-btn
        v-if="status && !running"
        flat
        dense
        label="skrýt výsledek"
        data-test="norm-backfill-dismiss"
        @click="dismiss"
      />
    </div>

    <q-card v-if="status" flat bordered class="rounded-md">
      <div class="p-4 flex flex-col gap-3">
        <template v-if="status.state === 'pending'">
          <q-linear-progress indeterminate rounded size="10px" />
          <span class="text-muted text-sm" data-test="norm-progress">
            Úloha čeká ve frontě na zpracování...
          </span>
        </template>

        <template v-else-if="status.state === 'running'">
          <q-linear-progress :value="(status.percent ?? 0) / 100" rounded size="10px" />
          <div class="flex items-center gap-3 text-sm" data-test="norm-progress">
            <strong>{{ (status.percent ?? 0).toFixed(1) }} %</strong>
            <span class="text-muted">
              zpracováno {{ status.stage_done }} z {{ status.stage_total }} produktů
            </span>
          </div>
        </template>

        <q-banner
          v-else-if="status.state === 'failed'"
          rounded
          class="bg-negative/15"
          data-test="norm-error"
        >
          {{ status.error }}
        </q-banner>

        <NormBackfillResult v-else-if="status.result" :result="status.result" />
      </div>
    </q-card>
  </section>
</template>

<script setup lang="ts">
import { useNormBackfillJob } from '@/composables/use-norm-backfill-job'
import NormBackfillResult from './NormBackfillResult.vue'

const { status, running, start, dismiss } = useNormBackfillJob()
</script>
