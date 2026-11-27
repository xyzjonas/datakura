<template>
  <div class="flex flex-col gap-2">
    <ListRow
      v-for="(field, index) in model"
      :key="index"
      :index="index"
      :count="model.length"
      data-test="field"
      @move="move(index, $event)"
      @remove="remove(index)"
    >
      <CompositeFieldEditor v-if="isComposite(field)" :model-value="field" :options="options" />
      <FieldPartEditor v-else :model-value="field" :options="options" />
    </ListRow>
    <p v-if="!model.length" class="m-0 text-sm text-muted">Nic není vybráno.</p>
    <AddValueBar
      :options="options"
      composite
      @attribute="addAttribute"
      @static="addStatic"
      @composite="addComposite"
    />
  </div>
</template>

<script setup lang="ts">
import type { CatalogFieldSchema, LayoutFieldSchema } from '@/client'
import AddValueBar from './AddValueBar.vue'
import CompositeFieldEditor from './CompositeFieldEditor.vue'
import FieldPartEditor from './FieldPartEditor.vue'
import ListRow from './ListRow.vue'

const props = defineProps<{ options: CatalogFieldSchema[] }>()
const model = defineModel<LayoutFieldSchema[]>({ required: true })

// an empty composite stays one, so parts can be added to it
const isComposite = (field: LayoutFieldSchema) =>
  Array.isArray(field.parts) && !field.key && !field.text

const append = (field: LayoutFieldSchema) => {
  model.value = [...model.value, field]
}
const addAttribute = (option: CatalogFieldSchema) =>
  append({ key: option.key, label: option.label })
const addStatic = () => append({ text: 'text', show_label: false })
// the first two attributes as a start (the picker changes them); caption hidden by default
const addComposite = () =>
  append({
    show_label: false,
    direction: 'row',
    separator: ', ',
    parts: props.options
      .slice(0, 2)
      .map((o) => ({ key: o.key, label: o.label, show_label: false })),
  })
const remove = (index: number) => {
  model.value = model.value.filter((_, i) => i !== index)
}
const move = (index: number, by: -1 | 1) => {
  const next = [...model.value]
  const [moved] = next.splice(index, 1)
  next.splice(index + by, 0, moved!)
  model.value = next
}
</script>
