<template>
  <q-toggle v-model="hidden" size="sm" data-test="hide-manufacturing">
    <span class="text-xs">Skrýt výrobu</span>
  </q-toggle>
</template>

<script setup lang="ts">
const hidden = defineModel<boolean>({ default: false })
</script>
