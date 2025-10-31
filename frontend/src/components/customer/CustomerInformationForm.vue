<template>
  <q-form @submit="console.info('form sent!')" class="grid grid-cols-2 gap-2">
    <q-input outlined :readonly="readonly" v-model="customer.identification" label="IČ"></q-input>
    <q-input
      outlined
      :readonly="readonly"
      v-model="customer.tax_identification"
      label="DIČ"
    ></q-input>
    <q-input outlined :readonly="readonly" v-model="customer.name" label="Název"></q-input>
    <q-input outlined :readonly="readonly" v-model="customer.code" label="Kód"></q-input>
    <q-input
      outlined
      :readonly="readonly"
      v-model="customer.responsible_user"
      label="Zodpovědná osoba"
    ></q-input>
    <q-input outlined :readonly="readonly" v-model="customer.customer_type" label="Typ"></q-input>
    <q-input
      outlined
      :readonly="readonly"
      v-model="customer.price_type"
      label="Cenový typ"
    ></q-input>
    <q-input outlined :readonly="readonly" v-model="customer.group" label="Skupina"></q-input>
    <q-input
      outlined
      :readonly="readonly"
      v-model="customer.invoice_due_days"
      label="Splatnost"
    ></q-input>
    <q-input
      outlined
      :readonly="readonly"
      v-model="customer.block_after_due_days"
      label="Blokovat po dnech nezaplacení"
    ></q-input>
    <q-input
      type="textarea"
      outlined
      :readonly="readonly"
      v-model="customer.note"
      label="Poznámka"
      class="col-span-2"
    ></q-input>
  </q-form>
</template>

<script setup lang="ts">
defineProps<{ readonly?: boolean }>()

interface CustomerIn {
  identification: string
  tax_identification: string
  name: string
  code: string
  customer_type: string
  price_type: string
  invoice_due_days: 0
  block_after_due_days: 0
  data_collection_agreement: boolean
  marketing_data_use_agreement: boolean
  is_valid: boolean
  is_deleted: boolean
  owner: string
  responsible_user: string
  group: string
  note: string
  register_information: string
}

const customer = defineModel<CustomerIn>({
  default: {
    identification: '',
    tax_identification: '',
    name: '',
    code: '',
    responsible_user: '',
  },
})
</script>

<style lang="scss" scoped></style>
