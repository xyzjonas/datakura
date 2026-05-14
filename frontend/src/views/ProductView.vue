<template>
  <div v-if="product" class="flex flex-col gap-5 flex-1">
    <div class="flex justify-between flex-wrap">
      <q-breadcrumbs class="mb-3">
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
    <div class="flex gap-5 flex-wrap">
      <ForegroundPanel class="flex flex-col min-w-[312px] flex-1">
        <template #header>
          <span class="text-muted">DETAIL PRODUKTU</span>
        </template>
        <span class="text-gray-5 flex items-center gap-1 mb-1">
          <span>
            <ProductTypeIcon :type="product.type" />
            {{ product.type }}
          </span>
        </span>
        <h1 class="h1 mb-1">{{ product.name }}</h1>
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
            <q-item-section>Slevové skupiny</q-item-section>
            <q-item-section avatar>
              <q-badge :color="product.no_discount ? 'negative' : 'positive'">
                {{ product.no_discount ? 'Zakázáno' : 'Povoleno' }}
              </q-badge>
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
        class="min-w-[300px] sm:min-w-xl flex-1 overflow-hidden"
      />
    </div>

    <ForegroundPanel class="flex flex-col">
      <template #header>
        <div class="flex justify-between items-center w-full">
          <span class="text-muted">ČÁROVÉ KÓDY</span>
          <q-btn
            flat
            dense
            round
            icon="add"
            size="sm"
            color="primary"
            @click="openAddBarcodeDialog"
          >
            <q-tooltip>Přidat čárový kód</q-tooltip>
          </q-btn>
        </div>
      </template>
      <q-list
        v-if="product.barcodes && product.barcodes.length > 0"
        bordered
        separator
        class="rounded"
      >
        <q-item v-for="barcode in product.barcodes" :key="barcode.id">
          <q-item-section>
            <div class="flex flex-col md:flex-row gap-2 justify-between">
              <div class="flex gap-1">
                <div class="flex items-center gap-2">
                  <CopyToClipBoardButton :text="barcode.code" class="translate-y-[-6px]" />
                  <BarcodeElement :barcode="barcode.code" :height="30" :width="2" />
                  <div class="flex gap-2 sm:translate-y-[-8px]">
                    <q-badge v-if="barcode.is_primary" color="primary" class="ml-2">
                      <q-icon name="sym_o_star" size="xs" class="mr-1" />
                      Primární
                    </q-badge>
                    <q-badge color="secondary">{{
                      getBarcodeTypeLabel(barcode.barcode_type)
                    }}</q-badge>
                  </div>
                </div>
              </div>
              <div class="flex gap-1 items-center">
                <q-btn
                  v-if="!barcode.is_primary"
                  outline
                  dense
                  class="px-5"
                  icon="sym_o_star"
                  color="accent"
                  label="primární"
                  @click="setPrimaryBarcode(barcode.id)"
                >
                  <q-tooltip>Nastavit jako primární</q-tooltip>
                </q-btn>
                <q-btn
                  outline
                  dense
                  class="px-5"
                  icon="edit"
                  label="upravit"
                  color="primary"
                  @click="openEditBarcodeDialog(barcode)"
                >
                  <q-tooltip>Upravit</q-tooltip>
                </q-btn>
                <q-btn
                  outline
                  dense
                  class="px-5"
                  icon="delete"
                  label="smazat"
                  color="negative"
                  @click="deleteBarcode(barcode.id)"
                >
                  <q-tooltip>Smazat</q-tooltip>
                </q-btn>
              </div>
            </div>
          </q-item-section>
        </q-item>
      </q-list>
      <div v-else class="text-center text-gray-5 py-4">Žádné čárové kódy</div>
      <div class="flex mt-auto w-full pt-3">
        <q-btn
          outline
          color="primary"
          icon="sym_o_barcode"
          label="přidat kód"
          @click="openAddBarcodeDialog"
          class="ml-auto"
        ></q-btn>
      </div>
    </ForegroundPanel>

    <ProductOrdersSection :product-code="product.code" />
    <div class="flex gap-5 flex-1">
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

    <BarcodeUpsertDialog
      v-model:show="showAddBarcodeDialog"
      v-model="addBarcodeForm"
      title="Přidat čárový kód"
      submit-label="přidat"
      :loading="savingBarcode"
      @submit="addBarcode"
    />

    <BarcodeUpsertDialog
      v-model:show="showEditBarcodeDialog"
      v-model="editBarcodeForm"
      title="Upravit čárový kód"
      submit-label="uložit"
      :loading="savingBarcode"
      @submit="updateBarcode"
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
  warehouseApiRoutesProductAddProductBarcode,
  warehouseApiRoutesProductUpdateProductBarcode,
  warehouseApiRoutesProductDeleteProductBarcode,
  warehouseApiRoutesProductSetPrimaryBarcode,
  type ProductCreateOrUpdateSchema,
  type ProductDuplicateSchema,
  type ProductSchema,
  type ProductBarcodeCreateSchema,
  type ProductBarcodeUpdateSchema,
  type BarcodeSchema,
} from '@/client'
import BarcodeElement from '@/components/BarcodeElement.vue'
import CopyToClipBoardButton from '@/components/CopyToClipBoardButton.vue'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import ProductAvailability from '@/components/product/ProductAvailability.vue'
import ProductOrdersSection from '@/components/product/ProductOrdersSection.vue'
import ProductPricingCard from '@/components/product/ProductPricingCard.vue'
import ProductTypeIcon from '@/components/product/ProductTypeIcon.vue'
import ProductUpsertDialog from '@/components/product/ProductUpsertDialog.vue'
import BarcodeUpsertDialog from '@/components/product/BarcodeUpsertDialog.vue'
import WarehouseCard from '@/components/product/WarehouseCard.vue'
import AuditLogDialog from '@/components/warehouse/AuditLogDialog.vue'
import { useApi } from '@/composables/use-api'
import { useQuasar } from 'quasar'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const { onResponse } = useApi()
const $q = useQuasar()

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

