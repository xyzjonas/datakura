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
      :grid="$q.screen.lt.md"
    >
      <template #item="slotProps">
        <div class="q-pa-xs col-12">
          <ProductPricingGridCard
            :row="slotProps.row"
            :price-type-label="formatPriceType(slotProps.row.price_type)"
            :final-price="getFinalPrice(slotProps.row)"
            :deleting-price-id="deletingPriceId"
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
            <span class="truncate max-w-30 2xl:max-w-xs">
              {{ slotProps.row.customer.name }}
            </span>
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
      :saving="isSaving"
      @submit="onAddDynamicPrice"
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
  type DynamicProductPriceCreateSchema,
  type DynamicProductPriceSchema,
  type ProductSchema,
} from '@/client'
import AddDynamicPriceDialog from '@/components/product/AddDynamicPriceDialog.vue'
import ProductPricingGridCard from '@/components/product/ProductPricingGridCard.vue'
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
const showDeleteDialog = ref(false)
const isSaving = ref(false)
const deletingPriceId = ref<number | null>(null)
const pendingDeletePriceId = ref<number | null>(null)

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

  const target = price.group
    ? `skupina ${price.group}`
    : price.customer
      ? `zákazník ${price.customer.code} - ${price.customer.name}`
      : 'bez cíle'
  const finalPrice = round(
    product.value.base_price! - (price.discount_percent / 100) * product.value.base_price!,
  )
  return `${formatPriceType(price.price_type)}, ${target}, sleva ${price.discount_percent} %, cena ${finalPrice} Kč`
})

const onAddDynamicPrice = async (body: DynamicProductPriceCreateSchema) => {
  isSaving.value = true
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
    isSaving.value = false
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
    price_type: 'BASE_PRICE',
    discount_percent: 0,
  } as DynamicProductPriceSchema,
])

const prices = computed(() => basePrice.value.concat(product.value.dynamic_prices ?? []))

const getFinalPrice = (row: DynamicProductPriceSchema) => {
  return round(product.value.base_price! - (row.discount_percent / 100) * product.value.base_price!)
}

const formatPriceType = (type: string) => {
  switch (type) {
    case 'BASE_PRICE':
      return 'Základní cena'
    case 'GROUP_DISCOUNT':
      return 'Skupinová sleva'
    case 'CUSTOMER_DISCOUNT':
      return 'Sleva pro zákazníka'
    default:
      return type
  }
}

const columns: QTableColumn[] = [
  {
    name: 'type',
    label: 'Typ ceny',
    field: 'price_type',
    align: 'left',
    format: (val) => formatPriceType(val),
  },
  {
    name: 'group',
    label: 'Skupina',
    field: 'group',
    align: 'left',
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
  {
    name: 'actions',
    label: '',
    field: 'price_id',
    align: 'right',
  },
]
</script>

<style lang="scss" scoped></style>
