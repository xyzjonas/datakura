<template>
  <div v-if="credit_note" class="w-full flex flex-col gap-2">
    <q-breadcrumbs class="mb-5">
      <q-breadcrumbs-el label="Home" :to="{ name: 'home' }" />
      <q-breadcrumbs-el label="Dobropisy" :to="{ name: 'creditNotes' }" />
      <q-breadcrumbs-el :label="credit_note.code" />
    </q-breadcrumbs>

    <div class="mb-2 flex justify-between items-center">
      <div class="flex gap-2 items-center">
        <div>
          <span class="text-gray-5 flex items-center gap-1">DOBROPIS</span>
          <h1 class="text-primary mb-1 text-5xl">{{ credit_note.code }}</h1>
          <div class="flex items-center gap-1">
            <h5>{{ credit_note.code }}</h5>
            <CopyToClipBoardButton v-if="credit_note.code" :text="credit_note.code" />
          </div>
        </div>
        <GenericStateBadge :state="credit_note.state" />
      </div>
      <PrintDropdownButton
        :items="[
          {
            label: 'PDF bez cen',
            onClick: openPdf,
          },
        ]"
      />
    </div>

    <div class="flex gap-2">
      <CustomerCard :customer="credit_note.order.supplier" title="DODAVATEL" class="flex-1" />
      <LinkedEntitiesCard show-inbound-order :inbound-order="credit_note.order" />
    </div>

    <div class="flex items-center gap-2 mt-5">
      <!-- <CurrencyDropdown v-model="credit_note.currency" /> -->
      <h2>Položky dobropisu</h2>
      <TotalPrice
        :order="{ items: credit_note.items, currency: credit_note.order.currency }"
        negative
        class="ml-auto"
      />
    </div>
    <div>
      <ProductsList
        v-model:items="credit_note.items"
        :currency="credit_note.order.currency"
        readonly
      />
    </div>
  </div>
  <ForegroundPanel v-else class="grid justify-center w-full content-center text-center">
    <span class="text-5xl text-gray-5">404</span>
    <span class="text-lg text-gray-5"> OBJEDNÁVKA NENALEZENA </span>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesCreditNotesGetCreditNoteToSupplier,
  warehouseApiRoutesInboundOrdersGetInboundOrderPdf,
  type CreditNoteSupplierSchema,
} from '@/client'
import CopyToClipBoardButton from '@/components/CopyToClipBoardButton.vue'
import CustomerCard from '@/components/customer/CustomerCard.vue'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import GenericStateBadge from '@/components/GenericStateBadge.vue'
import LinkedEntitiesCard from '@/components/order/LinkedEntitiesCard.vue'
import ProductsList from '@/components/order/ProductsList.vue'
import TotalPrice from '@/components/order/TotalPrice.vue'
import PrintDropdownButton from '@/components/PrintDropdownButton.vue'
import { useApi } from '@/composables/use-api'
import { ref } from 'vue'

const props = defineProps<{ code: string }>()
const credit_note = ref<CreditNoteSupplierSchema>()

const { onResponse } = useApi()

const response = await warehouseApiRoutesCreditNotesGetCreditNoteToSupplier({
  path: { note_code: props.code },
})
const data = onResponse(response)
if (data) {
  credit_note.value = data.data
}

const openPdf = async () => {
  const resonse = await warehouseApiRoutesInboundOrdersGetInboundOrderPdf({
    path: { order_code: props.code },
  })
  if (!resonse.error) {
    const blobUrl = URL.createObjectURL(resonse.data as unknown as Blob)
    window.open(blobUrl, '_blank')
    setTimeout(() => URL.revokeObjectURL(blobUrl), 100)
  }
}
</script>

<style lang="scss" scoped></style>
