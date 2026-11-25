<template>
  <div class="flex flex-col gap-2">
    <LogoBlockEditor v-model="model.logo" />

    <LayoutBlock title="Hlavička (kód a čárový kód)">
      <q-input
        v-model="model.header.title"
        outlined
        dense
        hide-bottom-space
        label="Nadpis dokladu"
        maxlength="100"
        data-test="header-title"
      />
      <q-toggle v-model="model.header.show_barcode" label="Čárový kód s kódem dokladu" />
      <FieldListEditor v-model="model.header.fields" :options="catalog.header_fields" />
    </LayoutBlock>

    <PartyBlockEditor
      v-model="model.supplier"
      heading="Dodavatel"
      :options="catalog.party_fields"
    />
    <PartyBlockEditor
      v-model="model.customer"
      heading="Odběratel"
      :options="catalog.party_fields"
    />

    <LayoutBlock v-model:enabled="model.items.enabled" title="Tabulka položek" toggleable>
      <div class="text-sm font-semibold">Sloupce</div>
      <FieldListEditor v-model="model.items.columns" :options="catalog.item_columns" />
      <div class="text-sm font-semibold">Souhrny pod tabulkou</div>
      <FieldListEditor v-model="model.items.summaries" :options="catalog.summaries" />
    </LayoutBlock>

    <LayoutBlock v-model:enabled="model.footer.enabled" title="Patička" toggleable>
      <q-input
        v-model="model.footer.text"
        type="textarea"
        outlined
        dense
        autogrow
        hide-bottom-space
        label="Text patičky"
        maxlength="1000"
        data-test="footer-text"
      />
    </LayoutBlock>
  </div>
</template>

<script setup lang="ts">
import type { DocumentCatalogSchema } from '@/client'
import FieldListEditor from './FieldListEditor.vue'
import LayoutBlock from './LayoutBlock.vue'
import LogoBlockEditor from './LogoBlockEditor.vue'
import PartyBlockEditor from './PartyBlockEditor.vue'
import type { DocumentLayout } from './types'

defineProps<{ catalog: DocumentCatalogSchema }>()
const model = defineModel<DocumentLayout>({ required: true })
</script>
