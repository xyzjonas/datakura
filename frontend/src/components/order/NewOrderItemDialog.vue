<template>
  <q-dialog v-model="showDialog" position="bottom">
    <q-card class="w-full">
      <div class="p-4 flex flex-col">
        <div class="w-full flex justify-between items-center mb-3">
          <span class="text-2xl uppercase">Přidat položku</span>
          <q-btn flat round icon="close" v-close-popup />
        </div>
        <ProductAvailability v-if="product" :product-code="product.code" class="w-fit mb-3" />
        <q-form ref="form" class="flex flex-col gap-2" @submit="addItem">
          <!-- <ItemSelectByName v-model="newItem" :rules="[rules.notEmpty]" class="flex-1" />
          <PlaceSelect v-show="manualSearchItem" v-model="newPlace" :rules="[rules.notEmpty]" /> -->
          <ProductSearchSelect ref="productSelect" v-model="product" />
          <q-input
            v-model.number="item.amount"
            outlined
            label="Počet"
            hint="Počet Kusů dle MJ"
            inputmode="numeric"
            :debounce="300"
            :rules="[rules.atLeastOne, rules.max9999]"
          >
            <template #append>
              <span class="text-sm">{{ productUom }}</span>
            </template>
          </q-input>
          <q-input
            :model-value="derivedUnitPrice"
            readonly
            outlined
            label="Nákupní cena"
            hint="Nákupní cena za MJ"
            inputmode="numeric"
            :error="priceSanityCheck"
            :error-message="`Nákupní cena se příliš liší od aktuální ceny produktu (${serverPurchasePrice} ${product?.currency}) o ${percentDifference}%!`"
          >
            <template #append>
              <span class="text-sm">{{ currency }} / {{ productUom }}</span>
            </template>
          </q-input>
          <q-input
            v-model.number="item.total_price"
            outlined
            label="Celková cena"
            hint="Celková cena položky"
            inputmode="numeric"
            :rules="[rules.atLeastZero, rules.max99999]"
          >
            <template #append>
              <span class="text-sm">{{ currency }}</span>
            </template>
          </q-input>
          <InboundItemPricingPanel
            v-model:product="product"
            :currency="currency"
            :new-purchase-price="Number(derivedUnitPrice) || 0"
            data-test="new-item-pricing"
          />
          <CountrySelect
            v-model="item.origin_country"
            label="Země původu"
            hint="Výchozí je země dodavatele"
          />
          <q-toggle
            v-model="item.requires_certification"
            label="Certifikované zboží"
            data-test="requires-certification"
          />
          <CertificationFields
            v-if="item.requires_certification"
            v-model:draft="certificationDraft"
            optional
          />
          <div class="flex gap-2 mt-3">
            <q-btn
              type="submit"
              unelevated
              color="primary"
              label="přidat"
              class="h-[3rem] flex-1"
              @click="keepOpen = false"
            />
            <q-btn
              type="submit"
              outline
              color="primary"
              label="přidat a nový"
              class="h-[3rem] flex-1"
              @click="keepOpen = true"
            />
          </div>
        </q-form>
      </div>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import type { InboundOrderItemCreateSchema, ProductSchema } from '@/client'
import { rules } from '@/utils/rules'
import { computed, nextTick, ref, watch } from 'vue'
import type { QForm } from 'quasar'
import CertificationFields from '../certification/CertificationFields.vue'
import {
  emptyCertificationDraft,
  type CertificationDraft,
} from '../certification/certification-upload'
import CountrySelect from '../selects/CountrySelect.vue'
import ProductSearchSelect from '../selects/ProductSearchSelect.vue'
import InboundItemPricingPanel from './InboundItemPricingPanel.vue'
import ProductAvailability from '../product/ProductAvailability.vue'
import { round } from '@/utils/round'

const showDialog = defineModel('show', { default: false })

export interface NewOrderItemDialogExpose {
  reset: (close?: boolean) => void
}

const props = defineProps<{
  currency: string
  /** country of the supplier - the default origin country of new items */
  supplierCountry?: string | null
}>()

// just for display purposes
const productUom = ref('')

const emptyItem = (): InboundOrderItemCreateSchema => ({
  product_code: '',
  product_name: '',
  amount: 0,
  total_price: 0,
  unit_price: 0,
  origin_country: props.supplierCountry ?? null,
  requires_certification: false,
})

const item = ref<InboundOrderItemCreateSchema>(emptyItem())
/** Certificate supplied along with a certified row (attached once the row exists). */
const certificationDraft = ref<CertificationDraft>(emptyCertificationDraft())

watch(
  () => props.supplierCountry,
  (country) => {
    item.value.origin_country = country ?? null
  },
)

const allowedPercent = 20
const serverPurchasePrice = ref(0)
const derivedUnitPrice = computed(() => {
  if (!item.value.amount) {
    return serverPurchasePrice.value
  }
  if (!item.value.total_price) {
    return serverPurchasePrice.value
  }
  return round(item.value.total_price / item.value.amount)
})

const percentDifference = computed(() => {
  if (!serverPurchasePrice.value) {
    return 0
  }
  return round((1 - derivedUnitPrice.value / serverPurchasePrice.value) * 100)
})
const priceSanityCheck = computed(() => {
  if (!product.value) {
    return false
  }
  return percentDifference.value > allowedPercent || percentDifference.value < -allowedPercent
})
const product = ref<ProductSchema>()

// keyed on the code: saving a new base price swaps the product object but must not reset the prices
watch(
  () => product.value?.code,
  () => {
    const newValue = product.value
    if (newValue) {
      item.value.product_code = newValue.code
      item.value.product_name = newValue.name
      item.value.unit_price = newValue.purchase_price ?? 0
      item.value.total_price = (newValue.purchase_price ?? 0) * item.value.amount
      serverPurchasePrice.value = newValue.purchase_price ?? 0
      productUom.value = newValue.unit
    } else {
      item.value.product_code = ''
      item.value.product_name = ''
    }
  },
)

watch(
  () => item.value.amount,
  (newAmount) => {
    if (item.value.total_price <= 0) {
      item.value.total_price = round((item.value.unit_price ?? 0) * newAmount)
    }
  },
)

const emit = defineEmits<{
  (
    e: 'addItem',
    item: InboundOrderItemCreateSchema,
    keepOpen: boolean,
    certification: CertificationDraft | null,
  ): void
}>()

const form = ref<QForm>()
const productSelect = ref<InstanceType<typeof ProductSearchSelect>>()
const keepOpen = ref(false)

const addItem = () => {
  emit(
    'addItem',
    item.value,
    keepOpen.value,
    item.value.requires_certification ? certificationDraft.value : null,
  )
  keepOpen.value = false
}

const reset = (close = true) => {
  item.value = emptyItem()
  certificationDraft.value = emptyCertificationDraft()
  product.value = undefined
  if (close) {
    showDialog.value = false
    return
  }
  nextTick(() => {
    form.value?.resetValidation()
    productSelect.value?.focus()
  })
}

defineExpose<NewOrderItemDialogExpose>({
  reset,
})
</script>
<style lang="css" scoped></style>
