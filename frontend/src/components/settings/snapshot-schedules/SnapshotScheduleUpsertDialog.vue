<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-full max-w-lg">
      <div class="p-4">
        <div class="w-full flex items-center mb-4 gap-2">
          <span class="text-2xl uppercase">{{ title }}</span>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>

        <q-form class="flex flex-col gap-3" @submit="onSubmit">
          <q-input
            v-model.trim="form.name"
            outlined
            label="Název"
            :rules="[rules.notEmpty]"
            hint="Jednoznačný název plánu"
          />

          <q-btn-toggle
            v-model="form.mode"
            unelevated
            spread
            no-caps
            toggle-color="primary"
            :options="modeOptions"
            class="border border-solid border-gray-3"
          />

          <div v-if="form.mode === 'day_of_month'" class="flex flex-col gap-1">
            <q-date
              v-model="calendarDate"
              minimal
              flat
              :navigation-min-year-month="CALENDAR_NAV_YEAR_MONTH"
              :navigation-max-year-month="CALENDAR_NAV_YEAR_MONTH"
              class="w-full border border-solid border-gray-3 [&_.q-date__navigation]:hidden"
            />
            <p class="text-sm">
              Stav skladu se uloží každého <strong>{{ form.day_of_month }}.</strong> dne v měsíci.
            </p>
            <p v-if="(form.day_of_month ?? 0) > 28" class="text-xs text-muted">
              V kratších měsících, které tento den nemají, se stav skladu neuloží. Pro vždy poslední
              den zvolte „Poslední den v měsíci“.
            </p>
          </div>
          <p v-else class="text-sm text-muted">
            Stav skladu se uloží poslední den každého měsíce, bez ohledu na jeho délku.
          </p>

          <q-input
            v-model="time"
            outlined
            type="time"
            label="Čas"
            hint="Čas spuštění"
            :rules="[rules.notEmpty]"
          />

          <q-toggle v-model="form.enabled" label="Aktivní" />

          <div class="mt-2 flex justify-end">
            <q-btn
              type="submit"
              unelevated
              color="primary"
              :loading="loading"
              :label="submitLabel"
              class="h-[3rem] min-w-[10rem]"
            />
          </div>
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import type { SnapshotScheduleCreateOrUpdateSchema } from '@/client'
import { rules } from '@/utils/rules'
import { computed } from 'vue'
import {
  CALENDAR_NAV_YEAR_MONTH,
  calendarDateToDay,
  dayToCalendarDate,
  formatTime,
  parseTime,
} from './snapshot-schedule'

const showDialog = defineModel<boolean>('show', { default: false })
const form = defineModel<SnapshotScheduleCreateOrUpdateSchema>({ required: true })

withDefaults(
  defineProps<{
    title?: string
    submitLabel?: string
    loading?: boolean
  }>(),
  {
    title: 'Plán stavu skladu',
    submitLabel: 'uložit',
    loading: false,
  },
)

const emit = defineEmits<{
  (e: 'submit', body: SnapshotScheduleCreateOrUpdateSchema): void
}>()

const modeOptions = [
  { label: 'Den v měsíci', value: 'day_of_month', icon: 'event' },
  { label: 'Poslední den v měsíci', value: 'last_day_of_month', icon: 'event_available' },
]

const calendarDate = computed<string>({
  get: () => dayToCalendarDate(form.value.day_of_month),
  set: (value) => {
    // clicking the selected day again clears the model - keep the current day
    const day = calendarDateToDay(value)
    if (day !== null) {
      form.value.day_of_month = day
    }
  },
})

const time = computed<string>({
  get: () => formatTime(form.value.hour ?? 0, form.value.minute ?? 0),
  set: (value) => {
    const parsed = parseTime(value)
    if (parsed) {
      form.value.hour = parsed.hour
      form.value.minute = parsed.minute
    }
  },
})

const onSubmit = () => {
  emit('submit', {
    ...form.value,
    name: form.value.name.trim(),
    day_of_month: form.value.mode === 'day_of_month' ? form.value.day_of_month : null,
  })
}
</script>
