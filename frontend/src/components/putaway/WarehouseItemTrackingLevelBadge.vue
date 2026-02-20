<template>
  <q-badge :class="['text-xs', color]">
    <q-icon :name="icon" class="mr-1" size="14px"></q-icon>
    {{ label }}
  </q-badge>
</template>

<script setup lang="ts">
import type { TrackingLevel } from '@/client'
import { computed } from 'vue'

const props = defineProps<{ level: TrackingLevel }>()

const color = computed(() => {
  switch (props.level) {
    case 'SERIALIZED_PACKAGE':
      return 'bg-primary'
    case 'SERIALIZED_PIECE':
      return 'bg-primary'
    case 'BATCH':
      return 'bg-accent'
    default:
      return 'bg-gray-5'
  }
})

const icon = computed(() => {
  switch (props.level) {
    case 'SERIALIZED_PACKAGE':
      return 'sym_o_package_2'
    case 'SERIALIZED_PIECE':
      return 'sym_o_counter_1'
    case 'BATCH':
      return 'sym_o_auto_awesome_motion'
    default:
      return 'sym_o_activity_zone'
  }
})

const label = computed(() => {
  switch (props.level) {
    case 'SERIALIZED_PACKAGE':
      return 'Balení'
    case 'SERIALIZED_PIECE':
      return 'Kus'
    case 'BATCH':
      return 'Šarže'
    default:
      return 'Volně skladem'
  }
})
</script>
