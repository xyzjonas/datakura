<template>
  <q-badge :color="color"><q-icon :name="icon" class="mr-1" size="14px" />{{ label }}</q-badge>
</template>

<script setup lang="ts">
import type { TrackingLevel } from '@/client'
import { computed } from 'vue'

const props = defineProps<{ level: TrackingLevel | string }>()

const label = computed(() => {
  switch (props.level) {
    case 'SERIALIZED_PACKAGE':
      return 'Balení'
    case 'BATCH':
      return 'Šarže'
    case 'SERIALIZED_PIECE':
      return 'Kus'
    default:
      return 'Nesledováno'
  }
})

const color = computed(() => {
  switch (props.level) {
    case 'SERIALIZED_PACKAGE':
      return 'primary'
    case 'BATCH':
      return 'purple'
    case 'SERIALIZED_PIECE':
      return 'green'
    default:
      return 'gray'
  }
})
const icon = computed(() => {
  switch (props.level) {
    case 'SERIALIZED_PACKAGE':
      return 'sym_o_package_2'
    case 'BATCH':
      return 'sym_o_barcode'
    case 'SERIALIZED_PIECE':
      return 'sym_o_looks_one'
    default:
      return 'sym_o_crop_free'
  }
})
</script>

<style lang="scss" scoped></style>
