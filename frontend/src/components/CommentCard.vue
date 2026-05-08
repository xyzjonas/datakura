<template>
  <ForegroundPanel class="border-primary border-l-5">
    <div class="flex gap-2 items-start flex-nowrap">
      <q-icon name="sym_o_sticky_note_2" color="primary" size="sm" class="translate-y-1" />
      <div>
        <span class="text-muted">{{ title }}</span>
        <div>
          <slot></slot>
        </div>
      </div>
    </div>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import ForegroundPanel from './ForegroundPanel.vue'

withDefaults(defineProps<{ title?: string }>(), {
  title: 'Komentář k objednávce',
})
</script>

<style lang="scss" scoped></style>
