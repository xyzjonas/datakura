<template>
  <div
    ref="pane"
    class="relative h-full min-h-60 overflow-auto rounded-md border border-solid border-gray-300 bg-gray-100"
  >
    <q-inner-loading :showing="loading" />
    <p v-if="failed" class="m-0 p-4 text-sm text-negative">Náhled se nepodařilo načíst.</p>
    <p v-else-if="!html && !loading" class="m-0 p-4 text-sm text-muted">
      Vyberte záznam, nad kterým se má doklad vykreslit.
    </p>
    <div v-else :style="{ width: `${A4_WIDTH * scale}px`, height: `${height * scale}px` }">
      <!-- no scripts; same-origin only so the page height can be measured -->
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
</template>

<script setup lang="ts">
import { useElementSize } from '@vueuse/core'
import { computed, ref } from 'vue'

defineProps<{ html: string; loading?: boolean; failed?: boolean }>()

/** A4 in CSS px (210 x 297 mm @ 96 dpi) - the page the PDF is laid out on. */
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
