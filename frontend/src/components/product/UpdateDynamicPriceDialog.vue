<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-lg">
      <div class="p-4 flex flex-col">
        <div class="w-full flex justify-between items-center mb-3">
          <span class="text-2xl uppercase">Upravit cenu</span>
          <q-btn flat round icon="close" v-close-popup />
        </div>

        <q-form class="flex flex-col gap-2" @submit="onSubmit">
          <q-input
            v-model.number="fixedPrice"
            label="Cena (Kc)"
            type="number"
            min="0"
            step="0.01"
            outlined
            :rules="[rules.isNumber, rules.atLeastZero]"
          />

          <small class="text-gray-5">
            Aktualni zakaznik: {{ props.price?.customer?.name ?? 'neni nastaven' }}
          </small>

          <q-btn
            type="submit"
            unelevated
            color="primary"
            label="Ulozit"
            class="h-[3rem] mt-3"
            :loading="props.saving"
          />
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { type DynamicProductPriceUpdateSchema, type DynamicProductPriceSchema } from '@/client'
import { useQuasar } from 'quasar'
import { ref, watch } from 'vue'
import { rules } from '@/utils/rules'

const showDialog = defineModel('show', { default: false })

const props = defineProps<{
  price?: DynamicProductPriceSchema
  saving?: boolean
}>()

const emit = defineEmits<{
  (e: 'submit', body: DynamicProductPriceUpdateSchema): void
}>()

const $q = useQuasar()

const fixedPrice = ref<number | null>(null)

const fillForm = () => {
  fixedPrice.value = props.price?.fixed_price ?? null
}

watch(showDialog, (value) => {
  if (value) {
    fillForm()
  }
})

watch(
  () => props.price,
  () => {
    if (showDialog.value) {
      fillForm()
    }
  },
)

const onSubmit = () => {
  if (fixedPrice.value === null || fixedPrice.value < 0) {
    $q.notify({ type: 'warning', message: 'Cena musi byt rovna nebo vyssi nez 0.' })
    return
  }

  const customerCode = props.price?.customer?.code
  if (!customerCode) {
    $q.notify({ type: 'warning', message: 'Vyberte zakaznika.' })
    return
  }

  emit('submit', {
    fixed_price: fixedPrice.value,
    customer_code: customerCode,
  })
}
</script>
