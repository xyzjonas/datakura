<template>
  <LayoutBlock title="Stránka">
    <q-select
      v-model="model.font"
      :options="fonts"
      option-value="key"
      option-label="label"
      emit-value
      map-options
      outlined
      dense
      hide-bottom-space
      label="Písmo dokladu"
      data-test="page-font"
    />
    <LogoUpload v-model="model.logo" />
    <div class="text-sm font-semibold">Okraje</div>
    <div class="grid grid-cols-2 gap-2">
      <q-input
        v-for="side in sides"
        :key="side.key"
        :model-value="model[side.key]"
        type="number"
        min="0"
        max="200"
        suffix="px"
        outlined
        dense
        hide-bottom-space
        :label="side.label"
        :data-test="side.key"
        @update:model-value="set(side.key, $event)"
      />
    </div>
    <p class="m-0 text-xs text-muted">
      0 = bez okraje. Okraje se projeví v PDF, náhled je nezobrazuje.
    </p>
  </LayoutBlock>
</template>

<script setup lang="ts">
import type { CatalogFieldSchema, PageSchema } from '@/client'
import LayoutBlock from './LayoutBlock.vue'
import LogoUpload from './LogoUpload.vue'

type Side = 'margin_top' | 'margin_right' | 'margin_bottom' | 'margin_left'

defineProps<{ fonts: CatalogFieldSchema[] }>()
const model = defineModel<Required<PageSchema>>({ required: true })

const sides: { key: Side; label: string }[] = [
  { key: 'margin_top', label: 'Nahoře' },
  { key: 'margin_right', label: 'Vpravo' },
  { key: 'margin_bottom', label: 'Dole' },
  { key: 'margin_left', label: 'Vlevo' },
]

// an empty / invalid input means no margin, the API accepts 0-200
const set = (side: Side, value: string | number | null) => {
  const px = Math.round(Number(value))
  model.value[side] = Number.isFinite(px) ? Math.min(200, Math.max(0, px)) : 0
}
</script>
