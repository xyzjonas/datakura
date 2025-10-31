<template>
  <div
    class="flex border-dashed rounded-xl border-1 light:border-gray-3 dark:border-dark-3 grid gap-3 justify-center items-center text-gray-5"
  >
    <q-icon :name="icon" size="32px"></q-icon>
    <span class="text-lg">{{ text }}</span>
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
defineProps<{ text?: string; icon?: string }>()
</script>

<style lang="scss" scoped></style>
