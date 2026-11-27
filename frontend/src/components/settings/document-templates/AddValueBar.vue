<template>
  <div class="mt-1 flex items-center gap-1">
    <q-select
      :model-value="null"
      :options="options"
      option-value="key"
      option-label="label"
      outlined
      dense
      hide-bottom-space
      label="Přidat údaj"
      class="flex-1"
      data-test="add-field"
      @update:model-value="(o: CatalogFieldSchema | null) => o && emit('attribute', o)"
    />
    <q-btn
      flat
      dense
      icon="sym_o_text_fields"
      label="Text"
      data-test="add-static"
      @click="emit('static')"
    />
    <q-btn
      v-if="composite"
      flat
      dense
      icon="sym_o_join"
      label="Složený"
      data-test="add-composite"
      @click="emit('composite')"
    />
  </div>
</template>

<script setup lang="ts">
import type { CatalogFieldSchema } from '@/client'

defineProps<{ options: CatalogFieldSchema[]; composite?: boolean }>()
const emit = defineEmits<{
  attribute: [option: CatalogFieldSchema]
  static: []
  composite: []
}>()
</script>
