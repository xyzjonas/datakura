<template>
  <q-dialog v-model="show" @before-show="reset" @hide="reset">
    <q-card class="w-full max-w-lg">
      <q-card-section class="flex items-start gap-2 pb-0">
        <div class="flex flex-col">
          <span class="text-xl uppercase">Skenovat existující zboží</span>
          <span class="text-gray-5 text-sm">
            Naskenujte původní čárový kód vráceného zboží - příjemkou se vrátí přesně tato položka.
          </span>
        </div>
        <q-btn flat round dense icon="sym_o_close" v-close-popup class="ml-auto" />
      </q-card-section>

      <q-card-section class="flex flex-col gap-3">
        <q-input
          v-model="barcode"
          outlined
          autofocus
          label="Čárový kód"
          icon="sym_o_qr_code_scanner"
          :loading="matching"
          :error="!!error"
          :error-message="error ?? undefined"
          data-test="returned-item-barcode"
          @keydown.enter.prevent="match"
        >
          <template #prepend><q-icon name="sym_o_qr_code_scanner" /></template>
        </q-input>

        <div
          v-if="matched"
          class="flex flex-col gap-1 p-3 rounded border border-solid border-primary"
          data-test="returned-item-match"
        >
          <span class="text-xs text-muted uppercase">Nalezená položka</span>
          <span class="font-semibold">{{ matched.warehouse_item.product.name }}</span>
          <span class="text-xs font-mono text-gray-6">
            {{ matched.warehouse_item.primary_barcode ?? matched.warehouse_item.product.code }}
          </span>
          <span class="text-sm">
            {{ matched.warehouse_item.amount }} {{ matched.warehouse_item.product.unit }}
            <template v-if="matched.warehouse_item.outbound_order_code">
              · vydáno výdejkou {{ matched.warehouse_item.outbound_order_code }}
            </template>
          </span>
        </div>
      </q-card-section>

      <q-card-actions align="right" class="px-4 pb-4">
        <q-btn flat color="negative" label="zrušit" v-close-popup />
        <q-btn
          v-if="!matched"
          unelevated
          color="primary"
          label="vyhledat"
          :disable="!barcode.trim()"
          :loading="matching"
          data-test="returned-item-match-btn"
          @click="match"
        />
        <q-btn
          v-else
          unelevated
          color="primary"
          label="evidovat tuto položku"
          :loading="claiming"
          data-test="returned-item-claim"
          @click="claim"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import {
  warehouseApiRoutesWarehouseClaimReturnedItem,
  warehouseApiRoutesWarehouseMatchReturnedItem,
  type InboundWarehouseOrderSchema,
  type ReturnedItemMatchSchema,
} from '@/client'
import { useApi } from '@/composables/use-api'
import { ref } from 'vue'

const props = defineProps<{ orderCode: string }>()
const emit = defineEmits<{ (e: 'claimed', order: InboundWarehouseOrderSchema): void }>()

const show = defineModel<boolean>('show', { default: false })

const { onResponse } = useApi()

const barcode = ref('')
const matched = ref<ReturnedItemMatchSchema | null>(null)
const matching = ref(false)
const claiming = ref(false)
const error = ref<string | null>(null)

const reset = () => {
  barcode.value = ''
  matched.value = null
  error.value = null
}

const match = async () => {
  const code = barcode.value.trim()
  if (!code || matching.value) {
    return
  }
  matching.value = true
  error.value = null
  try {
    const data = onResponse(
      await warehouseApiRoutesWarehouseMatchReturnedItem({
        path: { code: props.orderCode },
        body: { barcode: code },
      }),
      { hideNotification: true },
    )
    if (data) {
      matched.value = data.data
    } else {
      error.value = 'Položka nenalezena - zkontrolujte, že byla vydána touto objednávkou.'
    }
  } finally {
    matching.value = false
  }
}

const claim = async () => {
  if (!matched.value) {
    return
  }
  claiming.value = true
  try {
    const data = onResponse(
      await warehouseApiRoutesWarehouseClaimReturnedItem({
        path: { code: props.orderCode },
        body: {
          order_item_id: matched.value.order_item_id,
          warehouse_item_id: matched.value.warehouse_item.id,
        },
      }),
    )
    if (data) {
      emit('claimed', data.data)
      show.value = false
    }
  } finally {
    claiming.value = false
  }
}
</script>
