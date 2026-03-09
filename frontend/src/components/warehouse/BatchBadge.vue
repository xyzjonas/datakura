<template>
  <q-badge color="primary"
    ><q-icon name="sym_o_barcode" class="mr-1" size="14px" />{{ batchCode ?? '-' }}</q-badge
  >
</template>

<script setup lang="ts">
defineProps<{ batchCode?: string }>()
</script>

<style lang="scss" scoped></style>
