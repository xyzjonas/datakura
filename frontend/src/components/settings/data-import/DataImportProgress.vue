<template>
  <q-card flat bordered class="rounded-md">
    <div class="p-4 flex flex-col gap-3">
      <div class="flex items-center gap-3">
        <h2 class="text-lg font-semibold uppercase">Průběh importu</h2>
        <q-space />
        <q-btn
          v-if="status.state === 'pending'"
          flat
          dense
          size="sm"
          label="přestat sledovat"
          data-test="stop-watching"
          @click="emit('stop')"
        />
      </div>

      <template v-if="status.state === 'pending'">
        <q-linear-progress indeterminate rounded size="10px" />
        <span class="text-muted text-sm" data-test="progress-label">
          Import čeká ve frontě na zpracování...
        </span>
      </template>

      <template v-else-if="status.state === 'running'">
        <q-linear-progress :value="fraction" rounded size="10px" color="primary" />
        <div class="flex items-center gap-3 text-sm" data-test="progress-label">
          <strong>{{ percentLabel }}</strong>
          <span>{{ stageLabel }}</span>
          <span v-if="status.stage_total" class="text-muted">
            zbývá {{ remaining }} z {{ status.stage_total }} záznamů
          </span>
        </div>
      </template>

      <q-banner
        v-else-if="status.state === 'failed'"
        rounded
        class="bg-negative/15"
        data-test="progress-error"
      >
        <div class="font-semibold mb-1">Import selhal, žádná data nebyla uložena.</div>
        <div class="max-h-64 overflow-auto whitespace-pre-wrap text-sm">{{ status.error }}</div>
      </q-banner>
    </div>
  </q-card>
</template>

<script setup lang="ts">
import type { DataImportJobStatusSchema } from '@/client'
import { computed } from 'vue'

const PHASE_LABELS: Record<string, string> = {
  parsing: 'načítání souboru',
  validating: 'kontrola dat',
  importing: 'ukládání',
  done: 'hotovo',
}

const props = defineProps<{ status: DataImportJobStatusSchema }>()
const emit = defineEmits<{ stop: [] }>()

const percent = computed(() => props.status.percent ?? 0)
const fraction = computed(() => percent.value / 100)
const percentLabel = computed(() => `${percent.value.toFixed(1)} %`)
const remaining = computed(() =>
  Math.max((props.status.stage_total ?? 0) - (props.status.stage_done ?? 0), 0),
)
const stageLabel = computed(() => {
  const phase = PHASE_LABELS[props.status.phase ?? ''] ?? props.status.phase ?? ''
  return [props.status.stage, phase].filter(Boolean).join(' - ')
})
</script>
