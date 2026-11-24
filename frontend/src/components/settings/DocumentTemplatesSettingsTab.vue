<template>
  <div class="flex h-full flex-col gap-3">
    <p class="max-w-3xl text-sm text-muted">
      Šablony tištěných dokladů (HTML, Jinja). Vyberte doklad a záznam, nad kterým se šablona
      vykreslí. Změny se zobrazují hned, uloží se až tlačítkem. PDF export ověří výsledný tisk.
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
        {{ template.is_default ? 'výchozí šablona' : 'upravená šablona' }}
      </q-badge>
      <q-btn flat dense icon="sym_o_help" label="Legenda" @click="showLegend = !showLegend" />
      <q-btn
        flat
        dense
        icon="sym_o_restart_alt"
        label="Výchozí"
        :disable="!template || template.is_default"
        @click="confirmReset"
      />
      <q-btn
        outline
        color="primary"
        icon="sym_o_picture_as_pdf"
        label="Export PDF"
        :disable="!recordCode"
        :loading="exporting"
        @click="exportPdf"
      />
      <q-btn
        unelevated
        color="primary"
        label="uložit"
        :loading="saving"
        :disable="!isDirty"
        @click="save"
      />
    </div>
    <div
      class="grid h-[70vh] gap-3"
      :class="showLegend ? 'grid-cols-[1fr_1fr_16rem]' : 'grid-cols-2'"
    >
      <TemplateEditor ref="editor" v-model="content" :legend="template?.legend" />
      <TemplatePreview :html="html" :error="error" :loading="previewLoading" />
      <ContextLegend v-if="showLegend" :legend="template?.legend" @insert="insertSnippet" />
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
import { useTemplatePreview } from '@/composables/use-template-preview'
import { useQuasar } from 'quasar'
import { computed, onMounted, ref } from 'vue'
import ContextLegend from './document-templates/ContextLegend.vue'
import TemplateEditor from './document-templates/TemplateEditor.vue'
import TemplatePreview from './document-templates/TemplatePreview.vue'

const { onResponse } = useApi()
const $q = useQuasar()

const targets = ref<DocumentTargetSchema[]>([])
const target = ref<DocumentTarget>()
const template = ref<DocumentTemplateSchema>()
const content = ref('')
const recordCode = ref<string>()
const recordOptions = ref<DocumentRecordSchema[]>([])
const showLegend = ref(false)
const saving = ref(false)
const exporting = ref(false)
const editor = ref<InstanceType<typeof TemplateEditor>>()

const isDirty = computed(() => !!template.value && content.value !== template.value.content)

const { html, error, loading: previewLoading } = useTemplatePreview(target, recordCode, content)

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
  content.value = loaded.content
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
    message: 'Šablona obsahuje neuložené změny. Opravdu je zahodit?',
    cancel: true,
  }).onOk(() => void loadTarget(value))
}

onMounted(async () => {
  const response = onResponse(await warehouseApiRoutesDocumentTemplatesGetDocumentTargets())
  targets.value = response?.data ?? []
  const first = targets.value[0]
  if (first) await loadTarget(first.target)
})

const refreshTargets = async () => {
  const response = onResponse(await warehouseApiRoutesDocumentTemplatesGetDocumentTargets())
  targets.value = response?.data ?? targets.value
}

const save = async () => {
  if (!target.value) return
  saving.value = true
  try {
    const response = onResponse(
      await warehouseApiRoutesDocumentTemplatesUpdateDocumentTemplate({
        path: { target: target.value },
        body: { content: content.value },
      }),
    )
    if (response?.data) {
      applyTemplate(response.data)
      await refreshTargets()
      $q.notify({ type: 'positive', message: 'Šablona byla uložena.' })
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
    $q.notify({ type: 'positive', message: 'Obnovena výchozí šablona.' })
  }
}

const confirmReset = () =>
  $q
    .dialog({
      title: 'Obnovit výchozí šablonu',
      message: 'Vlastní úpravy šablony budou nenávratně smazány.',
      cancel: true,
    })
    .onOk(() => void reset())

const exportPdf = async () => {
  if (!target.value || !recordCode.value) return
  exporting.value = true
  try {
    // exports the draft in the editor, not only the saved template
    const response = await warehouseApiRoutesDocumentTemplatesExportDocumentPdf({
      path: { target: target.value },
      body: { record_code: recordCode.value, content: content.value },
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

const insertSnippet = (snippet: string) => editor.value?.insert(snippet)
</script>
