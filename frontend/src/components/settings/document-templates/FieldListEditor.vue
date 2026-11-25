<template>
  <div class="flex flex-col gap-1">
    <div v-for="(field, index) in model" :key="field.key" class="flex items-center gap-1">
      <div class="flex flex-col">
        <q-btn
          flat
          dense
          round
          size="xs"
          icon="sym_o_keyboard_arrow_up"
          :disable="index === 0"
          data-test="move-up"
          @click="move(index, -1)"
        />
        <q-btn
          flat
          dense
          round
          size="xs"
          icon="sym_o_keyboard_arrow_down"
          :disable="index === model.length - 1"
          data-test="move-down"
          @click="move(index, 1)"
        />
      </div>
      <q-input
        v-model="field.label"
        outlined
        dense
        hide-bottom-space
        class="flex-1"
        :label="labelOf(field.key)"
        :placeholder="noCaptionHint"
        maxlength="100"
        data-test="field-label"
      />
      <q-btn
        flat
        dense
        round
        size="sm"
        icon="sym_o_close"
        data-test="remove"
        @click="remove(index)"
      />
    </div>
    <p v-if="!model.length" class="m-0 text-sm text-muted">Nic není vybráno.</p>
    <q-select
      v-if="available.length"
      :model-value="null"
      :options="available"
      option-value="key"
      option-label="label"
      outlined
      dense
      hide-bottom-space
      label="Přidat údaj"
      class="mt-1"
      data-test="add-field"
      @update:model-value="add"
    />
  </div>
</template>

<script setup lang="ts">
import type { CatalogFieldSchema, LayoutFieldSchema } from '@/client'
import { computed } from 'vue'

const props = defineProps<{ options: CatalogFieldSchema[] }>()
const model = defineModel<LayoutFieldSchema[]>({ required: true })

const noCaptionHint = 'bez popisku'

const labelOf = (key: string) => props.options.find((o) => o.key === key)?.label ?? key
const available = computed(() =>
  props.options.filter((o) => !model.value.some((f) => f.key === o.key)),
)

const add = (option: CatalogFieldSchema | null) => {
  if (option) model.value = [...model.value, { key: option.key, label: option.label }]
}
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
