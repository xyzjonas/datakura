<template>
  <div v-if="product" class="flex flex-col gap-2 flex-1">
    <div class="flex justify-between flex-wrap">
      <q-breadcrumbs class="mb-5 flex-[3]">
        <q-breadcrumbs-el label="Domů" :to="{ name: 'home' }" />
        <q-breadcrumbs-el label="Produkty" :to="{ name: 'products' }" />
        <q-breadcrumbs-el :label="product.name" />
      </q-breadcrumbs>
      <div class="flex flex-col items-end gap-3 flex-1">
        <q-btn flat color="primary" icon-right="sym_o_query_stats" @click="auditDialog = true">
          <q-tooltip :offset="[0, 10]">Zobrazit historii</q-tooltip>
        </q-btn>
      </div>
    </div>

    <div class="flex justify-between gap-2">
      <div class="flex items-center gap-2">
        <ProductAvailability :product-code="product.code" />
      </div>
      <div class="flex items-center gap-2">
        <q-btn color="primary" icon="edit" label="upravit" @click="openEditDialog" />
        <q-btn
          color="primary"
          icon="content_copy"
          label="duplikovat"
          @click="openDuplicateDialog"
        />
      </div>
    </div>
    <div class="flex gap-2 flex-wrap">
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
          <CopyToClipBoardButton :text="product.code" />
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
            <q-item-section avatar>
              <span
                class="flex border px-2 rounded-xl py-1 shadow-sm text-primary translate-x-3 cursor-help"
              >
                <q-icon name="sym_o_autorenew" size="xs" class="mr-1" />
                <span class="font-bold">
                  {{ product.purchase_price }}&hairsp;{{ product.currency }}
                </span>
                <q-tooltip class="max-w-xs"
                  >Průměrná nákupní cena je průběžně automaticky přepočítávána kdykoliv dojde ke
                  změně skladových zásob.</q-tooltip
                >
              </span>
            </q-item-section>
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
      </ForegroundPanel>
      <ProductPricingCard
        v-model="product"
        class="min-w-[370px] sm:min-w-xl flex-1 overflow-hidden"
      />
    </div>

    <ProductOrdersSection :product-code="product.code" />
    <div class="flex gap-2 flex-1">
      <WarehouseCard :product-code="product.code" :product-unit="product.unit" />
    </div>

    <AuditLogDialog
      v-model:show="auditDialog"
      source="product"
      :code="product.code"
      title="Historie změn produktu"
    />

    <ProductUpsertDialog
      v-model:show="showEditDialog"
      v-model="editForm"
      title="Upravit produkt"
      submit-label="uložit"
      :loading="savingEdit"
      @submit="updateProduct"
    />

    <ProductUpsertDialog
      v-model:show="showDuplicateDialog"
      v-model="duplicateForm"
      title="Duplikovat produkt"
      submit-label="duplikovat"
      :loading="savingDuplicate"
      @submit="duplicateProduct"
    />
  </div>
  <ForegroundPanel v-else class="grid justify-center w-full content-center text-center">
    <span class="text-5xl text-gray-5">404</span>
    <span class="text-lg text-gray-5"> PRODUKT NENALEZEN </span>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesProductDuplicateProduct,
  warehouseApiRoutesProductGetProduct,
  warehouseApiRoutesProductUpdateProduct,
  type ProductCreateOrUpdateSchema,
  type ProductDuplicateSchema,
  type ProductSchema,
} from '@/client'
import CopyToClipBoardButton from '@/components/CopyToClipBoardButton.vue'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import ProductAvailability from '@/components/product/ProductAvailability.vue'
import ProductOrdersSection from '@/components/product/ProductOrdersSection.vue'
import ProductPricingCard from '@/components/product/ProductPricingCard.vue'
import ProductTypeIcon from '@/components/product/ProductTypeIcon.vue'
import ProductUpsertDialog from '@/components/product/ProductUpsertDialog.vue'
import WarehouseCard from '@/components/product/WarehouseCard.vue'
import AuditLogDialog from '@/components/warehouse/AuditLogDialog.vue'
import { useApi } from '@/composables/use-api'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const { onResponse } = useApi()

const props = defineProps<{
  productCode: string
}>()

const router = useRouter()

const result = await warehouseApiRoutesProductGetProduct({
  path: { product_code: props.productCode },
})
const data = onResponse(result)

const product = ref<ProductSchema | undefined>(data?.data)
const auditDialog = ref(false)

const showEditDialog = ref(false)
const showDuplicateDialog = ref(false)
const savingEdit = ref(false)
const savingDuplicate = ref(false)

const toFormSchema = (item: ProductSchema): ProductCreateOrUpdateSchema => ({
  name: item.name,
  code: item.code,
  type: item.type,
  unit: item.unit,
  group: item.group ?? '',
  unit_weight: item.unit_weight,
  base_price: item.base_price,
  purchase_price: item.purchase_price,
  currency: item.currency,
  customs_declaration_group: item.customs_declaration_group ?? '',
  attributes: item.attributes ?? {},
})

const editForm = ref<ProductCreateOrUpdateSchema>({
  name: '',
  code: '',
  type: '',
  unit: 'KS',
  group: '',
  unit_weight: 0,
  base_price: 0,
  purchase_price: 0,
  currency: 'CZK',
  customs_declaration_group: '',
  attributes: {},
})

const duplicateForm = ref<ProductCreateOrUpdateSchema>({ ...editForm.value })

const openEditDialog = () => {
  if (!product.value) {
    return
  }
  editForm.value = toFormSchema(product.value)
  showEditDialog.value = true
}

const openDuplicateDialog = () => {
  if (!product.value) {
    return
  }
  duplicateForm.value = {
    ...toFormSchema(product.value),
    code: `${product.value.code}-COPY`,
    name: `${product.value.name} (kopie)`,
  }
  showDuplicateDialog.value = true
}

const updateProduct = async (body: ProductCreateOrUpdateSchema) => {
  if (!product.value) {
    return
  }

  savingEdit.value = true
  try {
    const oldCode = product.value.code
    const result = await warehouseApiRoutesProductUpdateProduct({
      path: { product_code: oldCode },
      body,
    })
    const response = onResponse(result)
    if (response?.data) {
      product.value = response.data
      showEditDialog.value = false
      if (response.data.code !== oldCode) {
        await router.replace({ name: 'productDetail', params: { productCode: response.data.code } })
      }
    }
  } finally {
    savingEdit.value = false
  }
}

const duplicateProduct = async (body: ProductCreateOrUpdateSchema) => {
  if (!product.value) {
    return
  }

  savingDuplicate.value = true
  try {
    const payload: ProductDuplicateSchema = { ...body }
    const result = await warehouseApiRoutesProductDuplicateProduct({
      path: { product_code: product.value.code },
      body: payload,
    })
    const response = onResponse(result)
    if (response?.data) {
      showDuplicateDialog.value = false
      await router.push({ name: 'productDetail', params: { productCode: response.data.code } })
    }
  } finally {
    savingDuplicate.value = false
  }
}
</script>

<style></style>
