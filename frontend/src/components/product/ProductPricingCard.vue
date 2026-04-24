<template>
  <ForegroundPanel no-padding class="flex flex-col p-2">
    <!-- <h2 class="mb-4">Ceník</h2> -->
    <q-table
      :rows="prices"
      :columns="columns"
      flat
      title="Ceník"
      :pagination="{ rowsPerPage: 5 }"
      class="bg-transparent"
      no-data-label="Prodejní cena není nastavena!"
      :grid="$q.screen.lg"
    >
      <template #item="slotProps">
        <div class="q-pa-xs col-12">
          <ProductPricingGridCard
            :row="slotProps.row"
            :price-type-label="formatPriceType(slotProps.row)"
            :final-price="getFinalPrice(slotProps.row)"
            :deleting-price-id="deletingPriceId"
            @edit="onEditDynamicPrice"
            @delete="onDeleteDynamicPrice"
          />
        </div>
      </template>

      <template #top-right>
        <q-btn
          outline
          color="primary"
          icon="attach_money"
          label="přidat cenu"
          @click="showAddDialog = true"
        ></q-btn>
      </template>

      <template #body-cell-customer="slotProps">
        <q-td :props="slotProps" auto-width>
          <router-link
            v-if="slotProps.row.customer?.code"
            :to="{ name: 'customerDetail', params: { customerCode: slotProps.row.customer.code } }"
            class="link flex"
          >
            <span class="truncate max-w-30">
              {{ slotProps.row.customer.name }}
            </span>
            <small class="text-gray-5">{{ slotProps.row.customer.code }}</small>
          </router-link>
          <span v-else>—</span>
        </q-td>
      </template>

      <template #body-cell-actions="slotProps">
        <q-td :props="slotProps" class="text-right">
          <q-btn
            v-if="slotProps.row.price_id >= 0"
            flat
            round
            dense
            icon="sym_o_edit"
            color="primary"
            @click="onEditDynamicPrice(slotProps.row.price_id)"
          >
            <q-tooltip>Upravit cenu</q-tooltip>
          </q-btn>
          <q-btn
            v-if="slotProps.row.price_id >= 0"
            flat
            round
            dense
            icon="sym_o_close_small"
            color="negative"
            :loading="deletingPriceId === slotProps.row.price_id"
            @click="onDeleteDynamicPrice(slotProps.row.price_id)"
          >
            <q-tooltip>Odstranit cenu</q-tooltip>
          </q-btn>
        </q-td>
      </template>
    </q-table>

    <AddDynamicPriceDialog
      v-model:show="showAddDialog"
      :saving="isAdding"
      @submit="onAddDynamicPrice"
    />

    <UpdateDynamicPriceDialog
      v-model:show="showEditDialog"
      :price="selectedEditPrice ?? undefined"
      :saving="isUpdating"
      @update:show="onEditDialogVisibilityChange"
      @submit="onUpdateDynamicPrice"
    />

    <ConfirmDialog
      v-model:show="showDeleteDialog"
      title="Opravdu odstranit tuto cenu?"
      @update:show="onDeleteDialogVisibilityChange"
      @confirm="onConfirmDeleteDynamicPrice"
    >
      <span>
        Tato akce smaže vybranou cenu:
        <strong>{{ pendingDeletePriceDescription }}</strong>
      </span>
    </ConfirmDialog>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesProductAddProductDynamicPrice,
  warehouseApiRoutesProductDeleteProductDynamicPrice,
  warehouseApiRoutesProductUpdateProductDynamicPrice,
  type DynamicProductPriceCreateSchema,
  type DynamicProductPriceSchema,
  type DynamicProductPriceUpdateSchema,
  type ProductSchema,
} from '@/client'
import AddDynamicPriceDialog from '@/components/product/AddDynamicPriceDialog.vue'
import ProductPricingGridCard from '@/components/product/ProductPricingGridCard.vue'
import UpdateDynamicPriceDialog from '@/components/product/UpdateDynamicPriceDialog.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { useApi } from '@/composables/use-api'
import ForegroundPanel from '../ForegroundPanel.vue'
import { useQuasar, type QTableColumn } from 'quasar'
import { computed, ref } from 'vue'
import { round } from '@/utils/round'

const product = defineModel<ProductSchema>({ required: true })

type DynamicPriceRow = DynamicProductPriceSchema & {
  customer?: { code: string; name: string } | null
}

const { onResponse } = useApi()
const $q = useQuasar()

const showAddDialog = ref(false)
const showEditDialog = ref(false)
const showDeleteDialog = ref(false)
const isAdding = ref(false)
const isUpdating = ref(false)
const deletingPriceId = ref<number | null>(null)
const pendingDeletePriceId = ref<number | null>(null)
const pendingEditPriceId = ref<number | null>(null)

const selectedEditPrice = computed<DynamicPriceRow | null>(() => {
  if (pendingEditPriceId.value === null) {
    return null
  }

  const found =
    product.value.dynamic_prices?.find((price) => price.price_id === pendingEditPriceId.value) ??
    null
  return found as DynamicPriceRow | null
})

const pendingDeletePrice = computed<DynamicPriceRow | null>(() => {
  if (pendingDeletePriceId.value === null) {
    return null
  }

  const found =
    product.value.dynamic_prices?.find((price) => price.price_id === pendingDeletePriceId.value) ??
    null
  return found as DynamicPriceRow | null
})

