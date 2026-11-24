<template>
  <div
    ref="host"
    class="h-full min-h-60 overflow-hidden rounded-md border border-solid border-gray-300"
  />
</template>

<script setup lang="ts">
import type { DocumentLegendSchema } from '@/client'
import { createTemplateCompletion } from './template-completions'
import { autocompletion, closeBrackets } from '@codemirror/autocomplete'
import { html } from '@codemirror/lang-html'
import { EditorState } from '@codemirror/state'
import { EditorView } from '@codemirror/view'
import { basicSetup } from 'codemirror'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps<{ legend?: DocumentLegendSchema }>()
const model = defineModel<string>({ default: '' })

const host = ref<HTMLElement>()
let view: EditorView | undefined

const theme = EditorView.theme({
  '&': { height: '100%', fontSize: '12px' },
  '.cm-scroller': { overflow: 'auto', fontFamily: 'ui-monospace, monospace' },
})

onMounted(() => {
  view = new EditorView({
    parent: host.value,
    state: EditorState.create({
      doc: model.value,
      extensions: [
        basicSetup,
        html(),
        closeBrackets(),
        autocompletion({ override: [createTemplateCompletion(() => props.legend)] }),
        EditorView.lineWrapping,
        theme,
        EditorView.updateListener.of((update) => {
          if (update.docChanged) model.value = update.state.doc.toString()
        }),
      ],
    }),
  })
})

onBeforeUnmount(() => view?.destroy())

// external changes (another template loaded, reset) -> into the editor
watch(model, (value) => {
  if (!view || value === view.state.doc.toString()) return
  view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: value } })
})

/** Insert a snippet at the cursor (replacing the selection) and focus the editor. */
const insert = (text: string) => {
  if (!view) return
  const { from, to } = view.state.selection.main
  view.dispatch({
    changes: { from, to, insert: text },
    selection: { anchor: from + text.length },
  })
  view.focus()
}

defineExpose({ insert })
</script>
