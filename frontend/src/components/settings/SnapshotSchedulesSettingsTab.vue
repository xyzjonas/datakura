<template>
  <div>
    <h1 class="mb-1">STAV SKLADU</h1>
    <p class="mb-5 text-sm text-muted">
      Automatické ukládání stavu skladu podle plánu. Plánů lze nastavit libovolný počet.
    </p>
    <SnapshotSchedulesTable />
  </div>
</template>

<script setup lang="ts">
import SnapshotSchedulesTable from './snapshot-schedules/SnapshotSchedulesTable.vue'
</script>
