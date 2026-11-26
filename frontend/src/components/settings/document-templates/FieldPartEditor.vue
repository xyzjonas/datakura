<template>
  <div class="flex flex-col gap-1">
    <q-input
      v-if="isStatic"
      v-model="model.text"
      outlined
      dense
      hide-bottom-space
      label="Text"
      maxlength="200"
      data-test="static-text"
    />
    <q-input
      v-if="!isStatic || model.show_label !== false"
      v-model="model.label"
      outlined
      dense
      hide-bottom-space
      :label="isStatic ? 'Popisek' : (labelOf(model.key) ?? model.key)"
      placeholder="bez popisku"
      :disable="model.show_label === false"
      maxlength="100"
      data-test="field-label"
    />
    <FieldOptions :model-value="model" :hide-barcode="model.key === 'logo'" />
  </div>
</template>

<script setup lang="ts">
import type { CatalogFieldSchema, LayoutPartSchema } from '@/client'
import { computed } from 'vue'
import FieldOptions from './FieldOptions.vue'

const props = defineProps<{ options: CatalogFieldSchema[] }>()
// a catalog attribute (key) or a static text
const model = defineModel<LayoutPartSchema>({ required: true })

const isStatic = computed(() => !model.value.key)
const labelOf = (key?: string) => props.options.find((o) => o.key === key)?.label
</script>
