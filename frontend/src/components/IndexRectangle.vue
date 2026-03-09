<template>
  <span
    class="font-mono text-lg border light:border-gray-3 dark:border-gray-5 aspect-ratio-square grid content-center justify-center rounded w-8"
    >{{ index }}</span
  >
</template>

<script setup lang="ts">
defineProps<{
  index: number
  size?: string
}>()
</script>

<style lang="scss" scoped></style>
