<template>
  <div v-if="customer" class="flex flex-col gap-2 flex-1">
    <div class="flex gap-2">
      <ForegroundPanel class="flex flex-col min-w-[312px] flex-[2] min-w-sm">
        <span class="text-gray-5 flex items-center gap-1 capitalize">
          <CustomerTypeIcon :type="customer.customer_type" />
          {{ customer.customer_type.toLowerCase() }}
        </span>
        <div class="flex items-center flex-nowrap justify-between">
          <h1 class="text-primary mb-1">{{ customer.name }}</h1>
          <div class="flex flex-col items-end flex-nowrap gap-1">
            <span class="flex items-center gap-1 flex-nowrap whitespace-nowrap">
              <q-icon name="groups"></q-icon>
              {{ customer.group.name }}
            </span>
            <span class="flex items-center gap-1 flex-nowrap whitespace-nowrap">
              <q-icon name="percent"></q-icon>
              {{ customer.discount_group?.name ?? 'Bez slevové skupiny' }}
              <small v-if="customer.discount_group" class="text-gray-5">
                ({{ customer.discount_group.discount_percent }} %)
              </small>
            </span>
            <span class="text-gray-5">
              <q-btn flat round size="8px" icon="content_copy" />
              <small>kód: </small>{{ customer.code }}
            </span>
          </div>
        </div>

        <CustomerInformationForm v-model="customerInformation" readonly class="my-2" />

        <div class="mt-auto flex gap-2 flex-row-reverse">
          <q-btn
            outline
            color="primary"
            icon="sym_o_percent"
            label="změnit slevovou skupinu"
            @click="showDiscountDialog = true"
          ></q-btn>
          <q-btn
            outline
            color="primary"
            icon="sym_o_order_play"
            label="rychlá objednávka"
            disable
          ></q-btn>
          <q-btn outline color="primary" icon="edit" label="upravit" disable></q-btn>
        </div>
      </ForegroundPanel>
      <ForegroundPanel class="flex-1 min-w-sm">
        <CustomerContactForm v-model="customerContact" class="h-full" readonly />
      </ForegroundPanel>
    </div>
    <div class="flex flex-col gap-2 flex-nowrap">
      <ForegroundPanel v-for="(contact, index) in customerContacts" :key="index" class="flex-1">
        <q-expansion-item
          icon="sym_o_contact_phone"
          :label="`${contact.title_pre} ${contact.first_name} ${contact.last_name} ${contact.title_post}`"
          :caption="contact.email"
        >
          <CustomerContactPersonForm v-model="customerContacts[index]" readonly class="mt-2" />
        </q-expansion-item>
      </ForegroundPanel>
      <EmptyPanel class="flex-1 py-5">
        <div class="flex flex-col justify-center items-center">
          <q-btn flat icon="add" label="Přidat nový kontakt" disable />
        </div>
      </EmptyPanel>
    </div>
  </div>
  <ForegroundPanel v-else class="grid justify-center w-full content-center text-center">
    <span class="text-5xl text-gray-5">404</span>
    <span class="text-lg text-gray-5"> ZÁKAZNÍK NENALEZEN </span>
  </ForegroundPanel>

  <CustomerDiscountGroupDialog
    v-model:show="showDiscountDialog"
    :current-code="customer?.discount_group?.code ?? null"
    :groups="discountGroups"
    :loading="assigningDiscountGroup"
    @submit="onAssignDiscountGroup"
  />
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesCustomerAssignCustomerDiscountGroup,
  warehouseApiRoutesCustomerGetCustomer,
  warehouseApiRoutesProductGetDiscountGroups,
} from '@/client'
import CustomerContactForm from '@/components/customer/CustomerContactForm.vue'
import CustomerDiscountGroupDialog from '@/components/customer/CustomerDiscountGroupDialog.vue'
import CustomerContactPersonForm from '@/components/customer/CustomerContactPersonForm.vue'
import CustomerInformationForm from '@/components/customer/CustomerInformationForm.vue'
import CustomerTypeIcon from '@/components/customer/CustomerTypeIcon.vue'
import EmptyPanel from '@/components/EmptyPanel.vue'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import { useApi } from '@/composables/use-api'
import { useQuasar } from 'quasar'
import { ref } from 'vue'

const props = defineProps<{
  customerCode: string
}>()

const { onResponse } = useApi()
const $q = useQuasar()
const showDiscountDialog = ref(false)
const assigningDiscountGroup = ref(false)

const result = await warehouseApiRoutesCustomerGetCustomer({
  path: { customer_code: props.customerCode },
})

const discountGroupsResult = await warehouseApiRoutesProductGetDiscountGroups()
const discountGroups = ref(discountGroupsResult.data?.data ?? [])

const customer = ref(result.data?.data)
const customerContact = ref()
if (customer.value) {
  customerContact.value = {
    email: customer.value.email,
    phone: customer.value.phone,
    street: customer.value.street,
    city: customer.value.city,
    postal_code: customer.value.postal_code,
    state: customer.value.state,
  }
}

const customerInformation = ref()
if (customer.value) {
  customerInformation.value = {
    identification: customer.value.identification,
    tax_identification: customer.value.tax_identification,
    name: customer.value.name,
    code: customer.value.code,
    customer_type: customer.value.customer_type,
    price_type: customer.value.price_type,
    invoice_due_days: customer.value.invoice_due_days,
    block_after_due_days: customer.value.block_after_due_days,
    data_collection_agreement: customer.value.data_collection_agreement,
    marketing_data_use_agreement: customer.value.marketing_data_use_agreement,
    is_valid: customer.value.is_valid,
    is_deleted: customer.value.is_deleted,
    owner: customer.value.owner,
    responsible_user: customer.value.responsible_user,
    group: customer.value.group.name,
    discount_group: customer.value.discount_group?.name ?? '',
    note: customer.value.note,
    register_information: customer.value.register_information,
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const customerContacts = ref<any[]>([])
if (customer.value && customer.value.contacts) {
  console.info(customer.value.contacts)
  customerContacts.value = customer.value.contacts.map((contact) => {
    return {
      title_pre: contact.title_pre || '',
      first_name: contact.first_name || '',
      middle_name: contact.middle_name || '',
      last_name: contact.last_name || '',
      title_post: contact.title_post || '',
      email: contact.email || '',
      phone: contact.phone || '',
      birth_date: contact.birth_date ? new Date(contact.birth_date) : new Date(1990, 0, 1),
      street: contact.street || '',
      city: contact.city || '',
      postal_code: contact.postal_code || '',
      state: contact.state || '',
      profile_picture_url: contact.profile_picture_url || '',
      is_deleted: contact.is_deleted || false,
      note: contact.note || '',
    }
  })
}

const onAssignDiscountGroup = async (discountGroupCode: string | null) => {
  if (!customer.value) {
    return
  }

  assigningDiscountGroup.value = true
  try {
    const result = await warehouseApiRoutesCustomerAssignCustomerDiscountGroup({
      path: { customer_code: customer.value.code },
      body: {
        discount_group_code: discountGroupCode,
      },
    })

    const response = onResponse(result)
    if (!response?.data) {
      return
    }

    customer.value = response.data
    customerInformation.value.discount_group = customer.value.discount_group?.name ?? ''
    showDiscountDialog.value = false
    $q.notify({ type: 'positive', message: 'Slevová skupina byla aktualizována.' })
  } finally {
    assigningDiscountGroup.value = false
  }
}
</script>

<style></style>
