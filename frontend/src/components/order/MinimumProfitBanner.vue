<template>
  <q-banner
    v-if="itemCount || orderBelow"
    rounded
    class="bg-light-red text-red"
    data-test="minimum-profit-banner"
  >
    <template #avatar><q-icon name="sym_o_error" color="negative" /></template>
    <div>
      Minimální povolený zisk je přirážka {{ format(minimumMarkupPercent) }} % (marže
      {{ format(markupToMargin(minimumMarkupPercent)) }} %).
    </div>
    <div v-if="itemCount" data-test="minimum-profit-items">
      Pod hranicí je {{ itemCount }} {{ itemCount === 1 ? 'položka' : 'položek' }}.
    </div>
    <div v-if="orderBelow" data-test="minimum-profit-order">
      Celkový zisk {{ documentLabel }} je pod hranicí.
    </div>
  </q-banner>
</template>

<script setup lang="ts">
import { markupToMargin } from '@/utils/minimum-profit'

defineProps<{
  /** Number of items below the minimum profit. */
  itemCount: number
  /** The order as a whole is below the minimum profit. */
  orderBelow: boolean
  minimumMarkupPercent: number
  /** 'objednávky' / 'nabídky' */
  documentLabel: string
}>()

const format = (value: number) => Number(value.toFixed(2))
</script>
