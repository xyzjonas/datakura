<template>
  <div class="flex flex-col gap-3 w-full">
    <div class="flex items-center">
      <h1 class="text-3xl font-bold">Šarže</h1>
    </div>
    <BatchesTable />
  </div>
</template>

<script setup lang="ts">
import BatchesTable from '@/components/settings/packaging/BatchesTable.vue'
</script>

<style lang="scss" scoped></style>
