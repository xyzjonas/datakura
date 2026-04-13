<template>
  <div class="flex items-start gap-2 w-full">
    <div class="flex flex-col min-w-70">
      <div class="flex items-center gap-1">
        <q-btn
          flat
          dense
          icon="sym_o_help"
          size="sm"
          :color="marginAmount >= 0 ? 'positive' : 'negative'"
        >
          <q-popup-proxy>
            <q-card class="p-3 max-w-80">
              <div class="text-sm font-bold mb-2">Vysvětlení ceny</div>
              <div class="text-xs mb-1">
                Základní cena: {{ basePrice.toFixed(2) }} {{ currency }}
              </div>
              <div class="text-xs mb-1">
                Nákupní cena (průměr): {{ avgPurchasePrice.toFixed(2) }} {{ currency }}
              </div>
              <div class="text-xs mb-1">
                Sleva: {{ discountPercent.toFixed(2) }}% ({{ reason }})
              </div>
              <div class="text-xs mb-1">
                Navržená cena: {{ suggestedPrice.toFixed(2) }} {{ currency }}
              </div>
              <div class="text-xs font-medium">
                Zvolená cena: {{ resolvedModelValue.toFixed(2) }} {{ currency }}
              </div>
            </q-card>
          </q-popup-proxy>
        </q-btn>
        <span :class="marginClass">Marže: {{ marginText }}</span>
      </div>
      <q-input
        :model-value="editorValue"
        :readonly="readonly"
        dense
        outlined
        class="w-full"
        label="Prodejní cena"
        @update:model-value="onInputChange"
        :debounce="300"
      >
        <template #append>
          <span class="text-xs">{{ currency }} / {{ unit }}</span>
        </template>
      </q-input>

      <q-slider
        :model-value="editorValue"
        :min="sliderMin"
        :max="sliderMax"
        :step="0.01"
        color="primary"
        label
        class="pt-1 px-2"
        :disable="readonly"
        @update:model-value="onSliderChange"
        @change="onSliderCommit"
      />

      <div class="flex items-center gap-2 flex-wrap">
        <q-btn
          v-if="isOverridden && !readonly"
          dense
          flat
          no-caps
          size="sm"
          color="grey-6"
          icon="sym_o_restart_alt"
          label="Resetovat"
          @click="resetToSuggested"
        />
        <q-btn
          v-if="canPersistOverride && isOverridden"
          dense
          flat
          no-caps
          size="sm"
          color="primary"
          icon="sym_o_save"
          label="Uložit pro zákazníka"
          :loading="overrideSaving"
          @click="emit('persistOverride')"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

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
    priceSource?: string | null
    canPersistOverride?: boolean
    overrideSaving?: boolean
    readonly?: boolean
  }>(),
  {
    readonly: false,
    priceSource: null,
    canPersistOverride: false,
    overrideSaving: false,
  },
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: number): void
  (e: 'persistOverride'): void
}>()

const resetToSuggested = () => {
  const suggested = Number(props.suggestedPrice.toFixed(2))
  editorValue.value = suggested
  emit('update:modelValue', suggested)
}

const resolvedModelValue = computed(() => Number(props.modelValue ?? 0))
const editorValue = ref(resolvedModelValue.value)

watch(
  () => props.modelValue,
  () => {
    editorValue.value = resolvedModelValue.value
  },
)

const SLIDER_DEBOUNCE_MS = 300
let sliderDebounceTimer: ReturnType<typeof setTimeout> | null = null

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

const isOverridden = computed(
  () => Math.abs(resolvedModelValue.value - props.suggestedPrice) >= 0.01,
)

const onInputChange = (value: number | string | null) => {
  const numberValue = Number(value ?? 0)
  const sanitizedValue = Number.isFinite(numberValue) ? numberValue : 0
  editorValue.value = sanitizedValue
  emit('update:modelValue', sanitizedValue)
}

const onSliderChange = (value: number | null) => {
  const sanitizedValue = Number((value ?? 0).toFixed(2))
  editorValue.value = sanitizedValue

  if (sliderDebounceTimer) {
    clearTimeout(sliderDebounceTimer)
  }
  sliderDebounceTimer = setTimeout(() => {
    emit('update:modelValue', sanitizedValue)
    sliderDebounceTimer = null
  }, SLIDER_DEBOUNCE_MS)
}

const onSliderCommit = (value: number | null) => {
  const sanitizedValue = Number((value ?? 0).toFixed(2))
  editorValue.value = sanitizedValue

  if (sliderDebounceTimer) {
    clearTimeout(sliderDebounceTimer)
    sliderDebounceTimer = null
  }
  emit('update:modelValue', sanitizedValue)
}

onBeforeUnmount(() => {
  if (sliderDebounceTimer) {
    clearTimeout(sliderDebounceTimer)
    sliderDebounceTimer = null
  }
})
</script>
