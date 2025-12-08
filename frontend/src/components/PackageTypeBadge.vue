<template>
  <q-badge color="primary"><q-icon :name="icon" class="mr-1" />{{ label }}</q-badge>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ packageType?: string }>()

const label = computed(() => props.packageType ?? 'Skladem volně')
const icon = computed(() => (props.packageType ? 'sym_o_package_2' : 'sym_o_crop_free'))
</script>

<style lang="scss" scoped></style>
