<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-full">
      <div class="p-4 flex flex-col">
        <div class="w-full flex justify-between items-center mb-3">
          <span class="text-2xl uppercase">{{ editing ? 'Upravit kód' : 'Přidat kód' }}</span>
          <q-btn flat round icon="close" v-close-popup />
        </div>

        <q-form class="flex flex-col gap-2" @submit="onSubmit">
          <CustomerSearchSelect v-if="!editing" v-model="customer" />
          <div v-else class="text-sm">
            Zákazník: <strong>{{ editing.customer.name }}</strong>
            <small class="text-gray-5 ml-1">{{ editing.customer.code }}</small>
          </div>

          <q-input
            v-model.trim="code"
            label="Kód zákazníka"
            outlined
            maxlength="100"
            :rules="[rules.notEmpty]"
          />

          <q-btn
            type="submit"
            unelevated
            color="primary"
            label="Uložit"
            class="h-[3rem] mt-3"
            :loading="saving"
          />
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import type { CustomerProductCodeSchema, CustomerSchema } from '@/client'
import CustomerSearchSelect from '@/components/selects/CustomerSearchSelect.vue'
import { rules } from '@/utils/rules'
import { useQuasar } from 'quasar'
import { ref, watch } from 'vue'

const showDialog = defineModel<boolean>('show', { default: false })

const props = defineProps<{
  /** Existing code to edit - only the code changes, the customer is fixed. */
  editing?: CustomerProductCodeSchema | null
  saving?: boolean
}>()

const emit = defineEmits<{
  (e: 'submit', body: { customerCode: string; code: string }): void
}>()

const $q = useQuasar()
const customer = ref<CustomerSchema>()
const code = ref('')

watch(showDialog, (visible) => {
  if (visible) {
    code.value = props.editing?.code ?? ''
  } else {
    customer.value = undefined
    code.value = ''
  }
})

const onSubmit = () => {
  const customerCode = props.editing?.customer.code ?? customer.value?.code
  if (!customerCode) {
    $q.notify({ type: 'warning', message: 'Vyberte zákazníka.' })
    return
  }
  emit('submit', { customerCode, code: code.value })
}
</script>
