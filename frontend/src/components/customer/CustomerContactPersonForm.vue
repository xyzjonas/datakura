<template>
  <q-form @submit="console.info('form sent!')" class="flex flex-col gap-2">
    <div class="flex gap-2">
      <q-input
        outlined
        :readonly="readonly"
        v-model="contact.title_pre"
        label="Titul před"
      ></q-input>
      <q-input
        outlined
        :readonly="readonly"
        v-model="contact.first_name"
        label="Jméno"
        class="flex-1"
      ></q-input>
      <q-input
        outlined
        :readonly="readonly"
        v-model="contact.middle_name"
        label="Prostřední jméno"
        class="flex-1"
      ></q-input>
      <q-input
        outlined
        :readonly="readonly"
        v-model="contact.last_name"
        label="Příjmení"
        class="flex-1"
      ></q-input>
      <q-input
        outlined
        :readonly="readonly"
        v-model="contact.title_post"
        label="Titul za"
      ></q-input>
    </div>
    <div class="flex gap-2">
      <q-input
        outlined
        :readonly="readonly"
        v-model="contact.email"
        label="Email"
        type="email"
        class="flex-1"
      ></q-input>
      <q-input
        outlined
        :readonly="readonly"
        v-model="contact.phone"
        label="Telefon"
        class="flex-1"
      ></q-input>

      <q-input
        outlined
        landscape
        :readonly="readonly"
        v-model="contact.birth_date"
        label="Datum narození"
        class="flex-1"
      ></q-input>
      <q-input
        outlined
        :readonly="readonly"
        v-model="contact.profile_picture_url"
        label="URL profilového obrázku"
        class="flex-1"
      ></q-input>
    </div>
    <div class="flex gap-2">
      <q-input
        outlined
        :readonly="readonly"
        v-model="contact.street"
        label="Ulice"
        class="flex-[2]"
      ></q-input>
      <q-input
        outlined
        :readonly="readonly"
        v-model="contact.city"
        label="Město"
        class="flex-1"
      ></q-input>
      <q-input outlined :readonly="readonly" v-model="contact.postal_code" label="PSČ"></q-input>
      <q-input outlined :readonly="readonly" v-model="contact.state" label="Stát"></q-input>
    </div>
    <q-input
      outlined
      :readonly="readonly"
      v-model="contact.note"
      label="Poznámka"
      type="textarea"
      rows="3"
    ></q-input>
  </q-form>
</template>

<script setup lang="ts">
defineProps<{ readonly?: boolean }>()

interface CusomerContactPersonIn {
  title_pre: string
  first_name: string
  middle_name: string
  last_name: string
  title_post: string
  email: string
  phone: string
  birth_date: string
  street: string
  city: string
  postal_code: string
  state: string
  profile_picture_url: string
  is_deleted: boolean
  note: string
}

const contact = defineModel<CusomerContactPersonIn>({
  default: {
    title_pre: '',
    first_name: '',
    middle_name: '',
    last_name: '',
    title_post: '',
    email: '',
    phone: '',
    birth_date: new Date(1990, 0, 1),
    street: '',
    city: '',
    postal_code: '',
    state: '',
    profile_picture_url: '',
    is_deleted: false,
    note: '',
  },
})
</script>

<style lang="scss" scoped></style>
