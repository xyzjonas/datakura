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
          <q-btn
            outline
            color="primary"
            icon="edit"
            label="upravit"
            @click="onEditCustomer"
          ></q-btn>
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
          <div class="mt-2 flex gap-2">
            <CustomerContactPersonForm v-model="customerContacts[index]" readonly class="flex-1" />
            <div class="flex flex-col gap-2">
              <q-btn flat round icon="edit" @click="onEditContact(index)" size="md" />
              <q-btn
                flat
                round
                icon="delete"
                color="negative"
                @click="onDeleteContact(index)"
                size="md"
              />
            </div>
          </div>
        </q-expansion-item>
      </ForegroundPanel>
      <EmptyPanel class="flex-1 py-5">
        <div class="flex flex-col justify-center items-center">
          <q-btn flat icon="add" label="Přidat nový kontakt" @click="onAddContact" />
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

  <CustomerUpsertDialog
    v-model:show="showCustomerUpsertDialog"
    v-model="editingCustomer"
    :customer-groups="customerGroups"
    :title="`${isCreatingCustomer ? 'Nový' : 'Upravit'} Zákazník`"
    :submit-label="isCreatingCustomer ? 'vytvořit' : 'aktualizovat'"
    :loading="savingCustomer"
    @submit="onSaveCustomer"
  />

  <ContactPersonUpsertDialog
    v-model:show="showContactUpsertDialog"
    v-model="editingContact"
    :title="`${isCreatingContact ? 'Nový' : 'Upravit'} Kontakt`"
    :submit-label="isCreatingContact ? 'vytvořit' : 'aktualizovat'"
    :loading="savingContact"
    @submit="onSaveContact"
  />
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesCustomerAssignCustomerDiscountGroup,
  warehouseApiRoutesCustomerGroupsGetCustomerGroups,
  warehouseApiRoutesCustomerGetCustomer,
  warehouseApiRoutesProductGetDiscountGroups,
  warehouseApiRoutesCustomerUpdateCustomer,
  warehouseApiRoutesCustomerCreateCustomerContact,
  warehouseApiRoutesCustomerUpdateCustomerContact,
  warehouseApiRoutesCustomerDeleteCustomerContact,
} from '@/client'
import type {
  CustomerCreateOrUpdateSchema,
  CustomerGroupSchema,
  ContactPersonCreateOrUpdateSchema,
} from '@/client'
import CustomerContactForm from '@/components/customer/CustomerContactForm.vue'
import CustomerDiscountGroupDialog from '@/components/customer/CustomerDiscountGroupDialog.vue'
import CustomerUpsertDialog from '@/components/customer/CustomerUpsertDialog.vue'
import ContactPersonUpsertDialog from '@/components/customer/ContactPersonUpsertDialog.vue'
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
const showCustomerUpsertDialog = ref(false)
const savingCustomer = ref(false)
const showContactUpsertDialog = ref(false)
const savingContact = ref(false)
const editingContactIndex = ref<number | null>(null)

const mapContactToEditor = (contact: {
  id?: number
  title_pre?: string | null
  first_name: string
  middle_name?: string | null
  last_name: string
  title_post?: string | null
  email?: string | null
  phone?: string | null
  birth_date?: string | null
  street?: string | null
  city?: string | null
  postal_code?: string | null
  state?: string | null
  profile_picture_url?: string | null
  is_deleted?: boolean
  note?: string | null
}) => ({
  id: contact.id,
  title_pre: contact.title_pre || '',
  first_name: contact.first_name || '',
  middle_name: contact.middle_name || '',
  last_name: contact.last_name || '',
  title_post: contact.title_post || '',
  email: contact.email || '',
  phone: contact.phone || '',
  birth_date: contact.birth_date || '',
  street: contact.street || '',
  city: contact.city || '',
  postal_code: contact.postal_code || '',
  state: contact.state || '',
  profile_picture_url: contact.profile_picture_url || '',
  is_deleted: contact.is_deleted || false,
  note: contact.note || '',
})

const toContactPayload = (body: ContactPersonCreateOrUpdateSchema) => ({
  ...body,
  birth_date: body.birth_date || undefined,
})

const result = await warehouseApiRoutesCustomerGetCustomer({
  path: { customer_code: props.customerCode },
})

const discountGroupsResult = await warehouseApiRoutesProductGetDiscountGroups()
const discountGroups = ref(discountGroupsResult.data?.data ?? [])
const customerGroupsResult = await warehouseApiRoutesCustomerGroupsGetCustomerGroups({
  query: { page: 1, page_size: 200 },
})
const customerGroups = ref<CustomerGroupSchema[]>(customerGroupsResult.data?.data ?? [])

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
  customerContacts.value = customer.value.contacts.map(mapContactToEditor)
}

