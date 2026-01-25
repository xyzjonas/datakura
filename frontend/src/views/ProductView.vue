<template>
  <div v-if="product" class="flex flex-col gap-2 flex-1">
    <div class="flex justify-end gap-2">
      <q-btn color="primary" icon="edit" label="upravit" disable></q-btn>
      <q-btn color="primary" icon="copy" label="duplikovat" disable></q-btn>
    </div>
    <div class="flex gap-2">
      <ForegroundPanel class="flex flex-col min-w-[312px] flex-1">
        <span class="text-gray-5 flex items-center gap-1 mb-1">
          <span>
            <ProductTypeIcon :type="product.type" />
            {{ product.type }}
          </span>
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

        <q-list dense class="mt-2 mb-2">
          <q-item>
            <q-item-section>Skupina zboží</q-item-section>
            <q-item-section
              :class="{ 'font-bold': product.group, 'text-gray-5': !product.group }"
              avatar
              >{{ product.group ?? '-' }}</q-item-section
            >
          </q-item>
          <q-item>
            <q-item-section>Průměrná nákupní cena</q-item-section>
            <q-item-section avatar
              >{{ product.purchase_price }}&hairsp;{{ product.currency }}</q-item-section
            >
          </q-item>
          <q-item>
            <q-item-section>Celní nomenklatura</q-item-section>
            <q-item-section avatar :class="{ 'text-gray-5': true }">{{
              product.customs_declaration_group ?? '-'
            }}</q-item-section>
          </q-item>
          <q-item>
            <q-item-section>Váha</q-item-section>
            <q-item-section avatar>
              <span v-if="product.unit_weight"
                >{{ product.unit_weight }}&hairsp;g / {{ product.unit }}</span
              ><span v-else>-</span>
            </q-item-section>
          </q-item>
          <q-separator
            v-if="product.attributes && Object.keys(product.attributes).length > 0"
          ></q-separator>
          <q-item v-for="(value, key) in product.attributes" :key="key">
            <q-item-section>{{ key }}</q-item-section>
            <q-item-section avatar
              ><q-badge color="gray">{{ value }}</q-badge></q-item-section
            >
          </q-item>
        </q-list>

        <div class="mt-auto flex justify-between">
          <ProductAvailability :product-code="product.code" />

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
          no-data-label="Prodejní cena není nastavena!"
        >
          <template #body-cell-price="props">
            <q-td v-if="props.row.price">
              {{ props.row.price }}
              {{ props.row.currency }}
            </q-td>
          </template>
        </q-table>
        <div class="flex flex-row-reverse mt-auto">
          <q-btn outline color="primary" icon="attach_money" label="přidat cenu" disable></q-btn>
        </div>
      </ForegroundPanel>
    </div>
    <div class="flex gap-2 flex-1">
      <WarehouseCard :product-code="product.code" :product-unit="product.unit" />
    </div>
  </div>
  <ForegroundPanel v-else class="grid justify-center w-full content-center text-center">
    <span class="text-5xl text-gray-5">404</span>
    <span class="text-lg text-gray-5"> PRODUKT NENALEZEN </span>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import { warehouseApiRoutesProductGetProduct } from '@/client'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import ProductAvailability from '@/components/product/ProductAvailability.vue'
import ProductTypeIcon from '@/components/product/ProductTypeIcon.vue'
import WarehouseCard from '@/components/product/WarehouseCard.vue'
import { useApi } from '@/composables/use-api'
import type { QTableColumn } from 'quasar'
import { computed, ref } from 'vue'

const { onResponse } = useApi()

const props = defineProps<{
  productCode: string
}>()

const result = await warehouseApiRoutesProductGetProduct({
  path: { product_code: props.productCode },
})
const data = onResponse(result)

const product = ref(data?.data)

// const prices = [
//   {
//     type: 'Prodejní',
//     customer: 'AKROS, s.r.o.',
//     minimum: 0,
//     maximum: 100,
//     currency: 'CZK',
//     unit: '100ks',
//     amount: 1,
//     price: 777.77,
//   },
// ]

const prices = computed(() => {
  if (product.value && product.value.base_price) {
    return [
      {
        type: 'základní',
        customer: undefined,
        minimum: undefined,
        maximum: undefined,
        currency: product.value.currency,
        unit: product.value.unit,
        amount: 1,
        price: product.value.base_price,
      },
    ]
  }
  return []
})

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
    align: 'left',
    classes: 'text-primary font-bold',
  },
]
</script>

<style></style>