const showAddBarcodeDialog = ref(false)
const showEditBarcodeDialog = ref(false)
const savingBarcode = ref(false)
const editingBarcodeId = ref<number | null>(null)

const toFormSchema = (item: ProductSchema): ProductCreateOrUpdateSchema => ({
  name: item.name,
  code: item.code,
  type: item.type,
  unit: item.unit,
  group: item.group ?? '',
  unit_weight: item.unit_weight,
  base_price: item.base_price,
  purchase_price: item.purchase_price,
  no_discount: item.no_discount,
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
  no_discount: false,
  currency: 'CZK',
  customs_declaration_group: '',
  attributes: {},
})

const duplicateForm = ref<ProductCreateOrUpdateSchema>({ ...editForm.value })

interface BarcodeFormData {
  code: string
  barcode_type: string
  is_primary: boolean
}

const addBarcodeForm = ref<BarcodeFormData>({
  code: '',
  barcode_type: 'EAN13',
  is_primary: false,
})

const editBarcodeForm = ref<BarcodeFormData>({
  code: '',
  barcode_type: 'EAN13',
  is_primary: false,
})

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

const getBarcodeTypeLabel = (type: string): string => {
  const typeMap: Record<string, string> = {
    EAN13: 'EAN-13',
    EAN8: 'EAN-8',
    UPC: 'UPC',
    GS1_128: 'GS1-128',
    QR: 'QR Code',
    SERIAL: 'Serial Number',
    SSCC: 'SSCC',
    CUSTOM: 'Custom',
  }
  return typeMap[type] || type
}

const openAddBarcodeDialog = () => {
  addBarcodeForm.value = {
    code: '',
    barcode_type: 'EAN13',
    is_primary: false,
  }
  showAddBarcodeDialog.value = true
}

const openEditBarcodeDialog = (barcode: BarcodeSchema) => {
  editingBarcodeId.value = barcode.id
  editBarcodeForm.value = {
    code: barcode.code,
    barcode_type: barcode.barcode_type,
    is_primary: barcode.is_primary,
  }
  showEditBarcodeDialog.value = true
}

const addBarcode = async (body: BarcodeFormData) => {
  if (!product.value) {
    return
  }

  savingBarcode.value = true
  try {
    const payload: ProductBarcodeCreateSchema = {
      code: body.code,
      barcode_type: body.barcode_type,
      is_primary: body.is_primary,
    }
    const result = await warehouseApiRoutesProductAddProductBarcode({
      path: { product_code: product.value.code },
      body: payload,
    })
    const response = onResponse(result)
    if (response?.data) {
      product.value = response.data
      showAddBarcodeDialog.value = false
      $q.notify({
        type: 'positive',
        message: 'Čárový kód byl přidán',
      })
    }
  } finally {
    savingBarcode.value = false
  }
}

const updateBarcode = async (body: BarcodeFormData) => {
  if (!product.value || editingBarcodeId.value === null) {
    return
  }

  savingBarcode.value = true
  try {
    const payload: ProductBarcodeUpdateSchema = {
      code: body.code,
      barcode_type: body.barcode_type,
      is_primary: body.is_primary,
    }
    const result = await warehouseApiRoutesProductUpdateProductBarcode({
      path: {
        product_code: product.value.code,
        barcode_id: editingBarcodeId.value,
      },
      body: payload,
    })
    const response = onResponse(result)
    if (response?.data) {
      product.value = response.data
      showEditBarcodeDialog.value = false
      editingBarcodeId.value = null
      $q.notify({
        type: 'positive',
        message: 'Čárový kód byl aktualizován',
      })
    }
  } finally {
    savingBarcode.value = false
  }
}

const deleteBarcode = async (barcodeId: number) => {
  if (!product.value) {
    return
  }

  $q.dialog({
    title: 'Smazat čárový kód',
    message: 'Opravdu chcete smazat tento čárový kód?',
    cancel: true,
    persistent: true,
  }).onOk(async () => {
    const result = await warehouseApiRoutesProductDeleteProductBarcode({
      path: {
        product_code: product.value!.code,
        barcode_id: barcodeId,
      },
    })
    const response = onResponse(result)
    if (response?.data) {
      product.value = response.data
      $q.notify({
        type: 'positive',
        message: 'Čárový kód byl smazán',
      })
    }
  })
}

const setPrimaryBarcode = async (barcodeId: number) => {
  if (!product.value) {
    return
  }

  const result = await warehouseApiRoutesProductSetPrimaryBarcode({
    path: {
      product_code: product.value.code,
      barcode_id: barcodeId,
    },
  })
  const response = onResponse(result)
  if (response?.data) {
    product.value = response.data
    $q.notify({
      type: 'positive',
      message: 'Primární čárový kód byl nastaven',
    })
  }
}
</script>

<style></style>
