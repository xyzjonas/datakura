<template>
  <div class="flex flex-col gap-1">
    <div class="flex items-center gap-1">
      <q-btn
        v-for="format in formats"
        :key="format.key"
        flat
        dense
        size="sm"
        :icon="format.icon"
        :title="format.title"
        :data-test="`footer-${format.key}`"
        @click="apply(format.key)"
      />
      <span class="ml-2 text-xs text-muted">**tučně** *kurzíva* __podtržení__</span>
    </div>
    <q-input
      ref="input"
      v-model="model"
      type="textarea"
      outlined
      dense
      autogrow
      hide-bottom-space
      label="Text patičky"
      maxlength="1000"
      data-test="footer-text"
    />
  </div>
</template>

<script setup lang="ts">
import type { QInput } from 'quasar'
import { nextTick, ref } from 'vue'
import { toggleFormat, type FooterFormat } from './footer-format'

const model = defineModel<string>({ required: true })
const input = ref<InstanceType<typeof QInput>>()

const formats: { key: FooterFormat; icon: string; title: string }[] = [
  { key: 'bold', icon: 'sym_o_format_bold', title: 'Tučně' },
  { key: 'italic', icon: 'sym_o_format_italic', title: 'Kurzíva' },
  { key: 'underline', icon: 'sym_o_format_underlined', title: 'Podtržení' },
]

const apply = async (format: FooterFormat) => {
  const el = input.value?.nativeEl as HTMLTextAreaElement | undefined
  const text = model.value ?? ''
  const result = toggleFormat(
    { text, start: el?.selectionStart ?? text.length, end: el?.selectionEnd ?? text.length },
    format,
  )
  model.value = result.text
  await nextTick()
  el?.focus()
  el?.setSelectionRange(result.start, result.end)
}
</script>
