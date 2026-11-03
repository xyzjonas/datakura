<template>
  <ForegroundPanel class="flex flex-col">
    <template #header>
      <div class="flex items-center justify-between gap-2">
        <span class="text-xs text-muted">DOPRAVA</span>
        <q-btn
          v-if="shipping && editable"
          flat
          dense
          size="sm"
          icon="sym_o_delete"
          color="negative"
          data-testid="shipping-remove"
          @click="emit('remove')"
        >
          <q-tooltip :offset="[0, 10]">Odebrat dopravu</q-tooltip>
        </q-btn>
      </div>
    </template>

    <div
      v-if="!shipping"
      class="flex items-center justify-between gap-3 text-gray-5"
      data-testid="shipping-empty"
    >
      <span class="flex items-center gap-2">
        <q-icon name="sym_o_local_shipping" size="24px" />
        Doprava zatím není zadána
      </span>
      <q-btn
        v-if="editable"
        unelevated
        color="primary"
        icon="sym_o_add"
        label="zadat dopravu"
        @click="emit('edit')"
      />
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-5">
      <div class="flex flex-col gap-1">
        <span class="flex items-center gap-2 text-lg font-bold text-primary">
          <q-icon name="sym_o_local_shipping" size="24px" />
          {{ shipping.shipping_type.name }}
        </span>
        <div v-if="shipping.package_number" class="flex items-center gap-1 text-sm">
          <small class="text-muted">číslo balíku:</small>
          <strong>{{ shipping.package_number }}</strong>
          <CopyToClipBoardButton :text="shipping.package_number" />
        </div>
        <div class="flex items-center gap-1 text-sm">
          <q-icon name="sym_o_straighten" size="16px" class="text-muted" />
          <span data-testid="shipping-dimensions">{{ dimensions }}</span>
        </div>
        <div class="flex items-center gap-1 text-sm">
          <q-icon name="sym_o_weight" size="16px" class="text-muted" />
          <span data-testid="shipping-weight">{{ formattedWeight }} g</span>
        </div>
      </div>

      <div class="flex flex-col gap-0.5 text-sm" data-testid="shipping-address">
        <strong class="text-base">{{ shipping.name || '—' }}</strong>
        <span>{{ shipping.street }}</span>
        <span>{{ [shipping.postal_code, shipping.city].filter(Boolean).join(' ') }}</span>
        <span class="text-muted">{{ shipping.state }}</span>
        <span v-if="shipping.email" class="flex items-center gap-1 mt-1">
          <q-icon name="sym_o_mail" size="16px" class="text-muted" />{{ shipping.email }}
        </span>
        <span v-if="shipping.phone" class="flex items-center gap-1">
          <q-icon name="sym_o_call" size="16px" class="text-muted" />{{ shipping.phone }}
        </span>
      </div>

      <div class="flex flex-col gap-1 md:items-end">
        <template v-if="shipping.price != null || shipping.price_with_vat != null">
          <span class="text-xs text-muted">Cena dopravy</span>
          <span v-if="shipping.price != null" data-testid="shipping-price">
            {{ formatPrice(shipping.price) }}
          </span>
          <strong v-if="shipping.price_with_vat != null" data-testid="shipping-price-vat">
            {{ formatPrice(shipping.price_with_vat) }} s DPH
          </strong>
        </template>
        <span v-else class="text-sm text-muted">Cena nezadána</span>
        <q-btn
          v-if="editable"
          class="mt-auto"
          unelevated
          color="primary"
          icon="edit"
          label="upravit"
          data-testid="shipping-edit"
          @click="emit('edit')"
        />
      </div>
    </div>
  </ForegroundPanel>
</template>

<script setup lang="ts">
import type { OutboundOrderShippingSchema } from '@/client'
import CopyToClipBoardButton from '@/components/CopyToClipBoardButton.vue'
import ForegroundPanel from '@/components/ForegroundPanel.vue'
import { computed } from 'vue'

const props = defineProps<{
  shipping: OutboundOrderShippingSchema | null
  /** derived from the order items */
  weight: number
  currency: string
  editable?: boolean
}>()

const emit = defineEmits<{
  (e: 'edit'): void
  (e: 'remove'): void
}>()

const formattedWeight = computed(() => (Math.round(props.weight * 100) / 100).toFixed(2))

const dimensions = computed(() => {
  const { width, height, depth } = props.shipping ?? {}
  if (width == null && height == null && depth == null) {
    return 'rozměry nezadány'
  }
  return [width, height, depth].map((value) => value ?? '?').join(' × ') + ' cm'
})

const formatPrice = (value: number) =>
  `${value.toLocaleString('cs-CZ', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${props.currency}`
</script>
