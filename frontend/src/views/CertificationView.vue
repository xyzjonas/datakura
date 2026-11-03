<template>
  <div v-if="certification" class="flex flex-col gap-3 flex-1">
    <q-breadcrumbs class="mb-2">
      <q-breadcrumbs-el label="Domů" :to="{ name: 'home' }" />
      <q-breadcrumbs-el :label="`Certifikace ${certification.code}`" />
    </q-breadcrumbs>

    <ForegroundPanel class="flex flex-col gap-3" data-test="certification-detail">
      <div class="flex justify-between items-start gap-4 flex-wrap">
        <div class="min-w-0">
          <span class="text-gray-5 flex items-center gap-1 mb-1">
            <q-icon name="sym_o_verified" size="18px" /> CERTIFIKACE
          </span>
          <h1 class="text-primary mb-1" data-test="certification-code">{{ certification.code }}</h1>
          <p v-if="certification.description" class="text-gray-6 whitespace-pre-line">
            {{ certification.description }}
          </p>
        </div>
        <q-btn
          v-if="certification.attachment"
          unelevated
          color="primary"
          no-caps
          icon="sym_o_description"
          :label="certification.attachment.name"
          :href="certification.attachment.url"
          target="_blank"
          rel="noopener"
          data-test="certification-open-file"
        />
        <span v-else class="text-gray-5 italic">bez přílohy</span>
      </div>

      <div v-if="certification.batch_codes?.length" class="flex items-center gap-2 flex-wrap">
        <span class="text-gray-5 text-sm">Šarže:</span>
        <BatchBadge v-for="code in certification.batch_codes" :key="code" :batch-code="code" />
      </div>
    </ForegroundPanel>

    <ForegroundPanel>
      <div class="flex items-center justify-between mb-3">
        <h2>Skladem s touto certifikací</h2>
        <span class="text-gray-5 text-sm" data-test="items-count">{{ items.length }} pol.</span>
      </div>
      <q-table
        :rows="items"
        :columns="columns"
        row-key="id"
        flat
        class="bg-transparent"
        :pagination="{ rowsPerPage: 20 }"
        no-data-label="Žádné zboží s touto certifikací není skladem"
      >
        <template #body-cell-product="props">
          <q-td>
            <router-link
              :to="{ name: 'productDetail', params: { productCode: props.row.product.code } }"
              class="link"
              >{{ props.row.product.name }}</router-link
            >
            <div class="text-xs text-gray-5">{{ props.row.product.code }}</div>
          </q-td>
        </template>
        <template #body-cell-batch="props">
          <q-td auto-width>
            <BatchBadge :batch-code="props.row.batch?.primary_barcode?.code" />
          </q-td>
        </template>
        <template #body-cell-packaging="props">
          <q-td auto-width><PackageTypeBadge :package-type="props.value" /></q-td>
        </template>
        <template #body-cell-location="props">
          <q-td>
            <router-link
              v-if="props.row.location"
              :to="{ name: 'warehouses', query: { location: props.row.location.code } }"
              class="link"
              >{{ props.row.location.code }}</router-link
            >
          </q-td>
        </template>
        <template #body-cell-amount="props">
          <q-td auto-width><WarehouseItemCountBadge :item="props.row" /></q-td>
        </template>
        <template #body-cell-detail="props">
          <q-td auto-width>
            <q-btn
              flat
              round
              size="sm"
              icon="sym_o_open_in_new"
              :to="{ name: 'warehouseItemDetail', params: { itemId: props.row.id } }"
            />
          </q-td>
        </template>
      </q-table>
    </ForegroundPanel>
  </div>
  <ForegroundPanel v-else class="grid justify-center w-full content-center text-center">
    <span class="text-5xl text-gray-5">404</span>
    <span class="text-lg text-gray-5">CERTIFIKACE NENALEZENA</span>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesCertificationsGetCertification,
  warehouseApiRoutesCertificationsGetCertificationItems,
  type WarehouseItemSchema,
} from '@/client'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import PackageTypeBadge from '@/components/PackageTypeBadge.vue'
import WarehouseItemCountBadge from '@/components/product/WarehouseItemCountBadge.vue'
import BatchBadge from '@/components/warehouse/BatchBadge.vue'
import { useApi } from '@/composables/use-api'
import type { QTableColumn } from 'quasar'

const props = defineProps<{ id: string }>()

const { onResponse } = useApi()

const [certificationResponse, itemsResponse] = await Promise.all([
  warehouseApiRoutesCertificationsGetCertification({
    path: { certification_id: Number(props.id) },
  }),
  warehouseApiRoutesCertificationsGetCertificationItems({
    path: { certification_id: Number(props.id) },
  }),
])

const certification = onResponse(certificationResponse, { hideNotification: true })?.data
const items: WarehouseItemSchema[] =
  onResponse(itemsResponse, { hideNotification: true })?.data ?? []

const columns: QTableColumn<WarehouseItemSchema>[] = [
  {
    name: 'product',
    label: 'Produkt',
    field: (i) => i.product.name,
    align: 'left',
    sortable: true,
  },
  {
    name: 'batch',
    label: 'Šarže',
    field: (i) => i.batch?.primary_barcode?.code ?? '',
    align: 'left',
    sortable: true,
  },
  { name: 'packaging', label: 'Balení', field: (i) => i.package?.type, align: 'left' },
  {
    name: 'location',
    label: 'Lokace',
    field: (i) => i.location?.code ?? '',
    align: 'left',
    sortable: true,
  },
  { name: 'amount', label: 'Množství', field: (i) => i.amount, align: 'left', sortable: true },
  { name: 'detail', label: '', field: () => '', align: 'right' },
]
</script>
