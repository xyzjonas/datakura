<template>
  <OrderItemCard
    v-if="cardLayout"
    :item="item"
    :currency="currency"
    :base-currency="baseCurrency"
    :readonly="readonly"
    :purchase-price="Number(pricing.avgPurchasePrice)"
    :selling-price="Number(item.document_unit_price)"
    :margin="item.is_returned ? undefined : margin"
    :own-code="item.customer_product_code"
    :own-code-missing="ownCodeMissing"
    :below-minimum-profit="belowMinimumProfit"
    :returned="item.is_returned"
    @edit="editDialog = true"
    @remove="removeDialog = true"
  >
    <template v-if="returnSelection?.active.value" #actions>
      <OutboundItemReturnControl :item="item" />
    </template>

    <template #requirements>
      <OutboundItemRequirementBadges
        class="mt-1"
        :package-type="item.desired_package_type_name"
        :batch-code="item.desired_batch_code"
        :batch-certification="item.desired_batch_certification"
        :origin-country="item.required_origin_country"
      />
    </template>
  </OrderItemCard>
  <div
    v-else
    :class="[
      'flex flex-col flex-1 gap-2',
      item.is_returned
        ? 'border-l-4 border-solid border-0 border-red pl-2 light:bg-red-50 dark:bg-red-9/20'
        : ownCodeMissing || belowMinimumProfit
          ? 'border-l-4 border-solid border-0 border-red pl-2'
          : '',
    ]"
  >
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
        <div
          v-if="item.customer_product_code"
          class="text-xs font-mono font-semibold"
          data-test="item-own-code"
        >
          {{ item.customer_product_code }}
        </div>
        <div v-else class="text-xs text-gray-5">{{ item.product.code }}</div>
        <ReturnedBadge v-if="item.is_returned" class="mt-1" />
        <MissingOwnCodeBadge v-if="ownCodeMissing" class="mt-1" />
        <NonPhysicalBadge v-if="item.product.non_physical" class="mt-1" />
        <BelowMinimumProfitBadge v-if="belowMinimumProfit" class="mt-1" />
        <OutboundItemRequirementBadges
          class="mt-1"
          :package-type="item.desired_package_type_name"
          :batch-code="item.desired_batch_code"
          :batch-certification="item.desired_batch_certification"
          :origin-country="item.required_origin_country"
        />
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
          <span>{{ baseCurrency }}</span>
          <span class="text-xs text-muted">za {{ item.product.unit }}</span>
        </div>

        <!-- Unit price (asking price) -->
        <div>
          <div class="flex flex-col" data-test="item-unit-price">
            <div class="flex items-center justify-end">
              <PriceExplanationButton
                :currency="baseCurrency"
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
          <div v-if="foreign" class="text-xs text-muted" data-test="item-unit-price-base">
            ≈ {{ Number(item.unit_price).toFixed(2) }} {{ baseCurrency }}
          </div>
        </div>

        <!-- Margin -->
        <div data-test="item-margin" class="flex flex-col">
          <template v-if="!item.is_returned">
            <span class="text-lg tabular-nums text-nowrap"
              ><MarginPercent :margin="margin" :danger="belowMinimumProfit" />
            </span>
            <span class="text-sm tabular-nums text-nowrap">
              <MarginText :margin="margin" :currency="baseCurrency" :danger="belowMinimumProfit" />
            </span>
          </template>
        </div>

        <!-- Total price -->
        <div class="flex flex-col">
          <span :class="['text-lg font-bold tabular-nums', item.is_returned ? 'text-red' : '']"
            >{{ item.is_returned ? '-' : '' }}{{ totalPrice }}</span
          >
          <span>{{ currency }}</span>
          <span v-if="foreign" class="text-xs text-muted" data-test="item-total-price-base">
            ≈ {{ Number(item.total_price).toFixed(2) }} {{ baseCurrency }}
          </span>
        </div>

        <!-- Actions -->
        <div class="flex gap-1 justify-end">
          <OutboundItemReturnControl v-if="returnSelection?.active.value" :item="item" />
          <template v-else-if="!item.is_returned">
            <EditIconButton @click="editDialog = true" :disable="readonly">
              <q-tooltip>Upravit</q-tooltip>
            </EditIconButton>
            <CloseIconButton @click="removeDialog = true" :disable="readonly">
              <q-tooltip>Odebrat</q-tooltip>
            </CloseIconButton>
          </template>
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
    :base-currency="baseCurrency"
    :exchange-rate="exchangeRate"
    :order-code="orderCode"
    :customer-code="customerCode"
    :requires-own-codes="requiresOwnCodes"
  />
</template>

<script setup lang="ts">
import type { OutboundOrderItemSchema } from '@/client'
import { useOrderItemCardLayout } from '@/composables/use-order-item-card-layout'
import { useMinimumProfit } from '@/composables/use-minimum-profit'
import { useReturnSelection } from '@/composables/use-return-selection'
import { calculateMargin } from '@/utils/margin'
import { itemIsBelowMinimumProfit } from '@/utils/minimum-profit'
import { computed, defineEmits, defineModel, defineProps, ref } from 'vue'
import CommentCard from '../CommentCard.vue'
import OrderItemCard from './OrderItemCard.vue'
import CloseIconButton from '../common/buttons/CloseIconButton.vue'
import EditIconButton from '../common/buttons/EditIconButton.vue'
import ConfirmDialog from '../ConfirmDialog.vue'
import IndexRectangle from '../IndexRectangle.vue'
import OutboundItemRequirementBadges from './OutboundItemRequirementBadges.vue'
import BelowMinimumProfitBadge from './BelowMinimumProfitBadge.vue'
import MissingOwnCodeBadge from './MissingOwnCodeBadge.vue'
import NonPhysicalBadge from './NonPhysicalBadge.vue'
import OutboundItemReturnControl from './OutboundItemReturnControl.vue'
import ReturnedBadge from './ReturnedBadge.vue'
import MarginPercent from './MarginPercent.vue'
import MarginText from './MarginText.vue'
import OutboundOrderItemEditDialog from './OutboundOrderItemEditDialog.vue'
import PriceExplanationButton from './PriceExplanationButton.vue'

const props = defineProps<{
  /** Document currency (what the customer sees): selling prices and totals are in it. */
  currency: string
  /** Base currency: purchase prices and margins are in it. */
  baseCurrency: string
  /** Base currency units per 1 unit of the document currency (frozen on the order). */
  exchangeRate: number
  readonly?: boolean
  orderCode: string
  customerCode?: string
  /** Customer orders by own codes - every item has to have one. */
  requiresOwnCodes?: boolean
}>()

defineEmits<{ (e: 'remove'): void }>()

const item = defineModel<OutboundOrderItemSchema>('item', { required: true })

const ownCodeMissing = computed(() => !!props.requiresOwnCodes && !item.value.customer_product_code)

const { minimumMarkupPercent } = useMinimumProfit()
const belowMinimumProfit = computed(() =>
  itemIsBelowMinimumProfit(item.value, minimumMarkupPercent.value),
)

const returnSelection = useReturnSelection()

const cardLayout = useOrderItemCardLayout()
const editDialog = ref(false)
const removeDialog = ref(false)

const foreign = computed(() => props.currency !== props.baseCurrency)
const unitPrice = computed(() => Number(item.value.document_unit_price).toFixed(2))
const totalPrice = computed(() => Number(item.value.document_total_price).toFixed(2))

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
