<template>
  <q-btn
    dense
    flat
    round
    size="10px"
    icon="sym_o_open_in_new"
    :to="{ name: 'warehouseItemDetail', params: { itemId } }"
  >
    <q-tooltip :offset="[0, 10]">Zobrazit detail skladové položky</q-tooltip>
  </q-btn>
</template>

<script setup lang="ts">
defineProps<{ itemId: number }>()
</script>

<style lang="scss" scoped></style>
