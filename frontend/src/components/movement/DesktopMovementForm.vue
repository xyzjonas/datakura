<template>
  <q-form @submit.prevent="submit" greedy>
    <!-- Product selection -->
    <div class="text-sm text-muted mb-3">Vyberte produkt a zásoby k přesunutí</div>

    <StockProductSearchSelect
      v-model="selectedProductCode"
      label="Produkt"
      class="mb-3"
      :dense="false"
      @update:model-value="onProductSelected"
    />

    <!-- Item selection (after product selected) -->
    <template v-if="selectedProductCode && stockItems.length">
      <q-select
        v-model="selectedItemId"
        outlined
        emit-value
        map-options
        option-value="id"
        :option-label="itemLabel"
        :options="stockItems"
        label="Zásoby (položka)"
        class="mb-3"
        @update:model-value="onItemSelected"
      />
    </template>

    <template v-if="selectedItem">
      <!-- Unpack option for packages -->
      <template v-if="isPackage">
        <q-toggle v-model="doUnpack" label="Rozbalit (přesunout jen část balení)" class="mb-3" />
        <q-input
          v-if="doUnpack"
          v-model.number="amount"
          outlined
          type="number"
          label="Množství k rozbalení"
          :rules="[amountRule]"
          class="mb-3"
        />
      </template>

      <!-- Quantity for batch / fungible -->
      <template v-else-if="needsAmount">
        <q-input
          v-model.number="amount"
          outlined
          type="number"
          label="Množství k přesunu"
          :rules="[amountRule]"
          class="mb-3"
        />
      </template>

      <!-- Destination location -->
      <WarehouseLocationSearchSelect
        v-model="locationCode"
        label="Cílové místo"
        class="mb-3"
        :dense="false"
      />

      <div class="text-xs text-negative mb-2" v-if="submitError">{{ submitError }}</div>

      <q-btn
        type="submit"
        color="positive"
        class="w-full"
        label="Přesunout"
        :loading="submitLoading"
        :disable="!locationCode"
      />
    </template>

    <div
      v-else-if="selectedProductCode && !stockItems.length && !loadingItems"
      class="text-sm text-muted"
    >
      Pro tento produkt nejsou dostupné žádné zásoby.
    </div>
    <div v-if="loadingItems" class="text-center mt-3">
      <q-spinner color="primary" />
    </div>
  </q-form>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesProductGetProductWarehouseInfo,
  warehouseApiRoutesWarehouseCreateMovement,
  warehouseApiRoutesWarehouseGetWarehouseItem,
  type WarehouseItemSchema,
} from '@/client'
import WarehouseLocationSearchSelect from '@/components/selects/WarehouseLocationSearchSelect.vue'
import StockProductSearchSelect from '@/components/selects/StockProductSearchSelect.vue'
import { computed, onMounted, ref } from 'vue'

const props = defineProps<{ itemId?: number }>()

const emit = defineEmits<{
  (e: 'done'): void
}>()

const selectedProductCode = ref<string | null>(null)
const selectedItemId = ref<number | null>(null)
const stockItems = ref<WarehouseItemSchema[]>([])
const loadingItems = ref(false)
const amount = ref<number | null>(null)
const doUnpack = ref(false)
const locationCode = ref<string | null | undefined>(null)
const submitLoading = ref(false)
const submitError = ref<string | null>(null)

const selectedItem = computed(
  () => stockItems.value.find((i) => i.id === selectedItemId.value) ?? null,
)

const isPackage = computed(() => selectedItem.value?.tracking_level === 'SERIALIZED_PACKAGE')
const needsAmount = computed(
  () =>
    selectedItem.value?.tracking_level === 'BATCH' ||
    selectedItem.value?.tracking_level === 'FUNGIBLE',
)

const itemLabel = (item: WarehouseItemSchema) =>
  `${item.location.code} · ${item.amount} ${item.unit_of_measure}${item.batch ? ` · šarže ${item.batch.primary_barcode?.code ?? item.batch.id}` : ''}`

const amountRule = (val: number | null) => {
  if (val === null || val === undefined) return 'Zadejte množství'
  if (val <= 0) return 'Množství musí být kladné'
  if (selectedItem.value && val > Number(selectedItem.value.amount))
    return `Maximálně ${selectedItem.value.amount}`
  return true
}

const onProductSelected = async (code: string | null | undefined) => {
  selectedItemId.value = null
  stockItems.value = []
  amount.value = null
  doUnpack.value = false
  locationCode.value = null
  if (!code) return

  loadingItems.value = true
  try {
    const result = await warehouseApiRoutesProductGetProductWarehouseInfo({
      path: { product_code: code },
    })
    const warehouses = result.data?.data ?? []
    const items: WarehouseItemSchema[] = []
    for (const wh of warehouses) {
      for (const loc of wh.locations) {
        items.push(...loc.items)
      }
    }
    stockItems.value = items
    if (items.length === 1) {
      selectedItemId.value = items[0].id
      onItemSelected(items[0].id)
    }
  } finally {
    loadingItems.value = false
  }
}

const onItemSelected = (id: number | null) => {
  amount.value = null
  doUnpack.value = false
  locationCode.value = null
  const item = stockItems.value.find((i) => i.id === id)
  if (item?.tracking_level === 'SERIALIZED_PIECE') {
    amount.value = null
  }
}

onMounted(async () => {
  if (!props.itemId) return
  const resp = await warehouseApiRoutesWarehouseGetWarehouseItem({
    path: { item_id: props.itemId },
  })
  const itemData = resp.data?.data
  if (!itemData) return
  selectedProductCode.value = itemData.product.code
  await onProductSelected(itemData.product.code)
  selectedItemId.value = props.itemId
  onItemSelected(props.itemId)
})

const submit = async () => {
  if (!selectedItem.value || !locationCode.value) return
  submitError.value = null
  submitLoading.value = true

  const body: {
    item_id: number
    location_to_code: string
    amount?: number
    unpack?: boolean
  } = {
    item_id: selectedItem.value.id,
    location_to_code: locationCode.value,
  }

  if (doUnpack.value && amount.value !== null) {
    body.amount = amount.value
    body.unpack = true
  } else if (needsAmount.value && amount.value !== null) {
    body.amount = amount.value
  }

  try {
    const result = await warehouseApiRoutesWarehouseCreateMovement({ body })
    if (result.response.ok) {
      emit('done')
    } else {
      const err = result.error as { error?: { exception?: string } } | undefined
      submitError.value = err?.error?.exception ?? result.response.statusText
    }
  } finally {
    submitLoading.value = false
  }
}
</script>
