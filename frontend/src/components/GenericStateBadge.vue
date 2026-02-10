<template>
  <q-badge :icon="config.icon" :color="config.color" class="text-xs">
    <q-icon :name="config.icon" class="mr-1"></q-icon>
    {{ config.label }}
  </q-badge>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ state: string }>()

export interface StateConfig {
  label: string
  icon: string
  color: string
}

const unknown = computed<StateConfig>(() => ({
  color: 'grey-7',
  icon: 'question_mark',
  label: props.state,
}))

const mapping: Record<string, StateConfig> = {
  draft: {
    label: 'Koncept',
    icon: 'sym_o_ink_pen',
    color: 'grey-7',
  },
  submitted: {
    label: 'Objednáno',
    icon: 'sym_o_delivery_truck_speed',
    color: 'primary',
  },
  receiving: {
    label: 'Příjem',
    icon: 'sym_o_fact_check',
    color: 'orange-8',
  },
  putaway: {
    label: 'Naskladnění',
    icon: 'sym_o_input',
    color: 'cyan-8',
  },
  completed: {
    label: 'Dokončeno',
    icon: 'sym_o_check_circle',
    color: 'positive',
  },
  cancelled: {
    label: 'Zrušeno',
    icon: 'sym_o_block',
    color: 'negative',
  },
  confirmed: {
    label: 'Potvrzeno',
    icon: 'sym_o_check',
    color: 'positive',
  },
}

const config = computed(() => mapping[props.state] ?? unknown.value)
</script>
