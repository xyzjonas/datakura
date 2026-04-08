<template>
  <q-card flat bordered class="bg-transparent">
    <q-card-section class="flex justify-between items-start gap-2">
      <div class="min-w-0">
        <div class="font-semibold">{{ priceTypeLabel }}</div>
        <div class="text-gray-5 text-sm truncate">
          {{ targetDescription }}
        </div>
      </div>
      <div class="text-right">
        <div class="text-gray-5 text-xs">Cena / MJ</div>
        <div class="text-primary font-bold">{{ finalPrice }} Kč</div>
      </div>
    </q-card-section>

    <q-separator />

    <q-card-section class="space-y-2">
      <div class="flex items-center justify-between gap-2">
        <span class="text-gray-5">Skupina</span>
        <span class="truncate max-w-48 text-right">{{ row.group ?? '—' }}</span>
      </div>
      <div class="flex items-center justify-between gap-2">
        <span class="text-gray-5">Zákazník</span>
        <router-link
          v-if="row.customer?.code"
          :to="{ name: 'customerDetail', params: { customerCode: row.customer.code } }"
          class="link truncate max-w-48 text-right"
        >
          {{ row.customer.name }}
        </router-link>
        <span v-else>—</span>
      </div>
      <div class="flex items-center justify-between gap-2">
        <span class="text-gray-5">Sleva</span>
        <span class="font-semibold">{{ row.discount_percent }} %</span>
      </div>
    </q-card-section>

    <q-card-actions align="right">
      <q-btn
        v-if="row.price_id >= 0"
        flat
        round
        dense
        icon="sym_o_close_small"
        color="negative"
        :loading="deletingPriceId === row.price_id"
        @click="$emit('delete', row.price_id)"
      >
        <q-tooltip>Odstranit cenu</q-tooltip>
      </q-btn>
    </q-card-actions>
  </q-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DynamicProductPriceSchema } from '@/client'

type DynamicPriceRow = DynamicProductPriceSchema & {
  customer?: { code: string; name: string } | null
}

const props = defineProps<{
  row: DynamicPriceRow
  priceTypeLabel: string
  finalPrice: number
  deletingPriceId: number | null
}>()

defineEmits<{ delete: [priceId: number] }>()

const targetDescription = computed(() => {
  if (props.row.group) {
    return `Skupina: ${props.row.group}`
  }
  if (props.row.customer?.code) {
    return `Zákazník: ${props.row.customer.code}`
  }
  return 'Bez cíle'
})
</script>

<style lang="scss" scoped></style>