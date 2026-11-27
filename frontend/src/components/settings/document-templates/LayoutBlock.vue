<template>
  <q-expansion-item
    group="layout-blocks"
    dense-toggle
    header-class="font-semibold"
    class="overflow-hidden rounded-md border border-solid border-gray-300 bg-white"
  >
    <template #header>
      <q-item-section>{{ title }}</q-item-section>
      <q-item-section v-if="toggleable" side @click.stop>
        <q-toggle v-model="enabled" dense data-test="block-enabled" />
      </q-item-section>
    </template>
    <div class="flex flex-col gap-3 p-3 pt-1" :class="{ 'opacity-50': toggleable && !enabled }">
      <slot />
    </div>
  </q-expansion-item>
</template>

<script setup lang="ts">
defineProps<{ title: string; toggleable?: boolean }>()
const enabled = defineModel<boolean>('enabled', { default: true })
</script>
