<template>
  <div class="flex flex-col flex-1 gap-2">
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
        <div class="text-xs text-gray-5">{{ item.product.code }}</div>
      </div>

      <div class="grid items-center grid-cols-4 flex-1 text-right">
        <!-- Amount -->
        <div class="flex flex-col">
          <span class="text-lg font-bold tabular-nums">{{ item.amount }}</span>
          <div class="text-xs text-gray-5">
            {{ item.amount }} x <q-badge color="gray">{{ item.product.unit }}</q-badge>
          </div>
        </div>

        <!-- Purchase price -->
        <div class="flex flex-col" data-test="item-purchase-price">
          <span class="tabular-nums font-semibold">{{ unitPrice }}</span>
          <span>{{ currency }}</span>
          <span class="text-xs text-muted">za {{ item.product.unit }}</span>
        </div>

        <!-- Total price -->
        <div class="flex flex-col" data-test="item-total-price">
          <span class="text-lg font-bold tabular-nums">{{ totalPrice }}</span>
          <span>{{ currency }}</span>
        </div>

        <!-- Actions -->
        <div class="flex gap-1 justify-end">
          <EditIconButton @click="editDialog = true" :disable="readonly">
            <q-tooltip>Upravit</q-tooltip>
          </EditIconButton>
          <CloseIconButton @click="removeDialog = true" :disable="readonly">
            <q-tooltip>Odebrat</q-tooltip>
          </CloseIconButton>
        </div>
      </div>
    </div>
  </div>

  <ConfirmDialog v-model:show="removeDialog" title="Odebrat položku" @confirm="$emit('remove')">
    Opravdu odebrat položku <strong>{{ item.product.name }}</strong
    >?
  </ConfirmDialog>

  <InboundOrderItemEditDialog
    v-model:show="editDialog"
    v-model:item="item"
    :currency="currency"
    :order-code="orderCode"
  />
</template>

<script setup lang="ts">
import type { InboundOrderItemSchema } from '@/client'
import { computed, ref } from 'vue'
import CloseIconButton from '../common/buttons/CloseIconButton.vue'
import EditIconButton from '../common/buttons/EditIconButton.vue'
import ConfirmDialog from '../ConfirmDialog.vue'
import IndexRectangle from '../IndexRectangle.vue'
import InboundOrderItemEditDialog from './InboundOrderItemEditDialog.vue'

defineProps<{
  currency: string
  readonly?: boolean
  orderCode: string
}>()

defineEmits<{ (e: 'remove'): void }>()

const item = defineModel<InboundOrderItemSchema>('item', { required: true })

const editDialog = ref(false)
const removeDialog = ref(false)

const unitPrice = computed(() => Number(item.value.unit_price).toFixed(2))
const totalPrice = computed(() => Number(item.value.total_price).toFixed(2))
</script>
