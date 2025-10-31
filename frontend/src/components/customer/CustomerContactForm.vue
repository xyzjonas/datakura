<template>
  <q-form @submit="console.info('form sent!')" class="flex flex-col gap-2">
    <q-input outlined :readonly="readonly" v-model="customer.street" label="Ulice"></q-input>
    <q-input outlined :readonly="readonly" v-model="customer.city" label="Město"></q-input>
    <q-input outlined :readonly="readonly" v-model="customer.postal_code" label="PSČ"></q-input>
    <q-input outlined :readonly="readonly" v-model="customer.state" label="Stát"></q-input>
    <q-input outlined :readonly="readonly" v-model="customer.phone" label="Telefon"></q-input>
    <q-input outlined :readonly="readonly" v-model="customer.email" label="Email"></q-input>
    <div class="mt-auto flex gap-2 flex-row-reverse">
      <q-btn type="submit" outline color="primary" label="uložit" disable></q-btn>
      <q-btn outline color="primary" label="štítek" icon="print" disable></q-btn>
    </div>
  </q-form>
</template>

<script setup lang="ts">
defineProps<{ readonly?: boolean }>()

interface CusomerContactIn {
  email: string
  phone: string
  street: string
  city: string
  postal_code: string
  state: string
}

const customer = defineModel<CusomerContactIn>({
  default: {
    email: '',
    phone: '',
    street: '',
    city: '',
    postal_code: '',
    state: '',
  },
})
</script>

<style lang="scss" scoped></style>
