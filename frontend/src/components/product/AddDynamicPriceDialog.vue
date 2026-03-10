<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-lg">
      <div class="p-4 flex flex-col">
        <div class="w-full flex justify-between items-center mb-3">
          <span class="text-2xl uppercase">Přidat cenu</span>
          <q-btn flat round icon="close" v-close-popup />
        </div>

        <q-form class="flex flex-col gap-2" @submit="onSubmit">
          <q-select
            v-model="addForm.price_type"
            label="Typ ceny"
            :options="priceTypeOptions"
            emit-value
            map-options
            outlined
          />

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

          <q-input
            v-if="addForm.price_type === 'GROUP_DISCOUNT'"
            v-model="addForm.group_name"
            label="Skupina"
            outlined
          />

          <q-input
            v-if="addForm.price_type === 'CUSTOMER_DISCOUNT'"
            v-model="addForm.customer_code"
            label="Kód zákazníka"
            outlined
          />

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
  price_type: 'GROUP_DISCOUNT' | 'CUSTOMER_DISCOUNT'
  discount_percent: number | null
  group_name: string
  customer_code: string
}>({
  price_type: 'GROUP_DISCOUNT',
  discount_percent: null,
  group_name: '',
  customer_code: '',
})

const priceTypeOptions = [
  { label: 'Skupinová sleva', value: 'GROUP_DISCOUNT' },
  { label: 'Sleva pro zákazníka', value: 'CUSTOMER_DISCOUNT' },
]

const resetAddForm = () => {
  addForm.value = {
    price_type: 'GROUP_DISCOUNT',
    discount_percent: null,
    group_name: '',
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

  if (addForm.value.price_type === 'GROUP_DISCOUNT' && !addForm.value.group_name.trim()) {
    $q.notify({ type: 'warning', message: 'Vyplňte skupinu.' })
    return
  }

  if (addForm.value.price_type === 'CUSTOMER_DISCOUNT' && !addForm.value.customer_code.trim()) {
    $q.notify({ type: 'warning', message: 'Vyplňte kód zákazníka.' })
    return
  }

  const body: DynamicProductPriceCreateSchema = {
    price_type: addForm.value.price_type,
    discount_percent: discount,
    group_name:
      addForm.value.price_type === 'GROUP_DISCOUNT' ? addForm.value.group_name.trim() : undefined,
    customer_code:
      addForm.value.price_type === 'CUSTOMER_DISCOUNT'
        ? addForm.value.customer_code.trim()
        : undefined,
  }

  emit('submit', body)
}
</script>
