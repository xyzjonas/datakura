<template>
  <div v-if="product" class="flex flex-col gap-2 flex-1">
    <div class="flex gap-2">
      <ForegroundPanel class="flex flex-col min-w-[312px] flex-1">
        <span class="text-gray-5 flex items-center gap-1 mb-1">
          <ProductTypeIcon :type="product.type" />
          {{ product.type }}
        </span>
        <h1 class="text-primary mb-1">{{ product.name }}</h1>
        <span class="flex items-center gap-1 mb-3">
          <small class="text-gray-5">kód:</small>
          <h5>{{ product.code }}</h5>
          <q-btn flat round size="8px" icon="content_copy"></q-btn>
        </span>

        <div class="mt-2">
          <q-list bordered separator dense class="rounded">
            <q-item>
              <q-item-section>Měrná jednotka</q-item-section>
              <q-item-section avatar>{{ product.unit }}</q-item-section>
            </q-item>
          </q-list>
        </div>

        <q-list dense class="mt-2">
          <q-item>
            <q-item-section>Skupina zboží</q-item-section>
            <q-item-section
              :class="{ 'font-bold': product.group, 'text-gray-5': !product.group }"
              avatar
              >{{ product.group ?? '-' }}</q-item-section
            >
          </q-item>
          <q-item>
            <q-item-section>Nákupní cena</q-item-section>
            <q-item-section avatar>235.686047</q-item-section>
          </q-item>
          <q-item>
            <q-item-section>Celní nomenklatura</q-item-section>
            <q-item-section avatar :class="{ 'text-gray-5': true }">-</q-item-section>
          </q-item>
          <q-item>
            <q-item-section>DIN_94</q-item-section>
            <q-item-section avatar>DIN 94</q-item-section>
          </q-item>
        </q-list>

        <div class="mt-5 flex flex-row-reverse">
          <q-btn outline color="primary" icon="edit" label="upravit" disable></q-btn>
        </div>
      </ForegroundPanel>
      <ForegroundPanel class="flex-[2] flex flex-col">
        <h2 class="mb-4">Ceník</h2>
        <q-table
          :rows="prices"
          :columns="columns"
          flat
          hide-pagination
          :pagination="{ rowsPerPage: -1 }"
          class="bg-transparent"
        ></q-table>
        <div class="flex flex-row-reverse mt-auto">
          <q-btn outline color="primary" icon="attach_money" label="přidat cenu" disable></q-btn>
        </div>
      </ForegroundPanel>
    </div>
    <div class="flex gap-2 flex-1">
      <WarehouseCard :product-code="product.code" :product-unit="product.unit" />
    </div>
  </div>
  <ForegroundPanel v-else class="grid justify-center"> PRODUKT NENALEZEN </ForegroundPanel>
</template>

<script setup lang="ts">
import { warehouseApiRoutesProductGetProduct } from '@/client'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import ProductTypeIcon from '@/components/product/ProductTypeIcon.vue'
import WarehouseCard from '@/components/product/WarehouseCard.vue'
import type { QTableColumn } from 'quasar'
import { ref } from 'vue'

const props = defineProps<{
  productCode: string
}>()

const result = await warehouseApiRoutesProductGetProduct({
  path: { product_code: props.productCode },
})

const product = ref(result.data?.data)

const prices = [
  {
    type: 'Prodejní',
    customer: 'AKROS, s.r.o.',
    minimum: 0,
    maximum: 100,
    currency: 'CZK',
    unit: '100ks',
    amount: 1,
    price: 777.77,
  },
]

const columns: QTableColumn[] = [
  {
    name: 'type',
    label: 'Typ ceny',
    field: 'type',
    align: 'left',
  },
  {
    name: 'customer',
    label: 'Zákazník',
    field: 'customer',
    align: 'left',
  },
  {
    name: 'minimum',
    label: 'Minimální počet',
    field: 'minimum',
    align: 'left',
  },
  {
    name: 'maximum',
    label: 'Maximální počet',
    field: 'maximum',
    align: 'left',
  },
  {
    name: 'currency',
    label: 'Měna',
    field: 'currency',
    align: 'left',
  },
  {
    name: 'unit',
    label: 'Jednotka',
    field: 'unit',
    align: 'left',
  },
  {
    name: 'amount',
    label: 'Počet jednotek',
    field: 'amount',
    align: 'left',
  },
  {
    name: 'price',
    label: 'Cena',
    field: 'price',
    classes: 'text-primary font-bold',
  },
]
</script>

<style></style>
