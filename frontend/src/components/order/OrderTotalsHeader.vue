<template>
  <div class="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6" data-test="order-totals-header">
    <div class="flex justify-between">
      <div class="flex flex-col gap-2 p-4">
        <span>Hodnota ve skladové ceně</span>
        <span>
          <strong class="text-lg">{{ formattedPurchaseValue }}</strong> {{ currency }}
        </span>
      </div>
      <q-separator vertical />
    </div>

    <div class="flex justify-between">
      <div class="flex flex-col gap-2 p-4">
        <span>Celková prodejní cena</span>
        <span class="text-primary">
          <strong class="text-lg">{{ formattedTotalPrice }}</strong> {{ currency }}
        </span>
      </div>
      <q-separator vertical />
    </div>

    <div class="flex justify-between" data-test="order-margin-percent">
      <div class="flex flex-col gap-2 p-4">
        <span>Marže</span>
        <span :class="marginColor">
          <strong class="text-lg">{{ formattedMarginPercent || '–' }}</strong>
        </span>
      </div>
      <q-separator vertical />
    </div>

    <div class="flex justify-between" data-test="order-markup-percent">
      <div class="flex flex-col gap-2 p-4">
        <span>Přirážka</span>
        <span :class="marginColor">
          <strong class="text-lg">{{ formattedMarkupPercent || '–' }}</strong>
        </span>
      </div>
      <q-separator vertical />
    </div>

    <div class="flex justify-between" data-test="order-profit">
      <div class="flex flex-col gap-2 p-4">
        <span>Zisk</span>
        <span :class="marginColor">
          <strong class="text-lg">{{ formattedMarginValue }}</strong> {{ currency }}
        </span>
      </div>
      <q-separator vertical />
    </div>

    <div class="flex justify-between">
      <div class="flex flex-col gap-2 p-4">
        <span>Hmotnost objednávky</span>
        <div class="flex gap-2 items-center">
          <q-icon name="sym_o_weight" size="sm" />
          <span>
            <strong class="text-lg">{{ formattedWeight }}</strong> kg
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useOrderTotals, type OrderTotalsSource } from '@/composables/use-order-totals'

// Accepts any order-like object with items (outbound today, inbound later).
const props = defineProps<{ order: OrderTotalsSource }>()

const {
  formattedTotalPrice,
  formattedPurchaseValue,
  currency,
  formattedMarginValue,
  formattedMarginPercent,
  formattedMarkupPercent,
  formattedWeight,
  isMarginPositive,
} = useOrderTotals(() => props.order)

const marginColor = computed(() => (isMarginPositive.value ? 'text-green' : 'text-red'))
</script>
