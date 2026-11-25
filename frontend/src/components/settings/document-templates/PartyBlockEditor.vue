<template>
  <LayoutBlock v-model:enabled="model.enabled" :title="heading" toggleable>
    <q-input
      v-model="model.title"
      outlined
      dense
      hide-bottom-space
      label="Nadpis bloku"
      maxlength="100"
      data-test="party-title"
    />
    <FieldListEditor v-model="model.fields" :options="options" />
  </LayoutBlock>
</template>

<script setup lang="ts">
import type { CatalogFieldSchema, PartyBlockSchema } from '@/client'
import FieldListEditor from './FieldListEditor.vue'
import LayoutBlock from './LayoutBlock.vue'

defineProps<{ heading: string; options: CatalogFieldSchema[] }>()
const model = defineModel<Required<PartyBlockSchema>>({ required: true })
</script>
