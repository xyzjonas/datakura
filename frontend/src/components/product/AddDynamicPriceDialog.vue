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
            v-model.number="addForm.fixed_price"
            label="Cena (Kč)"
            type="number"
            min="0"
            step="0.01"
            outlined
            :rules="[rules.isNumber, rules.atLeastZero]"
          />

          <CustomerSearchSelect v-model="addForm.customer" />

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
import { type DynamicProductPriceCreateSchema, type CustomerSchema } from '@/client'
import CustomerSearchSelect from '@/components/selects/CustomerSearchSelect.vue'
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
  fixed_price: number | null
  customer: CustomerSchema | undefined
}>({
  fixed_price: null,
  customer: undefined,
})

const resetAddForm = () => {
  addForm.value = {
    fixed_price: null,
    customer: undefined,
  }
}

watch(showDialog, (value) => {
  if (!value) {
    resetAddForm()
  }
})

const onSubmit = () => {
  const fixedPrice = addForm.value.fixed_price
  if (fixedPrice === null || fixedPrice < 0) {
    $q.notify({ type: 'warning', message: 'Cena musí být rovna nebo vyšší než 0.' })
    return
  }

  if (!addForm.value.customer) {
    $q.notify({ type: 'warning', message: 'Vyberte zákazníka.' })
    return
  }

  const body: DynamicProductPriceCreateSchema = {
    fixed_price: fixedPrice,
    customer_code: addForm.value.customer.code,
  }

  emit('submit', body)
}
</script>
