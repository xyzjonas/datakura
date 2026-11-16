<template>
  <div class="flex flex-col" data-test="toggle-row">
    <q-toggle v-model="modelValue" :label="label" class="font-medium translate-x-[-4px]" />
    <span class="text-xs text-muted">{{ description }}</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{ label: string; description: string }>()

const modelValue = defineModel<boolean>({ default: false })
</script>
