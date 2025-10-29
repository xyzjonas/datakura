<template>
  <div
    class="flex h-md w-full border-dashed rounded-xl border-1 light:border-gray-3 dark:border-dark-3 mt-5 flex flex-col gap-3 justify-center items-center text-gray-5"
  >
    <q-icon :name="icon" size="32px"></q-icon>
    <span class="text-lg">{{ text }}</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{ text: string; icon: string }>()
</script>

<style lang="scss" scoped></style>
