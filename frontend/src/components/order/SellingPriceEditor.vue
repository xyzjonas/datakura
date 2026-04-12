<template>
  <div class="flex items-start gap-2">
    <div class="flex flex-col min-w-70">
      <q-input
        :model-value="resolvedModelValue"
        :readonly="readonly"
        dense
        outlined
        class="max-w-50"
        label="Prodejní cena"
        @update:model-value="onInputChange"
        :debounce="300"
      >
        <template #append>
          <span class="text-xs">{{ currency }} / {{ unit }}</span>
        </template>
      </q-input>

      <q-slider
        :model-value="resolvedModelValue"
        :min="sliderMin"
        :max="sliderMax"
        :step="0.01"
        color="primary"
        label
        label-always
        class="pt-1 px-2"
        :disable="readonly"
        @update:model-value="onSliderChange"
      />

      <div class="text-xs text-gray-6 px-2">
        Navrženo: {{ suggestedPrice.toFixed(2) }} {{ currency }}
      </div>
    </div>

    <div class="flex flex-col items-start min-w-48 pt-2">
      <span :class="marginClass">Marže: {{ marginText }}</span>
      <q-btn flat dense icon="sym_o_help" color="primary" class="mt-1">
        <q-popup-proxy>
          <q-card class="p-3 max-w-80">
            <div class="text-sm font-bold mb-2">Vysvětlení ceny</div>
            <div class="text-xs mb-1">Základní cena: {{ basePrice.toFixed(2) }} {{ currency }}</div>
            <div class="text-xs mb-1">
              Nákupní cena (průměr): {{ avgPurchasePrice.toFixed(2) }} {{ currency }}
            </div>
            <div class="text-xs mb-1">Sleva: {{ discountPercent.toFixed(2) }}% ({{ reason }})</div>
            <div class="text-xs mb-1">
              Navržená cena: {{ suggestedPrice.toFixed(2) }} {{ currency }}
            </div>
            <div class="text-xs font-medium">
              Zvolená cena: {{ resolvedModelValue.toFixed(2) }} {{ currency }}
            </div>
          </q-card>
        </q-popup-proxy>
      </q-btn>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: number | null | undefined
    currency: string
    unit: string
    basePrice: number
    suggestedPrice: number
    avgPurchasePrice: number
    discountPercent: number
    reason: string
    readonly?: boolean
  }>(),
  {
    readonly: false,
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: number): void
}>()

const resolvedModelValue = computed(() => Number(props.modelValue ?? 0))

const sliderMin = computed(() =>
  Math.max(0, Math.floor((props.suggestedPrice * 0.5) / 0.01) * 0.01),
)
const sliderMax = computed(() =>
  Math.max(props.suggestedPrice * 1.5, resolvedModelValue.value * 1.2, 1),
)

const marginAmount = computed(() => resolvedModelValue.value - props.avgPurchasePrice)
const marginPercent = computed(() => {
  if (!props.avgPurchasePrice) {
    return 0
  }
  return (marginAmount.value / props.avgPurchasePrice) * 100
})

const marginClass = computed(() =>
  marginAmount.value >= 0
    ? 'text-xs text-positive font-medium'
    : 'text-xs text-negative font-medium',
)

const marginText = computed(() => {
  const sign = marginAmount.value >= 0 ? '+' : ''
  return `${sign}${marginAmount.value.toFixed(2)} (${sign}${marginPercent.value.toFixed(1)}%)`
})

const onInputChange = (value: number | string | null) => {
  const numberValue = Number(value ?? 0)
  emit('update:modelValue', Number.isFinite(numberValue) ? numberValue : 0)
}

const onSliderChange = (value: number | null) => {
  emit('update:modelValue', Number((value ?? 0).toFixed(2)))
}
</script>
