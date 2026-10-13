<template>
  <div class="flex flex-col flex-1 gap-2">
    <div class="flex items-center w-full flex-nowrap">
      <div class="w-12">
        <IndexRectangle :index="item.index + 1" />
      </div>
      <!-- Product -->
      <div class="w-xs">
        <router-link
          :to="{ name: 'productDetail', params: { productCode: item.product.code } }"
          class="link font-medium leading-tight"
          >{{ item.product.name }}</router-link
        >
        <div class="text-xs text-gray-5">{{ item.product.code }}</div>
      </div>

      <div class="grid items-center grid-cols-6 flex-1 text-right">
        <!-- Amount -->
        <div class="flex flex-col">
          <span class="text-lg font-bold tabular-nums">{{ item.amount }}</span>
          <div class="text-xs text-gray-5">
            {{ item.amount }} x <q-badge color="gray">{{ item.product.unit }}</q-badge>
          </div>
        </div>

        <!-- Purchase price -->
        <div class="flex flex-col" data-test="item-purchase-price">
          <span class="tabular-nums">{{ pricing.avgPurchasePrice.toFixed(2) }}</span>
          <span>{{ currency }}</span>
          <span class="text-xs text-muted">za {{ item.product.unit }}</span>
        </div>

        <!-- Unit price (asking price) -->
        <div>
          <div class="flex flex-col" data-test="item-unit-price">
            <div class="flex items-center justify-end">
              <PriceExplanationButton
                :currency="currency"
                :base-price="pricing.basePrice"
                :suggested-price="pricing.suggestedPrice"
                :avg-purchase-price="pricing.avgPurchasePrice"
                :selected-price="Number(item.unit_price)"
                :discount-percent="pricing.discountPercent"
                :reason="pricing.reason"
                :price-source="pricing.source"
              />
              <span class="tabular-nums font-semibold">{{ unitPrice }}</span>
            </div>
            <span>{{ currency }}</span>
          </div>
          <div class="text-xs text-muted">za {{ item.product.unit }}</div>
        </div>

        <!-- Margin -->
        <div data-test="item-margin" class="flex flex-col">
          <div class="text-sm tabular-nums text-nowrap">
            <MarginText :margin="margin" />
          </div>
          <span :class="margin.amount >= 0 ? 'text-green-600' : 'text-red'">{{ currency }}</span>
          <span><MarginPercent :margin="margin" /></span>
        </div>

        <!-- Total price -->
        <div class="flex flex-col">
          <span class="text-lg font-bold tabular-nums">{{ totalPrice }}</span>
          <span>{{ currency }}</span>
        </div>

        <!-- Actions -->
        <div class="flex gap-1 justify-end">
          <EditIconButton @click="editDialog = true" :disable="readonly">
            <q-tooltip>Upravit</q-tooltip>
          </EditIconButton>
          <CloseIconButton @click="removeDialog = true" :disable="readonly">
            <q-tooltip>Odebrat</q-tooltip>
          </CloseIconButton>
        </div>
      </div>
    </div>
    <CommentCard v-if="item.note" :title="item.note" />
  </div>

  <ConfirmDialog v-model:show="removeDialog" title="Odebrat položku" @confirm="$emit('remove')">
    Opravdu odebrat položku <strong>{{ item.product.name }}</strong
    >?
  </ConfirmDialog>

  <OutboundOrderItemEditDialog
    v-model:show="editDialog"
    v-model:item="item"
    :currency="currency"
    :order-code="orderCode"
    :customer-code="customerCode"
  />
</template>

<script setup lang="ts">
import type { OutboundOrderItemSchema } from '@/client'
import { calculateMargin } from '@/utils/margin'
import { computed, defineEmits, defineModel, defineProps, ref } from 'vue'
import CommentCard from '../CommentCard.vue'
import CloseIconButton from '../common/buttons/CloseIconButton.vue'
import EditIconButton from '../common/buttons/EditIconButton.vue'
import ConfirmDialog from '../ConfirmDialog.vue'
import IndexRectangle from '../IndexRectangle.vue'
import MarginPercent from './MarginPercent.vue'
import MarginText from './MarginText.vue'
import OutboundOrderItemEditDialog from './OutboundOrderItemEditDialog.vue'
import PriceExplanationButton from './PriceExplanationButton.vue'

defineProps<{
  currency: string
  readonly?: boolean
  orderCode: string
  customerCode?: string
}>()

defineEmits<{ (e: 'remove'): void }>()

const item = defineModel<OutboundOrderItemSchema>('item', { required: true })

const editDialog = ref(false)
const removeDialog = ref(false)

const unitPrice = computed(() => Number(item.value.unit_price).toFixed(2))
const totalPrice = computed(() => Number(item.value.total_price).toFixed(2))

const pricing = computed(() => {
  const details = item.value.pricing_details
  const unit = Number(item.value.unit_price)
  return {
    basePrice: details?.base_price ?? item.value.product.base_price ?? unit,
    suggestedPrice: details?.suggested_unit_price ?? unit,
    avgPurchasePrice: details?.avg_purchase_price ?? item.value.product.purchase_price ?? 0,
    discountPercent: details?.discount_percent ?? 0,
    reason: details?.reason ?? 'Base selling price',
    source: details?.source ?? 'BASE_PRICE',
  }
})

const margin = computed(() =>
  calculateMargin(
    Number(item.value.total_price),
    item.value.amount * pricing.value.avgPurchasePrice,
  ),
)
</script>
