<template>
  <div v-if="invoice" class="flex w-full flex-col gap-3">
    <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
      <q-breadcrumbs>
        <q-breadcrumbs-el label="Home" :to="{ name: 'home' }" />
        <q-breadcrumbs-el label="Faktury" :to="{ name: 'invoices' }" />
        <q-breadcrumbs-el :label="invoice.code" />
      </q-breadcrumbs>

      <div class="flex flex-wrap items-center justify-end gap-2">
        <q-btn unelevated color="primary" icon="edit" label="Upravit" @click="openEditDialog" />
        <q-btn
          v-if="!invoice.paid_date"
          unelevated
          color="positive"
          icon="sym_o_paid"
          label="Označit jako uhrazeno"
          :loading="markPaidLoading"
          @click="markAsPaid"
        />
        <PrintDropdownButton
          :items="[
            {
              label: 'Stáhnout PDF',
              onClick: openPdf,
            },
          ]"
        />
      </div>
    </div>

    <div class="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
      <div>
        <span class="flex items-center gap-1 text-muted">FAKTURA</span>
        <h1 class="mb-1 text-5xl text-primary">{{ invoice.code }}</h1>
        <div class="flex flex-wrap items-center gap-2 text-muted">
          <span>{{ invoice.issued_date }}</span>
          <span>/</span>
          <span>splatnost {{ invoice.due_date }}</span>
        </div>
      </div>

      <div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <ForegroundPanel class="min-w-[10rem]">
          <div class="text-xs uppercase text-muted">Platební metoda</div>
          <div class="mt-2 text-lg font-semibold">{{ invoice.payment_method.name }}</div>
        </ForegroundPanel>
        <ForegroundPanel class="min-w-[10rem]">
          <div class="text-xs uppercase text-muted">Měna</div>
          <div class="mt-2 text-lg font-semibold">{{ invoice.currency }}</div>
        </ForegroundPanel>
        <ForegroundPanel class="min-w-[10rem]">
          <div class="text-xs uppercase text-muted">Objednávky</div>
          <div class="mt-2 text-lg font-semibold">{{ invoiceOrders.length }}</div>
        </ForegroundPanel>
        <ForegroundPanel class="min-w-[10rem]">
          <div class="text-xs uppercase text-muted font-bold">Celkem</div>
          <div class="mt-2 text-lg font-semibold text-primary">
            {{ invoiceTotal.toFixed(2) }} {{ invoice.currency }}
          </div>
        </ForegroundPanel>
      </div>
    </div>

    <div class="grid gap-3 lg:grid-cols-[1fr_1fr_0.9fr]">
      <CustomerCard v-if="invoice.customer" :customer="invoice.customer" title="ODBĚRATEL" />
      <ForegroundPanel v-else class="flex items-center justify-center text-gray-5">
        Odběratel není vyplněn.
      </ForegroundPanel>

      <CustomerCard v-if="invoice.supplier" :customer="invoice.supplier" title="DODAVATEL" />
      <ForegroundPanel v-else class="flex items-center justify-center text-gray-5">
        Dodavatel není vyplněn.
      </ForegroundPanel>

      <ForegroundPanel class="flex flex-col gap-3">
        <div>
          <div class="text-xs uppercase tracking-[0.16em] text-gray-5">DUZP</div>
          <div class="mt-1 text-lg font-semibold">{{ invoice.taxable_supply_date }}</div>
        </div>
        <div v-if="invoice.external_code">
          <div class="text-xs uppercase tracking-[0.16em] text-gray-5">Externí číslo</div>
          <div class="mt-1 text-sm font-semibold">{{ invoice.external_code }}</div>
        </div>
        <div v-if="invoice.paid_date">
          <div class="text-xs uppercase tracking-[0.16em] text-gray-5">Uhrazeno</div>
          <div class="mt-1 text-sm font-semibold">{{ invoice.paid_date }}</div>
        </div>
        <div class="rounded bg-[#f7fafc] p-3 text-sm text-gray-6">
          {{ invoice.note || 'Faktura byla vygenerována nebo přiložena ke zvoleným objednávkám.' }}
        </div>
      </ForegroundPanel>
    </div>

    <div class="mt-4 flex items-center justify-between gap-3">
      <div>
        <h2>Položky faktury</h2>
        <div class="mt-1 text-sm text-gray-6">{{ itemsSectionDescription }}</div>
      </div>
    </div>

    <div class="flex flex-col gap-3">
      <ForegroundPanel v-for="order in invoiceOrders" :key="order.code" class="overflow-hidden">
        <div class="flex flex-col gap-4 p-4 md:flex-row md:items-start md:justify-between">
          <div>
            <div class="text-xs uppercase tracking-[0.16em] text-gray-5">Objednávka</div>
            <div class="mt-2 flex flex-wrap items-center gap-3">
              <button
                class="text-left text-2xl font-semibold text-primary"
                @click="goToOrder(order.code)"
              >
                {{ order.code }}
              </button>
              <component :is="orderStateBadge" :state="order.state" />
            </div>
            <div v-if="order.external_code" class="mt-1 text-sm text-gray-6">
              Externí kód: {{ order.external_code }}
            </div>
          </div>

          <div class="text-right">
            <div class="text-xs uppercase tracking-[0.16em] text-gray-5">Mezisoučet</div>
            <div class="mt-2 text-2xl font-semibold text-slate-8">
              {{ getOrderTotal(order).toFixed(2) }} {{ invoice.currency }}
            </div>
          </div>
        </div>

        <q-markup-table flat square class="border-t border-[#e8edf2] bg-transparent">
          <thead>
            <tr>
              <th class="text-left">Položka</th>
              <th class="text-right">Množství</th>
              <th class="text-right">Cena / MJ</th>
              <th class="text-right">Celkem</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in order.items"
              :key="`${order.code}-${item.index}-${item.product.code}`"
            >
              <td>
                <div class="font-semibold">{{ item.product.name }}</div>
                <div class="text-xs text-gray-5">{{ item.product.code }}</div>
              </td>
              <td class="text-right">{{ item.amount.toFixed(4) }} {{ item.product.unit ?? '' }}</td>
              <td class="text-right">{{ item.unit_price.toFixed(4) }} {{ invoice.currency }}</td>
              <td class="text-right font-semibold">
                {{ item.total_price.toFixed(4) }} {{ invoice.currency }}
              </td>
            </tr>
          </tbody>
        </q-markup-table>
      </ForegroundPanel>
    </div>
  </div>

  <ForegroundPanel v-else class="grid w-full content-center justify-center text-center">
    <span class="text-5xl text-gray-5">404</span>
    <span class="text-lg text-gray-5">FAKTURA NENALEZENA</span>
  </ForegroundPanel>

  <InvoiceUpsertDialog
    v-model:show="editDialog"
    v-model="invoiceForm"
    title="Upravit fakturu"
    submit-label="Uložit změny"
    :loading="editLoading"
    :default-customer="invoice?.customer ?? null"
    :default-supplier="invoice?.supplier ?? null"
    :existing-document="invoice?.document ?? null"
    :require-invoice-file="false"
    @submit="saveInvoice"
  />
