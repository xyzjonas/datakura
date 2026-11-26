<template>
  <div class="flex h-full flex-col gap-3">
    <p class="m-0 max-w-3xl text-sm text-muted">
      Vzhled tištěných dokladů. Základní šablona má pevná místa (hlavička, dodavatel, odběratel,
      tabulka položek, patička) - zde vyberete, které údaje se v nich vytisknou a v jakém pořadí.
      Změny se hned promítnou do náhledu, uloží se až tlačítkem.
    </p>
    <div class="flex flex-wrap items-center gap-3">
      <q-select
        :model-value="target"
        :options="targets"
        option-value="target"
        option-label="label"
        emit-value
        map-options
        outlined
        dense
        label="Doklad"
        class="w-56"
        hide-bottom-space
        data-test="target"
        @update:model-value="selectTarget"
      />
      <q-select
        v-model="recordCode"
        :options="recordOptions"
        option-value="code"
        option-label="label"
        emit-value
        map-options
        use-input
        input-debounce="250"
        outlined
        dense
        label="Záznam pro náhled"
        class="w-80"
        hide-bottom-space
        :disable="!target"
        @filter="filterRecords"
      >
        <template #no-option>
          <q-item><q-item-section class="text-muted">Žádný záznam</q-item-section></q-item>
        </template>
      </q-select>
      <q-space />
      <q-badge v-if="template" :color="template.is_default ? 'grey' : 'primary'">
        {{ template.is_default ? 'výchozí vzhled' : 'upravený vzhled' }}
      </q-badge>
      <q-btn
        flat
        dense
        icon="sym_o_restart_alt"
        label="Výchozí"
        :disable="!template || template.is_default"
        data-test="reset"
        @click="confirmReset"
      />
      <q-btn
        outline
        color="primary"
        icon="sym_o_picture_as_pdf"
        label="Export PDF"
        :disable="!recordCode"
        :loading="exporting"
        data-test="export-pdf"
        @click="exportPdf"
      />
      <q-btn
        unelevated
        color="primary"
        label="uložit"
        :loading="saving"
        :disable="!isDirty"
        data-test="save"
        @click="save"
      />
    </div>
    <div v-if="template && layout" class="grid h-[75vh] grid-cols-[minmax(20rem,26rem)_1fr] gap-3">
      <div class="overflow-y-auto pr-1">
        <LayoutEditor v-model="layout" :catalog="template.catalog" />
      </div>
      <DocumentPreview :html="html" :loading="previewLoading" :failed="failed" />
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesDocumentTemplatesExportDocumentPdf,
  warehouseApiRoutesDocumentTemplatesGetDocumentRecords,
  warehouseApiRoutesDocumentTemplatesGetDocumentTargets,
  warehouseApiRoutesDocumentTemplatesGetDocumentTemplate,
  warehouseApiRoutesDocumentTemplatesResetDocumentTemplate,
  warehouseApiRoutesDocumentTemplatesUpdateDocumentTemplate,
  type DocumentRecordSchema,
  type DocumentTarget,
  type DocumentTargetSchema,
  type DocumentTemplateSchema,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { useDocumentPreview } from '@/composables/use-document-preview'
import { useQuasar } from 'quasar'
import { computed, onMounted, ref } from 'vue'
import DocumentPreview from './document-templates/DocumentPreview.vue'
import LayoutEditor from './document-templates/LayoutEditor.vue'
import type { DocumentLayout } from './document-templates/types'

const { onResponse } = useApi()
const $q = useQuasar()

const targets = ref<DocumentTargetSchema[]>([])
const target = ref<DocumentTarget>()
const template = ref<DocumentTemplateSchema>()
// the draft being edited
const layout = ref<DocumentLayout>()
const recordCode = ref<string>()
const recordOptions = ref<DocumentRecordSchema[]>([])
const saving = ref(false)
const exporting = ref(false)

const isDirty = computed(
  () => !!template.value && JSON.stringify(layout.value) !== JSON.stringify(template.value.layout),
)

const { html, failed, loading: previewLoading } = useDocumentPreview(target, recordCode, layout)

const loadRecords = async (query?: string) => {
  if (!target.value) return
  const response = onResponse(
    await warehouseApiRoutesDocumentTemplatesGetDocumentRecords({
      path: { target: target.value },
      query: { q: query || undefined },
    }),
  )
  recordOptions.value = response?.data ?? []
}

const filterRecords = (query: string, update: (fn: () => void) => void) => {
  void loadRecords(query).then(() => update(() => {}))
}

const applyTemplate = (loaded: DocumentTemplateSchema) => {
  template.value = loaded
  layout.value = structuredClone(loaded.layout) as DocumentLayout
}

const loadTarget = async (value: DocumentTarget) => {
  const response = onResponse(
    await warehouseApiRoutesDocumentTemplatesGetDocumentTemplate({ path: { target: value } }),
  )
  if (!response?.data) return
  target.value = value
  recordCode.value = undefined
  applyTemplate(response.data)
  await loadRecords()
  recordCode.value = recordOptions.value[0]?.code
}

const selectTarget = (value: DocumentTarget) => {
  if (!isDirty.value) {
    void loadTarget(value)
    return
  }
  $q.dialog({
    title: 'Neuložené změny',
    message: 'Vzhled dokladu obsahuje neuložené změny. Opravdu je zahodit?',
    cancel: true,
  }).onOk(() => void loadTarget(value))
}

const refreshTargets = async () => {
  const response = onResponse(await warehouseApiRoutesDocumentTemplatesGetDocumentTargets())
  targets.value = response?.data ?? targets.value
}

onMounted(async () => {
  await refreshTargets()
  const first = targets.value[0]
  if (first) await loadTarget(first.target)
})

const save = async () => {
  if (!target.value || !layout.value) return
  saving.value = true
  try {
    const response = onResponse(
      await warehouseApiRoutesDocumentTemplatesUpdateDocumentTemplate({
        path: { target: target.value },
        body: { layout: layout.value },
      }),
    )
    if (response?.data) {
      applyTemplate(response.data)
      await refreshTargets()
      $q.notify({ type: 'positive', message: 'Vzhled dokladu byl uložen.' })
    }
  } finally {
    saving.value = false
  }
}

const reset = async () => {
  if (!target.value) return
  const response = onResponse(
    await warehouseApiRoutesDocumentTemplatesResetDocumentTemplate({
      path: { target: target.value },
    }),
  )
  if (response?.data) {
    applyTemplate(response.data)
    await refreshTargets()
    $q.notify({ type: 'positive', message: 'Obnoven výchozí vzhled.' })
  }
}

const confirmReset = () =>
  $q
    .dialog({
      title: 'Obnovit výchozí vzhled',
      message: 'Vlastní úpravy vzhledu dokladu budou nenávratně smazány.',
      cancel: true,
    })
    .onOk(() => void reset())

const exportPdf = async () => {
  if (!target.value || !recordCode.value || !layout.value) return
  exporting.value = true
  try {
    // exports the draft in the editor, not only the saved layout
    const response = await warehouseApiRoutesDocumentTemplatesExportDocumentPdf({
      path: { target: target.value },
      body: { record_code: recordCode.value, layout: layout.value },
    })
    if (response.error) {
      onResponse(response)
      return
    }
    const blobUrl = URL.createObjectURL(response.data as unknown as Blob)
    window.open(blobUrl, '_blank')
    setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000)
  } finally {
    exporting.value = false
  }
}
</script>
