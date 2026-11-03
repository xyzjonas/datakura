<template>
  <div
    class="w-full flex flex-col gap-2.5 p-3.5 rounded-xl border border-solid light:border-slate-200 dark:border-gray-7 light:bg-white shadow-sm"
    data-test="order-item-card"
  >
    <div class="flex items-start justify-between gap-2">
      <div class="flex items-start gap-2 flex-1 min-w-0">
        <span
          class="inline-flex items-center justify-center px-1.5 py-0.5 text-xs font-semibold rounded border border-solid shrink-0 light:text-slate-600 light:bg-slate-100 light:border-slate-200 dark:border-gray-7"
          data-test="item-index"
          >#{{ item.index + 1 }}</span
        >
        <div class="flex flex-col min-w-0">
          <router-link
            :to="{ name: 'productDetail', params: { productCode: item.product.code } }"
            class="link text-sm font-semibold leading-snug break-words"
            >{{ item.product.name }}</router-link
          >
          <span class="text-xs text-slate-500 font-mono mt-1">{{ item.product.code }}</span>
          <CertificationBadge
            class="mt-1 self-start"
            :requires-certification="requiresCertification"
            :certification="certification"
          />
        </div>
      </div>
      <div class="flex items-center gap-1 shrink-0">
        <EditIconButton class="min-w-9 min-h-9" :disable="readonly" @click="$emit('edit')" />
        <CloseIconButton class="min-w-9 min-h-9" :disable="readonly" @click="$emit('remove')" />
      </div>
    </div>

    <div
      class="flex items-center justify-between px-2.5 py-1.5 rounded-lg light:bg-slate-50 dark:bg-dark-6"
      data-test="item-amount"
    >
      <div class="flex items-center gap-2 text-xs">
        <q-icon name="sym_o_inventory_2" size="1rem" color="primary" />
        <span class="font-semibold tabular-nums">{{ item.amount }} {{ item.product.unit }}</span>
      </div>
    </div>

    <div class="pt-1 flex flex-col gap-1.5 border-0 border-t border-solid light:border-slate-100">
      <div class="flex items-center justify-between text-xs text-slate-500">
        <div data-test="item-purchase-price">
          Nákupní / {{ item.product.unit }}:
          <span class="font-medium">{{ money(purchasePrice) }}</span>
        </div>
        <div v-if="sellingPrice !== undefined" class="text-right" data-test="item-unit-price">
          Prodejní / {{ item.product.unit }}:
          <span class="font-medium">{{ money(sellingPrice) }}</span>
        </div>
      </div>

      <div class="flex items-end justify-between mt-0.5">
        <div v-if="margin" class="flex flex-col" data-test="item-margin">
          <span class="text-[11px] text-slate-500">Marže položky</span>
          <span
            :class="['text-xs font-semibold', margin.amount >= 0 ? 'text-green-600' : 'text-red']"
          >
            {{ formatDecimal(margin.amount, true) }} {{ currency }}
            <span class="text-[11px] font-medium"
              >({{ formatDecimal(margin.percent, true) }} %)</span
            >
          </span>
        </div>
        <div v-else />
        <span class="text-base font-bold tabular-nums leading-none" data-test="item-total-price">{{
          money(item.total_price)
        }}</span>
      </div>
    </div>

    <div v-if="item.note" class="text-xs text-muted">{{ item.note }}</div>
  </div>
</template>

<script setup lang="ts">
import { formatDecimal } from '@/utils/format-number'
import type { Margin } from '@/utils/margin'
import CertificationBadge from '../certification/CertificationBadge.vue'
import CloseIconButton from '../common/buttons/CloseIconButton.vue'
import EditIconButton from '../common/buttons/EditIconButton.vue'

const props = defineProps<{
  item: {
    index: number
    amount: number
    total_price: number
    note?: string | null
    product: { code: string; name: string; unit: string }
  }
  currency: string
  readonly?: boolean
  /** Inbound only. */
  requiresCertification?: boolean
  /** Inbound only. */
  certification?: { code: string } | null
  purchasePrice: number
  /** Outbound only. */
  sellingPrice?: number
  /** Outbound only. */
  margin?: Margin
}>()

defineEmits<{ (e: 'edit'): void; (e: 'remove'): void }>()

const money = (value: number) => `${formatDecimal(Number(value))} ${props.currency}`
</script>