</template>

<script setup lang="ts">
import {
  type GetInvoiceResponse,
  type InvoiceStoreSchema,
  warehouseApiRoutesInvoicesGetInvoice,
  warehouseApiRoutesInvoicesGetInvoicePdf,
  type InvoiceDetailSchema,
} from '@/client'
import { formDataBodySerializer } from '@/client/client'
import { client } from '@/client/client.gen'
import CustomerCard from '@/components/customer/CustomerCard.vue'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import InboundOrderStateBadge from '@/components/order/InboundOrderStateBadge.vue'
import type { InvoiceUpsertSubmitPayload } from '@/components/order/invoice-upload'
import { toInvoiceMultipartBody } from '@/components/order/invoice-upload'
import InvoiceUpsertDialog from '@/components/order/InvoiceUpsertDialog.vue'
import OutboundOrderStateBadge from '@/components/order/OutboundOrderStateBadge.vue'
import PrintDropdownButton from '@/components/PrintDropdownButton.vue'
import { useApi } from '@/composables/use-api'
import { useAppRouter } from '@/composables/use-app-router'
import { useQuasar } from 'quasar'
import { computed, ref, watch } from 'vue'
import {
  getInvoiceDetailDirection,
  getInvoiceDetailOrders,
  getInvoiceDetailOrderTotal,
  getInvoiceDetailTotal,
  type InvoiceDetailLike,
  type InvoiceDetailOrderLike,
} from './invoice-detail'

const props = defineProps<{ code: string }>()
type InvoiceDetailModel = InvoiceDetailSchema & InvoiceDetailLike

const invoice = ref<InvoiceDetailModel>()
const editDialog = ref(false)
const editLoading = ref(false)
const markPaidLoading = ref(false)
const invoiceForm = ref<InvoiceStoreSchema>({
  code: '',
  issued_date: '',
  due_date: '',
  payment_method_name: '',
  taxable_supply_date: '',
  currency: 'CZK',
  external_code: undefined,
  paid_date: undefined,
  note: undefined,
  customer_code: undefined,
  supplier_code: undefined,
})

const { onResponse } = useApi()
const { goToInvoice, goToOrderIn, goToOrderOut } = useAppRouter()
const $q = useQuasar()

