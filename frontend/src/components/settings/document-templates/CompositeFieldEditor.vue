<template>
  <div class="flex flex-col gap-1">
    <q-input
      v-model="model.label"
      outlined
      dense
      hide-bottom-space
      label="Složený údaj - popisek"
      placeholder="bez popisku"
      :disable="model.show_label === false"
      maxlength="100"
      data-test="field-label"
    />
    <FieldOptions :model-value="model" hide-barcode />
    <div class="flex items-center gap-1">
      <q-btn
        flat
        dense
        round
        size="sm"
        :icon="model.direction === 'column' ? 'sym_o_table_rows' : 'sym_o_view_column'"
        data-test="toggle-direction"
        @click="model.direction = model.direction === 'column' ? 'row' : 'column'"
      >
        <q-tooltip>{{
          model.direction === 'column' ? 'Pod sebou (sloupec)' : 'Vedle sebe (řádek)'
        }}</q-tooltip>
      </q-btn>
      <q-input
        v-if="model.direction !== 'column'"
        v-model="model.separator"
        outlined
        dense
        hide-bottom-space
        label="Oddělovač"
        class="w-28"
        maxlength="10"
        data-test="separator"
      />
    </div>
    <div class="flex flex-col gap-2 border-0 border-l-2 border-solid border-gray-300 pl-2">
      <ListRow
        v-for="(part, index) in parts"
        :key="index"
        :index="index"
        :count="parts.length"
        data-test="part"
        @move="move(index, $event)"
        @remove="remove(index)"
      >
        <FieldPartEditor :model-value="part" :options="options" />
      </ListRow>
      <AddValueBar :options="options" @attribute="addAttribute" @static="addStatic" />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { CatalogFieldSchema, LayoutFieldSchema, LayoutPartSchema } from '@/client'
import { computed } from 'vue'
import AddValueBar from './AddValueBar.vue'
import FieldOptions from './FieldOptions.vue'
import FieldPartEditor from './FieldPartEditor.vue'
import ListRow from './ListRow.vue'

defineProps<{ options: CatalogFieldSchema[] }>()
const model = defineModel<LayoutFieldSchema>({ required: true })

// the parts' own captions are hidden by default, like the composite's
const parts = computed({
  get: () => model.value.parts ?? [],
  set: (value: LayoutPartSchema[]) => {
    model.value.parts = value
  },
})

const addAttribute = (option: CatalogFieldSchema) => {
  parts.value = [...parts.value, { key: option.key, label: option.label, show_label: false }]
}
const addStatic = () => {
  parts.value = [...parts.value, { text: 'text', show_label: false }]
}
const remove = (index: number) => {
  parts.value = parts.value.filter((_, i) => i !== index)
}
const move = (index: number, by: -1 | 1) => {
  const next = [...parts.value]
  const [moved] = next.splice(index, 1)
  next.splice(index + by, 0, moved!)
  parts.value = next
}
</script>