const editingCustomer = ref<CustomerCreateOrUpdateSchema>({
  code: '',
  name: '',
  customer_type: '',
  price_type: '',
  customer_group_code: '',
})

const editingContact = ref<ContactPersonCreateOrUpdateSchema>({
  first_name: '',
  last_name: '',
  is_deleted: false,
})

const isCreatingCustomer = ref(false)
const isCreatingContact = ref(false)

const onEditCustomer = () => {
  if (!customer.value) return
  isCreatingCustomer.value = false
  editingCustomer.value = {
    code: customer.value.code,
    name: customer.value.name,
    email: customer.value.email,
    phone: customer.value.phone,
    street: customer.value.street,
    city: customer.value.city,
    postal_code: customer.value.postal_code,
    state: customer.value.state,
    identification: customer.value.identification,
    tax_identification: customer.value.tax_identification,
    customer_type: customer.value.customer_type,
    price_type: customer.value.price_type,
    invoice_due_days: customer.value.invoice_due_days,
    block_after_due_days: customer.value.block_after_due_days,
    data_collection_agreement: customer.value.data_collection_agreement,
    marketing_data_use_agreement: customer.value.marketing_data_use_agreement,
    is_valid: customer.value.is_valid,
    is_deleted: customer.value.is_deleted,
    customer_group_code: customer.value.group.code,
    discount_group_code: customer.value.discount_group?.code,
    owner: customer.value.owner,
    responsible_user: customer.value.responsible_user,
    note: customer.value.note,
    register_information: customer.value.register_information,
  }
  showCustomerUpsertDialog.value = true
}

const onSaveCustomer = async (body: CustomerCreateOrUpdateSchema) => {
  if (!customer.value) return

  savingCustomer.value = true
  try {
    const result = await warehouseApiRoutesCustomerUpdateCustomer({
      path: { customer_code: customer.value.code },
      body,
    })

    const response = onResponse(result)
    if (!response?.data) {
      return
    }

    customer.value = response.data
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
    showCustomerUpsertDialog.value = false
    $q.notify({ type: 'positive', message: 'Zákazník byl aktualizován.' })
  } finally {
    savingCustomer.value = false
  }
}

const onAddContact = () => {
  isCreatingContact.value = true
  editingContactIndex.value = null
  editingContact.value = {
    title_pre: '',
    first_name: '',
    middle_name: '',
    last_name: '',
    title_post: '',
    email: '',
    phone: '',
    birth_date: undefined,
    street: '',
    city: '',
    postal_code: '',
    state: '',
    profile_picture_url: '',
    is_deleted: false,
    note: '',
  }
  showContactUpsertDialog.value = true
}

const onEditContact = (index: number) => {
  isCreatingContact.value = false
  editingContactIndex.value = index
  editingContact.value = { ...customerContacts.value[index] }
  showContactUpsertDialog.value = true
}

const onDeleteContact = async (index: number) => {
  const contact = customerContacts.value[index]
  if (!customer.value || !contact.id) return

  $q.dialog({
    title: 'Smazat kontakt',
    message: `Opravdu chcete smazat kontakt ${contact.first_name} ${contact.last_name}?`,
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    try {
      const result = await warehouseApiRoutesCustomerDeleteCustomerContact({
        path: { customer_code: customer.value!.code, contact_id: contact.id },
      })
      const response = onResponse(result)
      if (!response) {
        return
      }
      customerContacts.value.splice(index, 1)
      $q.notify({ type: 'positive', message: 'Kontakt byl smazán.' })
    } catch {
      $q.notify({ type: 'negative', message: 'Chyba při mazání kontaktu.' })
    }
  })
}

const onSaveContact = async (body: ContactPersonCreateOrUpdateSchema) => {
  if (!customer.value) return

  savingContact.value = true
  try {
    if (isCreatingContact.value) {
      const result = await warehouseApiRoutesCustomerCreateCustomerContact({
        path: { customer_code: customer.value.code },
        body: toContactPayload(body),
      })

      const response = onResponse(result)
      if (!response) {
        return
      }

      customerContacts.value.push(mapContactToEditor(response))
      $q.notify({ type: 'positive', message: 'Kontakt byl vytvořen.' })
    } else if (editingContactIndex.value !== null) {
      const contact = customerContacts.value[editingContactIndex.value]
      const result = await warehouseApiRoutesCustomerUpdateCustomerContact({
        path: { customer_code: customer.value.code, contact_id: contact.id },
        body: toContactPayload(body),
      })

      const response = onResponse(result)
      if (!response) {
        return
      }

      customerContacts.value[editingContactIndex.value] = mapContactToEditor(response)
      $q.notify({ type: 'positive', message: 'Kontakt byl aktualizován.' })
    }
    showContactUpsertDialog.value = false
  } finally {
    savingContact.value = false
  }
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
