<template>
  <q-dialog v-model="show" position="bottom">
    <q-card class="w-full max-w-md">
      <q-card-section class="flex items-center justify-between pb-0">
        <div class="text-base font-semibold">Přesun zásob</div>
        <q-btn icon="sym_o_close" flat round dense v-close-popup />
      </q-card-section>

      <q-card-section v-if="!successMessage">
        <BarcodeMovementForm v-if="scannerMode && !itemId" :key="barcodeKey" @done="onDone" />
        <DesktopMovementForm
          v-else
          :key="`${desktopKey}-${itemId}`"
          :item-id="itemId"
          @done="onDone"
        />
      </q-card-section>

      <q-card-section v-if="successMessage">
        <EmptyPanel
          class="flex flex-col py-5 text-positive"
          icon="sym_o_check_circle"
          :text="successMessage"
        >
          <q-btn unelevated color="primary" label="Další přesun" @click="nextMove" />
        </EmptyPanel>
      </q-card-section>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { useAppSettings } from '@/composables/use-app-settings'
import { ref } from 'vue'
import BarcodeMovementForm from './BarcodeMovementForm.vue'
import DesktopMovementForm from './DesktopMovementForm.vue'
import EmptyPanel from '../EmptyPanel.vue'

const show = defineModel<boolean>({ default: false })

defineProps<{ itemId?: number }>()

const { scannerMode } = useAppSettings()
const successMessage = ref<string | null>(null)
const barcodeKey = ref(0)
const desktopKey = ref(0)

const onDone = () => {
  successMessage.value = 'Přesun byl úspěšně zaznamenán.'
}

const nextMove = () => {
  successMessage.value = null
  if (scannerMode.value) {
    barcodeKey.value++
  } else {
    desktopKey.value++
  }
}
</script>
