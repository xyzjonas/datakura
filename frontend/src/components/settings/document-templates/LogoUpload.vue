<template>
  <div class="flex flex-col gap-1">
    <div class="flex items-center gap-3">
      <img
        v-if="model"
        :src="model"
        alt="Logo"
        class="max-h-16 max-w-40 border border-solid border-gray-300"
      />
      <q-file
        v-model="file"
        outlined
        dense
        hide-bottom-space
        class="flex-1"
        label="Logo (PNG, JPEG, GIF, WebP)"
        accept="image/png,image/jpeg,image/gif,image/webp"
        :max-file-size="MAX_FILE_BYTES"
        data-test="logo-file"
        @update:model-value="load"
        @rejected="rejected"
      />
      <q-btn
        v-if="model"
        flat
        dense
        round
        icon="sym_o_delete"
        data-test="logo-remove"
        @click="remove"
      />
    </div>
    <p class="m-0 text-xs text-muted">
      Logo se vytiskne tam, kam ho přidáte jako atribut „Logo“ (hlavička, dodavatel, odběratel).
    </p>
  </div>
</template>

<script setup lang="ts">
import { useQuasar } from 'quasar'
import { ref } from 'vue'

/** Stays well below the server limit (the image is stored as base64 in the layout). */
const MAX_FILE_BYTES = 400_000

// the image as a base64 data URL
const model = defineModel<string | null>({ required: true })
const $q = useQuasar()
const file = ref<File | null>(null)

const load = (picked: File | null) => {
  if (!picked) return
  const reader = new FileReader()
  reader.onload = () => {
    model.value = String(reader.result)
  }
  reader.readAsDataURL(picked)
}

const remove = () => {
  model.value = null
  file.value = null
}

const rejected = () =>
  $q.notify({ type: 'negative', message: 'Obrázek je příliš velký (maximum 400 kB).' })
</script>
