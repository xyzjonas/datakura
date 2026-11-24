<template>
  <div class="flex h-full min-h-60 flex-col gap-2">
    <q-banner v-if="error" dense rounded class="bg-red-1 text-negative">
      <div class="text-sm">
        <strong v-if="error.line">Řádek {{ error.line }}: </strong>{{ error.message }}
      </div>
      <div v-if="html" class="text-xs text-muted">Zobrazen poslední funkční náhled.</div>
    </q-banner>
    <div
      ref="pane"
      class="relative flex-1 overflow-auto rounded-md border border-solid border-gray-300 bg-gray-100"
    >
      <q-inner-loading :showing="loading" />
      <div v-if="!html && !error && !loading" class="p-4 text-sm text-muted">
        Vyberte záznam, nad kterým se má šablona vykreslit.
      </div>
      <div v-else :style="{ width: `${A4_WIDTH * scale}px`, height: `${height * scale}px` }">
        <!-- no scripts: the template is user content; same-origin only to measure it -->
        <iframe
          ref="frame"
          sandbox="allow-same-origin"
          :srcdoc="html"
          title="Náhled dokumentu"
          class="origin-top-left border-0 bg-white"
          :style="{ width: `${A4_WIDTH}px`, height: `${height}px`, transform: `scale(${scale})` }"
          @load="measure"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { TemplateErrorSchema } from '@/client'
import { useElementSize } from '@vueuse/core'
import { computed, ref } from 'vue'

defineProps<{
  html: string
  error?: TemplateErrorSchema | null
  loading?: boolean
}>()

/** A4 width in CSS px (210 mm @ 96 dpi) - the page the PDF is laid out on. */
const A4_WIDTH = 794
const A4_HEIGHT = 1123

const pane = ref<HTMLElement>()
const frame = ref<HTMLIFrameElement>()
const { width: paneWidth } = useElementSize(pane)
const height = ref(A4_HEIGHT)

// fit the page into the pane, never enlarge it
const scale = computed(() =>
  paneWidth.value > 0 ? Math.min(1, (paneWidth.value - 16) / A4_WIDTH) : 1,
)

const measure = () => {
  const doc = frame.value?.contentDocument
  if (doc) height.value = Math.max(A4_HEIGHT, doc.documentElement.scrollHeight)
}
</script>