const pendingDeletePriceDescription = computed(() => {
  const price = pendingDeletePrice.value
  if (!price) {
    return 'neznámá cena'
  }

  const target = price.customer
    ? `zákazník ${price.customer.code} - ${price.customer.name}`
    : 'bez cíle'
  return `${formatPriceType(price)}, ${target}, sleva ${price.discount_percent} %, cena ${round(price.fixed_price)} Kč`
})

const onAddDynamicPrice = async (body: DynamicProductPriceCreateSchema) => {
  isAdding.value = true
  try {
    const result = await warehouseApiRoutesProductAddProductDynamicPrice({
      path: { product_code: product.value.code },
      body,
    })
    const data = onResponse(result)
    if (!data?.data) {
      return
    }

    product.value = data.data
    showAddDialog.value = false
    $q.notify({ type: 'positive', message: 'Dynamická cena byla přidána.' })
  } finally {
    isAdding.value = false
  }
}

const onEditDynamicPrice = (priceId: number) => {
  if (priceId < 0) {
    return
  }

  pendingEditPriceId.value = priceId
  showEditDialog.value = true
}

const onUpdateDynamicPrice = async (body: DynamicProductPriceUpdateSchema) => {
  const priceId = pendingEditPriceId.value
  if (priceId === null) {
    return
  }

  isUpdating.value = true
  try {
    const result = await warehouseApiRoutesProductUpdateProductDynamicPrice({
      path: { product_code: product.value.code, price_id: priceId },
      body,
    })
    const data = onResponse(result)
    if (!data?.data) {
      return
    }

    product.value = data.data
    showEditDialog.value = false
    pendingEditPriceId.value = null
    $q.notify({ type: 'positive', message: 'Dynamicka cena byla upravena.' })
  } finally {
    isUpdating.value = false
  }
}

const onEditDialogVisibilityChange = (visible: boolean) => {
  showEditDialog.value = visible
  if (!visible) {
    pendingEditPriceId.value = null
  }
}

const onDeleteDynamicPrice = async (priceId: number) => {
  if (priceId < 0) {
    return
  }

  pendingDeletePriceId.value = priceId
  showDeleteDialog.value = true
}

const onDeleteDialogVisibilityChange = (visible: boolean) => {
  showDeleteDialog.value = visible
  if (!visible) {
    pendingDeletePriceId.value = null
  }
}

const onConfirmDeleteDynamicPrice = async () => {
  const priceId = pendingDeletePriceId.value
  if (priceId === null) {
    return
  }

  deletingPriceId.value = priceId
  try {
    const result = await warehouseApiRoutesProductDeleteProductDynamicPrice({
      path: { product_code: product.value.code, price_id: priceId },
    })
    const data = onResponse(result)
    if (!data?.data) {
      return
    }

    product.value = data.data
    $q.notify({ type: 'positive', message: 'Cena byla odstraněna z ceníku.' })
  } finally {
    deletingPriceId.value = null
    pendingDeletePriceId.value = null
  }
}

const basePrice = computed<DynamicProductPriceSchema[]>(() => [
  {
    price_id: -1,
    fixed_price: product.value.base_price ?? 0,
    discount_percent: 0,
    customer: {
      code: '',
      name: '',
    },
  } as DynamicProductPriceSchema,
])

const prices = computed(() => basePrice.value.concat(product.value.dynamic_prices ?? []))

const getFinalPrice = (row: DynamicProductPriceSchema) => {
  return round(row.fixed_price)
}

const formatPriceType = (row: DynamicProductPriceSchema) => {
  return row.price_id < 0 ? 'Základní cena' : 'Sleva pro zákazníka'
}

const columns: QTableColumn[] = [
  {
    name: 'actions',
    label: '',
    field: 'price_id',
    align: 'right',
  },
  {
    name: 'type',
    label: 'Typ ceny',
    field: 'price_id',
    align: 'left',
    format: (_, row: DynamicProductPriceSchema) => formatPriceType(row),
  },
  {
    name: 'customer',
    label: 'Zákazník',
    field: 'customer',
    align: 'left',
  },
  // {
  //   name: 'minimum',
  //   label: 'Minimální počet',
  //   field: 'minimum',
  //   align: 'left',
  // },
  // {
  //   name: 'maximum',
  //   label: 'Maximální počet',
  //   field: 'maximum',
  //   align: 'left',
  // },
  // {
  //   name: 'unit',
  //   label: 'Jednotka',
  //   field: 'unit',
  //   align: 'left',
  // },
  // {
  //   name: 'amount',
  //   label: 'Počet jednotek',
  //   field: 'amount',
  //   align: 'left',
  // },
  {
    name: 'discount',
    label: 'Sleva',
    field: 'discount_percent',
    align: 'left',
    format: (val) => `${val} %`,
    classes: 'font-bold',
  },
  {
    name: 'price',
    label: 'Cena / MJ',
    field: (row: DynamicProductPriceSchema) => getFinalPrice(row),
    align: 'left',
    format: (val) => `${val} Kč`,
    classes: 'text-primary font-bold',
  },
]
</script>

<style lang="scss" scoped></style>
