<template>
  <div class="flex items-center gap-1">
    <q-btn
      flat
      dense
      round
      size="sm"
      :color="model.show_label === false ? 'grey' : 'primary'"
      :icon="model.show_label === false ? 'sym_o_label_off' : 'sym_o_label'"
      data-test="toggle-label"
      @click="model.show_label = model.show_label === false"
    >
      <q-tooltip>{{
        model.show_label === false ? 'Popisek skrytý' : 'Popisek zobrazen'
      }}</q-tooltip>
    </q-btn>
    <q-btn
      flat
      dense
      round
      size="sm"
      :color="model.bold ? 'primary' : 'grey'"
      icon="sym_o_format_bold"
      data-test="toggle-bold"
      @click="model.bold = !model.bold"
    >
      <q-tooltip>Tučně</q-tooltip>
    </q-btn>
    <q-btn
      flat
      dense
      round
      size="sm"
      :color="model.muted ? 'primary' : 'grey'"
      icon="sym_o_opacity"
      data-test="toggle-muted"
      @click="model.muted = !model.muted"
    >
      <q-tooltip>Potlačeně (šedě)</q-tooltip>
    </q-btn>
    <template v-if="!hideBarcode">
      <q-btn
        flat
        dense
        round
        size="sm"
        :color="model.barcode ? 'primary' : 'grey'"
        icon="sym_o_barcode"
        data-test="toggle-barcode"
        @click="model.barcode = !model.barcode"
      >
        <q-tooltip>Vytisknout jako čárový kód</q-tooltip>
      </q-btn>
      <q-btn
        v-if="model.barcode"
        flat
        dense
        round
        size="sm"
        :color="model.barcode_text ? 'primary' : 'grey'"
        icon="sym_o_subtitles"
        data-test="toggle-barcode-text"
        @click="model.barcode_text = !model.barcode_text"
      >
        <q-tooltip>Text pod čárovým kódem</q-tooltip>
      </q-btn>
    </template>
    <q-input
      :model-value="model.font_size ?? ''"
      type="number"
      min="6"
      max="72"
      outlined
      dense
      hide-bottom-space
      label="Písmo"
      class="w-20"
      data-test="font-size"
      @update:model-value="setSize"
    />
  </div>
</template>

<script setup lang="ts">
import type { LayoutPartSchema } from '@/client'

defineProps<{ hideBarcode?: boolean }>()
// a single value or a composite - both carry the same options
const model = defineModel<LayoutPartSchema>({ required: true })

// empty = inherit, the API accepts 6-72 px
const setSize = (value: string | number | null) => {
  const size = Number(value)
  model.value.font_size = value === '' || value === null || !size ? null : size
}
</script>
