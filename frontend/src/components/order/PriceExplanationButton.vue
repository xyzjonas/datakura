<template>
  <q-btn flat dense rounded icon="sym_o_help" size="sm">
    <q-tooltip class="text-xs">Vysvětlení ceny</q-tooltip>
    <q-popup-proxy>
      <q-card class="p-3 max-w-80">
        <div class="text-lg font-bold text-primary mb-2">Vysvětlení ceny</div>
        <div class="text-xs mb-1 font-bold">
          Základní cena: {{ basePrice.toFixed(2) }} {{ currency }}
        </div>
        <div class="text-xs mb-1">
          Nákupní cena (průměr): {{ avgPurchasePrice.toFixed(2) }} {{ currency }}
        </div>
        <div class="text-xs mb-1">Sleva: {{ discountPercent.toFixed(2) }}% ({{ reason }})</div>
        <div v-if="priceSource === 'NO_DISCOUNT'" class="text-xs mb-1 text-negative">
          Sleva nepoužita: slevové skupiny nejsou pro tento produkt povoleny.
        </div>
        <div class="text-xs mb-1">
          Navržená cena: {{ suggestedPrice.toFixed(2) }} {{ currency }}
        </div>
        <div class="text-positive font-medium">
          Zvolená cena: {{ selectedPrice.toFixed(2) }} {{ currency }}
        </div>
      </q-card>
    </q-popup-proxy>
  </q-btn>
</template>

<script setup lang="ts">

defineProps<{
  currency: string
  basePrice: number
  suggestedPrice: number
  avgPurchasePrice: number
  selectedPrice: number
  discountPercent: number
  reason: string
  priceSource?: string | null
}>()
</script>
