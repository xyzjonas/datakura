<template>
  <q-dialog v-model="showDialog">
    <q-card class="w-full max-w-lg">
      <div class="p-4">
        <div class="w-full flex items-center mb-4 gap-2">
          <span class="text-2xl uppercase">Oříznout fotografii</span>
          <q-btn flat round icon="close" v-close-popup class="ml-auto" />
        </div>

        <Cropper
          ref="cropper"
          class="h-80 bg-black"
          :src="src"
          :stencil-component="CircleStencil"
          :canvas="{ maxWidth: 512, maxHeight: 512 }"
        />

        <div class="mt-4 flex justify-end gap-2">
          <q-btn flat color="negative" label="zrušit" v-close-popup />
          <q-btn unelevated color="primary" label="uložit" :loading="loading" @click="onSave" />
        </div>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { CircleStencil, Cropper } from 'vue-advanced-cropper'
import 'vue-advanced-cropper/dist/style.css'

const showDialog = defineModel<boolean>('show', { default: false })

defineProps<{
  src: string
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'crop', file: File): void
}>()

const cropper = ref<InstanceType<typeof Cropper>>()

const onSave = () => {
  const canvas = cropper.value?.getResult().canvas
  canvas?.toBlob(
    (blob) => {
      if (blob) {
        emit('crop', new File([blob], 'avatar.webp', { type: blob.type }))
      }
    },
    'image/webp',
    0.85,
  )
}
</script>
