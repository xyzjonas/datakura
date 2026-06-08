<template>
  <q-badge color="primary">
    <q-icon name="sym_o_barcode" class="mr-1" size="14px" />
    {{ batchCode ?? '-' }}
    <q-tooltip>
      <strong>Šarže</strong> umožňuje seskupovat zboží podle výrobních dávek, sledovat expirace nebo
      jednoduše organizovat skladové zásoby.</q-tooltip
    >
  </q-badge>
</template>

<script setup lang="ts">
defineProps<{ batchCode?: string }>()
</script>

<style lang="scss" scoped></style>
