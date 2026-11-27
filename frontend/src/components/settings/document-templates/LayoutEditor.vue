<template>
  <div class="flex flex-col gap-2">
    <LayoutBlock title="Hlavička">
      <q-input
        v-model="model.header.title"
        outlined
        dense
        hide-bottom-space
        label="Nadpis dokladu"
        maxlength="100"
        data-test="header-title"
      />
      <div v-for="section in sections" :key="section.key" class="flex flex-col gap-1">
        <div class="text-sm font-semibold">{{ section.label }}</div>
        <FieldListEditor v-model="model.header[section.key]" :options="catalog.header_fields" />
      </div>
    </LayoutBlock>

    <PartyBlockEditor
      v-model="model.supplier"
      heading="Dodavatel"
      :options="catalog.supplier_fields"
    />
    <PartyBlockEditor
      v-model="model.customer"
      heading="Odběratel"
      :options="catalog.customer_fields"
    />

    <LayoutBlock v-model:enabled="model.items.enabled" title="Tabulka položek" toggleable>
      <div class="text-sm font-semibold">Sloupce</div>
      <FieldListEditor v-model="model.items.columns" :options="catalog.item_columns" />
      <div class="text-sm font-semibold">Souhrny pod tabulkou</div>
      <FieldListEditor v-model="model.items.summaries" :options="catalog.summaries" />
    </LayoutBlock>

    <LayoutBlock v-model:enabled="model.footer.enabled" title="Patička" toggleable>
      <FooterTextEditor v-model="model.footer.text" />
    </LayoutBlock>

    <PageBlockEditor v-model="model.page" :fonts="catalog.fonts" />

    <LayoutBlock v-model:enabled="model.pagination.enabled" title="Číslování stran" toggleable>
      <q-select
        v-model="model.pagination.position"
        :options="positions"
        emit-value
        map-options
        outlined
        dense
        hide-bottom-space
        label="Umístění čísla strany"
        data-test="pagination-position"
      />
      <p class="m-0 text-xs text-muted">Číslo strany se tiskne jen do PDF, náhled nestránkuje.</p>
    </LayoutBlock>
  </div>
</template>

<script setup lang="ts">
import type { DocumentCatalogSchema } from '@/client'
import FieldListEditor from './FieldListEditor.vue'
import FooterTextEditor from './FooterTextEditor.vue'
import LayoutBlock from './LayoutBlock.vue'
import PageBlockEditor from './PageBlockEditor.vue'
import PartyBlockEditor from './PartyBlockEditor.vue'
import type { DocumentLayout } from './types'

defineProps<{ catalog: DocumentCatalogSchema }>()
const model = defineModel<DocumentLayout>({ required: true })

const sections = [
  { key: 'left', label: 'Vlevo' },
  { key: 'middle', label: 'Uprostřed' },
  { key: 'right', label: 'Vpravo' },
] as const

const positions = [
  { value: 'top-left', label: 'Nahoře vlevo' },
  { value: 'top-center', label: 'Nahoře uprostřed' },
  { value: 'top-right', label: 'Nahoře vpravo' },
  { value: 'bottom-left', label: 'Dole vlevo' },
  { value: 'bottom-center', label: 'Dole uprostřed' },
  { value: 'bottom-right', label: 'Dole vpravo' },
]
</script>
