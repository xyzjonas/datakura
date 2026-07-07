<template>
  <div class="flex items-center gap-5 w-full flex-nowrap flex-col md:flex-row">
    <div
      class="grid grid-cols-1 md:grid-cols-[minmax(0,1fr)_auto_5rem_8rem_8rem] items-center gap-x-3 gap-y-1.5 w-full min-w-0"
    >
      <div class="flex items-center gap-5 min-w-0">
        <IndexRectangle :index="item.index + 1" />

        <!-- Product -->
        <div class="min-w-12">
          <router-link
            :to="{ name: 'productDetail', params: { productCode: item.product.code } }"
            class="link text-sm font-medium leading-tight"
            >{{ item.product.name }}</router-link
          >
          <div class="text-xs text-gray-5 mt-0.5">{{ item.product.code }}</div>
        </div>

        <!-- Note (readonly) -->
        <CommentCard v-if="item.note" title="Poznámka" class="text-xs max-w-xs">
          {{ item.note }}
        </CommentCard>
      </div>

      <!-- Status badges -->
      <div class="hidden sm:flex items-center gap-1.5">
        <ProductAvailability :product-code="item.product.code" />
        <PackageTypeBadge
          v-if="item.desired_package_type_name"
          :package-type="item.desired_package_type_name"
        />
        <BatchBadge v-if="item.desired_batch_code" :batch-code="item.desired_batch_code" />
        <q-icon v-if="item.note" name="sym_o_sticky_note_2" size="xs" class="text-gray-4">
          <q-tooltip class="text-xs">{{ item.note }}</q-tooltip>
        </q-icon>
      </div>

      <!-- Amount -->
      <div class="md:text-right">
        <div class="tabular-nums flex items-center md:justify-end gap-1">
          <span class="text-lg">{{ item.amount }}</span>
          <q-badge color="gray" rounded>{{ item.product.unit }}</q-badge>
        </div>
        <div class="text-xs text-gray-5">Množství</div>
      </div>

      <!-- Unit price -->
      <div class="md:text-right">
        <div class="text-sm tabular-nums text-nowrap">{{ unitPrice }} {{ currency }}</div>
        <div class="text-xs text-gray-5">/ {{ item.product.unit }}</div>
      </div>

      <!-- Total price -->
      <div class="md:text-right">
        <div class="text-sm font-semibold tabular-nums text-primary">
          {{ totalPrice }} {{ currency }}
        </div>
        <div class="text-xs text-gray-5">Celkem</div>
      </div>
    </div>
    <!-- Actions -->
    <div v-if="!readonly" class="flex items-center gap-8 sm:gap-2 shrink-0 pl-5">
      <q-btn unelevated icon="sym_o_delete" color="negative" @click="$emit('remove')">
        <q-tooltip>Odebrat</q-tooltip>
      </q-btn>
      <q-btn
        unelevated
        icon="sym_o_edit"
        label="upravit"
        color="primary"
        @click="editDialog = true"
      >
        <q-tooltip>Upravit</q-tooltip>
      </q-btn>
    </div>
  </div>

  <OutboundOrderItemEditDialog
    v-model:show="editDialog"
    v-model:item="item"
    :currency="currency"
    :order-code="orderCode"
    :customer-code="customerCode"
  />
</template>

<script setup lang="ts">
import type { OutboundOrderItemSchema } from '@/client'
import { computed, ref } from 'vue'
import IndexRectangle from '../IndexRectangle.vue'
import PackageTypeBadge from '../PackageTypeBadge.vue'
import BatchBadge from '../warehouse/BatchBadge.vue'
import ProductAvailability from '../product/ProductAvailability.vue'
import OutboundOrderItemEditDialog from './OutboundOrderItemEditDialog.vue'
import CommentCard from '../CommentCard.vue'

defineProps<{
  currency: string
  readonly?: boolean
  orderCode: string
  customerCode?: string
}>()

defineEmits<{ (e: 'remove'): void }>()

const item = defineModel<OutboundOrderItemSchema>('item', { required: true })

const editDialog = ref(false)

const unitPrice = computed(() => Number(item.value.unit_price).toFixed(2))
const totalPrice = computed(() => Number(item.value.total_price).toFixed(2))
</script>
