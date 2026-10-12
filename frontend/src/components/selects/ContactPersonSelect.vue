<template>
  <q-select
    v-model="modelValue"
    outlined
    clearable
    clear-icon="sym_o_close_small"
    :dense="dense"
    :label="label"
    :hint="hint"
    :options="contacts"
    :option-label="contactFullName"
    option-value="id"
    :disable="disable || !customerCode"
    :loading="loading"
  >
    <template #no-option>
      <q-item>
        <q-item-section class="text-grey">Zákazník nemá žádné kontakty</q-item-section>
      </q-item>
    </template>
  </q-select>
</template>

<script setup lang="ts">
import { warehouseApiRoutesCustomerGetCustomerContacts, type ContactPersonSchema } from '@/client'
import { contactFullName } from '@/utils/contact-name'
import { ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    customerCode?: string
    label?: string
    hint?: string
    disable?: boolean
    dense?: boolean
  }>(),
  {
    customerCode: undefined,
    label: 'Kontakt / pobočka',
    hint: undefined,
    disable: false,
    dense: false,
  },
)

const modelValue = defineModel<ContactPersonSchema | null>({ default: null })

const contacts = ref<ContactPersonSchema[]>([])
const loading = ref(false)

const loadContacts = async (customerCode?: string) => {
  contacts.value = []
  if (!customerCode) {
    return
  }
  loading.value = true
  try {
    const result = await warehouseApiRoutesCustomerGetCustomerContacts({
      path: { customer_code: customerCode },
    })
    // ignore stale responses when the customer changed meanwhile
    if (customerCode === props.customerCode) {
      contacts.value = result.data ?? []
    }
  } finally {
    loading.value = false
  }
}

watch(() => props.customerCode, loadContacts, { immediate: true })
</script>
