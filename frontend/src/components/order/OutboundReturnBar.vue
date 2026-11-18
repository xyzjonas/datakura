<template>
  <div
    v-if="selection?.active.value"
    class="flex items-center gap-3 px-4 py-3 border-0 border-b border-solid border-amber light:bg-amber-1 dark:bg-amber-9/20"
    data-test="return-bar"
  >
    <q-icon name="sym_o_assignment_return" size="sm" color="warning" />
    <div class="flex flex-col">
      <span class="font-semibold">
        Vratka: {{ selection.count.value ? `vybráno ${selection.count.value}` : 'nic nevybráno' }}
        <template v-if="selection.count.value">
          {{ selection.count.value === 1 ? 'položka' : 'položek' }}
        </template>
      </span>
      <span class="text-xs text-gray-6">
        U položek zvolte „vrátit“ a množství. Změny se uloží až tlačítkem „použít“.
      </span>
    </div>
    <span v-if="selection.count.value" class="ml-auto tabular-nums" data-test="return-value">
      Hodnota vratky: <strong>{{ formatDecimal(value) }}</strong> {{ currency }}
    </span>
    <div :class="['flex gap-2', selection.count.value ? '' : 'ml-auto']">
      <q-btn
        flat
        color="negative"
        label="zrušit"
        data-test="return-cancel"
        @click="selection.reset()"
      />
      <q-btn
        unelevated
        color="primary"
        label="použít"
        :disable="!selection.count.value"
        :loading="loading"
        data-test="return-apply"
        @click="emit('apply')"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useReturnSelection } from '@/composables/use-return-selection'
import { formatDecimal } from '@/utils/format-number'

const emit = defineEmits<{ (e: 'apply'): void }>()

defineProps<{ value: number; currency: string; loading?: boolean }>()

const selection = useReturnSelection()
</script>
