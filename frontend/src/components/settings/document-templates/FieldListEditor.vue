<template>
  <div class="flex flex-col gap-1">
    <div v-for="(field, index) in model" :key="index" class="flex flex-col gap-1">
      <div class="flex items-center gap-1">
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
          :label="field.parts?.length ? 'Složený údaj' : labelOf(field.key)"
          :placeholder="noCaptionHint"
          :disable="field.show_label === false"
          maxlength="100"
          data-test="field-label"
        />
        <q-btn
          flat
          dense
          round
          size="sm"
          :color="field.show_label === false ? 'grey' : 'primary'"
          :icon="field.show_label === false ? 'sym_o_label_off' : 'sym_o_label'"
          data-test="toggle-label"
          @click="field.show_label = field.show_label === false"
        >
          <q-tooltip>{{
            field.show_label === false ? 'Popisek skrytý' : 'Popisek zobrazen'
          }}</q-tooltip>
        </q-btn>
        <q-btn
          flat
          dense
          round
          size="sm"
          :color="field.barcode ? 'primary' : 'grey'"
          icon="sym_o_barcode"
          data-test="toggle-barcode"
          @click="field.barcode = !field.barcode"
        >
          <q-tooltip>Vytisknout jako čárový kód</q-tooltip>
        </q-btn>
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
      <div v-if="field.parts?.length" class="flex items-center gap-1 pl-7">
        <q-select
          v-model="field.parts"
          :options="options"
          option-value="key"
          option-label="label"
          emit-value
          map-options
          multiple
          use-chips
          outlined
          dense
          hide-bottom-space
          label="Spojené údaje"
          class="flex-1"
          data-test="parts"
        />
        <q-btn
          flat
          dense
          round
          size="sm"
          :icon="field.direction === 'column' ? 'sym_o_table_rows' : 'sym_o_view_column'"
          data-test="toggle-direction"
          @click="field.direction = field.direction === 'column' ? 'row' : 'column'"
        >
          <q-tooltip>{{
            field.direction === 'column' ? 'Pod sebou (sloupec)' : 'Vedle sebe (řádek)'
          }}</q-tooltip>
        </q-btn>
        <q-input
          v-if="field.direction !== 'column'"
          v-model="field.separator"
          outlined
          dense
          hide-bottom-space
          label="Oddělovač"
          class="w-24"
          maxlength="10"
          data-test="separator"
        />
      </div>
    </div>
    <p v-if="!model.length" class="m-0 text-sm text-muted">Nic není vybráno.</p>
    <div class="mt-1 flex gap-1">
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
        @update:model-value="add"
      />
      <q-btn
        flat
        dense
        icon="sym_o_join"
        label="Složený"
        data-test="add-composite"
        @click="addComposite"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { CatalogFieldSchema, LayoutFieldSchema } from '@/client'

const props = defineProps<{ options: CatalogFieldSchema[] }>()
const model = defineModel<LayoutFieldSchema[]>({ required: true })

const noCaptionHint = 'bez popisku'

const labelOf = (key?: string) => props.options.find((o) => o.key === key)?.label ?? key

const add = (option: CatalogFieldSchema | null) => {
  if (option) model.value = [...model.value, { key: option.key, label: option.label }]
}
// the first two attributes as a start, the admin changes them in the picker
const addComposite = () => {
  const parts = props.options.slice(0, 2).map((o) => o.key)
  model.value = [...model.value, { key: '', parts, label: '', direction: 'row', separator: ', ' }]
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