const toInvoiceForm = (currentInvoice?: InvoiceDetailModel): InvoiceStoreSchema => ({
  code: currentInvoice?.code ?? '',
  issued_date: currentInvoice?.issued_date ?? '',
  due_date: currentInvoice?.due_date ?? '',
  payment_method_name: currentInvoice?.payment_method.name ?? '',
  taxable_supply_date: currentInvoice?.taxable_supply_date ?? '',
  currency: currentInvoice?.currency ?? 'CZK',
  external_code: currentInvoice?.external_code ?? undefined,
  paid_date: currentInvoice?.paid_date ?? undefined,
  note: currentInvoice?.note ?? undefined,
  customer_code: currentInvoice?.customer?.code,
  supplier_code: currentInvoice?.supplier?.code,
})

const setInvoice = (nextInvoice?: InvoiceDetailSchema) => {
  invoice.value = nextInvoice as InvoiceDetailModel | undefined
  invoiceForm.value = toInvoiceForm(invoice.value)
}

const loadInvoice = async (invoiceCode: string) => {
  const response = await warehouseApiRoutesInvoicesGetInvoice({
    path: { invoice_code: invoiceCode },
  })
  const data = onResponse(response)
  if (data) {
    setInvoice(data.data)
  }
}

watch(
  () => props.code,
  async (invoiceCode) => {
    await loadInvoice(invoiceCode)
  },
  { immediate: true },
)

const invoiceDirection = computed(() => getInvoiceDetailDirection(invoice.value))
const invoiceOrders = computed(() => getInvoiceDetailOrders(invoice.value))
const invoiceTotal = computed(() => getInvoiceDetailTotal(invoice.value))
const orderStateBadge = computed(() =>
  invoiceDirection.value === 'outbound' ? OutboundOrderStateBadge : InboundOrderStateBadge,
)
const itemsSectionDescription = computed(() =>
  invoiceDirection.value === 'outbound'
    ? 'Seskupeno podle vydané objednávky.'
    : 'Seskupeno podle přijaté objednávky.',
)

const getOrderTotal = (order: InvoiceDetailOrderLike) => getInvoiceDetailOrderTotal(order)

const openEditDialog = () => {
  invoiceForm.value = toInvoiceForm(invoice.value)
  editDialog.value = true
}

const goToOrder = (code: string) => {
  if (invoiceDirection.value === 'outbound') {
    goToOrderOut(code)
    return
  }

  goToOrderIn(code)
}

const saveInvoice = async (payload: InvoiceUpsertSubmitPayload) => {
  if (!invoice.value) {
    return
  }

  editLoading.value = true
  try {
    const response = await client.put<{ 200: GetInvoiceResponse }>({
      ...formDataBodySerializer,
      security: [
        {
          in: 'cookie',
          name: 'sessionid',
          type: 'apiKey',
        },
      ],
      headers: { 'Content-Type': null },
      url: '/api/v1/invoices/{invoice_code}',
      path: { invoice_code: invoice.value.code },
      body: toInvoiceMultipartBody(payload),
    })
    const data = onResponse(response)
    if (data?.data) {
      const previousCode = invoice.value.code
      setInvoice(data.data)
      editDialog.value = false
      $q.notify({
        type: 'positive',
        message: 'Faktura byla aktualizována.',
      })
      if (data.data.code !== previousCode) {
        goToInvoice(data.data.code)
      }
    }
  } finally {
    editLoading.value = false
  }
}

const markAsPaid = async () => {
  if (!invoice.value || invoice.value.paid_date) {
    return
  }

  markPaidLoading.value = true
  try {
    const paidDate = new Date().toISOString().split('T')[0]
    const response = await client.post<{ 200: GetInvoiceResponse }>({
      security: [
        {
          in: 'cookie',
          name: 'sessionid',
          type: 'apiKey',
        },
      ],
      url: '/api/v1/invoices/{invoice_code}/mark-paid',
      path: { invoice_code: invoice.value.code },
      body: { paid_date: paidDate },
    })
    const data = onResponse(response)
    if (data?.data) {
      setInvoice(data.data)
      $q.notify({
        type: 'positive',
        message: 'Faktura byla označena jako uhrazená.',
      })
    }
  } finally {
    markPaidLoading.value = false
  }
}

const openPdf = async () => {
  const response = await warehouseApiRoutesInvoicesGetInvoicePdf({
    path: { invoice_code: invoice.value?.code ?? props.code },
  })
  if (!response.error) {
    const blobUrl = URL.createObjectURL(response.data as unknown as Blob)
    window.open(blobUrl, '_blank')
    setTimeout(() => URL.revokeObjectURL(blobUrl), 100)
  }
}
</script>
