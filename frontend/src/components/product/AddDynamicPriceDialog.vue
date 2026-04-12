<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-lg">
      <div class="p-4 flex flex-col">
        <div class="w-full flex justify-between items-center mb-3">
          <span class="text-2xl uppercase">Přidat cenu</span>
          <q-btn flat round icon="close" v-close-popup />
        </div>

        <q-form class="flex flex-col gap-2" @submit="onSubmit">
          <q-input
            v-model.number="addForm.discount_percent"
            label="Sleva (%)"
            type="number"
            min="0"
            max="100"
            step="0.01"
            outlined
            :rules="[rules.isPercentage]"
          />

          <q-input v-model="addForm.customer_code" label="Kód zákazníka" outlined />

          <q-btn
            type="submit"
            unelevated
            color="primary"
            label="Uložit"
            class="h-[3rem] mt-3"
            :loading="props.saving"
          />
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { type DynamicProductPriceCreateSchema } from '@/client'
import { useQuasar } from 'quasar'
import { ref, watch } from 'vue'
import { rules } from '@/utils/rules'

const showDialog = defineModel('show', { default: false })

const props = defineProps<{
  saving?: boolean
}>()

const emit = defineEmits<{
  (e: 'submit', body: DynamicProductPriceCreateSchema): void
}>()

const $q = useQuasar()

const addForm = ref<{
  discount_percent: number | null
  customer_code: string
}>({
  discount_percent: null,
  customer_code: '',
})

const resetAddForm = () => {
  addForm.value = {
    discount_percent: null,
    customer_code: '',
  }
}

watch(showDialog, (value) => {
  if (!value) {
    resetAddForm()
  }
})

const onSubmit = () => {
  const discount = addForm.value.discount_percent
  if (discount === null || discount < 0 || discount > 100) {
    $q.notify({ type: 'warning', message: 'Sleva musí být v rozmezí 0 až 100 %.' })
    return
  }

  if (!addForm.value.customer_code.trim()) {
    $q.notify({ type: 'warning', message: 'Vyplňte kód zákazníka.' })
    return
  }

  const body: DynamicProductPriceCreateSchema = {
    discount_percent: discount,
    customer_code: addForm.value.customer_code.trim(),
  }

  emit('submit', body)
}
</script>
