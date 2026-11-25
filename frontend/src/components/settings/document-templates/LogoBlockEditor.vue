<template>
  <LayoutBlock v-model:enabled="model.enabled" title="Logo" toggleable>
    <div class="flex items-center gap-3">
      <img
        v-if="model.image"
        :src="model.image"
        alt="Logo"
        class="max-h-16 max-w-40 border border-solid border-gray-300"
      />
      <q-file
        v-model="file"
        outlined
        dense
        hide-bottom-space
        class="flex-1"
        label="Nahrát obrázek (PNG, JPEG, GIF, WebP)"
        accept="image/png,image/jpeg,image/gif,image/webp"
        :max-file-size="MAX_FILE_BYTES"
        data-test="logo-file"
        @update:model-value="load"
        @rejected="rejected"
      />
      <q-btn
        v-if="model.image"
        flat
        dense
        round
        icon="sym_o_delete"
        data-test="logo-remove"
        @click="remove"
      />
    </div>
    <q-btn-toggle
      v-model="model.align"
      unelevated
      dense
      toggle-color="primary"
      :options="ALIGNMENTS"
      data-test="logo-align"
    />
  </LayoutBlock>
</template>

<script setup lang="ts">
import type { LogoBlockSchema } from '@/client'
import { useQuasar } from 'quasar'
import { ref } from 'vue'
import LayoutBlock from './LayoutBlock.vue'

/** Stays well below the server limit (the image is stored as base64 in the layout). */
const MAX_FILE_BYTES = 400_000
const ALIGNMENTS = [
  { label: 'Vlevo', value: 'left' },
  { label: 'Na střed', value: 'center' },
  { label: 'Vpravo', value: 'right' },
]

const model = defineModel<Required<LogoBlockSchema>>({ required: true })
const $q = useQuasar()
const file = ref<File | null>(null)

const load = (picked: File | null) => {
  if (!picked) return
  const reader = new FileReader()
  reader.onload = () => {
    model.value.image = String(reader.result)
    model.value.enabled = true
  }
  reader.readAsDataURL(picked)
}

const remove = () => {
  model.value.image = null
  model.value.enabled = false
  file.value = null
}

const rejected = () =>
  $q.notify({ type: 'negative', message: 'Obrázek je příliš velký (maximum 400 kB).' })
</script>
