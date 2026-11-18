<template>
  <q-btn
    v-if="selection"
    flat
    no-caps
    :color="selection.active.value ? 'warning' : 'primary'"
    icon="sym_o_assignment_return"
    label="vratka"
    :disable="disabled"
    data-test="return-toggle"
    @click="selection.active.value ? selection.reset() : (selection.active.value = true)"
  >
    <q-tooltip>Přijmout zboží zpět od zákazníka</q-tooltip>
  </q-btn>
</template>

<script setup lang="ts">
import { useReturnSelection } from '@/composables/use-return-selection'

defineProps<{ disabled?: boolean }>()

const selection = useReturnSelection()
</script>
